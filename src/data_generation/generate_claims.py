"""AssureX Claim Engine - synthetic claim dataset generator and splitter.

Produces data/claims.csv: 1500 records (500 per class), split 70/15/15
into train/validation/test with exact per-class quotas (350/75/75 each).
"""

import random
from datetime import date, timedelta
import numpy as np
import pandas as pd

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

PRODUCTS = [
    ("Smartphone", "Electronics", "Nova", ["NV-100", "NV-200", "NV-X1"]),
    ("Washing Machine", "Home Appliance", "Cleanwave", ["CW-700", "CW-750D"]),
    ("Laptop", "Electronics", "Vertex", ["VT-14", "VT-15Pro"]),
    ("Refrigerator", "Home Appliance", "FrostLine", ["FL-220", "FL-300X"]),
    ("Air Conditioner", "Home Appliance", "Chillmax", ["CM-1T", "CM-1.5T"]),
    ("Television", "Electronics", "Vistara", ["VS-43", "VS-55UHD"]),
]
PRODUCT_WEIGHTS = [0.22, 0.18, 0.20, 0.14, 0.12, 0.14]
RETAILERS = ["MegaMart Electronics", "HomeStyle Retail", "TechHub Store", "CityWide Appliances"]
RETAILER_WEIGHTS = [0.35, 0.28, 0.22, 0.15]

COVERED_FAULTS = ["Manufacturing defect", "Component failure", "Motor malfunction",
                   "Display fault", "Battery defect", "Compressor failure"]
EXCLUDED_FAULTS = ["Water damage", "Physical/drop damage", "Unauthorized repair damage",
                    "Power surge (external)", "Normal wear and tear"]
DOC_TYPES = ["receipt", "warranty_card", "product_photo", "serial_evidence", "fault_evidence"]


def _random_date(start: date, end: date) -> date:
    span = max((end - start).days, 0)
    return start + timedelta(days=random.randint(0, span))


def _weighted_choice(items, weights):
    return random.choices(items, weights=weights, k=1)[0]


def _make_product():
    idx = _weighted_choice(range(len(PRODUCTS)), PRODUCT_WEIGHTS)
    name, category, brand, models = PRODUCTS[idx]
    model_number = random.choice(models)
    serial_number = f"SN{random.randint(10_000_000, 99_999_999)}"
    return name, category, brand, model_number, serial_number


def _repair_count(mean: float) -> int:
    return int(np.random.poisson(lam=mean))


def _price_for(category: str) -> float:
    base = 650 if category == "Electronics" else 900
    price = np.random.normal(loc=base, scale=base * 0.35)
    return round(max(40.0, price), 2)


def _base_record(claim_idx: int, purchase_date: date, warranty_months: int,
                  claim_date: date) -> dict:
    name, category, brand, model_number, serial_number = _make_product()
    warranty_end = purchase_date + timedelta(days=warranty_months * 30)
    return {
        "claim_id": f"CLM-{claim_idx:06d}",
        "product_name": name,
        "category": category,
        "brand": brand,
        "model_number": model_number,
        "serial_number": serial_number,
        "retailer": _weighted_choice(RETAILERS, RETAILER_WEIGHTS),
        "purchase_date": purchase_date.isoformat(),
        "purchase_price": _price_for(category),
        "warranty_duration_months": warranty_months,
        "warranty_end_date": warranty_end.isoformat(),
        "claim_date": claim_date.isoformat(),
        "product_age_days": (claim_date - purchase_date).days,
        "remaining_warranty_days": (warranty_end - claim_date).days,
    }


def generate_valid_claim(claim_idx: int) -> dict:
    purchase_date = _random_date(date(2022, 1, 1), date(2025, 6, 1))
    warranty_months = _weighted_choice([12, 18, 24, 36], [0.35, 0.20, 0.30, 0.15])
    warranty_end = purchase_date + timedelta(days=warranty_months * 30)

    margin_days = int(np.random.exponential(scale=120))
    margin_days = min(margin_days, max((warranty_end - purchase_date).days - 15, 15))
    claim_date = warranty_end - timedelta(days=max(margin_days, 1))
    claim_date = max(claim_date, purchase_date + timedelta(days=10))

    rec = _base_record(claim_idx, purchase_date, warranty_months, claim_date)
    rec.update({
        "fault_type": random.choice(COVERED_FAULTS),
        "fault_covered": True,
        "repair_history_count": _repair_count(mean=0.3),
        "serial_number_entered": rec["serial_number"],
        "serial_number_match": True,
        "documents_provided": ",".join(DOC_TYPES),
        "missing_document_count": 0,
        "claim_date_before_purchase": False,
        "repair_date_before_purchase": False,
        "class_label": "Valid Claim",
    })
    return rec


def generate_invalid_claim(claim_idx: int) -> dict:
    purchase_date = _random_date(date(2020, 1, 1), date(2025, 3, 1))
    warranty_months = _weighted_choice([12, 18, 24], [0.5, 0.25, 0.25])
    warranty_end = purchase_date + timedelta(days=warranty_months * 30)

    reasons = ["expired", "excluded_fault", "serial_mismatch", "contradiction"]
    active_reasons = {random.choice(reasons)}
    if random.random() < 0.20:
        active_reasons.add(random.choice([r for r in reasons if r not in active_reasons]))

    claim_date_before_purchase = False
    repair_date_before_purchase = False
    fault_covered = True
    fault_type = random.choice(COVERED_FAULTS)
    serial_match = True
    docs = DOC_TYPES.copy()

    if "expired" in active_reasons:
        overdue_days = int(np.random.exponential(scale=90)) + 1
        claim_date = warranty_end + timedelta(days=overdue_days)
    else:
        claim_date = _random_date(purchase_date + timedelta(days=10), warranty_end)

    if "excluded_fault" in active_reasons:
        fault_type = random.choice(EXCLUDED_FAULTS)
        fault_covered = False
    if "serial_mismatch" in active_reasons:
        serial_match = False
    if "contradiction" in active_reasons:
        if random.random() < 0.5:
            claim_date_before_purchase = True
        else:
            repair_date_before_purchase = True

    rec = _base_record(claim_idx, purchase_date, warranty_months, claim_date)
    entered_serial = (rec["serial_number"] if serial_match
                       else f"SN{random.randint(10_000_000, 99_999_999)}")
    rec.update({
        "fault_type": fault_type,
        "fault_covered": fault_covered,
        "repair_history_count": _repair_count(mean=1.4),
        "serial_number_entered": entered_serial,
        "serial_number_match": serial_match,
        "documents_provided": ",".join(docs),
        "missing_document_count": 0,
        "claim_date_before_purchase": claim_date_before_purchase,
        "repair_date_before_purchase": repair_date_before_purchase,
        "class_label": "Invalid Claim",
    })
    return rec


def generate_manual_review_claim(claim_idx: int) -> dict:
    purchase_date = _random_date(date(2021, 1, 1), date(2025, 5, 1))
    warranty_months = _weighted_choice([12, 18, 24, 36], [0.3, 0.25, 0.3, 0.15])
    warranty_end = purchase_date + timedelta(days=warranty_months * 30)

    factors = ["borderline_warranty", "one_missing_doc", "high_repair_history", "near_serial_typo"]
    active_factors = {random.choice(factors)}
    if random.random() < 0.25:
        active_factors.add(random.choice([f for f in factors if f not in active_factors]))

    if "borderline_warranty" in active_factors:
        offset = int(np.random.normal(loc=0, scale=6))
        claim_date = warranty_end + timedelta(days=offset)
        claim_date = max(claim_date, purchase_date + timedelta(days=10))
    else:
        claim_date = _random_date(purchase_date + timedelta(days=10),
                                   warranty_end - timedelta(days=5))

    docs = DOC_TYPES.copy()
    missing_count = 0
    repair_count = _repair_count(mean=0.5)

    rec = _base_record(claim_idx, purchase_date, warranty_months, claim_date)
    entered_serial = rec["serial_number"]
    serial_match = True

    if "one_missing_doc" in active_factors:
        missing_doc = random.choice(DOC_TYPES)
        docs.remove(missing_doc)
        missing_count = 1
    if "high_repair_history" in active_factors:
        repair_count = _repair_count(mean=2.8)
    if "near_serial_typo" in active_factors:
        chars = list(rec["serial_number"])
        pos = random.randint(2, len(chars) - 1)
        original_char = chars[pos]
        chars[pos] = random.choice([c for c in "0123456789" if c != original_char])
        entered_serial = "".join(chars)
        serial_match = False

    rec.update({
        "fault_type": random.choice(COVERED_FAULTS),
        "fault_covered": True,
        "repair_history_count": repair_count,
        "serial_number_entered": entered_serial,
        "serial_number_match": serial_match,
        "documents_provided": ",".join(docs),
        "missing_document_count": missing_count,
        "claim_date_before_purchase": False,
        "repair_date_before_purchase": False,
        "class_label": "Manual Review",
    })
    return rec


def generate_dataset(n_per_class: int = 500) -> pd.DataFrame:
    records = []
    idx = 1
    for _ in range(n_per_class):
        records.append(generate_valid_claim(idx)); idx += 1
    for _ in range(n_per_class):
        records.append(generate_invalid_claim(idx)); idx += 1
    for _ in range(n_per_class):
        records.append(generate_manual_review_claim(idx)); idx += 1
    return pd.DataFrame(records)


def exact_stratified_split(df: pd.DataFrame, train_frac=0.70, val_frac=0.15) -> pd.DataFrame:
    """Split each class independently by exact row count (not approximate
    global proportions), so class balance is exact in every split with no
    rounding drift."""
    parts = []
    for label, group in df.groupby("class_label"):
        group = group.sample(frac=1, random_state=SEED).reset_index(drop=True)
        n = len(group)
        n_train = int(round(n * train_frac))
        n_val = int(round(n * val_frac))

        train = group.iloc[:n_train].copy()
        val = group.iloc[n_train:n_train + n_val].copy()
        test = group.iloc[n_train + n_val:].copy()

        train["split"] = "train"
        val["split"] = "validation"
        test["split"] = "test"
        parts.extend([train, val, test])

    result = pd.concat(parts).sample(frac=1, random_state=SEED).reset_index(drop=True)
    return result.sort_values("claim_id").reset_index(drop=True)


def print_split_report(df: pd.DataFrame) -> None:
    report = df.groupby(["split", "class_label"]).size().unstack(fill_value=0)
    print(report)
    print(df["split"].value_counts())
    print(f"Total: {len(df)}")


if __name__ == "__main__":
    dataset = generate_dataset(n_per_class=500)
    assert len(dataset) == 1500, f"Expected 1500 records, got {len(dataset)}"

    final_df = exact_stratified_split(dataset)
    print_split_report(final_df)

    final_df.to_csv("data/claims.csv", index=False)
    print(f"Saved {len(final_df)} records to data/claims.csv")