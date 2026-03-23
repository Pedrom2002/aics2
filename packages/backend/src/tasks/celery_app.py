from celery import Celery

from src.config import settings

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
    },
)

celery_app.autodiscover_tasks(["src.tasks"])
