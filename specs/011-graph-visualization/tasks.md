# Tasks — SPEC-011 Producer graph visualization and interaction

- **Status:** Implemented locally; headless physics, spacing and label checks passed; manual interaction and remote CI pending
- **Spec:** [spec.md](spec.md)
- **Plan:** [plan.md](plan.md)

## 1. Execution order

```text
T-001 ─► T-002 ─┬─► T-003 ─┬─► T-004 ─┐
                │          └─► T-005 ─┼─► T-006 ─► T-007 ─► T-008 ─► T-009 ─► T-010
                └─► T-004 ────────────┘
```

T-001 establishes the typed client and adapter. T-002 adds the route/page shell. T-003 adds the physics canvas. T-004 adds visual mapping, legend, details and filter controls. T-005 hardens states and truncation. T-006 completes accessibility. T-007 proves physics lifecycle and scope with tests. T-008 closes documentation, manual checklist, full checks and CI. T-009 fixes d3-force node identity and guards layout startup failures. T-010 tunes neighbor spacing and makes album titles permanently visible.

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
- **Description:** Add unit/component tests with mocked Cytoscape and d3-force for layout registration, infinite physics options, drag handling, freeze/resume/reheat, visibility pause and cleanup. Update the E9 scope guard so graph/`cytoscape-d3-force` is allowed in E10 but API/schema/Tailwind/Plotly/new-renderer changes remain rejected.
- **Done when:** physics lifecycle and options are asserted; scope guards reflect E10; no API/schema changes; tests pass.
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

## 3. Coverage matrix

### Functional requirements

| Requirement | Tasks |
|---|---|
| FR-001 | T-002 |
| FR-002 | T-001, T-003 |
| FR-003 | T-001, T-002, T-005 |
| FR-004 | T-003, T-007, T-009, T-010 |
| FR-005 | T-003, T-007 |
| FR-006 | T-003, T-007, T-009 |
| FR-007 | T-001, T-004, T-010 |
| FR-008 | T-002, T-004, T-005 |
| FR-009 | T-004 |
| FR-010 | T-006 |
| FR-011 | T-002, T-005, T-009 |
| FR-012 | T-003, T-006 |
| FR-013 | T-003, T-007 |
| FR-014 | T-007 |
| FR-015 | T-007, T-008, T-009, T-010 |

### Non-functional requirements

| Requirement | Tasks |
|---|---|
| NFR-001 | T-002, T-003, T-005, T-008, T-009, T-010 |
| NFR-002 | T-003, T-006 |
| NFR-003 | T-006, T-010 |
| NFR-004 | T-004 |
| NFR-005 | T-007 |
| NFR-006 | T-001, T-007 |
| NFR-007 | T-003, T-006, T-009 |
| NFR-008 | T-004, T-005, T-008 |

## 4. Validation evidence

| Criterion | Result | Evidence |
|---|---|---|
| AC-001 | Passed | Route/link tests |
| AC-002 | Passed | Adapter tests |
| AC-003 | Passed | Limit/truncation tests |
| AC-004 | Passed | Physics config tests and headless browser smoke |
| AC-005 | Pending manual | Drag/neighbor physics check |
| AC-006 | Passed | Control tests |
| AC-007 | Passed | Style/adapter tests |
| AC-008 | Passed | Filter tests |
| AC-009 | Passed | Detail tests |
| AC-010 | Passed | Fallback tests |
| AC-011 | Passed | State tests |
| AC-012 | Passed | Reduced-motion test |
| AC-013 | Passed | Visibility test |
| AC-014 | Pending manual | 500-node browser check |
| AC-015 | Passed | Scope inspection |
| AC-016 | Passed | 62 frontend tests, lint, typecheck and build |
| AC-017 | Passed | Docs review |
| AC-018 | Pending | Remote CI |
| AC-019 | Passed | Album label style test and headless browser |
| AC-020 | Passed | Layout config test and headless distance probe |

## 5. Notes

- Physics is presentation, not evidence.
- d3-force links resolve endpoints through `linkId: (node) => node.id`; omitting it throws `node not found` and can blank the React root.
- Layout errors must stay inside the canvas component and fall back to a frozen static layout.
- E10 v1 uses E8 limits and client-side filters.
- No full graph, API changes or new renderer.
- Manual physics/performance checks are required; jsdom cannot validate the feel.
- Do not mark a task complete until its verification is executed.
