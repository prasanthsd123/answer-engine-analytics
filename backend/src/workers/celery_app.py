"""
Celery application configuration.
"""

from celery import Celery

from ..config import settings

celery_app = Celery(
    "answer_engine_analytics",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "src.workers.query_worker",
        "src.workers.analysis_worker",
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task settings
    task_soft_time_limit=300,  # 5 minutes soft limit
    task_time_limit=600,  # 10 minutes hard limit
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Rate limiting
    task_default_rate_limit="10/m",

    # Result expiration
    result_expires=3600,  # 1 hour

    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,

    # Beat schedule for periodic tasks
    beat_schedule={
        "daily-metrics-calculation": {
            "task": "src.workers.analysis_worker.calculate_all_daily_metrics",
            "schedule": 86400.0,  # Daily
        },
    },
)


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    print(f"Request: {self.request!r}")
    return "Celery is working!"
