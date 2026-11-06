# Technical plan — SPEC-001 Foundations

- **Status:** Approved
- **Spec:** [spec.md](spec.md)
- **Tasks:** [tasks.md](tasks.md)
- **Stage:** E1
- **Module:** `platform`
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0003](../../docs/01-architecture/adr/ADR-0003-synchronous-sqlalchemy.md), [ADR-0006](../../docs/01-architecture/adr/ADR-0006-read-only-api.md)

## 1. Solution summary

E1 creates a reproducible monorepo with three development services:

- PostgreSQL 16 for persistence.
- A FastAPI backend with a database health check, synchronous SQLAlchemy and an Alembic baseline.
- A React + TypeScript + Vite web shell that reads the API health status through a proxy.

The backend and frontend have test harnesses, lint/format/typecheck/build commands and a GitHub Actions pipeline. There are no domain tables, domain endpoints, ingestion code or analytics.

The foundation is intentionally small. It proves that the future vertical slice can connect the database, API and web shell without adding product features now.

## 2. Architecture and data flow

```text
Browser
  │  http://127.0.0.1:5173
  ▼
Vite dev server (web container)
  │  proxy /health and /api → http://api:8000
  ▼
FastAPI (api container)
  │  SQLAlchemy + psycopg
  ▼
PostgreSQL 16 (db container)
```

Health flow:

1. The browser loads the React shell.
2. `App` requests `/health` through the Vite proxy.
3. FastAPI opens a SQLAlchemy session and executes `SELECT 1`.
4. The API returns `200` when the database is reachable or `503` when it is not.
5. The shell shows available or degraded status without crashing.

CI flow:

1. GitHub Actions starts a PostgreSQL service.
2. The backend job installs with `uv sync --frozen`, runs Ruff and pytest.
3. The frontend job runs `npm ci`, lint, typecheck, tests and build.
4. No deployment occurs.

## 3. Components and responsibilities

### Backend

| Path | Responsibility |
|---|---|
| `backend/src/hmde/main.py` | Create the FastAPI app and register the health router. |
| `backend/src/hmde/core/config.py` | Read and validate environment configuration. |
| `backend/src/hmde/core/logging.py` | Configure stdout logging without secrets. |
| `backend/src/hmde/db/base.py` | Declare the SQLAlchemy declarative base. |
| `backend/src/hmde/db/session.py` | Create engine, session factory and `get_db`; expose connectivity check. |
| `backend/src/hmde/api/schemas/health.py` | Pydantic response schema for health. |
| `backend/src/hmde/api/routes/health.py` | `GET /health`, database check and 200/503 responses. |
| `backend/tests/conftest.py` | Set test environment and provide FastAPI test client. |
| `backend/tests/unit/test_config.py` | Configuration success and missing-variable cases. |
| `backend/tests/unit/test_health.py` | Health success and failure with dependency substitution. |
| `backend/tests/integration/test_health_database.py` | Health check against `TEST_DATABASE_URL`; skipped when absent. |
| `backend/alembic/env.py` | Read `DATABASE_URL` and connect Alembic to `Base.metadata`. |
| `backend/alembic/versions/0001_baseline.py` | Empty reversible baseline revision. |
| `backend/alembic.ini` | Alembic configuration without a hard-coded URL. |
| `backend/pyproject.toml` | Dependencies, Ruff and pytest configuration. |
| `backend/uv.lock` | Locked Python dependency graph. |

### Frontend

| Path | Responsibility |
|---|---|
| `frontend/src/main.tsx` | Mount the React application. |
| `frontend/src/App.tsx` | Initial shell and health request lifecycle. |
| `frontend/src/components/ApiStatus.tsx` | Accessible loading/available/degraded presentation. |
| `frontend/src/api/client.ts` | Small fetch wrapper with uniform error handling. |
| `frontend/src/api/health.ts` | `getHealth()` API function. |
| `frontend/src/types/health.ts` | Health response type. |
| `frontend/src/index.css` | Minimal accessible styling. |
| `frontend/src/test/setup.ts` | Testing Library and jest-dom setup. |
| `frontend/src/App.test.tsx` | Render, loading, success and failure tests. |
| `frontend/vite.config.ts` | React plugin, `/health` and `/api` proxy, Vitest config. |
| `frontend/eslint.config.js` | ESLint configuration. |
| `frontend/tsconfig*.json` | Strict TypeScript configuration. |
| `frontend/package.json` | Scripts and dependencies. |
| `frontend/package-lock.json` | Locked Node dependency graph. |
| `frontend/index.html` | Vite HTML entry point. |

### Infrastructure and documentation

| Path | Responsibility |
|---|---|
| `infra/Dockerfile.api` | Development API image with uv and Uvicorn. |
| `compose.yaml` | `db`, `api` and `web` development services. |
| `.dockerignore` | Exclude secrets, caches, dependencies and unrelated directories from the build context. |
| `.env.example` | Development environment values. |
| `.github/workflows/ci.yml` | Backend and frontend CI jobs. |
| `README.md` | Startup, URLs, tests, migrations and troubleshooting. |
| `AGENTS.md` | Verified commands, current state and workflow. |
| `.gitignore` | Ignore secrets, caches, dependencies and raw data. |

## 4. Technical decisions and alternatives

### 4.1 Stack and versions

- Python 3.13 with uv.
- FastAPI, Pydantic v2 and Uvicorn.
- SQLAlchemy 2.0 in synchronous mode with `psycopg` 3.
- Alembic for migrations.
- PostgreSQL 16 Alpine.
- React, TypeScript and Vite, with Node.js 20.
- Vitest, jsdom and React Testing Library.
- Ruff, ESLint and TypeScript strict.
- GitHub Actions.

Exact dependency versions are resolved by `uv.lock` and `package-lock.json`.

### 4.2 Configuration

`app/core/config.py` exposes:

- `Settings`: immutable dataclass with `database_url`, `app_env`, `log_level` and `test_database_url`.
- `load_settings(env)`: pure function for tests.
- `get_settings()`: cached application accessor.

If `DATABASE_URL` is missing or empty, raise `RuntimeError` naming the variable but never printing its value.

No `pydantic-settings` dependency is added; four variables do not justify it.

### 4.3 Persistence

`app/db/session.py` creates:

- An engine from `DATABASE_URL` with `pool_pre_ping=True` and `connect_args={"connect_timeout": 3}`.
- `SessionLocal` with `autocommit=False` and `autoflush=False`.
- `get_db` yielding one session per request and closing it in `finally`.
- A bounded connectivity helper used by the health route.

`Base` is declared in `app/db/base.py`. No `Base.metadata.create_all()` exists anywhere.

### 4.4 Health endpoint

`GET /health`:

- Success: `200 {"status":"ok","database":"ok"}`.
- Database failure: `503 {"status":"degraded","database":"unavailable"}`.
- No parameters, authentication or sensitive details.
- Declared in OpenAPI with both responses.
- Operational path outside `/api/v1`.

The route catches SQLAlchemy connection errors, logs a warning without connection details and returns the degraded response. The API process remains running when PostgreSQL is down.

### 4.5 Frontend and proxy

- Vite serves the shell on port `5173`.
- `/health` and `/api` proxy to `VITE_API_PROXY_TARGET`, default `http://localhost:8000`, Compose value `http://api:8000`.
- Components use relative paths only.
- No CORS is enabled.
- The shell uses `fetch`, local state and minimal CSS.
- Tailwind, React Router and TanStack Query are deferred.

### 4.6 Docker development

`infra/Dockerfile.api`:

- Uses `python:3.13-slim`.
- Copies `uv` from the official image.
- Uses `UV_PROJECT_ENVIRONMENT=/opt/venv`.
- Installs with `uv sync --frozen`.
- Runs Uvicorn with reload for development.

`compose.yaml`:

- `db`: PostgreSQL 16 Alpine, persistent volume, `pg_isready` healthcheck, host port `127.0.0.1:5433`.
- `api`: build from the repository root, mount `backend/`, internal `DATABASE_URL` pointing to `db:5432`, port `127.0.0.1:8000`, HTTP healthcheck.
- `web`: Node 20 Alpine, mount `frontend/`, named `node_modules` volume, Vite host `0.0.0.0`, port `127.0.0.1:5173`, depends on the API service being started (not necessarily healthy) so the degraded UI can be tested.
- `web` runs `npm ci` and `npm run dev -- --host 0.0.0.0`.

### 4.7 Testing

- Backend unit tests do not need PostgreSQL.
- Health success/failure is tested with `get_db` substitution.
- Integration test uses `TEST_DATABASE_URL`, skips when absent and rejects the same URL as `DATABASE_URL`.
- Local integration tests require an isolated `hmde_test` database; the README documents its creation.
- Frontend tests mock `fetch`; no running API is required.
- CI uses a PostgreSQL service for integration tests.

### 4.8 CI

`.github/workflows/ci.yml` has two jobs:

- `backend`: PostgreSQL service, `uv sync --frozen`, `ruff check`, `ruff format --check`, `pytest`. `DATABASE_URL` is a syntactically valid local URL used only for configuration/unit tests; `TEST_DATABASE_URL` points to the service's isolated test database.
- `frontend`: Node 20, `npm ci`, `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build`.

No deployment job.

### 4.9 Alternatives considered

| Alternative | Reason for rejection |
|---|---|
| `pydantic-settings` | Four variables do not justify another dependency in E1. |
| Async SQLAlchemy | Unnecessary complexity for a read-only MVP; ADR-0003 selects sync. |
| CORS | Vite proxy provides same-origin requests in development. |
| Rootless production containers in E1 | Production hardening belongs to E12. |
| Tailwind in E1 | The shell needs only minimal CSS; Tailwind belongs to the product UI. |
| OpenAPI-to-TypeScript generation in E1 | There is only `/health`; generation starts with the domain API in E2. |
| SQLite for tests | It does not reproduce PostgreSQL connection or type behavior. |

## 5. Data model and migrations

No domain tables are created in E1.

| Object | Change |
|---|---|
| `alembic_version` | Created by Alembic when the baseline is applied. |
| Domain tables | None. Created in later specs. |

`0001_baseline.py` has no-op `upgrade()` and `downgrade()`. The migration must be reversible and safe to apply twice.

## 6. API contract

### `GET /health`

No authentication. No parameters.

Response `200`:

```json
{
  "status": "ok",
  "database": "ok"
}
```

Response `503`:

```json
{
  "status": "degraded",
  "database": "unavailable"
}
```

Rules:

- No exception details, credentials or connection URLs in the response.
- Database check timeout is at most 3 seconds.
- The endpoint is documented in OpenAPI.
- The endpoint is operational, not part of `/api/v1`.

## 7. Frontend impact

- Initial page with project name, construction message and API status.
- `ApiStatus` uses a status role and `aria-live="polite"`.
- Loading, available and degraded states.
- Request is cancelled or guarded against updates after unmount.
- Minimal responsive CSS, readable contrast and visible focus.
- No route navigation, global state library or charting library.

## 8. Error handling and consistency

- **`DATABASE_URL` missing:** fail at startup with a clear message.
- **PostgreSQL down:** API remains running; `/health` returns `503`; shell shows degraded.
- **Migration failure:** Alembic exits non-zero; baseline has no domain effects.
- **Frontend without API:** shell renders unavailable state; no unhandled rejection or blank page.
- **Port conflict:** ports are configurable through `.env`.
- **Integration test URL missing:** skip with a clear message.
- **Test URL equals application URL:** abort in the fixture.
- **Session cleanup:** `get_db` always closes the session.

## 9. Security and trust boundaries

- Development only; not exposed to the Internet.
- All published ports bind to `127.0.0.1`.
- `.env` is ignored; `.env.example` contains development values only.
- No secrets or connection strings in logs.
- No authentication or CORS in the MVP.
- Development containers may run as root for mount simplicity; production hardening belongs to E12.
- `.dockerignore` excludes secrets, caches and unrelated directories.

## 10. Observability

- Uvicorn and application logs go to stdout.
- Health failure logs a warning without sensitive details.
- `/health` is the Docker Compose health signal.
- No metrics, traces, alerts or external monitoring in E1.

## 11. Testing strategy

| Level | Case | Evidence |
|---|---|---|
| Unit | Valid configuration | `backend/tests/unit/test_config.py` |
| Unit | Missing `DATABASE_URL` | `backend/tests/unit/test_config.py` |
| Unit | Health `200` with substituted session | `backend/tests/unit/test_health.py` |
| Unit | Health `503` with failing session | `backend/tests/unit/test_health.py` |
| Integration | Health `200` against real PostgreSQL | `backend/tests/integration/test_health_database.py` |
| Component | Title and construction message | `frontend/src/App.test.tsx` |
| Component | Loading state | `frontend/src/App.test.tsx` |
| Component | Available state | `frontend/src/App.test.tsx` |
| Component | Degraded state | `frontend/src/App.test.tsx` |
| Manual | Compose health, degraded API and migrations | E1 validation checklist |

Commands:

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run pytest

cd ../frontend
npm run lint
npm run typecheck
npm run test
npm run build
```

## 12. Deployment and reversibility

- `docker compose up --build` is the main development flow.
- `docker compose down` preserves the PostgreSQL volume.
- `docker compose down -v` is not part of the normal flow.
- `alembic downgrade base` reverses the baseline without domain effects.
- Ports are configurable through `.env`.
- `uv.lock` and `package-lock.json` make installs reproducible.

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Backend volume mount hides the virtual environment | `UV_PROJECT_ENVIRONMENT=/opt/venv`. |
| `npm ci` at every start slows the web service | Named `node_modules` volume; initial install documented. |
| Vite proxy points to the wrong host inside Compose | `VITE_API_PROXY_TARGET=http://api:8000` in Compose. |
| Local port conflict | `API_PORT`, `WEB_PORT` and `DB_PORT` variables. |
| `%` in `DATABASE_URL` breaks Alembic interpolation | Escape `%` before `set_main_option`. |
| Health check fails when PostgreSQL is down | Expected; return `503` without crashing. |
| Tests import the app before environment setup | `conftest.py` sets required variables before imports. |
| CI cannot reach PostgreSQL | Service container and explicit `TEST_DATABASE_URL`. |
| Node version incompatible with Vite | Pin Node 20 and verify build in CI. |
| Development image runs as root | Documented as development-only; hardening in E12. |

## 14. Traceability requirements → plan → tasks

| Requirement | Plan section | Tasks |
|---|---|---|
| FR-001 | 3, 4.6 | T-001, T-006, T-008, T-009 |
| FR-002 | 4.4, 6, 8 | T-004 |
| FR-003 | 4.2, 8 | T-002 |
| FR-004 | 4.3, 8 | T-003, T-004 |
| FR-005 | 5, 12 | T-005, T-013 |
| FR-006 | 4.5, 7 | T-007 |
| FR-007 | 4.6, 12 | T-008, T-009 |
| FR-008 | 4.7, 11 | T-004, T-013 |
| FR-009 | 4.7, 11 | T-006, T-007 |
| FR-010 | 4.1, 11 | T-001, T-006 |
| FR-011 | 4.8 | T-010 |
| FR-012 | 4.4, 10 | T-002, T-004, T-011 |
| FR-013 | 3 | T-012, T-013 |
| FR-014 | 1, 5, 8 | T-013 |
| NFR-001 | 4.6, 12 | T-008, T-009, T-012 |
| NFR-002 | 9 | T-002, T-008, T-009, T-013 |
| NFR-003 | 4.7 | T-002, T-004, T-007 |
| NFR-004 | 1, 4.9 | T-001, T-006 |
| NFR-005 | 7 | T-007 |
| NFR-006 | 10 | T-004, T-011, T-013 |
| NFR-007 | 4.6, 12 | T-009, T-012 |
| NFR-008 | 4.4 | T-004 |
| NFR-009 | 3, 7 | T-012 |
| NFR-010 | 4.1 | T-001, T-006 |

## 15. Approval and next step

This plan is a draft. It must be reviewed and approved together with `tasks.md` before implementation starts. The first task is T-001.
