"""Backend API foundation tests."""

from datetime import datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import session_scope
from app.main import app
from app.models import Claim
from app.services.queue import QueueUnavailableError
from redis.exceptions import ConnectionError as RedisConnectionError

client = TestClient(app)


def test_health_endpoints_succeed() -> None:
    for path in ("/health", "/api/v1/health"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert response.headers.get("X-Request-ID")


def test_frontend_origin_is_allowed_by_cors() -> None:
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_valid_claim_submission_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.routes.enqueue_claim", lambda claim_id: None)
    response = client.post(
        "/api/v1/claims",
        json={
            "complaint": "Flight AI245 was delayed by four hours.",
            "flight_number": "AI245",
            "disruption_type": "delay",
            "scheduled_time": "09:10",
            "actual_time": "13:40",
        },
    )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pending"
    assert body["message"] == "Claim accepted and pending processing."
    assert UUID(body["claim_id"])
    assert datetime.fromisoformat(body["created_at"]).utcoffset().total_seconds() == 0


def test_missing_complaint_is_rejected() -> None:
    response = client.post("/api/v1/claims", json={})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_empty_complaint_is_rejected() -> None:
    response = client.post("/api/v1/claims", json={"complaint": "   "})
    assert response.status_code == 422


def test_invalid_field_type_is_rejected() -> None:
    response = client.post("/api/v1/claims", json={"complaint": 42})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_invalid_optional_field_format_is_rejected() -> None:
    response = client.post(
        "/api/v1/claims",
        json={"complaint": "Delayed flight", "flight_number": "not a flight", "scheduled_time": "9am"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_excessively_long_complaint_is_rejected() -> None:
    response = client.post("/api/v1/claims", json={"complaint": "x" * 10_001})
    assert response.status_code == 422


def test_pending_claim_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.routes.enqueue_claim", lambda claim_id: None)
    submitted = client.post("/api/v1/claims", json={"complaint": "Flight delayed."}).json()

    response = client.get(f"/api/v1/claims/{submitted['claim_id']}")
    assert response.status_code == 200
    assert response.json()["status"] == "pending"


def test_unknown_claim_returns_not_found() -> None:
    response = client.get("/api/v1/claims/98b81df5-eb4a-43d0-8eb5-6ddd5ea3e756")
    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Claim not found."


def test_completed_claim_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.routes.enqueue_claim", lambda claim_id: None)
    submitted = client.post("/api/v1/claims", json={"complaint": "Flight delayed."}).json()
    workflow_result = {
        "mode": "demo",
        "claim_analysis": {"complaint_summary": "Flight delayed."},
        "regulation_research": {"relevant_provisions": [{"citation": "DGCA.pdf, page 1"}]},
        "entitlement": {"recommendation": "request_further_evidence", "citations": ["DGCA.pdf, page 1"]},
        "verification": {"supported": True, "flags": []},
        "note": "Demo/test output only.",
    }
    monkeypatch.setattr("app.workers.tasks.run_claim_workflow", lambda claim: workflow_result)

    from app.workers.tasks import process_claim

    assert process_claim(submitted["claim_id"]) == {"status": "completed"}
    response = client.get(f"/api/v1/claims/{submitted['claim_id']}/result")
    assert response.status_code == 200
    assert response.json()["result"] == workflow_result
    assert response.json()["result"]["mode"] == "demo"


def test_failed_claim_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.routes.enqueue_claim", lambda claim_id: None)
    submitted = client.post("/api/v1/claims", json={"complaint": "Flight delayed."}).json()

    def raise_workflow_error(claim):
        raise RuntimeError("FAISS index is unavailable")

    monkeypatch.setattr("app.workers.tasks.run_claim_workflow", raise_workflow_error)
    from app.workers.tasks import process_claim

    assert process_claim(submitted["claim_id"]) == {"status": "failed"}
    response = client.get(f"/api/v1/claims/{submitted['claim_id']}/result")
    assert response.status_code == 409
    assert response.json()["status"] == "failed"
    assert "FAISS index is unavailable" in response.json()["failure_message"]


def test_redis_unavailable_marks_claim_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable(claim_id):
        raise QueueUnavailableError("Redis is unavailable.")

    monkeypatch.setattr("app.api.routes.enqueue_claim", unavailable)
    response = client.post("/api/v1/claims", json={"complaint": "Flight delayed."})
    assert response.status_code == 503

    with session_scope() as session:
        claim = session.scalar(select(Claim))
        assert claim is not None
        assert claim.status == "failed"


def test_claim_persists_after_database_reconfiguration(
    monkeypatch: pytest.MonkeyPatch, isolated_database: str
) -> None:
    monkeypatch.setattr("app.api.routes.enqueue_claim", lambda claim_id: None)
    submitted = client.post("/api/v1/claims", json={"complaint": "Flight delayed."}).json()

    from app.database import configure_database, init_db
    from app.services.claim_service import get_claim

    configure_database(isolated_database)
    init_db()
    with session_scope() as session:
        claim = get_claim(session, submitted["claim_id"])
        assert claim is not None
        assert claim.complaint == "Flight delayed."


def test_metrics_return_actual_persisted_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.routes.enqueue_claim", lambda claim_id: None)
    client.post("/api/v1/claims", json={"complaint": "Flight delayed."})

    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    assert response.json()["total_claims"] == 1
    assert response.json()["pending_claims"] == 1
    assert len(response.json()["recent_claims"]) == 1


def test_queue_retries_transient_redis_connectivity(monkeypatch: pytest.MonkeyPatch) -> None:
    from uuid import uuid4
    from app.services import queue as queue_service

    attempts = 0

    def transient_failure():
        nonlocal attempts
        attempts += 1
        raise QueueUnavailableError("Redis is unavailable.") from RedisConnectionError("temporary disconnect")

    monkeypatch.setattr(queue_service, "get_queue", transient_failure)
    monkeypatch.setattr(queue_service.time, "sleep", lambda _duration: None)
    with pytest.raises(QueueUnavailableError):
        queue_service.enqueue_claim(uuid4())
    assert attempts == 3
