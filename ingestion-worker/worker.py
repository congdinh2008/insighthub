"""Public ARQ entry point for the separately built ingestion-worker service."""

from app.worker import WorkerSettings as SharedWorkerSettings


# ARQ reads direct class attributes, so an alias preserves the registered
# functions and all settings without duplicating its implementation.
WorkerSettings = SharedWorkerSettings


def create_worker_settings() -> SharedWorkerSettings:
    """Construct the configured entry point for packaging checks and local inspection."""
    return SharedWorkerSettings()
