import sentry_sdk
from celery import Celery
from sentry_sdk.integrations.celery import CeleryIntegration

from src.config import settings

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release=settings.APP_VERSION,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,
        integrations=[CeleryIntegration(monitor_beat_tasks=True)],
    )

celery_app = Celery(
    "cs2-analytics",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "src.tasks.demo_processing.*": {"queue": "demo-processing"},
        "src.tasks.pro_ingestion.*": {"queue": "pro-ingestion"},
    },
    # Celery Beat schedule — periodic tasks
    beat_schedule={
        "ingest-pro-demos-hltv": {
            "task": "src.tasks.pro_ingestion.ingest_hltv",
            "schedule": 1800.0,  # every 30 minutes
        },
        "ingest-pro-demos-faceit": {
            "task": "src.tasks.pro_ingestion.ingest_faceit",
            "schedule": 1800.0,  # every 30 minutes
        },
        "ml-drift-daily": {
            "task": "src.tasks.ml_drift.compute_drift",
            "schedule": 86400.0,  # daily
        },
    },
)

celery_app.autodiscover_tasks(["src.tasks"])
