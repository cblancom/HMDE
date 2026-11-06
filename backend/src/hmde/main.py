"""FastAPI application entry point."""

import logging

from fastapi import FastAPI

from hmde.api.routes.health import router as health_router
from hmde.core.config import get_settings
from hmde.core.logging import configure_logging

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("Starting HMDE API in %s", settings.app_env)

    app = FastAPI(title="HMDE API", version="0.1.0")
    app.include_router(health_router)
    return app


app = create_app()
