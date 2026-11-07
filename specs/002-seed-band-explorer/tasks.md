# Tasks — SPEC-002 Seed band explorer

- **Status:** In implementation
- **Spec:** [spec.md](spec.md)
- **Plan:** [plan.md](plan.md)

## 1. Execution order

```text
T-001 ──► T-002 ──► T-003 ──► T-004 ──► T-005 ──► T-006 ──► T-007
                                                              │
                                                              ▼
T-008 ──► T-009 ──► T-010 ───────────────────────────────► T-011 ──► T-012
```

T-002 can start once T-001 defines the model and ID strategy. T-004–T-006 are API layers over the loaded fixtures. Frontend work starts after the OpenAPI contract is generated. T-011 integrates and extends CI; T-012 documents and validates.

## 2. Tasks

### T-001 — Create the catalog data model and migration

- **Requirements:** FR-001, NFR-006.
- **Dependencies:** SPEC-001 validated.
- **Status:** Completed (2026-11-06).
- **Description:** create SQLAlchemy models for source records, external IDs, artists, subgenres, release groups, releases, recordings, recording–release links, roles, credits and fixture loads. Create Alembic `0002_catalog_v0` with keys, constraints and indexes.
- **Done when:** the migration applies to an empty database, downgrades cleanly and the required tables/constraints exist.
- **Verification:**
  ```bash
  cd backend
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde uv run alembic upgrade head
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde uv run alembic downgrade base
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde uv run alembic upgrade head
  uv run pytest
  uv run ruff check .
  ```
- **Files:** `backend/src/hmde/models/`, `backend/alembic/versions/0002_catalog_v0.py`, model tests.
- **Evidence:** 2026-11-06: 12 catalog tables created by `0002_catalog_v0`; migration applied, downgraded to base and reapplied successfully; `credit` scope/status/confidence/scope-target checks and indexes verified with `\d credit`; 17 tests passed and 1 integration test skipped; Ruff check/format passed (31 files). `0003_credit_target_restrict` changed `credit.release_id` and `credit.recording_id` FKs to `RESTRICT`; upgrade and downgrade verified. The local `hmde` database is at `0003 (head)`.

### T-002 — Build and commit the E2 fixtures

- **Requirements:** FR-002, NFR-001, NFR-003.
- **Dependencies:** T-001.
- **Status:** Completed (2026-11-06).
- **Description:** create the one-off fixture builder that reads the spike cache, selects 14 bands (2 per subgenre), 2–3 albums per band, and writes versioned entity/credit/source fixtures plus a manifest with counts and checksums.
- **Done when:** fixtures contain 14 bands, 2 per subgenre, 2–3 albums per band, at least one producer/co-producer credit per band, and complete provenance.
- **Verification:**
  ```bash
  python3 scripts/build_e2_fixtures.py
  python3 - <<'PY'
  import json
  from pathlib import Path
  m = json.loads(Path('data/fixtures/e2/manifest.json').read_text())
  assert m['band_count'] == 14
  assert m['subgenre_distribution'] == {k: 2 for k in m['subgenre_distribution']}
  print('fixture manifest OK')
  PY
  ```
- **Files:** `scripts/build_e2_fixtures.py`, `data/fixtures/e2/`.
- **Evidence:** 2026-11-06: builder generated `e2-v0.1.0` with 14 bands, 2 per subgenre, 41 albums, 60 releases, 247 recordings, 859 credits (779 recording-scope, 80 release-scope), 442 source records and 948 KB of JSON. Mayhem has 2 eligible studio albums and is documented in the manifest. The builder is deterministic: rerunning it produced the same manifest checksum. Fixture validation tests pass (manifest counts/checksums, references, producer coverage).

### T-003 — Implement the idempotent fixture loader

- **Requirements:** FR-003, NFR-001, NFR-005.
- **Dependencies:** T-001, T-002.
- **Description:** implement `python -m hmde.seed.loader --fixtures ../data/fixtures/e2` with deterministic UUIDs, transactional upserts, manifest validation, `fixture_load` records and no network calls.
- **Done when:** loading twice leaves entity/credit counts unchanged and the command does not delete unrelated rows.
- **Verification:**
  ```bash
  cd backend
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run python -m hmde.seed.loader --fixtures ../data/fixtures/e2
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run python -m hmde.seed.loader --fixtures ../data/fixtures/e2
  uv run pytest tests/integration/test_fixture_loader.py
  ```
- **Files:** `backend/src/hmde/seed/loader.py`, `backend/tests/integration/test_fixture_loader.py`.
- **Evidence:** Pending.

### T-004 — Implement band list and search API

- **Requirements:** FR-004, NFR-002.
- **Dependencies:** T-003.
- **Description:** add `/api/v1/bands` with `q`, `subgenre`, `limit` and `offset`; return `items`, `total`, `limit` and `offset`; add Pydantic schemas and integration tests.
- **Done when:** list, search, subgenre filter and pagination work; invalid pagination returns 422.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/integration/test_catalog_api.py -k bands
  uv run ruff check .
  ```
- **Files:** `backend/src/hmde/api/routes/bands.py`, `backend/src/hmde/schemas/band.py`, `backend/src/hmde/services/catalog.py`, API tests.
- **Evidence:** Pending.

### T-005 — Implement band detail API

- **Requirements:** FR-005, NFR-002, NFR-003.
- **Dependencies:** T-004.
- **Description:** add `/api/v1/bands/{band_id}` with metadata, chronological albums and aggregated credits. Include role, scope, supporting-recording counts, confidence and status. Return 404 for unknown bands.
- **Done when:** a seeded band returns albums/credits and unknown IDs return 404.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/integration/test_catalog_api.py -k detail
  uv run ruff check .
  ```
- **Files:** `backend/src/hmde/schemas/band.py`, `backend/src/hmde/services/catalog.py`, `backend/src/hmde/api/routes/bands.py`, API tests.
- **Evidence:** Pending.

### T-006 — Implement the band–producer graph API

- **Requirements:** FR-006, NFR-002.
- **Dependencies:** T-005.
- **Description:** add `/api/v1/bands/{band_id}/graph` returning one-hop nodes/edges for documented producer/co-producer credits. Group by producer, record album support, handle no-credit and unknown bands.
- **Done when:** known bands return expected nodes/edges; no-credit bands return a band node with no edges; unknown IDs return 404.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/integration/test_catalog_api.py -k graph
  uv run ruff check .
  ```
- **Files:** `backend/src/hmde/schemas/graph.py`, `backend/src/hmde/services/graph.py`, `backend/src/hmde/api/routes/bands.py`, API tests.
- **Evidence:** Pending.

### T-007 — Export OpenAPI and generate frontend types

- **Requirements:** FR-009.
- **Dependencies:** T-006.
- **Description:** add the backend `hmde.openapi` command, commit `openapi.json`, add `openapi-typescript` and frontend `generate:api`/`pretypecheck`/`predev`/`prebuild` scripts, and ignore `src/api/schema.d.ts`.
- **Done when:** `openapi.json` is generated from the app, the frontend type generation runs and typecheck uses the generated types.
- **Verification:**
  ```bash
  cd backend
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run python -m hmde.openapi --output ../openapi.json
  cd ../frontend
  npm run generate:api
  npm run typecheck
  ```
- **Files:** `backend/src/hmde/openapi.py`, `openapi.json`, `frontend/package.json`, `frontend/src/api/schema.d.ts` (ignored), `.gitignore`.
- **Evidence:** Pending.

### T-008 — Add frontend routing, providers and band list

- **Requirements:** FR-007, NFR-004.
- **Dependencies:** T-007.
- **Description:** add React Router, TanStack Query, routes `/bands` and `/bands/:bandId`, generated API types, band list/search/subgenre filter, URL search params and loading/error/empty states.
- **Done when:** the band list/search/filter works and component tests cover the states.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  npm run build
  ```
- **Files:** `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/pages/BandsPage.tsx`, `frontend/src/components/BandList.tsx`, `frontend/src/components/AsyncState.tsx`, `frontend/src/api/bands.ts`, tests.
- **Evidence:** Pending.

### T-009 — Build the band detail and credits UI

- **Requirements:** FR-007, FR-008, NFR-003, NFR-004.
- **Dependencies:** T-008.
- **Description:** add the detail page with band metadata, chronological albums, credits, role/scope labels, provenance status and loading/error/not-found states.
- **Done when:** a seeded band renders albums and credits and the page handles unknown/error/empty cases.
- **Verification:**
  ```bash
  cd frontend
  npm run test
  npm run lint
  npm run typecheck
  npm run build
  ```
- **Files:** `frontend/src/pages/BandDetailPage.tsx`, `frontend/src/components/CreditList.tsx`, tests.
- **Evidence:** Pending.

### T-010 — Add the Cytoscape mini graph and fallback

- **Requirements:** FR-008, NFR-004.
- **Dependencies:** T-009.
- **Description:** add the Cytoscape band–producer graph with legend, node/edge mapping, lifecycle cleanup, empty state and accessible table fallback.
- **Done when:** a seeded band renders a graph, the fallback is present and component tests cover graph and empty cases.
- **Verification:**
  ```bash
  cd frontend
  npm run test
  npm run lint
  npm run typecheck
  npm run build
  ```
- **Files:** `frontend/src/components/BandGraph.tsx`, `frontend/src/pages/BandDetailPage.tsx`, tests, `frontend/src/index.css`.
- **Evidence:** Pending.

### T-011 — Extend tests and CI

- **Requirements:** FR-010, NFR-002, NFR-007.
- **Dependencies:** T-006, T-010.
- **Description:** complete backend integration tests with migrations/fixtures, frontend component tests, CI migration/OpenAPI drift checks and full backend/frontend runs.
- **Done when:** local suites pass and CI passes with the expanded tests.
- **Verification:**
  ```bash
  (cd backend && uv run ruff check . && uv run ruff format --check . && uv run pytest)
  (cd frontend && npm ci && npm run lint && npm run typecheck && npm run test && npm run build)
  ```
- **Files:** `backend/tests/integration/`, `frontend/src/**/*.test.tsx`, `.github/workflows/ci.yml`.
- **Evidence:** Pending.

### T-012 — Document and validate E2

- **Requirements:** FR-011, FR-012, NFR-001, NFR-003, NFR-005, NFR-007, NFR-008.
- **Dependencies:** T-001 through T-011.
- **Description:** update README/AGENTS with fixture loading, endpoints, routes and tests; run the full E2 validation; record fixture counts, API/UI evidence, CI, scope guard and update spec/result.
- **Done when:** all acceptance criteria have evidence and the spec is marked Validated.
- **Verification:**
  ```bash
  docker compose up --build -d
  cd backend
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run python -m hmde.seed.loader --fixtures ../data/fixtures/e2
  uv run pytest
  uv run ruff check .
  uv run ruff format --check .
  cd ../frontend
  npm run lint
  npm run typecheck
  npm run test
  npm run build
  ```
- **Files:** `README.md`, `AGENTS.md`, `specs/002-seed-band-explorer/spec.md`, `specs/002-seed-band-explorer/tasks.md`, `specs/README.md`, `docs/00-vision/roadmap.md`.
- **Evidence:** Pending.

## 3. Coverage matrix

### Functional requirements

| Requirement | Tasks |
|---|---|
| FR-001 | T-001 |
| FR-002 | T-002 |
| FR-003 | T-003 |
| FR-004 | T-004 |
| FR-005 | T-005 |
| FR-006 | T-006 |
| FR-007 | T-008, T-009 |
| FR-008 | T-009, T-010 |
| FR-009 | T-007 |
| FR-010 | T-011 |
| FR-011 | T-012 |
| FR-012 | T-012 |

### Non-functional requirements

| Requirement | Tasks |
|---|---|
| NFR-001 | T-002, T-003 |
| NFR-002 | T-004, T-005, T-006, T-011 |
| NFR-003 | T-002, T-003, T-012 |
| NFR-004 | T-008, T-009, T-010 |
| NFR-005 | T-003, T-012 |
| NFR-006 | T-001, T-004 |
| NFR-007 | T-011, T-012 |
| NFR-008 | T-012 |

## 4. Validation evidence

| Criterion | Result | Evidence |
|---|---|---|
| AC-001 | Pending | Migration up/down/up and schema inspection |
| AC-002 | Pending | Fixture manifest counts |
| AC-003 | Pending | Loader twice; counts unchanged; no network |
| AC-004 | Pending | Band list/search/filter/pagination tests |
| AC-005 | Pending | Detail and 404 tests |
| AC-006 | Pending | Graph, no-credit and 404 tests |
| AC-007 | Pending | Frontend list/search/detail tests |
| AC-008 | Pending | Cytoscape and fallback tests |
| AC-009 | Pending | OpenAPI generation and frontend typecheck |
| AC-010 | Pending | Local and CI suites |
| AC-011 | Pending | Test isolation and code inspection |
| AC-012 | Pending | Clean-copy command validation |
| AC-013 | Pending | Dependency and OpenAPI inspection |

## 5. Notes

- E2 uses fixtures, not live ingestion.
- The fixture builder is a one-off development tool and is not imported by the API.
- Do not commit generated TypeScript types; commit the reviewed `openapi.json` snapshot.
- Do not introduce Tailwind, Plotly or analytics in E2.
- Record follow-up debt or open issues here.
