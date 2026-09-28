"""OCR and structured field extraction for warranty documents."""

from datetime import date, datetime
from pathlib import Path
import os
import re
import shutil

from PIL import Image
import pytesseract
from pdf2image import convert_from_path


class OCRService:
    """Extract text from supported receipt/invoice/warranty images and PDFs."""

    DATE_PATTERNS = (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d.%m.%Y",
    )

    def extract(self, path: str | Path) -> dict[str, object]:
        path = Path(path)
        suffix = path.suffix.lower()
        self._configure_tesseract()
        try:
            if suffix in {".jpg", ".jpeg", ".png"}:
                with Image.open(path) as image:
                    text = pytesseract.image_to_string(image)
            elif suffix == ".pdf":
                pages = convert_from_path(path, dpi=180, first_page=1, last_page=1)
                if not pages:
                    text = ""
                else:
                    text = pytesseract.image_to_string(pages[0])
            else:
                raise ValueError("OCR supports PDF, JPG, JPEG, and PNG files only.")
        except (pytesseract.TesseractNotFoundError, FileNotFoundError, OSError) as exc:
            return {
                "raw_text": "",
                "fields": self.extract_fields(""),
                "ocr_error": (
                    "Tesseract OCR is not installed or cannot be located. "
                    "Install Tesseract and optionally set TESSERACT_CMD. "
                    f"Details: {exc}"
                ),
            }

        return {
            "raw_text": text,
            "fields": self.extract_fields(text),
        }


    @staticmethod
    def _configure_tesseract() -> None:
        """Resolve the Tesseract executable on local Windows/Linux machines."""
        configured = os.getenv("TESSERACT_CMD")
        if configured:
            pytesseract.pytesseract.tesseract_cmd = configured
            return

        if shutil.which("tesseract"):
            return

        if os.name == "nt":
            for candidate in (
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            ):
                if Path(candidate).exists():
                    pytesseract.pytesseract.tesseract_cmd = candidate
                    return

    def extract_fields(self, text: str) -> dict[str, object]:
        cleaned = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        return {
            "purchase_date": self._find_date(cleaned, r"(?:purchase|bought|date)\s*[:#-]?\s*([0-9./-]{8,10})"),
            "invoice_number": self._find_value(cleaned, r"(?:invoice|receipt)\s*(?:no|number|#)?\s*[:#-]?\s*([A-Za-z0-9/-]{3,40})"),
            "serial_number": self._find_value(cleaned, r"(?:serial|s/n|sn)\s*(?:no|number)?\s*[:#-]?\s*([A-Za-z0-9-]{4,40})"),
            "model_number": self._find_value(cleaned, r"(?:model)\s*(?:no|number)?\s*[:#-]?\s*([A-Za-z0-9._/-]{2,40})"),
            "purchase_amount": self._find_float(cleaned, r"(?:total|amount|price)\s*[:#-]?\s*([0-9,]+(?:\.\d{1,2})?)"),
            "warranty_duration_months": self._find_int(cleaned, r"(?:warranty)\s*(?:period|duration)?\s*[:#-]?\s*(\d{1,2})\s*(?:month|months)"),
            "product_name": self._find_value(cleaned, r"(?:product|item)\s*(?:name)?\s*[:#-]?\s*([^\n]{2,100})"),
            "retailer": self._find_value(cleaned, r"(?:retailer|seller|store)\s*[:#-]?\s*([^\n]{2,100})"),
        }

    @classmethod
    def _find_value(cls, text: str, pattern: str) -> str | None:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        return match.group(1).strip() if match else None

    @classmethod
    def _find_date(cls, text: str, pattern: str) -> str | None:
        raw = cls._find_value(text, pattern)
        if not raw:
            return None
        for fmt in cls.DATE_PATTERNS:
            try:
                return datetime.strptime(raw, fmt).date().isoformat()
            except ValueError:
                continue
        return raw

    @classmethod
    def _find_float(cls, text: str, pattern: str) -> float | None:
        raw = cls._find_value(text, pattern)
        if not raw:
            return None
        try:
            return float(raw.replace(",", ""))
        except ValueError:
            return None

    @classmethod
    def _find_int(cls, text: str, pattern: str) -> int | None:
        raw = cls._find_value(text, pattern)
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            return None
