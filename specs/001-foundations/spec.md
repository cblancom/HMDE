# SPEC-001 — Foundations

- **Status:** Implemented
- **Stage:** E1
- **Iteration:** MVP
- **Module:** `platform`
- **Date:** 2026-11-05
- **Depends on:** E0 complete; [`constitution.md`](../../constitution.md), [`AGENTS.md`](../../AGENTS.md), [architecture overview](../../docs/01-architecture/overview.md), [engineering conventions](../../docs/01-architecture/conventions.md)
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0003](../../docs/01-architecture/adr/ADR-0003-synchronous-sqlalchemy.md), [ADR-0006](../../docs/01-architecture/adr/ADR-0006-read-only-api.md)
- **Plan:** [plan.md](plan.md) (approved)
- **Tasks:** [tasks.md](tasks.md) (completed; remote CI pending first push)
- **Owner:** Cristian

## Revision history

| Revision | Date | Change |
|---|---|---|
| 1 | 2026-11-05 | Initial draft |
| 2 | 2026-11-05 | Spec approved; plan and tasks drafted |
| 3 | 2026-11-05 | Plan/tasks approved; T-001–T-005 implemented |
| 4 | 2026-11-05 | T-006–T-007 implemented (frontend shell and API status) |
| 5 | 2026-11-05 | T-008–T-009 implemented; local API/DB ports changed to 8001/5434 to avoid conflicts |
| 6 | 2026-11-05 | T-010–T-011 implemented (CI workflow and logging verification) |
| 7 | 2026-11-05 | T-012–T-013 local validation complete; remote CI pending first push |

## 1. Context and problem

E0 is complete: the project has a constitution, scope, architecture, data model, source evaluation, ADRs, a MusicBrainz feasibility spike and a 42-band seed list. No application code exists yet.

E2 and later stages need a reproducible repository, a stable backend and frontend skeleton, a PostgreSQL connection, Alembic migrations, test harnesses, quality tooling and CI. Without this foundation, every later feature would have to solve configuration, database sessions, migrations, proxy setup and test infrastructure independently.

This spec builds only the technical foundation. It does not create domain tables, ingest data, expose domain endpoints or implement product features.

## 2. Users and actors

- **Developer owner:** clones the repository, runs the environment, applies migrations and maintains the foundation.
- **Implementation agent:** works from this spec, `plan.md`, `tasks.md`, the constitution and `AGENTS.md`.
- **Future end user:** not part of an end-user flow yet; only sees the initial shell and API status.
- **System:** PostgreSQL, FastAPI, Vite and Docker Compose provide the development environment.

There are no user accounts, roles, permissions or authentication in this iteration.

## 3. User stories and flows

### US-001 — Reproducible startup

As a developer, I want to start the full development environment from a clean clone so that I can work without hidden manual setup.

**Expected flow:**

1. A `.env.example` exists with the required development values.
2. `docker compose up --build` starts PostgreSQL, the API and the web shell.
3. PostgreSQL becomes healthy before the API starts.
4. The API responds on `GET /health`.
5. The web shell loads and shows the API status.

### US-002 — Verifiable quality

As a developer, I want documented lint, format, test, typecheck and build commands so that I can verify the repository before closing a task.

**Expected flow:**

1. Backend commands run through `uv`.
2. Frontend commands run through `npm`.
3. The commands in `AGENTS.md` and `README.md` match the repository scripts.
4. CI runs the same checks on push and pull request.

### US-003 — Controlled schema evolution

As a developer, I want Alembic configured from the start so that the schema can evolve without recreating the database.

**Expected flow:**

1. Alembic reads the database URL from the environment.
2. A baseline revision applies to an empty database.
3. The baseline can be downgraded and applied again.
4. No code creates tables outside Alembic.

### US-004 — Visible API status

As a developer, I want the initial web shell to show whether the API is available so that infrastructure problems are distinguishable from UI problems.

**Expected flow:**

1. The web shell requests `/health` through the Vite proxy.
2. If the API and database are available, it shows an available status.
3. If the API or database is unavailable, it shows a degraded status without breaking the page.

### US-005 — Continuous integration

As a developer, I want every push and pull request to run backend and frontend checks so that regressions are caught early.

**Expected flow:**

1. GitHub Actions starts the backend and frontend jobs.
2. Backend lint, format check and tests run.
3. Frontend lint, typecheck, tests and build run.
4. A failing check blocks the change.

## 4. Functional requirements

### FR-001 — Repository structure

The repository must contain:

- `backend/` with the FastAPI application, Alembic, tests and dependency files.
- `frontend/` with the React application, tests and dependency files.
- `infra/` with container assets that are not Compose files.
- `compose.yaml` at the repository root.
- `docs/` with reference documentation.
- `specs/` with SDD specs and templates.
- `data/` with the versioned seed list; raw local data is ignored by Git.
- `spike/` with disposable research code.
- Root `README.md`, `AGENTS.md`, `constitution.md` and `.gitignore`.

The backend uses a `src/` layout:

```text
backend/
  src/hmde/
    api/
      routes/
      schemas/
    core/
    db/
    main.py
  tests/
    unit/
    integration/
  alembic/
  pyproject.toml
```

Only directories needed by this iteration are created. Domain modules such as `models`, `services`, `etl` and `analytics` are created when their first feature needs them.

**Verification:** the repository tree matches this structure and contains no empty placeholder directories.

### FR-002 — Backend application and health endpoint

The backend must start with FastAPI and expose `GET /health`.

When PostgreSQL is available, it must respond `200`:

```json
{
  "status": "ok",
  "database": "ok"
}
```

When PostgreSQL is unavailable, it must respond `503`:

```json
{
  "status": "degraded",
  "database": "unavailable"
}
```

The endpoint must:

- Execute a bounded database check with a timeout of at most 3 seconds.
- Avoid exposing connection strings, credentials or internal exception details.
- Appear in OpenAPI.
- Remain operational when the database is down; the API process must not crash.

`/health` is an operational endpoint outside the future `/api/v1` domain contract. Its keys remain in English.

**Verification:** both responses are checked with the API running, with PostgreSQL available and stopped.

### FR-003 — Environment configuration

The backend must read configuration from environment variables:

| Variable | Required | Default | Use |
|---|---|---|---|
| `DATABASE_URL` | Yes | — | SQLAlchemy connection URL |
| `APP_ENV` | No | `development` | Environment label |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `TEST_DATABASE_URL` | No | — | Isolated integration-test database |

If `DATABASE_URL` is missing or empty, the application must fail to start with a clear message that names the variable and does not expose secrets.

`.env.example` must contain development-only values. `.env` must be ignored by Git.

This iteration does not add `pydantic-settings`; a small standard-library configuration module is sufficient for four variables.

**Verification:** starting without `DATABASE_URL` fails clearly; starting with it succeeds; `.env` is ignored.

### FR-004 — Persistence foundations

The backend must provide:

- A synchronous SQLAlchemy 2.0 engine created from `DATABASE_URL`.
- `pool_pre_ping=True` and a bounded connection timeout.
- A reusable session factory.
- A FastAPI dependency that yields one session per request and closes it.
- A declarative `Base` for future models.
- A database connectivity check used by `/health`.

No code may call `Base.metadata.create_all()` or create tables outside Alembic.

**Verification:** the API uses the injected session; `/health` reflects real PostgreSQL connectivity; no `create_all` exists in application code.

### FR-005 — Alembic baseline

Alembic must be configured to read `DATABASE_URL` from the environment.

A baseline revision must:

- Apply to an empty database without creating domain tables.
- Be reversible with `alembic downgrade base`.
- Be safe to apply twice.
- Create only the Alembic version table in this iteration.

`alembic.ini` must not contain a hard-coded database URL.

**Verification:** upgrade, downgrade and upgrade again succeed on a clean database.

### FR-006 — Frontend shell

The frontend must use React, TypeScript and Vite with TypeScript in strict mode.

The initial page must show:

- The project name, Heavy Metal Data Explorer.
- A message that the application is under construction.
- The API health status.

The frontend must request `/health` through a relative path and the Vite proxy. Components must not contain a hard-coded API host. The page must handle loading, available and unavailable states without a blank screen.

This iteration uses minimal CSS. Tailwind, React Router, TanStack Query and Cytoscape are introduced in later specs.

**Verification:** with the API running the page shows available; with the API stopped it shows unavailable; tests cover all three states.

### FR-007 — Development Docker Compose

`compose.yaml` must define three services:

- `db`: PostgreSQL 16 with a persistent volume and a healthcheck.
- `api`: backend built from `infra/Dockerfile.api`, with source mounting and a healthcheck.
- `web`: Node 20 with the Vite development server and a dependency on the API.

The environment must support editing code without rebuilding images. Published ports bind to `127.0.0.1`:

- Web: `5173`
- API: `8001`
- PostgreSQL: `5434` on the host

`docker compose up --build` must work from a clean clone using `.env.example` values.

Nginx, TLS, production images and container hardening are out of scope.

**Verification:** all three services become healthy; the web shell and `/health` respond; ports are locally bound.

### FR-008 — Backend test harness

The backend must include pytest with:

- Unit tests for configuration and health responses.
- Tests for the available and unavailable health states using dependency substitution.
- At least one integration test against real PostgreSQL when `TEST_DATABASE_URL` is set.
- Unit tests that run without PostgreSQL.
- Integration tests that skip when `TEST_DATABASE_URL` is absent.
- A fixture that refuses to use the same database as `DATABASE_URL`.

**Verification:** `uv run pytest` passes without PostgreSQL; the full suite passes with the test database.

### FR-009 — Frontend test harness

The frontend must include Vitest, jsdom and React Testing Library with tests for:

- Rendering the project name and construction message.
- Loading state.
- Available API state.
- Unavailable API state.

Network calls are mocked; tests do not require a running API.

**Verification:** `npm run test` passes.

### FR-010 — Quality tooling

Backend:

- Ruff for lint and format checks.
- pytest configuration.
- A lockfile (`uv.lock`).

Frontend:

- ESLint.
- TypeScript strict mode.
- Scripts: `dev`, `lint`, `typecheck`, `test`, `build`.
- A lockfile (`package-lock.json`).

**Verification:** all commands documented in `AGENTS.md` exist and pass.

### FR-011 — Continuous integration

GitHub Actions must run on push and pull request with:

- A backend job: dependency install, Ruff check, format check and tests.
- A frontend job: `npm ci`, lint, typecheck, tests and build.
- A PostgreSQL service for backend integration tests, or an explicit documented skip when unavailable.

There is no deployment job in this iteration.

**Verification:** the workflow passes on the initial commit.

### FR-012 — Logging and operational visibility

The backend must write logs to stdout through the standard logging module.

Logs must not contain:

- Passwords.
- Complete connection strings.
- Secret values.
- Internal exception details returned to clients.

The health endpoint is the operational signal used by Docker Compose.

**Verification:** logs are readable, health checks work and no secrets appear in log output.

### FR-013 — Documentation and commands

`README.md` must document:

- Requirements.
- Environment setup.
- Development startup.
- URLs and ports.
- Tests and quality commands.
- Migrations.
- Troubleshooting basics.

`AGENTS.md` must be updated with the exact verified commands and current state. Commands must match the real scripts and configuration.

**Verification:** a person can follow the README from a clean clone without consulting another document.

### FR-014 — Scope guard

This iteration must not include:

- Domain tables, migrations or models.
- MusicBrainz ingestion, normalization or analytics.
- Domain API endpoints under `/api/v1`.
- Seed data loading.
- Authentication, users or CORS.
- Graph or chart components.
- Production deployment.

**Verification:** repository inspection shows no domain schema or endpoints beyond `/health`.

## 5. Non-functional requirements

### NFR-001 — Reproducibility

The full development environment must start from a clean clone with Docker, Docker Compose and the documented `.env.example`, without requiring Python or Node on the host for the main flow.

### NFR-002 — Security and secrets

No secret may be committed. `.env` is ignored; `.env.example` contains only development values. The database is published only on `127.0.0.1`.

### NFR-003 — Deterministic tests

Unit tests must not depend on external services, execution order or persistent data. Integration tests must use an isolated test database.

### NFR-004 — Simplicity and maintainability

The foundation must avoid redundant configuration and unnecessary abstractions. No generic repository layer, service layer or async database stack is introduced in this iteration.

### NFR-005 — Basic accessibility

The initial page must use semantic HTML, readable contrast, a visible focus state and an understandable error state that does not rely on color alone.

### NFR-006 — Safe observability

Services log to stdout without credentials, connection strings or sensitive data. The API exposes `/health`. No metrics, traces or external alerting are added.

### NFR-007 — Compatibility

The foundation must work on Linux and macOS with Docker. It must not depend on absolute host paths.

### NFR-008 — Health performance

With PostgreSQL available, `/health` should respond within 500 ms under local development load. With PostgreSQL unavailable, the connection attempt must be bounded to at most 3 seconds.

### NFR-009 — Language

All project content is in English: documentation, code, identifiers, API descriptions and UI copy.

### NFR-010 — Locked dependencies

`backend/uv.lock` and `frontend/package-lock.json` are versioned to pin resolved dependencies.

## 6. Business rules

- **BR-001:** E1 contains no domain data or domain features. The 42-band seed list is not loaded.
- **BR-002:** Alembic is the only way to change the database schema.
- **BR-003:** SQLAlchemy is synchronous in the MVP.
- **BR-004:** `/health` is operational and outside the `/api/v1` domain contract.
- **BR-005:** The frontend and API use the same origin through the Vite proxy; no CORS is enabled.
- **BR-006:** The MVP has no authentication or user roles.
- **BR-007:** No secrets, credentials or connection strings are committed or logged.
- **BR-008:** Commands in `AGENTS.md` and `README.md` must match the real repository.
- **BR-009:** New dependencies must be justified by this spec or a later approved spec.

## 7. Edge cases and errors

- **`DATABASE_URL` missing or empty:** fail fast with a clear message; do not print the value.
- **PostgreSQL down:** API remains running; `/health` returns `503`; the web shell shows degraded status.
- **Port already in use:** the developer can change `API_PORT`, `WEB_PORT` or `DB_PORT` in `.env`.
- **Migration applied twice:** `alembic upgrade head` is safe and idempotent.
- **Empty database:** upgrade and downgrade work without domain data.
- **Frontend without API:** the shell renders and shows unavailable status.
- **Missing dependencies:** error messages point to `uv sync` or `npm ci`.
- **Existing Compose volume:** `docker compose down` preserves data; `down -v` is not part of the normal flow.
- **Integration tests without `TEST_DATABASE_URL`:** they skip with a clear message.
- **Test database equals application database:** the fixture aborts.

## 8. Out of scope

- Domain tables, domain models and seed data.
- MusicBrainz ingestion, normalization, quality or analytics.
- Domain endpoints under `/api/v1`.
- Authentication, authorization, users and roles.
- CORS.
- Tailwind, React Router, TanStack Query, Cytoscape and Plotly.
- OpenAPI-to-TypeScript type generation.
- Production Docker images, Nginx, TLS and backups.
- Deployment, CD, metrics, tracing and alerts.
- Playwright end-to-end tests.
- Search, pagination, subgraphs and graph visualization.

## 9. Acceptance criteria

| ID | Criterion | Evidence |
|---|---|---|
| AC-001 | The repository structure matches FR-001 and contains no empty domain placeholders. | Directory inspection and CI tree check. |
| AC-002 | `docker compose up --build` starts `db`, `api` and `web` from a clean clone. | `docker compose ps` with three healthy services. |
| AC-003 | `GET /health` returns `200` with `database: ok` when PostgreSQL is available. | `curl` output and automated test. |
| AC-004 | `GET /health` returns `503` when PostgreSQL is stopped, and the API remains running. | Manual check and automated test with dependency substitution. |
| AC-005 | Alembic applies the baseline, downgrades to base and applies again on a clean database. | Command output; only `alembic_version` exists. |
| AC-006 | The web shell renders the project name, construction message and API status. | Component tests and browser check. |
| AC-007 | `uv run pytest` passes without PostgreSQL; the integration suite passes with `TEST_DATABASE_URL`. | Command output. |
| AC-008 | `npm run lint`, `npm run typecheck`, `npm run test` and `npm run build` pass. | Command output. |
| AC-009 | `uv run ruff check .` and `uv run ruff format --check .` pass. | Command output. |
| AC-010 | No secrets are committed; `.env` is ignored and `.env.example` contains only development values. | `.gitignore` inspection and secret scan. |
| AC-011 | GitHub Actions runs backend and frontend checks and passes. | CI run. |
| AC-012 | `README.md` and `AGENTS.md` contain verified commands that work from a clean clone. | Guided clean-clone validation. |
| AC-013 | No domain tables or domain endpoints exist in this iteration. | Schema inspection and OpenAPI inspection. |

## 10. Assumptions and open questions

### Verified assumptions

- Python 3.13.5, uv 0.11.21, Node.js 20.19.2 and npm 9.2.0 are available.
- Docker 29.8.1 and Docker Compose v5.5.1 are available.
- PostgreSQL 16 is used for development and tests.
- The backend package uses the `src/hmde` layout.
- Development ports are `5173` for web, `8001` for API and `5434` for PostgreSQL on the host.
- Compose uses `infra/Dockerfile.api` for the backend and the Node image for the Vite web service.
- Configuration uses the standard library, without `pydantic-settings`.
- No CORS because the Vite proxy provides same-origin access.
- Tailwind, React Router and TanStack Query are deferred to later specs.
- OpenAPI-to-TypeScript generation is deferred to E2.
- CI uses GitHub Actions and a PostgreSQL service for integration tests.

### Open questions

| Question | Blocking? | Proposed resolution |
|---|---|---|
| Should the health endpoint be `/health` or `/api/health`? | No | `/health` as an operational endpoint outside `/api/v1`. |
| Should E1 include a Dockerfile for the web service? | No | No; Vite runs from the Node image in development. Production images belong to E12. |
| Should integration tests run in CI with a PostgreSQL service? | No | Yes, with `TEST_DATABASE_URL` pointing to an isolated database. |
| Should E1 install Tailwind? | No | No; minimal CSS until E2/E9. |

No blocking questions for the technical plan.

## 11. Validation result

- **Date:** 2026-11-05
- **Verdict:** Implemented; local validation complete, remote CI pending first push.
- **Evidence:** `tasks.md` validation table. AC-011 is partial until GitHub Actions runs after the first push.

## 12. References

- [Constitution](../../constitution.md)
- [AGENTS.md](../../AGENTS.md)
- [Architecture overview](../../docs/01-architecture/overview.md)
- [Engineering conventions](../../docs/01-architecture/conventions.md)
- [Scope](../../docs/00-vision/scope.md)
- [Roadmap](../../docs/00-vision/roadmap.md)
- [ADR-0001 — Modular monolith](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md)
- [ADR-0003 — Synchronous SQLAlchemy](../../docs/01-architecture/adr/ADR-0003-synchronous-sqlalchemy.md)
- [ADR-0006 — Read-only API](../../docs/01-architecture/adr/ADR-0006-read-only-api.md)
