"""Final deterministic pre-submission validator for AssureX."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLAIMS = ROOT / "data" / "claims.csv"
REPORTS = ROOT / "reports"
POLICIES = ROOT / "policies"
TM = ROOT / "static" / "teachable_machine"

EXPECTED_SPLIT = {
    ("train", "Valid Claim"): 350,
    ("train", "Invalid Claim"): 350,
    ("train", "Manual Review"): 350,
    ("validation", "Valid Claim"): 75,
    ("validation", "Invalid Claim"): 75,
    ("validation", "Manual Review"): 75,
    ("test", "Valid Claim"): 75,
    ("test", "Invalid Claim"): 75,
    ("test", "Manual Review"): 75,
}


def main() -> None:
    checks: dict[str, str] = {}
    frame = pd.read_csv(CLAIMS)
    if len(frame) != 1500 or frame.claim_id.duplicated().any():
        raise SystemExit("FAIL: claims.csv must contain 1,500 unique claim IDs")
    actual = frame.groupby(["split", "class_label"]).size().to_dict()
    checks["dataset_split"] = "PASS" if actual == EXPECTED_SPLIT else "FAIL"

    card_audit = json.loads((REPORTS / "card_fidelity_audit.json").read_text(encoding="utf-8"))
    checks["card_fidelity"] = "PASS" if card_audit.get("result") == "PASS" else "FAIL"

    mapping = pd.read_csv(REPORTS / "card_mapping.csv")
    checks["card_mapping"] = "PASS" if len(mapping) == 2550 and mapping.claim_id.nunique() == 1500 else "FAIL"

    checks["standalone_policies"] = "PASS" if all(
        (POLICIES / name).exists() for name in ("electronics.json", "home_appliances.json", "default.json")
    ) else "FAIL"

    checks["tm_artifact"] = "PASS" if all(
        (TM / name).exists() for name in ("model.json", "metadata.json")
    ) else "PENDING"

    compare = REPORTS / "model_comparison_30.csv"
    if compare.exists():
        comparison = pd.read_csv(compare)
        required_columns = {
            "claim_id",
            "actual_class",
            "python_predicted_class",
            "python_valid_confidence",
            "python_invalid_confidence",
            "python_manual_review_confidence",
            "claim_summary_card_filename",
            "tm_predicted_class",
            "tm_valid_confidence",
            "tm_invalid_confidence",
            "tm_manual_review_confidence",
            "predicted_class_match",
            "top_class_confidence_difference",
            "model_consistency_status",
            "warranty_rule_result",
            "missing_documents",
            "contradictions_detected",
            "duplicate_indicator",
            "final_application_decision",
            "disagreement_explanation",
        }
        required_non_null = required_columns - {
            "missing_documents",
            "contradictions_detected",
        }
        has_required_columns = required_columns.issubset(comparison.columns)
        has_required_values = (
            not comparison[list(required_non_null)].isna().any().any()
            if has_required_columns
            else False
        )
        checks["comparison_30"] = (
            "PASS"
            if len(comparison) >= 30
            and has_required_columns
            and has_required_values
            else "FAIL"
        )
    else:
        checks["comparison_30"] = "PENDING"

    output = {"checks": checks, "overall": "PASS" if all(v == "PASS" for v in checks.values()) else "PENDING"}
    print(json.dumps(output, indent=2))
    if any(v == "FAIL" for v in checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
