"""Verify citation resolution and minimum textual support before returning a route."""
import re
from .schemas import ClaimAnalysis,EntitlementResult,ResearchResult,VerificationResult
_STOP={"the","and","for","with","from","that","this","were","was","are","has","have","into","when","under","shall","would","could","there","their","they","only","not","due","claim","flight","passenger","airline","paragraph","provide","provided","provision","result","recommendation","human","review","demo","mode","output","evidence","because"}
def _terms(text):return {x for x in re.findall(r"[a-z0-9]+",text.lower()) if len(x)>3 and x not in _STOP}
def verify_recommendation(claim:ClaimAnalysis,research:ResearchResult,entitlement:EntitlementResult)->VerificationResult:
    flags=[]; passages=research.relevant_provisions
    available={str(p.get("citation")):str(p.get("text","")) for p in passages if p.get("citation")}
    if not entitlement.citations:flags.append("Recommendation has no citations.")
    unresolved=set(entitlement.citations)-set(available)
    if unresolved:flags.append("One or more citations do not resolve to retrieved text.")
    if not passages:flags.append("No regulatory evidence was retrieved.")
    cited_text=" ".join(available.get(c,"") for c in entitlement.citations)
    rationale_terms=_terms(entitlement.rationale); evidence_terms=_terms(cited_text)
    overlap=len(rationale_terms & evidence_terms)/max(len(rationale_terms),1)
    if entitlement.citations and overlap<0.08:flags.append("Rationale has insufficient lexical support in its cited passages.")
    if entitlement.compensation_amount is not None:
        amount=str(entitlement.compensation_amount).rstrip("0").rstrip(".")
        if amount not in cited_text:flags.append("Compensation amount is not stated in cited text and must not be returned as verified.")
    if entitlement.uncertainties or claim.missing_information or research.evidence_gaps:
        flags.append("Assessment contains missing information or uncertainty.")
    route=entitlement.recommendation
    if flags and route in {"pay_as_computed","decline"}:
        route="escalate_to_human"; flags.append("Escalated because claim support could not be verified.")
    return VerificationResult(supported=not flags,flags=flags,recommendation=route)
