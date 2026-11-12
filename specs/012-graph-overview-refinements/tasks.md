# Tasks — SPEC-012 Graph overview workspace refinements

- **Status:** Implemented locally; T-001–T-010 completed; remote CI pending
- **Spec:** [spec.md](spec.md)
- **Plan:** [plan.md](plan.md)

## 1. Execution order

```text
T-001 ─┐
       ├─► T-004 ─┐
T-002 ─┴─► T-003 ─┴─► T-005 ─► T-006 ─► T-007 ─► T-008 ─► T-009 ─► T-010
```

T-001 and T-002 are independent adapter/test tasks. T-003 and T-004 depend on T-002. T-005 integrates the page. T-006 closes the revision-2 documentation. T-007–T-010 deliver revision 3: navigation rail, wide shell, collapsible panels and canvas resize.

## 2. Tasks

### T-001 — Add the dynamic overview year scale

- **Status:** Completed (2026-11-11).
- **Requirements:** FR-006, FR-007, AC-005, AC-006.
- **Dependencies:** none.
- **Description:** Add a `YearRange` type and a light-to-dark overview color helper. Compute the range from visible album nodes after client filters and the isolated toggle. Keep the ego graph on its existing scale. Extend `GraphLegend` with an optional dynamic range; hide the year item when the overview has no albums.
- **Done when:** the oldest visible album uses the lightest tone, the newest the darkest, unknown years stay grey, a single year uses a documented midpoint, and the legend shows the real minimum and maximum.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  ```
- **Files:** `frontend/src/graph/adapter.ts`, `frontend/src/graph/adapter.test.ts`, `frontend/src/components/GraphLegend.tsx`, `frontend/src/components/GraphLegend.test.tsx`, `frontend/src/graph/styles.ts`.
- **Evidence:** 2026-11-11: added `YearRange`, `overviewYearColor`, `OVERVIEW_YEAR_GRADIENT` and `yearRange` on `AdaptedOverviewGraph`. The overview maps visible album years from `#bcd8c2` (oldest) to `#123c38` (newest), uses a documented midpoint for a single year, keeps grey for unknown years and hides the legend year item when no albums are visible. The ego graph keeps its existing viridis scale. Added adapter and legend tests for dynamic ranges, single-year fallback and missing years. `npm run lint`, `npm run typecheck` and the focused tests passed (13 tests).

### T-002 — Add index and full-incident selectors to the overview adapter

- **Status:** Completed (2026-11-11).
- **Requirements:** FR-002, FR-003, FR-009, BR-001, BR-002, BR-004.
- **Dependencies:** none.
- **Description:** Add selectors for the producer index, band index and all incident producers by target node. Producer rows use loaded nodes with the `producer` role and `attributes.album_count`; band rows use the existing band list fields `id`, `name` and `album_count`. Sort both descending by count, then label/name. Build `allIncidentProducersById` from every overview edge, before role/search/isolated filtering.
- **Done when:** producer and band rows are deterministic and sorted; band-role producers appear in the producer index; album details can list producers hidden by filters.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  ```
- **Files:** `frontend/src/graph/adapter.ts`, `frontend/src/graph/adapter.test.ts`.
- **Evidence:** 2026-11-11: added `OverviewIndexRow`, `buildProducerIndex`, `buildBandIndex` and sorted row construction. Producer rows include band-role producers and use `album_count`; band rows use the band-list `album_count`. Added `allIncidentProducersById`, computed from every overview edge before client filters, alongside the filtered incident map. Tests cover ordering, band-role producers, unfiltered album producers and the retained filtered map. `npm run lint`, `npm run typecheck` and 11 focused adapter tests passed.

### T-003 — Add the collapsible left index and workspace sizing

- **Status:** Completed (2026-11-11).
- **Requirements:** FR-001, FR-002, FR-003, FR-004, FR-005, NFR-001, NFR-002, NFR-004, AC-001–AC-004.
- **Dependencies:** T-002.
- **Description:** Create `OverviewIndex.tsx` with two native `<details>` sections for producers and bands. Add the band list query with the active decade/subgenre filters and `limit=200`. Add the three-region workspace grid, equal-height side panels, internal scroll and responsive stacking CSS. Keep the index read-only, with entity links and counts.
- **Done when:** both lists render, are sorted and collapsible, the summaries show entry counts, the panels match the graph workspace height on wide screens, and each panel scrolls independently without growing the page.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  ```
- **Files:** `frontend/src/components/OverviewIndex.tsx`, `frontend/src/components/OverviewIndex.test.tsx`, `frontend/src/pages/ProducerOverviewPage.tsx`, `frontend/src/index.css`.
- **Evidence:** 2026-11-11: added the native collapsible producer and band index with counts, entity links, loading/error/empty states and a retry action. Both sections start collapsed so either list is reachable without scrolling past the other. The page now fetches `GET /api/v1/bands` with the active decade/subgenre filters and `limit=200`, builds sorted index rows, and composes a three-column workspace. The workspace owns a shared height; the graph column flexes its canvas and both side panels use `min-height: 0` with independent vertical scroll. Responsive stacking and bounded panel heights were added below 1280px. Tests cover counts, links, ordering, collapse/expand, loading and retry. Frontend lint, typecheck and all 84 tests passed.

### T-004 — Extend the right detail panel

- **Status:** Completed (2026-11-11).
- **Requirements:** FR-008, FR-009, FR-010, FR-011, FR-012, NFR-001, NFR-002, AC-007–AC-010.
- **Dependencies:** T-002.
- **Description:** Extend `ProducerOverviewDetails` so it renders related data by node type. For producers, fetch both existing ego graphs in parallel and list bands and albums with truncation disclosure. For bands, fetch the existing band detail and list albums plus deduplicated producer/co-producer credits. For albums, show band, year and every incident producer from the unfiltered overview edges. Add panel-local loading, empty, error and retry states. Keep the edge details.
- **Done when:** each node type shows the requested information without leaving the page; a failing related query leaves the canvas and table usable; a filtered-out selection clears or explains the panel.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  ```
- **Files:** `frontend/src/components/ProducerOverviewDetails.tsx`, `frontend/src/components/ProducerOverviewDetails.test.tsx`, `frontend/src/pages/ProducerOverviewPage.test.tsx`.
- **Evidence:** 2026-11-11: extended the panel by node type. Producers fetch both existing ego graphs in one cached query and list bands and albums with truncation disclosure; bands fetch the existing band detail endpoint and list albums plus deduplicated producer/co-producer credits; albums show band, year and all incident producers from the unfiltered overview edges. Added panel-local loading/error/retry states, entity links and the existing edge detail. Page now passes unfiltered incident producers to the panel. Added four detail tests and updated the page tests; frontend lint, typecheck and all 88 tests passed.

### T-005 — Integrate the workspace and selection lifecycle

- **Status:** Completed (2026-11-11).
- **Requirements:** FR-001, FR-005, FR-012, NFR-001, NFR-004, AC-004, AC-011, AC-013.
- **Dependencies:** T-001, T-003, T-004.
- **Description:** Compose the left index, center graph and right panel in `ProducerOverviewPage`. Pass the selected node and unfiltered incident producers to the panel. Keep the existing URL state and clear selection when server or display filters change. Ensure the graph column owns the workspace height and the side panels stretch and scroll. Verify the responsive stack and existing empty/error/truncation states.
- **Done when:** the three regions compose correctly at desktop and narrow widths; selection updates the panel; panel scrolling does not move or resize the canvas; existing graph controls and tests still pass.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  npm run build
  ```
- **Files:** `frontend/src/pages/ProducerOverviewPage.tsx`, `frontend/src/pages/ProducerOverviewPage.test.tsx`, `frontend/src/index.css`, `frontend/src/graph/adapter.ts`.
- **Evidence:** 2026-11-11: composed the left index, center graph and right details inside the equal-height workspace; the graph column owns the canvas height and both side panels scroll independently. The page now passes unfiltered incident producers to the details panel and shows a clear "selected entity is not in the current view" state when a URL selection cannot be resolved. Added page tests for the band query filters, missing selections and the dynamic year legend. Frontend lint, typecheck, 90 tests and build passed.

### T-006 — Verify in a browser and close documentation

- **Status:** Completed locally (2026-11-11); remote CI pending explicit authorization.
- **Requirements:** FR-005, FR-006, NFR-003, NFR-004, AC-004, AC-011, AC-012, AC-013.
- **Dependencies:** T-005.
- **Description:** Run headless Chromium checks at desktop and narrow viewports. Verify equal panel heights, independent scrolling, the dynamic year range after filters, producer/album/band detail flows, and no console errors. Run the full frontend and backend regression checks. Update the frontend docs, roadmap, README, AGENTS current state and SPEC-012 evidence if implementation proceeds to validation.
- **Done when:** browser checks and commands pass; screenshots/probes are recorded; documentation reflects the implemented workspace.
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
  Plus headless Chromium bounding-box and interaction probes.
- **Files:** `README.md`, `AGENTS.md`, `docs/01-architecture/frontend.md`, `docs/00-vision/roadmap.md`, `docs/README.md`, `specs/README.md`, `specs/012-graph-overview-refinements/`.
- **Evidence:** 2026-11-11: headless Chromium confirmed equal 858 px heights for the index, graph and detail columns; the index scrolled 14,700 px of content inside an 856 px panel; the producer index showed 384 sorted rows and the band index 57; the 900 px and 1200 px viewports stacked without horizontal overflow. The overview year scale used `#bcd8c2` for 1968 and `#123c38` for 2026 with a dynamic legend. Charlie Bauerfeind showed 4 bands and 20 albums, Master of the Rings showed Helloween/1994/3 producers, and Motörhead showed 23 albums and 33 producers; the detail column scrolled independently. Full checks: frontend lint, typecheck, 90 tests, production build; backend Ruff/format and 220 unit tests; `docker compose config -q`; OpenAPI drift unchanged. Updated frontend docs, roadmap, README, AGENTS and the SDD indexes. Remote CI was not run because pushing requires explicit authorization.


### T-007 — Collapse the navigation rail and widen the shell

- **Status:** Completed (2026-11-11).
- **Requirements:** FR-013, FR-014, NFR-005, AC-014, AC-015, AC-016.
- **Dependencies:** T-006.
- **Description:** Add a persisted rail-collapsed state to `AppShell`, a labelled toggle and a 3rem desktop strip with the `HMDE` monogram. Default to collapsed on `/graph` when no preference exists and expanded on other routes. Remove the shell `96rem` ceiling, reduce horizontal main padding, center reading pages within their existing width and leave `/graph` unbounded. Keep the mobile top-bar navigation unchanged.
- **Done when:** the rail collapses/expands with keyboard-accessible state, the preference persists, `/graph` starts collapsed without a stored preference, and the shell uses the viewport width without horizontal overflow.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  ```
- **Files:** `frontend/src/components/AppShell.tsx`, `frontend/src/components/AppShell.test.tsx`, `frontend/src/index.css`.
- **Evidence:** 2026-11-11: added a persisted 3rem rail with an accessible toggle and `HMDE` monogram, route-based default (`/graph` collapsed, other routes expanded) and a user preference that overrides the default. The shell no longer has the 96rem ceiling, main padding is `clamp(0.75rem, 1.5vw, 1.5rem)`, reading pages are centered and `/graph` is unbounded. Mobile keeps the existing top navigation. Tests cover collapse/expand, `aria-expanded`, the class, localStorage persistence and the `/graph` default. Frontend lint, typecheck and tests passed.

### T-008 — Make the overview panels collapsible and resize the canvas

- **Status:** Completed (2026-11-11).
- **Requirements:** FR-015, FR-016, NFR-005, AC-017, AC-018.
- **Dependencies:** T-007.
- **Description:** Add `Index` and `Details` toggles above the overview workspace, default both open, close their grid columns when toggled off, narrow the panel widths and gaps, and reopen Details when a node is selected. Add a `ResizeObserver` in `ProducerGraph` that calls `cy.resize()` when the graph column width changes without recreating Cytoscape or restarting physics.
- **Done when:** each panel toggles independently, the graph expands into closed columns, selecting a node reopens Details, and the canvas width follows the container after rail/panel changes.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  ```
- **Files:** `frontend/src/pages/ProducerOverviewPage.tsx`, `frontend/src/components/ProducerGraph.tsx`, `frontend/src/index.css`, tests.
- **Evidence:** 2026-11-11: added `Index`/`Details` toggle controls, conditional panel columns, narrower panel widths and 0.75rem gaps. Closing a panel gives its column to the graph; selecting a node reopens Details. Added a `ResizeObserver` that calls `cy.resize()` without recreating Cytoscape or restarting physics. Page and component tests pass.

### T-009 — Add regression coverage for the space-efficiency changes

- **Status:** Completed (2026-11-11).
- **Requirements:** AC-014–AC-018, NFR-001, NFR-005.
- **Dependencies:** T-007, T-008.
- **Description:** Add tests for rail collapse/expand, localStorage persistence and route defaults; overview panel toggles and details auto-open; and `ProducerGraph` resize observer behavior with a mocked `ResizeObserver`. Keep the existing suite green.
- **Done when:** the new behaviors are asserted and the full frontend suite passes.
- **Verification:**
  ```bash
  cd frontend
  npm run test
  ```
- **Files:** `frontend/src/components/AppShell.test.tsx`, `frontend/src/pages/ProducerOverviewPage.test.tsx`, `frontend/src/components/ProducerGraph.test.tsx`.
- **Evidence:** 2026-11-11: added tests for rail collapse/expand, persistence, `/graph` default, panel toggles independently hiding each region, and the resize observer calling `cy.resize()` and disconnecting on unmount. Full frontend suite: 94 tests passed; lint, typecheck and build passed.

### T-010 — Verify the wide layout and close revision 3

- **Status:** Completed locally (2026-11-11); remote CI pending explicit authorization.
- **Requirements:** FR-013–FR-016, NFR-005, AC-014–AC-018.
- **Dependencies:** T-009.
- **Description:** Run headless Chromium checks at 1440 and 1920 px for rail collapse, persistence, panel toggles, graph width and canvas resize; verify 900/1200 px remain overflow-free. Run the full frontend/backend checks and update SPEC-012 revision 3, the frontend/roadmap/README/AGENTS docs and the SDD index.
- **Done when:** the browser probes and commands pass, the width targets are recorded, and revision 3 is reflected in the spec and documentation.
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
  Plus headless Chromium width and interaction probes.
- **Files:** `README.md`, `AGENTS.md`, `docs/01-architecture/frontend.md`, `docs/00-vision/roadmap.md`, `docs/README.md`, `specs/README.md`, `specs/012-graph-overview-refinements/`.
- **Evidence:** 2026-11-11: headless Chromium at 1440 px showed `/bands` with a 272 px expanded rail and `/graph` with a 48 px collapsed rail; the graph was 876 px with both panels open, 1,144 px with Details closed and 1,348 px with both closed; the canvas matched the column after every toggle and selection reopened Details. The rail preference persisted across reloads. At 1920 px the shell used the full 1,920 px and the graph reached 1,352 px with both panels open; 900/1200 px stacked with no horizontal overflow. Full checks passed: frontend lint, typecheck, 94 tests and build; backend Ruff/format and 220 unit tests; `docker compose config -q`; OpenAPI drift unchanged. Documentation updated. Remote CI was not run because pushing requires explicit authorization.

## 3. Coverage matrix

### Functional requirements

| Requirement | Tasks |
|---|---|
| FR-001 | T-003, T-005 |
| FR-002 | T-002, T-003 |
| FR-003 | T-002, T-003 |
| FR-004 | T-003 |
| FR-005 | T-003, T-005, T-006 |
| FR-006 | T-001, T-005 |
| FR-007 | T-001, T-005 |
| FR-008 | T-004 |
| FR-009 | T-002, T-004 |
| FR-010 | T-004 |
| FR-011 | T-004, T-005 |
| FR-012 | T-004, T-005 |
| FR-013 | T-007 |
| FR-014 | T-007 |
| FR-015 | T-008 |
| FR-016 | T-008 |

### Non-functional requirements

| Requirement | Tasks |
|---|---|
| NFR-001 | T-003, T-004, T-005 |
| NFR-002 | T-003, T-004 |
| NFR-003 | T-005, T-006 |
| NFR-004 | T-003, T-005, T-006 |
| NFR-005 | T-007, T-008, T-009, T-010 |

## 4. Validation evidence

| Criterion | Result | Evidence |
|---|---|---|
| AC-001 | Passed | Index component/page tests; headless summaries 384 producers / 57 bands |
| AC-002 | Passed | Selector tests; headless counts descend from 20/17/17 and 25/23/23 |
| AC-003 | Passed | Collapsible list keyboard test |
| AC-004 | Passed | Headless equal 858 px heights and independent panel scroll |
| AC-005 | Passed | Adapter/legend tests; headless 1968 `#bcd8c2` to 2026 `#123c38` |
| AC-006 | Passed | Legend/page tests; headless `1968 to 2026` |
| AC-007 | Passed | Producer detail test; headless 4 bands / 20 albums |
| AC-008 | Passed | Album detail test; headless Helloween / 1994 / 3 producers |
| AC-009 | Passed | Band detail test; headless 23 albums / 33 producers |
| AC-010 | Passed | Detail state tests; panel-local loading/error/retry |
| AC-011 | Passed | Headless 900 px and 1200 px stacked without horizontal overflow |
| AC-012 | Passed | Diff/scope inspection; no backend, schema, migration or dependency changes |
| AC-013 | Passed | Frontend lint/typecheck/94 tests/build; backend Ruff/format/220 tests |
| AC-014 | Passed | AppShell tests; headless 272 px expanded / 48 px collapsed rail |
| AC-015 | Passed | localStorage and route-default tests; reload verification |
| AC-016 | Passed | Headless 1440/1920 width checks; no overflow |
| AC-017 | Passed | Page tests; headless panel widths 876/1,144/1,348 px and selection auto-open |
| AC-018 | Passed | ResizeObserver test; headless canvas width follows column |

## 5. Notes

- The panels are read-only navigation aids; selecting a node remains a canvas action.
- The index reflects the server-loaded overview and period filters, not client-only role/search/isolated filters.
- The ego graph year scale is intentionally unchanged.
- The lightest overview year tone must remain distinguishable from the `#dde2dc` canvas.
- No backend, API, schema, migration or dependency change belongs in this spec.
- Do not mark a task complete until its verification has been executed.
