from __future__ import annotations

import ast
from pathlib import Path

import hmde

REPO_ROOT = Path(hmde.__file__).resolve().parents[3]
FORBIDDEN = (
    "hmde.api",
    "hmde.analytics",
    "hmde.etl",
    "hmde.main",
    "hmde.services",
    "httpx",
    "requests",
)


def _imported_modules(source: str) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
            modules.update(f"{node.module}.{alias.name}" for alias in node.names)
    return modules


def test_network_runtime_does_not_import_api_etl_analytics_or_http() -> None:
    offenders: dict[str, list[str]] = {}
    for path in Path(REPO_ROOT, "backend", "src", "hmde", "network").rglob("*.py"):
        if path.name == "__main__.py":
            continue
        modules = sorted(
            module
            for module in _imported_modules(path.read_text(encoding="utf-8"))
            if module == "hmde" or any(module.startswith(prefix) for prefix in FORBIDDEN)
        )
        if modules:
            offenders[str(path.relative_to(REPO_ROOT))] = modules
    assert offenders == {}
