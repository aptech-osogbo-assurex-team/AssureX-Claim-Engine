"""Canonical domain models for the AssureX Claim Engine."""

from .enums import (
    ClaimDecision,
    ClaimStatus,
    ConsistencyStatus,
    DocumentType,
    ModelClass,
    RepairAuthorization,
    RuleSeverity,
    VerificationStatus,
    UserRole,
)
from .schemas import (
    Claim,
    ClaimSummaryCard,
    DecisionEvidence,
    Document,
    FinalDecision,
    ModelPrediction,
    Product,
    RepairRecord,
    RuleResult,
    Warranty,
)

__all__ = [
    "Claim",
    "ClaimSummaryCard",
    "ClaimDecision",
    "ClaimStatus",
    "ConsistencyStatus",
    "DecisionEvidence",
    "Document",
    "DocumentType",
    "FinalDecision",
    "ModelClass",
    "ModelPrediction",
    "Product",
    "RepairAuthorization",
    "RuleSeverity",
    "RepairRecord",
    "RuleResult",
    "VerificationStatus",
    "UserRole",
    "Warranty",
]
