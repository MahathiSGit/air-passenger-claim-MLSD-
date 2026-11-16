"""Versioned REST interfaces for claims, feedback, metrics and health."""
import json
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.database import get_session
from app.models import Claim, Feedback, QualityScore, QuarantinedRequest
from app.schemas.claims import ClaimAccepted, ClaimFailedResponse, ClaimResultResponse, ClaimStatusResponse, ClaimSubmission, FeedbackAccepted, FeedbackSubmission, HealthResponse
from app.services.claim_service import create_claim, fail_claim, get_claim, serialized_workflow_result
from app.services.queue import QueueUnavailableError, enqueue_claim
from app.guardrails import GuardrailRejected, inspect_input
from app.rate_limit import RateLimitExceeded, check_client_limit
from app.metrics import FEEDBACK, RUNS
router = APIRouter()
def _as_utc(value: datetime):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
@router.get("/health", response_model=HealthResponse)
async def versioned_health(): return HealthResponse()
@router.post("/claims", response_model=ClaimAccepted, status_code=status.HTTP_202_ACCEPTED)
async def submit_claim(claim: ClaimSubmission, request: Request, session: Session = Depends(get_session)):
    client_id = request.headers.get("X-Client-ID") or (request.client.host if request.client else "unknown")
    try:
        check_client_limit(client_id)
        for field,value in claim.model_dump().items():
            if isinstance(value,str):inspect_input(value)
    except GuardrailRejected as exc:
        session.add(QuarantinedRequest(client_id=client_id,payload_json=json.dumps(claim.model_dump()),field_errors_json=json.dumps([{"loc":["body","complaint"],"msg":str(exc),"type":"guardrail_rejected"}]),request_id=getattr(request.state,"request_id",None))); session.commit()
        raise HTTPException(status_code=400,detail=str(exc)) from exc
    except RateLimitExceeded as exc:
        raise HTTPException(status_code=429,detail=str(exc)) from exc
    claim_id = uuid4()
    created = create_claim(session, claim_id, claim.model_dump(), correlation_id=getattr(request.state, "request_id", None))
    try: enqueue_claim(claim_id)
    except QueueUnavailableError as exc:
        fail_claim(session, str(claim_id), "Claim queue is unavailable; processing was not started.")
        session.commit()
        raise HTTPException(status_code=503, detail="Claim queue is unavailable. Please retry later.") from exc
    return ClaimAccepted(claim_id=claim_id, created_at=_as_utc(created.created_at))
@router.get("/claims/{claim_id}", response_model=ClaimStatusResponse)
async def get_claim_status(claim_id: str, session: Session = Depends(get_session)):
    claim = get_claim(session, claim_id)
    if claim is None: raise HTTPException(status_code=404, detail="Claim not found.")
    return ClaimStatusResponse(claim_id=claim.id, status=claim.status, created_at=_as_utc(claim.created_at), updated_at=_as_utc(claim.updated_at), failure_message=claim.failure_message)
@router.get("/claims/{claim_id}/result", response_model=ClaimResultResponse)
async def get_claim_result(claim_id: str, session: Session = Depends(get_session)):
    claim = get_claim(session, claim_id)
    if claim is None: raise HTTPException(status_code=404, detail="Claim not found.")
    if claim.status == "completed":
        result = serialized_workflow_result(claim)
        if result is None: raise HTTPException(status_code=500, detail="Completed claim has no stored workflow result.")
        return ClaimResultResponse(claim_id=claim.id, status="completed", created_at=_as_utc(claim.created_at), updated_at=_as_utc(claim.updated_at), result=result)
    if claim.status == "failed":
        return JSONResponse(status_code=409, content=ClaimFailedResponse(claim_id=claim.id, status="failed", created_at=_as_utc(claim.created_at), updated_at=_as_utc(claim.updated_at), failure_message=claim.failure_message or "Claim processing failed.").model_dump(mode="json"))
    return JSONResponse(status_code=202, content=ClaimStatusResponse(claim_id=claim.id, status=claim.status, created_at=_as_utc(claim.created_at), updated_at=_as_utc(claim.updated_at)).model_dump(mode="json"))
@router.post("/claims/{claim_id}/feedback", response_model=FeedbackAccepted, status_code=201)
async def submit_feedback(claim_id: str, data: FeedbackSubmission, session: Session = Depends(get_session)):
    claim = get_claim(session, claim_id)
    if claim is None or claim.status != "completed": raise HTTPException(status_code=404, detail="Completed claim not found.")
    record = Feedback(claim_id=claim_id, satisfactory=data.satisfactory, reason=data.reason)
    session.add(record); session.commit(); session.refresh(record)
    FEEDBACK.labels(str(data.satisfactory).lower()).inc()
    return FeedbackAccepted(feedback_id=record.id, claim_id=claim_id, created_at=_as_utc(record.created_at))
@router.get("/feedback/summary")
async def feedback_summary(session: Session = Depends(get_session)):
    rows = session.execute(select(Feedback.satisfactory, func.count()).group_by(Feedback.satisfactory)).all()
    return {"total": sum(int(count) for _, count in rows), "satisfactory": sum(int(count) for value, count in rows if value), "unsatisfactory": sum(int(count) for value, count in rows if not value)}
@router.get("/metrics")
async def get_metrics(session: Session = Depends(get_session)):
    counts = {state: int(session.scalar(select(func.count()).select_from(Claim).where(Claim.status == state)) or 0) for state in ("pending", "processing", "completed", "failed")}
    total = int(session.scalar(select(func.count()).select_from(Claim)) or 0)
    recent = session.scalars(select(Claim).order_by(Claim.created_at.desc()).limit(10)).all()
    escalated=0
    for row in session.scalars(select(Claim).where(Claim.workflow_result_json.is_not(None))).all():
        try: escalated += json.loads(row.workflow_result_json or "{}").get("entitlement",{}).get("recommendation")=="escalate_to_human"
        except (TypeError,ValueError): pass
    return {"total_claims": total, **{f"{k}_claims": v for k,v in counts.items()}, "escalated_claims":int(escalated), "recent_claims": [{"claim_id": c.id, "status": c.status, "created_at": _as_utc(c.created_at).isoformat(), "flight_number": json.loads(c.claim_data_json).get("flight_number")} for c in recent]}

@router.get("/quality/timeseries")
async def quality_timeseries(limit:int=100,session:Session=Depends(get_session)):
    rows=session.scalars(select(QualityScore).order_by(QualityScore.scored_at.desc()).limit(min(max(limit,1),1000))).all()
    return {"sample_count":len(rows),"method":"live_proxy_v1; see evaluation protocol for metric definitions","samples":[{"run_id":r.run_id,"scored_at":_as_utc(r.scored_at).isoformat(),"groundedness":r.groundedness,"context_relevance":r.context_relevance,"faithfulness":r.faithfulness,"hallucination_rate":r.hallucination_rate} for r in reversed(rows)]}


