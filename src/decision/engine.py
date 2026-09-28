"""Deterministic final claim adjudication built on independent evidence."""

from datetime import datetime, timezone
from pathlib import Path

from src.domain.enums import ClaimDecision, ConsistencyStatus, ModelClass, RuleSeverity
from src.domain.schemas import DecisionEvidence, FinalDecision, ModelPrediction, RuleResult

from .policy import ConsistencyPolicy, load_consistency_policy


class DecisionEngine:
    """Compare both models and combine their evidence with business rules.

    The engine is intentionally deterministic and explainable. It does not
    invent confidence values and does not train or modify either model.
    """

    def __init__(self, policy_source: str | Path | ConsistencyPolicy):
        self.policy = (
            policy_source
            if isinstance(policy_source, ConsistencyPolicy)
            else load_consistency_policy(policy_source)
        )

    def compare_models(
        self,
        python_prediction: ModelPrediction,
        teachable_machine_prediction: ModelPrediction,
    ) -> tuple[bool, float, ConsistencyStatus]:
        python_conf = python_prediction.confidence
        tm_conf = teachable_machine_prediction.confidence
        difference = abs(python_conf - tm_conf)

        if min(python_conf, tm_conf) < self.policy.min_confidence:
            status = ConsistencyStatus.UNCERTAIN_RESULT
        elif python_prediction.predicted_class != teachable_machine_prediction.predicted_class:
            status = ConsistencyStatus.MODEL_DISAGREEMENT
        elif difference <= self.policy.confidence_diff_tight_band:
            status = ConsistencyStatus.STRONG_MATCH
        elif difference <= self.policy.confidence_diff_wide_band:
            status = ConsistencyStatus.ACCEPTABLE_MATCH
        else:
            status = ConsistencyStatus.WEAK_MATCH

        return (
            python_prediction.predicted_class == teachable_machine_prediction.predicted_class,
            difference,
            status,
        )

    def decide(
        self,
        claim_id: str,
        python_prediction: ModelPrediction,
        teachable_machine_prediction: ModelPrediction,
        rule_results: list[RuleResult],
        *,
        contradiction_flags: list[str] | None = None,
        missing_document_flags=None,
        duplicate_flag: bool = False,
        reviewer_id: str | None = None,
    ) -> FinalDecision:
        predicted_match, confidence_difference, consistency_status = self.compare_models(
            python_prediction, teachable_machine_prediction
        )

        contradictions = list(contradiction_flags or [])
        missing_documents = list(missing_document_flags or [])
        failed_rules = [rule for rule in rule_results if not rule.passed]
        critical_failures = [rule for rule in failed_rules if rule.severity == RuleSeverity.CRITICAL]
        warning_failures = [rule for rule in failed_rules if rule.severity == RuleSeverity.WARNING]

        evidence = DecisionEvidence(
            python_prediction=python_prediction,
            teachable_machine_prediction=teachable_machine_prediction,
            predicted_classes_match=predicted_match,
            confidence_difference=confidence_difference,
            consistency_status=consistency_status,
            rule_results=rule_results,
            contradiction_flags=contradictions,
            duplicate_flag=duplicate_flag,
            missing_document_flags=missing_documents,
        )

        escalation_reasons: list[str] = []
        supporting: list[str] = []
        opposing: list[str] = []

        if consistency_status in {
            ConsistencyStatus.UNCERTAIN_RESULT,
            ConsistencyStatus.MODEL_DISAGREEMENT,
            ConsistencyStatus.WEAK_MATCH,
        }:
            escalation_reasons.append(f"Model consistency status is {consistency_status.value}.")
        elif consistency_status in {ConsistencyStatus.STRONG_MATCH, ConsistencyStatus.ACCEPTABLE_MATCH}:
            supporting.append(f"Both models produced a {consistency_status.value} comparison.")

        if python_prediction.predicted_class == ModelClass.VALID_CLAIM:
            supporting.append(f"Python model predicts Valid Claim at {python_prediction.confidence:.1%}.")
        elif python_prediction.predicted_class == ModelClass.INVALID_CLAIM:
            opposing.append(f"Python model predicts Invalid Claim at {python_prediction.confidence:.1%}.")
        else:
            escalation_reasons.append("Python model predicts Manual Review.")

        if teachable_machine_prediction.predicted_class == ModelClass.VALID_CLAIM:
            supporting.append(
                f"Teachable Machine predicts Valid Claim at {teachable_machine_prediction.confidence:.1%}."
            )
        elif teachable_machine_prediction.predicted_class == ModelClass.INVALID_CLAIM:
            opposing.append(
                f"Teachable Machine predicts Invalid Claim at {teachable_machine_prediction.confidence:.1%}."
            )
        else:
            escalation_reasons.append("Teachable Machine predicts Manual Review.")

        if critical_failures:
            escalation_reasons.append(
                "Critical warranty/integrity rule failures: "
                + ", ".join(rule.rule_id for rule in critical_failures)
                + "."
            )
            opposing.extend(rule.message for rule in critical_failures)
        if warning_failures:
            escalation_reasons.append(
                "Warning-level evidence gaps: "
                + ", ".join(rule.rule_id for rule in warning_failures)
                + "."
            )
            opposing.extend(rule.message for rule in warning_failures)
        if contradictions:
            escalation_reasons.append("Contradictory claim evidence was detected.")
            opposing.extend(contradictions)
        if missing_documents:
            escalation_reasons.append("Required claim documents are missing.")
            opposing.extend(f"Missing document: {item.value}" for item in missing_documents)
        if duplicate_flag:
            escalation_reasons.append("A possible duplicate claim has been detected.")
            opposing.append("Duplicate-claim indicator is active.")

        must_review = bool(escalation_reasons)
        if must_review:
            decision = ClaimDecision.MANUAL_REVIEW_REQUIRED
            reasons = escalation_reasons
        elif python_prediction.predicted_class == ModelClass.VALID_CLAIM:
            decision = ClaimDecision.LIKELY_VALID
            reasons = ["Both independent model results agree and no configured rule failed."]
        elif python_prediction.predicted_class == ModelClass.INVALID_CLAIM:
            decision = ClaimDecision.LIKELY_INVALID
            reasons = ["Both independent model results agree and no configured rule failed."]
        else:
            decision = ClaimDecision.MANUAL_REVIEW_REQUIRED
            reasons = ["At least one model returned Manual Review."]

        return FinalDecision(
            claim_id=claim_id,
            decision=decision,
            reasons=reasons,
            supporting_factors=supporting,
            opposing_factors=opposing,
            evidence=evidence,
            decided_at=datetime.now(timezone.utc),
            reviewer_id=reviewer_id,
        )
