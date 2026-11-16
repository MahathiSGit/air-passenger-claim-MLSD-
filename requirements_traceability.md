# Requirement traceability

Implementation evidence in the repository maps to the supplied L1-L6, D1-D8 and assignment A1-A8 requirements. Runtime measurements must be reported from the included commands; a design artifact is not a measurement.

## LLMOps requirements

| Requirement | Evidence and current status |
|---|---|
| L1 | LangGraph re-planning agent calls LangChain StructuredTools over FAISS. Clause-aware chunking, paragraph overlap, local embeddings, lexical reranking, incremental append and `--reembed` are implemented. Section 4.1 targeted retrieval is verified to return exact 3.3.2 and 3.8.1 citations. |
| L2 | Prompts are versioned under `agents/prompts/{v1,v2}`. Every model call and final run records prompt version. Batch comparison is `python -m eval.evaluate`; 20-scenario local-stub metrics and section 4.1 outcome are in `eval/MEASURED.md` and `eval/report.json`. |
| L3 | `eval/scenarios.json` holds 20 scenarios, expected routes and supporting passage text, including section 4.1; CLI evaluator is implemented. Before/after values and metric deltas are in `eval/MEASURED.md`; they are local-stub measurements, not live-provider quality claims. |
| L4 | User text and tool queries are injection/toxicity screened, model outputs are screened, and output filtering blocks unauthorized payment claims. The API validates before queueing and quarantines schema/guardrail errors. |
| L5 | Provider usage or documented character estimates, configured runtime prices, call latency and cost are recorded per model step and summed per run. Stub cost is zero unless nonzero rates are injected. |
| L6 | Caller feedback and reason are persisted and summarized. Stable 10% live sampling writes proxy quality scores; API and Grafana provide a time series. These are labeled proxies, distinct from reference-set evaluation. |

## Platform requirements

| Requirement | Evidence and current status |
|---|---|
| D1 | Pydantic contracts validate type, range, category and cross-field constraints before queueing. Invalid body and guardrail failures are quarantined with field-level errors. |
| D2 | Runtime configuration and `.env.example`; incremental idempotent index CLI records built time, sources, embedding configuration, chunks and throughput, with metrics. Local Compose service endpoints are internal service discovery values. |
| D3 | Compose defines API, worker, Redis, one-shot indexer, model stub, frontend, Prometheus, Grafana, Jaeger, Redis exporter and cAdvisor. Health checks and dependencies are configured. |
| D4 | Runtime model URL, ID, key and price are injected from environment. Local data service endpoints are defined for Compose wiring. |
| D5 | Structured request IDs/correlation IDs span API and agent steps; OTEL exports to Jaeger; Prometheus scrapes services; Grafana dashboard provisions complete-run p50/p95, errors, throughput, availability, resource use and index/quality panels. Stored run result contains tool queries, passages, prompt version, per-step tokens/cost/latency and verification. |
| D6 | A 60-second complete-run p95 SLO is declared before measurement and Locust measures POST through result polling against the fixed-delay stub. Locust measurements at 1 and 10 users with 1 worker and 10 users with 3 workers are recorded in `docs/ops-and-measurements.md` and `eval/locust/`; single-worker p95 first fails at tested concurrency 10. |
| D7 | Embedding/retrieval caches and per-client rate limiting are implemented. `eval.cache_report.json` records a 99.96% warm retrieval p95 reduction; zero-priced stub provider cost remains $0/run before and after. |
| D8 | Redis/queue and FAISS runbooks are documented. Incident log contains actual encoding, port collision and first-run retrieval failures with recovery. |

## Agent/API requirements

| Requirement | Evidence and current status |
|---|---|
| A1 | Bounded LangGraph researcher dynamically selects among LangChain tools, with a six-call maximum and run trace. |
| A2 | Analysis, research, entitlement and verification are distinct stages. Per-run trace and failure handling are persisted. |
| A3 | Verification resolves citations, checks lexical support and prevents unsupported amount/decline outcomes. |
| A4 | Async API submission, status/result, feedback, aggregation, quality and metrics endpoints are defined in `contracts/interfaces.md`. |
| A5 | Model HTTP timeout, bounded retry, shared circuit breaker, tool timeout and safe provider-unavailable fallback are implemented. |
| A6 | Per-step agent/model metrics and traces are exported and retained by run ID. |
| A7 | RQ worker replicas can scale independently; 10-user/3-worker Locust results show 0.303 RPS and 36-second p95 versus 0.102 RPS and 96-second p95 for 1 worker. |
| A8 | Existing frontend submits claims, polls status and shows the result/feedback flow. |

## Measurements still required

Prompt metric values and winners, cache benefit, complete-run load/concurrency results, scaling impact, and a provider-priced cost figure depend on running the included batch/benchmark/load commands with runtime pricing/model configuration. Do not infer these from code or the fixed stub. The stub can verify control flow and system latency, but its zero price and fixed answers do not represent a model provider.


