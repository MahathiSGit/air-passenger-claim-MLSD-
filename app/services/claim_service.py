"""Claim persistence and state transition helpers."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID
from sqlalchemy import update
from sqlalchemy.orm import Session
from app.models import Claim

def _now(): return datetime.now(timezone.utc)
def create_claim(session: Session, claim_id: UUID, data: dict[str, Any], correlation_id: str | None = None) -> Claim:
    claim = Claim(id=str(claim_id), complaint=data["complaint"], claim_data_json=json.dumps(data), status="pending", created_at=_now(), updated_at=_now(), correlation_id=correlation_id)
    session.add(claim); session.commit(); session.refresh(claim); return claim
def get_claim(session: Session, claim_id: UUID | str): return session.get(Claim, str(claim_id))
def begin_processing(session: Session, claim_id: str) -> bool:
    statement = update(Claim).where(Claim.id == claim_id, Claim.status == "pending").values(status="processing", updated_at=_now())
    return session.execute(statement).rowcount == 1
def complete_claim(session: Session, claim_id: str, result: dict[str, Any], latency_seconds: float | None = None):
    claim = session.get(Claim, claim_id)
    if claim is None: return
    claim.status = "completed"; claim.workflow_result_json = json.dumps(result); claim.failure_message = None; claim.updated_at = _now(); claim.run_latency_seconds = latency_seconds
def fail_claim(session: Session, claim_id: str, message: str):
    claim = session.get(Claim, claim_id)
    if claim is None: return
    claim.status = "failed"; claim.failure_message = message[:2000]; claim.updated_at = _now()
def serialized_claim_data(claim: Claim): return json.loads(claim.claim_data_json)
def serialized_workflow_result(claim: Claim): return json.loads(claim.workflow_result_json) if claim.workflow_result_json else None
