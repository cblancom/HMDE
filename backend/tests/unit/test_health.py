from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.exc import SQLAlchemyError

from hmde.db.session import get_db


class HealthySession:
    def execute(self, _statement: object) -> None:
        return None


class FailingSession:
    def execute(self, _statement: object) -> None:
        raise SQLAlchemyError("database unavailable")


def _override_session(session: object):
    def override() -> Iterator[object]:
        yield session

    return override


def test_health_returns_ok(client, app_instance) -> None:
    app_instance.dependency_overrides[get_db] = _override_session(HealthySession())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_returns_degraded_without_leaking_details(client, app_instance) -> None:
    app_instance.dependency_overrides[get_db] = _override_session(FailingSession())

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "unavailable"}
    assert "database unavailable" not in response.text


def test_health_is_documented_in_openapi(client) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/health" in response.json()["paths"]


def test_health_does_not_require_a_session_for_openapi(client) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "get" in response.json()["paths"]["/health"]
