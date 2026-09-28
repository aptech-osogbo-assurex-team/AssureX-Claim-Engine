"""Persistence service for registering claims before evaluation."""

from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session

from src.domain.schemas import Claim, Document
from src.persistence.models import (
    AuditLogRecord,
    ClaimRecord,
    DocumentRecord,
    ProductRecord,
    RepairRecordDB,
    WarrantyRecord,
    UserRecord,
)


class ClaimRegistrationService:
    def __init__(self, session_factory: Callable[[], Session]):
        self.session_factory = session_factory

    def register(self, claim: Claim) -> Claim:
        session = self.session_factory()
        now = datetime.now(timezone.utc)
        try:
            if session.query(ClaimRecord).filter_by(claim_id=claim.claim_id).first() is not None:
                raise ValueError(f"claim {claim.claim_id} already exists")

            if session.query(UserRecord).filter_by(user_id=claim.customer_id).one_or_none() is None:
                raise ValueError("customer account does not exist")

            existing_product = session.get(ProductRecord, claim.product.product_id)
            if existing_product is not None:
                if existing_product.customer_id != claim.customer_id:
                    raise ValueError("product does not belong to the authenticated customer")
                stored_product_identity = (
                    existing_product.serial_number,
                    existing_product.model_number,
                    existing_product.brand,
                )
                incoming_product_identity = (
                    claim.product.serial_number,
                    claim.product.model_number,
                    claim.product.brand,
                )
                if stored_product_identity != incoming_product_identity:
                    raise ValueError("existing product identity conflicts with the submitted product")

            existing_warranty = session.get(WarrantyRecord, claim.warranty.warranty_id)
            if existing_warranty is not None and existing_warranty.product_id != claim.product.product_id:
                raise ValueError("warranty is already linked to a different product")

            session.merge(
                ProductRecord(
                    product_id=claim.product.product_id,
                    customer_id=claim.customer_id,
                    product_name=claim.product.product_name,
                    category=claim.product.category,
                    brand=claim.product.brand,
                    model_number=claim.product.model_number,
                    serial_number=claim.product.serial_number,
                    purchase_date=claim.product.purchase_date,
                    purchase_price=claim.product.purchase_price,
                    retailer=claim.product.retailer,
                    invoice_number=claim.product.invoice_number,
                    warranty_duration_months=claim.product.warranty_duration_months,
                )
            )
            session.merge(
                WarrantyRecord(
                    warranty_id=claim.warranty.warranty_id,
                    product_id=claim.warranty.product_id,
                    provider=claim.warranty.provider,
                    start_date=claim.warranty.start_date,
                    end_date=claim.warranty.end_date,
                    coverage_conditions=claim.warranty.coverage_conditions,
                    exclusions=claim.warranty.exclusions,
                    service_center=claim.warranty.service_center,
                    extended=claim.warranty.extended,
                    reporting_deadline_days=claim.warranty.reporting_deadline_days,
                    grace_period_days=claim.warranty.grace_period_days,
                    mandatory_document_types=[item.value for item in claim.warranty.mandatory_document_types],
                )
            )
            session.add(
                ClaimRecord(
                    claim_id=claim.claim_id,
                    customer_id=claim.customer_id,
                    product_id=claim.product.product_id,
                    warranty_id=claim.warranty.warranty_id,
                    fault_occurrence_date=claim.fault_occurrence_date,
                    claim_submission_date=claim.claim_submission_date,
                    fault_description=claim.fault_description,
                    fault_category=claim.fault_category,
                    damage_type=claim.damage_type,
                    previous_replacement=claim.previous_replacement,
                    previous_replacement_details=claim.previous_replacement_details,
                    serial_number_match=claim.serial_number_match,
                    duplicate_claim=claim.duplicate_claim,
                    missing_document_types=[item.value for item in claim.missing_document_types],
                    status=claim.status.value,
                )
            )
            for repair in claim.previous_repairs:
                session.merge(
                    RepairRecordDB(
                        repair_id=repair.repair_id,
                        product_id=repair.product_id,
                        repair_date=repair.repair_date,
                        repair_center=repair.repair_center,
                        replaced_parts=repair.replaced_parts,
                        outcome=repair.outcome,
                        repair_cost=repair.repair_cost,
                        authorized=repair.authorized.value,
                    )
                )
            for document in claim.submitted_documents:
                self._persist_document(session, document)

            session.add(
                AuditLogRecord(
                    claim_id=claim.claim_id,
                    user_id=claim.customer_id,
                    action="claim_registered",
                    details={"status": claim.status.value},
                    created_at=now,
                )
            )
            session.commit()
            return claim
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def _persist_document(session: Session, document: Document) -> None:
        session.merge(
            DocumentRecord(
                document_id=document.document_id,
                claim_id=document.claim_id,
                document_type=document.document_type.value,
                filename=document.filename,
                mime_type=document.mime_type,
                size_bytes=document.size_bytes,
                sha256=document.sha256,
                uploaded_at=document.uploaded_at,
                verification_status=document.verification_status.value,
                extracted_data=document.extracted_data,
            )
        )
