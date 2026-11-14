# SPEC-017 — Implementation plan

- **Status:** Plan/tasks in review
- **Spec:** [spec.md](spec.md)
- **Tasks:** [tasks.md](tasks.md)
- **Modules:** `web`
- **Depends on:** SPEC-011, SPEC-013

## 1. Solution summary

Add two static, client-side layout modes to the `/graph` overview:

1. **Coreness** — compute k-core shell numbers on the loaded graph and render with Cytoscape `concentric`.
2. **Rings** — render bands, albums and producers in three type regions using a composed `concentric` score; producers are ordered by a metric selected from a dropdown.

The work is confined to the frontend. The overview API continues to accept only its existing `layout` values; the new modes and the Rings metric are URL-backed client state and never enter the API query key. The existing force engine selector remains Force-only.

## 2. Architecture and data flow

```text
URL layout=coreness|rings + ring_metric
        |
        v
ProducerOverviewPage
  - parse and validate client-only state
  - do not pass these values to the overview API
  - include them in the Cytoscape layout input, not the query key
        |
        v
ProducerGraph
  - reuse the loaded graph
  - compute coreness / Rings score in the client
  - run cy.layout({ name: 'concentric', ... })
        |
        v
Static canvas + status text
  - Freeze/Resume/Reheat disabled
  - selection, details, table and resize unchanged
```

Client-only filters (role, search, isolated visibility) remain presentation filters. Scores are calculated from the loaded graph before those filters are applied so the layout does not reshuffle when a node is hidden.

## 3. Components and files

| Area | File | Change |
|------|------|--------|
| Coreness utility | `frontend/src/graph/coreness.ts` (new) | Bucket-based k-core peeling over unique neighbors. |
| Metric scores | `frontend/src/graph/radialLayouts.ts` (new) | Rings metric types, normalization, producer projection and `concentric` score builders. |
| Overview graph | `frontend/src/components/ProducerGraph.tsx` | Accept the client radial mode and metric; run static `concentric`; disable physics; fallback handling. |
| Controls | `frontend/src/components/ProducerOverviewControls.tsx` | Add Coreness/Rings options and the Rings metric dropdown. |
| Page state | `frontend/src/pages/ProducerOverviewPage.tsx` | Parse `layout=coreness|rings` and `ring_metric`; keep them out of the API request and query key. |
| Styles | `frontend/src/index.css` | Only if the new control needs existing form styling; no new visual system. |
| Tests | `frontend/src/graph/coreness.test.ts` (new), `frontend/src/graph/radialLayouts.test.ts` (new), component/page tests | Unit, rendering and URL-state coverage. |

No backend files, migrations, generated API clients or dependencies are expected.

## 4. Technical decisions

### 4.1 Coreness algorithm

- Build adjacency from unique neighbor IDs; parallel edges do not inflate degree.
- Use bucket-based peeling (Matula–Beck / Batagelj–Zaveršnik style) rather than rescanning the remaining graph per shell. This keeps the utility effectively linear in nodes plus adjacency for the overview sizes.
- Isolated nodes receive coreness 0.
- Preserve deterministic iteration by sorting neighbor IDs and using stable tie-breakers.
- Unit fixtures cover: empty graph, isolated nodes, a path/leaf, a cycle, a dense core, parallel/duplicate neighbors and disconnected components.

### 4.2 Rings metrics

- `coreness`: the utility result from 4.1.
- `betweenness`: read the existing producer node attribute; non-finite or absent values rank below finite values.
- `degree`: distinct neighbor count in the loaded graph.
- `producer-connectivity`: build a producer projection by grouping producers that share a band or album target, then count distinct producer neighbors. This is projection degree, not projection coreness.
- Normalize each metric independently to `[0, 1]`; if all values are equal, use a neutral value. Higher values receive a higher `concentric` score.
- Ties break by label and then ID.

### 4.3 Concentric scoring

- Coreness mode: `score = coreness`; use a level width that groups integer shells.
- Rings mode: compose bounded type bases so type order cannot invert:
  - bands: `3 + 0.25 * normalizedDegree`
  - albums: `2 + 0.25 * normalizedDegree`
  - producers: `1 + 0.5 * normalizedMetric`
  - This keeps producers below 2, albums below 3 and bands at the center. `levelWidth` is calibrated (initially `0.25`) so producer values form visible outer sub-rings without crossing type regions.
- `concentric` options: `animate: false`, `fit: true`, `padding` consistent with the existing graph, `minNodeSpacing` and `avoidOverlap` enabled where supported.
- Layout runs only when the mode is Coreness or Rings and the graph is ready. It does not start any force engine.

### 4.4 State and URL contract

- Layout values: existing Force, Bipartite, Community plus `coreness` and `rings`.
- `ring_metric`: `betweenness` (default), `coreness`, `degree`, `producer-connectivity`.
- Invalid or unknown values normalize to Force / betweenness.
- The overview API request and TanStack Query key exclude `coreness`, `rings` and `ring_metric`. This avoids 422 responses from the API layout enum and prevents refetches.
- The metric dropdown is rendered when Rings is active, with a programmatic label and keyboard support.

### 4.5 Static lifecycle and fallback

- Freeze/Resume/Reheat are disabled for both modes because there is no simulation.
- Status text: `Coreness layout` or `Rings layout · Betweenness`.
- On score or `concentric` failure: run static `breadthfirst`, show a non-blocking notice and preserve the selected mode where possible.
- If `breadthfirst` also fails: fall back to Force and show the existing error/notice pattern.
- Client filters do not trigger recomputation; a metric change does trigger a new score and layout pass without a network request.

## 5. API and data model

No changes.

- `GET /api/v1/graph/producers` remains unchanged.
- No new fields, database tables, migrations or OpenAPI output.
- No generated TypeScript API changes.

## 6. Frontend impact

- The Layout selector gains two options.
- The Rings metric control appears only for Rings.
- Existing `engine` state remains Force-only; selecting Coreness or Rings disables it.
- Selection, detail panel, index/table, zoom/pan, canvas resizing and the static fallback continue to use the existing graph data.
- No new CSS framework or dependency.

## 7. Error handling

| Condition | Behavior |
|-----------|----------|
| Empty graph | Render an empty static canvas; no error. |
| One node | Place it at the center; no error. |
| Missing betweenness | Rank as lowest; no error. |
| All scores equal | Neutral normalized value; deterministic tie order. |
| Invalid `ring_metric` | Use `betweenness`; keep the graph usable. |
| Score computation throws | Static `breadthfirst` + notice. |
| `concentric` throws | Static `breadthfirst` + notice. |
| Both static layouts fail | Force fallback + notice. |

## 8. Security, privacy and provenance

No change. The feature reads the existing read-only overview response and makes no new network request. No user data is persisted.

## 9. Observability

No new logs or metrics. Existing client errors remain visible through the current graph error/notice path.

## 10. Testing strategy

| Layer | Coverage |
|-------|----------|
| Unit | Coreness fixtures, duplicate neighbors, disconnected graphs; metric normalization; missing betweenness; producer projection; score ordering; URL validation. |
| Component | Layout options, metric dropdown visibility/label, status text, disabled physics controls, fallback notice. |
| Integration/page | URL round-trip, no API request on mode/metric change, query key stability, selection/details preserved. |
| Headless | Coreness and Rings at the current 398-node and 968-node views; metric switch; empty/single-node fallback; resize. |
| Regression | Force/Bipartite/Community and force engines unchanged; ego graph unchanged. |

Commands:

```bash
cd frontend
npm run lint
npm run typecheck
npm run test
npm run build
```

## 11. Deployment and reversibility

Frontend-only change. No migration, flag or environment variable. Reverting the frontend commit restores the previous layout selector. Existing Force/Bipartite/Community URLs remain valid.

## 12. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| `concentric` level mixing makes type rings unclear | Bounded type bases, calibrated `levelWidth`, headless checks at both views. |
| Coreness is misread as producer connectivity | BR-006, concise status/help copy, no misleading label. |
| Missing betweenness creates misleading order | Explicit lowest-rank rule and existing missing-data surfaces. |
| Large graph layout blocks interaction | Score computation is linear; layout is static; measure at 398/968 nodes. |
| Client filters reshuffle positions | Compute scores before client filters; no recomputation on visibility changes. |
| API rejects new layout values | Keep new modes out of the API request and query key. |
| New dependency creep | Use Cytoscape core only. |

## 13. Traceability

| Requirement | Design/test |
|-------------|-------------|
| FR-001, FR-008 | 4.4, page tests, URL tests |
| FR-002, FR-003 | 4.1, 4.3, coreness unit tests, headless Coreness check |
| FR-004, FR-007 | 4.2, 4.3, Rings unit/headless checks |
| FR-005, FR-006 | 4.2, metric unit tests, control tests |
| FR-009, FR-010 | 4.5, component tests, filter regression |
| FR-011 | 4.5, forced-failure tests |
| FR-012 | 5, 6, regression checks |
| NFR-001–NFR-004 | Testing strategy, performance/headless checks, dependency review |

## 14. Approval

Plan ready for review. Implementation is not authorized until the spec, plan and tasks are approved.
