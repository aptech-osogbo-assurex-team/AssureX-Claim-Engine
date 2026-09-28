"""End-to-end claim evaluation orchestration."""

from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session

from src.decision.engine import DecisionEngine
from src.domain.enums import DocumentType
from src.domain.schemas import Claim, FinalDecision, ModelPrediction
from src.ml.inference import PythonClaimPredictor
from src.persistence.models import (
    AuditLogRecord,
    ClaimRecord,
    DecisionRecord,
    NotificationRecord,
    DocumentRecord,
    PredictionRecord,
    ProductRecord,
    RepairRecordDB,
    RuleResultRecord,
    WarrantyRecord,
)
from src.rules.engine import RuleEngine


class ClaimEvaluationService:
    """Run ML, rules, model comparison, decision, and persistence as one unit."""

    def __init__(
        self,
        predictor: PythonClaimPredictor,
        rule_engine: RuleEngine,
        decision_engine: DecisionEngine,
        session_factory: Callable[[], Session],
    ):
        self.predictor = predictor
        self.rule_engine = rule_engine
        self.decision_engine = decision_engine
        self.session_factory = session_factory

    def evaluate(self, claim: Claim, teachable_machine_prediction: ModelPrediction) -> FinalDecision:
        duplicate_flag = claim.duplicate_claim or self._duplicate_claim_exists(claim)
        evaluated_claim = claim.model_copy(update={"duplicate_claim": duplicate_flag})

        python_prediction = self.predictor.predict(evaluated_claim)
        rule_results = self.rule_engine.evaluate(evaluated_claim)
        missing_documents = self._missing_documents(evaluated_claim)
        contradictions = self._contradiction_flags(rule_results)

        final_decision = self.decision_engine.decide(
            evaluated_claim.claim_id,
            python_prediction,
            teachable_machine_prediction,
            rule_results,
            contradiction_flags=contradictions,
            missing_document_flags=missing_documents,
            duplicate_flag=duplicate_flag,
        )

        self._persist(
            evaluated_claim,
            python_prediction,
            teachable_machine_prediction,
            rule_results,
            final_decision,
        )
        return final_decision

    def _persist(self, claim, python_prediction, tm_prediction, rule_results, final_decision) -> None:
        session = self.session_factory()
        now = datetime.now(timezone.utc)
        try:
            existing_product = session.get(ProductRecord, claim.product.product_id)
            if existing_product is not None:
                if existing_product.customer_id != claim.customer_id:
                    raise ValueError("product does not belong to the authenticated customer")
                if (
                    existing_product.serial_number,
                    existing_product.model_number,
                    existing_product.brand,
                ) != (
                    claim.product.serial_number,
                    claim.product.model_number,
                    claim.product.brand,
                ):
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
                    mandatory_document_types=[d.value for d in claim.warranty.mandatory_document_types],
                )
            )
            session.merge(
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
                    missing_document_types=[d.value for d in claim.missing_document_types],
                    status=claim.status.value,
                )
            )

            for document in claim.submitted_documents:
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

            # Re-evaluation should not leave a second set of stale results.
            session.query(PredictionRecord).filter_by(claim_id=claim.claim_id).delete()
            session.query(RuleResultRecord).filter_by(claim_id=claim.claim_id).delete()

            for prediction in (python_prediction, tm_prediction):
                session.add(
                    PredictionRecord(
                        claim_id=claim.claim_id,
                        model_name=prediction.model_name,
                        model_version=prediction.model_version,
                        predicted_class=prediction.predicted_class.value,
                        confidence=prediction.confidence,
                        probabilities={k.value: v for k, v in prediction.probabilities.items()},
                        timestamp=prediction.timestamp,
                    )
                )
            for result in rule_results:
                session.add(
                    RuleResultRecord(
                        claim_id=claim.claim_id,
                        rule_id=result.rule_id,
                        passed=result.passed,
                        severity=result.severity.value,
                        message=result.message,
                        evaluated_at=now,
                    )
                )

            session.merge(
                DecisionRecord(
                    claim_id=final_decision.claim_id,
                    decision=final_decision.decision.value,
                    reasons=final_decision.reasons,
                    supporting_factors=final_decision.supporting_factors,
                    opposing_factors=final_decision.opposing_factors,
                    evidence=final_decision.evidence.model_dump(mode="json"),
                    decided_at=final_decision.decided_at,
                    reviewer_id=final_decision.reviewer_id,
                    reviewer_comments=final_decision.reviewer_comments,
                    override_applied=final_decision.override_applied,
                )
            )

            status_by_decision = {
                "likely_valid": "approved",
                "likely_invalid": "rejected",
                "manual_review_required": "manual_review",
            }
            session.query(ClaimRecord).filter_by(claim_id=claim.claim_id).update(
                {"status": status_by_decision[final_decision.decision.value]}
            )
            session.add(
                NotificationRecord(
                    user_id=claim.customer_id,
                    claim_id=claim.claim_id,
                    notification_type="claim_decision",
                    message=f"Claim {claim.claim_id} evaluation result: {final_decision.decision.value}.",
                    is_read=False,
                    created_at=now,
                )
            )
            session.add(
                AuditLogRecord(
                    claim_id=claim.claim_id,
                    user_id=claim.customer_id,
                    action="claim_evaluated",
                    details={
                        "python_model_version": python_prediction.model_version,
                        "teachable_machine_model_version": tm_prediction.model_version,
                        "decision": final_decision.decision.value,
                    },
                    created_at=now,
                )
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _duplicate_claim_exists(self, claim: Claim) -> bool:
        session = self.session_factory()
        try:
            existing = session.query(ClaimRecord).filter(ClaimRecord.claim_id != claim.claim_id).all()
            product_invoice = claim.product.invoice_number
            for record in existing:
                if record.customer_id != claim.customer_id or record.product_id != claim.product.product_id:
                    continue
                if product_invoice:
                    product = session.get(ProductRecord, record.product_id)
                    if product is not None and product.invoice_number == product_invoice:
                        return True
                if (
                    claim.fault_occurrence_date is not None
                    and record.fault_occurrence_date == claim.fault_occurrence_date
                    and record.fault_category.casefold() == claim.fault_category.casefold()
                ):
                    return True

            incoming_hashes = {document.sha256 for document in claim.submitted_documents}
            if incoming_hashes:
                duplicate_document = (
                    session.query(DocumentRecord)
                    .filter(DocumentRecord.sha256.in_(incoming_hashes))
                    .first()
                )
                if duplicate_document is not None and duplicate_document.claim_id != claim.claim_id:
                    return True
            return False
        finally:
            session.close()


    def _missing_documents(self, claim: Claim) -> list[DocumentType]:
        policy = self.rule_engine.policy_set.for_category(claim.product.category)
        submitted = {document.document_type for document in claim.submitted_documents}
        missing = list(claim.missing_document_types)
        for group in policy.required_document_groups:
            if not any(document_type in submitted for document_type in group):
                candidate = group[0]
                if candidate not in missing:
                    missing.append(candidate)
        return missing

    @staticmethod
    def _contradiction_flags(rule_results) -> list[str]:
        contradiction_prefixes = (
            "claim_date_not_before_purchase",
            "fault_date_before_submission",
            "document_serial_consistency",
            "document_model_consistency",
            "repair_date_",
        )
        return [
            result.message
            for result in rule_results
            if not result.passed and result.rule_id.startswith(contradiction_prefixes)
        ]
