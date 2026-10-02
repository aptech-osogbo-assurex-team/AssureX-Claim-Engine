"""Build deterministic SRS evidence artifacts from the common claims dataset.

This script does not train Teachable Machine. It prepares the exact card dataset,
its train/validation/test manifests, mapping evidence, Python model evaluation,
and a browser-ready manifest for the independently trained Teachable Machine.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from src.cards.dataset import row_to_claim, generate_cards
from src.cards.generator import ClaimSummaryCardBuilder
from src.domain.enums import ModelClass
from src.ml.inference import PythonClaimPredictor
from src.rules.engine import RuleEngine

CLAIMS = ROOT / "data" / "claims.csv"
DATASETS = ROOT / "data" / "datasets"
CARD_ROOT = ROOT / "data" / "claim_cards"
REPORTS = ROOT / "reports"
MODEL_PATH = ROOT / "model" / "classifier.joblib"
METRICS_PATH = ROOT / "model" / "training_metrics.json"
POLICY_PATH = ROOT / "policies" / "warranty_policies.json"

LABELS = ["Valid Claim", "Invalid Claim", "Manual Review"]

DATA_DICTIONARY = {
    "claim_id": "Unique claim identifier.",
    "product_name": "Product name.",
    "category": "Product category used by the warranty policy and model.",
    "brand": "Product manufacturer/brand.",
    "model_number": "Product model identifier.",
    "serial_number": "Registered product serial number.",
    "retailer": "Retailer recorded for the purchase.",
    "purchase_date": "Purchase date in ISO date format.",
    "purchase_price": "Purchase price in the dataset currency units.",
    "warranty_duration_months": "Nominal warranty duration.",
    "warranty_end_date": "Calculated warranty end date.",
    "claim_date": "Claim submission date.",
    "product_age_days": "Days between purchase and claim submission.",
    "remaining_warranty_days": "Days remaining in warranty at claim submission.",
    "fault_type": "Reported fault category.",
    "fault_covered": "Whether the generated fault is covered by the scenario.",
    "repair_history_count": "Number of previous repair events.",
    "serial_number_entered": "Serial number supplied by claimant.",
    "serial_number_match": "Whether entered and registered serial numbers match.",
    "documents_provided": "Comma-separated document types represented by the scenario.",
    "missing_document_count": "Number of mandatory document groups missing.",
    "claim_date_before_purchase": "Contradiction flag derived from claim and purchase dates.",
    "repair_date_before_purchase": "Contradiction flag derived from repair and purchase dates.",
    "class_label": "Target class: Valid Claim, Invalid Claim, or Manual Review.",
    "repair_date": "Representative repair date when repair history exists.",
    "warranty_boundary_proximity": "Absolute days from the warranty boundary.",
    "has_partial_documents": "Indicator that some but not all mandatory documents are present.",
    "split": "Dataset partition: train, validation, or test.",
}


def reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def write_dataset_artifacts(frame: pd.DataFrame) -> None:
    reset_dir(DATASETS)
    for split in ("train", "validation", "test"):
        split_frame = frame[frame["split"] == split].copy().sort_values("claim_id")
        split_frame.to_csv(DATASETS / f"{split}.csv", index=False)

    stats = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_records": int(len(frame)),
        "classes": frame["class_label"].value_counts().sort_index().to_dict(),
        "splits": {
            split: {
                "records": int((frame["split"] == split).sum()),
                "classes": frame.loc[frame["split"] == split, "class_label"].value_counts().sort_index().to_dict(),
            }
            for split in ("train", "validation", "test")
        },
        "claim_ids_unique": bool(frame["claim_id"].is_unique),
    }
    (REPORTS / "dataset_statistics.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")

    with (REPORTS / "data_dictionary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["field", "description"])
        for field in frame.columns:
            writer.writerow([field, DATA_DICTIONARY.get(field, "Dataset field.")])


def _render_card_task(task: tuple[dict, str, str, int]) -> dict:
    card_payload, output_path, relative_path, variation = task
    builder = ClaimSummaryCardBuilder()
    from src.domain.schemas import ClaimSummaryCard
    card = ClaimSummaryCard.model_validate(card_payload)
    output = Path(output_path)
    builder.render(card, output, variation=variation)
    return {
        "claim_id": card.claim_id,
        "variation": variation,
        "relative_image_path": relative_path,
        "image_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }


def render_and_map(frame: pd.DataFrame) -> None:
    reset_dir(CARD_ROOT)
    builder = ClaimSummaryCardBuilder()
    mapping_rows: list[dict[str, object]] = []
    card_data_rows: list[dict[str, object]] = []
    tm_test_manifest: list[dict[str, str]] = []
    render_tasks: list[tuple[dict, str, str, int]] = []

    for _, row in frame.sort_values("claim_id").iterrows():
        claim = row_to_claim(row)
        card = builder.build_data(claim)
        split = str(row.split)
        label = str(row.class_label)
        variations = (1, 2) if split == "train" else (1,)
        for variation in variations:
            output = CARD_ROOT / split / label / f"{claim.claim_id}_v{variation}.jpg"
            render_tasks.append((card.model_dump(mode="json"), str(output), output.relative_to(ROOT).as_posix(), variation))

        card_data_rows.append({
            "claim_id": card.claim_id,
            "split": split,
            "class_label": label,
            "product_age_days": card.product_age_days,
            "warranty_status": card.warranty_status,
            "remaining_warranty_days": card.remaining_warranty_days,
            "fault_category": card.fault_category,
            "repair_history_count": card.repair_history_count,
            "receipt_available": card.receipt_available,
            "warranty_card_available": card.warranty_card_available,
            "serial_number_match": card.serial_number_match,
            "missing_documents": ",".join(item.value for item in card.missing_documents) or "None",
            "damage_type": card.damage_type or "",
        })

    max_workers = max(1, min(4, os.cpu_count() or 1))
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        rendered = list(pool.map(_render_card_task, render_tasks, chunksize=12))

    mapping_by_claim_variation = {(r["claim_id"], r["variation"]): r for r in rendered}
    for _, row in frame.sort_values("claim_id").iterrows():
        claim_id = str(row.claim_id)
        split = str(row.split)
        label = str(row.class_label)
        variations = (1, 2) if split == "train" else (1,)
        for variation in variations:
            result = mapping_by_claim_variation[(claim_id, variation)]
            mapping_rows.append({
                "claim_id": claim_id,
                "split": split,
                "class_label": label,
                "variation": variation,
                "relative_image_path": result["relative_image_path"],
                "image_sha256": result["image_sha256"],
            })

        if split == "test":
            tm_test_manifest.append({
                "claim_id": claim_id,
                "actual_class": label,
                "image_path": "/" + f"data/claim_cards/test/{label}/{claim_id}_v1.jpg",
            })

    pd.DataFrame(mapping_rows).to_csv(REPORTS / "card_mapping.csv", index=False)
    pd.DataFrame(card_data_rows).to_csv(REPORTS / "card_data_manifest.csv", index=False)
    (ROOT / "static" / "tm_test_manifest.json").write_text(
        json.dumps(tm_test_manifest, indent=2), encoding="utf-8"
    )
    expected_counts = {"train": 2100, "validation": 225, "test": 225}
    actual_counts = {split: sum(1 for item in mapping_rows if item["split"] == split) for split in expected_counts}
    if actual_counts != expected_counts:
        raise ValueError(f"Unexpected generated card counts: {actual_counts}")

    # Build a compact integrity summary used by the final evidence audit.
    fidelity_mismatches = 0
    for _, row in frame.iterrows():
        expected_claim = row_to_claim(row)
        expected_card = builder.build_data(expected_claim)
        actual = pd.DataFrame(card_data_rows).query("claim_id == @row.claim_id").iloc[0]
        checks = {
            "product_age_days": expected_card.product_age_days,
            "warranty_status": expected_card.warranty_status,
            "remaining_warranty_days": expected_card.remaining_warranty_days,
            "fault_category": expected_card.fault_category,
            "repair_history_count": expected_card.repair_history_count,
            "receipt_available": expected_card.receipt_available,
            "warranty_card_available": expected_card.warranty_card_available,
            "serial_number_match": expected_card.serial_number_match,
            "missing_documents": ",".join(item.value for item in expected_card.missing_documents) or "None",
        }
        for key, value in checks.items():
            actual_value = actual[key]
            if str(actual_value) != str(value):
                fidelity_mismatches += 1
    (REPORTS / "card_fidelity_audit.json").write_text(
        json.dumps({"claims_checked": int(len(frame)), "field_mismatches": fidelity_mismatches, "result": "PASS" if fidelity_mismatches == 0 else "FAIL"}, indent=2),
        encoding="utf-8",
    )


def write_python_evaluation(frame: pd.DataFrame) -> None:
    train = frame[frame["split"] == "train"].copy()
    val = frame[frame["split"] == "validation"].copy()
    test = frame[frame["split"] == "test"].copy()

    features = [
        "purchase_price", "warranty_duration_months", "product_age_days",
        "remaining_warranty_days", "repair_history_count", "missing_document_count",
        "warranty_boundary_proximity", "has_partial_documents", "category", "brand",
        "retailer", "fault_type", "fault_covered", "serial_number_match",
        "claim_date_before_purchase", "repair_date_before_purchase",
    ]
    model = joblib.load(MODEL_PATH)
    predictions = model.predict(test[features])
    report = classification_report(
        test["class_label"], predictions, labels=LABELS, output_dict=True, zero_division=0
    )
    matrix = confusion_matrix(test["class_label"], predictions, labels=LABELS).tolist()
    metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    payload = {
        "model_name": metrics["model_name"],
        "model_artifact": str(MODEL_PATH.relative_to(ROOT)).replace("\\", "/"),
        "training_records": int(len(train)),
        "validation_records": int(len(val)),
        "test_records": int(len(test)),
        "validation_accuracy": metrics["validation_accuracy"],
        "cross_validation": metrics["cross_validation"],
        "test_accuracy": round(float(accuracy_score(test["class_label"], predictions)), 6),
        "classification_report": {
            label: {
                "precision": round(float(report[label]["precision"]), 6),
                "recall": round(float(report[label]["recall"]), 6),
                "f1_score": round(float(report[label]["f1-score"]), 6),
                "support": int(report[label]["support"]),
            }
            for label in LABELS
        },
        "confusion_matrix_labels": LABELS,
        "confusion_matrix": matrix,
    }
    (REPORTS / "python_model_evaluation.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Python Model Evaluation",
        "",
        f"**Model:** {payload['model_name']}",
        f"**Training / validation / test:** {payload['training_records']} / {payload['validation_records']} / {payload['test_records']}",
        f"**Held-out test accuracy:** {payload['test_accuracy']:.4f}",
        f"**5-fold CV mean:** {payload['cross_validation']['mean']:.4f}",
        f"**5-fold CV standard deviation:** {payload['cross_validation']['std']:.4f}",
        "",
        "## Class-wise metrics",
        "",
        "| Class | Precision | Recall | F1 | Support |",
        "|---|---:|---:|---:|---:|",
    ]
    for label in LABELS:
        m = payload["classification_report"][label]
        lines.append(f"| {label} | {m['precision']:.4f} | {m['recall']:.4f} | {m['f1_score']:.4f} | {m['support']} |")
    lines += ["", "## Confusion matrix", "", "| Actual \\ Predicted | Valid Claim | Invalid Claim | Manual Review |", "|---|---:|---:|---:|"]
    for label, row in zip(LABELS, matrix):
        lines.append(f"| {label} | {row[0]} | {row[1]} | {row[2]} |")
    lines += [
        "",
        "## Evidence note",
        "",
        "The score is measured on the held-out synthetic test split. It is not presented as evidence of real-world production generalisation.",
    ]
    (REPORTS / "python_model_evaluation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_comparison_template(frame: pd.DataFrame) -> None:
    # Ten deterministic unseen test claims per class. TM fields are intentionally blank
    # until the independently trained exported model is evaluated in the browser.
    selected = pd.concat([
        frame[(frame.split == "test") & (frame.class_label == label)].sort_values("claim_id").head(10)
        for label in LABELS
    ]).sort_values("claim_id")

    predictor = PythonClaimPredictor(MODEL_PATH, ROOT / "model" / "model_metadata.json", POLICY_PATH)
    rule_engine = RuleEngine(POLICY_PATH)
    rows = []
    for _, raw in selected.iterrows():
        claim = row_to_claim(raw)
        prediction = predictor.predict(claim)
        rule_results = rule_engine.evaluate(claim)
        failed = [r.rule_id for r in rule_results if not r.passed]
        rows.append({
            "claim_id": claim.claim_id,
            "actual_class": raw.class_label,
            "python_predicted_class": prediction.predicted_class.value,
            "python_valid_confidence": prediction.probabilities[ModelClass.VALID_CLAIM.value],
            "python_invalid_confidence": prediction.probabilities[ModelClass.INVALID_CLAIM.value],
            "python_manual_review_confidence": prediction.probabilities[ModelClass.MANUAL_REVIEW.value],
            "claim_summary_card_filename": f"data/claim_cards/test/{raw.class_label}/{claim.claim_id}_v1.jpg",
            "tm_predicted_class": "",
            "tm_valid_confidence": "",
            "tm_invalid_confidence": "",
            "tm_manual_review_confidence": "",
            "predicted_class_match": "",
            "top_class_confidence_difference": "",
            "model_consistency_status": "",
            "warranty_rule_result": ";".join(failed) if failed else "pass",
            "missing_documents": ",".join(d.value for d in claim.missing_document_types),
            "contradictions_detected": ",".join(r.rule_id for r in rule_results if "contradiction" in r.rule_id or "before_purchase" in r.rule_id),
            "duplicate_indicator": claim.duplicate_claim,
            "final_application_decision": "",
            "disagreement_explanation": "",
        })
    pd.DataFrame(rows).to_csv(REPORTS / "model_comparison_30_template.csv", index=False)


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(CLAIMS)
    if len(frame) != 1500:
        raise ValueError(f"Expected 1500 claims, found {len(frame)}")
    if frame["claim_id"].duplicated().any():
        raise ValueError("Duplicate claim IDs found")
    expected = {
        ("train", "Valid Claim"): 350, ("train", "Invalid Claim"): 350, ("train", "Manual Review"): 350,
        ("validation", "Valid Claim"): 75, ("validation", "Invalid Claim"): 75, ("validation", "Manual Review"): 75,
        ("test", "Valid Claim"): 75, ("test", "Invalid Claim"): 75, ("test", "Manual Review"): 75,
    }
    actual = frame.groupby(["split", "class_label"]).size().to_dict()
    if actual != expected:
        raise ValueError(f"Unexpected split counts: {actual}")

    write_dataset_artifacts(frame)
    render_and_map(frame)
    write_python_evaluation(frame)
    write_comparison_template(frame)

    card_counts = {
        split: sum(1 for p in (CARD_ROOT / split).rglob("*.jpg"))
        for split in ("train", "validation", "test")
    }
    integrity = {
        "claim_records": 1500,
        "card_counts": card_counts,
        "training_card_variations_per_claim": 2,
        "validation_variations_per_claim": 1,
        "test_variations_per_claim": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (REPORTS / "card_dataset_integrity.json").write_text(json.dumps(integrity, indent=2), encoding="utf-8")
    print(json.dumps(integrity, indent=2))


if __name__ == "__main__":
    main()
