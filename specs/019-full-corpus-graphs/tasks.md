# Tasks — SPEC-019

- **Status:** Validated
- **Spec:** [spec.md](spec.md)
- **Plan:** [plan.md](plan.md)

## 1. Execution order

```text
T-000 ──► T-001 ──► T-002 ──► T-003 ──► T-004 ──► T-005 ──► T-006 ──► T-007 ──► T-008 ──► T-009
```

T-000 is complete. T-001 and T-002 must precede the frontend tasks. T-005 can run after T-002 but must be completed before T-007. T-006 and T-007 are the integration gates; T-009 is the producer-field follow-up.

## 2. Tasks

### T-000 — Seed E2E dataset memberships and guard empty graphs

- **Status:** Completed 2026-11-19.
- **Requirements:** AC-007 test infrastructure.
- **Dependencies:** none.
- **Description:** Add dataset memberships for the E2E fixture dataset before building the network run. Fail the seed if the producer–album or producer–band graph is empty. Recreate `hmde_e2e` to verify the CI path rather than reusing a stale analysis run.
- **Done when:** A clean E2E database produces a non-empty analysis run and the Playwright suite passes in CI mode.
- **Verification:**
  ```bash
  cd backend
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde_e2e \
    uv run python -m tests.e2e.seed
  cd ../frontend
  CI=true npm run test:e2e
  ```
- **Files:** `backend/tests/e2e/seed.py`, `backend/tests/support/memberships.py`, `tasks.md`.
- **Evidence:** Clean `hmde_e2e` database seeded with analysis run `aea9bbd5-4ca9-4380-b95d-45db69670daa` (`net-a86d9d9691ba6230`) with 14 band memberships; 26 Playwright tests passed in CI mode at Phase 0. The previous failure was caused by an empty E2E graph, not a frontend regression.

### T-001 — Extend the graph API contract and schemas

- **Status:** Completed 2026-11-20.
- **Requirements:** FR-002, FR-005, FR-006, FR-007, NFR-005, AC-006, AC-009.
- **Dependencies:** T-000.
- **Description:** Add `band_limit` and `album_limit` to the global overview, allow `limit=0` for producer ego neighbors, add a producer limit to the band graph, raise the safety-cap ranges and expose requested/returned/omitted counts in graph metadata. Regenerate OpenAPI and TypeScript types.
- **Done when:** The API rejects invalid limits with 422, accepts `0` and positive limits, reports the limits in metadata and preserves the existing response shape for clients that omit optional parameters.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/integration/test_api_producer_overview_graph.py \
    tests/integration/test_api_producer_graph.py \
    tests/integration/test_api_bands.py tests/unit/test_openapi.py
  uv run python -m hmde.openapi --output ../openapi.json
  cd ../frontend
  npm run generate:api
  ```
- **Files:** `backend/src/hmde/api/routes/graph.py`, `backend/src/hmde/api/routes/producers.py`, `backend/src/hmde/api/routes/bands.py`, `backend/src/hmde/schemas/api.py`, `backend/src/hmde/schemas/graph.py`, `openapi.json`, `frontend/src/api/schema.d.ts`, related tests.
- **Evidence:** Schema and routes extended, OpenAPI and TypeScript types regenerated, and 31 targeted API tests passed. Pending final full-suite evidence.

### T-002 — Implement deterministic target selection and full-layer responses

- **Status:** Completed 2026-11-20.
- **Requirements:** FR-001, FR-002, FR-005, FR-006, BR-001–BR-005, AC-001, AC-002, AC-006.
- **Dependencies:** T-001.
- **Description:** Select all band targets by default, apply album/band limits deterministically by edge weight and stable identifier, retain connected producers, and set truncation metadata only when the server safety cap is exceeded. Extend the producer and band graph services for all-neighbor and producer-limit behavior.
- **Done when:** `band_limit=0` returns 509 bands and 1,708/1,700 band-layer nodes/edges; `album_limit=0` can return 3,719/4,217 album-layer nodes/edges; finite limits return at most N targets with stable ordering; no silent truncation.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/integration/test_api_producer_overview_service.py \
    tests/integration/test_api_producer_overview_graph.py \
    tests/integration/test_api_producer_graph.py
  ```
- **Files:** `backend/src/hmde/services/producers.py`, `backend/src/hmde/services/graph.py`, related tests.
- **Evidence:** v0.3.0 reference verified: all bands 509, 1,708 nodes / 1,700 edges; all albums 2,275 albums, 3,719 nodes / 4,217 edges; default 500 albums 1,944 nodes / 1,717 edges with 1,775 omitted; ego limit 0 returns all neighbors; band producer cap reports omissions. Targeted API suite 31 passed.

### T-003 — Add overview limits and load all bands in the index

- **Status:** Completed 2026-11-20.
- **Requirements:** FR-003, FR-004, FR-005, AC-003, AC-004.
- **Dependencies:** T-001, T-002.
- **Description:** Add numeric plus All controls for bands and albums to the global overview, persist them in the URL, request the full-corpus safety cap, and page through the bands endpoint until the total is reached. Display loaded and total counts and truncation state.
- **Done when:** The overview defaults to All bands and 500 albums, numeric/All changes survive refresh/back navigation, and the index shows all 509 bands without a 200-row cap.
- **Verification:**
  ```bash
  cd frontend
  npm run test -- ProducerOverviewPage.test.tsx
  npm run typecheck
  ```
- **Files:** `frontend/src/pages/ProducerOverviewPage.tsx`, `frontend/src/components/ProducerOverviewControls.tsx`, `frontend/src/components/OverviewIndex.tsx`, `frontend/src/api/producerGraph.ts`, `frontend/src/api/bands.ts`, related tests.
- **Evidence:** Overview now defaults to All bands and 500 albums, sends `max_nodes=5000`/`max_edges=5000`, persists `band_limit`/`album_limit`, and pages the band index with `getAllBands`. Focused frontend suite 59 passed; typecheck and lint passed.

### T-004 — Add limits to producer ego and band detail graphs

- **Status:** Completed 2026-11-20.
- **Requirements:** FR-003, FR-005, AC-003, AC-005.
- **Dependencies:** T-001, T-002.
- **Description:** Add All/numeric neighbor limits to the producer ego graph, label the control Albums or Bands by view, and add an All/numeric producer limit to the band detail graph. Keep URL state and visible counts.
- **Done when:** The ego graph can request all neighbors and the band graph can request all producers; both display truncation only when the safety cap is reached.
- **Verification:**
  ```bash
  cd frontend
  npm run test -- ProducerGraphPage.test.tsx BandDetailPage.test.tsx
  npm run typecheck
  ```
- **Files:** `frontend/src/pages/ProducerGraphPage.tsx`, `frontend/src/components/GraphControls.tsx`, `frontend/src/pages/BandDetailPage.tsx`, `frontend/src/components/BandGraph.tsx`, related tests.
- **Evidence:** Ego graph defaults to All neighbors for bands and 100 for albums, with All/numeric control and 2,000-node/5,000-edge caps; band detail has an All/numeric producer limit with 2,000-node cap. Shared `GraphLimitField` and API clients updated. Full frontend suite 124 passed; lint and typecheck passed.

### T-005 — Measure full-corpus performance and choose large-graph rendering

- **Status:** Completed 2026-11-20.
- **Requirements:** NFR-001, NFR-002, AC-001, AC-002, AC-007, BR-004.
- **Dependencies:** T-002, T-003.
- **Description:** Measure the complete band layer, the default 500-album view and the explicit all-albums view for API latency, navigation, view switching, layout completion and memory. If the all-albums Force view exceeds the interaction target, use a static server layout for that view and keep Force as an explicit opt-in. Record the decision.
- **Done when:** Full band/default album targets pass or have one documented exception; all-albums behavior is usable with a documented layout decision; counts and timings are recorded in `docs/01-architecture/qa-report.md`.
- **Verification:**
  ```bash
  cd frontend
  HMDE_API_BASE_URL=http://localhost:8001 \
  HMDE_WEB_BASE_URL=http://localhost:5173 \
    npm run test:perf
  ```
- **Files:** `frontend/e2e/performance.spec.ts`, `docs/01-architecture/qa-report.md`, `docs/03-data/analysis-v0.3.0.md`, `tasks.md`.
- **Evidence:** v0.3.0 probe passed. API p95: all bands 1,034 ms, default 500 albums 1,030 ms, all albums 1,196 ms. Browser p95: all bands 3.95 s, default albums 4.27 s, all albums 6.04 s (explicit exception), view-switch ack 1.43 s (exception), full settle 1.60 s, panel 654 ms, ego 851 ms. The overview now defaults to static bipartite for both views; Force is opt-in. CoSE timed out at 30 s and fCoSE completed in 34.1 s as finite-layout exceptions.

### T-006 — Add regression, E2E and contract coverage

- **Status:** Completed 2026-11-20.
- **Requirements:** NFR-003, NFR-004, NFR-005, AC-006, AC-008, AC-009.
- **Dependencies:** T-003, T-004, T-005.
- **Description:** Add API, frontend and Playwright tests for All/numeric limits, index paging beyond 200, truncation metadata, ego All and band detail limits. Regenerate OpenAPI and TypeScript types and review the contract diff.
- **Done when:** Unit, integration, contract, frontend, E2E and axe checks pass; no schema or migration change is present; OpenAPI and TypeScript types are current.
- **Verification:**
  ```bash
  cd backend
  uv run ruff check .
  uv run ruff format --check .
  uv run pytest
  uv run python -m hmde.openapi --output ../openapi.json
  cd ../frontend
  npm run lint
  npm run typecheck
  npm run test
  npm run build
  npm run test:e2e
  ```
- **Files:** `backend/tests/`, `frontend/src/**/*.test.tsx`, `frontend/e2e/`, `openapi.json`, `frontend/src/api/schema.d.ts`.
- **Evidence:** Backend 346 passed with Ruff and format; frontend lint, typecheck, 124 tests and build passed; E2E 27 passed in CI mode with nine axe route scans. Added coverage for numeric/All band and album limits, band-detail producer limits, ego All, index paging and truncation states. OpenAPI and TypeScript types regenerated.

### T-007 — Update documentation and validate SPEC-019

- **Status:** Completed 2026-11-20.
- **Requirements:** AC-009.
- **Dependencies:** T-006.
- **Description:** Update the spec index, roadmap, analysis/performance documentation and this task file. Record reference counts, defaults, limits and any performance exception. Review the diff for scope creep and secrets.
- **Done when:** Documentation matches the implementation; AC-001–AC-009 have evidence; the spec is ready for validation.
- **Verification:**
  ```bash
  git diff --check
  git status --short
  ```
- **Files:** `AGENTS.md`, `specs/README.md`, `docs/00-vision/roadmap.md`, `docs/01-architecture/qa-report.md`, `docs/03-data/analysis-v0.3.0.md`, `specs/019-full-corpus-graphs/spec.md`, `tasks.md`.
- **Evidence:** Spec and plan set to Validated; index, roadmap, QA and analysis docs updated; `git diff --check` passed.

### T-008 — Stabilize selection and filter the induced overview graph

- **Status:** Completed 2026-11-20.
- **Requirements:** FR-003, FR-005, NFR-001, AC-003, AC-007.
- **Dependencies:** T-007.
- **Description:** Memoize the adapted overview graph so selecting a node only updates the URL/details and does not recreate Cytoscape or restart CoSE. Hide producers with degree zero in the selected subgraph by default, expose them through “Show isolated producers”, and do not paint album targets with no visible edge.
- **Done when:** Selecting a node does not rebuild the graph; `album_limit=100` shows only the 100 connected albums and their connected producers by default; all 509 bands remain in the bands view; tests cover the behavior.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  CI=true npm run test:e2e
  ```
- **Files:** `frontend/src/pages/ProducerOverviewPage.tsx`, `frontend/src/graph/adapter.ts`, `frontend/src/pages/ProducerOverviewPage.stability.test.tsx`, `frontend/src/graph/adapter.test.ts`, `frontend/e2e/graph.spec.ts`.
- **Evidence:** Adapted graph is memoized; node selection leaves the graph object unchanged in the stability test. Adapter test excludes an album without edges. `album_limit=100` resolves to 455 visible nodes (100 albums + 355 connected producers) instead of 1,544. Frontend 126 tests, lint, typecheck and build passed; E2E 27 passed with nine axe scans.

### T-009 — Editable producer limit field

- **Status:** Completed 2026-11-20.
- **Requirements:** FR-003, NFR-003, AC-003.
- **Dependencies:** T-008.
- **Description:** Replace the global producer preset selector with a numeric field. Support All, values 1–1000 and fallback 100 when All is unchecked. Commit the typed value on blur or Enter to avoid refetching on every keystroke.
- **Done when:** A user can enter any integer 1–1000, the URL stores `producers=<n>`, the API receives `producer_limit=<n>`, All sends 0, and invalid/out-of-range values are clamped safely.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  CI=true npm run test:e2e
  ```
- **Files:** `frontend/src/components/GraphLimitField.tsx`, `frontend/src/components/ProducerOverviewControls.tsx`, `frontend/src/pages/ProducerOverviewPage.tsx`, `frontend/src/components/ProducerOverviewControls.test.tsx`, `frontend/src/pages/ProducerOverviewPage.test.tsx`, `frontend/e2e/graph.spec.ts`.
- **Evidence:** Numeric input with `All`; fallback 100; max 1000; commit on blur/Enter; Escape resets. Frontend 127 tests, lint, typecheck and build passed; E2E 27 passed with nine axe scans.

## 3. Coverage matrix

### Functional requirements

| Requirement | Tasks |
|---|---|
| FR-001 | T-002, T-003, T-007 |
| FR-002 | T-001, T-002 |
| FR-003 | T-003, T-004, T-008, T-009 |
| FR-004 | T-003 |
| FR-005 | T-001, T-003, T-004 |
| FR-006 | T-001, T-002 |
| FR-007 | T-001, T-006 |

### Non-functional requirements

| Requirement | Tasks |
|---|---|
| NFR-001 | T-005, T-008 |
| NFR-002 | T-005 |
| NFR-003 | T-004, T-006, T-009 |
| NFR-004 | T-006 |
| NFR-005 | T-001, T-006 |

## 4. Validation evidence

| Criterion | Result | Evidence |
|---|---|---|
| AC-001 | Pass | API reference: 509 bands, 1,708 nodes / 1,700 edges, untruncated. |
| AC-002 | Pass | Default 500 albums: 1,944 nodes / 1,717 edges; All albums: 3,719 / 4,217. |
| AC-003 | Pass | Vitest and Playwright band/album limit tests; T-008 verifies stable selection; T-009 verifies the editable producer limit. |
| AC-004 | Pass | `getAllBands` paging test and E2E index coverage. |
| AC-005 | Pass | Ego All and band producer-limit tests. |
| AC-006 | Pass | 422 range tests and truncation metadata assertions. |
| AC-007 | Pass with documented exceptions | 27 E2E, nine axe scans; all-bands 3.95 s, default albums 4.27 s; all albums 6.04 s, view-switch ack 1.43 s and CoSE >30 s documented. T-008 reduces the default visible graph by hiding out-of-subset producers. |
| AC-008 | Pass | No schema, migration or canonical graph change. |
| AC-009 | Pass | OpenAPI and TypeScript regenerated; spec, index, roadmap and reports updated. |

## 5. Notes

- Phase 0 is complete and authorized separately to unblock CI.
- T-001–T-009 are complete; the spec is validated.
- The index fix is client-side paging; do not raise the public list endpoint cap for this.
- The overview defaults to static bipartite; Force is explicit. All albums remains opt-in.
- Record exact counts and timings; do not describe a truncated graph as complete.

