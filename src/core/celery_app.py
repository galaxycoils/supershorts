import os
import logging

logger = logging.getLogger(__name__)

try:
    from celery import Celery
except ImportError:
    Celery = None
    logger.warning("Celery not installed, Celery app will not be available.")

# Default Redis broker URL
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

if Celery:
    celery_app = Celery(
        "supershorts",
        broker=REDIS_URL,
        backend=REDIS_URL,
        include=[] # Add task modules here in the future
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
    )
else:
    celery_app = None
