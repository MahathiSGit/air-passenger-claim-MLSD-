"""Bounded evidence researcher with dynamic LangGraph agent path and demo fallback."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from .tools import claim_field_lookup, clause_lookup, corpus_search
MAX_TOOL_CALLS=6
@dataclass
class ResearchTrace:
    passages: list[dict[str, Any]]=field(default_factory=list)
    calls: list[dict[str, Any]]=field(default_factory=list)
class ResearchAgent:
    """Model-selected LangGraph tools in LLM mode; bounded tool policy in demo mode."""
    def __init__(self, *, max_tool_calls: int=MAX_TOOL_CALLS, model=None):
        if not 1<=max_tool_calls<=MAX_TOOL_CALLS: raise ValueError(f"max_tool_calls must be between 1 and {MAX_TOOL_CALLS}")
        self.max_tool_calls=max_tool_calls; self.model=model
    def run(self, claim: dict[str, Any]) -> ResearchTrace:
        if self.model is not None:
            from .langgraph_research import LangGraphResearchAgent
            result=LangGraphResearchAgent(self.model,self.max_tool_calls).run(claim)
            return ResearchTrace(result["passages"],result["calls"])
        trace=ResearchTrace(); complaint=str(claim_field_lookup(claim,"complaint")); self._search(trace,"corpus_search",complaint,lambda:corpus_search(complaint))
        lower=complaint.lower()
        if "cancel" in lower:
            self._search(trace,"clause_lookup","3.3.2",lambda:clause_lookup("3.3.2"))
            self._search(trace,"corpus_search","alternate flight compensation refund facilities meals refreshments",lambda:corpus_search("alternate flight compensation refund facilities meals refreshments"))
        elif "delay" in lower: self._search(trace,"corpus_search","delay block time notice cause exceptions facilities",lambda:corpus_search("delay block time notice cause exceptions facilities"))
        elif "denied boarding" in lower: self._search(trace,"corpus_search","denied boarding volunteers compensation exceptions",lambda:corpus_search("denied boarding volunteers compensation exceptions"))
        else: self._search(trace,"corpus_search","applicable entitlement conditions exemptions definitions",lambda:corpus_search("applicable entitlement conditions exemptions definitions"))
        unique={(str(p.get("citation","")),str(p.get("text",""))):p for p in trace.passages}; trace.passages=list(unique.values()); return trace
    def _search(self,trace,tool,query,invoke):
        if len(trace.calls)>=self.max_tool_calls:return
        try:
            passages=invoke(); trace.calls.append({"tool":tool,"query":query,"result_count":len(passages),"status":"ok"}); trace.passages.extend(passages)
        except Exception as exc: trace.calls.append({"tool":tool,"query":query,"status":"error","error_type":type(exc).__name__})
