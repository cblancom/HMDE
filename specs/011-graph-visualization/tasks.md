# Tasks — SPEC-011 Producer graph visualization and interaction

- **Status:** Implemented locally; T-001–T-016 completed; remote CI and manual ego interaction/performance checks pending
- **Spec:** [spec.md](spec.md)
- **Plan:** [plan.md](plan.md)

## 1. Execution order

```text
T-001 ─► T-002 ─┬─► T-003 ─┬─► T-004 ─┐
                │          └─► T-005 ─┼─► T-006 ─► T-007 ─► T-008 ─► T-009 ─► T-010
                └─► T-004 ────────────┘                                              │
                                                                                     ▼
T-011 ─► T-012 ─► T-013 ─► T-014 ─► T-015 ─► T-016
```

T-001–T-010 delivered the producer ego graph. T-011–T-016 deliver the global producer overview: backend schemas/service, API route/tests, frontend client/adapter, page/controls/details, physics/labels, then documentation and full CI.

## 2. Tasks

### T-001 — Add physics dependency, graph client and adapter

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-002, FR-003, FR-007, NFR-006.
- **Dependencies:** SPEC-010 validated; plan/tasks approved.
- **Description:** Add `cytoscape-d3-force@1.1.4`. Add typed `getProducerGraph` API client and query key. Implement graph adapter functions for `albums` and `bands` views: validate node types, map nodes/edges, normalize attributes/evidence, apply role/decade/taxonomy filters and produce fallback table data. Add the year color scale and graph class mapping.
- **Done when:** adapter rejects mixed views; nodes/edges map deterministically; filters work on available metadata; year/type/role/support classes exist; unit tests cover mapping and filtering.
- **Verification:**
  ```bash
  cd frontend
  npm run generate:api
  npm run lint
  npm run typecheck
  npm run test
  ```
- **Files:** `frontend/package.json`, `frontend/package-lock.json`, `frontend/src/api/producerGraph.ts`, `frontend/src/api/queryKeys.ts`, `frontend/src/graph/adapter.ts`, `frontend/src/types/cytoscape-d3-force.d.ts`, tests.
- **Evidence:** 2026-11-10: added `cytoscape-d3-force@1.1.4`, typed graph client/query key, adapter for album/band views, role/decade/taxonomy filters, year scale and table mapping. Frontend lint/typecheck/46 tests passed.

### T-002 — Add graph route, page shell and producer entry

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-001, FR-003, FR-008, FR-011, NFR-001.
- **Dependencies:** T-001.
- **Description:** Add `/producers/:producerId/graph` route and `ProducerGraphPage`. Add the `Open graph` link from producer detail. Add view tabs (`Albums`/`Bands`), limit/depth controls, URL state, API query, run metadata and loading/error/empty/truncated states.
- **Done when:** producer detail links to the graph; view/tab and limit/depth update the URL; API metadata and truncation are visible; invalid producer/view states are recoverable.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  ```
- **Files:** `frontend/src/App.tsx`, `frontend/src/pages/ProducerGraphPage.tsx`, `frontend/src/pages/ProducerDetailPage.tsx`, `frontend/src/components/GraphControls.tsx`, `frontend/src/api/producerGraph.ts`, tests.
- **Evidence:** 2026-11-10: graph route, producer entry link, view tabs, limit/depth URL state, loading/error/404/truncated states and graph page shell added. Frontend lint/typecheck/48 tests passed.

### T-003 — Implement Cytoscape canvas and d3-force lifecycle

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-004, FR-005, FR-006, FR-012, FR-013, NFR-001, NFR-002, NFR-007.
- **Dependencies:** T-002.
- **Description:** Implement the Cytoscape canvas with `cytoscape-d3-force`. Start infinite force simulation on the loaded ego network; support node dragging; add freeze, resume and reheat controls; pause on hidden documents; start frozen under reduced motion; destroy the instance and listeners on unmount.
- **Done when:** dragging moves neighbors according to the force simulation; freeze stops ticks; resume/reheat restart safely; hidden tabs pause; reduced motion starts frozen; cleanup leaves no listeners/instance.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  ```
- **Files:** `frontend/src/components/ProducerGraph.tsx`, `frontend/src/components/GraphControls.tsx`, `frontend/src/pages/ProducerGraphPage.tsx`, `frontend/src/graph/styles.ts`, tests.
- **Evidence:** 2026-11-10: Cytoscape canvas with `cytoscape-d3-force`, infinite physics, drag support, freeze/resume/reheat, visibility pause, reduced-motion fallback and cleanup implemented. Physics lifecycle tests passed; frontend 50 tests.

### T-004 — Add visual encoding, legend, details and filters

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-007, FR-008, FR-009, NFR-004.
- **Dependencies:** T-003.
- **Description:** Apply shapes/colors/line styles and year scale to Cytoscape elements. Add legend, selected node/edge details panel and client-side filters. Show edge evidence, support, role, year/decade and related links. Disable decade/taxonomy filters in band view with an explanation.
- **Done when:** visual encodings match the legend; selection shows details and links; filters hide matching elements; band-view limitations are explicit; color is not the only signal.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  ```
- **Files:** `frontend/src/components/GraphLegend.tsx`, `GraphDetails.tsx`, `GraphFilters.tsx`, `GraphControls.tsx`, `graph/styles.ts`, `pages/ProducerGraphPage.tsx`, tests.
- **Evidence:** 2026-11-10: visual encodings, year scale, legend, selection details, role/decade/taxonomy filters and band-view filter limitations implemented. Frontend lint/typecheck/53 tests passed.

### T-005 — Harden empty, error, truncated and filtered states

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-003, FR-008, FR-011, NFR-001.
- **Dependencies:** T-003, T-004.
- **Description:** Handle no graph, no edges, API errors, missing producer, invalid view, `truncated=true`, filtered-empty and canvas failure. Keep run metadata/truncation persistent and provide clear recovery actions.
- **Done when:** every state is explicit and recoverable; truncation is never hidden; filtered-empty offers clear filters; canvas failure preserves fallback data.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  ```
- **Files:** `pages/ProducerGraphPage.tsx`, `components/ProducerGraph.tsx`, `components/AsyncState.tsx`, `graph/adapter.ts`, tests.
- **Evidence:** 2026-11-10: empty graph, invalid view, filtered-empty, truncation, adapter mismatch and 404 states implemented. Frontend lint/typecheck/56 tests passed.

### T-006 — Complete accessibility and fallback

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-010, FR-012, NFR-002, NFR-003, NFR-007.
- **Dependencies:** T-003, T-004, T-005.
- **Description:** Add the accessible node/edge table fallback, canvas accessible name, keyboard-reachable controls, visible focus and reduced-motion path. Ensure details and legend expose the same information as the canvas.
- **Done when:** table fallback lists all loaded nodes and edges; controls are keyboard operable; reduced motion starts frozen; focus is visible; legend/details are outside the canvas.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  npm run build
  ```
- **Files:** `components/GraphFallbackTable.tsx`, `GraphLegend.tsx`, `GraphDetails.tsx`, `pages/ProducerGraphPage.tsx`, tests.
- **Evidence:** 2026-11-10: accessible node/edge tables, legend/details outside canvas, labeled controls, focus treatment, reduced-motion start and no color-only encoding verified. Frontend lint/typecheck/57 tests/build passed.

### T-007 — Prove physics lifecycle, adapter and scope with tests

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-004, FR-005, FR-006, FR-014, FR-015, NFR-005, NFR-006.
- **Dependencies:** T-006.
- **Description:** Add unit/component tests with mocked Cytoscape and d3-force for layout registration, infinite physics options, drag handling, freeze/resume/reheat, visibility pause and cleanup. Update the E9 scope guard so graph/`cytoscape-d3-force` is allowed in E10 but Tailwind/Plotly/new-renderer changes remain rejected.
- **Done when:** physics lifecycle and options are asserted; scope guards reflect E10; tests pass.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  ```
- **Files:** `frontend/src/**/*.test.tsx`, `frontend/src/scope.test.ts`, package inspection.
- **Evidence:** 2026-11-10: physics options, freeze/resume/reheat, reduced-motion start, hidden-tab pause, cleanup and scope guards tested. Frontend lint/typecheck/59 tests passed.

### T-008 — Document physics, run manual checklist and close CI

- **Status:** Completed locally (2026-11-10); manual browser physics and remote CI pending.
- **Requirements:** FR-015, NFR-001–NFR-008.
- **Dependencies:** T-007.
- **Description:** Document graph route, views, physics controls, force parameters, filter limitations and 500-node cap. Run a manual browser checklist for drag/neighbor response, freeze/resume/reheat, reduced motion, hidden-tab pause, empty/truncated states and 500-node behavior. Run full frontend/backend checks and Compose validation. Push only with explicit authorization and record remote CI.
- **Done when:** docs match behavior; manual checklist is recorded; full checks pass; remote CI passes; spec/tasks evidence and status are updated.
- **Verification:**
  ```bash
  cd frontend
  npm ci
  npm run generate:api
  npm run lint
  npm run typecheck
  npm run test
  npm run build

  cd ../backend
  uv run ruff check .
  uv run ruff format --check .
  uv run pytest

  cd ..
  docker compose config -q
  ```
- **Files:** `README.md`, `AGENTS.md`, `docs/01-architecture/frontend.md`, `docs/README.md`, `docs/00-vision/roadmap.md`, `specs/README.md`, `specs/011-graph-visualization/`.
- **Evidence:** 2026-11-10: docs updated; frontend 59 tests, lint, typecheck and build passed; backend 313 tests, Ruff/format and Compose passed; dev graph endpoint and graph page modules returned HTTP 200; web container recreated with the new dependency. Manual drag/freeze/reheat and 500-node visual checklist pending (no graphical browser). Remote CI pending.

### T-009 — Fix force node identity and guard layout failures

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-004, FR-006, FR-011, NFR-001, NFR-007.
- **Dependencies:** T-008.
- **Description:** The graph page rendered a blank screen because `FORCE_OPTIONS` omitted `linkId`. `cytoscape-d3-force` copies edge data with canonical UUID `source`/`target` values, while d3-force defaults the node accessor to the array index; `layout.run()` then threw `node not found: <uuid>` synchronously inside the component effect, unmounting the React root. Add the id accessor, catch force-layout failures, fall back to a frozen static `breadthfirst` layout, and add regression coverage.
- **Done when:** the force layout uses node ids; a failing layout leaves the page content, table fallback and a frozen canvas visible; tests cover both behaviors.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  ```
- **Files:** `frontend/src/components/ProducerGraph.tsx`, `frontend/src/components/ProducerGraph.test.tsx`, spec/tasks documentation.
- **Evidence:** 2026-11-10: added `linkId: (node) => node.id`; `runForce` now catches layout errors and applies a frozen `breadthfirst` fallback; tests assert the id accessor and the fallback. Frontend lint, typecheck and 60 tests passed. Headless Chromium loaded `?view=bands` and `?view=albums`: `<div id="root">` is populated, the page shows `Physics running`, the table fallback is present and the console has no errors.

### T-010 — Improve neighbor spacing and album label readability

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-004, FR-007, NFR-001, NFR-003.
- **Dependencies:** T-009.
- **Description:** The single-producer ego graph collapsed leaves around the seed because collision radius was effectively 1 and many-body strength was weak. Album titles were hidden by a `label: ''` override until selection. Tune collision/repulsion/link distance by node type, give the canvas more vertical space, and always show album titles with wrapping and a readable background.
- **Done when:** neighbors spread around the producer, album titles are readable without hover or selection, and physics remains responsive.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  npm run build
  ```
  Plus a headless-browser screenshot of the `albums` and `bands` views.
- **Files:** `frontend/src/components/ProducerGraph.tsx`, `frontend/src/graph/styles.ts`, `frontend/src/graph/styles.test.ts`, `frontend/src/components/ProducerGraph.test.tsx`, `frontend/src/index.css`, spec/tasks/plan documentation.
- **Evidence:** 2026-11-10: added type-sized collision radii (producer 22, album 28, band 34), `collideStrength: 0.9`, `collideIterations: 2`, `manyBodyStrength: -320` and a node-count-based `linkDistance` (180–300) capped by the canvas height. The canvas min-height is now `clamp(32rem, 65vh, 48rem)`. Album labels always render with `font-size: 10px`, wrapping at 100px and a 90% background. Frontend lint, typecheck, 62 tests and build passed. A headless Chromium runtime probe on the 21-node album graph measured producer-to-album distances of 276–290 px (average 285), centered in a 1136×723 canvas, with album labels rendered at 10px and full opacity; at a 900px viewport the layout adapted to 199–202 px and remained centered without clipping. The bands view also rendered without console errors.

### T-011 — Add overview schemas and producer graph service

- **Status:** Completed (2026-11-11).
- **Requirements:** FR-016, FR-018, FR-019, FR-020, NFR-004, NFR-010.
- **Dependencies:** Revision 6 spec/plan/tasks approved; T-010.
- **Description:** Add `ProducerOverviewGraphLimits`, `ProducerOverviewGraphMeta` and `ProducerOverviewGraphResponse` to `schemas/api.py`. Implement `get_producer_overview_graph` in `services/producers.py`: producer ranking/filter reuse, view-specific edge selection, shared-neighbor edges, album role deduplication, isolated-producer handling, node metric enrichment, deterministic caps/truncation and run metadata.
- **Done when:** both views return one node per shared band/album with one edge per credited producer; no producer–producer edges; all producers fit the 1,000-node cap in the current corpus; top-k, filters, isolated toggle and truncation are deterministic.
- **Verification:**
  ```bash
  cd backend
  uv run ruff check .
  uv run ruff format --check .
  uv run pytest
  ```
- **Files:** `backend/src/hmde/schemas/api.py`, `backend/src/hmde/services/producers.py`, service tests.
- **Evidence:** 2026-11-11: added the overview limits, meta and response schemas and implemented `get_producer_overview_graph` with producer ranking reuse, shared band/album nodes, album role deduplication, isolated handling, metric enrichment, deterministic caps and run metadata. Band targets are typed `band` even when the artist also has a producer role, so no producer–producer edge is exposed. Added five integration service tests covering shared nodes, role deduplication, isolated toggle, top-k ordering and filters/caps. `uv run ruff check .`, `uv run ruff format --check .` and `uv run pytest` passed (220 passed, 98 skipped). The new integration suite passed 5/5 with `TEST_DATABASE_URL`; the full-corpus v0.2 run returns 398 nodes / 426 edges in `bands` (341 producer sources + 57 bands, 384 matched producers) and 968 nodes / 1,134 edges in `albums`, with no truncation at the 1,000-node cap.

### T-012 — Add overview API route, OpenAPI and integration tests

- **Status:** Pending.
- **Requirements:** FR-016, FR-014, NFR-005, NFR-010.
- **Dependencies:** T-011.
- **Description:** Add `api/routes/graph.py` with `GET /api/v1/graph/producers`, query validation and the existing analysis-run dependency. Register the router in `main.py`. Add integration tests for both views, shared band/album fixtures, isolated toggle, top-k/sort, decade/subgenre, caps/truncation, invalid run and OpenAPI path/schema presence.
- **Done when:** endpoint and parameters match the spec; shared-node and isolated behavior are proven; OpenAPI exposes the new path and schemas; no migration is added.
- **Verification:**
  ```bash
  cd backend
  uv run ruff check .
  uv run ruff format --check .
  uv run --env-file ../.env pytest
  ```
  plus `uv run python -m hmde.openapi --output ../openapi.json`.
- **Files:** `backend/src/hmde/api/routes/graph.py`, `backend/src/hmde/main.py`, `backend/tests/integration/test_api_producer_overview_graph.py`, `backend/tests/unit/test_openapi.py`, `openapi.json`.
- **Evidence:** Pending.

### T-013 — Add overview client and adapter

- **Status:** Completed (2026-11-11).
- **Requirements:** FR-002, FR-007, FR-018, NFR-006.
- **Dependencies:** T-012.
- **Description:** Add `getProducerOverviewGraph` and the overview query key. Add `adaptOverviewGraph` for producer, band and album nodes: validate view, merge metric attributes, compute degree-based sizes, derive incident producer lists for shared nodes, build details/table data and expose filtered counts.
- **Done when:** generated API types compile; adapter rejects mixed views; shared nodes list every incident producer; table and details match the canvas; unit tests cover both views and filters.
- **Verification:**
  ```bash
  cd frontend
  npm run generate:api
  npm run lint
  npm run typecheck
  npm run test
  ```
- **Files:** `frontend/src/api/producerGraph.ts`, `frontend/src/api/queryKeys.ts`, `frontend/src/graph/adapter.ts`, `frontend/src/graph/adapter.test.ts`.
- **Evidence:** 2026-11-11: added the generated overview response type, `getProducerOverviewGraph`, the overview query key and `adaptOverviewGraph`. The adapter validates the view, filters by role/decade/subgenre, removes isolated producers on request, computes degree sizes, incident-producer lists and post-filter counts, marks producer search matches and adds producer names to the shared-node table detail. Unit tests cover both views, shared nodes, role/taxonomy/decade filters, isolated hiding and the API query mapping. Frontend lint, typecheck and 73 tests passed.

### T-014 — Add `/graph` page, navigation, controls, details and table

- **Status:** Completed (2026-11-11).
- **Requirements:** FR-001, FR-003, FR-006, FR-008, FR-009, FR-010, FR-011, FR-017, FR-019, FR-020, FR-021, NFR-003, NFR-008.
- **Dependencies:** T-013.
- **Description:** Add the `/graph` route and primary `Graph` navigation. Build `ProducerOverviewPage` and `ProducerOverviewControls` with view tabs, producer selection/sort, decade/subgenre, isolated toggle, physics controls, URL state, counts, truncation, details and accessible table. Add producer and ego drill-down links.
- **Done when:** global bands/albums views load, filters and toggle update counts/table immediately, shared-node selection lists connected producers, producer selection links to its ego graph, and empty/error/truncated states are recoverable.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  npm run build
  ```
- **Files:** `frontend/src/App.tsx`, `frontend/src/components/AppShell.tsx`, `frontend/src/pages/ProducerOverviewPage.tsx`, `frontend/src/components/ProducerOverviewControls.tsx`, `frontend/src/pages/ProducersPage.tsx`, `frontend/src/pages/ProducerDetailPage.tsx`, tests.
- **Evidence:** 2026-11-11: added `/graph`, the primary `Graph` navigation item, producer-page and producer-detail entry links, the overview page and controls. The page carries view, producer limit/sort/order, decade, subgenre, isolated and selection URL state; shows post-filter counts, truncation and invalid-view notices; renders legend, canvas, accessible tables and a details panel with incident producers, entity links and ego-graph drill-down. Tests cover route/navigation links, server parameter updates, isolated hiding, shared-node details, drill-down links, truncation, empty and error states. Frontend lint, typecheck, 73 tests and build passed.

### T-015 — Tune overview physics, labels and browser behavior

- **Status:** Completed (2026-11-11).
- **Requirements:** FR-004, FR-005, FR-012, FR-013, FR-015, FR-022, NFR-001, NFR-002, NFR-004, NFR-007, NFR-009.
- **Dependencies:** T-014.
- **Description:** Add the overview force preset and label decluttering. Verify initial fit, shared hubs, isolated producers, producer/album label visibility by zoom, dragging, freeze/resume/reheat, reduced motion, hidden-tab pause and the 398/968-node views in a headless browser. Use a documented finite settle if infinite physics is not usable.
- **Done when:** the global network is readable and responsive, labels follow the contract, physics failures keep the table/details visible, and the chosen preset/mode is recorded.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  npm run build
  ```
  plus headless browser screenshots/probes for both views.
- **Files:** `frontend/src/components/ProducerGraph.tsx`, `frontend/src/graph/styles.ts`, `frontend/src/index.css`, tests and docs.
- **Evidence:** 2026-11-11: added an infinite overview force preset (`manyBodyStrength=-45`, `linkDistance=42–90`, type collision 8/7/10, `collideStrength=0.6`, `alphaDecay=0.035`, `velocityDecay=0.55`), a stable initial fit, degree-sized nodes, zoom-decluttered labels (bands always; producers/albums at 12px; selected/search matches always), muted isolated producers and search highlighting without recreating the graph. A headless Chromium probe on the v0.2 corpus loaded 398 nodes / 426 edges in `bands` (341 producers + 57 bands, 43 isolated producer entities represented by their shared band nodes) and 968 nodes / 1,134 edges in `albums` (384 producers + 584 albums, 43 isolated producers); the initial fit kept the networks inside the canvas, physics moved nodes, freeze/resume/reheat and dragging kept the page stable, search matched 5 producers, reduced motion started frozen with the table available, and shared-node selection listed all 32 producers for Motörhead. The albums isolated toggle reduced the loaded network to 893 nodes / 951 edges and 341 producers. Frontend lint, typecheck, 76 tests and build passed. Bands-view isolated producers share band entities, so they remain visible as band nodes to avoid deleting shared bands; the albums view hides them as producer nodes.

### T-016 — Update documentation, run full checks and close CI

- **Status:** Completed locally (2026-11-11); remote CI pending explicit authorization.
- **Requirements:** FR-014, FR-015, FR-022, NFR-005.
- **Dependencies:** T-012, T-014, T-015.
- **Description:** Update API, frontend, roadmap, README, AGENTS, docs index and specs index. Record the overview endpoint, routes, limits, shared-neighbor rule, isolated toggle, physics preset and current corpus counts. Run full backend/frontend checks and Compose validation. Push only with explicit authorization and record remote CI.
- **Done when:** docs match behavior; current-state docs reflect revision 6; full checks pass; remote CI passes; spec/tasks evidence and statuses are updated.
- **Verification:**
  ```bash
  cd backend
  uv sync
  uv run ruff check .
  uv run ruff format --check .
  uv run pytest

  cd ../frontend
  npm ci
  npm run generate:api
  npm run lint
  npm run typecheck
  npm run test
  npm run build

  cd ..
  docker compose config -q
  ```
- **Files:** `README.md`, `AGENTS.md`, `docs/03-data/api-v1.md`, `docs/01-architecture/frontend.md`, `docs/00-vision/roadmap.md`, `docs/README.md`, `specs/README.md`, `specs/011-graph-visualization/`.
- **Evidence:** 2026-11-11: updated the API, frontend, roadmap, README, AGENTS, docs and spec indexes with the overview endpoint, `/graph`, shared-neighbor rule, 1,000-node cap, isolated semantics, overview physics preset and current corpus counts (398 band-view nodes, 968 album-view nodes; 893/951 with isolated producers hidden in the albums view). Full checks passed: backend 220 unit + 325 integration tests, Ruff and format; frontend `npm ci`, OpenAPI generation, lint, typecheck, 76 tests and production build; `docker compose config -q`. Remote CI was not run because pushing requires explicit authorization; the manual ego 500-node/drag feel review remains pending.

## 3. Coverage matrix

### Functional requirements

| Requirement | Tasks |
|---|---|
| FR-001 | T-002, T-014 |
| FR-002 | T-001, T-003, T-013 |
| FR-003 | T-001, T-002, T-005, T-014 |
| FR-004 | T-003, T-007, T-009, T-010, T-015 |
| FR-005 | T-003, T-007, T-015 |
| FR-006 | T-003, T-007, T-009, T-014 |
| FR-007 | T-001, T-004, T-010, T-013, T-015 |
| FR-008 | T-002, T-004, T-005, T-014 |
| FR-009 | T-004, T-014 |
| FR-010 | T-006, T-014 |
| FR-011 | T-002, T-005, T-009, T-014 |
| FR-012 | T-003, T-006, T-015 |
| FR-013 | T-003, T-007, T-015 |
| FR-014 | T-007, T-012, T-016 |
| FR-015 | T-007, T-008, T-009, T-010, T-015, T-016 |
| FR-016 | T-011, T-012 |
| FR-017 | T-014 |
| FR-018 | T-011, T-013 |
| FR-019 | T-011, T-014 |
| FR-020 | T-011, T-014 |
| FR-021 | T-014 |
| FR-022 | T-012, T-015, T-016 |

### Non-functional requirements

| Requirement | Tasks |
|---|---|
| NFR-001 | T-002, T-003, T-005, T-008, T-009, T-010, T-015 |
| NFR-002 | T-003, T-006, T-015 |
| NFR-003 | T-006, T-010, T-014 |
| NFR-004 | T-004, T-011, T-015 |
| NFR-005 | T-007, T-012, T-016 |
| NFR-006 | T-001, T-007, T-013, T-014 |
| NFR-007 | T-003, T-006, T-009, T-015 |
| NFR-008 | T-004, T-005, T-008, T-014 |
| NFR-009 | T-015 |
| NFR-010 | T-011, T-012 |

## 4. Validation evidence

| Criterion | Result | Evidence |
|---|---|---|
| AC-001 | Passed | Route/link tests |
| AC-002 | Passed | Adapter tests |
| AC-003 | Passed | Limit/truncation tests |
| AC-004 | Passed | Physics config tests and headless browser smoke |
| AC-005 | Partial | Headless drag kept the page stable; manual neighbor-response review pending |
| AC-006 | Passed | Control tests |
| AC-007 | Passed | Style/adapter tests |
| AC-008 | Passed | Filter tests |
| AC-009 | Passed | Detail tests |
| AC-010 | Passed | Fallback tests |
| AC-011 | Passed | State tests |
| AC-012 | Passed | Reduced-motion test |
| AC-013 | Passed | Visibility test |
| AC-014 | Pending manual | 500-node browser check |
| AC-015 | Passed | Scope inspection; no schema changes |
| AC-016 | Passed | 76 frontend tests, lint, typecheck and build |
| AC-017 | Passed | Docs review |
| AC-018 | Pending | Remote CI |
| AC-019 | Passed | Album label style test and headless browser |
| AC-020 | Passed | Layout config test and headless distance probe |
| AC-021 | Passed | API/page tests; headless bands view 398 nodes / 426 edges |
| AC-022 | Passed | API/page tests; headless albums view 968 nodes / 1,134 edges |
| AC-023 | Passed | Shared-node API and adapter tests; no producer–producer edges |
| AC-024 | Passed locally | Albums view hides 43 isolated producer nodes and leaves 893 nodes / 951 edges; bands-view isolated producers share band entities and remain visible as bands |
| AC-025 | Passed | Route/navigation tests and producer entry links |
| AC-026 | Passed | Overview details/accessibility tests; Motörhead details listed 32 producers |
| AC-027 | Passed | Limits, truncation, filter and count tests |
| AC-028 | Passed locally | Full backend/frontend checks and docs review |
| AC-029 | Passed locally | 968-node album overview stayed responsive in headless Chromium |

## 5. Notes

- Physics is presentation, not evidence.
- d3-force links resolve endpoints through `linkId: (node) => node.id`; omitting it throws `node not found` and can blank the React root.
- Layout errors must stay inside the canvas component and fall back to a frozen static layout.
- The global overview is bounded to 1,000 nodes / 2,000 edges; the ego graph remains 500 / 2,000.
- Shared band/album nodes are the only relationship encoding; no producer–producer edges.
- The current bands view has 398 unique nodes / 426 edges; the albums view has 968 nodes / 1,134 simple edges. Both fit the cap without truncation.
- Isolated producer nodes are visible by default. The albums view hides them client-side (968 → 893 nodes, 1,134 → 951 edges). In the bands view the 43 isolated producer entities are the same shared band nodes, so they remain visible as bands rather than deleting documented band connections.
- The overview uses infinite physics with a compact preset: `manyBodyStrength=-45`, `linkDistance=42–90`, collision 8/7/10 by type, `collideStrength=0.6`, `alphaDecay=0.035`, `velocityDecay=0.55`; the initial view fits immediately and again after 1.2 s.
- Overview labels are decluttered by zoom: bands always visible, producers/albums at 12 px, selected and search-matched labels always visible.
- The only API change is the additive read-only overview endpoint; no schema migration or writes.
- Manual physics/performance checks are required; jsdom cannot validate the feel.
- Do not mark a task complete until its verification is executed.
