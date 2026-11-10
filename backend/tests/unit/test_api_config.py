from __future__ import annotations

from hmde.core.config import load_settings


def test_cors_origins_default_and_override() -> None:
    settings = load_settings({"DATABASE_URL": "postgresql+psycopg://test"})
    assert "http://localhost:5173" in settings.cors_origins

    configured = load_settings(
        {
            "DATABASE_URL": "postgresql+psycopg://test",
            "CORS_ORIGINS": "https://hmde.example, http://localhost:3000/",
        }
    )
    assert configured.cors_origins == ("https://hmde.example", "http://localhost:3000")
