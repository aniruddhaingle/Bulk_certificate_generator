import os

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "bulk_certificate_gen",
    broker=settings.celery_broker_url or settings.redis_url,
    backend=settings.celery_result_backend or settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # acks_late + reject_on_worker_lost: if a worker process dies mid-task, the
    # broker redelivers the message to another worker instead of losing it.
    # Safe here because every task claims its row atomically before doing any
    # real work (see try_claim_pending / start_processing) — a redelivered
    # task either finds the row already claimed/finished and no-ops, or finds
    # it genuinely still pending and reprocesses it cleanly.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_time_limit=300,
    task_soft_time_limit=270,
)

# Test-only escape hatch: run tasks synchronously in-process with no broker.
# Never set this in .env for real docker-compose usage.
if os.environ.get("CELERY_TASK_ALWAYS_EAGER", "").lower() in ("1", "true", "yes"):
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
