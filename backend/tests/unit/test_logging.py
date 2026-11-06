from __future__ import annotations

import logging

import hmde.main as main_module
from hmde.core.config import Settings
from hmde.core.logging import resolve_log_level


def test_resolve_log_level_accepts_known_and_unknown_values() -> None:
    assert resolve_log_level("debug") == logging.DEBUG
    assert resolve_log_level("WARNING") == logging.WARNING
    assert resolve_log_level("not-a-level") == logging.INFO


def test_create_app_configures_logging_from_settings(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(main_module, "configure_logging", lambda level: calls.append(level))
    monkeypatch.setattr(
        main_module,
        "get_settings",
        lambda: Settings(
            database_url="postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde",
            app_env="test",
            log_level="DEBUG",
        ),
    )

    app = main_module.create_app()

    assert calls == ["DEBUG"]
    assert app.title == "HMDE API"
