"""Generate the SRS-required Claim Summary Card dataset from claims.csv.

The card dataset must be a faithful visual representation of the same underlying
claim records used by the Python classifier. This module therefore reconstructs
submitted-document and repair-history evidence from the CSV before rendering.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import pandas as pd

from src.cards.generator import ClaimSummaryCardBuilder
from src.domain.enums import DocumentType, RepairAuthorization
from src.domain.schemas import Claim, Document, Product, RepairRecord, Warranty


DOC_COLUMN_VALUES: dict[str, DocumentType] = {
    "receipt": DocumentType.RECEIPT,
    "invoice": DocumentType.INVOICE,
    "warranty_card": DocumentType.WARRANTY_CARD,
    "product_photo": DocumentType.PRODUCT_PHOTO,
    "serial_evidence": DocumentType.SERIAL_EVIDENCE,
    "fault_evidence": DocumentType.FAULT_EVIDENCE,
    "fault_video": DocumentType.FAULT_VIDEO,
    "repair_report": DocumentType.REPAIR_REPORT,
    "diagnostic_report": DocumentType.DIAGNOSTIC_REPORT,
    "replacement_evidence": DocumentType.REPLACEMENT_EVIDENCE,
    "other": DocumentType.OTHER,
}

REQUIRED_DOCUMENT_GROUPS: tuple[tuple[DocumentType, ...], ...] = (
    (DocumentType.RECEIPT, DocumentType.INVOICE),
    (DocumentType.WARRANTY_CARD,),
    (DocumentType.PRODUCT_PHOTO,),
    (DocumentType.SERIAL_EVIDENCE,),
    (DocumentType.FAULT_EVIDENCE,),
)


def _is_present(value: object) -> bool:
    return not pd.isna(value) and str(value).strip() != ""


def _parse_documents(raw: object) -> list[DocumentType]:
    if not _is_present(raw):
        return []
    return [
        DOC_COLUMN_VALUES[token.strip()]
        for token in str(raw).split(",")
        if token.strip() in DOC_COLUMN_VALUES
    ]


def _missing_documents(submitted: list[DocumentType]) -> list[DocumentType]:
    available = set(submitted)
    missing: list[DocumentType] = []
    for group in REQUIRED_DOCUMENT_GROUPS:
        if not any(item in available for item in group):
            missing.append(group[0])
    return missing


def _document_for(claim_id: str, submitted_at: date, document_type: DocumentType) -> Document:
    digest = hashlib.sha256(f"{claim_id}:{document_type.value}".encode("utf-8")).hexdigest()
    timestamp = datetime.combine(submitted_at, time.min, tzinfo=timezone.utc)
    return Document(
        document_id=f"DOC-{claim_id}-{document_type.value}",
        claim_id=claim_id,
        document_type=document_type,
        filename=f"{claim_id}_{document_type.value}.synthetic",
        mime_type="application/octet-stream",
        size_bytes=1,
        sha256=digest,
        uploaded_at=timestamp,
    )


def _repair_records(
    claim_id: str,
    product_id: str,
    purchase_date: date,
    claim_date: date,
    count: int,
    recorded_date: date | None,
) -> list[RepairRecord]:
    if count <= 0:
        return []

    # The CSV stores one repair date. The remaining records are deterministic
    # synthetic placeholders needed only to preserve the repair-history count.
    dates: list[date] = []
    if recorded_date is not None:
        dates.append(recorded_date)
    else:
        dates.append(max(purchase_date, claim_date - timedelta(days=1)))

    while len(dates) < count:
        candidate = dates[-1] - timedelta(days=30)
        if candidate < purchase_date:
            candidate = purchase_date
        dates.append(candidate)

    return [
        RepairRecord(
            repair_id=f"REP-{claim_id}-{index:02d}",
            product_id=product_id,
            repair_date=repair_date,
            repair_center="Synthetic dataset record",
            replaced_parts=[],
            outcome="Recorded repair history",
            repair_cost=0,
            authorized=RepairAuthorization.UNKNOWN,
        )
        for index, repair_date in enumerate(dates, start=1)
    ]


def row_to_claim(row: pd.Series) -> Claim:
    """Convert one CSV row into the same evidence fields represented on its card."""

    purchase_date = date.fromisoformat(str(row.purchase_date))
    claim_date = date.fromisoformat(str(row.claim_date))
    product_id = f"PRD-{row.claim_id}"

    product = Product(
        product_id=product_id,
        product_name=str(row.product_name),
        category=str(row.category),
        brand=str(row.brand),
        model_number=str(row.model_number),
        serial_number=str(row.serial_number),
        purchase_date=purchase_date,
        purchase_price=float(row.purchase_price),
        retailer=str(row.retailer),
        invoice_number=None,
        warranty_duration_months=int(row.warranty_duration_months),
    )

    warranty = Warranty(
        warranty_id=f"WAR-{row.claim_id}",
        product_id=product_id,
        provider="AssureX Warranty",
        start_date=purchase_date,
        end_date=date.fromisoformat(str(row.warranty_end_date)),
    )

    supplied_types = _parse_documents(row.documents_provided)
    documents = [
        _document_for(str(row.claim_id), claim_date, document_type)
        for document_type in supplied_types
    ]
    missing_documents = _missing_documents(supplied_types)

    repair_date: date | None = None
    if _is_present(row.get("repair_date", "")):
        repair_date = date.fromisoformat(str(row.repair_date))

    repair_count = int(row.repair_history_count)
    repairs = _repair_records(
        str(row.claim_id),
        product_id,
        purchase_date,
        claim_date,
        repair_count,
        repair_date,
    )

    damage_type = None
    if "damage_type" in row.index and _is_present(row.get("damage_type")):
        damage_type = str(row.damage_type)

    return Claim(
        claim_id=str(row.claim_id),
        customer_id=f"CUS-{row.claim_id}",
        product=product,
        warranty=warranty,
        fault_occurrence_date=(
            date.fromisoformat(str(row.fault_occurrence_date))
            if "fault_occurrence_date" in row.index and _is_present(row.get("fault_occurrence_date"))
            else None
        ),
        claim_submission_date=claim_date,
        fault_description=str(row.fault_type),
        fault_category=str(row.fault_type),
        damage_type=damage_type,
        previous_repairs=repairs,
        previous_replacement=False,
        submitted_documents=documents,
        missing_document_types=missing_documents,
        serial_number_match=bool(row.serial_number_match),
    )


def generate_cards(
    csv_path: str | Path = "data/claims.csv",
    output_root: str | Path = "data/claim_cards",
) -> dict[str, int]:
    """Render every CSV row into the SRS-required split/card layout."""
    frame = pd.read_csv(csv_path)
    builder = ClaimSummaryCardBuilder()
    counts = {"train": 0, "validation": 0, "test": 0}

    for _, row in frame.iterrows():
        claim = row_to_claim(row)
        split = str(row.split)
        label = str(row.class_label)
        card_data = builder.build_data(claim)
        variations = (1, 2) if split == "train" else (1,)
        for variation in variations:
            destination = Path(output_root) / split / label / f"{claim.claim_id}_v{variation}.jpg"
            builder.render(card_data, destination, variation=variation)
            counts[split] += 1
    return counts


if __name__ == "__main__":
    print(generate_cards())
