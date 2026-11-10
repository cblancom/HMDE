# Tasks — SPEC-009 Read-only API v1

- **Status:** Validated
- **Spec:** [spec.md](spec.md)
- **Plan:** [plan.md](plan.md)

## 1. Execution order

```text
T-001 ─► T-002 ─┬─► T-003 ─► T-008 ─┐
                ├─► T-004 ──────────┤
                ├─► T-005 ──────────┼─► T-009 ─► T-010 ─► T-011
                ├─► T-006 ──────────┤
                └─► T-007 ──────────┘
```

T-001 and T-002 establish shared middleware, dependencies, pagination and schemas. T-003–T-007 can run in parallel after T-002 and converge on contract tests. T-008 validates compatibility/retired behavior. T-009 proves OpenAPI, types, CORS and read-only boundaries. T-010 runs fixture/full-corpus API verification. T-011 closes documentation and CI.

## 2. Tasks

### T-001 — Add CORS, settings and shared run resolution

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-001, FR-002, FR-019, NFR-009.
- **Dependencies:** SPEC-008 validated; plan/tasks approved.
- **Description:** Add configurable CORS settings and Starlette middleware. Add `hmde.api.dependencies` with latest/explicit completed E7 run resolution, error mapping (`404`/`409`/`503`) and shared run metadata. Register new routers in `main.py` as they are added. Extend `.env.example` with CORS origins.
- **Done when:** allowed origins receive CORS headers; disallowed origins are rejected; latest/explicit/missing/non-terminal runs resolve correctly; existing `/health` still works.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_api_dependencies.py tests/integration/test_api_health_cors.py
  ```
- **Files:** `backend/src/hmde/core/config.py`, `backend/src/hmde/main.py`, `backend/src/hmde/api/dependencies.py`, `.env.example`, tests.
- **Evidence:** 2026-11-10: configurable CORS origins and middleware added; latest/explicit completed E7 run resolution implemented with 404/409/503 errors. CORS, config and dependency tests passed (5).

### T-002 — Add pagination, filters, schemas and error contract

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-013, FR-014, NFR-007, NFR-010.
- **Dependencies:** T-001.
- **Description:** Add shared pagination/sort whitelist helpers and response metadata. Define Pydantic v2 schemas for artists, albums, credits, producers, taxonomy, analytics, communities and graph responses. Add a consistent service/error mapping layer for invalid filters, unknown entities, unusable runs and truncation.
- **Done when:** list responses include `items/total/limit/offset`; invalid limits/sorts return `422`; unknown entities return `404`; error responses contain no internal details.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_api_pagination.py tests/unit/test_api_schemas.py
  ```
- **Files:** `backend/src/hmde/api/pagination.py`, `backend/src/hmde/schemas/api.py`, tests.
- **Evidence:** 2026-11-10: shared pagination/sort validation and all E8 response schemas added; FastAPI HTTPException provides the v1 error shape. Pagination/schema tests passed (3).

### T-003 — Extend bands and add artist detail

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-001, FR-003.
- **Dependencies:** T-002.
- **Description:** Extend `/api/v1/bands` with decade/year/taxonomy/include-retired filters while preserving existing E2 behavior. Add `/api/v1/artists/{artist_id}` canonical detail. Keep `/bands/{id}` and `/bands/{id}/graph` compatible.
- **Done when:** E2 band tests pass unchanged; new filters and parent taxonomy work; artist detail works for band and non-band artists; unknown IDs return `404`.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/integration/test_api_bands.py tests/integration/test_api_artists.py tests/integration/test_catalog_api.py
  ```
- **Files:** `backend/src/hmde/api/routes/bands.py`, `backend/src/hmde/api/routes/artists.py`, `backend/src/hmde/services/catalog.py`, `backend/src/hmde/schemas/api.py`, tests.
- **Evidence:** 2026-11-10: band filters for decade/year/retired and generic artist detail implemented; E2 endpoint behavior preserved. New band/artist tests and existing E2 catalog tests passed (13).

### T-004 — Add album and credit resources

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-005, FR-006.
- **Dependencies:** T-002.
- **Description:** Add `/api/v1/albums` with search/band/producer/decade/subgenre filters and `/api/v1/albums/{id}` with band, taxonomy and support-aware credits. Add `/api/v1/credits` filtered by album/band/artist/role/scope/run, bounded and paginated.
- **Done when:** album and credit list/detail are deterministic and bounded; support counts/ratios map correctly; unknown IDs return `404`; no raw payloads leak.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/integration/test_api_albums.py tests/integration/test_api_credits.py
  ```
- **Files:** `backend/src/hmde/api/routes/albums.py`, `backend/src/hmde/api/routes/credits.py`, `backend/src/hmde/services/albums.py`, `backend/src/hmde/services/credits.py`, `backend/src/hmde/schemas/api.py`, tests.
- **Evidence:** 2026-11-10: album list/detail and credit list/filter endpoints implemented with support-aware album credits. Album/credit tests passed (3).

### T-005 — Add producer rankings, detail and graph views

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-002, FR-004, FR-009, FR-010, FR-011, NFR-005.
- **Dependencies:** T-001, T-002.
- **Description:** Add `/api/v1/producers` ranking/filter endpoints and `/api/v1/producers/{id}` detail. Add `/api/v1/producers/{id}/graph?view=albums|bands` with top-k/ego selection, depth, `max_nodes`, `max_edges`, truncation metadata and bounded evidence. Read E7 `graph_node`, `graph_edge`, `producer_metric`, `node_metric` and community membership.
- **Done when:** rankings sort by album count, band count and betweenness; graph views never mix node types; limits/truncation are explicit; self-produced behavior is represented correctly; unknown producers return `404`; run metadata is present.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/integration/test_api_producers.py tests/integration/test_api_producer_graph.py
  ```
- **Files:** `backend/src/hmde/api/routes/producers.py`, `backend/src/hmde/services/producers.py`, `backend/src/hmde/schemas/api.py`, tests, `backend/tests/integration/conftest.py`.
- **Evidence:** 2026-11-10: producer list/detail/rankings and bounded `albums`/`bands` graph views implemented with run metadata, limits and evidence. Producer/graph tests passed (3), including a persisted E7 fixture run.

### T-006 — Add analysis-run, analytics and community resources

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-002, FR-012, NFR-005.
- **Dependencies:** T-001, T-002.
- **Description:** Add `/api/v1/analysis-runs`, `/api/v1/analysis-runs/{id}`, `/api/v1/analytics/summary`, `/api/v1/analytics/decades`, `/api/v1/communities` and `/api/v1/communities/{key}`. Read E7 run, temporal, node/producer metrics and community tables; include run/version metadata.
- **Done when:** run list/detail works; summary and decade metrics match persisted rows; community detail lists producer members; missing/non-terminal runs follow the documented errors.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/integration/test_api_analytics.py tests/integration/test_api_communities.py
  ```
- **Files:** `backend/src/hmde/api/routes/analytics.py`, `backend/src/hmde/services/analytics.py`, `backend/src/hmde/schemas/api.py`, tests.
- **Evidence:** 2026-11-10: analysis-run list/detail, summary, decade metrics and community list/detail endpoints implemented. Analytics/community tests passed (2).

### T-007 — Add search and taxonomy resources

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-007, FR-008, NFR-006.
- **Dependencies:** T-002.
- **Description:** Add bounded grouped SQL search and `/api/v1/taxonomy`. Implement parent/descendant resolution shared by band and album filters. Reject unknown taxonomy codes consistently.
- **Done when:** search returns grouped bands/artists, albums and producers with stable IDs and limits; taxonomy version/nodes/parents/assignable flags are exposed; parent filters include descendants.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/integration/test_api_search.py tests/integration/test_api_taxonomy.py
  ```
- **Files:** `backend/src/hmde/api/routes/search.py`, `backend/src/hmde/api/routes/taxonomy.py`, `backend/src/hmde/services/search.py`, `backend/src/hmde/services/taxonomy.py`, `backend/src/hmde/schemas/api.py`, tests.
- **Evidence:** 2026-11-10: bounded grouped search and versioned taxonomy endpoint added; band/album filters now resolve parent taxonomy descendants. Taxonomy/search tests passed (3).

### T-008 — Validate retired bands and E2 compatibility

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-003, FR-008, FR-018.
- **Dependencies:** T-003, T-007.
- **Description:** Enforce `dataset_membership` lifecycle behavior: retired bands excluded from default lists/search, accessible by direct ID, included only with explicit `include_retired=true`. Preserve existing E2 endpoint paths and required fields.
- **Done when:** active/retired tests pass; direct retired detail returns `200`; default list/search exclude retired bands; E2 contract tests remain green.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/integration/test_api_retired_bands.py tests/integration/test_catalog_api.py
  ```
- **Files:** `backend/src/hmde/services/catalog.py`, `backend/src/hmde/services/albums.py`, `backend/tests/integration/test_api_retired_bands.py`, tests.
- **Evidence:** 2026-11-10: retired membership hides bands from default list/search and keeps direct detail accessible; parent taxonomy filters fall back to exact codes when hierarchy is absent. Retired-band and E2 catalog tests passed (11).

### T-009 — Prove OpenAPI, generated types, CORS and read-only scope

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-015, FR-016, FR-019, NFR-001, NFR-004, NFR-007, NFR-008.
- **Dependencies:** T-003, T-004, T-005, T-006, T-007, T-008.
- **Description:** Regenerate `openapi.json` and `frontend/src/api/schema.d.ts`. Extend OpenAPI tests for new paths/schemas, GET-only operations, limits and run metadata. Add route/scope guards proving no write routes, no ETL/normalization/graph-construction imports and no mutation. Add CORS tests for allowed/blocked origins.
- **Done when:** OpenAPI includes all resources and only GET operations; TS generation succeeds; scope guards pass; allowed CORS origin receives headers; disallowed origin does not.
- **Verification:**
  ```bash
  cd backend
  uv run python -m hmde.openapi --output ../openapi.json
  uv run pytest tests/unit/test_openapi.py tests/unit/test_api_scope_guard.py tests/integration/test_api_cors.py

  cd ../frontend
  npm run generate:api
  npm run typecheck
  ```
- **Files:** `openapi.json`, `frontend/src/api/schema.d.ts`, `backend/tests/unit/test_openapi.py`, `backend/tests/unit/test_api_scope_guard.py`, `backend/tests/integration/test_api_health_cors.py`, `backend/src/hmde/main.py`.
- **Evidence:** 2026-11-10: OpenAPI regenerated with all E8 paths/schemas; TypeScript generation/typecheck passed; scope guard confirmed no batch/HTTP imports; CORS tests passed. OpenAPI, scope and CORS tests passed (6).

### T-010 — Add E7 fixture API integration and performance checks

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-017, NFR-002, NFR-003, NFR-009.
- **Dependencies:** T-009.
- **Description:** Add a reusable E7 fixture analysis run over the E2 seeded database so producer/analytics/graph endpoints have real persisted rows. Cover full API flows, run selection, truncation, query counts and representative timings. Add a full-corpus smoke run outside ordinary CI and record any deviations.
- **Done when:** fixture API suite passes with a completed E7 run; graph limits and query counts are bounded; 500-node target is measured; full-corpus API smoke succeeds; no ignored data is required in CI.
- **Verification:**
  ```bash
  cd backend
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \\
  TEST_DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde_test \\
    uv run pytest tests/integration/test_api_e7_fixture.py tests/integration/test_api_performance.py

  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \\
    uv run uvicorn hmde.main:app --port 8001
  ```
- **Files:** `backend/tests/integration/test_api_e7_fixture.py`, `backend/tests/integration/test_api_performance.py`, `backend/tests/integration/conftest.py`, test helpers.
- **Evidence:** 2026-11-10: session-scoped E7 fixture run added; full producer/analytics/graph flow passed; graph query count ≤10 and fixture graph latency under 1s. Full-corpus smoke: 384 producers, graph request 5 nodes/4 edges in 25.8 ms; albums, summary, decades, communities, taxonomy and search returned 200.

### T-011 — Complete API documentation, full checks and CI

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-020, NFR-001–NFR-010.
- **Dependencies:** T-010.
- **Description:** Document endpoints, run selection, graph limits, taxonomy filters and retired-band behavior in README/AGENTS/docs. Run backend and frontend checks, migration/OpenAPI drift and Compose validation. Push only with explicit owner authorization and record remote CI.
- **Done when:** docs match the contract; full suite/Ruff/format/OpenAPI/TS/Compose pass; no writes or unwanted frontend UI exist; remote CI passes; spec/tasks evidence and status are updated.
- **Verification:**
  ```bash
  cd backend
  uv run ruff check .
  uv run ruff format --check .
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \\
  TEST_DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde_test \\
    uv run pytest

  cd ../frontend
  npm run lint
  npm run typecheck
  npm run test
  npm run build

  cd ..
  docker compose config -q
  ```
- **Files:** `README.md`, `AGENTS.md`, `docs/03-data/api-v1.md`, `docs/README.md`, `docs/00-vision/roadmap.md`, `specs/README.md`, `specs/009-read-api/`.
- **Evidence:** 2026-11-10: API documentation added; backend 313 tests, Ruff check/format, OpenAPI drift and Compose passed; frontend lint/typecheck/21 tests/build passed; full-corpus API smoke passed. Remote GitHub Actions CI run [42741669410](https://github.com/cblancom/HMDE/actions/runs/42741669410) passed for commit `bb4ca1a`.

## 3. Coverage matrix

### Functional requirements

| Requirement | Tasks |
|---|---|
| FR-001 | T-001, T-003, T-008 |
| FR-002 | T-001, T-005, T-006 |
| FR-003 | T-003, T-008 |
| FR-004 | T-005 |
| FR-005 | T-004 |
| FR-006 | T-004 |
| FR-007 | T-007 |
| FR-008 | T-003, T-007, T-008 |
| FR-009 | T-005 |
| FR-010 | T-005, T-009 |
| FR-011 | T-005 |
| FR-012 | T-006 |
| FR-013 | T-002, T-010 |
| FR-014 | T-002, T-009 |
| FR-015 | T-009 |
| FR-016 | T-009 |
| FR-017 | T-010 |
| FR-018 | T-008 |
| FR-019 | T-001, T-009 |
| FR-020 | T-011 |

### Non-functional requirements

| Requirement | Tasks |
|---|---|
| NFR-001 | T-009, T-011 |
| NFR-002 | T-010 |
| NFR-003 | T-005, T-010 |
| NFR-004 | T-009 |
| NFR-005 | T-005, T-006 |
| NFR-006 | T-007, T-009 |
| NFR-007 | T-002, T-009 |
| NFR-008 | T-009 |
| NFR-009 | T-001, T-010 |
| NFR-010 | T-011 |

## 4. Validation evidence

| Criterion | Result | Evidence |
|---|---|---|
| AC-001 | Passed | E2 compatibility tests |
| AC-002 | Passed | Run-selection tests |
| AC-003 | Passed | Run error tests |
| AC-004 | Passed | Band/artist tests |
| AC-005 | Passed | Producer tests |
| AC-006 | Passed | Album tests |
| AC-007 | Passed | Credit tests |
| AC-008 | Passed | Search tests |
| AC-009 | Passed | Taxonomy tests |
| AC-010 | Passed | Graph view tests |
| AC-011 | Passed | Limit/truncation tests |
| AC-012 | Passed | Ranking tests |
| AC-013 | Passed | Analytics/community tests |
| AC-014 | Passed | Pagination/filter tests |
| AC-015 | Passed | Error tests |
| AC-016 | Passed | OpenAPI/TS generation |
| AC-017 | Passed | Read-only/scope tests |
| AC-018 | Passed | Retired-band tests |
| AC-019 | Passed | Performance/query-count tests |
| AC-020 | Passed | CORS tests |
| AC-021 | Passed | Documentation review |
| AC-022 | Passed | 313 backend tests, frontend checks, OpenAPI, Compose and remote CI run 42741669410 |

## 5. Notes

- No schema change is planned; additive indexes require measured justification and approval.
- E8 does not add frontend UI; only generated API types may change.
- E8 never recomputes E7 analytics inside a request.
- The graph endpoints are bounded and layer-specific; no full graph.
- Do not mark a task complete until its verification has been executed and recorded.
