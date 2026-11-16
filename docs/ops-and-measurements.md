# Reliability, deployment and measurement notes

## SLO (declared before load measurement)

The complete-run p95 target is **60 seconds**, measured from claim POST through polling until the persisted final result is returned. Section 1 describes a multi-condition regulatory review with iterative retrieval and verification; one minute gives an analyst an asynchronous result within a practical interaction while allowing several bounded model/tool steps. Submission latency alone is not the SLO.

## Load-test procedure

Use the Compose model stub with a fixed 2-second response delay, configure `AGENT_MODE=llm`, `MODEL_API_URL` to the stub's chat-completions route and inject a non-secret test `MODEL_ID`; then run Locust against the API. Run once with one worker and again with `docker compose up --scale agent-worker=3`. The Locust user posts and polls to completion and names the measured transaction `complete_run`. Save HTML/CSV output, report completed RPS, p50/p95 and target pass/fail at each concurrency, and identify the saturated service. No result is prefilled: run this procedure on the target host before publishing measurements.

## Deployment boundaries

API handles validation, quarantine, feedback and status; it scales with request traffic. RQ workers execute retrieval/model steps and scale independently for CPU/model-call concurrency. Redis isolates queue/rate-limit/cache state and has a health check. The indexer is a one-shot idempotent init service sharing the persistent data volume. Prometheus, Grafana, Jaeger and cAdvisor are independent observability services so scrape, dashboard or trace failures do not stop claims. The web client is its own static container. The model stub replaces provider latency only during load tests.

## Cost and cache measurement

Each model call records provider-reported token counts where available (otherwise a documented character-based estimate), configured input/output price and computed cost. Per-run cost is summed from steps; `eval.report.json` includes cost per 100 completed runs and per-scenario cost so the largest step can be found. Embedding/retrieval caches are local and free; compare warm/cold timings with `python -m eval.cache_benchmark`, and report cost per run alongside p95. No performance delta is claimed until measured.

## Runbook

### Redis or queue unavailable
- Symptom: claim POST returns 503, or a pending run stops progressing.
- Confirm: `docker compose ps redis agent-worker`; inspect API/worker logs and Redis health.
- Recover: restore Redis health, restart workers, then retry the claim; failed/pending records remain queryable by run ID.

### FAISS index missing or inconsistent
- Symptom: worker fails a run with index-not-found or FAISS/metadata count mismatch.
- Confirm: inspect worker failure by run ID and index manifest/chunk gauges; check indexer logs.
- Recover: run `docker compose run --rm indexer python -m rag.retrieval --incremental`; for embedding dimension changes use `--reembed`, then restart workers.

## Development incident log

- 2026-11-13: Printing extracted DGCA PDF text on Windows raised `UnicodeEncodeError` because the console used cp1252 and the PDF contains a bullet glyph. Confirmed by the page extraction traceback; reran with `PYTHONIOENCODING=utf-8`, which preserved extracted text. Recovery: use UTF-8 for corpus inspection and keep PDF text encoding explicit.

## Quality metric caveat

The batch evaluator reports groundedness, context relevance, faithfulness and hallucination using the lexical formulas in `eval/README.md`. The live sample endpoint uses citation/verifier proxies because arbitrary live claims have no known expected label. Keep the batch metrics and live proxy series labeled separately.


- 2026-11-13: First full Compose startup failed to bind the API host port because port 8000 was already occupied by an unrelated local process. Confirmed with a listener query; no unrelated process was stopped. Recovery: remapped the container API to host port 18000.


- 2026-11-13: First completed section 4.1 API run exposed weak top-k ranking from the offline feature-hashing embedding. The run trace showed generic cancellation passages ahead of the modifying clause. Recovery: added lexical/explicit-clause reranking over FAISS candidates before returning passages; re-run the section 4.1 case and evaluation before claiming metric improvement.


## Measured run and scale results

2026-11-13, fixed one-second model stub, v2 prompt, complete-run metric captured from Locust submission through the final result. The local run had zero request failures. Results are a development-host measurement, not a production capacity guarantee.

| RQ worker replicas | Concurrent Locust users | Run duration | Completed runs | Complete-run RPS | p50 | p95 | 60 s SLO |
|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 1 | 45 s | 4 | 0.092 | 9.4 s | 10 s | Met |
| 1 | 10 | 100 s | 10 | 0.102 | 58 s | 96 s | Failed |
| 3 | 10 | 100 s | 30 | 0.303 | 27 s | 36 s | Met |

At the tested 10-user concurrency, one worker misses the target; three replicas reduce p95 by 62.5% and improve completed-run throughput by about 2.97x. The responsible component is the single serialized RQ worker queue: model stub delay is fixed and the API continues accepting requests without error. These tests identify a failure at 10 concurrent users with one worker; they do not establish an exact threshold between 1 and 10. CSVs are checked into `eval/locust/`.

## Measured cache effect

`eval.cache_report.json` records one cold pass over three retrieval queries and ten warm passes. Cold p95 was 88.16 ms; warm p95 was 0.0311 ms, a 99.96% reduction. Cold p50 was 5.347 ms and warm p50 was 0.0140 ms. On this local zero-priced stub, provider cost per run is $0.00 before and after caching, and model-call count is unchanged; the benchmark cannot establish savings for a priced provider. Retrieval and embedding cache latency is measured separately from complete-run load latency.

