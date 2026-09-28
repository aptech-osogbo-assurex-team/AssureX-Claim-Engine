from datetime import date, datetime, timezone

from PIL import Image

from src.cards.generator import ClaimSummaryCardBuilder
from src.domain.enums import DocumentType
from src.domain.schemas import Claim, Document, Product, Warranty


def make_claim() -> Claim:
    product = Product(
        product_id="PRD-CARD-001",
        product_name="Laptop",
        category="Electronics",
        brand="Vertex",
        model_number="VT-15Pro",
        serial_number="SN12345678",
        purchase_date=date(2025, 1, 10),
        purchase_price=900.0,
        retailer="TechHub Store",
        warranty_duration_months=24,
    )
    warranty = Warranty(
        warranty_id="WAR-CARD-001",
        product_id=product.product_id,
        provider="AssureX",
        start_date=product.purchase_date,
        end_date=date(2027, 1, 10),
    )
    docs = [
        Document(
            document_id="D1",
            claim_id="CLM-CARD-001",
            document_type=DocumentType.RECEIPT,
            filename="receipt.pdf",
            mime_type="application/pdf",
            size_bytes=10,
            sha256="a" * 64,
            uploaded_at=datetime.now(timezone.utc),
        ),
        Document(
            document_id="D2",
            claim_id="CLM-CARD-001",
            document_type=DocumentType.WARRANTY_CARD,
            filename="warranty.pdf",
            mime_type="application/pdf",
            size_bytes=10,
            sha256="b" * 64,
            uploaded_at=datetime.now(timezone.utc),
        ),
        Document(
            document_id="D3",
            claim_id="CLM-CARD-001",
            document_type=DocumentType.PRODUCT_PHOTO,
            filename="product.png",
            mime_type="image/png",
            size_bytes=10,
            sha256="c" * 64,
            uploaded_at=datetime.now(timezone.utc),
        ),
        Document(
            document_id="D4",
            claim_id="CLM-CARD-001",
            document_type=DocumentType.SERIAL_EVIDENCE,
            filename="serial.png",
            mime_type="image/png",
            size_bytes=10,
            sha256="d" * 64,
            uploaded_at=datetime.now(timezone.utc),
        ),
        Document(
            document_id="D5",
            claim_id="CLM-CARD-001",
            document_type=DocumentType.FAULT_EVIDENCE,
            filename="fault.png",
            mime_type="image/png",
            size_bytes=10,
            sha256="e" * 64,
            uploaded_at=datetime.now(timezone.utc),
        ),
    ]
    return Claim(
        claim_id="CLM-CARD-001",
        customer_id="CUS-CARD-001",
        product=product,
        warranty=warranty,
        claim_submission_date=date(2026, 1, 10),
        fault_description="Display failure",
        fault_category="Display fault",
        submitted_documents=docs,
        serial_number_match=True,
    )


def test_card_data_contains_required_evidence_and_no_prediction() -> None:
    card = ClaimSummaryCardBuilder().build_data(make_claim())
    payload = card.model_dump(mode="json")

    assert payload["claim_id"] == "CLM-CARD-001"
    assert payload["receipt_available"] is True
    assert payload["warranty_card_available"] is True
    assert payload["serial_number_match"] is True
    assert "predicted_class" not in payload
    assert "confidence" not in payload
    assert "decision" not in payload


def test_card_rendering_creates_valid_png(tmp_path) -> None:
    builder = ClaimSummaryCardBuilder()
    card = builder.build_data(make_claim())
    output = builder.render(card, tmp_path / "card.jpg", variation=2)

    assert output.exists()
    with Image.open(output) as image:
        assert image.size == (1200, 720)
        assert image.format == "JPEG"
