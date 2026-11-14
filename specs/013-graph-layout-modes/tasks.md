# Tasks — SPEC-013 Graph overview layout modes

- **Status:** Revisions 1–2 completed; revision 3 deferred; revision 4 plan approved, tasks in review
- **Spec:** [spec.md](spec.md)
- **Plan:** [plan.md](plan.md)

## 1. Execution order

```text
T-001 ─► T-002 ─► T-003 ─► T-004 ─► T-005
                                      │
                                      ▼
                          T-006 ─► T-007 ─► T-008 ─► T-009 ─► T-010
```

T-001 implements and tests the NetworkX layout functions. T-002 adds the API contract. T-003 adds the frontend types, adapter and static graph path. T-004 adds the selector and URL/query state. T-005 closes browser verification, performance and documentation.

T-006–T-010 implement revision 4 only: the approved fCoSE dependency, the force engine options module, the engine lifecycle, the selector/URL state, tests and headless verification. Revision 4 does not depend on revision 3. Coreness/radial layouts and orthogonal edge routing are separate follow-ups in SPEC-017 and SPEC-018 and are not part of these tasks.

## 2. Tasks

### T-001 — Implement NetworkX layout functions

- **Status:** Completed (2026-11-12).
- **Requirements:** FR-002, FR-003, FR-008, NFR-001, NFR-002, AC-002, AC-003, AC-007, AC-008.
- **Dependencies:** none.
- **Description:** Add `backend/src/hmde/services/graph_layouts.py` with pure functions for bipartite and community layouts. Bipartite uses `nx.bipartite_layout` with producers as the top node set and a deterministic two-column fallback for disconnected graphs. Community reuses the E7 Louvain community map, assigns bands/albums to the majority producer community, builds a contracted community graph, positions centers with seeded `spring_layout`, and places producers on an inner ring and targets on an outer ring. Normalize both outputs to a 1000×1000 box and return coordinates keyed by entity UUID.
- **Done when:** every node receives finite coordinates; producer x < target x in bipartite mode; community targets use the majority community; unassigned nodes are handled; repeated calls produce identical coordinates; disconnected/single-community cases do not fail.
- **Verification:**
  ```bash
  cd backend
  uv run ruff check .
  uv run ruff format --check .
  uv run pytest tests/unit/test_graph_layouts.py
  ```
- **Files:** `backend/src/hmde/services/graph_layouts.py`, `backend/tests/unit/test_graph_layouts.py`.
- **Evidence:** 2026-11-12: added deterministic NetworkX bipartite and community layout functions. Bipartite uses `nx.bipartite_layout` and deterministic row ordering; community reuses producer community keys, assigns targets by majority, places community centers with seeded `spring_layout` or a deterministic grid, and rings members around centers. Outputs are normalized to 1000×1000. Five unit tests cover ordering, isolated/disconnected nodes, majority assignment, unassigned nodes, single-community/no-edge cases and determinism. Ruff/format and tests passed.

### T-002 — Add layout API contract and service integration

- **Status:** Completed (2026-11-12).
- **Requirements:** FR-004, FR-008, NFR-002, NFR-003, AC-004, AC-007.
- **Dependencies:** T-001.
- **Description:** Add `ProducerOverviewGraphLayoutNode` and `ProducerOverviewGraphLayout` schemas and an optional `layout` field on the overview response. Add `layout=bipartite|community` validation to the route and pass the selected graph/community data to the layout functions after filtering and caps. Catch layout errors and return the graph without a layout. Regenerate OpenAPI and add integration tests for both modes, absent layout, failure fallback and schema presence.
- **Done when:** `layout` is optional and additive; both modes return coordinates for every node; invalid values return 422; a layout error still returns a usable graph; OpenAPI includes the optional layout block.
- **Verification:**
  ```bash
  cd backend
  uv run ruff check .
  uv run ruff format --check .
  uv run --env-file ../.env pytest
  uv run --env-file ../.env python -m hmde.openapi --output ../openapi.json
  ```
- **Files:** `backend/src/hmde/schemas/api.py`, `backend/src/hmde/services/producers.py`, `backend/src/hmde/api/routes/graph.py`, `backend/tests/integration/test_api_producer_overview_graph.py`, `backend/tests/unit/test_openapi.py`, `openapi.json`.
- **Evidence:** 2026-11-12: added optional `layout=bipartite|community` and optional `layout` coordinates to the overview response. Layout runs after filtering/caps, returns every selected node, and is omitted on failure. Integration tests cover absent layout, both algorithms, determinism, invalid values and monkeypatched failure fallback; OpenAPI includes both layout schemas. 9 integration endpoint tests and 225 backend unit tests passed; Ruff/format passed; OpenAPI regenerated.

### T-003 — Add frontend layout types, adapter and static graph path

- **Status:** Completed (2026-11-12).
- **Requirements:** FR-005, FR-006, FR-008, NFR-004, AC-005, AC-006, AC-007.
- **Dependencies:** T-002.
- **Description:** Regenerate TypeScript types, extend `ProducerOverviewGraphOptions` and `getProducerOverviewGraph` with the optional layout, and extend `AdaptedOverviewGraph` with validated layout coordinates. Attach positions to Cytoscape node elements when present. In `ProducerGraph`, apply a fitted static preset when the adapted graph has a layout, skip d3-force, disable Freeze/Resume/Reheat, show `Static layout`, and keep selection, details, search, table and ResizeObserver behavior. Keep the current Force path when there is no layout.
- **Done when:** valid coordinates are mapped to nodes; missing/duplicate/non-finite coordinates are ignored; static mode does not start physics and fits the graph; Force remains unchanged; existing graph tests pass.
- **Verification:**
  ```bash
  cd frontend
  npm run generate:api
  npm run lint
  npm run typecheck
  npm run test
  ```
- **Files:** `frontend/src/api/producerGraph.ts`, `frontend/src/api/schema.d.ts` (generated), `frontend/src/graph/adapter.ts`, `frontend/src/graph/adapter.test.ts`, `frontend/src/components/ProducerGraph.tsx`, `frontend/src/components/ProducerGraph.test.tsx`.
- **Evidence:** 2026-11-12: added layout types/client option, complete-coordinate validation, node position elements, and a static preset path that fits the graph, skips d3-force, disables physics controls and shows `Static layout`. Force remains unchanged. Adapter and component tests cover invalid layouts, positioning, static status and disabled controls. Focused tests passed.

### T-004 — Add layout selector, URL state and fallback notice

- **Status:** Completed (2026-11-12).
- **Requirements:** FR-001, FR-005, FR-006, FR-007, FR-009, NFR-004, AC-001, AC-005, AC-006, AC-009, AC-010.
- **Dependencies:** T-003.
- **Description:** Add `layout` to the overview URL/query state and a `Force / Bipartite / Community` selector in `ProducerOverviewControls`. Send `layout` only for the two static modes, include it in the query key, and show a non-blocking fallback notice when a requested layout has no valid coordinates. Keep the ego graph untouched. Add page and control tests for URL updates, API parameters and static/Force transitions.
- **Done when:** the selector has three options with Force default; Bipartite/Community send the layout parameter; Force omits it; static mode shows the fitted layout and disabled physics controls; an invalid/missing layout falls back to Force with a notice; the ego route and client are unchanged.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  npm run build
  ```
- **Files:** `frontend/src/components/ProducerOverviewControls.tsx`, `frontend/src/pages/ProducerOverviewPage.tsx`, `frontend/src/pages/ProducerOverviewPage.test.tsx`, `frontend/src/api/apiClients.test.ts`.
- **Evidence:** 2026-11-12: added the Force/Bipartite/Community selector, URL parsing/serialization, layout in the query key, layout only for static modes, static-mode rendering and a missing-coordinate fallback notice. Page and API client tests cover the selector, query parameter, static controls and fallback. Focused tests passed (35 tests across the touched suites).

### T-005 — Verify layouts in a browser and close documentation

- **Status:** Completed locally (2026-11-12); remote CI pending explicit authorization.
- **Requirements:** NFR-002, NFR-004, AC-009, AC-011, AC-012.
- **Dependencies:** T-004.
- **Description:** Run headless Chromium checks for Force, Bipartite and Community at 1440 and 1920 px; verify static status, disabled physics controls, fitted layouts, distinct positions, 398/968-node usability, panel/rail resizing and no console errors. Run full backend/frontend checks. Update the frontend/roadmap/README/AGENTS docs, SPEC-013 evidence and the SDD index when implementation is complete.
- **Done when:** browser probes and commands pass; layout times and screenshots/probes are recorded; docs and spec status reflect the result.
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
  Plus headless Chromium layout and performance probes.
- **Files:** `README.md`, `AGENTS.md`, `docs/01-architecture/frontend.md`, `docs/03-data/api-v1.md`, `docs/00-vision/roadmap.md`, `docs/README.md`, `specs/README.md`, `specs/013-graph-layout-modes/`.
- **Evidence:** 2026-11-12: headless Chromium confirmed Force, Bipartite and Community modes at 1440 px and the 1920 px resize. Bipartite produced producer x=80 and album x=920 with static controls disabled; Community produced distinct clusters; Force restored physics. The 968-node albums layout fit the canvas. Request times were ~0.16 s (Bipartite) and ~0.25 s (Community). Full checks passed: backend 225 unit + 332 full-suite tests, Ruff/format; frontend lint, typecheck, 98 tests and build; Compose config; OpenAPI drift unchanged. Remote CI not run because pushing requires explicit authorization.

### T-006 — Add approved force dependencies and option builders

- **Status:** Pending.
- **Requirements:** FR-011, FR-012, FR-013, NFR-003, NFR-005, AC-016, AC-017.
- **Dependencies:** Owner approval for `cytoscape-fcose` (given 2026-11-13); T-005 baseline.
- **Description:** Add the approved `cytoscape-fcose` runtime dependency and `@types/cytoscape-fcose` development dependency. Create `frontend/src/graph/forceLayouts.ts` with the `ForceEngine` union, default/invalid parsing, and option builders for d3-force, CoSE and fCoSE. Move the current d3-force overview option logic into the builder without changing its values; the ego graph path keeps its current behavior. CoSE uses the built-in layout. fCoSE uses `quality: 'proof'` when `randomize` is false and keeps `packComponents: false` for the first implementation. Add focused unit tests for defaults, invalid values and option flags.
- **Done when:** dependencies are locked; the new module exports typed builders; d3-force options match the current behavior; CoSE/fCoSE names and finite/infinite flags are correct; no API, backend or schema file changes; lint, typecheck and focused tests pass.
- **Verification:**
  ```bash
  cd frontend
  npm install cytoscape-fcose@2.2.0
  npm install -D @types/cytoscape-fcose@2.2.5
  npm run lint
  npm run typecheck
  npm run test
  ```
- **Files:** `frontend/package.json`, `frontend/package-lock.json`, `frontend/src/graph/forceLayouts.ts`, `frontend/src/graph/forceLayouts.test.ts`.
- **Evidence:** Pending.

### T-007 — Integrate force engine lifecycle in ProducerGraph

- **Status:** Pending.
- **Requirements:** FR-011, FR-012, FR-013, FR-014, FR-015, NFR-004, NFR-005, AC-015, AC-016, AC-017, AC-018.
- **Dependencies:** T-006.
- **Description:** Register `cytoscape-fcose` once at graph setup. Accept the selected engine through `ProducerGraph` props and start the matching layout: the current infinite d3-force, built-in CoSE, or fCoSE. Stop the previous layout before starting a new engine. Handle `layoutstop` for finite layouts, update the status text, fit the completed result, preserve current Freeze/Resume/Reheat semantics for d3-force, and define Resume/Reheat as re-runs for CoSE/fCoSE. Use `animate: false` under reduced motion. Catch engine failures, fall back to d3-force and then the existing static `breadthfirst` fallback. Stop layouts on unmount and ignore late callbacks.
- **Done when:** each engine can be selected and started; switching engines stops the previous simulation/layout; finite completion does not look like a hung infinite simulation; reduced motion does not animate; fallback never leaves a blank canvas; selection/details/table/resize remain usable.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  ```
  Plus a focused headless check of Force engine switching.
- **Files:** `frontend/src/components/ProducerGraph.tsx`, `frontend/src/components/ProducerGraph.test.tsx`, `frontend/src/graph/forceLayouts.ts`.
- **Evidence:** Pending.

### T-008 — Add the Force engine selector and URL state

- **Status:** Pending.
- **Requirements:** FR-010, FR-014, NFR-004, AC-013, AC-014, AC-019.
- **Dependencies:** T-007.
- **Description:** Add an accessible three-button Force engine group below the Layout selector in `ProducerOverviewControls`, visible with the selected state and disabled outside Force. Add `engine=d3-force|cose|fcose` to the overview URL state, omit the default, remove it for static layouts and retain the last engine in client state. Pass the engine to `ProducerGraph`. Keep `engine` out of the overview query key and API request. Add CSS consistent with the existing workspace and replacement history for engine-only changes.
- **Done when:** the group appears below Layout; `d3-force` is the default; the group is disabled for Bipartite/Community; URL state round-trips; changing the engine never refetches the overview; the ego graph does not receive the control; tests pass.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  ```
- **Files:** `frontend/src/components/ProducerOverviewControls.tsx`, `frontend/src/components/ProducerOverviewControls.test.tsx`, `frontend/src/pages/ProducerOverviewPage.tsx`, `frontend/src/pages/ProducerOverviewPage.test.tsx`, `frontend/src/index.css`.
- **Evidence:** Pending.

### T-009 — Complete force engine test coverage and scope checks

- **Status:** Pending.
- **Requirements:** AC-013, AC-014, AC-015, AC-016, AC-017, AC-018, AC-019.
- **Dependencies:** T-008.
- **Description:** Add or adjust unit, component and page tests for engine parsing, default omission, URL persistence, no overview refetch, static-mode disabling, fCoSE registration, finite/infinite lifecycle, reduced motion, fallback chains and ego-graph isolation. Verify the accessible name and `aria-pressed` state of the button group.
- **Done when:** the new behavior is covered by focused tests; existing Force/Bipartite/Community tests still pass; no test relies on network access or a live backend.
- **Verification:**
  ```bash
  cd frontend
  npm run test
  ```
- **Files:** `frontend/src/graph/forceLayouts.test.ts`, `frontend/src/components/ProducerGraph.test.tsx`, `frontend/src/components/ProducerOverviewControls.test.tsx`, `frontend/src/pages/ProducerOverviewPage.test.tsx`.
- **Evidence:** Pending.

### T-010 — Verify the force engines in a browser and update documentation

- **Status:** Pending.
- **Requirements:** NFR-005, AC-020.
- **Dependencies:** T-009.
- **Description:** Run headless Chromium checks for d3-force, CoSE and fCoSE on the 398-node bands view and the 968-node albums view. Record completion time, canvas usability, fallback behavior, reduced-motion behavior and console errors. Run the full frontend checks and, if applicable, backend checks. Update the spec/tasks evidence, `specs/README.md`, `AGENTS.md` and the relevant frontend/API docs only after implementation is complete.
- **Done when:** both corpus sizes are usable with all three engines; CoSE/fCoSE complete without a blank canvas; d3-force remains the default; lint, typecheck, tests and build pass; documentation reflects the verified state.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  npm run build
  ```
  Plus a headless Chromium probe for all three engines at 398/968 nodes.
- **Files:** `specs/013-graph-layout-modes/`, `specs/README.md`, `AGENTS.md`, `docs/01-architecture/frontend.md`, `docs/03-data/api-v1.md` (only if the implementation changes documented behavior).
- **Evidence:** Pending; remote CI requires explicit authorization.

## 3. Coverage matrix

### Functional requirements

| Requirement | Tasks |
|---|---|
| FR-001 | T-004 |
| FR-002 | T-001, T-002 |
| FR-003 | T-001, T-002 |
| FR-004 | T-002 |
| FR-005 | T-003, T-004 |
| FR-006 | T-003, T-004 |
| FR-007 | T-004 |
| FR-008 | T-001, T-002, T-003 |
| FR-009 | T-004, T-005 |
| FR-010 | T-008, T-009 |
| FR-011 | T-006, T-007 |
| FR-012 | T-006, T-007 |
| FR-013 | T-006, T-007 |
| FR-014 | T-007, T-008, T-009 |
| FR-015 | T-007, T-009 |

### Non-functional requirements

| Requirement | Tasks |
|---|---|
| NFR-001 | T-001 |
| NFR-002 | T-001, T-002, T-005 |
| NFR-003 | T-002, T-005, T-006 |
| NFR-004 | T-003, T-004, T-005, T-008, T-009 |
| NFR-005 | T-006, T-007, T-010 |

## 4. Validation evidence

| Criterion | Result | Evidence |
|---|---|---|
| AC-001 | Passed | Page/URL tests; selector and layout query |
| AC-002 | Passed | Backend bipartite test; producer x=80 / album x=920 |
| AC-003 | Passed | Backend community majority/unassigned test |
| AC-004 | Passed | Integration/OpenAPI tests |
| AC-005 | Passed | Component/headless static controls |
| AC-006 | Passed | Force transition/component tests; headless return to physics |
| AC-007 | Passed | Disconnected, missing-layout and layout-error fallbacks |
| AC-008 | Passed | Determinism tests |
| AC-009 | Passed | 968-node headless fit; API layout timings |
| AC-010 | Passed | Scope inspection; ego tests unchanged |
| AC-011 | Passed | Details/table/resize remain available; headless static mode |
| AC-012 | Passed | Full backend/frontend checks and OpenAPI generation |
| AC-013 | Pending | Revision 4: control/component tests |
| AC-014 | Pending | Revision 4: URL and no-refetch tests |
| AC-015 | Pending | Revision 4: default d3-force tests |
| AC-016 | Pending | Revision 4: CoSE component test/build inspection |
| AC-017 | Pending | Revision 4: fCoSE registration/typecheck/build tests |
| AC-018 | Pending | Revision 4: lifecycle/reduced-motion/fallback tests |
| AC-019 | Pending | Revision 4: ego/static scope tests |
| AC-020 | Pending | Revision 4: full checks and 398/968-node headless probe |

## 5. Revision 3 — deferred

No revision 3 tasks are defined. T-001–T-005 remain the completed baseline. Revision 3 remains deferred and must not be mixed into revision 4.

## 6. Revision 4 — plan approved, tasks in review

The revision 4 plan was approved on 2026-11-13. T-006–T-010 are defined but not implemented; they start only after these tasks are approved. Revision 4 is frontend-only; it does not change the API, backend, database or ego graph.

## 7. Notes

- NetworkX has `bipartite_layout`; it has no community layout, so Community is a documented custom cluster layout on top of E7 Louvain.
- Static layouts are not force simulations; Force remains the interactive mode.
- Revision 3 was reverted and is deferred; lanes, community spacing, labels, auto-freeze, Fit and edge separation are not active.
- Client-only role/search/isolated filters do not recompute server coordinates.
- No DB migration is required. Revisions 1–2 add no dependency; revision 4 adds the approved frontend `cytoscape-fcose` and `@types/cytoscape-fcose` dependencies only.
- Revision 4 engine switching is client-side and must not refetch the overview.
- Coreness and Rings are specified in [SPEC-017](../017-graph-coreness-radial-layouts/tasks.md), not here.
- Orthogonal edge routing is specified in [SPEC-018](../018-orthogonal-edge-routing/tasks.md), not here.
- Do not mark a task complete until its verification has been executed.
