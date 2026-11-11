"""FastAPI application entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hmde.api.routes.albums import router as albums_router
from hmde.api.routes.analytics import router as analytics_router
from hmde.api.routes.artists import router as artists_router
from hmde.api.routes.bands import router as bands_router
from hmde.api.routes.credits import router as credits_router
from hmde.api.routes.graph import router as graph_router
from hmde.api.routes.health import router as health_router
from hmde.api.routes.producers import router as producers_router
from hmde.api.routes.search import router as search_router
from hmde.api.routes.taxonomy import router as taxonomy_router
from hmde.core.config import get_settings
from hmde.core.logging import configure_logging

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("Starting HMDE API in %s", settings.app_env)

    app = FastAPI(title="HMDE API", version="0.1.0")
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_methods=["GET"],
            allow_headers=["*"],
            allow_credentials=False,
        )
    app.include_router(health_router)
    app.include_router(bands_router)
    app.include_router(artists_router)
    app.include_router(albums_router)
    app.include_router(credits_router)
    app.include_router(producers_router)
    app.include_router(graph_router)
    app.include_router(analytics_router)
    app.include_router(search_router)
    app.include_router(taxonomy_router)
    return app


app = create_app()
