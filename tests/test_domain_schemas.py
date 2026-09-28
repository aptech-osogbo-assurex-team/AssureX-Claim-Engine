from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from src.domain.enums import ClaimDecision, ClaimStatus, ModelClass
from src.domain.schemas import (
    Claim,
    ClaimSummaryCard,
    DecisionEvidence,
    FinalDecision,
    ModelPrediction,
    Product,
    RuleResult,
    Warranty,
)


@pytest.fixture
def product() -> Product:
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


@pytest.fixture
def warranty() -> Warranty:
    return Warranty(
        warranty_id="WAR-001",
        product_id="PRD-001",
        provider="AssureX Warranty",
        start_date=date(2025, 1, 10),
        end_date=date(2027, 1, 10),
    )


def make_prediction(
    model_name: str = "PythonClassifier",
    predicted_class: ModelClass = ModelClass.VALID_CLAIM,
) -> ModelPrediction:
    probabilities = {
        ModelClass.VALID_CLAIM: 0.90,
        ModelClass.INVALID_CLAIM: 0.05,
        ModelClass.MANUAL_REVIEW: 0.05,
    }
    return ModelPrediction(
        model_name=model_name,
        model_version="1.0.0",
        predicted_class=predicted_class,
        confidence=probabilities[predicted_class],
        probabilities=probabilities,
        timestamp=datetime.now(timezone.utc),
    )


def test_valid_claim_construction(product: Product, warranty: Warranty) -> None:
    claim = Claim(
        claim_id="CLM-000001",
        customer_id="CUS-001",
        product=product,
        warranty=warranty,
        claim_submission_date=date(2026, 1, 15),
        fault_description="Screen does not power on",
        fault_category="Display fault",
        status=ClaimStatus.SUBMITTED,
    )

    assert claim.claim_id == "CLM-000001"
    assert claim.status == ClaimStatus.SUBMITTED
    assert claim.product.serial_number == "SN12345678"
    assert claim.model_dump(mode="json")["status"] == "submitted"


def test_invalid_confidence_rejected() -> None:
    with pytest.raises(ValidationError):
        ModelPrediction(
            model_name="PythonClassifier",
            model_version="1.0.0",
            predicted_class=ModelClass.VALID_CLAIM,
            confidence=1.1,
            probabilities={
                ModelClass.VALID_CLAIM: 0.90,
                ModelClass.INVALID_CLAIM: 0.05,
                ModelClass.MANUAL_REVIEW: 0.05,
            },
            timestamp=datetime.now(timezone.utc),
        )


def test_invalid_probability_sum_rejected() -> None:
    with pytest.raises(ValidationError, match="sum to 1.0"):
        ModelPrediction(
            model_name="PythonClassifier",
            model_version="1.0.0",
            predicted_class=ModelClass.VALID_CLAIM,
            confidence=0.90,
            probabilities={
                ModelClass.VALID_CLAIM: 0.90,
                ModelClass.INVALID_CLAIM: 0.20,
                ModelClass.MANUAL_REVIEW: 0.05,
            },
            timestamp=datetime.now(timezone.utc),
        )


def test_invalid_enum_value_rejected(product: Product, warranty: Warranty) -> None:
    with pytest.raises(ValidationError):
        Claim(
            claim_id="CLM-INVALID",
            customer_id="CUS-INVALID",
            product=product,
            warranty=warranty,
            claim_submission_date=date(2026, 1, 15),
            fault_description="Battery issue",
            fault_category="Battery defect",
            status="not_a_real_status",
        )


def test_claim_relationship_mismatch_rejected(product: Product, warranty: Warranty) -> None:
    mismatch = warranty.model_copy(update={"product_id": "PRD-OTHER"})
    with pytest.raises(ValidationError, match="warranty.product_id"):
        Claim(
            claim_id="CLM-REL-001",
            customer_id="CUS-REL-001",
            product=product,
            warranty=mismatch,
            claim_submission_date=date(2026, 1, 15),
            fault_description="Screen issue",
            fault_category="Display fault",
        )


def test_extra_unexpected_claim_field_rejected(product: Product, warranty: Warranty) -> None:
    with pytest.raises(ValidationError):
        Claim(
            claim_id="CLM-000002",
            customer_id="CUS-002",
            product=product,
            warranty=warranty,
            claim_submission_date=date(2026, 1, 15),
            fault_description="Battery issue",
            fault_category="Battery defect",
            unexpected_field="should fail",
        )


def test_claim_summary_card_contains_no_model_decision_fields() -> None:
    card = ClaimSummaryCard(
        claim_id="CLM-CARD-001",
        card_version="1.0",
        product_age_days=120,
        warranty_status="active",
        remaining_warranty_days=240,
        fault_category="Display fault",
        repair_history_count=1,
        receipt_available=True,
        warranty_card_available=True,
        serial_number_match=True,
        generated_at=datetime.now(timezone.utc),
    )

    payload = card.model_dump(mode="json")
    assert "predicted_class" not in payload
    assert "confidence" not in payload
    assert "decision" not in payload


def test_model_prediction_serialization() -> None:
    prediction = make_prediction()
    dumped = prediction.model_dump(mode="json")

    assert dumped["predicted_class"] == "valid_claim"
    assert dumped["confidence"] == 0.90
    assert set(dumped["probabilities"]) == {
        "valid_claim",
        "invalid_claim",
        "manual_review",
    }


def test_final_decision_serialization(product: Product, warranty: Warranty) -> None:
    python_prediction = make_prediction()
    gtm_prediction = make_prediction(model_name="TeachableMachine")
    evidence = DecisionEvidence(
        python_prediction=python_prediction,
        teachable_machine_prediction=gtm_prediction,
        predicted_classes_match=True,
        confidence_difference=0.0,
        rule_results=[
            RuleResult(
                rule_id="warranty_active",
                passed=True,
                severity="info",
                message="Warranty is active.",
            )
        ],
    )
    decision = FinalDecision(
        claim_id="CLM-000003",
        decision=ClaimDecision.LIKELY_VALID,
        reasons=["Models agree and warranty checks passed."],
        evidence=evidence,
        decided_at=datetime.now(timezone.utc),
    )

    payload = decision.model_dump(mode="json")
    assert payload["decision"] == "likely_valid"
    assert payload["claim_id"] == "CLM-000003"
    assert payload["evidence"]["predicted_classes_match"] is True
