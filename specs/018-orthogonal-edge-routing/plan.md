# SPEC-018 — Implementation plan

- **Status:** Plan/tasks in review
- **Spec:** [spec.md](spec.md)
- **Tasks:** [tasks.md](tasks.md)
- **Modules:** `web`
- **Depends on:** SPEC-011, SPEC-013

## 1. Solution summary

Add a global overview-level **Orthogonal edges** toggle. It switches Cytoscape edge styles between the existing `bezier` routing and core `taxi` orthogonal routing. The toggle is URL-backed with `routing=orthogonal`, is independent of the Layout selector and applies to every `/graph` layout. No backend, API, database or dependency change is needed.

## 2. Architecture and data flow

```text
URL routing=orthogonal|curved
        |
        v
ProducerOverviewPage
  - parse and validate routing
  - keep it out of the overview API request and query key
        |
        v
ProducerOverviewControls
  - labeled toggle
        |
        v
ProducerGraph / Cytoscape
  - toggle the `orthogonal` class on all overview edges
  - no re-layout, no refetch, no element recreation
        |
        v
Edge style: bezier (default) or taxi (orthogonal)
```

## 3. Components and files

| Area | File | Change |
|------|------|--------|
| Edge styles | `frontend/src/graph/styles.ts` | Add an `edge.orthogonal` style block with `curve-style: 'taxi'` and taxi geometry. |
| Overview graph | `frontend/src/components/ProducerGraph.tsx` | Accept the routing state; toggle the edge class in place; keep the current layout. |
| Controls | `frontend/src/components/ProducerOverviewControls.tsx` | Add the labeled `Orthogonal edges` toggle. |
| Page state | `frontend/src/pages/ProducerOverviewPage.tsx` | Parse `routing`; keep it out of the API request and query key; pass it to the graph. |
| Tests | Component/page tests, graph style tests | Toggle, URL, no-refetch, no-layout-change and fallback coverage. |

No backend files, migrations, generated API clients or dependencies are expected.

## 4. Technical decisions

### 4.1 Edge style

- Keep the base edge style as `curve-style: 'bezier'`.
- Add a class selector, for example `edge.orthogonal`, with:
  - `curve-style: 'taxi'`
  - `taxi-direction: 'auto'`
  - `taxi-turn: '50%'`
  - `taxi-turn-min-distance: 10`
- Use a class toggle rather than recreating edges or rewriting inline styles. This preserves selection, underlay and role classes.
- Do not change edge width, opacity, color, arrowheads, labels or z-index.
- Do not add `round-taxi` in this iteration.

### 4.2 State and URL contract

- Values: `orthogonal` and `curved`; missing means `curved`.
- Invalid values normalize to `curved`.
- The API request and TanStack Query key exclude `routing`; toggling must not refetch.
- The toggle is visible in every overview layout and does not depend on the active layout or force engine.
- The toggle is not added to the ego graph route or its graph component state.

### 4.3 In-place update and layout independence

- On toggle, run `cy.edges().toggleClass('orthogonal', enabled)`.
- Do not call `cy.layout(...)` or `runForce(...)`.
- Do not change the node positions, the active layout state or the force engine state.
- If the graph is recreated after a data/filter change, reapply the current routing class from state.
- Selection, detail panels, table and resize continue to use the existing graph.

### 4.4 Fallback

- If `taxi` is unavailable or style application throws, keep `bezier`, leave the toggle recoverable and show a non-blocking notice.
- The graph must remain usable; no empty canvas.
- Headless checks assert that enabled routing produces the orthogonal style class and that disabling removes it.

## 5. API and data model

No changes.

- `GET /api/v1/graph/producers` remains unchanged.
- No new fields, tables, migrations or OpenAPI output.
- No generated TypeScript API changes.

## 6. Frontend impact

- One new toggle in the overview controls.
- One new edge style class.
- URL parsing and passing state through the existing page/graph boundary.
- Existing layouts, filters, engines, selection and details are unchanged.
- No new CSS framework or dependency.

## 7. Error handling

| Condition | Behavior |
|-----------|----------|
| Invalid `routing` value | Use curved; no error. |
| `taxi` unavailable | Keep curved; non-blocking notice. |
| Style application throws | Keep curved; non-blocking notice. |
| Toggle during a running layout | Apply the class; do not interrupt or restart the layout. |
| Dense graph with many crossings | Keep the toggle usable; no blocking error. |

## 8. Security, privacy and provenance

No change. The feature reads the existing read-only overview response and makes no new network request. No user data is persisted.

## 9. Observability

No new logs or metrics. Existing client errors remain visible through the current graph error/notice path.

## 10. Testing strategy

| Layer | Coverage |
|-------|----------|
| Unit/style | `edge.orthogonal` carries the expected taxi properties; base edges remain bezier. |
| Component | Toggle label, checked state, keyboard use, class toggling and no layout call. |
| Integration/page | URL round-trip, invalid value fallback, query-key stability and no refetch. |
| Headless | Curved/orthogonal at 398 and 968 nodes; representative Force/Bipartite/Community/Coreness/Rings views; resize. |
| Regression | Selection, underlay, details, filters, ego graph and all layouts unchanged. |

Commands:

```bash
cd frontend
npm run lint
npm run typecheck
npm run test
npm run build
```

## 11. Deployment and reversibility

Frontend-only change. No migration, flag or environment variable. Reverting the frontend commit restores the previous curved-only behavior. Existing URLs remain valid; `routing` is additive.

## 12. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Dense orthogonal edges are harder to read | Validate at 398/968 nodes; tune `taxi-turn-min-distance`; keep curved default. |
| Toggle triggers a layout or refetch | Explicit no-layout/no-refetch requirement and integration tests. |
| Class specificity fails to override bezier | Style unit test plus headless computed-style check. |
| State lost when the graph is recreated | Reapply the routing class from page state after graph creation. |
| Scope creep into edge bundling or routing around labels | Out-of-scope list; use Cytoscape `taxi` only. |
| Ego graph changes accidentally | Scope and regression checks. |

## 13. Traceability

| Requirement | Design/test |
|-------------|-------------|
| FR-001 | 4.2, controls tests |
| FR-002 | 4.1, style/headless tests |
| FR-003 | 4.2, URL tests |
| FR-004 | 4.3, integration tests |
| FR-005 | 4.2, 4.3, regression checks |
| FR-006 | 4.4, forced-failure tests |
| FR-007 | Controls tests, accessibility check |
| NFR-001–NFR-004 | Testing strategy, performance/headless checks, dependency review |

## 14. Approval

Plan ready for review. Implementation is not authorized until the spec, plan and tasks are approved.
