"""Bounded retrieval and model execution behind the API worker."""
from __future__ import annotations
import logging,os
from typing import Any
from agents.model import InstrumentedJsonModel,ProviderUnavailable
from agents.research_agent import ResearchAgent
from agents.workflow import run_workflow
from app.config import settings
from app.guardrails import filter_output
logger=logging.getLogger("app.workflow")
class RetrievalError(RuntimeError):pass
class WorkflowExecutionError(RuntimeError):pass
def run_claim_workflow(claim:dict[str,Any])->dict[str,Any]:
    correlation_id=claim.pop("_correlation_id",None)
    mode=settings.agent_mode
    model=InstrumentedJsonModel(prompt_version=os.getenv("PROMPT_VERSION","v1")) if mode=="llm" else None
    if model is not None:model.correlation_id=correlation_id
    try:
        tool_budget=max(1,min(6,int(os.getenv("MAX_TOOL_CALLS","3")))) if mode=="llm" else 6
        trace=ResearchAgent(model=model,max_tool_calls=tool_budget).run(claim)
        result=run_workflow(claim,trace.passages,model=model,mode=mode)
    except ProviderUnavailable as exc:
        logger.exception("Configured model provider unavailable",extra={"correlation_id":correlation_id})
        raise WorkflowExecutionError("Configured model provider is unavailable; no demo result was substituted.") from exc
    except Exception as exc:
        logger.exception("Agent workflow failed",extra={"correlation_id":correlation_id})
        raise WorkflowExecutionError(f"Agent workflow failed: {exc}") from exc
    serialized=filter_output(result.to_dict())
    serialized["correlation_id"]=correlation_id
    serialized["agent_trace"]={"topology":["LangGraph research agent","claim analysis agent","entitlement agent","verification agent"],"tool_calls":trace.calls,"tool_call_limit":tool_budget,"correlation_id":correlation_id}
    serialized["per_run_cost"]=sum(float(c.get("cost",0)) for c in serialized.get("model_calls",[]))
    serialized["total_prompt_tokens"]=sum(int(c.get("prompt_tokens",0)) for c in serialized.get("model_calls",[]))
    serialized["total_completion_tokens"]=sum(int(c.get("completion_tokens",0)) for c in serialized.get("model_calls",[]))
    return serialized
