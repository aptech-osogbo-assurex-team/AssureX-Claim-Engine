from datetime import datetime, timezone

import pytest
from PIL import Image, ImageDraw

from fastapi.testclient import TestClient

import src.api as api
from src.api import app, evaluation_service
from src.persistence.database import build_session_factory
from src.persistence.models import AuditLogRecord, ClaimRecord, DecisionRecord, NotificationRecord, PredictionRecord, RuleResultRecord, UserRecord

client = TestClient(app)


def tm_prediction() -> dict:
    return {
        "model_name": "TeachableMachine",
        "model_version": "tm-test-1.0.0",
        "predicted_class": "valid_claim",
        "confidence": 0.88,
        "probabilities": {
            "valid_claim": 0.88,
            "invalid_claim": 0.06,
            "manual_review": 0.06,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _login_for_test(monkeypatch, tmp_path) -> str:
    factory, _ = build_session_factory(f"sqlite:///{tmp_path / 'auth.db'}")
    monkeypatch.setattr(api, "session_factory", factory)
    response = client.post(
        "/api/auth/register",
        json={"email": "tester@example.com", "password": "TestPassword123"},
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def claim_payload() -> dict:
    return {
        "claim_id": "CLM-API-001",
        "customer_id": "CUS-API-001",
        "product": {
            "product_id": "PRD-API-001",
            "product_name": "Laptop",
            "category": "Electronics",
            "brand": "Vertex",
            "model_number": "VT-15Pro",
            "serial_number": "SN12345678",
            "purchase_date": "2025-01-10",
            "purchase_price": 900.0,
            "retailer": "TechHub Store",
            "invoice_number": "INV-API-001",
            "warranty_duration_months": 24,
        },
        "warranty": {
            "warranty_id": "WAR-API-001",
            "product_id": "PRD-API-001",
            "provider": "AssureX Warranty",
            "start_date": "2025-01-10",
            "end_date": "2027-01-10",
        },
        "fault_occurrence_date": "2025-06-01",
        "claim_submission_date": "2025-06-15",
        "fault_description": "Screen does not power on",
        "fault_category": "Display fault",
        "serial_number_match": True,
    }


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_auth_register_and_login(monkeypatch, tmp_path) -> None:
    factory, _ = build_session_factory(f"sqlite:///{tmp_path / 'auth.db'}")
    monkeypatch.setattr(api, "session_factory", factory)

    register_response = client.post(
        "/api/auth/register",
        json={"email": "tester@example.com", "password": "TestPassword123"},
    )
    assert register_response.status_code == 201, register_response.text
    registered = register_response.json()
    assert registered["access_token"]
    assert registered["role"] == "customer"

    login_response = client.post(
        "/api/auth/login",
        json={"email": "tester@example.com", "password": "TestPassword123"},
    )
    assert login_response.status_code == 200, login_response.text
    assert login_response.json()["access_token"]


def test_auth_required_for_claim_routes(monkeypatch, tmp_path) -> None:
    factory, _ = build_session_factory(f"sqlite:///{tmp_path / 'auth.db'}")
    monkeypatch.setattr(api, "session_factory", factory)
    response = client.post("/api/cards/render", json={"claim": claim_payload()})
    assert response.status_code == 401


def test_real_evaluation_route_runs_end_to_end(monkeypatch, tmp_path) -> None:
    factory, _ = build_session_factory(f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setattr(api, "session_factory", factory)
    monkeypatch.setattr(evaluation_service, "session_factory", factory)

    auth = client.post(
        "/api/auth/register",
        json={"email": "tester2@example.com", "password": "TestPassword123"},
    )
    assert auth.status_code == 201, auth.text
    token = auth.json()["access_token"]
    payload = claim_payload()
    payload["customer_id"] = auth.json()["user_id"]

    response = client.post(
        "/api/claims/evaluate",
        json={"claim": payload, "teachable_machine_prediction": tm_prediction()},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["claim_id"] == "CLM-API-001"
    assert body["decision"] in {"likely_valid", "manual_review_required", "likely_invalid"}
    assert "python_prediction" in body["evidence"]
    assert "teachable_machine_prediction" in body["evidence"]
    expected_difference = abs(body["evidence"]["python_prediction"]["confidence"] - 0.88)
    assert body["evidence"]["confidence_difference"] == pytest.approx(expected_difference)
    assert body["decision"] == "manual_review_required"

    session = factory()
    try:
        assert session.query(DecisionRecord).filter_by(claim_id="CLM-API-001").one().decision == body["decision"]
        assert session.query(PredictionRecord).filter_by(claim_id="CLM-API-001").count() == 2
        assert session.query(RuleResultRecord).filter_by(claim_id="CLM-API-001").count() > 0
        assert session.query(AuditLogRecord).filter_by(claim_id="CLM-API-001").count() == 1
        assert session.query(NotificationRecord).filter_by(claim_id="CLM-API-001").count() == 1
        assert session.query(ClaimRecord).filter_by(claim_id="CLM-API-001").one().status == "manual_review"
    finally:
        session.close()


def test_render_card_route(monkeypatch, tmp_path) -> None:
    factory, _ = build_session_factory(f"sqlite:///{tmp_path / 'card.db'}")
    monkeypatch.setattr(api, "session_factory", factory)
    auth = client.post(
        "/api/auth/register",
        json={"email": "cards@example.com", "password": "TestPassword123"},
    )
    token = auth.json()["access_token"]
    payload = claim_payload()
    payload["customer_id"] = auth.json()["user_id"]
    response = client.post(
        "/api/cards/render",
        json={"claim": payload},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["card"]["claim_id"] == "CLM-API-001"
    assert body["card"]["remaining_warranty_days"] == 574
    assert body["image_url"].startswith("/static/cards/")


def test_home_page() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "AssureX Claim Engine" in response.text
    assert "Teachable Machine model base URL" in response.text
    assert "Register" in response.text


def test_claim_registration_and_document_upload(monkeypatch, tmp_path) -> None:
    factory, _ = build_session_factory(f"sqlite:///{tmp_path / 'evidence.db'}")
    monkeypatch.setattr(api, "session_factory", factory)

    auth = client.post(
        "/api/auth/register",
        json={"email": "evidence@example.com", "password": "TestPassword123"},
    )
    assert auth.status_code == 201, auth.text
    token = auth.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    payload = claim_payload()
    payload["claim_id"] = "CLM-EVIDENCE-001"
    payload["customer_id"] = auth.json()["user_id"]

    registered = client.post("/api/claims/register", json={"claim": payload}, headers=headers)
    assert registered.status_code == 201, registered.text

    image = Image.new("RGB", (700, 220), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 40), "Serial: SN12345678", fill="black")
    data = __import__("io").BytesIO()
    image.save(data, format="PNG")
    data.seek(0)

    upload = client.post(
        "/api/claims/CLM-EVIDENCE-001/documents",
        data={"document_type": "serial_evidence"},
        files={"file": ("serial.png", data, "image/png")},
        headers=headers,
    )
    assert upload.status_code == 201, upload.text
    document = upload.json()
    assert document["claim_id"] == "CLM-EVIDENCE-001"
    assert document["sha256"]
    assert "raw_text" in document["extracted_data"]
    assert "fields" in document["extracted_data"]


def test_claim_ownership_is_enforced(monkeypatch, tmp_path) -> None:
    factory, _ = build_session_factory(f"sqlite:///{tmp_path / 'ownership.db'}")
    monkeypatch.setattr(api, "session_factory", factory)
    first = client.post("/api/auth/register", json={"email": "owner1@example.com", "password": "TestPassword123"})
    second = client.post("/api/auth/register", json={"email": "owner2@example.com", "password": "TestPassword123"})
    owner_headers = {"Authorization": f"Bearer {first.json()['access_token']}"}
    other_headers = {"Authorization": f"Bearer {second.json()['access_token']}"}

    payload = claim_payload()
    payload["claim_id"] = "CLM-OWNERSHIP-001"
    payload["customer_id"] = first.json()["user_id"]
    registered = client.post("/api/claims/register", json={"claim": payload}, headers=owner_headers)
    assert registered.status_code == 201, registered.text

    denied = client.post("/api/cards/render", json={"claim": payload}, headers=other_headers)
    assert denied.status_code == 403


def test_reviewer_override_and_decision_retrieval(monkeypatch, tmp_path) -> None:
    factory, _ = build_session_factory(f"sqlite:///{tmp_path / 'review.db'}")
    monkeypatch.setattr(api, "session_factory", factory)
    monkeypatch.setattr(evaluation_service, "session_factory", factory)

    customer = client.post(
        "/api/auth/register",
        json={"email": "customer-review@example.com", "password": "TestPassword123"},
    )
    assert customer.status_code == 201
    customer_id = customer.json()["user_id"]

    from src.auth_service import hash_password
    session = factory()
    try:
        reviewer = UserRecord(
            user_id="USR-REVIEWER-001",
            email="reviewer@example.com",
            role="reviewer",
            password_hash=hash_password("ReviewerPass123"),
            created_at=datetime.now(timezone.utc),
        )
        session.add(reviewer)
        session.commit()
    finally:
        session.close()

    reviewer_login = client.post(
        "/api/auth/login",
        json={"email": "reviewer@example.com", "password": "ReviewerPass123"},
    )
    assert reviewer_login.status_code == 200, reviewer_login.text
    reviewer_headers = {"Authorization": f"Bearer {reviewer_login.json()['access_token']}"}
    customer_headers = {"Authorization": f"Bearer {customer.json()['access_token']}"}

    payload = claim_payload()
    payload["claim_id"] = "CLM-REVIEW-001"
    payload["customer_id"] = customer_id
    registered = client.post("/api/claims/register", json={"claim": payload}, headers=customer_headers)
    assert registered.status_code == 201, registered.text

    eval_response = client.post(
        "/api/claims/evaluate",
        json={"claim": payload, "teachable_machine_prediction": tm_prediction()},
        headers=customer_headers,
    )
    assert eval_response.status_code == 200, eval_response.text

    override = client.post(
        "/api/claims/CLM-REVIEW-001/review",
        json={"decision": "likely_valid", "comments": "Reviewer verified the claim evidence and approved it."},
        headers=reviewer_headers,
    )
    assert override.status_code == 200, override.text
    body = override.json()
    assert body["decision"] == "likely_valid"
    assert body["override_applied"] is True
    assert body["reviewer_id"] == "USR-REVIEWER-001"

    fetched = client.get("/api/claims/CLM-REVIEW-001/decision", headers=customer_headers)
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["decision"] == "likely_valid"

    notifications = client.get("/api/notifications", headers=customer_headers)
    assert notifications.status_code == 200, notifications.text
    assert any(item["claim_id"] == "CLM-REVIEW-001" for item in notifications.json())

    session = factory()
    try:
        assert session.query(ClaimRecord).filter_by(claim_id="CLM-REVIEW-001").one().status == "approved"
        assert session.query(AuditLogRecord).filter_by(claim_id="CLM-REVIEW-001", action="review_override").count() == 1
    finally:
        session.close()


def test_duplicate_claim_detection_escalates_to_manual_review(monkeypatch, tmp_path) -> None:
    factory, _ = build_session_factory(f"sqlite:///{tmp_path / 'duplicate.db'}")
    monkeypatch.setattr(api, "session_factory", factory)
    monkeypatch.setattr(evaluation_service, "session_factory", factory)
    auth = client.post(
        "/api/auth/register",
        json={"email": "duplicate@example.com", "password": "TestPassword123"},
    )
    assert auth.status_code == 201, auth.text
    token = auth.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    owner_id = auth.json()["user_id"]

    first = claim_payload()
    first["claim_id"] = "CLM-DUP-001"
    first["customer_id"] = owner_id
    assert client.post("/api/claims/register", json={"claim": first}, headers=headers).status_code == 201
    first_eval = client.post(
        "/api/claims/evaluate",
        json={"claim": first, "teachable_machine_prediction": tm_prediction()},
        headers=headers,
    )
    assert first_eval.status_code == 200, first_eval.text

    second = claim_payload()
    second["claim_id"] = "CLM-DUP-002"
    second["customer_id"] = owner_id
    second_eval = client.post(
        "/api/claims/evaluate",
        json={"claim": second, "teachable_machine_prediction": tm_prediction()},
        headers=headers,
    )
    assert second_eval.status_code == 200, second_eval.text
    assert second_eval.json()["decision"] == "manual_review_required"
    assert second_eval.json()["evidence"]["duplicate_flag"] is True

    session = factory()
    try:
        assert session.query(ClaimRecord).filter_by(claim_id="CLM-DUP-002").one().duplicate_claim is True
    finally:
        session.close()


def test_product_ownership_cannot_be_reassigned(monkeypatch, tmp_path) -> None:
    factory, _ = build_session_factory(f"sqlite:///{tmp_path / 'product-owner.db'}")
    monkeypatch.setattr(api, "session_factory", factory)

    owner = client.post("/api/auth/register", json={"email": "product-owner@example.com", "password": "TestPassword123"})
    attacker = client.post("/api/auth/register", json={"email": "product-other@example.com", "password": "TestPassword123"})
    owner_headers = {"Authorization": f"Bearer {owner.json()['access_token']}"}
    attacker_headers = {"Authorization": f"Bearer {attacker.json()['access_token']}"}

    product = claim_payload()
    product["claim_id"] = "CLM-PRODUCT-OWNER-001"
    product["customer_id"] = owner.json()["user_id"]
    assert client.post("/api/claims/register", json={"claim": product}, headers=owner_headers).status_code == 201

    forged = claim_payload()
    forged["claim_id"] = "CLM-PRODUCT-OWNER-002"
    forged["customer_id"] = attacker.json()["user_id"]
    forged["product"]["serial_number"] = "FORGED-SERIAL"
    rejected = client.post("/api/claims/register", json={"claim": forged}, headers=attacker_headers)
    assert rejected.status_code == 400
    assert "does not belong" in rejected.json()["detail"]
