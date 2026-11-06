from __future__ import annotations

import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://hmde:hmde_dev@localhost:5433/hmde",
)
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("LOG_LEVEL", "WARNING")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from hmde.main import app  # noqa: E402


@pytest.fixture
def app_instance():
    return app


@pytest.fixture
def client(app_instance):
    with TestClient(app_instance) as test_client:
        yield test_client
    app_instance.dependency_overrides.clear()
