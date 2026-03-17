from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

celery = Celery(
    "invoice_tasks",
    broker=f"{REDIS_URL}/0",
    backend=f"{REDIS_URL}/1",
    include=["tasks"],
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
)