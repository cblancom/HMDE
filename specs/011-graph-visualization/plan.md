# Technical plan — SPEC-011 Producer graph visualization and interaction

- **Status:** Approved
- **Spec:** [spec.md](spec.md)
- **Tasks:** [tasks.md](tasks.md)
- **Stage:** E10
- **Module:** `web`
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0006](../../docs/01-architecture/adr/ADR-0006-read-only-api.md), [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)

## 1. Solution summary

SPEC-011 adds a producer graph page to the E9 explorer. It consumes the existing bounded E8 graph endpoint, maps nodes and edges into Cytoscape, and adds live force physics through the approved `cytoscape-d3-force` extension.

The graph is deliberately producer-centric and split by view:

- `view=albums`: producer + album nodes;
- `view=bands`: producer + band/artist nodes.

No backend, API, schema or data changes are required. The page uses E9 API clients, run metadata and the studio-ledger visual system. A selected producer is the seed; top-k selection happens through the existing producer ranking.

```text
Producer detail ──► /producers/:id/graph
                          │
                          ▼
                 E8 bounded graph response
                          │
                          ▼
                 graph adapter + filters
                          │
          ┌───────────────┼────────────────┐
          ▼               ▼                ▼
      Cytoscape       controls/legend   accessible table
      d3-force        details panel     + state messages
```

## 2. Architecture and data flow

### 2.1 Page flow

1. `/producers/:producerId/graph` reads `view`, `limit` and `depth` from the URL.
2. TanStack Query requests `/api/v1/producers/{id}/graph` with `include_evidence=true`.
3. The adapter validates and maps nodes/edges to Cytoscape elements and filter metadata.
4. The graph component initializes Cytoscape, registers `cytoscape-d3-force`, and starts the force simulation.
5. Selection and filters update the details/fallback views without another API request.
6. Unmount stops the simulation and destroys the Cytoscape instance.

### 2.2 Frontend layout

```text
frontend/src/
├── api/producerGraph.ts
├── components/ProducerGraph.tsx
├── components/GraphControls.tsx
├── components/GraphLegend.tsx
├── components/GraphDetails.tsx
├── components/GraphFallbackTable.tsx
├── graph/adapter.ts
├── graph/styles.ts
├── pages/ProducerGraphPage.tsx
└── graph/*.test.ts
```

`cytoscape-d3-force` is registered once at module scope. The graph canvas is isolated from route chrome and API clients.

## 3. Technical decisions

### 3.1 Physics: `cytoscape-d3-force`

Approved dependency:

```json
"cytoscape-d3-force": "1.1.4"
```

It brings `d3-force` transitively. No other graph renderer is added.

Configuration baseline:

```ts
{
  name: 'd3-force',
  infinite: true,
  fixedAfterDragging: false,
  ungrabifyWhileSimulating: false,
  animate: true,
  fit: false,
  padding: 40,
  randomize: false,
  alpha: 1,
  alphaMin: 0.001,
  alphaDecay: 0.0228,
  velocityDecay: 0.4,
  collideRadius: (node) => node.type === 'band' ? 34 : node.type === 'album' ? 28 : 22,
  collideStrength: 0.9,
  collideIterations: 2,
  manyBodyStrength: -320,
  linkDistance: 'max(120, min(clamp(180, 70 + nodeCount * 11, 300), canvasHeight / 2 - 60))',
  linkId: (node) => node.id,
}
```

`linkDistance` is computed from the loaded node count and capped by the canvas height (minimum 120) so small ego networks still use the canvas and larger ones keep labels apart without clipping. `linkId` is mandatory: edges carry canonical node UUIDs, while d3-force otherwise assumes array indices and throws `node not found: <uuid>`.

The exact force coefficients are tuned during implementation against a selected ego network. They are recorded in the page docs.

Alternative rejected: static Cytoscape layout. It does not meet the requested physical-drag feel.

Alternative rejected: replacing Cytoscape with a new renderer. It would duplicate pan/zoom/selection/accessibility work and increase scope.

### 3.2 Physics lifecycle

- Keep a reference to the active layout.
- `Freeze layout`: `layout.stop()`, keep node positions.
- `Resume physics`: rerun the layout from current positions.
- `Reheat`: stop, recreate/restart with `alpha: 1`, keeping or randomizing positions as documented.
- Pause simulation on `document.visibilitychange` when hidden.
- `prefers-reduced-motion`: start frozen with a deterministic initial layout; physics is opt-in.
- Guard layout startup: catch force-layout errors, apply a frozen static `breadthfirst` layout and keep the page and table fallback visible instead of unmounting React.
- Always destroy Cytoscape and remove listeners on unmount.

### 3.3 View mapping

`view=albums`:

- Node types: `producer`, `album`.
- Album year/taxonomy/band metadata from node attributes.
- Edges: producer–album role and support.

`view=bands`:

- Node types: `producer`, `band`.
- Edges: producer–band weight and album evidence.
- Self-produced producer remains a producer node; no self-loop.

The adapter rejects mixed views and returns an explicit error state if the API response contains the wrong node types.

### 3.4 Client-side filters

E8 has no server-side graph filters in v0.1. Filters are applied to the loaded subgraph:

- Role filter uses edge role; for band edges, `evidence.role_mix`.
- Decade filter applies exactly in album view from album node year.
- Taxonomy filter applies exactly in album view from album node primary/secondary codes.
- Band view uses role filters and available evidence; decade/taxonomy controls are disabled with an explanation because E8 band nodes do not carry album taxonomy/year metadata.
- If `meta.truncated` is true, a persistent notice explains that filters apply to the loaded subset.

This limitation is deliberate for E10 v1 and documented in the page.

### 3.5 Top-k and graph scope

- Producer selection comes from the existing `/producers` ranking.
- E10 v1 opens one producer ego network.
- No full graph is rendered.
- No top-k graph endpoint is added.
- E8 limits remain: 100 selection limit, depth 2, 500 nodes, 2,000 edges.

### 3.6 Visual mapping

| Element | Encoding |
|---|---|
| Producer person | Circle, oxide |
| Producer group/self-produced | Hexagon, brass |
| Producer unknown | Circle, grey |
| Album | Square, year color scale |
| Band/artist | Rounded rectangle, neutral petrol |
| Missing year | Grey |
| Producer edge | Solid |
| Co-producer edge | Dashed |
| Support | Width/opacity |
| Producer–band weight | Width |

Album titles are always shown below the node, with wrapping and a subtle background for readability; selection adds a border and details. Producer and band labels were already visible by default. Collision spacing and the taller canvas keep the label wall manageable within the 500-node cap.

### 3.7 Accessibility

- Canvas has an accessible name and a visible legend.
- A table fallback lists all loaded nodes and edges.
- Node/edge details are rendered outside the canvas.
- Physics controls are real buttons with state.
- Reduced motion starts frozen.
- Keyboard can reach controls and table; the canvas is an enhancement, not the only access path.
- Color is never the only channel for year/type/support.

## 4. Components and responsibilities

| Component | Responsibility |
|---|---|
| `api/producerGraph.ts` | Typed E8 graph request and query key. |
| `graph/adapter.ts` | Validate views, map nodes/edges, apply filters, produce table data. |
| `graph/styles.ts` | Cytoscape selectors, year scale and visual classes. |
| `components/ProducerGraph.tsx` | Cytoscape lifecycle, d3-force, drag/selection events. |
| `components/GraphControls.tsx` | View tabs, limit/depth controls and freeze/resume/reheat. |
| `components/GraphLegend.tsx` | Shape/color/line legend. |
| `components/GraphDetails.tsx` | Selected node/edge evidence. |
| `components/GraphFallbackTable.tsx` | Accessible nodes/edges tables. |
| `pages/ProducerGraphPage.tsx` | URL state, queries, filters, states and layout. |
| `pages/ProducerDetailPage.tsx` | Add `Open graph` link. |

## 5. URL and query contract

```text
/producers/:producerId/graph?view=bands&limit=20&depth=1
```

- `view`: `bands` default, `albums` alternative.
- `limit`: `20` default, max `100`.
- `depth`: `1` default, max `2`.
- Changing view/filter resets depth/limit only when required; the URL stays shareable.
- Filters are local UI state but may be mirrored in URL only if cheap; otherwise document them as session display state. The spec does not require filter URL persistence.

## 6. Error handling

- Invalid view: safe fallback to `bands` with a message.
- API 404: producer not found.
- API 503/no run: analysis unavailable.
- Empty graph: seed producer node and no-edge message.
- Truncated graph: persistent notice.
- Canvas failure/unsupported browser: show fallback table and a message.
- Filter empty: filtered-empty state with clear action.
- Simulation failure: stop physics, preserve table, allow retry/reset.
- Unmount: destroy layout, Cytoscape and listeners.

## 7. Testing strategy

| Level | What is tested | Evidence |
|---|---|---|
| Unit | Adapter mapping, view validation, filters, year scale, edge evidence. | `frontend/src/graph/*.test.ts` |
| Component | Legend, details, fallback tables, controls and states. | RTL tests |
| Integration | Route, query params, producer link, API error/truncation. | Page tests with mocked fetch |
| Physics | Layout registration/options (`linkId`, collision/repulsion, dynamic link distance), failure fallback and cleanup with mocked Cytoscape/d3-force. | Component tests |
| Visual | Album labels visible by default and legible styling independent of selection. | Style tests |
| Manual | Drag, neighbor response, freeze/resume/reheat, reduced motion, 500-node check. | E10 checklist |
| Build/CI | Lint, typecheck, tests, build and remote CI. | Commands/GitHub Actions |

Commands:

```bash
cd frontend
npm ci
npm run generate:api
npm run lint
npm run typecheck
npm run test
npm run build
```

## 8. Performance and limits

- Target: 500 nodes / 2,000 edges.
- Ego network defaults: 20 neighbors, depth 1.
- Max selection: 100 neighbors; depth 2.
- Physics pauses when hidden.
- Avoid label rendering for every album at once.
- No simulation in tests; mock Cytoscape/d3-force.
- If 500-node physics is not usable, use finite settle + reheat and document the fallback.

## 9. Dependencies

- Add `cytoscape-d3-force@1.1.4` and its transitive `d3-force`.
- No backend dependencies.
- No Tailwind, Plotly or new graph renderer.

## 10. Frontend and documentation impact

- Add graph route and producer detail link.
- Update `docs/01-architecture/frontend.md` with graph behavior and physics controls.
- Update README routes and limitations.
- Update E10 spec/tasks evidence.
- No changes to E8/E9 behavior.

## 11. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Infinite physics consumes CPU | Cap 500 nodes, pause hidden, freeze control, tune alpha/forces. |
| Drag feels static | Use `fixedAfterDragging: false`, `ungrabifyWhileSimulating: false`; manual check. |
| Graph becomes a hairball | Default ego network, selective labels, filters, legend. |
| Standalone graph renderer drift | Keep Cytoscape and one approved extension. |
| Client filters mislead after truncation | Persistent truncation notice and loaded-network wording. |
| Band-view filters lack metadata | Disable decade/taxonomy in band view with explanation. |
| Canvas inaccessible | Table fallback, details panel, keyboard controls, legend. |
| Test environment lacks canvas | Mock Cytoscape/d3-force; keep canvas init guarded. |
| Reduced-motion ignored | Start frozen and test media-query path. |
| Scope creep into E11 | Manual checklist only; Playwright/load tests in E11. |

## 12. Traceability requirements → plan → tasks

| Requirement | Plan section | Tasks |
|---|---|---|
| FR-001 | 2, 4 | T-002 |
| FR-002 | 3.3 | T-002, T-003 |
| FR-003 | 3.5, 5 | T-002, T-004 |
| FR-004 | 3.1 | T-003 |
| FR-005 | 3.1, 3.2 | T-003, T-006 |
| FR-006 | 3.2 | T-003, T-005 |
| FR-007 | 3.6 | T-004 |
| FR-008 | 3.4 | T-004, T-005 |
| FR-009 | 3.7, 4 | T-005 |
| FR-010 | 3.7 | T-006 |
| FR-011 | 6 | T-005 |
| FR-012 | 3.2, 3.7 | T-003 |
| FR-013 | 3.2 | T-003 |
| FR-014 | 1, 9 | T-007 |
| FR-015 | 7, 10 | T-007, T-008 |

| Non-functional requirement | Plan section | Tasks |
|---|---|---|
| NFR-001 | 8 | T-003, T-008 |
| NFR-002 | 3.2, 3.7 | T-003, T-006 |
| NFR-003 | 3.7 | T-006 |
| NFR-004 | 3.5 | T-004 |
| NFR-005 | 1, 9 | T-007 |
| NFR-006 | 4 | T-001, T-004 |
| NFR-007 | 3.2, 6 | T-003 |
| NFR-008 | 3.6, 6 | T-004, T-005 |

## 13. Approval and next step

This plan and `tasks.md` must be approved together before implementation. The first task is T-001: add the approved physics dependency, typed graph client and adapter.
