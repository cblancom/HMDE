# Technical plan — SPEC-013 Graph overview layout modes

- **Status:** Approved; implemented locally
- **Spec:** [spec.md](spec.md)
- **Tasks:** [tasks.md](tasks.md)
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0006](../../docs/01-architecture/adr/ADR-0006-read-only-api.md), [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)
- **Modules:** `api`, `web`

## 1. Solution summary

Add two server-generated static layout modes to the global producer overview:

- **Bipartite:** NetworkX `bipartite_layout` with producers on the left and bands/albums on the right.
- **Community:** a deterministic cluster layout built from the existing E7 Louvain `community_key`, a contracted community graph positioned with NetworkX `spring_layout`, and members placed around community centers.

The frontend keeps `Force` as the default. A compact `Layout` select in the overview controls stores `layout=force|bipartite|community` in the URL. For static modes, the overview request includes the layout parameter, the API returns optional coordinates, the adapter attaches positions to Cytoscape elements, and the graph applies a fitted preset without starting d3-force. Freeze/Resume/Reheat are disabled with a `Static layout` status.

No community detection is rerun. No database table, migration, new dependency or ego-graph change is included.

## 2. Architecture and data flow

```text
Layout select ──► URL layout=force|bipartite|community
                         │
                         ▼
              getProducerOverviewGraph(layout?)
                         │
                         ▼
            /api/v1/graph/producers?layout=…
                         │
        ┌────────────────┴─────────────────┐
        │                                  │
 layout absent                         layout present
        │                                  │
        ▼                                  ▼
 current graph response            graph + optional layout block
        │                                  │
        ▼                                  ▼
 d3-force (current)                 adapter positions
                                           │
                                           ▼
                                  Cytoscape preset + fit
                                  static controls disabled
```

The server applies selection, filters and caps first, then computes coordinates for exactly the nodes/edges that will be returned.

## 3. Components and responsibilities

| Component or path | Responsibility |
|---|---|
| `backend/src/hmde/services/graph_layouts.py` (new) | Pure NetworkX bipartite and community layout functions, normalization and fallbacks. |
| `backend/src/hmde/services/producers.py` | Pass selected graph data and community mapping to the layout functions; omit layout on failure. |
| `backend/src/hmde/schemas/api.py` | Add optional layout response schemas. |
| `backend/src/hmde/api/routes/graph.py` | Add the optional `layout` query parameter. |
| `backend/tests/unit/test_graph_layouts.py` (new) | Deterministic algorithm tests. |
| `backend/tests/integration/test_api_producer_overview_graph.py` | Layout parameter/response/fallback tests. |
| `backend/tests/unit/test_openapi.py` | Schema/path presence. |
| `frontend/src/api/producerGraph.ts`, `queryKeys.ts` | Layout option, generated types and query key. |
| `frontend/src/graph/adapter.ts` | Validate and attach layout coordinates; expose the static algorithm. |
| `frontend/src/components/ProducerOverviewControls.tsx` | Layout selector. |
| `frontend/src/pages/ProducerOverviewPage.tsx` | URL/query state and layout selection. |
| `frontend/src/components/ProducerGraph.tsx` | Static preset path, fit, disabled physics controls and status. |
| `frontend/src/**/*.test.ts(x)` | Backend-facing adapter/page/component coverage. |

## 4. Technical decisions and alternatives

### 4.1 Bipartite layout

Use `networkx.bipartite_layout` over the selected graph:

- top node set: producer graph nodes;
- all other selected nodes: bands/albums;
- `align="vertical"` so producers and targets form left/right columns;
- scale chosen so the resulting rows are legible after frontend fit.

The endpoint outputs coordinates keyed by entity UUID for every returned node. Nodes are added in sorted order to keep the row order deterministic.

NetworkX can raise `AmbiguousSolution` for disconnected bipartite graphs. The implementation catches that case and uses a deterministic two-column fallback:

- producers in column `x = 0`;
- targets in column `x = 1`;
- y positions distributed evenly in sorted node order.

Both outputs are normalized into a `1000 × 1000` coordinate box.

**Alternative:** use `cytoscape-d3-force` x/y forces. Rejected by the owner in favor of NetworkX `bipartite_layout`.

### 4.2 Community layout

Reuse the E7 Louvain partition persisted in `community` and `community_membership`. The overview service already builds a community map for producer nodes; pass it into the layout helper.

Steps:

1. Build `community_by_entity` for producer nodes.
2. Add `unassigned` for producers without a community.
3. Assign each target band/album to the community with the most incident producers; tie-break by community key.
4. Build a contracted community graph:
   - one node per community;
   - for each target connected to producers from multiple communities, increment the pair weight;
   - isolated communities remain nodes.
5. Position community centers with `nx.spring_layout(contracted, seed=42, weight="weight")`. A single community is centered at the origin.
6. Place members around each center deterministically:
   - producers on an inner ring;
   - bands/albums on an outer ring;
   - radius grows with `sqrt(member_count)` and is bounded to avoid unbounded overlap;
   - sort members by label/id before placement.
7. Normalize all coordinates into the same `1000 × 1000` box.

The layout is deterministic for a given run, view and selected node set. Shared nodes assigned to one community remain connected by cross-cluster edges, making inter-community links visible.

**Alternative:** a grid of communities. Rejected because it ignores inter-community relationships that the contracted spring layout captures.

**Alternative:** run a new community detection on the displayed bipartite graph. Out of scope; the spec reuses E7 communities.

### 4.3 API contract

Extend the existing endpoint:

```http
GET /api/v1/graph/producers?layout=bipartite|community
```

Add to `schemas/api.py`:

```python
class ProducerOverviewGraphLayoutNode(BaseModel):
    id: UUID
    x: float
    y: float


class ProducerOverviewGraphLayout(BaseModel):
    algorithm: Literal["bipartite", "community"]
    nodes: list[ProducerOverviewGraphLayoutNode]
```

`ProducerOverviewGraphResponse` gains:

```python
layout: ProducerOverviewGraphLayout | None = None
```

Rules:

- `layout` absent: current response and Force behavior.
- `layout=bipartite|community`: coordinates for every returned node.
- layout computation failure: return the normal graph with `layout=None`; do not fail the request.
- no database migration, no persisted layout, no write.

OpenAPI and generated TypeScript types change additively.

**Alternative:** a separate `/graph/layout` endpoint. Rejected: it duplicates selection/filter logic and adds a second request for the same node set.

### 4.4 Frontend flow

- Add `layout: 'force' | 'bipartite' | 'community'` to the overview URL state; Force is omitted from the URL.
- Add a `Layout` select to `ProducerOverviewControls`.
- Include layout in the overview query key and request:
  - `force`: no `layout` parameter;
  - `bipartite`/`community`: send the parameter.
- `adaptOverviewGraph` validates the layout block:
  - every returned node id has exactly one coordinate;
  - coordinates are finite numbers;
  - otherwise the layout is ignored.
- Node element definitions include `position` when coordinates exist.
- `ProducerGraph`:
  - if the adapted graph has a layout, create Cytoscape with the positions, apply a fitted preset, set `Static layout`, and do not start d3-force;
  - disable Freeze/Resume/Reheat in static mode;
  - if the graph has no layout, keep the current Force behavior;
  - keep selection, details, search, accessible table and `ResizeObserver`.
- If the requested mode has no valid coordinates, use Force and show a non-blocking notice.

### 4.5 Filter interaction

Server filters and view changes are part of the overview query and therefore recompute the layout. Client-only display filters (role, search and isolated toggle) do not trigger a layout recomputation; they hide loaded nodes. The static positions remain stable. This limitation is documented in the UI note and the frontend docs.

## 5. Data model and migrations

No changes. Layout coordinates are generated per request and returned in the API response. No persisted layout table or Alembic migration.

## 6. API contract details

- New optional query parameter: `layout` (`bipartite` or `community`).
- Invalid value returns `422` through FastAPI validation.
- Existing filters, producer limits and caps remain in force.
- Layout coordinates are keyed by the canonical entity UUID used by graph nodes.
- The response remains read-only and bounded.

## 7. Frontend impact

- `/graph` only; ego graph unchanged.
- URL: `layout=force|bipartite|community`.
- Query cache key includes layout.
- Static mode:
  - fits the graph;
  - disables physics buttons;
  - status text `Static layout`;
  - selection/details/search/table remain active;
  - panel and rail resizing continue to work.
- Force mode remains the default and full physics path.
- No community coloring or hulls in this iteration.

## 8. Error handling and consistency

- Layout computation error: backend returns graph without layout; frontend falls back to Force and shows a notice.
- Missing/duplicate coordinates: adapter rejects the layout; Force fallback.
- Disconnected bipartite graph: deterministic two-column fallback.
- No communities: all nodes go to `unassigned`.
- Target with no producer community: `unassigned`.
- Truncated graph: coordinates cover only returned nodes; truncation remains visible.
- Static layout while filters hide nodes: positions are stable; visible nodes keep their coordinates.
- Switching back to Force re-runs the existing force preset.

## 9. Security and trust boundaries

No change. Endpoints remain public and read-only. Layout computation uses server-side NetworkX and bounded graph data. No user input beyond the validated layout value and existing filters.

## 10. Observability

No new persisted records or metrics. Layout errors are caught and logged at the API layer without exposing internals. Existing analysis-run metadata remains in the response.

## 11. Testing strategy

| Level | What is tested | Evidence |
|---|---|---|
| Backend unit | Bipartite coordinates, left/right ordering, disconnected fallback, determinism | `backend/tests/unit/test_graph_layouts.py` |
| Backend unit | Community majority assignment, unassigned nodes, cluster determinism, single community | `backend/tests/unit/test_graph_layouts.py` |
| Backend integration | `layout` parameter, optional response block, absent layout, failure fallback, OpenAPI | `backend/tests/integration/test_api_producer_overview_graph.py`, `test_openapi.py` |
| Frontend adapter | Coordinate validation, positions in elements, static algorithm flag, fallback | `frontend/src/graph/adapter.test.ts` |
| Frontend page/component | Selector URL/query, Force behavior, static controls/status, fallback notice | `ProducerOverviewPage.test.tsx`, `ProducerOverviewControls.test.tsx`, `ProducerGraph.test.tsx` |
| Headless | Layout application, fit, static controls, 398/968-node performance, no console errors | Chromium probes/screenshots |

Exact commands:

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run pytest

cd ../frontend
npm run generate:api
npm run lint
npm run typecheck
npm run test
npm run build

cd ..
docker compose config -q
```

## 12. Deployment and reversibility

Backend and frontend can ship together. The API change is additive; older clients see the existing response when `layout` is absent. No migration or data cleanup is needed. Reverting the code removes the modes and leaves the Force graph.

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Bipartite lines are extremely long for 968 nodes. | Normalize, fit, tune scale and verify screenshots; fallback remains available. |
| Community clusters overlap with 78 communities. | Tune `spring_layout` scale, cluster radii and member rings with headless checks. |
| NetworkX layout is slow at full corpus size. | Compute only after caps; benchmark in headless tests; cache the response via TanStack Query. |
| Static controls confuse users. | Explicit `Static layout` status and disabled physics buttons; Force is one selector away. |
| Layout coordinates missing or incomplete. | Adapter validates all node ids and falls back to Force with a notice. |
| Client-only filters hide nodes used for layout. | Document that layout uses the server-selected network; positions remain stable. |

## 14. Traceability requirements → plan → tasks

| Requirement | Plan section | Tasks |
|---|---|---|
| FR-001 | 4.4 | T-004 |
| FR-002 | 4.1 | T-001, T-002 |
| FR-003 | 4.2 | T-001, T-002 |
| FR-004 | 4.3 | T-002 |
| FR-005 | 4.4 | T-003, T-004 |
| FR-006 | 4.4 | T-003, T-004 |
| FR-007 | 4.5 | T-004 |
| FR-008 | 4.1, 4.2, 8 | T-001, T-003 |
| FR-009 | 1, 7 | T-004, T-005 |
| NFR-001 | 4.1, 4.2 | T-001 |
| NFR-002 | 4.3, 13 | T-001, T-002, T-005 |
| NFR-003 | 1, 5, 6 | T-002, T-005 |
| NFR-004 | 4.4, 7 | T-003, T-004, T-005 |

## 15. Approval and next step

T-001–T-005 are implemented locally. The NetworkX layouts, API coordinates, selector and static controls passed the automated suite and headless Chromium checks. Remote CI remains pending.
