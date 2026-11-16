# Evaluation protocol

Run in the API/worker container after providing model settings at runtime:

```sh
python -m eval.evaluate --mode llm --before v1 --after v2 --output eval/report.json
```

The fixed corpus is `eval/scenarios.json` (20 cases, including section 4.1), generated with `python eval/build_dataset.py`. Each row includes the expected route, required evidence facts, and a citation-bearing source passage. The evaluator executes both prompt versions against the same rows and writes scenario-level results plus before/after aggregates and deltas. The model adapter records usage and cost per step; costs are summed and normalized to 100 runs.

Metrics are deterministic lexical checks, not an LLM judge: groundedness is required-fact coverage in retrieved passages; context relevance is the fraction of retrieved passages overlapping required evidence terms; faithfulness is required-fact coverage in the rationale plus a route-match bonus; hallucination rate is the unsupported rationale sentence fraction plus unresolved-citation fraction. These are transparent approximations and should be interpreted with the scenario-level output. Prompt comparisons require `AGENT_MODE=llm` and a configured provider; demo mode does not exercise prompt artifacts.

A deliberate change is v1 to v2: v2 explicitly requires searching for modifying conditions, exceptions, and linked facility provisions before recommending a route. The output contains all four metrics before and after. The checked-in `report.json` and `MEASURED.md` were generated against the local fixed-response stub with zero prices; use a configured provider to obtain provider-specific quality and cost measurements.
