# Engineering conventions

- **Status:** Draft; validated and completed in E1
- **Version:** 0.1
- **Date:** 2026-11-04

This document defines the detailed engineering conventions referenced by [`AGENTS.md`](../../AGENTS.md). It applies to all specs. Commands are proposed and will be confirmed once the repository skeleton exists in E1.

## 1. Structure

The proposed structure is in [Architecture overview](overview.md). Summary:

- `backend/` — API, ETL, analysis and Python tests.
- `frontend/` — React/TypeScript application.
- `docs/` — stable reference documentation.
- `specs/` — active SDD specs and templates.
- `compose.yaml` — development services.
- `infra/` — Dockerfiles and container assets.
- `data/` — local raw data, outside Git.

## 2. Planned commands

Confirmed in E1; they are not considered available until then.

| Action | Planned command |
|---|---|
| Sync backend | `uv sync` |
| Format Python | `uv run ruff format .` |
| Lint Python | `uv run ruff check .` |
| Backend tests | `uv run pytest` |
| Tests with coverage | `uv run pytest --cov` |
| Frontend development | `npm run dev` |
| Frontend build | `npm run build` |
| Frontend typecheck | `npm run typecheck` |
| Frontend lint | `npm run lint` |
| Start PostgreSQL | `docker compose up -d db` |
| Start the full environment | `docker compose up` |

## 3. Code style

### Python

- Python version fixed in E1 and documented in `pyproject.toml`.
- Static typing on public functions and models.
- Pydantic v2 for API and configuration schemas.
- SQLAlchemy 2.0 with typed declarative models.
- Ruff for formatting and lint.
- Names of classes, tables, columns, endpoints and variables in English.
- No comments that restate what the code already says. Comments explain non-obvious decisions.
- No `print`; use structured logging.

### TypeScript / React

- TypeScript in strict mode.
- Functional components and hooks.
- API types generated from OpenAPI; never hand-written.
- Avoid `any`; if unavoidable, justify it.
- Server state with TanStack Query; local UI state when appropriate.
- Shareable filters in the URL.
- Existing CSS for styling; no UI libraries or styling frameworks without justification. Tailwind is deferred.

### SQL and data

- Alembic migrations reviewed; never use `autogenerate` without inspection.
- Explicit foreign keys and constraints.
- Raw data is never edited by hand.
- Every transformation leaves a trace.
- Seed data lives in versioned fixtures, not in the production database.

## 4. Testing

| Level | Tool | Location |
|---|---|---|
| Backend unit | pytest | `backend/tests/unit` |
| Backend integration | pytest + PostgreSQL | `backend/tests/integration` |
| API contract | pytest + OpenAPI | `backend/tests/contract` |
| Data | pytest + fixtures | `backend/tests/data` |
| Frontend | Vitest + React Testing Library | `frontend/src/**/*.test.tsx` |
| End-to-end | Playwright | `frontend/e2e` |

Rules:

- Every acceptance criterion has at least one test.
- Integration tests use real PostgreSQL, not SQLite.
- A failing test is never deleted without justification and recorded debt.
- Tests do not depend on execution order.

## 5. Working boundaries

The canonical Always / Ask first / Never boundaries are in [`AGENTS.md`](../../AGENTS.md). This document adds only the detailed code-level rules that support them.

## 6. Documentation

- All project content is written in English: documentation, code, identifiers, API descriptions, UI copy and commit messages.
- Conversation with the project owner may be in Spanish; deliverables remain in English.
- Dates use ISO 8601.
- Links are relative.
- One source of truth per concern; see [docs/README.md](../README.md).
- Specs may be revised while in draft, clarification or approval. After validation, a behavior change requires a new spec or an explicit versioned revision with a changelog.

## 7. Git and review

- Small changes with one purpose.
- The commit message describes the what and the why.
- Every PR links the spec or ADR it implements.
- Unrelated refactors are not mixed with the feature.
- Generated code that can be regenerated is not committed (OpenAPI, types, builds).
