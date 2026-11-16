"""Redis/RQ queue integration for claim processing jobs."""

from __future__ import annotations

import time
from uuid import UUID

from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError, TimeoutError as RedisTimeoutError
from rq import Queue

from app.config import settings


class QueueUnavailableError(RuntimeError):
    """Raised when Redis cannot accept a new background job."""


def get_queue() -> Queue:
    """Create a queue only after confirming Redis is reachable."""
    try:
        connection = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=2,
            socket_timeout=3,
        )
        connection.ping()
        return Queue(settings.rq_queue_name, connection=connection)
    except RedisError as exc:
        raise QueueUnavailableError("Redis is unavailable.") from exc


def enqueue_claim(claim_id: UUID) -> None:
    """Enqueue idempotently with a small bounded retry for Redis connectivity."""
    from app.workers.tasks import process_claim

    job_id = str(claim_id)
    for attempt in range(3):
        try:
            queue = get_queue()
            # A previous enqueue may have succeeded even if its reply was lost.
            if queue.fetch_job(job_id) is None:
                queue.enqueue(process_claim, job_id, job_id=job_id, job_timeout=600)
            return
        except QueueUnavailableError as exc:
            if not isinstance(exc.__cause__, (RedisConnectionError, RedisTimeoutError)) or attempt == 2:
                raise
            time.sleep(0.2 * (attempt + 1))
        except (RedisConnectionError, RedisTimeoutError) as exc:
            if attempt == 2:
                raise QueueUnavailableError("Redis is unavailable.") from exc
            time.sleep(0.2 * (attempt + 1))
        except RedisError as exc:
            raise QueueUnavailableError("Redis is unavailable.") from exc
