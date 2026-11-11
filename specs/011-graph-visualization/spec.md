# SPEC-011 — Producer graph visualization and interaction

- **Status:** Implemented
- **Stage:** E10
- **Iteration:** MVP
- **Module:** `web`
- **Date:** 2026-11-10
- **Depends on:** SPEC-008 validated; SPEC-009 validated; SPEC-010 validated; read-only API v1; Cytoscape and the approved `cytoscape-d3-force` extension
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0006](../../docs/01-architecture/adr/ADR-0006-read-only-api.md), [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)
- **Plan:** [plan.md](plan.md) (approved).
- **Tasks:** [tasks.md](tasks.md) (implemented locally).
- **Conventions:** [Engineering conventions](../../docs/01-architecture/conventions.md)
- **Owner:** Cristian

## Revision history

| Revision | Date | Change |
|---|---|---|
| 1 | 2026-11-10 | Initial draft; producer graph views, d3-force physics, client-side display filters and 500-node v0.1 cap |
| 2 | 2026-11-10 | Technical plan and tasks drafted for review |
| 3 | 2026-11-10 | T-001–T-008 implemented locally; automated checks passed; manual physics and remote CI pending |
| 4 | 2026-11-10 | Fixed the blank graph page: d3-force links now use canonical node ids (`linkId`) and layout failures fall back to a static layout instead of unmounting React |
| 5 | 2026-11-10 | T-010 polishes the graph: stronger collision/repulsion spreads a producer's neighbors, album titles are always visible, and the canvas uses more vertical space |

## 1. Context and problem

E9 validated the entity explorer: bands, albums, producers, search and taxonomy views are available. E7 provides producer–album and producer–band layers; E8 exposes bounded graph endpoints with run/version metadata and limits.

E10 must turn those endpoints into an explorable graph with a physical, alive feeling rather than a static drawing. The desired interaction is close to Obsidian's graph: nodes repel, edges pull, dragging a node moves the surrounding network, and the layout can keep settling or be frozen deliberately.

The graph stays producer-centric:

- `view=albums`: producer and album nodes.
- `view=bands`: producer and band/artist nodes.
- No mixed album/band canvas and no album–album projection.

E10 v1 uses E8 as-is. There are no API, database or canonical-data changes. Graph filters are applied to the loaded ego network in the browser, and the v0.1 cap remains 500 nodes.

```text
E7 graph layers ──► E8 bounded graph endpoint
                           │
                           ▼
                    E10 graph page
       Cytoscape + cytoscape-d3-force
       separate albums / bands views
       freeze · resume · reheat · filters
       legend · details · accessible table
```

## 2. Goals and non-goals

### Goals

- Let users open a producer's graph from the existing producer ranking.
- Provide separate `albums` and `bands` views.
- Render a force-directed graph that feels alive when nodes are dragged.
- Allow the simulation to be frozen, resumed and reheated.
- Respect reduced-motion preferences and pause background simulation.
- Encode album year, producer type, edge role and support without relying on color alone.
- Provide details on selection and an accessible table fallback.
- Handle truncation, empty, error and no-credit states.
- Keep the v0.1 graph within 500 nodes and 2,000 edges.

### Non-goals

- A full-corpus graph.
- Album–album or artist–artist product views.
- Backend/API/schema changes.
- Server-side graph filtering in E10 v1.
- Persisting node positions or a graph editor.
- A new graph renderer or a D3 from-scratch rewrite.
- Replacing the E9 entity explorer.
- Playwright/performance QA; E11 owns that.
- Tailwind or a UI component library.

## 3. Users and flows

### US-001 — Open a producer graph

As an analyst, I want to open a graph from a producer so that I can inspect documented relationships without reading tables.

**Flow:**

1. User opens `/producers` and selects a producer.
2. Producer detail exposes `Open graph`.
3. Graph opens with `view=bands` by default.
4. Graph shows the selected producer and its documented band/artist neighbors.
5. User switches to `view=albums` to see album evidence.

### US-002 — Move the network physically

As a user, I want to drag a node and see the network respond so that the graph feels spatial rather than static.

**Flow:**

1. The force simulation is active.
2. User drags a producer or connected node.
3. Neighbors move under spring/repulsion forces.
4. On release, the simulation continues or settles based on the current mode.
5. User can freeze the layout at any time.

### US-003 — Control physics

As a user, I want to freeze, resume or reheat the layout so that I can inspect a stable graph or restart the simulation.

**Flow:**

1. `Freeze layout` stops simulation ticks while preserving positions.
2. `Resume physics` restarts the simulation from current positions.
3. `Reheat` restarts from a hotter state/randomized positions when needed.
4. The controls remain keyboard accessible.

### US-004 — Filter the loaded view

As a user, I want to filter by role, decade and taxonomy so that I can focus the graph.

**Flow:**

1. The graph API response is loaded within E8 limits.
2. Client-side filters hide non-matching nodes/edges.
3. Active filters are visible and can be cleared.
4. The UI states that filters apply to the loaded ego network.
5. If the API returned `truncated=true`, this remains visible.

### US-005 — Read the graph without seeing it

As a user who cannot use the canvas, I want an accessible table of nodes and edges.

**Flow:**

1. A legend explains shape/color/line semantics.
2. A table lists nodes, types and key attributes.
3. A table lists edges, roles, support and endpoint labels.
4. The selected node/edge details are exposed outside the canvas.

## 4. Routes and data contract

### 4.1 Routes

```text
/producers/:producerId/graph?view=bands&limit=20&depth=1
/producers/:producerId/graph?view=albums&limit=20&depth=1
```

- Default view: `bands`.
- `limit`: 20 default, max 100.
- `depth`: 1 default, max 2.
- `max_nodes`: 500.
- `max_edges`: 2000.
- `include_evidence=true` for edge detail panels when needed.

Top-k selection uses the existing `/api/v1/producers` ranking. E10 v1 does not add a top-k graph endpoint.

### 4.2 E8 response use

- `nodes[].id`: canonical entity UUID.
- `nodes[].type`: producer, album or band.
- `nodes[].roles`: source roles.
- `nodes[].attributes`: year, decade, artist type, band metadata, taxonomy and self-produced flags.
- `edges[].layer`: `producer_album` or `producer_band`.
- `edges[].role`: producer/co-producer or mixed.
- `edges[].support_ratio`, `supporting_recordings`, `album_recordings`.
- `edges[].weight` and `album_count`.
- `edges[].evidence`.
- `meta`: run/version, view, limits and `truncated`.

No new API fields are required for v0.1.

## 5. Visual contract

### 5.1 Studio-ledger extension

The graph page continues the E9 visual identity: galvanized paper, petrol canvas frame, oxide and brass accents, Bricolage Grotesque labels and Source Serif 4 explanatory text. The canvas is a working sheet inside the ledger, not a separate dark “graph app”.

### 5.2 Nodes

| Node | Shape | Color |
|---|---|---|
| Producer, person | Circle | Oxide |
| Producer, group/self-produced | Hexagon | Brass |
| Producer, unknown type | Circle | Muted grey |
| Album | Square | Year scale |
| Band/artist | Rounded rectangle | Neutral petrol/sheet |

Album node color uses a sequential colorblind-safe scale (Cividis/Viridis or equivalent) from 1960 to 2026. Missing years use a neutral grey. The year is also present in the details panel and table; color is never the only channel.

Album titles are always visible below the node. Selection adds a border and details without being required to read the title. Long titles wrap within a readable width, and album labels use a subtle background so they remain legible over edges.

### 5.3 Edges

- `producer` edge: solid.
- `co-producer` edge: dashed.
- Album support ratio: width/opacity.
- Producer–band weight: width by distinct album count.
- Edge labels are shown on selection, not permanently for every edge.
- Selecting an edge opens a detail panel with evidence and supports.

### 5.4 Layout and physics

Use `cytoscape-d3-force` with:

- force simulation, not a static layout;
- `infinite: true` for live physics on the loaded ego network;
- `fixedAfterDragging: false`;
- `ungrabifyWhileSimulating: false`;
- collision/repulsion/link-distance values tuned for the 500-node cap;
- collision radii sized by node type so neighbors do not overlap or bunch around the producer;
- enough link distance and repulsion for album titles to remain readable around the seed;
- a taller canvas that uses available viewport space without hiding the controls;
- simulation pause when the document is hidden;
- `Freeze layout`, `Resume physics` and `Reheat` controls;
- `prefers-reduced-motion`: start frozen; physics is opt-in and never required to read the graph.

Implementation constraints learned in T-009:

- d3-force must resolve link endpoints by canonical node id. The layout passes `linkId: (node) => node.id`; without it, d3-force uses the array index and throws `node not found: <uuid>`, which unmounts the React root and leaves a blank page.
- A physics failure must never escape the component. If the force layout cannot start, the canvas falls back to a static `breadthfirst` layout and freezes, keeping the page content and the accessible table available.

If continuous simulation causes unacceptable CPU/visual churn on supported hardware, the fallback is a finite animated simulation with `Reheat` on drag. The chosen mode and parameters must be recorded in the graph page documentation.

### 5.5 Filters

Client-side filters operate on the loaded E8 subgraph:

- role: producer/all, co-producer;
- decade;
- taxonomy leaf/family represented in album metadata;
- selected producer/band/album context where applicable.

The UI must visibly state:

- filters apply to the loaded ego network;
- API truncation remains in effect;
- clearing filters restores the loaded graph.

## 6. Functional requirements

### FR-001 — Graph route and producer entry

The graph must be reachable from a producer detail page via `/producers/{id}/graph`, with the producer as the selected seed.

**Verification:** route and link tests.

### FR-002 — Separate album and band views

The page must support `view=albums` and `view=bands` and never mix node types across those views.

**Verification:** graph adapter and component tests.

### FR-003 — Bounded graph loading

The page must use E8 limits for `limit`, `depth`, `max_nodes` and `max_edges`, preserve run metadata and display `truncated`.

**Verification:** limit/truncation tests.

### FR-004 — Force simulation

The graph must use an approved force layout that produces continuous or reheatable physics, rather than a static layout.

**Verification:** layout configuration tests and manual browser check.

### FR-005 — Drag behavior

Dragging a node must update its position and allow connected nodes to respond according to the active simulation.

**Verification:** manual interaction check and adapter tests.

### FR-006 — Physics controls

The page must expose freeze, resume and reheat controls with keyboard-accessible buttons and visible state.

**Verification:** control tests and manual check.

### FR-007 — Visual encodings

The page must encode node type, producer type, album year, edge role and support according to the visual contract.

**Verification:** adapter/style tests and legend review.

### FR-008 — Client-side filters

The page must filter the loaded graph by role, decade and taxonomy and clearly describe the loaded-network scope.

**Verification:** filter tests.

### FR-009 — Selection and details

Selecting a node or edge must show evidence, support, role, year/decade and related entity links in a details panel.

**Verification:** selection/detail tests.

### FR-010 — Accessible fallback

Every graph must have a visible legend and an accessible table fallback listing nodes and edges.

**Verification:** accessibility tests and manual keyboard check.

### FR-011 — Empty/error/truncated states

The page must handle no graph, no edges, API error, 404 producer and truncated response explicitly.

**Verification:** state tests.

### FR-012 — Reduced motion

With `prefers-reduced-motion: reduce`, the initial graph must be frozen and physics must be opt-in.

**Verification:** media-query test and manual check.

### FR-013 — Background pause

Physics must pause when the document is hidden and resume safely when visible if enabled.

**Verification:** visibility event tests and manual check.

### FR-014 — Scope boundary

E10 must not add API/schema changes, Tailwind, Plotly, a new graph renderer or writes.

**Verification:** dependency/route/scope inspection.

### FR-015 — Tests and documentation

The implementation must include unit/component tests for adapters, filters, controls, states, legend and fallback, plus a manual physics/performance checklist.

**Verification:** frontend checks and E10 docs.

## 7. Non-functional requirements

### NFR-001 — Performance

A 500-node / 2,000-edge ego network must remain usable. The simulation must be pausable and must not block navigation or the rest of the explorer.

### NFR-002 — Motion safety

Physics motion respects reduced-motion, pauses in hidden tabs and is never required to access data.

### NFR-003 — Accessibility

Keyboard-accessible controls, text labels, focus, legend, table fallback and non-color-only encodings are mandatory.

### NFR-004 — Determinism of data

Graph data and metrics remain deterministic per E7 run; layout positions are not persisted or treated as analytical facts.

### NFR-005 — Scope control

E10 is frontend-only. E8 remains the bounded graph contract.

### NFR-006 — Maintainability

Graph mapping and physics configuration are isolated from page chrome and API clients.

### NFR-007 — Browser stability

Cytoscape cleanup must destroy the instance on unmount; no leaks across route changes.

### NFR-008 — Language

All labels, legends, controls and empty/error copy are in English.

## 8. Business rules

- **BR-001:** Producers are the graph center.
- **BR-002:** Album and band views are separate; no mixed canvas.
- **BR-003:** Force motion is presentation, not analytical evidence.
- **BR-004:** Filters apply to the loaded ego network, and truncation remains visible.
- **BR-005:** Missing nodes/edges are not negative evidence.
- **BR-006:** Color is never the only carrier of year, type or support.
- **BR-007:** Reduced-motion starts frozen.
- **BR-008:** No API or data mutation is part of E10.
- **BR-009:** No full graph is loaded or rendered.
- **BR-010:** `cytoscape-d3-force` is the approved physics extension for E10.

## 9. Edge cases and errors

- Producer with no graph: show a clear empty state and link back.
- Ego network with one node: render the node and a no-connections message.
- API returns `truncated=true`: show a persistent truncation notice.
- Graph filter removes all visible nodes: show a filtered-empty state with clear action.
- No album year: grey node and “Year unknown” label.
- Self-produced producer: group/self-produced encoding; no self-loop.
- Very large labels: wrap/limit without breaking layout.
- Simulation errors or canvas failure: show fallback table and a recoverable message.
- Route unmount: destroy simulation/listeners.
- Hidden tab: pause simulation.
- Reduced motion: freeze initial layout.

## 10. Out of scope

- Server-side graph filters or a top-k graph API.
- A multi-producer overview; E10 renders one producer ego network per page. A future spec will define the bounded multi-producer view.
- More than 500 nodes in v0.1.
- Album–album or artist–artist graph views.
- Graph editing, pinned layouts or persisted positions.
- Playwright/load/accessibility audit, deployment and corpus expansion.
- Tailwind, Plotly or a component library.

## 11. Acceptance criteria

| ID | Criterion | Evidence |
|---|---|---|
| AC-001 | Producer detail links to the graph route with the producer as seed. | Route/link tests |
| AC-002 | `albums` and `bands` views never mix node types. | Adapter tests |
| AC-003 | E8 limits, run metadata and truncation are respected and visible. | Limit tests |
| AC-004 | Force simulation is active and reheatable. | Config/manual check |
| AC-005 | Dragging a node moves the connected network. | Manual interaction check |
| AC-006 | Freeze/resume/reheat controls work and are keyboard accessible. | Control tests |
| AC-007 | Node/edge visual encodings match the legend and contract. | Style/adapter tests |
| AC-008 | Client-side filters hide matches and disclose loaded-network scope. | Filter tests |
| AC-009 | Node/edge selection exposes evidence and support. | Detail tests |
| AC-010 | An accessible table fallback lists nodes and edges. | Accessibility tests |
| AC-011 | Empty, error, 404, no-edge and truncated states are handled. | State tests |
| AC-012 | Reduced motion starts the graph frozen. | Media-query/manual check |
| AC-013 | Physics pauses when the document is hidden. | Visibility test/manual check |
| AC-014 | 500-node / 2,000-edge graph remains usable. | Manual performance check |
| AC-015 | No API/schema/Tailwind/Plotly/new renderer changes occur. | Scope inspection |
| AC-016 | Tests, lint, typecheck and build pass. | Local/CI evidence |
| AC-017 | Graph page documentation includes physics parameters and limits. | Docs review |
| AC-018 | Remote CI passes. | CI evidence |
| AC-019 | Album titles are visible without hover or selection, and long titles remain readable. | Style test and browser check |
| AC-020 | A producer's neighbors spread around the canvas instead of bunching, with collision radii sized by node type. | Layout config test and browser check |

## 12. Assumptions and resolved decisions

### Assumptions

- E8 graph endpoints remain stable for v0.1.
- `cytoscape-d3-force` is compatible with the installed Cytoscape 3.x line.
- The graph page opens selected producer ego networks, not a full-corpus graph.
- Client-side filters are acceptable for the loaded network size.
- E11 will run Playwright/performance/a11y QA.

### Resolved decisions

| Decision | Resolution |
|---|---|
| Physics library | `cytoscape-d3-force` approved; transitive `d3-force` dependency. |
| Physics mode | Infinite force simulation by default on loaded ego networks; freeze/resume/reheat controls. |
| Reduced motion | Start frozen; physics opt-in. |
| Graph limits | v0.1 max 500 nodes / 2,000 edges. 2,000-node target moves to E13/API revision. |
| Filter placement | Client-side over the loaded E8 subgraph; API remains unchanged. |
| Top-k overview | Producer ranking from E9; no top-k graph endpoint in E10 v1. |
| Graph route | `/producers/:producerId/graph?view=albums|bands`. |
| Rendering | Cytoscape with force extension; no new renderer. |
| Force node identity | `linkId: (node) => node.id`; d3-force links carry canonical UUIDs, not array indices. |
| Neighbor spacing | Type-sized collision radii, stronger repulsion and a canvas-aware, node-count-based link distance (180–300). |
| Album labels | Album titles are always visible with wrapping and a subtle background; selection adds a border and details. |
| Physics failure | Fall back to a frozen static layout; never propagate layout errors to the React tree. |
| Scope | Frontend only; no API, schema or writes. |

### Open questions

No blocking question remains for planning. Exact force coefficients, freeze behavior and layout tuning are plan-level details.

## 13. Validation result

- **Date:** 2026-11-10
- **Verdict:** Implemented; automated validation passed; physics startup, neighbor spacing and album labels verified in a headless browser; manual drag review and remote CI pending
- **Evidence:** 62 frontend tests, lint, typecheck and production build passed; backend 313 tests, Ruff/format and Compose passed; the graph page and E8 graph endpoint return data in the dev environment. Headless Chromium renders the `bands` and `albums` views with no console errors; a runtime probe on the 21-node album graph confirmed centered neighbors at 276–290 px from the producer and album titles visible at 10px. Manual drag/freeze/reheat interaction review remains pending because no graphical browser is available. Remote CI is pending because no commit or push was performed. See `tasks.md`.

## 14. References

- [Constitution](../../constitution.md)
- [AGENTS.md](../../AGENTS.md)
- [Roadmap](../../docs/00-vision/roadmap.md)
- [Frontend explorer](../../docs/01-architecture/frontend.md)
- [Producer network analysis](../../docs/03-data/network-analysis.md)
- [Read-only API v1](../../docs/03-data/api-v1.md)
- [ADR-0006 — Read-only API](../../docs/01-architecture/adr/ADR-0006-read-only-api.md)
- [SPEC-008 — Network analysis](../008-network-analysis/spec.md)
- [SPEC-009 — Read API](../009-read-api/spec.md)
- [SPEC-010 — Entity explorer](../010-entity-explorer/spec.md)
