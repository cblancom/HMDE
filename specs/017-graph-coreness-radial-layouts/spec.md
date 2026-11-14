# SPEC-017 — Graph coreness and radial layouts

- **Status:** Plan/tasks in review
- **Stage:** E10 follow-up
- **Iteration:** MVP
- **Modules:** `web`
- **Date:** 2026-11-13
- **Depends on:** SPEC-011 (global producer overview), SPEC-013 (layout selector and force engine selector)
- **ADRs:** —
- **Plan:** [plan.md](plan.md)
- **Tasks:** [tasks.md](tasks.md)
- **Conventions:** [../../docs/01-architecture/conventions.md](../../docs/01-architecture/conventions.md)
- **Owner:** Cristian

## Revision history

| Rev | Date | Change |
|-----|------|--------|
| 1 | 2026-11-13 | Initial spec. Adds separate Coreness and Rings client-side modes, with a Rings metric selector. |

## 1. Context and problem

The `/graph` overview currently offers Force, Bipartite and Community layouts (SPEC-011, SPEC-013). Force supports the `d3-force`, CoSE and fCoSE engines (SPEC-013 revision 4). None of these modes exposes the structural center and periphery of the selected graph, and none offers a producer-centric radial ordering controlled by a metric.

This spec adds two **separate** static client-side modes:

- **Coreness**: k-core decomposition of the loaded overview graph. Nodes in denser k-cores are placed closer to the center; peripheral nodes are placed outward.
- **Rings**: three conceptual rings ordered from center to outside: bands, albums and producers. Producers are ordered within the outer region by a metric selected from a dropdown.

Both modes use the Cytoscape core `concentric` layout and run entirely in the browser. They add no API, backend, database or dependency changes.

This spec is separate from SPEC-013. SPEC-013 revision 4 remains limited to the Force engine selector. Orthogonal edge routing is specified separately in [SPEC-018](../018-orthogonal-edge-routing/spec.md).

## 2. Users and actors

- **Researcher:** compares the structural core of the selected graph and the producer-centric radial view.
- **Web client:** computes scores and runs the static `concentric` layout.
- **Cytoscape:** provides the `concentric` and `breadthfirst` layouts.

No backend actor is added.

## 3. User stories and flows

- **US-001:** As a researcher, I can select **Coreness** and see nodes with a higher k-core shell closer to the center.
- **US-002:** As a researcher, I can select **Rings** and see bands in the center, albums in the middle and producers on the outside.
- **US-003:** As a researcher, in Rings mode I can choose a metric from a dropdown and see producers reorder within the outer region without an API request.
- **US-004:** As a researcher, if a score or static layout cannot be computed, I see a usable fallback graph and a notice instead of a blank canvas.

## 4. Functional requirements

- **FR-001 — Layout options.** The `/graph` Layout selector offers **Coreness** and **Rings** in addition to Force, Bipartite and Community. The URL uses `layout=coreness` and `layout=rings`. The default remains Force.
- **FR-002 — Coreness score.** The client computes the k-core shell number for each node in the loaded server-selected graph. The graph is built from unique node neighbors; isolated nodes have coreness 0. The computation uses a bucket-based peeling queue and does not rescan every remaining node on every step.
- **FR-003 — Coreness layout.** Coreness mode uses the Cytoscape `concentric` layout. A higher coreness places a node closer to the center; equal coreness values share a ring. The layout is static and deterministic for the same loaded graph.
- **FR-004 — Rings layout.** Rings mode uses the Cytoscape `concentric` layout with three type regions, ordered from center to outside: bands, albums, producers. Type ordering is preserved regardless of the selected metric.
- **FR-005 — Rings metric selector.** When Rings is selected, a labeled dropdown offers `betweenness`, `coreness`, `degree` and `producer-connectivity`. The default is `betweenness`. The selected value is stored in the URL as `ring_metric=<value>`.
- **FR-006 — Metric definitions.** The Rings metric means:
  - `coreness`: the value from FR-002.
  - `betweenness`: the producer `betweenness` attribute returned by the overview API (`NA-BET-001`). A missing or non-finite value is treated as the lowest value.
  - `degree`: the number of distinct neighbors of the node in the loaded graph.
  - `producer-connectivity`: the number of distinct producer neighbors reachable through a shared band or album target in the loaded graph (producer-projection degree).
- **FR-007 — Metric ordering.** Metrics are normalized independently to `[0, 1]`; a higher value places a producer closer to the center. Bands and albums keep their type rings and are ordered within their ring by degree, not by the selected producer metric.
- **FR-008 — Client-only state.** `coreness`, `rings` and the Rings metric are client-side state. They are not sent to the overview API, are not part of the API query key, and do not trigger a network request. Invalid or missing URL values fall back to valid defaults.
- **FR-009 — Static layout behavior.** Coreness and Rings never start a force engine. Freeze, Resume and Reheat are disabled; the status text identifies the active mode and, for Rings, the selected metric. Node selection, detail panels, the index/table and canvas resizing continue to work.
- **FR-010 — Stability under client filters.** Scores are computed from the loaded graph before client-only role, search or isolated-node visibility filters. Hiding or showing client-filtered nodes must not recompute scores or reshuffle the layout.
- **FR-011 — Fallback.** If score computation or `concentric` fails, the client falls back to a static `breadthfirst` layout and shows a non-blocking notice. If that also fails, it falls back to Force. The graph must not remain blank.
- **FR-012 — Scope.** The change applies to the `/graph` overview only. The producer ego graph at `/producers/:id/graph`, the API contract, the database and the backend remain unchanged.

## 5. Non-functional requirements

- **NFR-001 — Determinism.** For the same loaded graph, view, client filters and Rings metric, repeated layout runs produce the same node ordering. Score ties break by label and then ID.
- **NFR-002 — Performance.** Coreness and metric computation plus the static layout complete without blocking navigation for the current 398-node band view and 968-node album view, and remain usable at the existing 500-node/1,134-edge safety limits.
- **NFR-003 — Accessibility and responsiveness.** The Rings metric control has a programmatic label, is keyboard operable and exposes its selected value. The graph remains usable at the existing narrow and wide layout breakpoints.
- **NFR-004 — Dependencies and contracts.** No new runtime dependency, no API change and no migration. The existing Cytoscape core layouts are sufficient.

## 6. Business rules

- **BR-001:** Coreness mode places higher k-core shells closer to the center.
- **BR-002:** Rings mode always orders bands inside albums and albums inside producers, regardless of the selected metric.
- **BR-003:** In Rings mode, the selected metric orders producers only; bands and albums use degree for ordering within their type ring.
- **BR-004:** Missing producer betweenness is not zero evidence of connectivity; it is ranked as the lowest available value and displayed as missing in existing detail surfaces.
- **BR-005:** Scores are derived from the loaded graph, not from the currently visible subset after client-only filters.
- **BR-006:** Coreness is structural embedding, not a count of producer-to-producer connections. A simple `producer–band–producer` chain can have coreness 1 for all three nodes. The UI must not describe Coreness mode as producer connectivity.

## 7. Edge cases and errors

- Empty graph or a graph with one node.
- No albums in the band view or no bands in the album view.
- All nodes have the same score.
- All producer betweenness values are missing or non-finite.
- Isolated producers are shown or hidden by the client filter.
- A metric change while the graph is selected, filtered or resized.
- An invalid `layout` or `ring_metric` URL value.
- A cycle or dense core that produces coreness 2 or higher.
- A client-side score or layout error.
- Reduced-motion preference; static layouts must not animate.

## 8. Out of scope

- Force-based radial layouts or new `forceX`/`forceY`/`forceRadial` forces.
- Backend coreness, metric computation, new API fields or database columns.
- Coloring nodes by coreness or showing score values in the UI.
- Producer ego graph changes.
- Orthogonal edge routing; see [SPEC-018](../018-orthogonal-edge-routing/spec.md).
- New dependencies or changes to the static layout fallback contract.

## 9. Acceptance criteria

- **AC-001:** The `/graph` Layout selector shows Coreness and Rings; selecting either sets the URL and restores the mode on reload. Force remains the default.
- **AC-002:** Coreness values are correct on fixture graphs: isolated nodes are 0, leaves are 1, and a cycle or denser core is at least 2.
- **AC-003:** Coreness mode places higher-coreness nodes closer to the center; repeated runs with the same input are deterministic.
- **AC-004:** Rings mode places every band inside every album and every album inside every producer for the tested band and album views.
- **AC-005:** Rings mode shows a metric dropdown with the four metrics, defaults to betweenness, and stores the choice in `ring_metric`.
- **AC-006:** Changing the Rings metric reorders producers without an overview API request and without changing the type-ring order.
- **AC-007:** Freeze, Resume and Reheat are disabled in Coreness and Rings; the status text names the mode and metric; no force engine starts.
- **AC-008:** Empty graphs, a single node, missing betweenness, an invalid URL metric and a forced score/layout failure produce a usable graph and a notice where applicable.
- **AC-009:** Coreness and Rings remain usable with the 398-node band view and 968-node album view, including selection and detail panels.
- **AC-010:** The API query key, API contract, backend, database and ego graph are unchanged.
- **AC-011:** Frontend lint, typecheck, tests and build pass; headless browser checks cover both modes and the metric switch.

## 10. Assumptions and open questions

### Assumptions

- Coreness and Rings are static client-side layouts; no force physics is required.
- Cytoscape core `concentric` is sufficient; no new dependency is introduced.
- `betweenness` is the default Rings metric because it is already persisted and gives a meaningful first render. The default may be changed by a later revision.
- `producer-connectivity` means producer-projection degree, not k-core of the projection. A projection-core metric would require a separate requirement.
- Scores are computed on the loaded server-selected graph before client-only filters, matching the stability rule for existing static layouts.
- No blocking questions remain for planning.

### Open questions

None blocking. The default Rings metric and the exact `levelWidth` calibration are implementation details to validate in T-003 and may be adjusted without changing the contract.

## 11. Validation result

Not implemented. Acceptance evidence will be recorded in [tasks.md](tasks.md) after implementation.

## 12. References

- [SPEC-011 — Graph overview](../011-graph-visualization/spec.md)
- [SPEC-013 — Graph layout modes](../013-graph-layout-modes/spec.md)
- [SPEC-018 — Orthogonal edge routing](../018-orthogonal-edge-routing/spec.md)
- [Frontend architecture](../../docs/01-architecture/frontend.md)
- [Roadmap](../../docs/00-vision/roadmap.md)
