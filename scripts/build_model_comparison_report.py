"""Merge real Teachable Machine predictions with Python/rules evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from src.cards.dataset import row_to_claim
from src.decision.engine import DecisionEngine
from src.domain.enums import ModelClass
from src.domain.schemas import ModelPrediction
from src.ml.inference import PythonClaimPredictor
from src.rules.engine import RuleEngine
from datetime import datetime, timezone

LABELS = ["Valid Claim", "Invalid Claim", "Manual Review"]
LABEL_TO_ENUM = {
    "valid_claim": ModelClass.VALID_CLAIM,
    "invalid_claim": ModelClass.INVALID_CLAIM,
    "manual_review": ModelClass.MANUAL_REVIEW,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tm-results", required=True)
    parser.add_argument("--claims", default="data/claims.csv")
    parser.add_argument("--output", default="reports/model_comparison_30.csv")
    parser.add_argument("--limit", type=int, default=30)
    args = parser.parse_args()

    tm = pd.read_csv(args.tm_results)
    required = {
        "claim_id", "actual_class", "tm_predicted_class", "tm_valid_confidence",
        "tm_invalid_confidence", "tm_manual_review_confidence"
    }
    missing = required - set(tm.columns)
    if missing:
        raise ValueError(f"TM results missing columns: {sorted(missing)}")

    claims = pd.read_csv(args.claims)
    claims = claims[claims["split"] == "test"].copy()
    merged = tm.merge(claims, on="claim_id", how="left", suffixes=("", "_csv"))
    if merged["product_name"].isna().any():
        raise ValueError("TM results contain claim IDs absent from the held-out test dataset")

    predictor = PythonClaimPredictor(
        ROOT / "model/classifier.joblib",
        ROOT / "model/model_metadata.json",
        ROOT / "policies/warranty_policies.json",
    )
    rule_engine = RuleEngine(ROOT / "policies/warranty_policies.json")
    decision_engine = DecisionEngine(ROOT / "policies/consistency_policy.json")
    rows = []
    for _, raw in merged.sort_values("claim_id").head(args.limit).iterrows():
        claim = row_to_claim(raw)
        python = predictor.predict(claim)
        tm_probs = {
            ModelClass.VALID_CLAIM: float(raw.tm_valid_confidence),
            ModelClass.INVALID_CLAIM: float(raw.tm_invalid_confidence),
            ModelClass.MANUAL_REVIEW: float(raw.tm_manual_review_confidence),
        }
        tm_class = LABEL_TO_ENUM[str(raw.tm_predicted_class).strip()]
        tm_prediction = ModelPrediction(
            model_name="TeachableMachine",
            model_version="exported-model",
            predicted_class=tm_class,
            confidence=tm_probs[tm_class],
            probabilities=tm_probs,
            timestamp=datetime.now(timezone.utc),
        )
        rules = rule_engine.evaluate(claim)
        failed_rules = [r.rule_id for r in rules if not r.passed]
        _, confidence_difference, consistency_status = decision_engine.compare_models(python, tm_prediction)
        contradictions = [
            r.rule_id for r in rules
            if ("before_purchase" in r.rule_id or "consistency" in r.rule_id or "contradiction" in r.rule_id)
            and not r.passed
        ]
        missing_docs = [d.value for d in claim.missing_document_types]
        final = decision_engine.decide(
            claim.claim_id,
            python,
            tm_prediction,
            rules,
            contradiction_flags=contradictions,
            missing_document_flags=claim.missing_document_types,
            duplicate_flag=claim.duplicate_claim,
        )
        diff = abs(python.confidence - tm_prediction.confidence)
        rows.append({
            "claim_id": claim.claim_id,
            "actual_class": raw.actual_class,
            "python_predicted_class": python.predicted_class.value,
            "python_valid_confidence": python.probabilities[ModelClass.VALID_CLAIM],
            "python_invalid_confidence": python.probabilities[ModelClass.INVALID_CLAIM],
            "python_manual_review_confidence": python.probabilities[ModelClass.MANUAL_REVIEW],
            "claim_summary_card_filename": f"data/claim_cards/test/{raw.actual_class}/{claim.claim_id}_v1.jpg",
            "tm_predicted_class": tm_prediction.predicted_class.value,
            "tm_valid_confidence": tm_prediction.probabilities[ModelClass.VALID_CLAIM],
            "tm_invalid_confidence": tm_prediction.probabilities[ModelClass.INVALID_CLAIM],
            "tm_manual_review_confidence": tm_prediction.probabilities[ModelClass.MANUAL_REVIEW],
            "predicted_class_match": python.predicted_class == tm_prediction.predicted_class,
            "top_class_confidence_difference": confidence_difference,
            "model_consistency_status": consistency_status.value,
            "warranty_rule_result": ";".join(failed_rules) if failed_rules else "pass",
            "missing_documents": ",".join(missing_docs),
            "contradictions_detected": ",".join(contradictions),
            "duplicate_indicator": claim.duplicate_claim,
            "final_application_decision": final.decision.value,
            "disagreement_explanation": "; ".join(final.reasons),
        })
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output, index=False)
    summary = pd.DataFrame(rows)
    print(json.dumps({
        "rows": len(summary),
        "prediction_agreement": int(summary["predicted_class_match"].sum()) if len(summary) else 0,
        "output": str(output),
    }, indent=2))


if __name__ == "__main__":
    main()
