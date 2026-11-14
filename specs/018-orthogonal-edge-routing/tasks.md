# SPEC-018 — Tasks

- **Status:** Plan/tasks in review
- **Spec:** [spec.md](spec.md)
- **Plan:** [plan.md](plan.md)
- **Modules:** `web`

## 1. Execution order

```text
T-001 -> T-002 -> T-003
```

## 2. Tasks

### T-001 — Add the orthogonal edge style

- **Requirements:** FR-002, FR-006, NFR-002, NFR-003
- **Depends on:** none
- **Description:** Add the `edge.orthogonal` Cytoscape style with `taxi` routing and taxi geometry while keeping the base edge style curved. Ensure role, selection and underlay styles are not overridden.
- **Files:** `frontend/src/graph/styles.ts`, style tests
- **Done when:** Style tests confirm the base `bezier` and orthogonal `taxi` properties, and no unrelated edge styles change.
- **Verification:** `cd frontend && npm run test -- styles`
- **Evidence:** Pending.

### T-002 — Add the global toggle and URL state

- **Requirements:** FR-001, FR-003, FR-004, FR-005, FR-007
- **Depends on:** T-001
- **Description:** Add the labeled `Orthogonal edges` toggle to the overview controls, parse `routing` on the page, keep it out of the API request/query key and toggle the edge class in place without re-layout or refetch.
- **Files:** `frontend/src/pages/ProducerOverviewPage.tsx`, `frontend/src/components/ProducerOverviewControls.tsx`, `frontend/src/components/ProducerGraph.tsx`, related tests
- **Done when:** Component/page tests cover default off, URL round-trip, invalid value fallback, keyboard operation, no refetch, no layout call and state restoration after graph recreation.
- **Verification:** `cd frontend && npm run test -- ProducerOverview`
- **Evidence:** Pending.

### T-003 — Implement fallback, headless checks and full verification

- **Requirements:** FR-006, AC-005, AC-006, AC-007, AC-008, AC-009, NFR-001, NFR-004
- **Depends on:** T-002
- **Description:** Implement the curved fallback and notice, then run headless checks for curved/orthogonal at 398 and 968 nodes across representative layouts, including resize, selection, details and the unchanged ego graph.
- **Files:** implementation files, `specs/018-orthogonal-edge-routing/tasks.md`, `specs/018-orthogonal-edge-routing/spec.md`
- **Done when:** Fallback tests and headless checks pass; full frontend lint, typecheck, tests and build pass; evidence is recorded.
- **Verification:** `cd frontend && npm run lint && npm run typecheck && npm run test && npm run build`
- **Evidence:** Pending.

## 3. Coverage

| Requirement | Tasks |
|-------------|-------|
| FR-001 | T-002 |
| FR-002 | T-001 |
| FR-003 | T-002 |
| FR-004 | T-002 |
| FR-005 | T-002, T-003 |
| FR-006 | T-001, T-003 |
| FR-007 | T-002 |
| NFR-001 | T-003 |
| NFR-002 | T-001, T-003 |
| NFR-003 | T-001 |
| NFR-004 | T-002, T-003 |

## 4. Validation evidence

Not implemented. No task has been started.

## 5. Notes

- This spec is independent of SPEC-017. Do not add layout modes here.
- Orthogonal routing is a presentation toggle, not a Layout option.
- The producer ego graph and the API contract must remain unchanged.
