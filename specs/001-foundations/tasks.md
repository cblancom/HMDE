# Tasks — SPEC-001 Foundations

- **Status:** Completed (local validation; remote CI pending first push)
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
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
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
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
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
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run alembic history
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run alembic heads
  ```
- **Files:** `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`, `backend/alembic/versions/0001_baseline.py`.
- **Evidence:** 2026-11-05: `alembic history`/`heads` reported `<base> -> 0001 (head), baseline`; against a temporary PostgreSQL 16 container, `upgrade head -> downgrade base -> upgrade head` succeeded and `current` reported `0001 (head)`. Ruff check and format check passed (22 files). The temporary container was removed after validation.

### T-006 — Create the frontend shell, quality tooling and test harness

- **Requirements:** FR-001, FR-009, FR-010, NFR-005, NFR-010.
- **Dependencies:** T-001 (parallel with backend after T-001).
- **Status:** Completed (2026-11-05).
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
- **Evidence:** 2026-11-05: Vite 8.3.6, React 19.3.1, TypeScript 6.0.3, Vitest 4.1.12, ESLint 10.14.0. Initial install required `npm install --legacy-peer-deps` because npm 9.2.0 hit a peer-graph `edgesOut` bug; `npm ci` works from the generated lockfile. `lint`, `typecheck`, `test` (1 test) and `build` pass; production dependency audit reports 0 vulnerabilities.

### T-007 — Implement the API client, status component and Vite proxy

- **Requirements:** FR-006, FR-009, NFR-005.
- **Dependencies:** T-006.
- **Status:** Completed (2026-11-05).
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
- **Evidence:** 2026-11-05: Vite proxies `/health` and `/api` to `VITE_API_PROXY_TARGET` with localhost fallback. 5 App tests pass (render, loading, available, degraded and unavailable). `npm ci`, lint, typecheck, 5 tests and build pass; no `localhost:8000` appears under `src`. Production dependency audit reports 0 vulnerabilities; development audit reports 10 moderate findings.

### T-008 — Create the development API image and build context

- **Requirements:** FR-007, NFR-001, NFR-002.
- **Dependencies:** T-004.
- **Status:** Completed (2026-11-05).
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
- **Evidence:** 2026-11-05: image `hmde-api:dev` built successfully; `uv sync --frozen` installed 36 packages in `/opt/venv`; container import printed `HMDE API` with a fake `DATABASE_URL`. Build context was 215.55 kB.

### T-009 — Create the development Docker Compose environment

- **Requirements:** FR-007, NFR-001, NFR-002, NFR-007.
- **Dependencies:** T-005, T-007, T-008.
- **Status:** Completed (2026-11-05).
- **Description:** create `compose.yaml` with `db`, `api` and `web`; add healthchecks, persistent PostgreSQL volume, development mounts, `node_modules` volume, dependencies, localhost port bindings, internal API `DATABASE_URL` and Vite proxy target. Create `.env.example` and update `.gitignore` if needed.
- **Done when:** `docker compose up --build -d` starts all three services healthy; `/health` responds; the web shell loads.
- **Verification:**
  ```bash
  docker compose config -q
  docker compose up --build -d
  docker compose ps
  curl -i http://127.0.0.1:8001/health
  curl -I http://127.0.0.1:5173/
  ```
- **Files:** `compose.yaml`, `.env.example`, `.gitignore`.
- **Evidence:** 2026-11-05: `docker compose config -q` passed; `db`, `api` and `web` reached healthy state; `/health` returned `{"status":"ok","database":"ok"}`; web returned 200; Vite proxy `/health` returned 200. The initial attempt exposed local conflicts on 8000/5433 from another project, so HMDE host defaults were changed to API 8001 and PostgreSQL 5434; the final run used the defaults successfully. Containers were stopped after validation; volumes were preserved.

### T-010 — Create the GitHub Actions CI workflow

- **Requirements:** FR-011, NFR-001, NFR-003.
- **Dependencies:** T-004, T-007.
- **Status:** Completed (2026-11-05; remote run pending first push).
- **Description:** create `.github/workflows/ci.yml` with backend and frontend jobs; use PostgreSQL 16 as a service; set `DATABASE_URL` to a syntactically valid local URL for configuration/unit tests and `TEST_DATABASE_URL` to the isolated test database; install with `uv sync --frozen` and `npm ci`; run Ruff, pytest, lint, typecheck, tests and build; no deployment.
- **Done when:** the workflow is valid and passes on the branch.
- **Verification:**
  ```bash
  # Local equivalent
  (cd backend && uv run ruff check . && uv run ruff format --check . && uv run pytest)
  (cd frontend && npm run lint && npm run typecheck && npm run test && npm run build)
  ```
- **Files:** `.github/workflows/ci.yml`.
- **Evidence:** 2026-11-05: workflow YAML parsed successfully with `backend` and `frontend` jobs; local equivalent checks passed (backend 13 tests passed, 1 integration skipped; frontend lint, typecheck, 5 tests and build passed). Remote GitHub Actions execution is pending the first push because no commit/push was requested.

### T-011 — Wire logging into application startup and health failures

- **Requirements:** FR-012, NFR-006.
- **Dependencies:** T-002, T-004.
- **Status:** Completed (2026-11-05).
- **Description:** configure logging at application startup from `LOG_LEVEL`; log health database failures as warnings without connection strings, credentials or stack details in the response.
- **Done when:** logs go to stdout and no sensitive values appear when health fails.
- **Verification:**
  ```bash
  cd backend
  uv run pytest
  uv run ruff check .
  ```
- **Files:** `backend/src/hmde/core/logging.py`, `backend/src/hmde/main.py`, `backend/src/hmde/api/routes/health.py`.
- **Evidence:** 2026-11-05: `resolve_log_level` normalizes known/unknown levels; `create_app` configures logging from settings and logs startup environment; health failures log a fixed warning. Tests cover log-level resolution, startup wiring and no secret leakage in the health warning. 13 tests passed, 1 integration skipped; Ruff check and format check passed (23 files).

### T-012 — Document startup, commands and current state

- **Requirements:** FR-013, NFR-001, NFR-007, NFR-009.
- **Dependencies:** T-009, T-010, T-011.
- **Status:** Completed (2026-11-05).
- **Description:** update root `README.md` with requirements, environment setup, Compose startup, URLs, local development, test database creation, tests, migrations and troubleshooting; update `AGENTS.md` with exact verified commands, current state and spec status.
- **Done when:** a clean-clone reader can follow the README; the `hmde_test` database creation is documented; every command in `README.md` and `AGENTS.md` exists and works.
- **Verification:**
  ```bash
  docker compose config -q
  cd backend && uv run pytest && uv run ruff check . && uv run ruff format --check .
  cd ../frontend && npm run lint && npm run typecheck && npm run test && npm run build
  ```
- **Files:** `README.md`, `AGENTS.md`, possibly `docs/README.md` if links change.
- **Evidence:** 2026-11-05: README now covers requirements, Docker quick start, service URLs, local backend/frontend, test database creation, tests, migrations and troubleshooting. AGENTS lists verified commands and current state. `uv run --env-file ../.env.example` loaded the expected database URL; backend 13 tests passed (1 integration skipped), Ruff/format passed; frontend lint, typecheck, 5 tests and build passed. `docker compose config -q` passed.

### T-013 — Validate E1 and record evidence

- **Requirements:** All FR, NFR, BR and AC for SPEC-001.
- **Dependencies:** T-001 through T-012.
- **Status:** Completed (2026-11-05; local validation complete, remote CI pending first push).
- **Description:** run the full validation: clean Compose startup, health `200`, health `503` with PostgreSQL stopped, Alembic upgrade/downgrade/upgrade, unit and integration tests, frontend checks, CI, secret scan and scope guard. Update the validation tables and current state.
- **Done when:** every acceptance criterion has evidence; no domain table or domain endpoint exists; the spec is marked Validated.
- **Verification:**
  ```bash
  docker compose up --build -d
  docker compose ps
  curl -i http://127.0.0.1:8001/health
  docker compose stop db
  curl -i http://127.0.0.1:8001/health
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
- **Evidence:** 2026-11-05: Compose started db/api/web healthy; `/health` returned 200; web and Vite proxy returned 200; stopping PostgreSQL produced 503 with `{"status":"degraded","database":"unavailable"}` while the API stayed up; restarting PostgreSQL restored 200. `hmde_test` was created; full backend suite passed 14/14; Alembic upgrade → downgrade base → upgrade succeeded and `current` returned `0001 (head)`; `\dt` showed only `alembic_version`. Frontend `npm ci`, lint, typecheck, 5 tests and build passed; backend Ruff/format passed. A clean-copy validation of backend/frontend commands and `docker compose config -q` passed. OpenAPI exposes only `/health`. `actionlint` exited 0, the local CI equivalent passed, and the remote GitHub Actions run passed after the first push (confirmed 2026-11-06).

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
| AC-001 | Met | Repository tree inspected; no empty domain placeholders. |
| AC-002 | Met | `docker compose up --build -d`; db, api and web healthy. |
| AC-003 | Met | `curl /health` returned 200 and automated test passed. |
| AC-004 | Met | With PostgreSQL stopped: 503 degraded, API stayed up; automated test passed. |
| AC-005 | Met | Alembic upgrade → downgrade base → upgrade; `current` = 0001; only `alembic_version` exists. |
| AC-006 | Met | Web returned 200; 5 component tests cover render/loading/available/degraded/unavailable. |
| AC-007 | Met | 14 tests passed with `TEST_DATABASE_URL`; 13 passed and 1 skipped without it. |
| AC-008 | Met | `npm ci`, lint, typecheck, 5 tests and build passed. |
| AC-009 | Met | Ruff check and format check passed (23 files). |
| AC-010 | Met | `.env` is absent/ignored; `.env.example` contains development values only; no real secrets found. |
| AC-011 | Met | `actionlint` passed, local CI equivalent passed, and the remote GitHub Actions run passed (confirmed 2026-11-06). |
| AC-012 | Met | README/AGENTS commands verified in a clean copy; `docker compose config -q` passed. |
| AC-013 | Met | OpenAPI exposes only `/health`; database contains only `alembic_version`. |

## 5. Notes

- Do not implement domain tables, ingestion or domain endpoints in this iteration.
- If a task reveals a decision not covered by the spec or plan, update the spec or plan first.
- Do not mark a task complete unless its verification was executed.
- Record follow-up debt or open issues here.
