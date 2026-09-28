from datetime import datetime, timezone

import pytest

from src.decision.engine import DecisionEngine
from src.domain.enums import ClaimDecision, ConsistencyStatus, ModelClass, RuleSeverity
from src.domain.schemas import ModelPrediction, RuleResult

POLICY = "policies/consistency_policy.json"


def prediction(name: str, cls: ModelClass, conf: float) -> ModelPrediction:
    remaining = round(1.0 - conf, 6)
    other = round(remaining / 2, 6)
    probabilities = {
        ModelClass.VALID_CLAIM: other,
        ModelClass.INVALID_CLAIM: other,
        ModelClass.MANUAL_REVIEW: remaining - other,
    }
    probabilities[cls] = conf
    total = sum(probabilities.values())
    # absorb rounding residue in the lowest non-top class
    if abs(total - 1.0) > 1e-9:
        for key in probabilities:
            if key != cls:
                probabilities[key] += 1.0 - total
                break
    return ModelPrediction(
        model_name=name,
        model_version="1.0.0",
        predicted_class=cls,
        confidence=conf,
        probabilities=probabilities,
        timestamp=datetime.now(timezone.utc),
    )


def pass_rule() -> RuleResult:
    return RuleResult(
        rule_id="warranty_active",
        passed=True,
        severity=RuleSeverity.CRITICAL,
        message="Warranty is active.",
    )


def fail_rule(severity=RuleSeverity.CRITICAL) -> RuleResult:
    return RuleResult(
        rule_id="serial_number_match",
        passed=False,
        severity=severity,
        message="Serial number mismatch.",
    )


def test_strong_model_match() -> None:
    engine = DecisionEngine(POLICY)
    py = prediction("Python", ModelClass.VALID_CLAIM, 0.90)
    tm = prediction("TeachableMachine", ModelClass.VALID_CLAIM, 0.88)
    match, diff, status = engine.compare_models(py, tm)

    assert match is True
    assert diff == pytest.approx(0.02)
    assert status == ConsistencyStatus.STRONG_MATCH


def test_model_disagreement_requires_review() -> None:
    engine = DecisionEngine(POLICY)
    result = engine.decide(
        "CLM-001",
        prediction("Python", ModelClass.VALID_CLAIM, 0.90),
        prediction("TeachableMachine", ModelClass.INVALID_CLAIM, 0.87),
        [pass_rule()],
    )
    assert result.decision == ClaimDecision.MANUAL_REVIEW_REQUIRED
    assert result.evidence.consistency_status == ConsistencyStatus.MODEL_DISAGREEMENT


def test_weak_same_class_requires_review() -> None:
    engine = DecisionEngine(POLICY)
    result = engine.decide(
        "CLM-002",
        prediction("Python", ModelClass.VALID_CLAIM, 0.91),
        prediction("TeachableMachine", ModelClass.VALID_CLAIM, 0.60),
        [pass_rule()],
    )
    assert result.evidence.consistency_status == ConsistencyStatus.WEAK_MATCH
    assert result.decision == ClaimDecision.MANUAL_REVIEW_REQUIRED


def test_rule_failure_requires_review() -> None:
    engine = DecisionEngine(POLICY)
    result = engine.decide(
        "CLM-003",
        prediction("Python", ModelClass.VALID_CLAIM, 0.90),
        prediction("TeachableMachine", ModelClass.VALID_CLAIM, 0.89),
        [pass_rule(), fail_rule()],
    )
    assert result.decision == ClaimDecision.MANUAL_REVIEW_REQUIRED
    assert "serial_number_match" in result.reasons[0]


def test_agreement_without_failures_can_be_likely_valid() -> None:
    engine = DecisionEngine(POLICY)
    result = engine.decide(
        "CLM-004",
        prediction("Python", ModelClass.VALID_CLAIM, 0.90),
        prediction("TeachableMachine", ModelClass.VALID_CLAIM, 0.91),
        [pass_rule()],
    )
    assert result.decision == ClaimDecision.LIKELY_VALID


def test_agreement_invalid_without_failures_can_be_likely_invalid() -> None:
    engine = DecisionEngine(POLICY)
    result = engine.decide(
        "CLM-005",
        prediction("Python", ModelClass.INVALID_CLAIM, 0.90),
        prediction("TeachableMachine", ModelClass.INVALID_CLAIM, 0.92),
        [pass_rule()],
    )
    assert result.decision == ClaimDecision.LIKELY_INVALID


def test_duplicate_and_missing_documents_require_review() -> None:
    from src.domain.enums import DocumentType

    engine = DecisionEngine(POLICY)
    result = engine.decide(
        "CLM-006",
        prediction("Python", ModelClass.VALID_CLAIM, 0.90),
        prediction("TeachableMachine", ModelClass.VALID_CLAIM, 0.91),
        [pass_rule()],
        duplicate_flag=True,
        missing_document_flags=[DocumentType.WARRANTY_CARD],
    )
    assert result.decision == ClaimDecision.MANUAL_REVIEW_REQUIRED
    assert result.evidence.duplicate_flag is True
    assert result.evidence.missing_document_flags == [DocumentType.WARRANTY_CARD]
