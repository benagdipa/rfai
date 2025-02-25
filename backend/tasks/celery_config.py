from celery import Celery
from config.settings import settings
from utils.logger import logger
from celery.signals import worker_process_init, celeryd_after_setup
import os

# Validate required settings
def _validate_settings() -> None:
    """Ensure required Celery settings are present."""
    required = ["CELERY_BROKER_URL", "CELERY_RESULT_BACKEND"]
    missing = [key for key in required if not hasattr(settings, key) or not getattr(settings, key)]
    if missing:
        logger.error(f"Missing required Celery settings: {missing}")
        raise ValueError(f"Missing Celery settings: {missing}")

# Celery application configuration
def configure_celery() -> Celery:
    """Configure and return a Celery instance."""
    _validate_settings()

    celery_app = Celery(
        "network_app",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
        include=[
            "agents.data_ingestion",
            "agents.eda_preprocessing",
            "agents.prediction",
            "agents.issue_detection",
            "agents.kpi_monitoring",
            "agents.schema_learning",
            "agents.root_cause_analysis",
            "agents.optimization_proposal"
        ]
    )

    # Celery configuration
    celery_app.conf.update(
        # Task settings
        task_serializer="json",
        accept_content=["json"],  # Only accept JSON-serialized tasks
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,

        # Task execution settings
        task_track_started=True,  # Track task start time
        task_time_limit=3600,     # 1 hour hard limit per task
        task_soft_time_limit=3300,  # 55 minutes soft limit
        task_acks_late=True,      # Acknowledge tasks after completion (for reliability)

        # Broker settings
        broker_connection_retry_on_startup=True,
        broker_connection_max_retries=5,
        broker_connection_timeout=10,

        # Result backend settings
        result_expires=86400,     # Results expire after 24 hours
        result_persistent=True,   # Persist results across restarts

        # Worker settings
        worker_prefetch_multiplier=1,  # Process one task at a time per worker
        worker_concurrency=os.cpu_count() or 4,  # Default to CPU count or 4

        # Task routing
        task_routes={
            "agents.data_ingestion.*": {"queue": "ingestion"},
            "agents.eda_preprocessing.*": {"queue": "preprocessing"},
            "agents.prediction.*": {"queue": "prediction"},
            "agents.issue_detection.*": {"queue": "analysis"},
            "agents.kpi_monitoring.*": {"queue": "monitoring"},
            "agents.schema_learning.*": {"queue": "schema"},
            "agents.root_cause_analysis.*": {"queue": "analysis"},
            "agents.optimization_proposal.*": {"queue": "optimization"}
        },

        # Task default settings
        task_default_retry_delay=60,  # Retry after 60 seconds
        task_max_retries=3,           # Max 3 retries
    )

    # Log Celery configuration
    logger.info(
        f"Celery configured: broker={settings.CELERY_BROKER_URL}, "
        f"backend={settings.CELERY_RESULT_BACKEND}, "
        f"workers={celery_app.conf.worker_concurrency}"
    )

    return celery_app

# Initialize Celery instance
celery_app = configure_celery()

# Signal to initialize worker process
@worker_process_init.connect
def init_worker(**kwargs) -> None:
    """Initialize worker process with logging."""
    logger.info(f"Celery worker process initialized: PID={os.getpid()}")

# Signal after Celery daemon setup
@celeryd_after_setup.connect
def setup_logging(sender, instance, conf, **kwargs) -> None:
    """Ensure logging is set up after Celery daemon starts."""
    logger.info(f"Celery worker {sender} started with config: {conf}")

# Utility function to check Celery health
def check_celery_health() -> Dict[str, Any]:
    """
    Check the health of the Celery application.

    Returns:
        dict: Health status and details.
    """
    try:
        # Inspect active workers
        inspector = celery_app.control.inspect()
        active_workers = inspector.active()
        if not active_workers:
            logger.warning("No active Celery workers detected")
            return {
                "status": "unhealthy",
                "details": "No active workers"
            }
        
        worker_count = len(active_workers)
        active_tasks = sum(len(tasks) for tasks in active_workers.values())
        logger.debug(f"Celery health: {worker_count} workers, {active_tasks} active tasks")
        return {
            "status": "healthy",
            "details": {
                "worker_count": worker_count,
                "active_tasks": active_tasks
            }
        }
    except Exception as e:
        logger.error(f"Celery health check failed: {e}")
        return {
            "status": "unhealthy",
            "details": str(e)
        }

if __name__ == "__main__":
    # Test Celery configuration
    health = check_celery_health()
    print(f"Celery Health: {health}")