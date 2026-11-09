from __future__ import annotations

import ast
from pathlib import Path

import hmde

REPO_ROOT = Path(hmde.__file__).resolve().parents[3]
FORBIDDEN = ("hmde.api", "hmde.etl", "hmde.main", "hmde.services")


def _imported_modules(source: str) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.update(f"{node.module}.{alias.name}" for alias in node.names)
            modules.add(node.module)
    return modules


def test_quality_runtime_does_not_import_api_etl_or_analytics() -> None:
    paths = Path(REPO_ROOT, "backend", "src", "hmde", "quality").rglob("*.py")
    offenders = {}
    for path in paths:
        modules = sorted(
            module
            for module in _imported_modules(path.read_text(encoding="utf-8"))
            if module == "hmde" or any(module.startswith(prefix) for prefix in FORBIDDEN)
        )
        if modules:
            offenders[str(path.relative_to(REPO_ROOT))] = modules
    assert offenders == {}
