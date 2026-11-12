# SPEC-012 — Graph overview workspace refinements

- **Status:** Implemented
- **Stage:** E10
- **Iteration:** MVP
- **Module:** `web`
- **Date:** 2026-11-11
- **Depends on:** SPEC-011 (implemented locally), SPEC-009, SPEC-010; existing read-only graph and entity endpoints
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0006](../../docs/01-architecture/adr/ADR-0006-read-only-api.md), [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)
- **Plan:** [plan.md](plan.md)
- **Tasks:** [tasks.md](tasks.md)
- **Conventions:** [Engineering conventions](../../docs/01-architecture/conventions.md)
- **Owner:** Cristian

## Revision history

| Revision | Date | Change |
|---|---|---|
| 1 | 2026-11-11 | Initial draft: producer and band index, panel-height contract, dynamic year scale and node detail panel |
| 2 | 2026-11-11 | T-001–T-006 implemented locally; equal-height scrollable panels, dynamic year scale, node detail panel and headless verification passed. Remote CI pending |
| 3 | 2026-11-11 | Space efficiency: collapsible navigation rail, wider global layout, collapsible index/detail panels and canvas resize |

## 1. Context and problem

SPEC-011 delivered the global producer overview at `/graph`: one canvas with producer nodes and shared band or album nodes, force physics, filters, an accessible table and selection details. The screen is usable, but three analysis tasks are still slower than they should be:

- Users cannot scan the producers or bands in the loaded network without reading the canvas or leaving the page.
- The album-year viridis scale is not self-explanatory: newer years are yellow and older years are purple, which is not obvious without checking the legend.
- Selecting a node exposes only a shallow summary. Users must leave the graph to see the bands and albums of a producer, the albums and producers of a band, or the band, year and producers of an album.

This spec refines the E10 overview workspace. It adds a left index, a right detail panel and a dynamic sequential year scale. It reuses the existing E8/E10 read-only endpoints and does not change the canonical data model or the API contract.

Revision 3 addresses the space cost of the new workspace: the application currently spends a large share of the viewport on the green rail, page padding and the two graph panels. The graph needs more horizontal room, the application should use the full viewport, and both the navigation rail and the graph panels should be collapsible without losing the features delivered in revisions 1–2.

## 2. Users and actors

- **Primary user:** a heavy-metal researcher exploring documented production relationships.
- **System actor:** the FastAPI read-only API and the persisted E7 analysis run.
- **Frontend actor:** React, TanStack Query, Cytoscape and the existing studio-ledger visual system.
- There are no authentication roles or write permissions in this iteration.

## 3. User stories and flows

### US-001 — Scan the loaded network from the left index

As a researcher, I want to see the producers and bands in the loaded network with their documented counts, so that I can orient myself before touching the graph.

**Expected flow:**

1. The user opens `/graph`.
2. The left side shows two collapsible lists: producers and bands.
3. Each summary states the number of entries.
4. Producers are ordered by documented album count, descending.
5. Bands are ordered by documented album count, descending.
6. Expanding a list shows every entry with its count and a link to the entity page.
7. The list scrolls internally when it exceeds the panel height.

### US-002 — Read the year color scale without guessing

As a researcher, I want the year scale to move from light to dark for older to newer albums, so that the encoding is intuitive and visible on the canvas.

**Expected flow:**

1. The user opens the Albums view.
2. The oldest visible album is rendered in the lightest tone; the newest in the darkest tone.
3. The legend shows the real minimum and maximum years currently visible.
4. Missing years use a neutral grey.
5. The year remains available in the detail panel and accessible table.

### US-003 — Inspect a selected node without leaving the graph

As a researcher, I want a right-side panel with the selected node's documented relationships, so that I can read its context while the graph stays visible.

**Expected flow:**

1. The user selects a producer, band or album node.
2. The right panel shows the node's identity and the relationships relevant to its type.
3. The panel loads additional documented data when the current view does not contain it.
4. Loading, error, empty and truncation states remain inside the panel.
5. The panel is the same height as the graph and scrolls internally.

## 4. Functional requirements

### FR-001 — Three-part overview workspace

The overview must use a wide-screen workspace with three vertical regions: a left index, the graph and a right detail panel. The graph remains the primary surface and keeps its controls and notices.

**Verification:** page tests and headless layout check.

### FR-002 — Producer index

The left index must list the producer entities in the loaded overview response with their documented album count. The list includes producer source nodes and band entities that also carry the `producer` role. It is ordered by album count descending, then name ascending.

**Verification:** selector/adapter tests with a mixed producer and band-role fixture.

### FR-003 — Band index

The left index must list bands with their documented album count. The data comes from the existing band list endpoint with the active `decade` and `subgenre` filters and `limit=200`. The list is ordered by album count descending, then name ascending.

**Verification:** API client test and index component test.

### FR-004 — Collapsible lists

Both index lists must be native collapsible sections. Each summary states the list name and entry count. Expanding or collapsing a list must be keyboard operable and must not change the graph selection or the URL.

**Verification:** component test with keyboard interaction.

### FR-005 — Panel height and internal scroll

On wide screens, the left index and right detail panel must render with the same vertical extent as the graph workspace. The graph column defines the height; both side panels stretch to it. When their content exceeds that height, each panel scrolls independently. The page itself must not grow because of long lists or long detail content.

On stacked layouts, the panels use a bounded maximum height and scroll internally.

**Verification:** headless bounding-box check and CSS review.

### FR-006 — Dynamic sequential year scale

The overview Albums view must use a sequential scale from light to dark. The lightest tone represents the oldest album visible at that moment and the darkest tone the newest. The scale must not use white or a tone indistinguishable from the canvas background. The minimum and maximum are computed from the album nodes visible after the active filters and client toggles, not from fixed 1960–2026 bounds. Missing years use a neutral grey.

**Verification:** adapter tests with varying ranges and a headless visual check.

### FR-007 — Dynamic year legend

The legend must show the current minimum and maximum years and a gradient using the same light-to-dark scale. When the current view has no album nodes, the year item is hidden. The ego graph at `/producers/:id/graph` keeps its current year scale.

**Verification:** legend tests and page test.

### FR-008 — Producer detail panel

Selecting a producer must show its name, album and band counts, betweenness and community, plus two related lists: the bands it has worked with and the albums it has produced. The related lists come from the existing bounded producer ego graphs (`view=bands` and `view=albums`). Truncation in either ego response must be disclosed.

**Verification:** detail component tests with mocked ego responses.

### FR-009 — Album detail panel

Selecting an album must show its band, year and every documented producer connected through the loaded overview, including producers hidden by display filters. The album also links to its album and band detail pages.

**Verification:** adapter test for unfiltered incident producers and detail component test.

### FR-010 — Band detail panel

Selecting a band must show its albums and the producers who worked with it. The albums and credits come from the existing band detail endpoint. Producer and co-producer credits are deduplicated by artist.

**Verification:** detail component test with a band detail fixture.

### FR-011 — Detail panel states

The detail panel must handle loading, missing entity, fetch error, empty relationships and truncated relationships without removing the graph or the accessible table. Each state must offer a recovery action or a clear explanation.

**Verification:** component tests for loading, error, empty and truncated cases.

### FR-012 — Selection lifecycle

Selecting a node updates the existing `selected` URL parameter and the right panel. Selecting an edge keeps the existing edge detail. Changing a server filter or display filter clears the selection and the panel. If a selected node disappears from the filtered graph, the panel shows a clear "not in current view" state.

**Verification:** page tests and URL state assertions.

### FR-013 — Collapsible navigation rail

The global navigation rail must collapse to a narrow strip through an accessible button and expand again without losing navigation or search. The user preference is stored locally. On a first visit, `/graph` opens with the rail collapsed; other pages open it expanded until the user makes an explicit choice. On mobile the existing top-bar navigation remains unchanged.

**Verification:** AppShell tests, localStorage assertions and headless layout check.

### FR-014 — Wider application layout

The application must use the available viewport width. The shell must not impose the current `96rem` centered ceiling, horizontal main padding must be reduced, reading pages remain centered within their existing readable width, and `/graph` must occupy the full available width.

**Verification:** CSS review and headless width measurements at 1440 and 1920 px.

### FR-015 — Collapsible overview panels

The overview must provide `Index` and `Details` toggle buttons. Both panels start open; closing one gives its column to the graph while preserving the other panel. The panels keep their equal height and internal scroll while open. Selecting a node reopens the details panel if it was closed.

**Verification:** page/component tests and headless panel measurements.

### FR-016 — Canvas resize without physics restart

When the graph column width changes because a panel or the navigation rail is toggled, Cytoscape must resize to the new container without recreating the graph or restarting the force simulation.

**Verification:** component resize test and headless canvas-width check.

## 5. Non-functional requirements

### NFR-001 — Accessibility

The index uses native `details`/`summary`, visible focus, semantic headings and scrollable regions that remain keyboard reachable. The detail panel is labelled and announces selection changes. Color is never the only channel for year or role information. The accessible table remains available.

### NFR-002 — Performance and caching

The page must stay responsive with 384 producer entries, 57 band entries and the current 398/968-node graphs. Producer neighbor queries are cached by producer id and reused when the user returns to the same node. No list virtualization or new rendering library is required.

### NFR-003 — Scope and dependencies

This refinement adds no backend endpoint, schema change, migration, new dependency or graph renderer. It uses the existing `getBands`, `getProducerGraph` and `getBand` clients and the existing query keys.

### NFR-004 — Visual and responsive quality

The workspace must preserve the studio-ledger visual identity and remain usable on tablet and mobile widths. At narrow widths the graph comes first, followed by details and the index; side panels must not force horizontal scrolling.

### NFR-005 — Space efficiency and motion safety

At 1440 px the graph should use roughly 60% of the viewport with the rail collapsed and both panels open, and more when panels are closed. Resizing must not restart physics, reset zoom or violate reduced-motion behavior. No new dependency, API or schema change is allowed.

## 6. Business rules

- **BR-001:** A producer's count is the number of documented albums in which the producer has a production credit (`album_count` from the E7 producer metrics).
- **BR-002:** A band's "productions" count is its number of documented albums (`album_count` from the band list endpoint), not the number of producer relationships.
- **BR-003:** The left index is a read-only navigation aid over the loaded analysis run. It reflects the server-side view and period filters; client-only role, search and isolated-producer filters do not rewrite the index.
- **BR-004:** A shared band or album node connects to every credited producer. Detail lists use all incident producers, not only those left visible by display filters.
- **BR-005:** The year scale runs from light for the oldest visible album to dark for the newest, with a neutral grey for unknown years.
- **BR-006:** The rail preference is explicit user state and overrides the route-based default. The default only applies when no preference has been stored.
- **BR-007:** Overview panels start open; collapsing them is reversible and details reopen on node selection.

## 7. Edge cases and errors

- No album nodes in the current view: hide the year legend item; producer and band indexes remain.
- A single visible album year: use a documented mid-tone instead of an undefined gradient.
- Missing album year: use the neutral grey and label it "Year unknown" in detail/table.
- Producer with more than 100 neighbors: show the ego truncation notice and the available lists.
- Band with no producer credits: show an empty producers state.
- Album with no incident producer in the loaded run: show an empty producers state.
- Producer or band detail request fails: keep the canvas and table; show an error with retry in the panel.
- Selected node is removed by a filter: clear the panel and show the current selection state.
- Long lists or long album titles: scroll inside the panel; do not grow the page or overlap the graph.
- Narrow viewport: stack the three regions; keep controls and scroll regions reachable.

## 8. Out of scope

- Backend, API, OpenAPI or database changes.
- Changing the year scale or labels of the ego graph.
- Selecting nodes from the index lists.
- List virtualization, export, tooltips or a new graph renderer.
- Tailwind, Plotly or a component library.
- Authentication, writes or deployment.

## 9. Acceptance criteria

| ID | Criterion | Evidence |
|---|---|---|
| AC-001 | The left index shows producer and band lists with entry counts. | Component/page tests |
| AC-002 | Producers and bands are ordered by documented album count descending. | Selector tests |
| AC-003 | Both lists are collapsible and keyboard operable. | Component test |
| AC-004 | On wide screens both panels match the graph workspace height and scroll internally. | Headless bounding-box check |
| AC-005 | The overview year scale is light-to-dark and uses the visible album minimum and maximum. | Adapter and legend tests |
| AC-006 | The legend shows the current year range and hides when no albums are visible. | Legend/page test |
| AC-007 | Selecting a producer shows its bands and albums from the ego graphs. | Detail test |
| AC-008 | Selecting an album shows band, year and all incident producers. | Detail/adapter test |
| AC-009 | Selecting a band shows its albums and producers. | Detail test |
| AC-010 | Loading, error, empty and truncated detail states do not break the canvas. | Detail/page tests |
| AC-011 | The workspace stacks without horizontal overflow on narrow screens. | Headless viewport check |
| AC-012 | No backend, schema, migration or dependency changes are introduced. | Diff/scope inspection |
| AC-013 | Frontend lint, typecheck, tests and build pass. | Local commands |
| AC-014 | The navigation rail collapses to a narrow strip, expands, and keeps an accessible toggle. | AppShell test and headless check |
| AC-015 | The rail preference persists; `/graph` starts collapsed without a stored preference. | localStorage and route tests |
| AC-016 | The shell and graph use the available width at 1440 and 1920 px without horizontal overflow. | Headless width measurements |
| AC-017 | Index and Details panels toggle independently; closing them widens the graph; selecting a node reopens Details. | Page tests and headless check |
| AC-018 | Canvas width follows panel/rail changes without recreating Cytoscape or restarting physics. | ResizeObserver test and headless check |

## 10. Assumptions and open questions

### Assumptions

- "Producciones" for a band means documented albums, as confirmed by the owner.
- Full producer relationship lists use the existing bounded ego graphs, as confirmed by the owner.
- The new year scale applies only to the global overview; the ego graph keeps its current scale.
- The index lists are read-only and start collapsed; node interaction stays on the canvas.
- The navigation rail collapses to a 3rem strip; the preference is stored in localStorage.
- The graph panels start open and their open state is local to the page.
- The new spec is `012`; the planned E11–E13 placeholder specs move to `013`–`015`.
- The exact palette may be tuned after a visual review; the lightest tone must remain distinguishable from `#dde2dc`.

### Open questions

No blocking question remains. The palette values and exact scrollbar styling are plan-level details.

## 11. Validation result

- **Date:** 2026-11-11
- **Verdict:** Revision 3 implemented locally; remote CI pending. All acceptance criteria have local automated or headless evidence.
- **Evidence:**
  - frontend lint, typecheck, 94 tests and production build passed;
  - headless Chromium confirmed equal 858 px heights for the index, graph and detail columns; the index scrolled from 14,700 px of content inside an 856 px panel; the producer index showed 384 rows and the band index 57;
  - the overview year scale used `#bcd8c2` for 1968 and `#123c38` for 2026, with the legend showing `1968 to 2026`;
  - producer detail showed 4 bands and 20 albums for Charlie Bauerfeind; album detail showed Helloween, 1994 and 3 producers; band detail showed 23 albums and 33 producers for Motörhead;
  - revision 3 headless checks: `/bands` starts with a 272 px expanded rail and `/graph` with a 48 px collapsed rail; the rail preference persisted across reloads; the 1440 px graph grew from 876 px with both panels open to 1,144 px with Details closed and 1,348 px with both closed; the 1920 px shell used the full width and the graph reached 1,352 px with both panels open; 900/1200 px layouts had no horizontal overflow; the canvas width followed the column after every toggle and node selection reopened Details;
  - backend Ruff/format and 220 unit tests passed; `docker compose config -q` passed; OpenAPI did not drift.

## 12. References

- [Constitution](../../constitution.md)
- [AGENTS.md](../../AGENTS.md)
- [Roadmap](../../docs/00-vision/roadmap.md)
- [Frontend explorer](../../docs/01-architecture/frontend.md)
- [Read-only API v1](../../docs/03-data/api-v1.md)
- [SPEC-009 — Read API](../009-read-api/spec.md)
- [SPEC-010 — Entity explorer](../010-entity-explorer/spec.md)
- [SPEC-011 — Graph visualization](../011-graph-visualization/spec.md)
