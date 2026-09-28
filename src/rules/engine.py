"""Deterministic, configurable warranty-rule evaluation."""

from datetime import date
from pathlib import Path
from typing import Iterable

from src.domain.enums import DocumentType, RepairAuthorization, RuleSeverity
from src.domain.schemas import Claim, Document, RepairRecord, RuleResult

from .policy import PolicySet, load_policy_set


class RuleEngine:
    """Evaluate claim facts against the configured warranty policy.

    The engine reports evidence only. It does not decide Valid/Invalid/Manual
    Review; final adjudication belongs to the decision engine.
    """

    def __init__(self, policy_source: str | Path | PolicySet):
        self.policy_set = (
            policy_source
            if isinstance(policy_source, PolicySet)
            else load_policy_set(policy_source)
        )

    def evaluate(self, claim: Claim) -> list[RuleResult]:
        policy = self.policy_set.for_category(claim.product.category)
        results: list[RuleResult] = []
        results.extend(self._warranty_rules(claim, policy.reporting_deadline_days, policy.grace_period_days))
        results.extend(self._evidence_rules(claim, policy.required_document_groups, policy.conditional_document_groups))
        results.extend(self._fault_rules(claim, policy.covered_fault_categories, policy.excluded_damage_types))
        results.extend(self._integrity_rules(claim))
        results.extend(self._repair_rules(claim, policy.reject_unauthorized_repairs, policy.reject_previous_replacement))
        results.append(
            self._result(
                "duplicate_claim",
                not claim.duplicate_claim,
                RuleSeverity.CRITICAL,
                "No duplicate claim indicator is present."
                if not claim.duplicate_claim
                else "A possible duplicate claim has been flagged.",
            )
        )
        return results

    @staticmethod
    def _result(rule_id: str, passed: bool, severity: RuleSeverity, message: str) -> RuleResult:
        return RuleResult(rule_id=rule_id, passed=passed, severity=severity, message=message)

    def _warranty_rules(self, claim: Claim, reporting_deadline_days: int, grace_period_days: int) -> list[RuleResult]:
        submission = claim.claim_submission_date
        start = claim.warranty.start_date
        effective_end = claim.warranty.end_date
        policy_grace = max(claim.warranty.grace_period_days, grace_period_days)
        if policy_grace:
            from datetime import timedelta

            effective_end = effective_end + timedelta(days=policy_grace)

        active = start <= submission <= effective_end
        results = [
            self._result(
                "warranty_active",
                active,
                RuleSeverity.CRITICAL,
                "Claim submission falls within the configured warranty period."
                if active
                else "Claim submission falls outside the configured warranty period.",
            )
        ]

        product_age_days = (submission - claim.product.purchase_date).days
        results.append(
            self._result(
                "product_age_non_negative",
                product_age_days >= 0,
                RuleSeverity.CRITICAL,
                "Product age at submission is non-negative."
                if product_age_days >= 0
                else "Claim was submitted before the product purchase date.",
            )
        )

        if claim.fault_occurrence_date is None:
            results.append(
                self._result(
                    "reporting_deadline",
                    False,
                    RuleSeverity.WARNING,
                    "Fault occurrence date is unavailable, so the reporting deadline cannot be verified.",
                )
            )
        else:
            elapsed = (submission - claim.fault_occurrence_date).days
            within_deadline = elapsed >= 0 and elapsed <= reporting_deadline_days
            results.append(
                self._result(
                    "reporting_deadline",
                    within_deadline,
                    RuleSeverity.CRITICAL,
                    f"Claim was submitted {elapsed} day(s) after the reported fault."
                    if within_deadline
                    else f"Claim reporting interval of {elapsed} day(s) exceeds the policy limit of {reporting_deadline_days} day(s) or is negative.",
                )
            )
        return results

    def _evidence_rules(
        self,
        claim: Claim,
        required_groups: list[list[DocumentType]],
        conditional_groups: dict[str, list[list[DocumentType]]],
    ) -> list[RuleResult]:
        docs = {doc.document_type for doc in claim.submitted_documents}
        results: list[RuleResult] = []

        for index, group in enumerate(required_groups, start=1):
            satisfied = any(doc_type in docs for doc_type in group)
            label = self._document_group_label(group)
            results.append(
                self._result(
                    f"required_documents_{index}",
                    satisfied,
                    RuleSeverity.WARNING,
                    f"Required document group satisfied: {label}."
                    if satisfied
                    else f"Missing required document group: {label}.",
                )
            )

        for condition, groups in conditional_groups.items():
            active = self._conditional_requirement_active(condition, claim)
            if not active:
                continue
            for index, group in enumerate(groups, start=1):
                satisfied = any(doc_type in docs for doc_type in group)
                label = self._document_group_label(group)
                results.append(
                    self._result(
                        f"conditional_documents_{condition}_{index}",
                        satisfied,
                        RuleSeverity.WARNING,
                        f"Conditional document group satisfied: {label}."
                        if satisfied
                        else f"Missing conditional document group: {label}.",
                    )
                )

        # The claim can carry upstream-prepared missing-document flags. The
        # rule engine keeps them visible, while also computing document gaps.
        if claim.missing_document_types:
            results.append(
                self._result(
                    "declared_missing_documents",
                    False,
                    RuleSeverity.WARNING,
                    "The claim contains declared missing-document flags: "
                    + ", ".join(sorted(item.value for item in claim.missing_document_types)),
                )
            )
        else:
            results.append(
                self._result(
                    "declared_missing_documents",
                    True,
                    RuleSeverity.INFO,
                    "No upstream missing-document flags were supplied.",
                )
            )
        return results

    def _fault_rules(
        self,
        claim: Claim,
        covered_fault_categories: list[str],
        excluded_damage_types: list[str],
    ) -> list[RuleResult]:
        fault_covered = not covered_fault_categories or claim.fault_category in covered_fault_categories
        results = [
            self._result(
                "fault_covered",
                fault_covered,
                RuleSeverity.CRITICAL,
                "Fault category is covered by policy."
                if fault_covered
                else f"Fault category '{claim.fault_category}' is outside the policy coverage.",
            )
        ]
        if claim.damage_type:
            excluded = claim.damage_type.strip().casefold() in {
                value.strip().casefold() for value in excluded_damage_types
            }
            results.append(
                self._result(
                    "excluded_damage",
                    not excluded,
                    RuleSeverity.CRITICAL,
                    "Reported damage type is not excluded by policy."
                    if not excluded
                    else f"Reported damage type '{claim.damage_type}' is excluded by policy.",
                )
            )
        else:
            results.append(
                self._result(
                    "excluded_damage",
                    True,
                    RuleSeverity.INFO,
                    "No damage type was supplied.",
                )
            )
        return results

    def _integrity_rules(self, claim: Claim) -> list[RuleResult]:
        purchase = claim.product.purchase_date
        submission = claim.claim_submission_date
        results = [
            self._result(
                "serial_number_match",
                claim.serial_number_match is not False,
                RuleSeverity.CRITICAL,
                "Serial-number evidence matches or has not yet been marked as mismatched."
                if claim.serial_number_match is not False
                else "Serial-number evidence does not match the registered product.",
            )
        ]

        if claim.fault_occurrence_date is None:
            results.append(
                self._result(
                    "fault_date_before_submission",
                    True,
                    RuleSeverity.INFO,
                    "Fault occurrence date was not supplied.",
                )
            )
        else:
            valid = purchase <= claim.fault_occurrence_date <= submission
            results.append(
                self._result(
                    "fault_date_before_submission",
                    valid,
                    RuleSeverity.CRITICAL,
                    "Fault occurrence date falls between purchase and claim submission."
                    if valid
                    else "Fault occurrence date contradicts the purchase or submission date.",
                )
            )

        extracted_serials = self._extracted_values(claim.submitted_documents, "serial_number")
        if extracted_serials:
            matches = all(self._normalize(value) == self._normalize(claim.product.serial_number) for value in extracted_serials)
            results.append(
                self._result(
                    "document_serial_consistency",
                    matches,
                    RuleSeverity.CRITICAL,
                    "Serial numbers extracted from documents are consistent with the registered product."
                    if matches
                    else "At least one document contains a conflicting serial number.",
                )
            )
        else:
            results.append(
                self._result(
                    "document_serial_consistency",
                    True,
                    RuleSeverity.INFO,
                    "No extracted serial-number values were available for comparison.",
                )
            )

        extracted_models = self._extracted_values(claim.submitted_documents, "model_number")
        if extracted_models:
            matches = all(self._normalize(value) == self._normalize(claim.product.model_number) for value in extracted_models)
            results.append(
                self._result(
                    "document_model_consistency",
                    matches,
                    RuleSeverity.CRITICAL,
                    "Model numbers extracted from documents are consistent with the registered product."
                    if matches
                    else "At least one document contains a conflicting model number.",
                )
            )
        else:
            results.append(
                self._result(
                    "document_model_consistency",
                    True,
                    RuleSeverity.INFO,
                    "No extracted model-number values were available for comparison.",
                )
            )

        results.append(
            self._result(
                "claim_date_not_before_purchase",
                submission >= purchase,
                RuleSeverity.CRITICAL,
                "Claim submission date is not before the purchase date."
                if submission >= purchase
                else "Claim submission date is before the purchase date.",
            )
        )

        for repair in claim.previous_repairs:
            results.append(self._repair_date_result(repair, purchase))
        return results

    def _repair_rules(
        self,
        claim: Claim,
        reject_unauthorized: bool,
        reject_previous_replacement: bool,
    ) -> list[RuleResult]:
        results: list[RuleResult] = []
        if reject_unauthorized:
            unauthorized = [r.repair_id for r in claim.previous_repairs if r.authorized == RepairAuthorization.UNAUTHORIZED]
            results.append(
                self._result(
                    "authorized_repairs",
                    not unauthorized,
                    RuleSeverity.CRITICAL,
                    "All recorded repairs were completed by authorized service centers."
                    if not unauthorized
                    else "Unauthorized repairs detected: " + ", ".join(unauthorized),
                )
            )
        else:
            results.append(
                self._result(
                    "authorized_repairs",
                    True,
                    RuleSeverity.INFO,
                    "Unauthorized-repair rejection is disabled by policy.",
                )
            )

        if reject_previous_replacement:
            results.append(
                self._result(
                    "previous_replacement",
                    not claim.previous_replacement,
                    RuleSeverity.CRITICAL,
                    "No previous product replacement is recorded."
                    if not claim.previous_replacement
                    else "A previous product replacement is recorded.",
                )
            )
        else:
            results.append(
                self._result(
                    "previous_replacement",
                    True,
                    RuleSeverity.INFO,
                    "Previous replacement does not block claims under the configured policy.",
                )
            )
        return results

    @staticmethod
    def _repair_date_result(repair: RepairRecord, purchase_date: date) -> RuleResult:
        valid = repair.repair_date >= purchase_date
        return RuleEngine._result(
            f"repair_date_{repair.repair_id}",
            valid,
            RuleSeverity.CRITICAL,
            f"Repair {repair.repair_id} occurred on or after purchase."
            if valid
            else f"Repair {repair.repair_id} is dated before the product purchase.",
        )

    @staticmethod
    def _conditional_requirement_active(condition: str, claim: Claim) -> bool:
        if condition == "previous_repairs":
            return bool(claim.previous_repairs)
        if condition == "previous_replacement":
            return claim.previous_replacement
        return False

    @staticmethod
    def _document_group_label(group: Iterable[DocumentType]) -> str:
        return " or ".join(item.value for item in group)

    @staticmethod
    def _extracted_values(documents: Iterable[Document], key: str) -> list[str]:
        values: list[str] = []
        for document in documents:
            value = document.extracted_data.get(key)
            if value not in (None, ""):
                values.append(str(value))
        return values

    @staticmethod
    def _normalize(value: str) -> str:
        return "".join(value.casefold().split())
