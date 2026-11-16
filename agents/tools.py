"""Validated retrieval tools exposed to LangGraph through LangChain schemas."""
from __future__ import annotations
from typing import Any
from rag.retrieval import retrieve_passages
from app.guardrails import inspect_input

def corpus_search(query:str,top_k:int=5)->list[dict[str,Any]]:
    inspect_input(query)
    return retrieve_passages(query,top_k=top_k)
def clause_lookup(clause_id:str,top_k:int=4)->list[dict[str,Any]]:
    inspect_input(clause_id)
    return corpus_search(f"{clause_id} conditions exceptions definitions facilities",top_k=top_k)
def claim_field_lookup(claim:dict[str,Any],field:str)->Any:
    if field not in claim:raise KeyError(f"Unsupported claim field: {field}")
    return claim[field]
def langchain_tools():
    """Return LangChain StructuredTools lazily so demo-only installs can inspect this module."""
    from langchain_core.tools import StructuredTool
    return {
        "corpus_search":StructuredTool.from_function(corpus_search,name="corpus_search",description="Search a natural-language query in the regulatory corpus."),
        "clause_lookup":StructuredTool.from_function(clause_lookup,name="clause_lookup",description="Retrieve a named regulatory clause and related conditions."),
        "claim_field_lookup":StructuredTool.from_function(claim_field_lookup,name="claim_field_lookup",description="Read one validated field from the current claim."),
    }
