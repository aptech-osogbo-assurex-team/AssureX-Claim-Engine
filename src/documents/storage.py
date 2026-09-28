"""Secure local document storage with type, size, and hash validation."""

from hashlib import sha256
from pathlib import Path
import secrets

from fastapi import UploadFile


ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}
DEFAULT_MAX_SIZE_BYTES = 10 * 1024 * 1024


class DocumentStorage:
    def __init__(self, root: str | Path = "data/uploads", max_size_bytes: int = DEFAULT_MAX_SIZE_BYTES):
        self.root = Path(root)
        self.max_size_bytes = max_size_bytes
        self.root.mkdir(parents=True, exist_ok=True)

    async def save_upload(self, upload: UploadFile) -> tuple[Path, str, int]:
        mime_type = (upload.content_type or "").lower()
        extension = Path(upload.filename or "").suffix.lower()
        if mime_type not in ALLOWED_MIME_TYPES or extension not in ALLOWED_EXTENSIONS:
            raise ValueError("Unsupported document type. Allowed formats: PDF, JPG, JPEG, PNG.")
        expected_extension = ALLOWED_MIME_TYPES[mime_type]
        if extension != expected_extension and not (mime_type == "image/jpeg" and extension == ".jpeg"):
            raise ValueError("File extension does not match its MIME type.")

        token = secrets.token_hex(16)
        destination = self.root / f"{token}{extension}"
        digest = sha256()
        total = 0
        try:
            with destination.open("wb") as handle:
                while True:
                    chunk = await upload.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > self.max_size_bytes:
                        raise ValueError("Document exceeds the maximum allowed size of 10 MB.")
                    digest.update(chunk)
                    handle.write(chunk)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()

        if total == 0:
            destination.unlink(missing_ok=True)
            raise ValueError("Uploaded document is empty.")
        return destination, digest.hexdigest(), total
