"""Generate the SRS-required Claim Summary Card dataset from claims.csv."""

from pathlib import Path

import pandas as pd

from src.cards.generator import ClaimSummaryCardBuilder
from src.domain.schemas import Claim, Product, Warranty


PRODUCT_CATEGORIES = {
    "Smartphone": ("Electronics", "Nova"),
    "Washing Machine": ("Home Appliance", "Cleanwave"),
    "Laptop": ("Electronics", "Vertex"),
    "Refrigerator": ("Home Appliance", "FrostLine"),
    "Air Conditioner": ("Home Appliance", "Chillmax"),
    "Television": ("Electronics", "Vistara"),
}


def row_to_claim(row: pd.Series) -> Claim:
    from datetime import date

    product = Product(
        product_id=f"PRD-{row.claim_id}",
        product_name=row.product_name,
        category=row.category,
        brand=row.brand,
        model_number=row.model_number,
        serial_number=row.serial_number,
        purchase_date=date.fromisoformat(row.purchase_date),
        purchase_price=float(row.purchase_price),
        retailer=row.retailer,
        invoice_number=None,
        warranty_duration_months=int(row.warranty_duration_months),
    )
    warranty = Warranty(
        warranty_id=f"WAR-{row.claim_id}",
        product_id=product.product_id,
        provider="AssureX Warranty",
        start_date=product.purchase_date,
        end_date=date.fromisoformat(row.warranty_end_date),
    )
    return Claim(
        claim_id=row.claim_id,
        customer_id=f"CUS-{row.claim_id}",
        product=product,
        warranty=warranty,
        claim_submission_date=date.fromisoformat(row.claim_date),
        fault_description=str(row.fault_type),
        fault_category=str(row.fault_type),
        serial_number_match=bool(row.serial_number_match),
        missing_document_types=[],
    )


def generate_cards(
    csv_path: str | Path = "data/claims.csv",
    output_root: str | Path = "data/claim_cards",
) -> dict[str, int]:
    frame = pd.read_csv(csv_path)
    builder = ClaimSummaryCardBuilder()
    counts = {"train": 0, "validation": 0, "test": 0}

    for _, row in frame.iterrows():
        claim = row_to_claim(row)
        split = str(row.split)
        label = str(row.class_label)
        card_data = builder.build_data(claim)
        for variation in (1, 2) if split == "train" else (1,):
            destination = Path(output_root) / split / label / f"{claim.claim_id}_v{variation}.jpg"
            builder.render(card_data, destination, variation=variation)
            counts[split] += 1
    return counts


if __name__ == "__main__":
    print(generate_cards())
