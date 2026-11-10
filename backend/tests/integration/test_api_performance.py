from __future__ import annotations

import time

from sqlalchemy import event


def _producer_id(api_client) -> str:
    body = api_client.get("/api/v1/producers", params={"limit": 200}).json()
    return next(item["id"] for item in body["items"] if item["band_count"] > 0)


def test_graph_query_count_and_latency_are_bounded(api_client, seeded_session_factory) -> None:
    producer_id = _producer_id(api_client)
    engine = seeded_session_factory.kw["bind"]
    statements: list[str] = []

    def count_selects(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", count_selects)
    started = time.perf_counter()
    try:
        response = api_client.get(
            f"/api/v1/producers/{producer_id}/graph",
            params={"view": "bands", "limit": 20, "depth": 1},
        )
    finally:
        event.remove(engine, "before_cursor_execute", count_selects)
    elapsed = time.perf_counter() - started
    assert response.status_code == 200
    assert len(statements) <= 10
    assert elapsed < 1.0
