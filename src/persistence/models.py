"""Relational persistence models for AssureX claim records and audit data."""

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


class UserRecord(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class SessionRecord(Base):
    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ProductRecord(Base):
    __tablename__ = "products"

    product_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id"), nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    brand: Mapped[str] = mapped_column(String(100), nullable=False)
    model_number: Mapped[str] = mapped_column(String(100), nullable=False)
    serial_number: Mapped[str] = mapped_column(String(100), nullable=False)
    purchase_date: Mapped[Any] = mapped_column(Date, nullable=False)
    purchase_price: Mapped[float] = mapped_column(Float, nullable=False)
    retailer: Mapped[str] = mapped_column(String(255), nullable=False)
    invoice_number: Mapped[str | None] = mapped_column(String(100))
    warranty_duration_months: Mapped[int] = mapped_column(Integer, nullable=False)


class WarrantyRecord(Base):
    __tablename__ = "warranties"

    warranty_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.product_id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[Any] = mapped_column(Date, nullable=False)
    end_date: Mapped[Any] = mapped_column(Date, nullable=False)
    coverage_conditions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    exclusions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    service_center: Mapped[str | None] = mapped_column(String(255))
    extended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reporting_deadline_days: Mapped[int | None] = mapped_column(Integer)
    grace_period_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mandatory_document_types: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class ClaimRecord(Base):
    __tablename__ = "claims"

    claim_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id"), nullable=False)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.product_id"), nullable=False)
    warranty_id: Mapped[str] = mapped_column(String(64), ForeignKey("warranties.warranty_id"), nullable=False)
    fault_occurrence_date: Mapped[Any | None] = mapped_column(Date)
    claim_submission_date: Mapped[Any] = mapped_column(Date, nullable=False)
    fault_description: Mapped[str] = mapped_column(Text, nullable=False)
    fault_category: Mapped[str] = mapped_column(String(255), nullable=False)
    damage_type: Mapped[str | None] = mapped_column(String(255))
    previous_replacement: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    previous_replacement_details: Mapped[str | None] = mapped_column(Text)
    serial_number_match: Mapped[bool | None] = mapped_column(Boolean)
    duplicate_claim: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    missing_document_types: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)


class DocumentRecord(Base):
    __tablename__ = "documents"

    document_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    claim_id: Mapped[str] = mapped_column(String(64), ForeignKey("claims.claim_id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False)
    extracted_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class RepairRecordDB(Base):
    __tablename__ = "repairs"

    repair_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    product_id: Mapped[str] = mapped_column(String(64), ForeignKey("products.product_id"), nullable=False)
    repair_date: Mapped[Any] = mapped_column(Date, nullable=False)
    repair_center: Mapped[str] = mapped_column(String(255), nullable=False)
    replaced_parts: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    repair_cost: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    authorized: Mapped[str] = mapped_column(String(32), nullable=False)


class PredictionRecord(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    claim_id: Mapped[str] = mapped_column(String(64), ForeignKey("claims.claim_id"), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    predicted_class: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    probabilities: Mapped[dict[str, float]] = mapped_column(JSON, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class RuleResultRecord(Base):
    __tablename__ = "rule_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    claim_id: Mapped[str] = mapped_column(String(64), ForeignKey("claims.claim_id"), nullable=False, index=True)
    rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class DecisionRecord(Base):
    __tablename__ = "decisions"

    claim_id: Mapped[str] = mapped_column(String(64), ForeignKey("claims.claim_id"), primary_key=True)
    decision: Mapped[str] = mapped_column(String(64), nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    supporting_factors: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    opposing_factors: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    reviewer_id: Mapped[str | None] = mapped_column(String(64))
    reviewer_comments: Mapped[str | None] = mapped_column(Text)
    override_applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class AuditLogRecord(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    claim_id: Mapped[str | None] = mapped_column(String(64), index=True)
    user_id: Mapped[str | None] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class NotificationRecord(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    claim_id: Mapped[str | None] = mapped_column(String(64), index=True)
    notification_type: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
