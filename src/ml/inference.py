"""Inference adapter for the trained AssureX Python classifier."""

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd

from src.domain.enums import DocumentType, ModelClass
from src.domain.schemas import Claim, ModelPrediction
from src.rules.policy import PolicySet, load_policy_set

MODEL_FEATURES = [
    "purchase_price",
    "warranty_duration_months",
    "product_age_days",
    "remaining_warranty_days",
    "repair_history_count",
    "missing_document_count",
    "warranty_boundary_proximity",
    "has_partial_documents",
    "category",
    "brand",
    "retailer",
    "fault_type",
    "fault_covered",
    "serial_number_match",
    "claim_date_before_purchase",
    "repair_date_before_purchase",
]

MODEL_REQUIRED_DOCUMENT_GROUPS = [
    (DocumentType.RECEIPT, DocumentType.INVOICE),
    (DocumentType.WARRANTY_CARD,),
    (DocumentType.PRODUCT_PHOTO,),
    (DocumentType.SERIAL_EVIDENCE,),
    (DocumentType.FAULT_EVIDENCE,),
]
MODEL_CLASS_MAP = {
    "Valid Claim": ModelClass.VALID_CLAIM,
    "Invalid Claim": ModelClass.INVALID_CLAIM,
    "Manual Review": ModelClass.MANUAL_REVIEW,
}


class PythonClaimPredictor:
    """Load the saved classifier once and return validated predictions."""

    def __init__(
        self,
        model_path: str | Path = "model/classifier.joblib",
        metadata_path: str | Path = "model/model_metadata.json",
        policy_source: str | Path | PolicySet = "policies/warranty_policies.json",
    ):
        self.model_path = Path(model_path)
        self.metadata = self._load_metadata(Path(metadata_path))
        self.model = joblib.load(self.model_path)
        self.policy_set = policy_source if isinstance(policy_source, PolicySet) else load_policy_set(policy_source)

        missing = [feature for feature in MODEL_FEATURES if feature not in getattr(self.model, "feature_names_in_", MODEL_FEATURES)]
        if missing:
            raise ValueError(f"Loaded model is missing expected feature contract fields: {missing}")

    def predict(self, claim: Claim) -> ModelPrediction:
        features = self.build_features(claim)
        frame = pd.DataFrame([features], columns=MODEL_FEATURES)
        probabilities_raw = self.model.predict_proba(frame)[0]
        predicted_raw = self.model.predict(frame)[0]

        try:
            predicted_class = MODEL_CLASS_MAP[predicted_raw]
        except KeyError as exc:
            raise ValueError(f"Unexpected model class returned by artifact: {predicted_raw!r}") from exc

        probabilities: dict[ModelClass, float] = {}
        for raw_class, probability in zip(self.model.classes_, probabilities_raw):
            try:
                probabilities[MODEL_CLASS_MAP[raw_class]] = float(probability)
            except KeyError as exc:
                raise ValueError(f"Unexpected model probability class: {raw_class!r}") from exc

        return ModelPrediction(
            model_name="PythonClassifier",
            model_version=self.metadata["version"],
            predicted_class=predicted_class,
            confidence=float(max(probabilities_raw)),
            probabilities=probabilities,
            timestamp=datetime.now(timezone.utc),
        )

    def build_features(self, claim: Claim) -> dict[str, object]:
        policy = self.policy_set.for_category(claim.product.category)
        purchase_date = claim.product.purchase_date
        submission_date = claim.claim_submission_date
        remaining_warranty_days = (claim.warranty.end_date - submission_date).days
        missing_document_count = self._missing_document_count(claim)

        fault_covered = (
            not policy.covered_fault_categories
            or claim.fault_category in policy.covered_fault_categories
        )
        serial_match = claim.serial_number_match
        if serial_match is None:
            serial_model_value: object = "unknown"
        else:
            serial_model_value = serial_match

        return {
            "purchase_price": claim.product.purchase_price,
            "warranty_duration_months": claim.product.warranty_duration_months,
            "product_age_days": (submission_date - purchase_date).days,
            "remaining_warranty_days": remaining_warranty_days,
            "repair_history_count": len(claim.previous_repairs),
            "missing_document_count": missing_document_count,
            "warranty_boundary_proximity": abs(remaining_warranty_days),
            "has_partial_documents": int(0 < missing_document_count < len(MODEL_REQUIRED_DOCUMENT_GROUPS)),
            "category": claim.product.category,
            "brand": claim.product.brand,
            "retailer": claim.product.retailer,
            "fault_type": claim.fault_category,
            "fault_covered": fault_covered,
            "serial_number_match": serial_model_value,
            "claim_date_before_purchase": submission_date < purchase_date,
            "repair_date_before_purchase": any(
                repair.repair_date < purchase_date for repair in claim.previous_repairs
            ),
        }

    @staticmethod
    def _missing_document_count(claim: Claim) -> int:
        submitted = {document.document_type for document in claim.submitted_documents}
        return sum(1 for group in MODEL_REQUIRED_DOCUMENT_GROUPS if not any(item in submitted for item in group))

    @staticmethod
    def _load_metadata(path: Path) -> dict[str, str]:
        with path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)
        if "version" not in metadata:
            raise ValueError("Model metadata must define a model version")
        return metadata
