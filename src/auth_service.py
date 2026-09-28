"""Small dependency-free authentication service for the AssureX prototype."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import secrets
import uuid

from sqlalchemy.orm import Session

from src.persistence.models import SessionRecord, UserRecord

ITERATIONS = 310_000
TOKEN_TTL_HOURS = 12


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("password must contain at least 8 characters")
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(derived).decode()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, derived_text = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_text)
        salt = base64.urlsafe_b64decode(salt_text.encode())
        expected = base64.urlsafe_b64decode(derived_text.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def register_user(session: Session, email: str, password: str, role: str = "customer") -> UserRecord:
    normalized_email = email.strip().lower()
    if not normalized_email or "@" not in normalized_email:
        raise ValueError("a valid email address is required")
    if session.query(UserRecord).filter_by(email=normalized_email).first() is not None:
        raise ValueError("an account with this email already exists")
    now = datetime.now(timezone.utc)
    user = UserRecord(
        user_id=f"USR-{uuid.uuid4().hex[:16].upper()}",
        email=normalized_email,
        role=role,
        password_hash=hash_password(password),
        created_at=now,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def authenticate(session: Session, email: str, password: str) -> tuple[UserRecord, str]:
    normalized_email = email.strip().lower()
    user = session.query(UserRecord).filter_by(email=normalized_email).first()
    if user is None or not verify_password(password, user.password_hash):
        raise ValueError("invalid email or password")
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)
    session.add(
        SessionRecord(
            session_id=f"SES-{uuid.uuid4().hex[:20].upper()}",
            user_id=user.user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked=False,
        )
    )
    session.commit()
    return user, raw_token


def resolve_token(session: Session, raw_token: str) -> UserRecord | None:
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    record = (
        session.query(SessionRecord)
        .filter_by(token_hash=token_hash, revoked=False)
        .first()
    )
    if record is None:
        return None
    now = datetime.now(timezone.utc)
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        record.revoked = True
        session.commit()
        return None
    return session.query(UserRecord).filter_by(user_id=record.user_id).one_or_none()
