from __future__ import annotations

import ast
import json
from pathlib import Path

import hmde

REPO_ROOT = Path(hmde.__file__).resolve().parents[3]
NETWORK_MODULES = {"aiohttp", "httpx", "requests", "socket", "urllib", "urllib3"}
FRONTEND_SCOPE_EXCLUSIONS = {"tailwindcss", "plotly.js", "@plotly/plotly.js"}


def _imported_roots(source: str) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_e2_runtime_does_not_import_network_clients() -> None:
    paths = list((REPO_ROOT / "backend" / "src" / "hmde").rglob("*.py"))
    paths.append(REPO_ROOT / "scripts" / "build_e2_fixtures.py")

    offenders = {
        str(path.relative_to(REPO_ROOT)): sorted(
            _imported_roots(path.read_text(encoding="utf-8")) & NETWORK_MODULES
        )
        for path in paths
    }
    offenders = {path: modules for path, modules in offenders.items() if modules}

    assert offenders == {}


def test_frontend_does_not_add_deferred_e2_dependencies() -> None:
    package = json.loads((REPO_ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    dependencies = set(package.get("dependencies", {})) | set(package.get("devDependencies", {}))

    assert dependencies.isdisjoint(FRONTEND_SCOPE_EXCLUSIONS)
