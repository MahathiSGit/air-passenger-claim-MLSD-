"""Provider-agnostic, metered JSON model adapter using runtime configuration only."""
from __future__ import annotations
import json,logging,time,urllib.error,urllib.request
from typing import Any,Protocol
from app.config import settings
from app.guardrails import inspect_input,inspect_model_output
from .prompts import DEFAULT_VERSION,load_prompt
logger=logging.getLogger("agents.model")
_CIRCUIT_FAILURES=0
_CIRCUIT_OPEN_UNTIL=0.0
class JsonModel(Protocol):
    def generate_json(self,*,task:str,payload:dict[str,Any])->dict[str,Any]:...
class ProviderUnavailable(RuntimeError):pass
class CircuitOpen(ProviderUnavailable):pass
class InstrumentedJsonModel:
    """OpenAI-compatible JSON adapter. Provider URL/model/key/prices are runtime settings."""
    def __init__(self,prompt_version:str=DEFAULT_VERSION,timeout:float|None=None):
        self.prompt_version=prompt_version; self.timeout=timeout or settings.model_timeout_seconds; self.call_records=[]; self.correlation_id=None
    @staticmethod
    def _scan(value:Any):
        if isinstance(value,str):inspect_input(value)
        elif isinstance(value,dict):
            for v in value.values():InstrumentedJsonModel._scan(v)
        elif isinstance(value,(list,tuple)):
            for v in value:InstrumentedJsonModel._scan(v)
    @staticmethod
    def _token_estimate(text:str)->int:return max(1,(len(text)+3)//4)
    def generate_json(self,*,task:str,payload:dict[str,Any])->dict[str,Any]:
        global _CIRCUIT_FAILURES,_CIRCUIT_OPEN_UNTIL
        if not settings.model_api_url or not settings.model_id:raise ProviderUnavailable("MODEL_API_URL and MODEL_ID must be injected at runtime for llm mode")
        started=time.perf_counter()
        if time.monotonic()<_CIRCUIT_OPEN_UNTIL:raise CircuitOpen("Model provider circuit is open")
        self._scan(payload)
        task_contracts={
          "research_tool_selection":"Return JSON {action:'tool',tool:'corpus_search|clause_lookup|claim_field_lookup',argument:string} or {action:'finish'}.",
          "claim_analysis":"Return ClaimAnalysis JSON keys claim_type, flight_number, airline, origin, destination, disruption_type, scheduled_time, actual_time, alternate_flight, complaint_summary, missing_information.",
          "regulation_research":"Return compact JSON keys relevant_citations (array of exact citation strings copied from supplied passages), conditions (short strings), evidence_gaps (short strings). Do not quote or copy passage text.",
          "entitlement":"Return JSON keys recommendation, rationale, compensation_amount, currency, citations, uncertainties. recommendation must be one of the allowed values in payload.",
        }
        system=load_prompt("triage",self.prompt_version)+chr(10)+"Task: "+task+chr(10)+task_contracts.get(task,"Return a JSON object matching the requested task.")
        user=json.dumps(payload,ensure_ascii=False); body=json.dumps({"model":settings.model_id,"messages":[{"role":"system","content":system},{"role":"user","content":user}],"response_format":{"type":"json_object"},"max_tokens":settings.model_max_tokens,"temperature":0}).encode()
        headers={"Content-Type":"application/json"}
        if settings.model_api_key:headers["Authorization"]="Bearer "+settings.model_api_key
        last_error=None
        for attempt in range(3):
            try:
                req=urllib.request.Request(settings.model_api_url,data=body,headers=headers,method="POST")
                with urllib.request.urlopen(req,timeout=self.timeout) as response:data=json.loads(response.read().decode("utf-8"))
                content=data["choices"][0]["message"]["content"]; result=json.loads(content)
                # Small local models sometimes wrap the requested object in a task-named key.
                if isinstance(result,dict) and isinstance(result.get(task),dict):result=result[task]
                inspect_model_output(result)
                output=json.dumps(result,ensure_ascii=False); usage=data.get("usage",{})
                prompt_tokens=int(usage.get("prompt_tokens",self._token_estimate(system+user))); completion_tokens=int(usage.get("completion_tokens",self._token_estimate(output)))
                cost=(prompt_tokens*settings.input_cost_per_million+completion_tokens*settings.output_cost_per_million)/1_000_000
                record={"step":task,"prompt_version":self.prompt_version,"correlation_id":self.correlation_id,"prompt_tokens":prompt_tokens,"completion_tokens":completion_tokens,"cost":cost,"latency_seconds":round(time.perf_counter()-started,4),"status":"ok"}
                self.call_records.append(record); _CIRCUIT_FAILURES=0; _CIRCUIT_OPEN_UNTIL=0.0
                logger.info("model_call_complete",extra=record); return result
            except (urllib.error.URLError,TimeoutError,json.JSONDecodeError,KeyError,ValueError) as exc:
                last_error=exc; _CIRCUIT_FAILURES+=1
                if _CIRCUIT_FAILURES>=3:_CIRCUIT_OPEN_UNTIL=time.monotonic()+30
                if attempt<2:time.sleep(0.2*(2**attempt))
        error={"step":task,"prompt_version":self.prompt_version,"correlation_id":self.correlation_id,"latency_seconds":round(time.perf_counter()-started,4),"status":"error","error_type":type(last_error).__name__ if last_error else "unknown"}
        self.call_records.append(error); logger.error("model_call_failed",extra=error)
        raise ProviderUnavailable("Model call failed after bounded retries") from last_error
def configured_mode()->str:
    import os
    mode=os.getenv("AGENT_MODE","demo").strip().lower()
    if mode not in {"demo","llm"}:raise ValueError("AGENT_MODE must be demo or llm")
    return mode
