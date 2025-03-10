import os
from celery import Celery
from celery.schedules import schedule

CELERY_BEAT_SCHEDULER = "sqlalchemy_celery_beat.schedulers:DatabaseScheduler"

broker_url = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
result_backend = os.getenv("DATABASE_URL", broker_url)

celery_app = Celery("worker", broker=broker_url, backend=result_backend)

celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_ignore_result=False,
    result_expires=3600,
    task_track_started=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    beat_scheduler=CELERY_BEAT_SCHEDULER,
    sqlalchemy_scheduler_connection_uri=os.getenv("DATABASE_URL"),
    sqlalchemy_scheduler_table_schema="celery_schema",
)

celery_app.autodiscover_tasks(["managers.telegram_manager"])

from managers.telegram_manager import send_message_task
