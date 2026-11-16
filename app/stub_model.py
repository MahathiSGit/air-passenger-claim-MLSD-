"""Deterministic OpenAI-compatible model stub for Locust and failure-path exercises."""
from __future__ import annotations
import asyncio,json,os,time
from fastapi import FastAPI,Request
from fastapi.responses import JSONResponse
from prometheus_client import Counter,generate_latest,CONTENT_TYPE_LATEST
from starlette.responses import Response
STUB_CALLS=Counter("model_stub_calls_total","Fixed-delay stub model calls")
app=FastAPI(title="Fixed-response model stub")
@app.get("/health")
async def health():return {"status":"ok"}
@app.post("/v1/chat/completions")
async def completion(request:Request):
    STUB_CALLS.inc()
    payload=await request.json(); delay=max(0,float(os.getenv("STUB_DELAY_SECONDS","2"))); await asyncio.sleep(delay)
    messages=payload.get("messages",[]); system=" ".join(str(m.get("content","")) for m in messages if m.get("role")=="system"); user=" ".join(str(m.get("content","")) for m in messages if m.get("role")=="user")
    task=system.rsplit("task:",1)[-1].strip().lower()
    try: data=json.loads(user)
    except Exception:data={}
    if "research_tool_selection" in task:
        claim=data.get("claim",{}); complaint=str(claim.get("complaint","")); lower=complaint.lower()
        calls=data.get("previous_tool_calls",[]); retrieved=" ".join(str(p.get("text","")) for p in data.get("retrieved_passages",[])).lower()
        v2="actively search for every condition" in system.lower()
        if not calls: result={"action":"tool","tool":"corpus_search","argument":complaint}
        elif not v2: result={"action":"finish"}
        elif "cancel" in lower and not any(c.get("tool")=="clause_lookup" for c in calls): result={"action":"tool","tool":"clause_lookup","argument":"3.3.2"}
        elif "cancel" in lower and not any("3.8.1" in str(c.get("query_or_field",c.get("argument",""))) or "facility" in str(c.get("query_or_field",c.get("argument",""))) for c in calls): result={"action":"tool","tool":"corpus_search","argument":"3.8.1(a) facilities meals refreshments waiting alternate flight"}
        elif "delay" in lower and len(calls)<3: result={"action":"tool","tool":"corpus_search","argument":"delay notice cause exceptions facilities"}
        elif "denied boarding" in lower and len(calls)<3: result={"action":"tool","tool":"corpus_search","argument":"denied boarding compensation exemptions"}
        else: result={"action":"finish"}
    elif "claim_analysis" in task:
        claim=data.get("claim",{}); complaint=claim.get("complaint",data.get("complaint","")); lower=str(complaint).lower()
        dtype=next((x for x in ["cancellation","delay","denied boarding","downgrading"] if x in lower),claim.get("disruption_type"))
        result={"claim_type":"flight disruption compensation","disruption_type":dtype,"flight_number":claim.get("flight_number"),"scheduled_time":claim.get("scheduled_time"),"actual_time":claim.get("actual_time"),"alternate_flight":claim.get("alternate_flight"),"complaint_summary":str(complaint)[:240],"missing_information":[]}
    elif "regulation_research" in task:
        claim=data.get("claim",{}); passages=data.get("passages",[]); provisions=[{"text":p.get("text",p.get("content","")),"citation":p.get("citation") or p.get("source") or p.get("id")} for p in passages if p.get("text") or p.get("content")]
        result={"relevant_provisions":provisions,"conditions":[],"evidence_gaps":[] if provisions else ["No retrieved provisions"]}
    elif "entitlement" in task:
        research=data.get("research",{}); provisions=research.get("relevant_provisions",[])
        citations=[p.get("citation") for p in provisions if p.get("citation")]
        claim=data.get("claim",{}); complaint=str(claim.get("complaint_summary",claim.get("complaint",""))).lower(); sections=" ".join(str(p.get("text", "")) for p in provisions).lower()
        hard_case="cancel" in complaint and ("alternate" in complaint or "flight" in complaint) and "3.3.2" in sections and "3.8.1" in sections
        recommendation="decline" if hard_case else ("request_further_evidence" if provisions else "escalate_to_human")
        rationale="The retrieved 3.3.2 passage supports the alternate-flight option in this fact pattern; the 3.8.1(a) waiting facilities remain applicable. This is provisional and requires authorized human review." if hard_case else "This fixed test stub never makes a final legal determination; a human must review the cited evidence and missing claim facts."
        result={"recommendation":recommendation,"rationale":rationale,"compensation_amount":None,"currency":None,"citations":citations,"uncertainties":[] if hard_case else ["Stub response; human review required"]}
    else:result={}
    content=json.dumps(result)
    return JSONResponse({"id":"stub","object":"chat.completion","created":int(time.time()),"model":payload.get("model",""),"choices":[{"index":0,"message":{"role":"assistant","content":content},"finish_reason":"stop"}],"usage":{"prompt_tokens":max(1,len(system+user)//4),"completion_tokens":max(1,len(content)//4)}})


@app.get("/metrics")
async def metrics():return Response(generate_latest(),media_type=CONTENT_TYPE_LATEST)




