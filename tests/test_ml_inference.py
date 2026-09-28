from datetime import date

from src.domain.enums import ModelClass
from src.domain.schemas import Claim, Product, Warranty
from src.ml.inference import PythonClaimPredictor


MODEL = "model/classifier.joblib"
METADATA = "model/model_metadata.json"
POLICY = "policies/warranty_policies.json"


def make_claim() -> Claim:
    product = Product(
        product_id="PRD-ML-001",
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
    warranty = Warranty(
        warranty_id="WAR-ML-001",
        product_id=product.product_id,
        provider="AssureX Warranty",
        start_date=product.purchase_date,
        end_date=date(2027, 1, 10),
    )
    return Claim(
        claim_id="CLM-ML-001",
        customer_id="CUS-001",
        product=product,
        warranty=warranty,
        claim_submission_date=date(2026, 1, 10),
        fault_description="Display stopped working",
        fault_category="Display fault",
        serial_number_match=True,
    )


def test_predictor_builds_the_frozen_feature_contract() -> None:
    predictor = PythonClaimPredictor(MODEL, METADATA, POLICY)
    features = predictor.build_features(make_claim())

    assert set(features) == set(predictor.model.feature_names_in_)
    assert features["product_age_days"] == 365
    assert features["repair_history_count"] == 0
    assert features["serial_number_match"] is True


def test_saved_model_returns_validated_prediction() -> None:
    predictor = PythonClaimPredictor(MODEL, METADATA, POLICY)
    result = predictor.predict(make_claim())

    assert result.model_name == "PythonClassifier"
    assert result.model_version == "1.0.0"
    assert result.predicted_class in set(ModelClass)
    assert 0.0 <= result.confidence <= 1.0
    assert set(result.probabilities) == set(ModelClass)
    assert abs(sum(result.probabilities.values()) - 1.0) < 1e-6
