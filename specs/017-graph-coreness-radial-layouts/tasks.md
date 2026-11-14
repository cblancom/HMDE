# SPEC-017 — Tasks

- **Status:** Plan/tasks in review
- **Spec:** [spec.md](spec.md)
- **Plan:** [plan.md](plan.md)
- **Modules:** `web`

## 1. Execution order

```text
T-001 -> T-002 -> T-003 -> T-004 -> T-005
```

## 2. Tasks

### T-001 — Implement the coreness utility

- **Requirements:** FR-002, NFR-001
- **Depends on:** none
- **Description:** Add `frontend/src/graph/coreness.ts` with a bucket-based k-core peeling function over unique neighbors. Return coreness 0 for isolated nodes and preserve deterministic behavior.
- **Files:** `frontend/src/graph/coreness.ts`, `frontend/src/graph/coreness.test.ts`
- **Done when:** Unit tests cover empty, single node, isolated nodes, path/leaf, cycle, dense core, duplicate neighbors, disconnected components and deterministic tie behavior.
- **Verification:** `cd frontend && npm run test -- coreness`
- **Evidence:** Pending.

### T-002 — Implement Rings metric scores

- **Requirements:** FR-006, FR-007, NFR-001
- **Depends on:** T-001
- **Description:** Add metric types, validation and score builders for `betweenness`, `coreness`, `degree` and `producer-connectivity`. Normalize values, handle missing/non-finite betweenness and build the producer projection from shared band/album targets.
- **Files:** `frontend/src/graph/radialLayouts.ts`, `frontend/src/graph/radialLayouts.test.ts`
- **Done when:** Unit tests verify each metric, projection adjacency, normalization, missing values, tie-breaking and the bounded type/score ranges.
- **Verification:** `cd frontend && npm run test -- radialLayouts`
- **Evidence:** Pending.

### T-003 — Add Coreness and Rings to the overview

- **Requirements:** FR-001, FR-003, FR-004, FR-009, FR-010, NFR-002, NFR-003
- **Depends on:** T-001, T-002
- **Description:** Extend the client layout state, controls and `ProducerGraph` integration. Run static `concentric` for Coreness/Rings, disable Freeze/Resume/Reheat, add the Rings metric dropdown and keep the new modes out of the overview API request.
- **Files:** `frontend/src/pages/ProducerOverviewPage.tsx`, `frontend/src/components/ProducerOverviewControls.tsx`, `frontend/src/components/ProducerGraph.tsx`, `frontend/src/index.css` (only if needed), related tests
- **Done when:** The selector, URL state, status text, metric control, score-before-filter behavior and static layout work in component and page tests.
- **Verification:** `cd frontend && npm run test -- ProducerOverview`
- **Evidence:** Pending.

### T-004 — Implement URL state and fallback behavior

- **Requirements:** FR-005, FR-008, FR-011, AC-005, AC-008
- **Depends on:** T-003
- **Description:** Validate `layout=coreness|rings` and `ring_metric`, restore state on reload, ensure no API refetch on mode/metric changes, and implement the `breadthfirst`/Force fallback with a non-blocking notice.
- **Files:** `frontend/src/pages/ProducerOverviewPage.tsx`, `frontend/src/components/ProducerGraph.tsx`, related tests
- **Done when:** URL round-trip, invalid values, query-key stability and forced-failure fallback tests pass.
- **Verification:** `cd frontend && npm run test -- ProducerOverview`
- **Evidence:** Pending.

### T-005 — Run headless and full frontend verification

- **Requirements:** AC-003, AC-004, AC-006, AC-007, AC-009, AC-010, AC-011, NFR-002
- **Depends on:** T-004
- **Description:** Run headless browser checks for Coreness and Rings at the current 398-node and 968-node views, switch metrics, resize and confirm selection/details and the ego graph remain unchanged. Record evidence and update the spec result.
- **Files:** `specs/017-graph-coreness-radial-layouts/tasks.md`, `specs/017-graph-coreness-radial-layouts/spec.md`, relevant implementation files
- **Done when:** The manual/headless checks and the full frontend suite pass; evidence is recorded.
- **Verification:** `cd frontend && npm run lint && npm run typecheck && npm run test && npm run build`
- **Evidence:** Pending.

## 3. Coverage

| Requirement | Tasks |
|-------------|-------|
| FR-001 | T-003, T-004 |
| FR-002 | T-001 |
| FR-003 | T-001, T-003 |
| FR-004 | T-002, T-003 |
| FR-005 | T-003, T-004 |
| FR-006 | T-002 |
| FR-007 | T-002 |
| FR-008 | T-003, T-004 |
| FR-009 | T-003 |
| FR-010 | T-003 |
| FR-011 | T-004 |
| FR-012 | T-003, T-004, T-005 |
| NFR-001 | T-001, T-002 |
| NFR-002 | T-003, T-005 |
| NFR-003 | T-003, T-005 |
| NFR-004 | T-001, T-003 |

## 4. Validation evidence

Not implemented. No task has been started.

## 5. Notes

- This spec is independent of SPEC-018. Orthogonal edge routing must not be implemented here.
- Do not change the overview API layout contract or add a migration for client-only modes.
- Coreness mode describes structural embedding, not producer-to-producer connectivity.
