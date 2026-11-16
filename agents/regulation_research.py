"""Map retrieved passages to claim facts; passage retrieval is external."""

from typing import Any

from .model import JsonModel
from .schemas import ClaimAnalysis, ResearchResult


def research_regulations(
    claim: ClaimAnalysis, passages: list[dict[str, Any] | str], model: JsonModel | None = None
) -> ResearchResult:
    """Identify potentially applicable provisions from supplied passages only."""
    normalized = [({"text": p} if isinstance(p, str) else dict(p)) for p in passages]
    if model:
        # Keep the local-model response compact: it selects exact citations, and this
        # service restores the authoritative passage text from retrieval results.
        candidates = []
        for passage in normalized:
            text = str(passage.get("text", passage.get("content", ""))).strip()
            citation = passage.get("citation") or passage.get("source") or passage.get("id")
            if text and citation:
                candidates.append({"citation": str(citation), "text": text[:500]})
        result = model.generate_json(task="regulation_research", payload={
            "claim": claim.__dict__, "passages": candidates[:8],
        })
        if isinstance(result.get("relevant_citations"), list):
            by_citation = {}
            for passage in normalized:
                citation = passage.get("citation") or passage.get("source") or passage.get("id")
                text = str(passage.get("text", passage.get("content", ""))).strip()
                if citation and text:
                    by_citation[str(citation)] = {"citation": str(citation), "text": text}
            citations = list(dict.fromkeys(str(c) for c in result["relevant_citations"] if str(c) in by_citation))
            result = {
                "relevant_provisions": [by_citation[c] for c in citations],
                "conditions": result.get("conditions", []),
                "evidence_gaps": result.get("evidence_gaps", []),
            }
        elif isinstance(result.get("relevant_provisions"), list):
            allowed = {str(p.get("citation") or p.get("source") or p.get("id")) for p in normalized}
            result["relevant_provisions"] = [
                {"citation": str(p.get("citation")), "text": str(next((src.get("text", src.get("content", "")) for src in normalized if str(src.get("citation") or src.get("source") or src.get("id")) == str(p.get("citation"))), ""))}
                for p in result["relevant_provisions"] if isinstance(p, dict) and str(p.get("citation")) in allowed
            ]
        return ResearchResult(**result)
    provisions = []
    for passage in normalized:
        text = str(passage.get("text", passage.get("content", ""))).strip()
        if not text:
            continue
        citation = passage.get("citation") or passage.get("source") or passage.get("id")
        provisions.append({"text": text, "citation": citation})
    gaps = ["No retrieved regulation passages were supplied."] if not provisions else []
    if provisions and not any(p["citation"] for p in provisions):
        gaps.append("Retrieved passages have no citation or source identifier.")
    return ResearchResult(
        relevant_provisions=provisions,
        conditions=[],
        evidence_gaps=gaps,
    )
