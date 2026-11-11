# Technical plan — SPEC-011 Producer graph visualization and interaction

- **Status:** Approved; implemented locally
- **Spec:** [spec.md](spec.md)
- **Tasks:** [tasks.md](tasks.md)
- **Stage:** E10
- **Modules:** `api`, `web`
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0006](../../docs/01-architecture/adr/ADR-0006-read-only-api.md), [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)

## 1. Solution summary

SPEC-011 revision 6 adds a global producer overview on `/graph`: many producers on one canvas, connected to their bands or albums. The revision 5 producer ego graph remains available at `/producers/:id/graph` as a drill-down.

Both scopes are producer-centric and split by view:

- `view=bands`: producer + band/artist nodes;
- `view=albums`: producer + album nodes.

A shared band or album is one node connected to every credited producer. There are no direct producer–producer edges in v1.

The global overview needs one additive read-only endpoint, `GET /api/v1/graph/producers`, backed by the persisted E7 graph layers. No database migration, canonical-data change or new dependency is required. The ego graph continues to use the existing E8 endpoint unchanged.

```text
E7 graph layers ──┬─► E8 ego endpoint ──────► /producers/:id/graph
                  │                              (one producer)
                  └─► overview endpoint ─────► /graph
                                                 (many producers)
        Cytoscape + cytoscape-d3-force
        separate albums / bands views
        shared band/album neighbors
        isolated-producer toggle · filters
        legend · details · accessible table
```

## 2. Architecture and data flow

### 2.1 Global overview flow

1. `/graph` reads `view`, producer selection, sort, decade, subgenre and selected entity from the URL.
2. TanStack Query requests `/api/v1/graph/producers` with the active run and limits.
3. The adapter validates node types, maps nodes/edges to Cytoscape elements and builds table/detail data.
4. The graph component applies the overview force preset and renders the network.
5. The isolated-producer toggle, role filter and album metadata filters update the loaded network without another request.
6. Selecting a producer exposes metrics, community and neighbors; selecting a band/album lists all connected producers.
7. A producer detail links to `/producers/:id/graph`; the ego graph remains unchanged.
8. Unmount stops the simulation and destroys the Cytoscape instance.

### 2.2 Ego flow

The revision 5 flow remains: `/producers/:id/graph` reads `view`, `limit` and `depth`, requests `/api/v1/producers/{id}/graph`, maps the bounded response and runs the ego force preset.

### 2.3 File layout

```text
backend/src/hmde/
├── api/routes/graph.py
├── main.py
├── schemas/api.py
└── services/producers.py

frontend/src/
├── api/producerGraph.ts
├── api/queryKeys.ts
├── components/ProducerGraph.tsx
├── components/GraphControls.tsx
├── components/GraphLegend.tsx
├── components/GraphDetails.tsx
├── components/GraphFallbackTable.tsx
├── components/ProducerOverviewControls.tsx
├── graph/adapter.ts
├── graph/styles.ts
├── pages/ProducerOverviewPage.tsx
├── pages/ProducerGraphPage.tsx
└── graph/*.test.ts
```

`cytoscape-d3-force` remains registered once at module scope. Shared presentational components are reused; the overview adds a page, controls and an adapter path rather than a second renderer.

## 3. Backend design

### 3.1 Endpoint

```http
GET /api/v1/graph/producers
```

Query parameters:

| Parameter | Default | Rules |
|---|---|---|
| `view` | `bands` | `bands` or `albums` |
| `producer_limit` | `0` | `0` = all; positive value = top-k |
| `producer_sort` | `album_count` | `album_count`, `band_count`, `betweenness`, `name` |
| `order` | `desc` | `asc` or `desc` |
| `decade` | none | `^\d{4}s$` |
| `subgenre` | none | max 50 characters |
| `include_isolated` | `true` | omit producers with no edges in the selected layer |
| `include_evidence` | `false` | bounded edge evidence |
| `max_nodes` | `1000` | 1–1,000 |
| `max_edges` | `2000` | 1–2,000 |
| `analysis_run` | active | existing `get_analysis_run` dependency |

The route lives in `api/routes/graph.py` with prefix `/api/v1/graph` and tag `graph`. It is registered in `main.py`.

### 3.2 Service

Add `get_producer_overview_graph` to `services/producers.py`:

1. Select artist graph nodes with the `producer` role.
2. Reuse the ranking/filter logic behind `list_producers` so `decade` and `subgenre` select producers through their album credits.
3. Sort by the persisted producer metrics (`NA-PROD-001`, `NA-PROD-002`, `NA-BET-001`) or name.
4. Apply `producer_limit` after sorting; `0` keeps all matched producers.
5. Load `producer_band` or `producer_album` edges for the selected producer graph-node ids.
6. In the albums view, apply `decade`/`subgenre` to album target nodes as well as producer eligibility. In the bands view, the filters only select producers because band nodes carry no temporal or taxonomy metadata.
7. Group album role rows by `(producer, target)` so a producer with both producer and co-producer roles has one overview edge; use the single role or `mixed`, and keep the source role codes in edge evidence.
8. Keep selected producers plus their target nodes. If `include_isolated=false`, drop producers with no edges in the selected layer.
9. Apply `max_nodes` and `max_edges` deterministically: ranked producers first, then edges by weight descending, then canonical source/target ids. Set `truncated=true` when anything is dropped.
10. Enrich producer nodes in `attributes` with `album_count`, `band_count`, `betweenness` and `community_key`.
11. Reuse `_node_payload` and `_edge_payload` for node/edge shape.

The query should use the existing `GraphNode` and `GraphEdge` models. No new table, migration or persisted artifact is needed.

### 3.3 Schemas

Add to `schemas/api.py`:

```python
class ProducerOverviewGraphLimits(BaseModel):
    producer_limit: int
    max_nodes: int
    max_edges: int


class ProducerOverviewGraphMeta(BaseModel):
    scope: Literal["overview"]
    view: Literal["albums", "bands"]
    analysis_run_id: UUID
    analysis_version: str
    dataset_version: str
    taxonomy_version: str
    graph_version: str
    truncated: bool
    matched_producers: int
    selected_producers: int
    include_isolated: bool
    limits: ProducerOverviewGraphLimits


class ProducerOverviewGraphResponse(BaseModel):
    nodes: list[ProducerGraphNode]
    edges: list[ProducerGraphEdge]
    meta: ProducerOverviewGraphMeta
```

Existing `ProducerGraphNode` and `ProducerGraphEdge` are reused, so OpenAPI and TypeScript generation stay small.

### 3.4 Shared-neighbor behavior

The graph is bipartite by layer:

- a band node has edges to all producers credited on that band;
- an album node has edges to all producers credited on that album;
- the node appears once;
- no producer–producer edge is synthesized.

The adapter and details panel derive "related producers" from the shared node's incident edges.

## 4. Frontend design

### 4.1 Routes and navigation

- Add `/graph` in `App.tsx`.
- Add a `Graph` item to the primary navigation.
- Add an `Open producer network` link on `/producers` and producer detail.
- Keep `/producers/:id/graph` and its `Open graph` link.
- A selected producer in `/graph` gets an `Open ego graph` link.

### 4.2 URL contract

```text
/graph?view=bands&producers=all&sort=album_count&order=desc&isolated=1&selected=<entityId>
```

- `view`: `bands` default, `albums` alternative.
- `producers`: `all` default; a positive integer selects top-k.
- `sort`: `album_count` default; `band_count`, `betweenness`, `name`.
- `order`: `desc` default.
- `decade`, `subgenre`: optional.
- `isolated`: `1` default; `0` hides isolated producers.
- `selected`: optional entity id for details.

### 4.3 API client and adapter

- Add `getProducerOverviewGraph` and an overview query key to `api/producerGraph.ts` / `queryKeys.ts`.
- Add `adaptOverviewGraph` to `graph/adapter.ts`:
  - validate `view` and node types;
  - map producer/band/album nodes and edges;
  - merge overview producer metrics into attributes;
  - compute degree-based node sizes and incident-producer lists for shared nodes;
  - build details and fallback table data;
  - expose counts after display filters.
- Keep `adaptGraph` for the ego response.

### 4.4 Page and components

- `ProducerOverviewPage.tsx`: URL state, query, loading/error/empty/truncated states, controls, canvas, details and table.
- `ProducerOverviewControls.tsx`: view tabs, producer selection/sort, decade/subgenre, isolated toggle and physics controls.
- `ProducerGraph.tsx`: accept a `variant` or force preset so the same Cytoscape lifecycle serves ego and overview.
- Reuse `GraphLegend`, `GraphDetails`, `GraphFallbackTable` and the physics control buttons.
- Details:
  - producer: album/band counts, betweenness, community, ego link;
  - band/album: incident producer list and links to their ego graphs.
- The accessible table follows the same view, filters and isolated toggle.

## 5. Physics

### 5.1 Shared lifecycle

- Keep the existing `linkId: (node) => node.id` requirement.
- Freeze, resume and reheat remain available.
- Pause when the document is hidden.
- Start frozen under `prefers-reduced-motion`.
- Guard force startup and fall back to a frozen static layout.
- Destroy Cytoscape and listeners on unmount.

### 5.2 Ego preset

Keep the revision 5 values: type-sized collision radii, `collideStrength: 0.9`, `collideIterations: 2`, `manyBodyStrength: -320` and a node-count-based link distance (180–300).

### 5.3 Overview preset

- Tune for 398 unique nodes in the bands view (341 producer sources + 57 bands) and 968 nodes in the albums view.
- `fit: true` or an explicit initial fit so the network appears whole. The implementation fits immediately and again after 1.2 s.
- Weaker many-body repulsion and shorter links than the ego preset.
- Node size from filtered degree.
- Collision radii remain type-sized but smaller than the ego preset.
- Infinite physics is usable at the current scale. The implemented preset is `manyBodyStrength=-45`, `linkDistance=42–90`, producer/album/band collision 8/7/10, `collideStrength=0.6`, `collideIterations=1`, `alphaDecay=0.035` and `velocityDecay=0.55`; a finite settle with `Reheat` remains the fallback for a future corpus.

## 6. Visual mapping and labels

| Element | Encoding |
|---|---|
| Producer person | Circle, oxide |
| Producer group/self-produced | Hexagon, brass |
| Producer unknown | Circle, grey |
| Album | Square, year color scale |
| Band/artist | Rounded rectangle, neutral petrol |
| Isolated producer | Muted producer style |
| Missing year | Grey |
| Producer edge | Solid |
| Co-producer edge | Dashed |
| Support | Width/opacity |
| Producer–band weight | Width |

Ego graph album titles stay always visible. Global overview labels declutter by zoom:

- band labels visible;
- producer labels on zoom/search/selection;
- album labels at a readable zoom; selected/searched labels always visible;
- long labels wrap with a subtle background.

The legend and details expose the same encodings outside the canvas.

## 7. Filters and counts

- Global producer selection/sort/decade/subgenre are server-side.
- The isolated toggle is client-side over the loaded overview so it is immediate; the API also supports `include_isolated=false`.
- Role filtering uses edge role and `evidence.role_mix`.
- Album decade/taxonomy filters apply in the albums view.
- Band view disables album-metadata filters with an explanation.
- Node and edge counts reflect the active filters and toggle.
- `truncated=true` remains visible.

## 8. Accessibility

- Canvas has an accessible name.
- Visible legend and details outside the canvas.
- Table fallback lists all visible nodes and edges and follows the toggle.
- Physics and filter controls are real buttons/inputs with state and focus.
- Keyboard users can reach controls, details and table without the canvas.
- Reduced motion starts frozen.
- Color is never the only encoding.

## 9. Error handling

- Invalid view: fall back to `bands` with a message.
- Invalid analysis run: existing API 404.
- No completed run: existing API 503.
- Empty overview after filters: clear state with reset action.
- Truncated overview: persistent notice.
- Canvas or physics failure: keep the page, details and table; show recoverable message.
- Ego producer 404: existing producer-not-found state.
- Unmount: destroy layout, Cytoscape and listeners.

## 10. Testing strategy

| Level | What is tested | Evidence |
|---|---|---|
| Backend unit/integration | Producer selection, ordering, view mapping, shared-neighbor edges, isolated toggle, caps/truncation, run metadata, OpenAPI paths/schemas. | `backend/tests/integration/test_api_producer_overview_graph.py`, `test_openapi.py` |
| Frontend unit | Overview adapter mapping, shared-node incident producers, counts, filters, year scale, table data. | `frontend/src/graph/*.test.ts` |
| Frontend component | Overview page states, controls, toggle, details, legend, fallback and navigation. | RTL tests |
| Physics | Overview preset options, `linkId`, failure fallback and cleanup with mocks. | Component tests |
| Manual | Global fit/labels, isolated toggle, shared-node selection, drag/freeze/reheat, 398/968-node usability, reduced motion. | E10 checklist |
| Build/CI | Backend Ruff/format/pytest; frontend lint/typecheck/test/build; remote CI. | Commands/GitHub Actions |

Commands:

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
```

Integration tests require `TEST_DATABASE_URL` and the `hmde_test` database.

## 11. Performance and limits

- Ego: 500 nodes / 2,000 edges; defaults 20 neighbors, depth 1.
- Global: 1,000 nodes / 2,000 edges.
- Current corpus: 398 unique nodes / 426 edges in bands (341 producer sources + 57 bands; 43 isolated producer entities share band entities); 968 nodes / 1,134 simple edges (1,151 role rows) in albums. Hiding isolated producer nodes in the albums view leaves 893 nodes / 951 edges.
- `producer_limit=0` means all; top-k remains available for future corpora.
- Deterministic truncation by rank, weight and ids.
- Labels declutter by zoom; no all-album label wall.
- Physics pauses when hidden; finite settle is the fallback.
- No simulation in tests; mock Cytoscape/d3-force.

## 12. Dependencies

- No new backend or frontend dependency.
- `cytoscape-d3-force@1.1.4` and transitive `d3-force` remain the approved physics stack.
- No database migration.
- No Tailwind, Plotly or new renderer.

## 13. Documentation impact

- `docs/03-data/api-v1.md`: global overview endpoint and parameters.
- `docs/01-architecture/frontend.md`: `/graph`, global/ego scopes, labels and physics presets.
- `docs/00-vision/roadmap.md`: E10 global overview scope.
- `README.md`, `AGENTS.md`, `docs/README.md`, `specs/README.md`: routes and current state.
- SPEC-011 plan/tasks/spec evidence.
- E8/E9 contracts remain unchanged.

## 14. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Global hairball | Separate views, shared-neighbor encoding, degree sizing, labels by zoom, filters. |
| 968-node physics unusable | Overview preset; finite settle + reheat fallback. |
| API responses become unbounded | 1,000/2,000 caps, top-k and deterministic truncation. |
| Producer selection surprises | Explicit sort/counts and visible controls; `all` default. |
| Isolated producers clutter the canvas | Muted style and immediate toggle. |
| Shared nodes misread as producer–producer links | Details list incident producers and state the shared-work rule. |
| Band-view filters lack metadata | Disable album filters in band view with explanation. |
| Client filters mislead after truncation | Persistent truncation notice and loaded-network wording. |
| Scope creep into graph editing | Read-only endpoint, no writes, no persisted positions. |
| Canvas inaccessible | Table fallback, details, keyboard controls and legend. |

## 15. Traceability requirements → plan → tasks

| Requirement | Plan section | Tasks |
|---|---|---|
| FR-001 | 4.1 | T-002, T-014 |
| FR-002 | 3.2, 4.3 | T-002, T-013 |
| FR-003 | 4.2, 11 | T-002, T-011 |
| FR-004 | 5 | T-003, T-015 |
| FR-005 | 5.1 | T-003, T-015 |
| FR-006 | 5.1 | T-003, T-014 |
| FR-007 | 6 | T-004, T-013, T-015 |
| FR-008 | 7 | T-004, T-014 |
| FR-009 | 4.4, 6 | T-004, T-014 |
| FR-010 | 8 | T-006, T-014 |
| FR-011 | 9 | T-005, T-014 |
| FR-012 | 5.1 | T-003, T-015 |
| FR-013 | 5.1 | T-003, T-015 |
| FR-014 | 1, 12 | T-012, T-016 |
| FR-015 | 10, 13 | T-015, T-016 |
| FR-016 | 3 | T-011, T-012 |
| FR-017 | 4.1, 4.2 | T-014 |
| FR-018 | 3.4, 4.3 | T-011, T-013 |
| FR-019 | 3.2, 11 | T-011, T-014 |
| FR-020 | 3.1, 7 | T-011, T-014 |
| FR-021 | 4.4 | T-014 |
| FR-022 | 10, 13 | T-012, T-015, T-016 |

| Non-functional requirement | Plan section | Tasks |
|---|---|---|
| NFR-001 | 5, 11 | T-015 |
| NFR-002 | 5.1, 8 | T-015 |
| NFR-003 | 8 | T-014 |
| NFR-004 | 3, 5 | T-011, T-015 |
| NFR-005 | 1, 12 | T-012, T-016 |
| NFR-006 | 2.3, 4 | T-013, T-014 |
| NFR-007 | 5.1, 9 | T-015 |
| NFR-008 | 6, 9 | T-014 |
| NFR-009 | 5.3, 11 | T-015 |
| NFR-010 | 3.1, 3.2, 11 | T-011, T-012 |

## 16. Approval and next step

T-011–T-016 are implemented locally. The overview service and endpoint are behind the existing E7 layers; the `/graph` page, physics preset and documentation are in place. Remote CI and the manual ego interaction/performance review remain pending.
