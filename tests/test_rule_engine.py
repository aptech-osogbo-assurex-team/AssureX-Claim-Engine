from datetime import date, datetime, timezone

from src.domain.enums import DocumentType, RepairAuthorization, RuleSeverity
from src.domain.schemas import Claim, Document, Product, RepairRecord, Warranty
from src.rules.engine import RuleEngine


POLICY = "policies/warranty_policies.json"


def make_product() -> Product:
    return Product(
        product_id="PRD-001",
        product_name="Laptop",
        category="Electronics",
        brand="Vertex",
        model_number="VT-15Pro",
        serial_number="SN12345678",
        purchase_date=date(2025, 1, 10),
        purchase_price=900.0,
        retailer="TechHub Store",
        invoice_number="INV-001",
        warranty_duration_months=24,
    )


def make_warranty() -> Warranty:
    return Warranty(
        warranty_id="WAR-001",
        product_id="PRD-001",
        provider="AssureX Warranty",
        start_date=date(2025, 1, 10),
        end_date=date(2027, 1, 10),
    )


def make_document(document_id: str, document_type: DocumentType, **extracted: str) -> Document:
    return Document(
        document_id=document_id,
        claim_id="CLM-001",
        document_type=document_type,
        filename=f"{document_id}.pdf",
        mime_type="application/pdf",
        size_bytes=1024,
        sha256="a" * 64,
        uploaded_at=datetime.now(timezone.utc),
        extracted_data=extracted,
    )


def make_claim(**overrides) -> Claim:
    data = dict(
        claim_id="CLM-001",
        customer_id="CUS-001",
        product=make_product(),
        warranty=make_warranty(),
        fault_occurrence_date=date(2025, 6, 1),
        claim_submission_date=date(2025, 6, 15),
        fault_description="Screen does not power on",
        fault_category="Display fault",
        submitted_documents=[
            make_document("D1", DocumentType.RECEIPT, serial_number="SN12345678", model_number="VT-15Pro"),
            make_document("D2", DocumentType.WARRANTY_CARD, serial_number="SN12345678"),
            make_document("D3", DocumentType.PRODUCT_PHOTO),
            make_document("D4", DocumentType.SERIAL_EVIDENCE, serial_number="SN12345678"),
            make_document("D5", DocumentType.FAULT_EVIDENCE),
        ],
    )
    data.update(overrides)
    return Claim(**data)


def by_id(results):
    return {result.rule_id: result for result in results}


def test_valid_claim_rules_pass() -> None:
    results = by_id(RuleEngine(POLICY).evaluate(make_claim()))

    assert results["warranty_active"].passed
    assert results["reporting_deadline"].passed
    assert results["fault_covered"].passed
    assert results["serial_number_match"].passed
    assert results["duplicate_claim"].passed
    assert results["warranty_active"].severity == RuleSeverity.CRITICAL


def test_expired_warranty_fails() -> None:
    claim = make_claim(claim_submission_date=date(2028, 1, 20))
    results = by_id(RuleEngine(POLICY).evaluate(claim))
    assert not results["warranty_active"].passed


def test_excluded_damage_fails() -> None:
    claim = make_claim(damage_type="Water damage")
    results = by_id(RuleEngine(POLICY).evaluate(claim))
    assert not results["excluded_damage"].passed


def test_serial_mismatch_fails() -> None:
    claim = make_claim(serial_number_match=False)
    results = by_id(RuleEngine(POLICY).evaluate(claim))
    assert not results["serial_number_match"].passed


def test_missing_required_document_is_detected() -> None:
    claim = make_claim(
        submitted_documents=[
            make_document("D1", DocumentType.RECEIPT),
            make_document("D2", DocumentType.WARRANTY_CARD),
            make_document("D3", DocumentType.PRODUCT_PHOTO),
            make_document("D4", DocumentType.SERIAL_EVIDENCE),
        ]
    )
    results = by_id(RuleEngine(POLICY).evaluate(claim))
    fault_group = results["required_documents_5"]
    assert not fault_group.passed
    assert fault_group.severity == RuleSeverity.WARNING


def test_duplicate_claim_fails() -> None:
    claim = make_claim(duplicate_claim=True)
    results = by_id(RuleEngine(POLICY).evaluate(claim))
    assert not results["duplicate_claim"].passed


def test_contradiction_is_detected_from_document_serial() -> None:
    claim = make_claim(
        submitted_documents=[
            make_document("D1", DocumentType.RECEIPT, serial_number="SN99999999"),
            make_document("D2", DocumentType.WARRANTY_CARD, serial_number="SN12345678"),
            make_document("D3", DocumentType.PRODUCT_PHOTO),
            make_document("D4", DocumentType.SERIAL_EVIDENCE, serial_number="SN12345678"),
            make_document("D5", DocumentType.FAULT_EVIDENCE),
        ]
    )
    results = by_id(RuleEngine(POLICY).evaluate(claim))
    assert not results["document_serial_consistency"].passed


def test_unauthorized_repair_and_repair_date_are_detected() -> None:
    repair = RepairRecord(
        repair_id="REP-001",
        product_id="PRD-001",
        repair_date=date(2025, 3, 1),
        repair_center="Unapproved Center",
        outcome="Repaired",
        authorized=RepairAuthorization.UNAUTHORIZED,
    )
    claim = make_claim(previous_repairs=[repair])
    results = by_id(RuleEngine(POLICY).evaluate(claim))

    assert not results["authorized_repairs"].passed
    assert results["repair_date_REP-001"].passed
    assert not results["conditional_documents_previous_repairs_1"].passed
