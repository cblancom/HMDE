# Technical plan — SPEC-012 Graph overview workspace refinements

- **Status:** Approved; implemented locally (revision 3)
- **Spec:** [spec.md](spec.md)
- **Tasks:** [tasks.md](tasks.md)
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0006](../../docs/01-architecture/adr/ADR-0006-read-only-api.md), [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)
- **Module:** `web`

## 1. Solution summary

Refine the existing `/graph` page into a three-region workspace without changing the API, schema or graph renderer:

- a left index with two native collapsible lists;
- the existing Cytoscape overview in the center;
- a right detail panel that reuses the selected node and loads related documented data from existing read-only endpoints.

The year scale becomes a dynamic light-to-dark sequence for the overview only. The ego graph at `/producers/:id/graph` keeps the current viridis scale.

Both side panels use the graph workspace height as their height on wide screens. Each panel owns its vertical scroll; the page does not grow because of long lists or long detail content.

No backend endpoint, OpenAPI schema, Alembic migration, dependency or renderer is added.

## 2. Architecture and data flow

```text
Overview API ──► ProducerOverviewPage ──► adaptOverviewGraph ──► ProducerGraph (center)
      │                    │                        │
      │                    │                        ├─ yearRange (visible albums)
      │                    │                        ├─ allIncidentProducersById
      │                    │                        └─ index selectors
      │                    │
      │                    ├─► OverviewIndex (left)
      │                    │     ├─ producer nodes from the overview response
      │                    │     └─ bands from GET /api/v1/bands?limit=200
      │                    │
      │                    └─► ProducerOverviewDetails (right)
      │                          ├─ producer: two GET /producers/{id}/graph queries
      │                          ├─ band: GET /bands/{id}
      │                          └─ album: node attributes + all overview edges
      └──────────────────────────── selected URL parameter ───────────────►
```

The center graph column determines the workspace height. The left and right columns stretch to the same row height and use `overflow-y: auto` with `min-height: 0`.

## 3. Components and responsibilities

| Component or path | Responsibility |
|---|---|
| `frontend/src/pages/ProducerOverviewPage.tsx` | Three-region layout, graph query, band index query, selection state, responsive composition. |
| `frontend/src/components/OverviewIndex.tsx` (new) | Two collapsible lists, counts, sorting, links and internal scroll. |
| `frontend/src/components/ProducerOverviewDetails.tsx` | Selected producer, band, album and edge details; related-data queries and states. |
| `frontend/src/graph/adapter.ts` | Dynamic `yearRange`, light-to-dark overview color helper, index selectors, unfiltered incident producers. |
| `frontend/src/components/GraphLegend.tsx` | Optional dynamic year range and gradient for the overview; unchanged ego behavior. |
| `frontend/src/index.css` | Workspace grid, equal panel heights, internal scroll and responsive stack. |
| `frontend/src/api/producerGraph.ts`, `frontend/src/api/producers.ts`, `frontend/src/api/bands.ts` | Existing clients; no signature changes expected. |
| `frontend/src/**/*.test.ts(x)` | Adapter, index, legend, detail and page tests. |

## 4. Technical decisions and alternatives

### 4.1 Workspace layout and equal panel heights

Use a CSS grid with a shared row height:

```text
.overview-workspace {
  --overview-workspace-height: clamp(36rem, 72vh, 54rem);
  display: grid;
  grid-template-columns: minmax(11rem, 13rem) minmax(0, 1fr) minmax(16rem, 18rem);
  gap: 1rem;
  height: var(--overview-workspace-height);
  align-items: stretch;
}
```

The center graph column is a flex column whose canvas fills the remaining height. The left index and right details use `height: 100%`, `min-height: 0`, and `overflow-y: auto`.

The graph component currently sizes its canvas with `clamp(36rem, 72vh, 54rem)` plus toolbar. The implementation will move the height ownership to the workspace and let the overview canvas fill its column, so the three regions share one rendered height. The ego graph retains its existing canvas sizing.

At widths below 1280px the grid becomes one column with the graph first, detail second and index third. Each scrollable region gets a bounded `max-height`.

**Alternative:** use JavaScript `ResizeObserver` to copy the graph height to the panels. Rejected: extra code and lifecycle complexity for a layout problem that CSS grid can solve.

### 4.2 Left index data

Producers:

- Source: `graphQuery.data.nodes` from the loaded overview response.
- Filter: `node.roles.includes('producer')`.
- Count: `node.attributes.album_count`, defaulting to 0.
- Sort: count descending, then label ascending, then id.
- Includes the 43 band entities that also carry the producer role.

Bands:

- Source: existing `getBands({ limit: 200, decade, subgenre })`.
- Count: `BandListItem.album_count`, which is the documented album count.
- Sort: count descending, then name ascending, then id.
- These are the loaded run's bands; the list is not rewritten by client role/search/isolated filters.

The index is a read-only navigation aid. Entries link to `/producers/:id` or `/bands/:id`.

**Alternative:** derive bands from the overview response in the bands view. Rejected: the albums view has no band nodes, so the band index would disappear or need a separate query anyway.

### 4.3 Dynamic year scale

Add to the overview adapter:

```ts
type YearRange = { min: number; max: number };
type AdaptedOverviewGraph = AdaptedGraph & {
  yearRange: YearRange | null;
  allIncidentProducersById: Record<string, ProducerGraphNode[]>;
};
```

- Compute `yearRange` from the visible album nodes after client filters and the isolated toggle.
- Use a two-stop sequential scale:
  - oldest: `#bcd8c2` (pale lichen, visibly darker than the `#dde2dc` canvas);
  - newest: `#123c38` (deep petrol).
- Interpolate in RGB and use the midpoint for a single visible year.
- Unknown years keep `#66736d`.
- The ego adapter continues to use the existing `yearColor` behavior.

`GraphLegend` accepts an optional `yearRange` and, when present, renders the gradient with the real minimum and maximum. When the overview has no album nodes, the year item is omitted.

**Alternative:** keep the fixed viridis scale and explain it in the legend. Rejected by the owner: intuitive luminance is the requirement.

### 4.4 Producer detail data

Use the existing bounded ego endpoints:

```text
GET /api/v1/producers/{id}/graph?view=bands&limit=100&depth=1&max_nodes=500&max_edges=2000
GET /api/v1/producers/{id}/graph?view=albums&limit=100&depth=1&max_nodes=500&max_edges=2000
```

A single TanStack Query keyed by producer id fetches both in parallel. The panel lists:

- bands: every non-producer node from the band response;
- albums: every album node from the album response, with year;
- a truncation note if either response has `meta.truncated`.

**Alternative:** `GET /api/v1/producers/{id}` top lists. Rejected: it only returns the top 20; the owner chose complete lists.

### 4.5 Band and album detail data

Band:

- `GET /api/v1/bands/{id}` returns albums with aggregated credits.
- Albums: `data.albums`.
- Producers: unique credits whose `role` is `producer` or `co-producer`.
- This endpoint is already read-only and does not require an analysis run.

Album:

- Band name, year and band id come from the overview album node attributes.
- Producers come from `allIncidentProducersById`, computed from every overview edge before client filters.
- No additional request is needed.

### 4.6 Detail states

- Loading: compact inline loading text inside the panel.
- Missing entity: panel message with a link back to the entity index.
- Error: panel-local error with retry; the canvas and table remain.
- Empty relationships: explicit empty text.
- Truncated ego graph: persistent note.
- Selection removed by a filter: clear the panel.

### 4.7 Revision 3 — space efficiency

**Navigation rail.** `AppShell` gains a persisted `rail-collapsed` state (`localStorage` key). Without a stored preference, `/graph` starts collapsed and other routes start expanded; an explicit toggle wins over the route default. The collapsed desktop rail is a 3rem strip containing only the expand button and an `HMDE` monogram. The mobile top-bar navigation is unchanged and hides the toggle.

**Wide layout.** Remove the `96rem` shell ceiling, reduce the horizontal main padding to `clamp(0.75rem, 1.5vw, 1.5rem)`, center reading pages with their existing `max-width`, and let `/graph` use the full width.

**Overview panels.** `ProducerOverviewPage` owns `indexOpen` and `detailsOpen` state, both initially true. A compact toggle group near the graph counts exposes `Index` and `Details` with `aria-pressed`. Closing a panel removes its grid column; the graph expands. Selecting a node sets `detailsOpen=true`.

**Canvas resize.** `ProducerGraph` observes its container with `ResizeObserver` and calls `cy.resize()` without recreating Cytoscape, resetting zoom or restarting physics. The observer is removed on unmount.

**Layout numbers.** At 1440 px the current graph is about 525 px. With the rail collapsed, reduced padding and the proposed panel widths (`minmax(10rem,12rem)` / `minmax(14rem,16rem)`, 0.75rem gaps), the graph should reach about 870 px with both panels open and over 1,300 px with both closed.

## 5. Data model and migrations

No changes. This refinement uses the existing persisted E7 graph and canonical entity reads.

## 6. API contract

No changes. Existing endpoints:

- `GET /api/v1/graph/producers`
- `GET /api/v1/producers/{id}/graph`
- `GET /api/v1/producers/{id}`
- `GET /api/v1/bands`
- `GET /api/v1/bands/{id}`
- `GET /api/v1/albums/{id}`

No OpenAPI or generated TypeScript change is expected.

## 7. Frontend impact

- Route: `/graph` only.
- State: existing view, producer limit/sort, decade, subgenre, isolated and selected URL parameters remain.
- Server state:
  - existing overview query;
  - new band index query using `queryKeys.bands`;
  - producer neighbor query using the existing ego client;
  - band detail query using `queryKeys.band`.
- Loading, error, empty and truncation states are panel-local.
- Accessibility: native disclosure widgets, labelled scroll regions, visible focus, selection announced in the panel, year still present in text.
- Performance: list rendering is plain React; 384 + 57 entries need no virtualization. Related queries are cached.

## 8. Error handling and consistency

- If the band index query fails, the producers list and graph remain; the bands section shows a retry.
- If a producer neighbor query fails, the panel shows the error and the graph remains selected.
- If a band detail request fails, the panel shows the error and the graph remains.
- If a selected node is filtered out, the page clears the details rather than showing stale data.
- The overview query remains the source of truth for the graph and the producer index.

## 9. Security and trust boundaries

No change. The application remains public and read-only. The new queries use existing GET endpoints. No secrets, writes, authentication or authorization changes are involved.

## 10. Observability

No new logs, metrics or run records. The existing API requests are visible through the browser network panel and the API process logs.

## 11. Testing strategy

| Level | What is tested | Evidence |
|---|---|---|
| Adapter unit | Year range, light-to-dark color endpoints, single-year fallback, missing years, producer index order, all incident producers | `frontend/src/graph/*.test.ts` |
| Component | Collapsible lists, counts, keyboard toggle, legend range, detail states | `frontend/src/components/*.test.tsx` |
| Page | Three-region composition, band query, selection URL, responsive classes, existing filters | `frontend/src/pages/ProducerOverviewPage.test.tsx` |
| Manual/headless | Equal panel heights, independent scroll, responsive stack, dynamic scale, node detail flows | Chromium screenshots and bounding-box probes |
| Revision 3 | Rail collapse/persistence, wide layout, panel toggles, details auto-open, canvas resize | AppShell/page/component tests and Chromium width checks |
| Regression | Existing overview page, graph physics and accessible table | Existing tests plus full frontend suite |

Exact commands:

```bash
cd frontend
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

## 12. Deployment and reversibility

Frontend-only change. No migration, environment variable or data cleanup. Reverting the commit restores the previous overview page.

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Equal-height CSS causes the page to grow with long lists. | Fixed workspace height, `min-height: 0`, and `overflow-y: auto` on both panels; verify with headless bounding boxes. |
| Two ego queries per producer add latency. | Parallel queries, TanStack Query cache, panel-local loading state. |
| Producer neighbor lists exceed the 100-neighbor cap. | Show the existing truncation notice; keep the entity link. |
| Dynamic year colors shift as filters change. | Document the behavior; years remain in the legend, details and table. |
| Band index and canvas differ after client filters. | State that the index reflects the loaded run and server filters; it is a navigation aid, not a canvas visibility count. |
| Narrow layouts become crowded. | Stack the three regions and bound panel heights. |
| Rail collapse is hard to discover. | Keep a 3rem strip with a labelled toggle and monogram. |
| Panel toggles resize the canvas incorrectly. | `ResizeObserver` calls `cy.resize()` without recreating the graph. |
| Global wide layout makes reading pages too wide. | Keep and center the existing `72rem` page width; only `/graph` is unbounded. |

## 14. Traceability requirements → plan → tasks

| Requirement | Plan section | Tasks |
|---|---|---|
| FR-001 | 4.1 | T-003, T-005 |
| FR-002 | 4.2 | T-002, T-003 |
| FR-003 | 4.2 | T-003 |
| FR-004 | 4.1, 4.2 | T-003 |
| FR-005 | 4.1 | T-003, T-006 |
| FR-006 | 4.3 | T-001, T-005 |
| FR-007 | 4.3 | T-001, T-005 |
| FR-008 | 4.4 | T-004 |
| FR-009 | 4.5 | T-002, T-004 |
| FR-010 | 4.5 | T-004 |
| FR-011 | 4.6 | T-004, T-005 |
| FR-012 | 4.6, 7 | T-004, T-005 |
| NFR-001 | 7 | T-003, T-004, T-005 |
| NFR-002 | 7, 13 | T-003, T-004 |
| NFR-003 | 1, 5, 6 | T-005, T-006 |
| NFR-004 | 4.1 | T-003, T-005, T-006 |
| AC-001–AC-003 | 4.2 | T-002, T-003 |
| AC-004 | 4.1 | T-003, T-006 |
| AC-005–AC-006 | 4.3 | T-001, T-005 |
| AC-007–AC-010 | 4.4–4.6 | T-004, T-005 |
| AC-011–AC-013 | 7, 11 | T-005, T-006 |
| FR-013–FR-016 | 4.7 | T-007, T-008 |
| AC-014–AC-018 | 4.7, 11 | T-008, T-009, T-010 |

## 15. Approval and next step

T-001–T-010 are implemented locally. The revision-3 space-efficiency changes passed the automated suite and headless Chromium checks. Remote CI and the manual ego interaction review from SPEC-011 remain pending.
