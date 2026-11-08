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


def _network_import_offenders(paths: list[Path]) -> dict[str, list[str]]:
    offenders = {
        str(path.relative_to(REPO_ROOT)): sorted(
            _imported_roots(path.read_text(encoding="utf-8")) & NETWORK_MODULES
        )
        for path in paths
    }
    return {path: modules for path, modules in offenders.items() if modules}


def test_api_runtime_does_not_import_network_clients() -> None:
    hmde_root = REPO_ROOT / "backend" / "src" / "hmde"
    paths = [
        path for path in hmde_root.rglob("*.py") if "etl" not in path.relative_to(hmde_root).parts
    ]
    paths.append(REPO_ROOT / "scripts" / "build_e2_fixtures.py")

    assert _network_import_offenders(paths) == {}


def test_network_clients_are_confined_to_the_musicbrainz_client() -> None:
    paths = list((REPO_ROOT / "backend" / "src" / "hmde" / "etl").rglob("*.py"))

    assert _network_import_offenders(paths) == {
        "backend/src/hmde/etl/musicbrainz/client.py": ["httpx"]
    }


def _imported_modules(source: str) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.update(f"{node.module}.{alias.name}" for alias in node.names)
            modules.add(node.module)
    return modules


def test_api_runtime_does_not_import_ingestion_packages() -> None:
    hmde_root = REPO_ROOT / "backend" / "src" / "hmde"
    paths = [
        path for path in hmde_root.rglob("*.py") if "etl" not in path.relative_to(hmde_root).parts
    ]

    offenders = {
        str(path.relative_to(REPO_ROOT)): sorted(
            module
            for module in _imported_modules(path.read_text(encoding="utf-8"))
            if module == "hmde.etl" or module.startswith("hmde.etl.")
        )
        for path in paths
    }
    assert {path: modules for path, modules in offenders.items() if modules} == {}


def test_normalization_does_not_import_api_or_analytics_packages() -> None:
    hmde_root = REPO_ROOT / "backend" / "src" / "hmde"
    paths = list((hmde_root / "normalization").rglob("*.py"))
    forbidden = ("hmde.api", "hmde.main", "hmde.services")

    offenders = {
        str(path.relative_to(REPO_ROOT)): sorted(
            module
            for module in _imported_modules(path.read_text(encoding="utf-8"))
            if module == "hmde" or any(module.startswith(prefix) for prefix in forbidden)
        )
        for path in paths
    }
    assert {path: modules for path, modules in offenders.items() if modules} == {}


def test_frontend_does_not_add_deferred_e2_dependencies() -> None:
    package = json.loads((REPO_ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    dependencies = set(package.get("dependencies", {})) | set(package.get("devDependencies", {}))

    assert dependencies.isdisjoint(FRONTEND_SCOPE_EXCLUSIONS)
