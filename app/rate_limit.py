"""Redis-backed shared rate limits with a bounded local fallback for development."""
from collections import defaultdict
from threading import Lock
from time import monotonic
import logging
from redis import Redis
from app.config import settings
logger=logging.getLogger("app.rate_limit")
class RateLimitExceeded(RuntimeError): pass
_local=defaultdict(list); _lock=Lock()
def check_client_limit(client_id:str)->None:
    key=f"airclaim:rate:{client_id}"
    try:
        client=Redis.from_url(settings.redis_url,socket_connect_timeout=1,socket_timeout=1)
        count=client.incr(key)
        if count==1:client.expire(key,settings.rate_limit_window_seconds)
        if count>settings.rate_limit_per_window:raise RateLimitExceeded("Client rate limit exceeded")
        return
    except RateLimitExceeded:raise
    except Exception:
        logger.warning("Redis rate limiter unavailable; using process-local fallback")
    now=monotonic(); cutoff=now-settings.rate_limit_window_seconds
    with _lock:
        _local[client_id]=[t for t in _local[client_id] if t>cutoff]
        if len(_local[client_id])>=settings.rate_limit_per_window:raise RateLimitExceeded("Client rate limit exceeded")
        _local[client_id].append(now)
