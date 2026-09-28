"""Deterministic visual Claim Summary Card generation."""

from datetime import datetime, timezone
from pathlib import Path
from functools import lru_cache
import os
import sys

from PIL import Image, ImageDraw, ImageFont

from src.domain.enums import DocumentType
from src.domain.schemas import Claim, ClaimSummaryCard


class ClaimSummaryCardBuilder:
    """Create the evidence-only card required by the SRS.

    The card never renders model predictions, confidence scores, or the final
    decision. Dataset labels are kept in the surrounding directory structure.
    """

    CARD_VERSION = "1.0.0"
    WIDTH = 1200
    HEIGHT = 720

    def build_data(self, claim: Claim) -> ClaimSummaryCard:
        submission = claim.claim_submission_date
        purchase = claim.product.purchase_date
        remaining = (claim.warranty.end_date - submission).days
        warranty_status = self._warranty_status(claim, remaining)
        docs = {document.document_type for document in claim.submitted_documents}
        missing = self._missing_documents(claim)

        return ClaimSummaryCard(
            claim_id=claim.claim_id,
            card_version=self.CARD_VERSION,
            product_age_days=(submission - purchase).days,
            warranty_status=warranty_status,
            remaining_warranty_days=remaining,
            fault_category=claim.fault_category,
            repair_history_count=len(claim.previous_repairs),
            receipt_available=(DocumentType.RECEIPT in docs or DocumentType.INVOICE in docs),
            warranty_card_available=DocumentType.WARRANTY_CARD in docs,
            serial_number_match=claim.serial_number_match,
            missing_documents=missing,
            damage_type=claim.damage_type,
            generated_at=datetime.now(timezone.utc),
        )

    def render(self, card: ClaimSummaryCard, destination: str | Path, variation: int = 1) -> Path:
        if variation not in (1, 2):
            raise ValueError("variation must be 1 or 2")

        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        image = Image.new("RGB", (self.WIDTH, self.HEIGHT), "white")
        draw = ImageDraw.Draw(image)
        font_regular, font_bold = self._fonts(variation)

        margin = 55 if variation == 1 else 60
        row_height = 49 if variation == 1 else 45
        draw.rectangle((margin, margin, self.WIDTH - margin, self.HEIGHT - margin), outline="black", width=3)
        draw.text((margin + 28, margin + 22), "ASSUREX CLAIM SUMMARY", fill="black", font=font_bold)
        draw.text((margin + 28, margin + 66), f"Claim ID: {card.claim_id}", fill="black", font=font_regular)

        rows = [
            ("Product age (days)", str(card.product_age_days)),
            ("Warranty status", card.warranty_status),
            ("Remaining warranty (days)", str(card.remaining_warranty_days) if card.remaining_warranty_days is not None else "N/A"),
            ("Fault category", card.fault_category),
            ("Repair history count", str(card.repair_history_count)),
            ("Receipt / invoice", "Available" if card.receipt_available else "Missing"),
            ("Warranty card", "Available" if card.warranty_card_available else "Missing"),
            ("Serial number status", self._serial_status(card.serial_number_match)),
            ("Missing documents", self._missing_label(card.missing_documents)),
        ]
        if card.damage_type:
            rows.append(("Damage type", card.damage_type))

        y = margin + 125
        split_x = self.WIDTH // 2
        for index, (label, value) in enumerate(rows):
            if index == 5 and variation == 2:
                y += 10
            draw.text((margin + 28, y), label, fill="black", font=font_bold)
            draw.text((split_x, y), value, fill="black", font=font_regular)
            y += row_height

        # No class label or decision result is rendered anywhere on the card.
        suffix = destination.suffix.lower()
        if suffix in {".jpg", ".jpeg"}:
            image.save(destination, format="JPEG", quality=88, optimize=True)
        else:
            image.save(destination, format="PNG", optimize=True)
        return destination

    @staticmethod
    @lru_cache(maxsize=2)
    def _fonts(variation: int):
        """Load portable regular/bold fonts across Windows/Linux environments."""
        regular_size = 24 if variation == 1 else 21
        bold_size = 30 if variation == 1 else 27

        candidates = []
        if sys.platform == "win32":
            candidates.extend([
                (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
                (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\segoeuib.ttf"),
            ])
        else:
            candidates.extend([
                ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
                ("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
                 "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
            ])

        regular_override = os.getenv("ASSUREX_FONT_REGULAR")
        bold_override = os.getenv("ASSUREX_FONT_BOLD")
        if regular_override and bold_override:
            candidates.insert(0, (regular_override, bold_override))

        for regular_path, bold_path in candidates:
            if Path(regular_path).exists() and Path(bold_path).exists():
                return (
                    ImageFont.truetype(regular_path, regular_size),
                    ImageFont.truetype(bold_path, bold_size),
                )

        # Last-resort fallback keeps card generation usable in stripped-down
        # environments where no system TrueType font is available.
        return ImageFont.load_default(), ImageFont.load_default()

    @staticmethod
    def _warranty_status(claim: Claim, remaining_days: int) -> str:
        if claim.warranty.extended and remaining_days >= 0:
            return "extended_active"
        if remaining_days >= 0:
            return "active"
        return "expired"

    @staticmethod
    def _serial_status(value: bool | None) -> str:
        if value is True:
            return "Match"
        if value is False:
            return "Mismatch"
        return "Unknown"

    @staticmethod
    def _missing_label(values: list[DocumentType]) -> str:
        if not values:
            return "None"
        return ", ".join(value.value for value in values)

    @staticmethod
    def _missing_documents(claim: Claim) -> list[DocumentType]:
        required = [
            (DocumentType.RECEIPT, DocumentType.INVOICE),
            (DocumentType.WARRANTY_CARD,),
            (DocumentType.PRODUCT_PHOTO,),
            (DocumentType.SERIAL_EVIDENCE,),
            (DocumentType.FAULT_EVIDENCE,),
        ]
        submitted = {document.document_type for document in claim.submitted_documents}
        missing = list(claim.missing_document_types)
        for group in required:
            if not any(item in submitted for item in group):
                candidate = group[0]
                if candidate not in missing:
                    missing.append(candidate)
        return missing
