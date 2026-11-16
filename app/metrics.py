"""Prometheus application metrics shared by API and worker."""
from prometheus_client import Counter,Gauge,Histogram
RUNS=Counter("claim_runs_total","Claim runs by final state",["state"])
RUN_LATENCY=Histogram("claim_run_seconds","Submission-to-final-result latency",buckets=(1,2,5,10,20,30,60,120,300))
REQUESTS=Counter("http_requests_total","HTTP requests",["method","path","status"])
REJECTED=Counter("claim_rejected_total","Rejected claims by reason")
FEEDBACK=Counter("claim_feedback_total","Feedback received",["satisfactory"])
INDEX_CHUNKS=Gauge("rag_index_chunks","Active chunks in index")
INDEX_AGE=Gauge("rag_index_age_seconds","Age of active index")
INDEX_BUILD_SECONDS=Gauge("rag_index_build_seconds","Last indexing pipeline duration")
INDEX_CHUNKS_PER_SECOND=Gauge("rag_index_chunks_per_second","Last indexing throughput")
QUALITY=Gauge("claim_quality_score","Sampled live quality scores",["metric"])
