# SPEC-018 — Orthogonal edge routing

- **Status:** Plan/tasks in review
- **Stage:** E10 follow-up
- **Iteration:** MVP
- **Modules:** `web`
- **Date:** 2026-11-13
- **Depends on:** SPEC-011 (global producer overview), SPEC-013 (layout modes)
- **ADRs:** —
- **Plan:** [plan.md](plan.md)
- **Tasks:** [tasks.md](tasks.md)
- **Conventions:** [../../docs/01-architecture/conventions.md](../../docs/01-architecture/conventions.md)
- **Owner:** Cristian

## Revision history

| Rev | Date | Change |
|-----|------|--------|
| 1 | 2026-11-13 | Initial spec. Adds a global curved/orthogonal edge-routing toggle to the `/graph` overview. |

## 1. Context and problem

The `/graph` overview draws producer–band and producer–album edges with Cytoscape's default curved `bezier` routing. Bezier edges are readable in sparse views but can become visually tangled in dense producer or album views. Cytoscape core supports orthogonal edge routing through `curve-style: 'taxi'` and `'round-taxi'`, so no new dependency is needed.

This spec adds one **global** edge-routing toggle to the `/graph` overview: **Curved** (current default) and **Orthogonal**. The toggle is independent of the Layout selector and applies to every overview layout, including Force, Bipartite, Community, Coreness and Rings. It does not change nodes, positions, data, filters or the producer ego graph.

Orthogonal routing is intentionally separate from the layout modes. It is not a Layout option and does not add a backend layout.

## 2. Users and actors

- **Researcher:** switches edge routing to reduce visual entanglement while keeping the current layout and selection.
- **Web client:** toggles a Cytoscape edge class and URL state.
- **Cytoscape:** renders `taxi` orthogonal edge segments.

No backend actor is added.

## 3. User stories and flows

- **US-001:** As a researcher, I can turn orthogonal edges on and off from the `/graph` controls without changing the layout.
- **US-002:** As a researcher, the choice survives reload via the URL and applies to the current overview mode.
- **US-003:** As a researcher, if orthogonal routing cannot be rendered, I keep a usable curved graph and see a notice.

## 4. Functional requirements

- **FR-001 — Global toggle.** The `/graph` overview controls expose a labeled **Orthogonal edges** toggle. It is visible in every overview layout and is off by default.
- **FR-002 — Orthogonal routing.** When enabled, every overview edge uses Cytoscape `curve-style: 'taxi'` with `taxi-direction: 'auto'`, `taxi-turn: '50%'` and a `taxi-turn-min-distance` value that avoids tiny first/last segments. Edge width, opacity, role styling, selection and underlay remain unchanged.
- **FR-003 — URL state.** The toggle is stored as `routing=orthogonal`. `routing=curved` and a missing value mean curved. Invalid values fall back to curved. The toggle state restores on reload and browser navigation.
- **FR-004 — No layout change.** Toggling routing does not change node positions, the active layout, the active force engine, filters, selection or details. The route updates in place without refetching or recreating the graph.
- **FR-005 — Scope.** The toggle applies to the `/graph` overview and all its layouts. The producer ego graph at `/producers/:id/graph` remains curved and unchanged.
- **FR-006 — Fallback.** If `taxi` is unavailable or applying the style fails, the client keeps `bezier` edges, leaves the toggle recoverable and shows a non-blocking notice. The graph must not remain blank.
- **FR-007 — Accessibility and status.** The toggle has a programmatic label, is keyboard operable, exposes its checked state and is reachable at the existing narrow and wide breakpoints.

## 5. Non-functional requirements

- **NFR-001 — Performance.** Toggling routing updates the existing 398-node/968-node views without a network request or a noticeable interaction block.
- **NFR-002 — Readability.** Orthogonal routing remains usable at the current 500-node/1,134-edge safety limit; edge intersections are acceptable but the graph must not become unreadable or unresponsive.
- **NFR-003 — Dependencies and contracts.** No new runtime dependency, API change, backend change or migration.
- **NFR-004 — Regression safety.** Curved routing remains the default and existing graph interactions, selection, details, filtering and layouts are unchanged.

## 6. Business rules

- **BR-001:** Curved `bezier` is the default; orthogonal routing is opt-in.
- **BR-002:** Routing changes presentation only; it does not alter graph data, layout input, filters or selection.
- **BR-003:** The toggle is global to the overview, not a per-edge or per-layout control.
- **BR-004:** Orthogonal routing uses Cytoscape `taxi`; custom obstacle avoidance and edge bundling are not implied.
- **BR-005:** An unavailable or failed orthogonal style falls back to curved rather than showing an empty canvas.

## 7. Edge cases and errors

- Dense producer and album views with many crossing edges.
- Selected or highlighted edges with underlay styling.
- Toggle while a force layout is running or while a static layout is settling.
- Invalid or missing `routing` URL value.
- Orthogonal routing combined with each overview layout and each force engine.
- Reduced-motion preference; the toggle itself does not animate.
- Client resize or filter change while orthogonal is active.
- Unsupported `taxi` style or style-application failure.

## 8. Out of scope

- Edge bundling, obstacle avoidance, routing around node labels or custom orthogonal routers.
- Arrowhead, label-placement or edge-semantics changes.
- `round-taxi` styling variants; the initial implementation uses `taxi`.
- Producer ego graph routing.
- Backend, API, database or dependency changes.
- Making orthogonal routing a Layout mode.

## 9. Acceptance criteria

- **AC-001:** The `/graph` controls show an orthogonal-edges toggle in every overview layout; it is off by default.
- **AC-002:** Enabling the toggle applies `taxi` routing to all overview edges while preserving width, opacity, role styling, selection and underlay.
- **AC-003:** Disabling the toggle restores `bezier` routing.
- **AC-004:** The toggle is stored as `routing=orthogonal`, restores on reload and accepts `routing=curved`/missing as curved; invalid values fall back safely.
- **AC-005:** Toggling does not refetch data, change node positions, change the active layout/engine, filters or selection.
- **AC-006:** The toggle works with Force, Bipartite, Community, Coreness and Rings; the ego graph stays curved.
- **AC-007:** A forced style failure keeps a usable curved graph and shows a non-blocking notice.
- **AC-008:** The 398-node/968-node views remain usable with orthogonal routing enabled.
- **AC-009:** Frontend lint, typecheck, tests and build pass; headless checks cover both routing states and representative layouts.

## 10. Assumptions and open questions

### Assumptions

- "Global" means across all `/graph` overview layouts, not across the entire application or the producer ego graph.
- Cytoscape core `taxi` is sufficient; no new dependency is introduced.
- The initial visual uses sharp `taxi` routing. `round-taxi` is a possible later visual refinement.
- The toggle changes only edge presentation and therefore does not require a new API parameter or query key.
- No blocking questions remain for planning.

### Open questions

None blocking. The exact `taxi-turn-min-distance` value and any readability tuning are implementation details to validate in T-003.

## 11. Validation result

Not implemented. Acceptance evidence will be recorded in [tasks.md](tasks.md) after implementation.

## 12. References

- [SPEC-011 — Graph overview](../011-graph-visualization/spec.md)
- [SPEC-013 — Graph layout modes](../013-graph-layout-modes/spec.md)
- [SPEC-017 — Graph coreness and radial layouts](../017-graph-coreness-radial-layouts/spec.md)
- [Frontend architecture](../../docs/01-architecture/frontend.md)
- [Roadmap](../../docs/00-vision/roadmap.md)
