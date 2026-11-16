"""RQ worker runner with metrics and OTEL export."""
from prometheus_client import start_http_server
from redis import Redis
from rq import Queue,Worker
from app.config import settings
from app.database import init_db

def configure_tracing():
    if not settings.otel_exporter_endpoint:return
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    provider=TracerProvider(resource=Resource.create({"service.name":"airclaim-worker"}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_endpoint)))
    trace.set_tracer_provider(provider)
def main():
    init_db(); configure_tracing(); start_http_server(8001)
    connection=Redis.from_url(settings.redis_url)
    Worker([Queue(settings.rq_queue_name,connection=connection)],connection=connection).work(with_scheduler=False)
if __name__=="__main__":main()
