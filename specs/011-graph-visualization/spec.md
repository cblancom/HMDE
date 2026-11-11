# SPEC-011 — Producer graph visualization and interaction

- **Status:** Implemented
- **Stage:** E10
- **Iteration:** MVP
- **Modules:** `api`, `web`
- **Date:** 2026-11-10
- **Depends on:** SPEC-008 validated; SPEC-009 validated; SPEC-010 validated; read-only API v1; Cytoscape and the approved `cytoscape-d3-force` extension
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0006](../../docs/01-architecture/adr/ADR-0006-read-only-api.md), [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)
- **Plan:** [plan.md](plan.md) (revision 6 approved).
- **Tasks:** [tasks.md](tasks.md) (T-001–T-016 completed locally; remote CI and manual interaction pending).
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
| 6 | 2026-11-10 | Global producer overview: one canvas with many producers and their bands or albums, additive read-only overview endpoint, 1,000-node cap, shared-neighbor semantics, isolated-producer toggle and ego-graph drill-down |
| 7 | 2026-11-11 | T-011–T-016 implemented locally: overview service and endpoint, `/graph` page, overview physics and labels, tests and documentation. Corrected corpus counts to 398 unique band-view nodes and 968 album-view nodes; the 43 isolated producer entities share band entities in the bands view. Remote CI and manual interaction remainder pending |

## 1. Context and problem

E9 validated the entity explorer: bands, albums, producers, search and taxonomy views are available. E7 provides producer–album and producer–band layers; E8 exposes bounded graph endpoints with run/version metadata and limits.

E10 must turn those endpoints into an explorable graph with a physical, alive feeling rather than a static drawing. The desired interaction is close to Obsidian's graph: nodes repel, edges pull, dragging a node moves the surrounding network, and the layout can keep settling or be frozen deliberately.

E10 has two graph scopes:

- **Global overview (`/graph`)**: one canvas with many producers and the bands or albums associated with them. This is the primary analysis view.
- **Producer ego graph (`/producers/:id/graph`)**: one producer and its neighbors. It remains as a drill-down from the global overview and producer detail.

Both scopes use the same producer-centric view rules:

- `view=bands`: producer and band/artist nodes. A shared band node connects to every producer that worked with it.
- `view=albums`: producer and album nodes. A shared album node connects to every producer credited on it.
- No mixed album/band canvas, no album–album projection and no producer–producer projection in v1.

The global overview adds an additive read-only API endpoint backed by the E7 persisted graph layers. It does not change the canonical data model or the database schema. The ego graph keeps the existing bounded E8 endpoint. Global selection is server-side and bounded; display filters are applied to the loaded network in the browser.

```text
E7 graph layers ──┬─► E8 ego endpoint ──────► /producers/:id/graph
                  │                              (one producer)
                  └─► E10 overview endpoint ──► /graph
                                                 (many producers)
       Cytoscape + cytoscape-d3-force
       separate albums / bands views
       shared band/album neighbors
       freeze · resume · reheat · filters
       legend · details · accessible table
```

## 2. Goals and non-goals

### Goals

- Let users open a producer's graph from the existing producer ranking.
- Provide a global overview with many producers on one canvas and the bands or albums associated with them.
- Keep the producer ego graph as a drill-down from the global overview.
- Provide separate `albums` and `bands` views.
- Connect a shared band or album node to every producer credited on it.
- Allow the global view to include all producers and albums in the current corpus within a 1,000-node cap.
- Let users hide producers that only have self-produced albums and no producer–band edges.
- Render a force-directed graph that feels alive when nodes are dragged.
- Allow the simulation to be frozen, resumed and reheated.
- Respect reduced-motion preferences and pause background simulation.
- Encode album year, producer type, edge role and support without relying on color alone.
- Provide details on selection and an accessible table fallback.
- Handle truncation, empty, error and no-credit states.
- Keep the ego graph within 500 nodes and 2,000 edges.
- Keep the global overview within 1,000 nodes and 2,000 edges.

### Non-goals

- An unbounded full-corpus graph or an unlimited album graph.
- Direct producer–producer edges or an inferred producer–producer projection.
- Mixed album/band canvases.
- Album–album or artist–artist product views.
- Database schema migrations or changes to canonical data.
- Writes, graph editing, pinned layouts or persisted positions.
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

1. The graph response is loaded within the active limits.
2. Display filters hide non-matching nodes/edges on the loaded network.
3. Active filters are visible and can be cleared.
4. The UI states that filters apply to the loaded network.
5. If the API returned `truncated=true`, this remains visible.

### US-005 — Read the graph without seeing it

As a user who cannot use the canvas, I want an accessible table of nodes and edges.

**Flow:**

1. A legend explains shape/color/line semantics.
2. A table lists nodes, types and key attributes.
3. A table lists edges, roles, support and endpoint labels.
4. The selected node/edge details are exposed outside the canvas.

### US-006 — Explore all producers together

As an analyst, I want one canvas with many producers and their associated bands or albums so that I can compare concentration, overlap and communities across the whole documented corpus.

**Flow:**

1. User opens `/graph` from the primary navigation.
2. The `bands` view loads all producers and band/artist nodes in one canvas.
3. The `albums` view loads all producers and album nodes within the global 1,000-node cap.
4. User selects a producer to inspect its metrics, community and neighbors.
5. User selects a band or album to see every producer connected to it.
6. User can open the selected producer's ego graph for a focused view.

### US-007 — Understand a shared band or album

As an analyst, I want a band or album node connected to every producer credited on it so that I can see who shares the same work.

**Flow:**

1. A band with two producers appears once on the canvas.
2. The single band node has an edge to each producer.
3. Selecting the band highlights all connected producers and lists them in the details panel.
4. No direct producer–producer edge is created.

### US-008 — Hide isolated producers

As an analyst, I want to hide producers that only have self-produced albums so that I can focus on producers with documented producer–band relationships.

**Flow:**

1. The global `bands` view shows isolated producers by default.
2. A visible toggle hides or shows those producers.
3. The node and edge counts update immediately.
4. The accessible table follows the same toggle.

## 4. Routes and data contract

### 4.1 Routes

```text
/producers/:producerId/graph?view=bands&limit=20&depth=1
/producers/:producerId/graph?view=albums&limit=20&depth=1
/graph?view=bands&producers=all&sort=album_count&isolated=1
/graph?view=albums&producers=all&sort=album_count&isolated=1
```

Ego graph:

- Default view: `bands`.
- `limit`: 20 default, max 100.
- `depth`: 1 default, max 2.
- `max_nodes`: 500.
- `max_edges`: 2000.
- `include_evidence=true` for edge detail panels when needed.

Global overview:

- Default view: `bands`.
- `producers`: `all` by default; a bounded top-k selection is optional.
- `max_nodes`: 1000.
- `max_edges`: 2000.
- The current corpus has 398 unique nodes in the bands view: 341 producer source nodes and 57 band nodes, representing 384 producer entities plus 57 bands because 43 band entities also carry the producer role. It has 426 simple producer–band edges. The albums view has 968 nodes (384 producers + 584 albums) and 1,134 simple edges (1,151 role rows). Both views fit the global cap.
- The 43 isolated producer entities have no outgoing producer–band edge. All of them are also band entities, so in the bands view they remain visible as shared band nodes; the API can omit their producer rows with `include_isolated=false`. In the albums view the toggle hides the 43 producer nodes and leaves 893 nodes / 951 edges.
- Isolated producers are included by default; the UI toggle can hide their producer identity.
- If a future corpus exceeds the caps, the server truncates deterministically and sets `truncated=true`; truncation is never hidden.

### 4.2 Ego response use

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

### 4.3 Global overview endpoint

```http
GET /api/v1/graph/producers
  ?view=bands|albums
  &producer_limit=0
  &producer_sort=album_count|band_count|betweenness|name
  &order=desc|asc
  &decade=1980s
  &subgenre=heavy-metal
  &include_isolated=true
  &include_evidence=false
  &max_nodes=1000
  &max_edges=2000
  &analysis_run=<uuid>
```

- `producer_limit=0` means all producers. A positive value (maximum 1,000) selects the top-k producers after filters.
- `producer_sort` uses the persisted E7 producer metrics and node labels; the default is `album_count`.
- `decade` and `subgenre` select producers with at least one matching producer–album credit. In the albums view they also restrict the album nodes and edges returned; in the bands view they only restrict producer eligibility because band nodes have no temporal or taxonomy metadata.
- `include_isolated=true` keeps producer entities with no outgoing producer–band edges (currently 43; all are also band entities). The global page loads them once and hides producer-typed isolated nodes client-side for immediate feedback; the API also accepts `false` for server-side omission. In the bands view the 43 entities remain as shared band nodes because removing them would delete documented band connections.
- `include_evidence=true` adds bounded edge evidence. The bands view requests it for `role_mix`; the albums view uses the persisted edge fields and may omit the larger evidence payload.
- The response reuses `ProducerGraphNode` and `ProducerGraphEdge` and adds a dedicated meta object with `scope=overview`, `selected_producers`, `matched_producers`, `truncated` and the global limits.
- Producer nodes are enriched in `attributes` with `album_count`, `band_count`, `betweenness` and `community_key` for sizing, filtering and details.
- Album role rows are deduplicated to one edge per producer–album pair; `role` is the single role or `mixed`, with source role codes preserved in evidence.
- No database schema change or migration is required.

Shared-neighbor semantics:

- A band or album appears once per analysis run.
- That node has one edge to each producer credited on it.
- For example, a band produced by two producers has two producer–band edges and one band node.
- No producer–producer edge is created; the shared node is the evidence of the relationship.

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

In the ego graph, album titles are always visible below the node. In the global overview, labels are decluttered for large networks:

- band labels remain visible;
- producer labels appear as the user zooms in, searches or selects a producer;
- album labels appear at a readable zoom, and the current 968-node album overview fits the 1,000-node cap; selected and searched nodes always show their label;
- long titles wrap within a readable width, and album labels use a subtle background so they remain legible over edges.

In the global overview, node size reflects connected-degree after filters so shared bands, prolific producers and co-produced albums stand out. Isolated producers are rendered muted and can be hidden with the global toggle.

### 5.3 Edges

- `producer` edge: solid.
- `co-producer` edge: dashed.
- Album support ratio: width/opacity.
- Producer–band weight: width by distinct album count.
- Edge labels are shown on selection, not permanently for every edge.
- Selecting an edge opens a detail panel with evidence and supports.
- A shared band or album node connects to every producer credited on it; there are no direct producer–producer edges.
- Selecting a shared node highlights all connected producers and exposes them in the details panel.

### 5.4 Layout and physics

Use `cytoscape-d3-force` with:

- force simulation, not a static layout;
- `infinite: true` for live physics;
- `fixedAfterDragging: false`;
- `ungrabifyWhileSimulating: false`;
- collision radii sized by node type so neighbors do not overlap or bunch;
- simulation pause when the document is hidden;
- `Freeze layout`, `Resume physics` and `Reheat` controls;
- `prefers-reduced-motion`: start frozen; physics is opt-in and never required to read the graph.

Ego graph:

- collision/repulsion/link-distance values tuned for the 500-node cap;
- enough link distance and repulsion for album titles to remain readable around the seed;
- a taller canvas that uses available viewport space without hiding the controls.

Global overview:

- tuned for 398 unique nodes in the bands view (341 producer sources + 57 bands) and 968 nodes in the albums view under the 1,000-node cap;
- initial `fit` so the whole network is visible before the user zooms;
- weaker many-body repulsion and shorter link distance than an ego graph, because the network has many hubs and leaves;
- label decluttering by zoom as described in 5.2;
- isolated producer nodes muted and hidden by the toggle in the albums view; in the bands view the isolated producer entities remain visible as shared band nodes;
- continuous infinite physics remains usable at the current scale; the overview preset is `manyBodyStrength=-45`, `linkDistance=42–90`, type collision 8/7/10, `collideStrength=0.6`, `alphaDecay=0.035` and `velocityDecay=0.55`.

Implementation constraints learned in T-009:

- d3-force must resolve link endpoints by canonical node id. The layout passes `linkId: (node) => node.id`; without it, d3-force uses the array index and throws `node not found: <uuid>`, which unmounts the React root and leaves a blank page.
- A physics failure must never escape the component. If the force layout cannot start, the canvas falls back to a static `breadthfirst` layout and freezes, keeping the page content and the accessible table available.

### 5.5 Filters

Ego graph filters operate on the loaded E8 subgraph:

- role: producer/all, co-producer;
- decade;
- taxonomy leaf/family represented in album metadata;
- selected producer/band/album context where applicable.

Global overview filters have two layers:

- server-side selection: producer limit/top-k, producer sort, decade and subgenre; the API can also omit isolated producers;
- client-side display filters: role, album decade/subgenre in the albums view, producer search/highlight and the isolated-producer toggle.

The global overview must expose:

- a visible toggle for isolated producers (default visible, toggle hides them);
- a producer search/highlight control;
- node and edge counts after the toggle and filters;
- a clear statement when the server truncated the network.

The UI must visibly state:

- filters apply to the loaded network;
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

E10 may add the additive read-only global overview endpoint, but must not add database schema changes or migrations, Tailwind, Plotly, a new graph renderer or writes.

**Verification:** dependency/route/scope inspection and migration check.

### FR-015 — Tests and documentation

The implementation must include unit/component tests for adapters, filters, controls, states, legend and fallback, plus a manual physics/performance checklist.

**Verification:** frontend checks and E10 docs.

### FR-016 — Global overview endpoint

The API must expose `GET /api/v1/graph/producers` with `view`, producer selection, filters, isolated-producer inclusion and global limits.

**Verification:** integration and OpenAPI tests.

### FR-017 — Global overview page

The web app must expose `/graph` with `Bands` and `Albums` views, primary navigation and URL state for selection and filters.

**Verification:** route, navigation and page tests.

### FR-018 — Shared-neighbor semantics

A band or album node must connect to every producer credited on it. The global view must not create direct producer–producer edges.

**Verification:** API and adapter tests with a shared band or album fixture.

### FR-019 — Global limits and truncation

The global overview must use a 1,000-node and 2,000-edge cap, show node/edge counts and expose `truncated=true` when the cap is reached.

**Verification:** limit, truncation and state tests.

### FR-020 — Isolated-producer toggle

The global bands view must include producers with no producer–band edges by default and provide a toggle that hides or shows them in the canvas, counts and table.

**Verification:** toggle and adapter tests.

### FR-021 — Global selection and drill-down

Selecting a producer, band or album must expose details and related producers/entities; a producer detail must link to its ego graph.

**Verification:** selection, details and navigation tests.

### FR-022 — Global tests and documentation

Global overview behavior must be covered by backend and frontend tests and documented in the API, frontend and E10 docs.

**Verification:** full checks and documentation review.

## 7. Non-functional requirements

### NFR-001 — Performance

A 500-node / 2,000-edge ego network and a 1,000-node / 2,000-edge global overview must remain usable. The simulation must be pausable and must not block navigation or the rest of the explorer.

### NFR-002 — Motion safety

Physics motion respects reduced-motion, pauses in hidden tabs and is never required to access data.

### NFR-003 — Accessibility

Keyboard-accessible controls, text labels, focus, legend, table fallback and non-color-only encodings are mandatory.

### NFR-004 — Determinism of data

Graph data and metrics remain deterministic per E7 run; layout positions are not persisted or treated as analytical facts.

### NFR-005 — Scope control

E10 may add the additive read-only global overview endpoint. E8 remains the bounded ego-graph contract. No schema migration or writes are allowed.

### NFR-006 — Maintainability

Graph mapping and physics configuration are isolated from page chrome and API clients.

### NFR-007 — Browser stability

Cytoscape cleanup must destroy the instance on unmount; no leaks across route changes.

### NFR-008 — Language

All labels, legends, controls and empty/error copy are in English.

### NFR-009 — Global scale

The global overview must load 398 unique nodes in the bands view (341 producer sources + 57 bands) and up to 968 nodes in the current albums view without blocking the page. Continuous infinite physics is used at this scale; if a future corpus makes it unusable, a finite settle with `Reheat` is acceptable and must be documented.

### NFR-010 — Global contract determinism

Global graph selection, ordering, caps and truncation must be deterministic per E7 run and documented. The endpoint must never return an unbounded graph.

## 8. Business rules

- **BR-001:** Producers are the graph center in both the global overview and ego graphs.
- **BR-002:** Album and band views are separate; no mixed canvas.
- **BR-003:** Force motion is presentation, not analytical evidence.
- **BR-004:** Filters apply to the loaded network, and truncation remains visible.
- **BR-005:** Missing nodes/edges are not negative evidence.
- **BR-006:** Color is never the only carrier of year, type or support.
- **BR-007:** Reduced-motion starts frozen.
- **BR-008:** No data mutation is part of E10. The only API change is the additive read-only overview endpoint.
- **BR-009:** The global overview is bounded; no unbounded full-corpus graph is loaded or rendered.
- **BR-010:** `cytoscape-d3-force` is the approved physics extension for E10.
- **BR-011:** A shared band or album node connects to every producer credited on it.
- **BR-012:** No direct producer–producer edges or inferred producer–producer projection are rendered in v1.
- **BR-013:** Isolated producers are visible by default and can be hidden with the global toggle.
- **BR-014:** Global selection and caps are server-side; role and album-metadata filters may be applied to the loaded network.
- **BR-015:** The producer ego graph remains available as a drill-down.

## 9. Edge cases and errors

- Producer with no graph: show a clear empty state and link back.
- Ego network with one node: render the node and a no-connections message.
- Global overview with no producers after filters: show an empty state with a clear reset action.
- Global all-producer bands view with isolated self-produced producers: show them muted by default; the toggle hides them.
- Shared band or album with multiple producers: render one node, one edge per producer and no direct producer–producer edge.
- API returns `truncated=true`: show a persistent truncation notice in the global overview and ego graph.
- Graph filter removes all visible nodes: show a filtered-empty state with clear action.
- No album year: grey node and “Year unknown” label.
- Self-produced producer: group/self-produced encoding; no self-loop.
- Very large labels: wrap/limit without breaking layout; global labels declutter by zoom.
- Simulation errors or canvas failure: show fallback table and a recoverable message.
- Route unmount: destroy simulation/listeners.
- Hidden tab: pause simulation.
- Reduced motion: freeze initial layout.

## 10. Out of scope

- An unbounded full-corpus graph or more than 1,000 nodes in the global overview.
- Direct producer–producer edges or a producer–producer projection.
- Mixed album/band canvases.
- Album–album or artist–artist graph views.
- Database schema changes or migrations.
- Graph editing, pinned layouts or persisted positions.
- Writes or data mutation.
- Playwright/load/accessibility audit, deployment and corpus expansion.
- Tailwind, Plotly or a component library.
- A producer–producer collaboration projection; shared band/album nodes are the only relationship encoding in v1.

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
| AC-014 | 500-node / 2,000-edge ego graph remains usable. | Manual performance check |
| AC-015 | No database schema/Tailwind/Plotly/new renderer changes occur; the global endpoint is additive and read-only. | Scope and migration inspection |
| AC-016 | Tests, lint, typecheck and build pass. | Local/CI evidence |
| AC-017 | Graph page documentation includes physics parameters and limits. | Docs review |
| AC-018 | Remote CI passes. | CI evidence |
| AC-019 | Ego-graph album titles are visible without hover or selection, and long titles remain readable. | Style test and browser check |
| AC-020 | A producer's neighbors spread around the canvas instead of bunching, with collision radii sized by node type. | Layout config test and browser check |
| AC-021 | The global bands view shows all current producers and bands in one canvas within 1,000 nodes and 2,000 edges. | API/page test and browser check |
| AC-022 | The global albums view loads all current producer–album nodes and edges under the 1,000-node cap, or truncates visibly. | API/page test and browser check |
| AC-023 | A shared band or album node connects to every credited producer and no direct producer–producer edge exists. | API/adapter tests with a shared fixture |
| AC-024 | Isolated producers are visible by default and the toggle hides/shows them in canvas, counts and table. | Toggle test |
| AC-025 | `/graph` is reachable from primary navigation and a producer can open its ego graph from the global view. | Route/navigation tests |
| AC-026 | Global node/edge selection exposes related producers and entity links, with an accessible table fallback. | Detail/accessibility tests |
| AC-027 | Global limits, truncation, filters and node/edge counts remain visible. | State tests |
| AC-028 | Global overview code paths have backend/frontend tests and documentation. | Full checks and docs review |
| AC-029 | A 1,000-node global overview remains usable or falls back to a documented finite settle. | Manual performance check |

## 12. Assumptions and resolved decisions

### Assumptions

- E8 graph endpoints remain stable for v0.1 and remain the ego-graph contract.
- `cytoscape-d3-force` is compatible with the installed Cytoscape 3.x line.
- The current corpus fits the global caps: 398 unique nodes / 426 edges in the bands view (341 producer sources + 57 bands; 43 isolated producer entities share band entities) and 968 nodes / 1,134 simple album edges (1,151 role rows) in the albums view.
- The global overview is the default entry point; ego networks remain available as drill-downs.
- Server-side selection is acceptable for global filtering; role and album-metadata display filters remain client-side.
- E11 will run Playwright/performance/a11y QA.

### Resolved decisions

| Decision | Resolution |
|---|---|
| Physics library | `cytoscape-d3-force` approved; transitive `d3-force` dependency. |
| Physics mode | Infinite force simulation by default; finite settle with reheat is allowed for the global scale if documented. |
| Reduced motion | Start frozen; physics opt-in. |
| Graph limits | Ego: 500 nodes / 2,000 edges. Global overview: 1,000 nodes / 2,000 edges. |
| Global default | `bands` view, all producers, producer sort by `album_count`, isolated producers visible. |
| Shared work semantics | One band or album node connected to every credited producer; no producer–producer edges. |
| Isolated producers | Visible by default; toggle hides producers with no producer–band edges. |
| Filter placement | Global selection server-side; role and album-metadata display filters over the loaded network. |
| Producer selection | `producer_limit=0` means all; optional bounded top-k by producer metrics. |
| Graph routes | Ego: `/producers/:producerId/graph?view=albums|bands`. Global: `/graph?view=albums|bands`. |
| Rendering | Cytoscape with force extension; no new renderer. |
| Force node identity | `linkId: (node) => node.id`; d3-force links carry canonical UUIDs, not array indices. |
| Neighbor spacing | Type-sized collision radii; ego uses stronger repulsion and 180–300 link distance. Global uses weaker repulsion and shorter links. |
| Labels | Ego album titles always visible. Global labels declutter by zoom; band labels remain visible and selected/searched labels always show. |
| Physics failure | Fall back to a frozen static layout; never propagate layout errors to the React tree. |
| Scope | Frontend plus the additive read-only `GET /api/v1/graph/producers` endpoint; no schema migration or writes. |

### Open questions

No blocking question remains for planning. Exact global force coefficients, finite-settle thresholds and top-k default presentation are plan-level details.

## 13. Validation result

- **Date:** 2026-11-11
- **Verdict:** Revision 7 is implemented locally and ready for validation. The global overview endpoint, `/graph` page, shared-neighbor semantics, overview physics, labels, filters and accessibility fallback are in place. Remote CI and the manual ego interaction/performance checks remain pending.
- **Backend:** 325 integration tests passed with `TEST_DATABASE_URL`; 220 unit tests passed with 105 integration tests skipped without it; Ruff and format passed. New tests cover the overview service, shared nodes, role deduplication, isolated handling, top-k, filters, caps, endpoint validation, OpenAPI paths and schemas.
- **Frontend:** lint, typecheck, 76 Vitest tests and the production build passed. Tests cover the overview client, adapter, page, navigation, controls, shared-node details, isolated toggle, truncation, empty/error states and overview physics presets.
- **Headless overview evidence:** 398 nodes / 426 edges in `bands` (341 producers + 57 bands, 43 isolated producer entities represented by their shared band nodes) and 968 nodes / 1,134 edges in `albums` (384 producers + 584 albums). Physics moved nodes, freeze/resume/reheat and dragging kept the page stable, the initial fit kept the network inside the canvas, search matched 5 producers, reduced motion started frozen with the table available, and shared-node selection listed all 32 producers for Motörhead. The albums isolated toggle reduced the network to 893 nodes / 951 edges and 341 producers.
- **Pending:** remote CI and the manual ego drag/500-node feel review.

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
