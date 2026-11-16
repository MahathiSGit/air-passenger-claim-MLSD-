"""Sequential hand-off among analysis, research, entitlement and verification agents."""
from typing import Any
from .claim_analysis import analyze_claim
from .entitlement import assess_entitlement
from .model import JsonModel, configured_mode
from .regulation_research import research_regulations
from .schemas import WorkflowResult
from .verification import verify_recommendation

def run_workflow(claim: str | dict[str, Any], passages: list[dict[str, Any] | str], *, model: JsonModel | None = None, mode: str | None = None) -> WorkflowResult:
    selected_mode = mode or configured_mode()
    if selected_mode not in {"demo", "llm"}: raise ValueError("mode must be demo or llm")
    if selected_mode == "llm" and model is None: raise ValueError("LLM mode requires a configured JsonModel adapter")
    active_model = model if selected_mode == "llm" else None
    analysis = analyze_claim(claim, active_model)
    research = research_regulations(analysis, passages, active_model)
    entitlement = assess_entitlement(analysis, research, active_model)
    verification = verify_recommendation(analysis, research, entitlement)
    if verification.recommendation != entitlement.recommendation: entitlement.recommendation = verification.recommendation
    note = "Demo/test output only; it is not a verified legal decision and does not authorize or transfer compensation." if selected_mode == "demo" else "Model-assisted triage is provisional; an authorized human must decide any claim or payment."
    version = getattr(model, "prompt_version", "demo-v1") if model else "demo-v1"
    calls = list(getattr(model, "call_records", [])) if model else []
    return WorkflowResult(selected_mode, analysis, research, entitlement, verification, note, version, calls)
