"""Stable, machine-readable enumerations used by AssureX domain objects."""

from enum import StrEnum


class ClaimStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_EVALUATION = "under_evaluation"
    ADDITIONAL_INFORMATION_REQUIRED = "additional_information_required"
    MANUAL_REVIEW = "manual_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CLOSED = "closed"


class ClaimDecision(StrEnum):
    LIKELY_VALID = "likely_valid"
    LIKELY_INVALID = "likely_invalid"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"


class ModelClass(StrEnum):
    VALID_CLAIM = "valid_claim"
    INVALID_CLAIM = "invalid_claim"
    MANUAL_REVIEW = "manual_review"


class DocumentType(StrEnum):
    RECEIPT = "receipt"
    INVOICE = "invoice"
    WARRANTY_CARD = "warranty_card"
    PRODUCT_PHOTO = "product_photo"
    SERIAL_EVIDENCE = "serial_evidence"
    FAULT_EVIDENCE = "fault_evidence"
    FAULT_VIDEO = "fault_video"
    REPAIR_REPORT = "repair_report"
    DIAGNOSTIC_REPORT = "diagnostic_report"
    REPLACEMENT_EVIDENCE = "replacement_evidence"
    OTHER = "other"


class VerificationStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class RepairAuthorization(StrEnum):
    AUTHORIZED = "authorized"
    UNAUTHORIZED = "unauthorized"
    UNKNOWN = "unknown"


class UserRole(StrEnum):
    CUSTOMER = "customer"
    REVIEWER = "reviewer"
    ADMIN = "admin"


class RuleSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class ConsistencyStatus(StrEnum):
    STRONG_MATCH = "strong_match"
    ACCEPTABLE_MATCH = "acceptable_match"
    WEAK_MATCH = "weak_match"
    MODEL_DISAGREEMENT = "model_disagreement"
    UNCERTAIN_RESULT = "uncertain_result"
