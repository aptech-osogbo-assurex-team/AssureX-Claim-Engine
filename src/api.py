"""FastAPI application for the AssureX claim evaluation workflow."""

from datetime import datetime, timezone
from pathlib import Path
import hashlib

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from src.auth_service import authenticate, register_user, resolve_token
from src.cards.generator import ClaimSummaryCardBuilder
from src.decision.engine import DecisionEngine
from src.documents.service import DocumentService
from src.documents.storage import DocumentStorage
from src.ocr.service import OCRService
from src.domain.auth import AuthResponse
from src.domain.enums import ClaimDecision, DocumentType, UserRole
from src.domain.schemas import Claim, ClaimSummaryCard, Document, FinalDecision, ModelPrediction
from src.ml.inference import PythonClaimPredictor
from src.persistence.database import build_session_factory
from src.persistence.models import AuditLogRecord, ClaimRecord, DecisionRecord, DocumentRecord, NotificationRecord, UserRecord
from src.rules.engine import RuleEngine
from src.services.evaluation import ClaimEvaluationService
from src.services.registration import ClaimRegistrationService


class EvaluateClaimRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: Claim
    teachable_machine_prediction: ModelPrediction


class RenderCardRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: Claim


class RenderCardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card: ClaimSummaryCard
    image_url: str


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=8)


class ReviewOverrideRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: ClaimDecision
    comments: str = Field(min_length=5, max_length=2000)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1)


app = FastAPI(title="AssureX Claim Engine", version="1.0.0")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = PROJECT_ROOT / "static"
CARD_ROOT = STATIC_ROOT / "cards"
CARD_ROOT.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "templates"))

predictor = PythonClaimPredictor(
    PROJECT_ROOT / "model/classifier.joblib",
    PROJECT_ROOT / "model/model_metadata.json",
    PROJECT_ROOT / "policies/warranty_policies.json",
)
rule_engine = RuleEngine(PROJECT_ROOT / "policies/warranty_policies.json")
decision_engine = DecisionEngine(PROJECT_ROOT / "policies/consistency_policy.json")
session_factory, _engine = build_session_factory(f"sqlite:///{PROJECT_ROOT / 'data/assurex.db'}")
evaluation_service = ClaimEvaluationService(predictor, rule_engine, decision_engine, session_factory)
card_builder = ClaimSummaryCardBuilder()
registration_service = ClaimRegistrationService(lambda: session_factory())
document_service = DocumentService(
    DocumentStorage(PROJECT_ROOT / "data/uploads"),
    OCRService(),
)
bearer = HTTPBearer(auto_error=False)


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> UserRecord:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="authentication required")
    session = session_factory()
    try:
        user = resolve_token(session, credentials.credentials)
        if user is None:
            raise HTTPException(status_code=401, detail="invalid or expired session")
        return user
    finally:
        session.close()


def can_access_claim(user: UserRecord, customer_id: str) -> bool:
    return user.user_id == customer_id or user.role in {UserRole.REVIEWER.value, UserRole.ADMIN.value}


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "project_title": "AssureX Claim Engine",
            "default_tm_model_url": "/static/teachable_machine/",
        },
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/register", response_model=AuthResponse, status_code=201)
def register(request: RegisterRequest) -> AuthResponse:
    session = session_factory()
    try:
        user = register_user(session, str(request.email), request.password, role=UserRole.CUSTOMER.value)
        user, token = authenticate(session, str(request.email), request.password)
        return AuthResponse(access_token=token, token_type="bearer", user_id=user.user_id, role=user.role)
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        session.close()


@app.post("/api/auth/login", response_model=AuthResponse)
def login(request: LoginRequest) -> AuthResponse:
    session = session_factory()
    try:
        user, token = authenticate(session, str(request.email), request.password)
        return AuthResponse(access_token=token, token_type="bearer", user_id=user.user_id, role=user.role)
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    finally:
        session.close()


@app.post("/api/claims/register", response_model=Claim, status_code=201)
def register_claim(request: RenderCardRequest, user: UserRecord = Depends(current_user)) -> Claim:
    if request.claim.customer_id != user.user_id:
        raise HTTPException(status_code=403, detail="claim does not belong to the authenticated user")
    try:
        return registration_service.register(request.claim)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Claim registration failed") from exc


@app.post("/api/claims/{claim_id}/documents", response_model=Document, status_code=201)
async def upload_claim_document(
    claim_id: str,
    document_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    user: UserRecord = Depends(current_user),
):
    session = session_factory()
    try:
        claim_record = session.query(ClaimRecord).filter_by(claim_id=claim_id).one_or_none()
        if claim_record is None:
            raise HTTPException(status_code=404, detail="claim not found")
        if not can_access_claim(user, claim_record.customer_id):
            raise HTTPException(status_code=403, detail="claim does not belong to the authenticated user")
        document = await document_service.ingest(claim_id, document_type, file)
        duplicate = (
            session.query(DocumentRecord)
            .filter(DocumentRecord.sha256 == document.sha256, DocumentRecord.document_id != document.document_id)
            .first()
            is not None
        )
        if duplicate:
            document.extracted_data = {**document.extracted_data, "duplicate_document_hash": True}
        session.add(
            DocumentRecord(
                document_id=document.document_id,
                claim_id=document.claim_id,
                document_type=document.document_type.value,
                filename=document.filename,
                mime_type=document.mime_type,
                size_bytes=document.size_bytes,
                sha256=document.sha256,
                uploaded_at=document.uploaded_at,
                verification_status=document.verification_status.value,
                extracted_data=document.extracted_data,
            )
        )
        session.add(AuditLogRecord(
            claim_id=claim_id,
            user_id=user.user_id,
            action="document_uploaded",
            details={"document_id": document.document_id, "document_type": document.document_type.value, "duplicate_hash": duplicate},
            created_at=datetime.now(timezone.utc),
        ))
        session.commit()
        return document
    except HTTPException:
        raise
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail="Document ingestion failed") from exc
    finally:
        session.close()


@app.post("/api/cards/render", response_model=RenderCardResponse)
def render_claim_card(request: RenderCardRequest, user: UserRecord = Depends(current_user)) -> RenderCardResponse:
    if not can_access_claim(user, request.claim.customer_id):
        raise HTTPException(status_code=403, detail="claim does not belong to the authenticated user")
    try:
        card = card_builder.build_data(request.claim)
        claim_key = hashlib.sha256(request.claim.claim_id.encode("utf-8")).hexdigest()[:20]
        output_path = CARD_ROOT / f"{claim_key}.jpg"
        card_builder.render(card, output_path, variation=1)
        return RenderCardResponse(card=card, image_url=f"/static/cards/{output_path.name}")
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/claims/{claim_id}/decision", response_model=FinalDecision)
def get_claim_decision(claim_id: str, user: UserRecord = Depends(current_user)) -> FinalDecision:
    session = session_factory()
    try:
        claim_record = session.query(ClaimRecord).filter_by(claim_id=claim_id).one_or_none()
        if claim_record is None:
            raise HTTPException(status_code=404, detail="claim not found")
        if not can_access_claim(user, claim_record.customer_id):
            raise HTTPException(status_code=403, detail="claim does not belong to the authenticated user")
        record = session.query(DecisionRecord).filter_by(claim_id=claim_id).one_or_none()
        if record is None:
            raise HTTPException(status_code=404, detail="no decision has been recorded for this claim")
        return FinalDecision.model_validate({
            "claim_id": record.claim_id,
            "decision": record.decision,
            "reasons": record.reasons,
            "supporting_factors": record.supporting_factors,
            "opposing_factors": record.opposing_factors,
            "evidence": record.evidence,
            "decided_at": record.decided_at,
            "reviewer_id": record.reviewer_id,
            "reviewer_comments": record.reviewer_comments,
            "override_applied": record.override_applied,
        })
    finally:
        session.close()


@app.post("/api/claims/{claim_id}/review", response_model=FinalDecision)
def review_claim(claim_id: str, request: ReviewOverrideRequest, user: UserRecord = Depends(current_user)) -> FinalDecision:
    if user.role not in {UserRole.REVIEWER.value, UserRole.ADMIN.value}:
        raise HTTPException(status_code=403, detail="reviewer privileges required")
    session = session_factory()
    try:
        claim_record = session.query(ClaimRecord).filter_by(claim_id=claim_id).one_or_none()
        record = session.query(DecisionRecord).filter_by(claim_id=claim_id).one_or_none()
        if claim_record is None or record is None:
            raise HTTPException(status_code=404, detail="claim decision not found")

        now = datetime.now(timezone.utc)
        record.decision = request.decision.value
        record.reviewer_id = user.user_id
        record.reviewer_comments = request.comments
        record.override_applied = True
        status = {
            ClaimDecision.LIKELY_VALID.value: "approved",
            ClaimDecision.LIKELY_INVALID.value: "rejected",
            ClaimDecision.MANUAL_REVIEW_REQUIRED.value: "manual_review",
        }[request.decision.value]
        claim_record.status = status
        session.add(
            AuditLogRecord(
                claim_id=claim_id,
                user_id=user.user_id,
                action="review_override",
                details={"decision": request.decision.value, "comments": request.comments},
                created_at=now,
            )
        )
        session.add(
            NotificationRecord(
                user_id=claim_record.customer_id,
                claim_id=claim_id,
                notification_type="review_decision",
                message=f"Claim {claim_id} was reviewed. Final result: {request.decision.value}.",
                is_read=False,
                created_at=now,
            )
        )
        session.commit()
        return FinalDecision.model_validate({
            "claim_id": record.claim_id,
            "decision": record.decision,
            "reasons": record.reasons,
            "supporting_factors": record.supporting_factors,
            "opposing_factors": record.opposing_factors,
            "evidence": record.evidence,
            "decided_at": record.decided_at,
            "reviewer_id": record.reviewer_id,
            "reviewer_comments": record.reviewer_comments,
            "override_applied": record.override_applied,
        })
    except HTTPException:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=500, detail="Review update failed") from exc
    finally:
        session.close()


@app.get("/api/notifications")
def get_notifications(user: UserRecord = Depends(current_user)) -> list[dict]:
    session = session_factory()
    try:
        rows = (
            session.query(NotificationRecord)
            .filter_by(user_id=user.user_id)
            .order_by(NotificationRecord.created_at.desc())
            .limit(50)
            .all()
        )
        return [
            {
                "id": row.id,
                "claim_id": row.claim_id,
                "notification_type": row.notification_type,
                "message": row.message,
                "is_read": row.is_read,
                "created_at": row.created_at,
            }
            for row in rows
        ]
    finally:
        session.close()


@app.post("/api/claims/evaluate", response_model=FinalDecision)
def evaluate_claim(request: EvaluateClaimRequest, user: UserRecord = Depends(current_user)) -> FinalDecision:
    if not can_access_claim(user, request.claim.customer_id):
        raise HTTPException(status_code=403, detail="claim does not belong to the authenticated user")
    try:
        return evaluation_service.evaluate(request.claim, request.teachable_machine_prediction)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Claim evaluation failed") from exc
