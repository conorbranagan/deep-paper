from celery import Celery
from app.config import settings, init_config

# Initialize configuration
init_config()

# Create Celery instance
celery_app = Celery(
    "paper_indexer",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes time limit for tasks
    worker_prefetch_multiplier=1,  # Process one task at a time per worker
)
