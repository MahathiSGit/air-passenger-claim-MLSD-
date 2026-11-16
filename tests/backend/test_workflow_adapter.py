"""Tests for the backend's integration with the existing RAG and agent APIs."""

import pytest

from app.services.workflow_adapter import RetrievalError, WorkflowExecutionError, run_claim_workflow


def test_adapter_retrieves_once_and_preserves_workflow_result(monkeypatch: pytest.MonkeyPatch) -> None:
    claim = {"complaint": "Flight delayed.", "flight_number": "AI245"}
    passages = [{"text": "Rule text", "citation": "DGCA.pdf, page 1"}]
    expected = {"mode": "demo", "entitlement": {"citations": ["DGCA.pdf, page 1"]}}
    calls = {"retrieval": 0}

    def retrieve(actual_claim, top_k):
        calls["retrieval"] += 1
        assert actual_claim == claim
        assert top_k == 5
        return passages

    class Result:
        def to_dict(self):
            return expected

    def workflow(actual_claim, actual_passages, *, mode):
        assert actual_claim == claim
        assert actual_passages == passages
        assert mode == "demo"
        return Result()

    monkeypatch.setattr("app.services.workflow_adapter.retrieve_passages", retrieve)
    monkeypatch.setattr("app.services.workflow_adapter.run_workflow", workflow)
    assert run_claim_workflow(claim) == expected
    assert calls["retrieval"] == 1


def test_adapter_runs_existing_demo_workflow(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise the actual repository workflow while isolating FAISS retrieval."""
    monkeypatch.setattr(
        "app.services.workflow_adapter.retrieve_passages",
        lambda claim, top_k: [{"text": "Example regulation passage.", "citation": "DGCA.pdf, page 1"}],
    )

    result = run_claim_workflow({"complaint": "Flight AI245 delayed from 09:10 to 13:40"})

    assert result["mode"] == "demo"
    assert result["entitlement"]["citations"] == ["DGCA.pdf, page 1"]
    assert result["verification"]


def test_adapter_wraps_retrieval_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    def retrieve(actual_claim, top_k):
        raise FileNotFoundError("FAISS index missing")

    monkeypatch.setattr("app.services.workflow_adapter.retrieve_passages", retrieve)
    with pytest.raises(RetrievalError, match="FAISS index missing"):
        run_claim_workflow({"complaint": "Flight delayed."})


def test_adapter_wraps_agent_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.services.workflow_adapter.retrieve_passages", lambda claim, top_k: [])

    def workflow(claim, passages, *, mode):
        raise RuntimeError("agent unavailable")

    monkeypatch.setattr("app.services.workflow_adapter.run_workflow", workflow)
    with pytest.raises(WorkflowExecutionError, match="agent unavailable"):
        run_claim_workflow({"complaint": "Flight delayed."})
