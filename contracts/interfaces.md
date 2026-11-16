# External API data contracts (v1)

FastAPI publishes the generated OpenAPI contract at `/openapi.json` and `/docs`. The following routes are externally supported:

| Method/path | Contract and behavior |
|---|---|
| `GET /health`, `GET /api/v1/health` | `HealthResponse {status: "ok"}` |
| `POST /api/v1/claims` | `ClaimSubmission` below; returns `202 ClaimAccepted` with run ID. Validates and screens before persistence/enqueue. |
| `GET /api/v1/claims/{claim_id}` | `ClaimStatusResponse`; `404` for unknown ID. |
| `GET /api/v1/claims/{claim_id}/result` | `ClaimResultResponse` with evidence, prompt version, costs, trace and verification; `202` while pending, `409` on failure. |
| `POST /api/v1/claims/{claim_id}/feedback` | `FeedbackSubmission`; only completed runs; feedback is persisted. |
| `GET /api/v1/feedback/summary` | Aggregated satisfactory/unsatisfactory counts. |
| `GET /api/v1/quality/timeseries` | Sampled quality observations. |
| `GET /api/v1/metrics` | Persisted claim counts and recent run rows for the UI. |
| `GET /metrics` | Prometheus exposition for API process. |

`ClaimSubmission` forbids unknown keys. `complaint` is a required string, 1..MAX_COMPLAINT_LENGTH characters; `flight_number` is an optional flight designator; `disruption_type` is optional and one of denied boarding, cancellation, delay, downgrading; times use 24-hour `HH:MM`; notice hours are 0..8760; block time hours are greater than 0 and at most 48; `actual_time` requires `scheduled_time`. Injection/toxicity screening runs before a row is queued. Invalid schema records are quarantined with field-level error locations and never create an agent job.

`FeedbackSubmission` is `{satisfactory: boolean, reason: string}`; reason length is 3..2000. Error responses use `{error:{code,message,details,request_id}}`. All interfaces use JSON except the Prometheus text endpoint.
