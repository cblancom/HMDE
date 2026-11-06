# Tasks — SPEC-001 Foundations

- **Status:** In implementation
- **Spec:** [spec.md](spec.md)
- **Plan:** [plan.md](plan.md)

## 1. Execution order

```text
T-001 ──► T-002 ──► T-003 ──► T-004 ──► T-008 ──┐
              │         └───► T-005 ────────────┼──► T-009 ──┐
              └───► T-011                       │            │
T-001 ──► T-006 ──► T-007 ──────────────────────┘            ├──► T-012 ──► T-013
                    └───► T-010 ─────────────────────────────┘
```

Backend and frontend can advance in parallel after T-001. T-009 integrates infrastructure; T-012 documents verified commands; T-013 validates the full iteration.

## 2. Tasks

### T-001 — Create the backend skeleton and pin dependencies

- **Requirements:** FR-001, FR-010, NFR-004, NFR-010.
- **Dependencies:** none.
- **Status:** Completed (2026-11-05).
- **Description:** create `backend/src/hmde/{api/routes,api/schemas,core,db}`, `backend/tests/{unit,integration}`, `backend/pyproject.toml`; declare runtime and development dependencies; configure Ruff and pytest; generate `uv.lock`.
- **Done when:** `uv sync` installs the environment; Ruff check and format check pass; a minimal package import works.
- **Verification:**
  ```bash
  cd backend
  uv sync
  uv run ruff check .
  uv run ruff format --check .
  uv run python -c "import hmde"
  ```
- **Files:** `backend/pyproject.toml`, `backend/uv.lock`, `backend/src/hmde/__init__.py`, package directories, `backend/tests/`.
- **Evidence:** 2026-11-05: `uv sync` installed 36 packages and built `hmde-backend`; Ruff check and format check passed (9 files); `import hmde` resolved from `backend/src/hmde`.

### T-002 — Implement configuration and logging primitives

- **Requirements:** FR-003, FR-012, NFR-002, NFR-003, NFR-009.
- **Dependencies:** T-001.
- **Status:** Completed (2026-11-05).
- **Description:** create `core/config.py` with `Settings`, `load_settings(env)` and `get_settings()`; require `DATABASE_URL`; add `APP_ENV`, `LOG_LEVEL` and optional `TEST_DATABASE_URL`; create `core/logging.py` for stdout logging. Add unit tests for valid, missing and blank values.
- **Done when:** configuration tests pass; missing `DATABASE_URL` raises a clear error without printing its value; logging is configured without secrets.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_config.py
  uv run ruff check .
  uv run ruff format --check .
  ```
- **Files:** `backend/src/hmde/core/config.py`, `backend/src/hmde/core/logging.py`, `backend/tests/unit/test_config.py`.
- **Evidence:** 2026-11-05: 6 configuration tests passed; Ruff check passed; Ruff format check passed (12 files).

### T-003 — Create SQLAlchemy persistence foundations

- **Requirements:** FR-004, NFR-003.
- **Dependencies:** T-001, T-002.
- **Status:** Completed (2026-11-05).
- **Description:** create `db/base.py` with `Base`; create `db/session.py` with a synchronous engine, `pool_pre_ping`, `connect_timeout=3`, `SessionLocal`, `get_db` and a bounded connectivity helper. Do not call `create_all`.
- **Done when:** modules import with a valid `DATABASE_URL`; no `create_all` exists; Ruff passes.
- **Verification:**
  ```bash
  cd backend
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5433/hmde \
    uv run python -c "from hmde.db.session import engine, SessionLocal, get_db; print(engine.url.get_backend_name())"
  grep -R "create_all" src tests || true
  uv run ruff check .
  ```
- **Files:** `backend/src/hmde/db/base.py`, `backend/src/hmde/db/session.py`, `backend/tests/unit/test_config.py` if imports require environment setup.
- **Evidence:** 2026-11-05: engine imported with backend `postgresql`; no `create_all` found; Ruff check passed; Ruff format check passed (14 files).

### T-004 — Implement `GET /health` with tests

- **Requirements:** FR-002, FR-004, FR-008, NFR-006, NFR-008.
- **Dependencies:** T-003.
- **Status:** Completed (2026-11-05).
- **Description:** create health response schema, health route and app factory/entry point; execute `SELECT 1` through `get_db`; return `200` or `503`; register the router; add unit tests for both states with dependency substitution; add an integration test against `TEST_DATABASE_URL` with a session dependency override; refuse to run integration tests when the test URL equals the application URL; verify the route appears in OpenAPI.
- **Done when:** `uv run pytest` passes without PostgreSQL; the integration test passes with an isolated test database; `/health` returns the agreed shapes; no exception details or credentials leak.
- **Verification:**
  ```bash
  cd backend
  uv run pytest
  uv run ruff check .
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5433/hmde \
    uv run python -c "from hmde.main import app; print('/health' in app.openapi()['paths'])"
  ```
- **Files:** `backend/src/hmde/api/schemas/health.py`, `backend/src/hmde/api/routes/health.py`, `backend/src/hmde/main.py`, `backend/tests/conftest.py`, `backend/tests/unit/test_health.py`, `backend/tests/integration/test_health_database.py`.
- **Evidence:** 2026-11-05: 10 unit tests passed and 1 integration test passed against a temporary PostgreSQL 16 container at `127.0.0.1:55433`; Ruff check passed; format check passed (20 files); `/health` is present in OpenAPI. A Starlette deprecation warning about `httpx`/`httpx2` remains and does not affect behavior.

### T-005 — Initialize Alembic and create the baseline

- **Requirements:** FR-005, BR-002.
- **Dependencies:** T-003.
- **Status:** Completed (2026-11-05).
- **Description:** create `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako` and `alembic/versions/0001_baseline.py`; read `DATABASE_URL` from settings; escape `%`; use `Base.metadata` as target metadata; keep the baseline empty and reversible.
- **Done when:** Alembic recognizes revision `0001`; no hard-coded URL exists; upgrade and downgrade are ready for integration validation.
- **Verification:**
  ```bash
  cd backend
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5433/hmde \
    uv run alembic history
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5433/hmde \
    uv run alembic heads
  ```
- **Files:** `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`, `backend/alembic/versions/0001_baseline.py`.
- **Evidence:** 2026-11-05: `alembic history`/`heads` reported `<base> -> 0001 (head), baseline`; against a temporary PostgreSQL 16 container, `upgrade head -> downgrade base -> upgrade head` succeeded and `current` reported `0001 (head)`. Ruff check and format check passed (22 files). The temporary container was removed after validation.

### T-006 — Create the frontend shell, quality tooling and test harness

- **Requirements:** FR-001, FR-009, FR-010, NFR-005, NFR-010.
- **Dependencies:** T-001 (parallel with backend after T-001).
- **Description:** create `frontend/` with Vite, React and strict TypeScript; configure ESLint, Vitest, jsdom, Testing Library and jest-dom; define scripts `dev`, `lint`, `typecheck`, `test`, `build`; add minimal shell files and a smoke test.
- **Done when:** all frontend quality commands pass and `package-lock.json` exists.
- **Verification:**
  ```bash
  cd frontend
  npm ci
  npm run lint
  npm run typecheck
  npm run test
  npm run build
  ```
- **Files:** `frontend/package.json`, `frontend/package-lock.json`, `frontend/index.html`, `frontend/vite.config.ts`, `frontend/eslint.config.js`, `frontend/tsconfig*.json`, `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/index.css`, `frontend/src/test/setup.ts`.
- **Evidence:** Pending.

### T-007 — Implement the API client, status component and Vite proxy

- **Requirements:** FR-006, FR-009, NFR-005.
- **Dependencies:** T-006.
- **Description:** configure `/health` and `/api` proxy targets in Vite; create health types, fetch client, `getHealth`; implement `ApiStatus` and the `App` request lifecycle with loading, available and degraded states; add component tests with mocked `fetch`; cancel or guard updates after unmount.
- **Done when:** tests cover render, loading, success and failure; no absolute API host exists in components; typecheck and build pass.
- **Verification:**
  ```bash
  cd frontend
  npm run test
  npm run lint
  npm run typecheck
  npm run build
  grep -R "localhost:8000" src || true
  ```
- **Files:** `frontend/vite.config.ts`, `frontend/src/api/client.ts`, `frontend/src/api/health.ts`, `frontend/src/types/health.ts`, `frontend/src/components/ApiStatus.tsx`, `frontend/src/App.tsx`, `frontend/src/App.test.tsx`.
- **Evidence:** Pending.

### T-008 — Create the development API image and build context

- **Requirements:** FR-007, NFR-001, NFR-002.
- **Dependencies:** T-004.
- **Description:** create `infra/Dockerfile.api` with Python 3.13, uv, `uv sync --frozen`, `UV_PROJECT_ENVIRONMENT=/opt/venv` and Uvicorn; create `.dockerignore` excluding secrets, caches, dependencies, frontend, spike, docs and local reference material.
- **Done when:** the image builds and imports `hmde.main` with a fake database URL.
- **Verification:**
  ```bash
  docker build -f infra/Dockerfile.api -t hmde-api:dev .
  docker run --rm \
    -e DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@db:5432/hmde \
    hmde-api:dev python -c "from hmde.main import app; print(app.title)"
  ```
- **Files:** `infra/Dockerfile.api`, `.dockerignore`.
- **Evidence:** Pending.

### T-009 — Create the development Docker Compose environment

- **Requirements:** FR-007, NFR-001, NFR-002, NFR-007.
- **Dependencies:** T-005, T-007, T-008.
- **Description:** create `compose.yaml` with `db`, `api` and `web`; add healthchecks, persistent PostgreSQL volume, development mounts, `node_modules` volume, dependencies, localhost port bindings, internal API `DATABASE_URL` and Vite proxy target. Create `.env.example` and update `.gitignore` if needed.
- **Done when:** `docker compose up --build -d` starts all three services healthy; `/health` responds; the web shell loads.
- **Verification:**
  ```bash
  docker compose config -q
  docker compose up --build -d
  docker compose ps
  curl -i http://127.0.0.1:8000/health
  curl -I http://127.0.0.1:5173/
  ```
- **Files:** `compose.yaml`, `.env.example`, `.gitignore`.
- **Evidence:** Pending.

### T-010 — Create the GitHub Actions CI workflow

- **Requirements:** FR-011, NFR-001, NFR-003.
- **Dependencies:** T-004, T-007.
- **Description:** create `.github/workflows/ci.yml` with backend and frontend jobs; use PostgreSQL 16 as a service; set `DATABASE_URL` to a syntactically valid local URL for configuration/unit tests and `TEST_DATABASE_URL` to the isolated test database; install with `uv sync --frozen` and `npm ci`; run Ruff, pytest, lint, typecheck, tests and build; no deployment.
- **Done when:** the workflow is valid and passes on the branch.
- **Verification:**
  ```bash
  # Local equivalent
  (cd backend && uv run ruff check . && uv run ruff format --check . && uv run pytest)
  (cd frontend && npm run lint && npm run typecheck && npm run test && npm run build)
  ```
- **Files:** `.github/workflows/ci.yml`.
- **Evidence:** Pending.

### T-011 — Wire logging into application startup and health failures

- **Requirements:** FR-012, NFR-006.
- **Dependencies:** T-002, T-004.
- **Description:** configure logging at application startup from `LOG_LEVEL`; log health database failures as warnings without connection strings, credentials or stack details in the response.
- **Done when:** logs go to stdout and no sensitive values appear when health fails.
- **Verification:**
  ```bash
  cd backend
  uv run pytest
  uv run ruff check .
  ```
- **Files:** `backend/src/hmde/core/logging.py`, `backend/src/hmde/main.py`, `backend/src/hmde/api/routes/health.py`.
- **Evidence:** Pending.

### T-012 — Document startup, commands and current state

- **Requirements:** FR-013, NFR-001, NFR-007, NFR-009.
- **Dependencies:** T-009, T-010, T-011.
- **Description:** update root `README.md` with requirements, environment setup, Compose startup, URLs, local development, test database creation, tests, migrations and troubleshooting; update `AGENTS.md` with exact verified commands, current state and spec status.
- **Done when:** a clean-clone reader can follow the README; the `hmde_test` database creation is documented; every command in `README.md` and `AGENTS.md` exists and works.
- **Verification:**
  ```bash
  docker compose config -q
  cd backend && uv run pytest && uv run ruff check . && uv run ruff format --check .
  cd ../frontend && npm run lint && npm run typecheck && npm run test && npm run build
  ```
- **Files:** `README.md`, `AGENTS.md`, possibly `docs/README.md` if links change.
- **Evidence:** Pending.

### T-013 — Validate E1 and record evidence

- **Requirements:** All FR, NFR, BR and AC for SPEC-001.
- **Dependencies:** T-001 through T-012.
- **Description:** run the full validation: clean Compose startup, health `200`, health `503` with PostgreSQL stopped, Alembic upgrade/downgrade/upgrade, unit and integration tests, frontend checks, CI, secret scan and scope guard. Update the validation tables and current state.
- **Done when:** every acceptance criterion has evidence; no domain table or domain endpoint exists; the spec is marked Validated.
- **Verification:**
  ```bash
  docker compose up --build -d
  docker compose ps
  curl -i http://127.0.0.1:8000/health
  docker compose stop db
  curl -i http://127.0.0.1:8000/health
  docker compose start db
  cd backend
  uv run alembic upgrade head
  uv run alembic downgrade base
  uv run alembic upgrade head
  uv run pytest
  uv run ruff check .
  uv run ruff format --check .
  cd ../frontend
  npm run lint
  npm run typecheck
  npm run test
  npm run build
  ```
- **Files:** `specs/001-foundations/spec.md`, `specs/001-foundations/tasks.md`, `AGENTS.md`, `README.md`, `specs/README.md`.
- **Evidence:** Pending.

## 3. Coverage matrix

### Functional requirements

| Requirement | Tasks |
|---|---|
| FR-001 | T-001, T-006, T-008, T-009 |
| FR-002 | T-004 |
| FR-003 | T-002 |
| FR-004 | T-003, T-004 |
| FR-005 | T-005, T-013 |
| FR-006 | T-007 |
| FR-007 | T-008, T-009 |
| FR-008 | T-004, T-013 |
| FR-009 | T-006, T-007 |
| FR-010 | T-001, T-006 |
| FR-011 | T-010 |
| FR-012 | T-002, T-004, T-011 |
| FR-013 | T-012, T-013 |
| FR-014 | T-013 |

### Non-functional requirements

| Requirement | Tasks |
|---|---|
| NFR-001 | T-008, T-009, T-012, T-013 |
| NFR-002 | T-002, T-008, T-009, T-013 |
| NFR-003 | T-002, T-004, T-007 |
| NFR-004 | T-001, T-006 |
| NFR-005 | T-007 |
| NFR-006 | T-004, T-011, T-013 |
| NFR-007 | T-009, T-012 |
| NFR-008 | T-004 |
| NFR-009 | T-012 |
| NFR-010 | T-001, T-006 |

## 4. Validation evidence

| Criterion | Result | Evidence |
|---|---|---|
| AC-001 | Pending | Directory inspection |
| AC-002 | Pending | `docker compose ps` |
| AC-003 | Pending | `curl /health` and test |
| AC-004 | Pending | Health with PostgreSQL stopped and test |
| AC-005 | Pending | Alembic upgrade/downgrade/upgrade |
| AC-006 | Pending | Component tests and browser check |
| AC-007 | Pending | `uv run pytest` |
| AC-008 | Pending | Frontend lint, typecheck, tests and build |
| AC-009 | Pending | Ruff check and format check |
| AC-010 | Pending | `.gitignore`, `.env.example`, secret scan |
| AC-011 | Pending | GitHub Actions run |
| AC-012 | Pending | Clean-clone command validation |
| AC-013 | Pending | Schema and OpenAPI inspection |

## 5. Notes

- Do not implement domain tables, ingestion or domain endpoints in this iteration.
- If a task reveals a decision not covered by the spec or plan, update the spec or plan first.
- Do not mark a task complete unless its verification was executed.
- Record follow-up debt or open issues here.
