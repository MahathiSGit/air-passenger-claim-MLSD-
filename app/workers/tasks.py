"""RQ task entry points with correlated spans and sampled quality monitoring."""
from __future__ import annotations
import json,logging,time
from app.database import init_db,session_scope
from app.models import QualityScore
from app.services.claim_service import begin_processing,complete_claim,fail_claim,get_claim,serialized_claim_data
from app.services.workflow_adapter import run_claim_workflow
from app.metrics import RUNS,RUN_LATENCY,QUALITY
from app.quality import score_live_result
logger=logging.getLogger("app.worker")
def process_claim(claim_id:str):
    init_db(); started=time.perf_counter()
    with session_scope() as session:
        claim=get_claim(session,claim_id)
        if claim is None:return {"status":"missing"}
        if not begin_processing(session,claim_id):return {"status":claim.status}
        payload=serialized_claim_data(claim); correlation_id=claim.correlation_id
    payload["_correlation_id"]=correlation_id
    try:
        from opentelemetry import trace
        tracer=trace.get_tracer("airclaim.worker")
        with tracer.start_as_current_span("claim.process") as span:
            span.set_attribute("claim.run_id",claim_id); span.set_attribute("claim.correlation_id",correlation_id or "")
            result=run_claim_workflow(payload)
        latency=time.perf_counter()-started
        result.update({"run_id":claim_id,"correlation_id":correlation_id,"end_to_end_latency_seconds":round(latency,4)})
        with session_scope() as session:
            complete_claim(session,claim_id,result,latency)
            if int(claim_id.replace("-",""),16)%10==0:
                scores=score_live_result(result)
                session.add(QualityScore(run_id=claim_id,**scores,detail_json=json.dumps({"verification":result.get("verification",{}),"citation_count":len(result.get("entitlement",{}).get("citations",[]))})))
                for metric,value in scores.items():QUALITY.labels(metric).set(value)
        RUNS.labels("completed").inc(); RUN_LATENCY.observe(latency)
        return {"status":"completed"}
    except Exception as exc:
        logger.exception("Claim processing failed",extra={"claim_id":claim_id,"correlation_id":correlation_id})
        with session_scope() as session:fail_claim(session,claim_id,str(exc))
        RUNS.labels("failed").inc(); return {"status":"failed"}
