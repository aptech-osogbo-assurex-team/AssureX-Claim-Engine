"""Canonical Pydantic v2 schemas for the AssureX claim lifecycle.

These models define the data contract between OCR, validation, ML inference,
rules, Teachable Machine integration, persistence, review, and audit modules.
They intentionally contain structural validation only; warranty business rules
belong in the rule engine.
"""

from datetime import date, datetime
from math import isclose
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .enums import (
    ClaimDecision,
    ClaimStatus,
    ConsistencyStatus,
    DocumentType,
    ModelClass,
    RepairAuthorization,
    RuleSeverity,
    VerificationStatus,
)


class DomainModel(BaseModel):
    """Shared strict configuration for domain objects."""

    model_config = ConfigDict(extra="forbid")


class Product(DomainModel):
    product_id: str = Field(min_length=1)
    product_name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    brand: str = Field(min_length=1)
    model_number: str = Field(min_length=1)
    serial_number: str = Field(min_length=1)
    purchase_date: date
    purchase_price: float = Field(ge=0)
    retailer: str = Field(min_length=1)
    invoice_number: str | None = None
    warranty_duration_months: int = Field(gt=0)


class Warranty(DomainModel):
    warranty_id: str = Field(min_length=1)
    product_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    start_date: date
    end_date: date
    coverage_conditions: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    service_center: str | None = None
    extended: bool = False
    reporting_deadline_days: int | None = Field(default=None, ge=0)
    grace_period_days: int = Field(default=0, ge=0)
    mandatory_document_types: list[DocumentType] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_date_order(self) -> "Warranty":
        if self.end_date < self.start_date:
            raise ValueError("warranty end_date must not be before start_date")
        return self


class RepairRecord(DomainModel):
    repair_id: str = Field(min_length=1)
    product_id: str = Field(min_length=1)
    repair_date: date
    repair_center: str = Field(min_length=1)
    replaced_parts: list[str] = Field(default_factory=list)
    outcome: str = Field(min_length=1)
    repair_cost: float = Field(default=0, ge=0)
    authorized: RepairAuthorization = RepairAuthorization.UNKNOWN


class Document(DomainModel):
    document_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    document_type: DocumentType
    filename: str = Field(min_length=1)
    mime_type: str = Field(min_length=1)
    size_bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[A-Fa-f0-9]{64}$")
    uploaded_at: datetime
    verification_status: VerificationStatus = VerificationStatus.PENDING
    extracted_data: dict[str, Any] = Field(default_factory=dict)


class ClaimSummaryCard(DomainModel):
    """Data contract for the visual card sent to Teachable Machine.

    This object contains claim evidence only. It intentionally has no model
    predictions, confidence values, or final decision.
    """

    claim_id: str = Field(min_length=1)
    card_version: str = Field(min_length=1)
    product_age_days: int
    warranty_status: str = Field(min_length=1)
    remaining_warranty_days: int | None = None
    fault_category: str = Field(min_length=1)
    repair_history_count: int = Field(ge=0)
    receipt_available: bool
    warranty_card_available: bool
    serial_number_match: bool | None = None
    missing_documents: list[DocumentType] = Field(default_factory=list)
    damage_type: str | None = None
    generated_at: datetime


class Claim(DomainModel):
    claim_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    product: Product
    warranty: Warranty
    fault_occurrence_date: date | None = None
    claim_submission_date: date
    fault_description: str = Field(min_length=1)
    fault_category: str = Field(min_length=1)
    damage_type: str | None = None
    previous_repairs: list[RepairRecord] = Field(default_factory=list)
    previous_replacement: bool = False
    previous_replacement_details: str | None = None
    submitted_documents: list[Document] = Field(default_factory=list)
    missing_document_types: list[DocumentType] = Field(default_factory=list)
    serial_number_match: bool | None = None
    duplicate_claim: bool = False
    status: ClaimStatus = ClaimStatus.DRAFT

    @model_validator(mode="after")
    def validate_relationships(self) -> "Claim":
        if self.warranty.product_id != self.product.product_id:
            raise ValueError("warranty.product_id must match product.product_id")

        for repair in self.previous_repairs:
            if repair.product_id != self.product.product_id:
                raise ValueError("all repair records must reference the claim product")

        for document in self.submitted_documents:
            if document.claim_id != self.claim_id:
                raise ValueError("all submitted documents must reference the claim")

        return self


class ModelPrediction(DomainModel):
    model_name: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    predicted_class: ModelClass
    confidence: float = Field(ge=0.0, le=1.0)
    probabilities: dict[ModelClass, float]
    timestamp: datetime

    @field_validator("probabilities")
    @classmethod
    def validate_probabilities(cls, value: dict[ModelClass, float]) -> dict[ModelClass, float]:
        required = set(ModelClass)
        if set(value) != required:
            raise ValueError("probabilities must contain exactly all three ModelClass values")
        if any(not 0.0 <= probability <= 1.0 for probability in value.values()):
            raise ValueError("probabilities must be between 0.0 and 1.0")
        if not isclose(sum(value.values()), 1.0, abs_tol=1e-6):
            raise ValueError("probabilities must sum to 1.0")
        return value

    @model_validator(mode="after")
    def validate_top_confidence(self) -> "ModelPrediction":
        top_probability = self.probabilities[self.predicted_class]
        if not isclose(self.confidence, top_probability, abs_tol=1e-6):
            raise ValueError("confidence must equal the predicted class probability")
        return self


class RuleResult(DomainModel):
    rule_id: str = Field(min_length=1)
    passed: bool
    severity: RuleSeverity
    message: str = Field(min_length=1)


class DecisionEvidence(DomainModel):
    python_prediction: ModelPrediction
    teachable_machine_prediction: ModelPrediction | None = None
    predicted_classes_match: bool | None = None
    confidence_difference: float | None = Field(default=None, ge=0.0, le=1.0)
    consistency_status: ConsistencyStatus | None = None
    rule_results: list[RuleResult] = Field(default_factory=list)
    contradiction_flags: list[str] = Field(default_factory=list)
    duplicate_flag: bool = False
    missing_document_flags: list[DocumentType] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_model_comparison(self) -> "DecisionEvidence":
        gtm = self.teachable_machine_prediction
        if gtm is None:
            if any(
                value is not None
                for value in (
                    self.predicted_classes_match,
                    self.confidence_difference,
                    self.consistency_status,
                )
            ):
                raise ValueError("model comparison fields require a Teachable Machine prediction")
            return self

        expected_match = self.python_prediction.predicted_class == gtm.predicted_class
        if self.predicted_classes_match != expected_match:
            raise ValueError("predicted_classes_match does not match the two model predictions")

        expected_difference = abs(self.python_prediction.confidence - gtm.confidence)
        if self.confidence_difference is None or not isclose(
            self.confidence_difference, expected_difference, abs_tol=1e-6
        ):
            raise ValueError("confidence_difference must equal the absolute top-confidence difference")

        return self


class FinalDecision(DomainModel):
    claim_id: str = Field(min_length=1)
    decision: ClaimDecision
    reasons: list[str] = Field(min_length=1)
    supporting_factors: list[str] = Field(default_factory=list)
    opposing_factors: list[str] = Field(default_factory=list)
    evidence: DecisionEvidence
    decided_at: datetime
    reviewer_id: str | None = None
    reviewer_comments: str | None = None
    override_applied: bool = False
