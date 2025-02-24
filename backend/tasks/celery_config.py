from celery import Celery
from config.settings import settings

celery_app = Celery(
    "network_app",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["agents.data_ingestion", "agents.eda_preprocessing", "agents.prediction"]
)
