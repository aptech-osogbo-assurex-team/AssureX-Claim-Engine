"""AssureX Claim Engine - baseline classification model.

Loads data/claims.csv (already split into train/validation/test by the
generator), trains a few candidate models on train, selects the best on
validation, and reports final accuracy on test - the held-out set that
stands in for "unseen claims" per the 85% requirement.

The test set is touched exactly once, at the end, after model selection
is already decided from validation - touching it earlier would make the
final number an unreliable estimate of real generalization.
"""

import pandas as pd
import joblib
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

NUMERIC_FEATURES = [
    "purchase_price", "warranty_duration_months", "product_age_days",
    "remaining_warranty_days", "repair_history_count", "missing_document_count",
]
CATEGORICAL_FEATURES = [
    "category", "brand", "retailer", "fault_type",
    "fault_covered", "serial_number_match",
    "claim_date_before_purchase", "repair_date_before_purchase",
]
TARGET = "class_label"


def load_splits(path: str = "data/claims.csv"):
    df = pd.read_csv(path)
    train = df[df["split"] == "train"]
    val = df[df["split"] == "validation"]
    test = df[df["split"] == "test"]
    return train, val, test


def build_pipeline(model) -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", "passthrough", NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
        ]
    )
    return Pipeline(steps=[("preprocess", preprocessor), ("model", model)])


def evaluate(pipeline: Pipeline, X, y, label: str):
    preds = pipeline.predict(X)
    acc = accuracy_score(y, preds)
    print(f"\n{label} accuracy: {acc:.4f}")
    print(classification_report(y, preds))
    return acc


if __name__ == "__main__":
    train, val, test = load_splits()
    X_train, y_train = train[NUMERIC_FEATURES + CATEGORICAL_FEATURES], train[TARGET]
    X_val, y_val = val[NUMERIC_FEATURES + CATEGORICAL_FEATURES], val[TARGET]
    X_test, y_test = test[NUMERIC_FEATURES + CATEGORICAL_FEATURES], test[TARGET]

    candidates = {
        "LogisticRegression": LogisticRegression(max_iter=5000),
        "RandomForest": RandomForestClassifier(n_estimators=300, random_state=42),
        "GradientBoosting": GradientBoostingClassifier(random_state=42),
    }

    best_name, best_pipeline, best_val_acc = None, None, -1.0
    print("=== Model selection on validation set ===")
    for name, model in candidates.items():
        pipeline = build_pipeline(model)
        pipeline.fit(X_train, y_train)
        val_acc = evaluate(pipeline, X_val, y_val, f"{name} (validation)")
        if val_acc > best_val_acc:
            best_name, best_pipeline, best_val_acc = name, pipeline, val_acc

    print(f"\n=== Selected model: {best_name} (validation accuracy {best_val_acc:.4f}) ===")

    test_acc = evaluate(best_pipeline, X_test, y_test, f"{best_name} (TEST - held out)")
    print("\nConfusion matrix (test):")
    print(confusion_matrix(y_test, best_pipeline.predict(X_test),
                            labels=["Valid Claim", "Invalid Claim", "Manual Review"]))

    print(f"\nTarget: 0.85 | Achieved on test: {test_acc:.4f} | "
          f"{'MEETS target' if test_acc >= 0.85 else 'BELOW target - needs work'}")

    joblib.dump(best_pipeline, "model/classifier.joblib")
    print(f"\nSaved best model ({best_name}) to model/classifier.joblib")