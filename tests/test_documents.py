from io import BytesIO
from pathlib import Path

from fastapi import UploadFile
from PIL import Image, ImageDraw
import pytest

from src.documents.storage import DocumentStorage
from src.ocr.service import OCRService


@pytest.mark.anyio
async def test_storage_hashes_and_limits_upload(tmp_path: Path) -> None:
    image = Image.new("RGB", (600, 220), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), "Serial: SN12345678", fill="black")
    payload = BytesIO()
    image.save(payload, format="PNG")
    payload.seek(0)

    upload = UploadFile(filename="serial.png", file=payload, headers={"content-type": "image/png"})
    storage = DocumentStorage(tmp_path, max_size_bytes=2 * 1024 * 1024)
    path, digest, size = await storage.save_upload(upload)

    assert path.exists()
    assert len(digest) == 64
    assert size > 0


@pytest.mark.anyio
async def test_storage_rejects_extension_mismatch(tmp_path: Path) -> None:
    upload = UploadFile(filename="serial.pdf", file=BytesIO(b"not really a pdf"), headers={"content-type": "image/png"})
    storage = DocumentStorage(tmp_path)
    with pytest.raises(ValueError, match="extension"):
        await storage.save_upload(upload)


def test_ocr_field_parser() -> None:
    text = """
    Invoice No: INV-2048
    Serial: SN12345678
    Model: VT-15Pro
    Purchase Date: 15/06/2025
    Total: 950,000.50
    Warranty: 24 months
    Product Name: Vertex Laptop
    Retailer: TechHub Store
    """
    fields = OCRService().extract_fields(text)
    assert fields["invoice_number"] == "INV-2048"
    assert fields["serial_number"] == "SN12345678"
    assert fields["model_number"] == "VT-15Pro"
    assert fields["purchase_date"] == "2025-06-15"
    assert fields["purchase_amount"] == 950000.50
    assert fields["warranty_duration_months"] == 24
    assert fields["product_name"] == "Vertex Laptop"
    assert fields["retailer"] == "TechHub Store"
