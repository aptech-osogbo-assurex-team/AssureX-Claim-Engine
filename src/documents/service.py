"""Document ingestion service combining secure storage and OCR."""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile

from src.domain.enums import DocumentType
from src.domain.schemas import Document

from .storage import DocumentStorage
from src.ocr.service import OCRService


class DocumentService:
    def __init__(self, storage: DocumentStorage, ocr: OCRService):
        self.storage = storage
        self.ocr = ocr

    async def ingest(self, claim_id: str, document_type: DocumentType, upload: UploadFile) -> Document:
        path, digest, size = await self.storage.save_upload(upload)
        try:
            extracted = self.ocr.extract(path)
        except Exception:
            extracted = {"ocr_error": "Document text extraction failed or is unavailable."}

        return Document(
            document_id=path.stem,
            claim_id=claim_id,
            document_type=document_type,
            filename=upload.filename or path.name,
            mime_type=upload.content_type or "application/octet-stream",
            size_bytes=size,
            sha256=digest,
            uploaded_at=datetime.now(timezone.utc),
            extracted_data=extracted,
        )
