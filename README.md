# Air Passenger Claim Triage

Production-style, asynchronous triage for claims under the included DGCA passenger-rights CAR. The service returns a **provisional recommendation with cited passages**; an authorized customer-relations officer makes the decision. It never authorizes payment.

## Start from a clean clone

From this directory, build and start the complete stack in the foreground:

```sh
docker compose up --build
```

To start it in the background instead:

```sh
docker compose up --build -d
```

For a staged startup, run these commands in order:

```sh
# 1. Start Redis, used by the API and RQ worker.
docker compose up -d redis

# 2. Build the application image and populate/update the retrieval index.
docker compose run --build --rm indexer

# 3. Build and start the API, worker, model stub, and web client.
docker compose up -d --build api agent-worker model-stub frontend

# 4. Start monitoring, tracing, and container metrics.
docker compose up -d prometheus grafana jaeger redis-exporter cadvisor

# 5. Check container status and follow logs when needed.
docker compose ps
docker compose logs -f api agent-worker
```

The indexer is idempotent. Compose also runs it as a dependency before starting the API and worker, so the staged sequence can perform an additional incremental pass. To stop the stack, press `Ctrl+C` when running in the foreground, or run `docker compose down` when it is in the background. Compose volumes preserve container data and the FAISS index; add `-v` to `docker compose down` only when you intend to delete that data.

The stack includes the corpus indexer, FastAPI, scalable RQ agent workers, Redis, the React client, a fixed-delay model stub, Prometheus, Grafana, Jaeger, Redis exporter, and cAdvisor. The indexer uses a deterministic local hashing embedding for an offline clean-clone start; a local sentence-transformer model can be injected at runtime with `RAG_EMBEDDING_MODEL`. The model stub is for load/failure testing. Set `AGENT_MODE=llm` in your untracked `.env` to use Ollama as the agent model. The API and worker connect to the Ollama server running on the host. In LLM mode, provider failures fail the run visibly; they do not silently substitute a demo result.

Open the UI at `http://localhost:5173`, API docs at `http://localhost:18000/docs`, Grafana at `http://localhost:3000`, Prometheus at `http://localhost:9090`, and Jaeger at `http://localhost:16686`. Container data and the FAISS index persist in Compose volumes.

## Runtime model configuration

Copy `.env.example` to `.env`; keep that file untracked. For a host-installed Ollama server, set `AGENT_MODE=llm`, set `MODEL_API_URL` to its OpenAI-compatible chat-completions endpoint reachable from Compose containers, and set `MODEL_ID` to an Ollama model already pulled on the host (for example, a locally installed 7B Q4 model). `MODEL_API_KEY` can remain empty for local Ollama. Set `MODEL_TIMEOUT_SECONDS` high enough for your hardware and tune `MODEL_MAX_TOKENS` to cap generation length (256 by default), and `MAX_TOOL_CALLS` to cap retrieval planning steps (3 by default). Calls use deterministic sampling. `PROMPT_VERSION` selects the versioned prompt artifact, and the input/output per-million prices remain zero for local inference. The sample `.env.example` stays provider-neutral; no provider endpoint, model ID, or credentials are committed. Local model embeddings are selected separately through `RAG_EMBEDDING_MODEL`.

To use the fixed-delay stub for load tests, set runtime `MODEL_API_URL` to the Compose stub's chat-completions route, set a test `MODEL_ID`, set `AGENT_MODE=llm`, then run/recreate the API and workers. The stub never makes a final legal determination. Do not use its result as an entitlement decision.

## API

The public contracts are documented in [contracts/interfaces.md](contracts/interfaces.md) and [contracts/claim-submission.json](contracts/claim-submission.json); FastAPI publishes the generated OpenAPI at `/openapi.json`. Submission validates, screens and persists before queueing, then returns a run ID. Poll `GET /api/v1/claims/{id}` and `GET /api/v1/claims/{id}/result`. Feedback uses `POST /api/v1/claims/{id}/feedback`; aggregate feedback is at `/api/v1/feedback/summary`. Sampled live quality is at `/api/v1/quality/timeseries`.

Malformed requests are stored in the quarantine table with field-level errors and never start a worker job. `X-Request-ID` may be supplied by a caller; otherwise the API creates it and persists it as the run correlation ID.

## Agents and retrieval

In LLM mode the LangGraph research agent chooses among LangChain structured tools for corpus search, clause lookup and validated claim-field lookup. It reads each result before selecting a follow-up query, up to six tool calls. Separate analysis, entitlement and verification stages receive the retrieved evidence. Provider calls have a timeout, bounded retries and a circuit breaker; a failed provider run is marked failed, with no silent demo substitution. Tool queries, passages, prompt version, token/cost record, latency and verification outcome are retained in the run result.

Chunks are about 1,000 characters with 150-character overlap, preferring paragraph/sentence boundaries, and retain source/page/section and a document-content hash. This is designed to keep an amount with nearby eligibility clauses while overlap preserves cross-boundary conditions. Retrieval searches the apparent entitlement and linked conditions/facilities; the section 4.1 scenario must surface both paragraph 3.3.2 and 3.8.1(a). The FAISS index appends only new/changed chunks and retires old versions. Re-embed the active chunks without reparsing PDFs using `docker compose run --rm indexer python -m rag.retrieval --reembed`; routine refresh is `--incremental`.

Index freshness, active chunk count, configured embedding strategy, build duration and throughput are stored in the index sidecar and exported as metrics. Retrieval and embedding results are cached; per-client rate limiting uses Redis with a process-local development fallback.

## Evaluation, cost and feedback

The fixed 20-scenario corpus, including section 4.1, is in `eval/scenarios.json`. Run the batch comparison in the container after configuring a provider:

```sh
docker compose exec api python -m eval.evaluate --mode llm --before v1 --after v2 --output eval/report.json
```

The evaluator compares both prompt versions on the same scenarios, computes groundedness, context relevance, faithfulness and hallucination rate, reports before/after deltas and per-step costs, and normalizes cost to 100 runs. The exact metric formulas and limitations are in [eval/README.md](eval/README.md). Do not treat demo-mode runs as prompt measurements. Warm/cold retrieval cache timings can be collected with `python -m eval.cache_benchmark` in the API container.

Feedback is persisted and aggregated. A stable 10% sample of completed runs is scored and available as a time series; live scores are labeled as citation/verifier proxies because arbitrary live claims have no known reference outcome. Batch evaluation metrics and live proxies are not conflated.

## Observability, scale and SLO

Prometheus scrapes API, agent worker, Redis exporter, container metrics, Grafana, Jaeger and the model stub. Grafana provisions the `Air Claim AgentOps` dashboard; traces export to Jaeger. Scale workers independently with:

```sh
docker compose up --scale agent-worker=3
```

The predeclared complete-run p95 SLO is 60 seconds from submission through the final persisted result, justified by the multi-condition review in assignment section 1. `loadtest/locustfile.py` measures submission-to-result against the fixed-delay model stub. Measured local-stub RPS, p50/p95, SLO result, worker scaling and cache deltas are in [docs/ops-and-measurements.md](docs/ops-and-measurements.md) and [eval/MEASURED.md](eval/MEASURED.md). These fixture measurements are not provider performance or pricing claims.

The runbook, deployment-boundary rationale and genuine development incident log are also in [docs/ops-and-measurements.md](docs/ops-and-measurements.md). The per-requirement status and measurement evidence are in [requirements_traceability.md](requirements_traceability.md).
