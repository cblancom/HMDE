# Frontend: entity explorer

- **Status:** E9 validated; E10 global overview, ego graph, space-efficient workspace and alternate layouts implemented locally; headless checks passed; manual ego interaction and remote CI pending
- **Stage:** E10
- **Specs:** [SPEC-011](../../specs/011-graph-visualization/spec.md), [SPEC-012](../../specs/012-graph-overview-refinements/spec.md), [SPEC-013](../../specs/013-graph-layout-modes/spec.md)
- **Design plans:** [SPEC-011 plan](../../specs/011-graph-visualization/plan.md), [SPEC-012 plan](../../specs/012-graph-overview-refinements/plan.md)

## 1. Routes

| Route | Purpose |
|---|---|
| `/` | Redirects to `/bands` |
| `/bands` | Searchable band ledger with taxonomy, decade and pagination |
| `/bands/:bandId` | Band detail, albums, credits and compact E2 producer view |
| `/albums` | Searchable album ledger |
| `/albums/:albumId` | Album detail, taxonomy and support-aware credits |
| `/producers` | Producer rankings with sort, search and filters |
| `/producers/:producerId` | Producer metrics, community, top albums and bands |
| `/producers/:producerId/graph` | Producer ego graph, album/band views and force physics |
| `/graph` | Global producer overview, shared band/album nodes and ego drill-down |
| `/search?q=` | Grouped bounded search |
| `*` | Not-found page |

## 2. Design direction

The interface is a **studio production ledger**, not a generic dashboard.

- Cool galvanized paper (`#E9EBE5`) with petrol structure (`#173D3D`).
- Oxide (`#8F3B28`) marks links, focus and selection; brass (`#7A5A20`) is a restrained secondary accent.
- Bricolage Grotesque carries display/UI; Source Serif 4 carries reading text.
- A persistent index rail and `band — album — producer` signal path are the memorable structural devices.
- Lists are ruled ledgers with no identical rounded-card kit.
- No all-caps eyebrows, middle-dot metadata strings, mono data labels or decorative metal clichés.
- Motion is limited to user-triggered state changes; reduced motion is respected.

Tailwind is deferred. The app uses the existing CSS architecture with custom properties.

## 3. State model

- React Router owns URL state: search, taxonomy, decade, sort and pagination.
- TanStack Query owns server state.
- Changing a filter resets `offset`.
- Browser back/forward restores list views.
- No global state store.
- The navigation-rail preference is stored in localStorage; graph panel toggles are local page state.

## 4. API clients

Typed modules under `frontend/src/api/` import response types from the generated `schema.d.ts`:

- `bands.ts`
- `albums.ts`
- `artists.ts`
- `producers.ts`
- `producerGraph.ts` (ego and global overview clients)
- `search.ts`
- `taxonomy.ts`
- `queryKeys.ts`

No hand-written duplicate entity interfaces.

## 5. Accessibility

- Skip link to `#main-content`.
- Visible oxide focus ring.
- Semantic headings and form labels.
- Table captions and column headers.
- Focusable, horizontally scrollable table wrappers.
- Live result/status announcements.
- Error, empty and not-found states with next actions.
- Reduced-motion media query.
- Cytoscape initialization is guarded when canvas is unavailable.

## 6. Graph views

E10 has two graph scopes built on separate endpoints and the same `cytoscape-d3-force` lifecycle:

- `/graph` is the global overview over `GET /api/v1/graph/producers`.
- `/producers/:producerId/graph` is the ego drill-down over the bounded E8 endpoint.

Both use `view=bands` (producer + band/artist nodes) or `view=albums` (producer + album nodes). Shared band/album nodes connect to every credited producer; no producer–producer edges are synthesized. The overview has a 1,000-node / 2,000-edge cap and the ego graph keeps 500 / 2,000.

The force layout must pass `linkId: (node) => node.id`. d3-force links carry canonical UUID endpoints, while its default accessor assumes array indices; omitting the accessor throws `node not found: <uuid>` and, because the layout starts inside a React effect, can unmount the root and blank the page. If a layout cannot start, the component catches the error, applies a static `breadthfirst` layout and freezes physics so the page and table fallback remain available.

Ego preset: type-sized collision radii (22/28/34), `collideStrength=0.9`, `collideIterations=2`, `manyBodyStrength=-320` and a node-count link distance of 180–300, capped by the canvas height. The canvas grows with the viewport (`clamp(32rem, 65vh, 48rem)`) and album titles are always visible.

Overview preset: infinite physics with `manyBodyStrength=-45`, `linkDistance=42–90`, collision 8/7/10 by producer/album/band, `collideStrength=0.6`, `collideIterations=1`, `alphaDecay=0.035` and `velocityDecay=0.55`. The initial view fits immediately and again after 1.2 s. Node size reflects filtered degree. Labels declutter by zoom: bands are always visible, producer and album labels appear at a 12 px rendered font size, and selected or search-matched labels always show. Search highlights matching producers without recreating the Cytoscape instance. Isolated producer nodes are muted.

Both scopes can be frozen, resumed or reheated; physics pauses when the tab is hidden and starts frozen under `prefers-reduced-motion`.

Overview controls cover view, producer top-k, sort/order, decade, subgenre, role, producer search/highlight and the isolated toggle. Server-side selection uses producer limit/sort/decade/subgenre; role, search and the toggle are client-side over the loaded network. Counts and API truncation remain visible. The accessible table lists the filtered nodes and edges, and details list incident producers with ego-graph links.

SPEC-012 turns the overview into a three-region workspace:

- the left index has native collapsible producer and band lists with documented album counts, sorted descending and linked to entity pages;
- the center keeps the graph;
- the right panel shows producer bands/albums from the two bounded ego graphs, band albums and producer credits from the band detail endpoint, or album band/year/producers from the loaded overview.

On wide screens the graph column defines the workspace height and both side panels stretch to it, scrolling independently. Below 1280 px the regions stack. The overview year scale runs from pale lichen `#bcd8c2` for the oldest visible album to deep petrol `#123c38` for the newest; the range is recomputed from the visible albums after filters and the isolated toggle. The legend shows the real minimum and maximum. The ego graph keeps its existing scale.

Revision 3 makes the layout space-efficient:

- the global rail collapses to a 3rem strip with an accessible toggle and `HMDE` monogram; the preference is stored in localStorage, `/graph` starts collapsed without a stored preference and other routes start expanded;
- the shell has no `96rem` ceiling, horizontal main padding is `clamp(0.75rem, 1.5vw, 1.5rem)`, reading pages stay centered and `/graph` uses the full width;
- the overview has `Index` and `Details` toggles; both panels start open and closing one or both gives the column width to the graph;
- selecting a node reopens the details panel;
- a `ResizeObserver` calls `cy.resize()` when the graph column changes width, without recreating Cytoscape or restarting physics;
- panel widths are `minmax(10rem,12rem)` and `minmax(14rem,16rem)` with 0.75rem gaps.

SPEC-013 adds a `Layout` selector with `Force`, `Bipartite` and `Community`:

- Force is the default and keeps the current d3-force behavior.
- Bipartite uses NetworkX `bipartite_layout` on the server: producers on the left, bands/albums on the right. The response includes deterministic coordinates and the graph applies a fitted static preset.
- Community reuses the E7 Louvain `community_key`, assigns targets to the majority producer community, and positions community centers with a contracted graph plus seeded `spring_layout`; members are placed on deterministic rings.
- Static modes disable Freeze/Resume/Reheat and show `Static layout`. Selecting Force restores physics.
- Layouts are requested only for the overview, included in the URL as `layout=force|bipartite|community` and cached by query key. The ego graph is unchanged.
- Missing or invalid coordinates fall back to Force with a visible notice.

Current v0.2 corpus: 398 unique nodes / 426 edges in `bands` and 968 nodes / 1,134 edges in `albums`. The albums isolated toggle reduces the loaded network to 893 nodes / 951 edges. In the bands view the 43 isolated producer entities share band entities and remain visible as bands.

## 7. Boundary

E10 does not include:

- database schema changes or migrations;
- Tailwind, Plotly or a component library;
- a new graph renderer;
- writes or authentication;
- Playwright, performance, accessibility audit or deployment (E11);
- corpus expansion (E13).

The only E10 API change is the additive read-only overview endpoint. SPEC-012 adds no endpoint, schema or dependency.

## 8. Verification

Local checks on 2026-11-11:

- frontend `npm ci`, OpenAPI generation, lint, typecheck, **98 tests**, production build;
- headless Chromium on `/graph`: 398-node bands and 968-node albums views, initial fit, live physics, freeze/resume/reheat, dragging, search highlight, isolated toggle, reduced-motion frozen start and accessible table;
- SPEC-012 headless checks: equal 858 px panel heights, independent panel scroll, 384 producer and 57 band index rows, dynamic `1968 to 2026` year scale, producer/album/band detail flows and stacked 900/1200 px layouts without horizontal overflow;
- revision 3 headless checks: 48 px collapsed and 272 px expanded rail with persisted state, 876/1,144/1,348 px graph widths at 1440 px for open/one-closed/both-closed panels, 1,352 px graph at 1920 px with both panels open, canvas width following the column after every toggle; `/bands`, `/albums`, `/producers`, `/graph` and `/search` had no horizontal overflow at 1440/1920 px;
- SPEC-013 headless checks: Force physics, Bipartite producer x=80 / album x=920, Community clusters, disabled static controls and a fitted 968-node album view; layout API requests took ~0.16 s (Bipartite) and ~0.25 s (Community);
- backend 220 unit tests with 105 integration tests skipped; Ruff and format;
- `docker compose config -q`;
- no Tailwind/Plotly/UI-kit dependencies;
- no hard-coded taxonomy arrays.

The last passed remote GitHub Actions CI run [42747146170](https://github.com/cblancom/HMDE/actions/runs/42747146170) covers SPEC-010; SPEC-011, SPEC-012 and SPEC-013 remote CI and the manual ego interaction review are pending.
