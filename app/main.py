"""FastAPI startup with correlated logs, OpenTelemetry, and Prometheus metrics."""
import logging,os,time,json
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI,Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST,generate_latest
from app.api.errors import register_error_handlers
from app.api.routes import router
from app.config import settings
from app.database import init_db
from app.metrics import REQUESTS,INDEX_AGE,INDEX_CHUNKS,INDEX_BUILD_SECONDS,INDEX_CHUNKS_PER_SECOND
from app.schemas.claims import HealthResponse
logging.basicConfig(level=getattr(logging,settings.log_level,logging.INFO),format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger=logging.getLogger("app.request")
try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    provider=TracerProvider(resource=Resource.create({"service.name":"airclaim-api"}))
    if settings.otel_exporter_endpoint:provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_endpoint)))
    trace.set_tracer_provider(provider)
except ImportError: pass
app=FastAPI(title=settings.app_title,version=settings.app_version,description="Provisional claim triage; never authorizes payment.")
try:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    FastAPIInstrumentor.instrument_app(app)
except ImportError:pass
app.add_middleware(CORSMiddleware,allow_origins=settings.allowed_origins,allow_credentials=False,allow_methods=["GET","POST","OPTIONS"],allow_headers=["Content-Type","X-Request-ID","X-Client-ID"])
register_error_handlers(app); init_db()
@app.middleware("http")
async def request_context(request:Request,call_next):
    request_id=request.headers.get("X-Request-ID") or str(uuid4()); request.state.request_id=request_id
    started=time.perf_counter(); status_code=500
    try:
        response=await call_next(request); status_code=response.status_code; response.headers["X-Request-ID"]=request_id; return response
    finally:
        elapsed=time.perf_counter()-started; REQUESTS.labels(request.method,request.url.path,str(status_code)).inc()
        logger.info("request_complete",extra={"request_id":request_id,"correlation_id":request_id,"method":request.method,"path":request.url.path,"status_code":status_code,"duration_seconds":round(elapsed,4)})
@app.get("/health",response_model=HealthResponse)
async def health():return HealthResponse()
@app.get("/metrics",include_in_schema=False)
async def prometheus_metrics():
    manifest_path=Path(os.getenv("RAG_INDEX_PATH","data/rag/faiss.index")).with_suffix(".json")
    if manifest_path.exists():
        try:
            raw=json.loads(manifest_path.read_text(encoding="utf-8")); manifest=raw.get("manifest",{}) if isinstance(raw,dict) else {}
            from datetime import datetime,timezone
            built=datetime.fromisoformat(manifest["built_at"]); INDEX_AGE.set(max(0,(datetime.now(timezone.utc)-built).total_seconds()))
            INDEX_CHUNKS.set(manifest.get("active_chunks",0)); INDEX_BUILD_SECONDS.set(manifest.get("last_pipeline_seconds",0)); INDEX_CHUNKS_PER_SECOND.set(manifest.get("last_pipeline_chunks_per_second",0))
        except Exception:logger.exception("Unable to refresh index metrics")
    return Response(generate_latest(),media_type=CONTENT_TYPE_LATEST)
app.include_router(router,prefix="/api/v1",tags=["claims"])

