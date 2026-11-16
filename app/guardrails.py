"""Input/output guardrails for untrusted passenger text and provisional results."""
from __future__ import annotations
import re
from typing import Any
INJECTION_PATTERNS=[re.compile(r"\b(ignore|disregard|override)\b.{0,80}\b(instruction|system prompt|policy|rules)\b",re.I),re.compile(r"\b(reveal|print|exfiltrate)\b.{0,50}\b(prompt|secret|api key|credential)\b",re.I),re.compile(r"\bcall\s+(the\s+)?tool\b|<\|.*?\|>",re.I)]
TOXIC_TERMS={"idiot","moron","stupid","kill yourself","i will hurt you"}
UNAUTHORIZED=re.compile(r"\b(payment (is )?approved|we have paid|payment authorized|claim is finally approved|you are guaranteed compensation|we guarantee payment|legally entitled to payment)\b",re.I)
class GuardrailRejected(ValueError):pass
def inspect_input(text:str)->dict[str,Any]:
    normalized=text.strip()
    if any(p.search(normalized) for p in INJECTION_PATTERNS):raise GuardrailRejected("Input contains instructions attempting to override system policy.")
    if any(term in normalized.lower() for term in TOXIC_TERMS):raise GuardrailRejected("Input failed toxicity screening.")
    return {"injection":False,"toxicity":False}
def inspect_model_output(value:Any)->None:
    if isinstance(value,str):
        if any(term in value.lower() for term in TOXIC_TERMS):raise GuardrailRejected("Model output failed toxicity screening.")
        if any(p.search(value) for p in INJECTION_PATTERNS):raise GuardrailRejected("Model output contains prompt injection instructions.")
    elif isinstance(value,dict):
        for v in value.values():inspect_model_output(v)
    elif isinstance(value,(list,tuple)):
        for v in value:inspect_model_output(v)
def filter_output(result:dict[str,Any])->dict[str,Any]:
    entitlement=result.setdefault("entitlement",{}); text=str(entitlement.get("rationale",""))
    if UNAUTHORIZED.search(text):
        entitlement.update({"recommendation":"escalate_to_human","compensation_amount":None,"rationale":"Output was blocked because it stated an unauthorized final determination. Human review is required."})
        result.setdefault("guardrails",[]).append("unauthorized_determination_blocked")
    if any(term in text.lower() for term in TOXIC_TERMS):
        entitlement.update({"recommendation":"escalate_to_human","rationale":"Output failed toxicity screening; human review is required."})
        result.setdefault("guardrails",[]).append("output_toxicity_blocked")
    note=str(result.get("note",""))
    if "human" not in note.lower() or "provisional" not in note.lower():result["note"]=(note+" Provisional triage only; an authorized human decides any claim or payment.").strip()
    return result
