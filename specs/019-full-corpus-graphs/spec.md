# SPEC-019 — Full-corpus graph viewing and limits

- **Status:** Validated (revision 3)
- **Stage:** E13 follow-up
- **Iteration:** v0.3.1
- **Module:** `api`, `web`
- **Date:** 2026-11-19
- **Depends on:** [SPEC-016](../016-corpus-expansion/spec.md) (v0.3.0 dataset and analysis runs), SPEC-014
- **ADRs:** [ADR-0006](../../docs/01-architecture/adr/ADR-0006-read-only-api.md)
- **Plan:** [plan.md](plan.md)
- **Tasks:** [tasks.md](tasks.md)
- **Conventions:** [Engineering conventions](../../docs/01-architecture/conventions.md)
- **Owner:** Cristian

## 1. Context and problem

The v0.3.0 corpus contains 509 active bands and a much larger producer–album and producer–band graph than v0.2.0. The current graph UI has three limits that hide the corpus:

- the global overview is capped at 1,000 nodes and 2,000 edges;
- the band index in the overview requests only 200 bands;
- the producer ego graph limits neighbors to 100 and nodes to 500.

The complete all-bands view has 509 band entities and 1,708 nodes / 1,700 edges; 245 bands also have producer roles and share their node with the producer layer. The complete album layer has 3,719 nodes and 4,217 edges. The current 1,000-node cap truncates the view, and the index shows 200 rows even though the corpus has 509 bands.

The owner wants all bands visible in the graphs by default and wants to limit the number of bands or albums from the frontend when needed. The same limit model must apply to every graph view where bands or albums are represented.

## 2. Users and actors

- **Primary user:** the owner or any public reader exploring the corpus.
- **Developer/agent:** implements the API limits, selection semantics, frontend controls and performance evidence.
- **System actor:** the read-only API returns bounded graph responses; PostgreSQL remains the source of truth.

There are no user accounts or write operations.

## 3. User stories and flows

### US-001 — See all bands in the global graph

As a reader, I want the global band view to show all active bands by default so that the graph reflects the corpus rather than an arbitrary server cap.

**Expected flow:**

1. Open `/graph` in the Bands view.
2. The request uses all bands and all connected producers.
3. The canvas renders all 509 bands and their producer nodes (1,708 nodes / 1,700 edges) without truncation.
4. The overview states the node, edge and band counts.

### US-002 — Limit bands or albums from the frontend

As a reader, I want to choose a numeric limit or “All” for bands and albums so that I can control graph size without changing code.

**Expected flow:**

1. The overview exposes a numeric control for the active target type: bands in Bands view, albums in Albums view.
2. “All” sends limit `0`; a positive number sends that limit.
3. The limit is stored in the URL and survives refresh/back navigation.
4. Metadata reports the requested limit, returned target count and truncation state.

### US-003 — Control every graph

As a reader, I want the same control model in the producer ego graph and the band detail graph so that no graph silently hides data.

**Expected flow:**

1. The producer ego graph offers “All” or a finite neighbor limit, labelled Albums or Bands according to the view.
2. The band detail graph offers “All” or a finite producer limit.
3. Every graph displays a truncation notice only when the server safety cap is reached.

## 4. Functional requirements

### FR-001 — All bands in the global band view

The global Bands view must return all active bands in the selected dataset by default, together with their producer nodes. The v0.3.0 reference response is 509 bands and 1,708 nodes / 1,700 edges; bands that also produce share a producer/band node.

**Verification:** API integration test and a v0.3.0 reference check.

### FR-002 — Band and album limits

The global overview must accept:

- `band_limit`: `0` means all bands; a positive integer limits the number of band targets.
- `album_limit`: `0` means all albums; a positive integer limits the number of album targets.

A limit selects the top target nodes by aggregate edge weight, then by stable name/MBID order. The response must report the requested and returned counts.

**Verification:** API tests for `0`, `N`, `N > total` and invalid values.

### FR-003 — Default and explicit controls

The frontend defaults are:

- global Bands view: **All bands**;
- global Albums view: **500 albums**, with an explicit “All” option;
- global overview producers: **All producers**, with a typed limit from `1` to `1000` and fallback `100` when All is disabled;
- producer ego Bands view: **All neighbors**;
- producer ego Albums view: **100 neighbors**, with an explicit “All” option;
- band detail graph: **All producers**.

Numeric limits are entered in the frontend and stored in the URL. “All” is represented by `0`. The producer field commits on blur or Enter, not on each keystroke.

**Verification:** frontend unit tests and Playwright controls.

### FR-004 — Complete band index

The overview band index must show all bands in the selected corpus, not just 200. It may page through the existing `GET /api/v1/bands` endpoint or use a dedicated index endpoint.

**Verification:** frontend test with `total > 200` and a v0.3.0 manual count of 509 rows.

### FR-005 — Graph response metadata

Every graph response must include:

- requested band/album/producer limits;
- returned target counts;
- safety limits;
- `truncated` and, when applicable, the omitted count.

The frontend must display the truncation state and the loaded counts.

**Verification:** API schema tests, frontend unit tests and Playwright.

### FR-006 — Safety caps

The API must retain safety caps to prevent unbounded responses:

- global overview: `max_nodes` and `max_edges` up to 5,000;
- producer ego graph: `max_nodes` up to 2,000 and `max_edges` up to 5,000;
- band detail graph: `max_nodes` up to 2,000.

The frontend requests the cap needed for the selected limit, but never silently exceeds it.

**Verification:** API tests for allowed/rejected ranges and truncation metadata.

### FR-007 — Read-only contract preservation

The change must not modify canonical entities, ingestion, normalization, quality or analysis data. It may add optional query parameters and additive response metadata.

**Verification:** OpenAPI diff review, no migration, existing contract tests.

## 5. Non-functional requirements

### NFR-001 — Global band performance

The global band view must remain interactive with the full band layer: API p95 ≤ 2,000 ms and the full view must settle within 5,000 ms on the local reference environment.

### NFR-002 — Album view performance

The default 500-album view must reuse the existing performance targets. An explicit “All albums” view may use a static server layout if Force is too slow; any exception must be measured and documented.

### NFR-003 — Accessibility

The controls, truncation status and fallback tables must remain keyboard accessible and pass axe checks on all graph routes.

### NFR-004 — No schema change

No database migration or schema change is expected. The graph data model and analysis runs remain unchanged.

### NFR-005 — Compatibility

Existing API consumers that omit the new parameters must keep the current defaults and response shape, except for additive metadata. OpenAPI and TypeScript types must be regenerated.

## 6. Business rules

- **BR-001:** “All bands” is the default for every band view.
- **BR-002:** The global album view defaults to 500 albums; “All albums” is explicit.
- **BR-003:** A numeric limit selects target nodes deterministically by edge weight and stable identifier.
- **BR-004:** A graph must never silently omit data; truncation must be visible.
- **BR-005:** The server safety cap is a last-resort guard, not the primary UX limit.
- **BR-006:** The change does not alter the corpus, producer–album evidence or producer–band derivation.

## 7. Edge cases and errors

- **Limit 0:** means all targets.
- **Limit greater than the total:** returns the total and reports the actual returned count.
- **Limit 1:** returns one deterministic target and its connected nodes.
- **No target nodes:** returns the normal empty state.
- **Filtered graph:** limits apply after decade/subgenre filters.
- **Producer limit:** can reduce connected target nodes; the UI reports the resulting counts.
- **Safety cap reached:** set `truncated=true`, report omitted counts and show the UI notice.
- **Invalid/non-numeric limit:** HTTP 422 at the API boundary.
- **Large graph:** the frontend must not freeze; use a static layout when the measured cost exceeds the target.

## 8. Out of scope

- New graph types, producer–producer edges or album collaboration edges.
- Changing the network analysis, normalization, quality or ingestion logic.
- Database schema or migration changes.
- A complete mobile redesign.
- Server-side aggregation or cluster summaries in this iteration.
- E12 production deployment.

## 9. Acceptance criteria

| ID | Criterion | Evidence |
|---|---|---|
| AC-001 | Global Bands view returns all 509 bands and 1,708 nodes / 1,700 edges by default without truncation. | API test, v0.3.0 reference check |
| AC-002 | Global Albums view defaults to 500 albums; `album_limit=0` returns all 3,719 nodes / 4,217 edges. | API test, performance run |
| AC-003 | Frontend provides numeric plus “All” controls for bands and albums, persisted in the URL. | Vitest, Playwright |
| AC-004 | The overview band index shows all 509 bands, including after filtering. | Frontend test, manual v0.3.0 check |
| AC-005 | Producer ego and band detail graphs expose “All” and finite limits with visible counts and truncation state. | API tests, Playwright |
| AC-006 | Invalid limits return 422; safety caps and omitted counts are reported. | API tests |
| AC-007 | E2E and axe checks pass; full band and default album views meet the performance targets. The explicit all-albums view, view-switch acknowledgement and CoSE completion are documented measured exceptions. | Playwright, axe, performance report |
| AC-008 | No schema change, no migration and no change to canonical graph data. | Diff and migration review |
| AC-009 | OpenAPI and TypeScript types are regenerated and documentation reflects defaults and caps. | OpenAPI diff, docs review |

## 10. Assumptions and open questions

### Assumptions

- The owner approved the recommendation on 2026-11-19: all bands by default, all albums as an explicit option, numeric limits with “All”.
- The v0.3.0 all-bands graph is 1,708 nodes / 1,700 edges; the all-albums graph is 3,719 nodes / 4,217 edges.
- The band detail graph uses a producer limit because it does not represent multiple bands or albums.
- The overview canvas hides producers with degree zero in the selected subgraph by default; “Show isolated producers” reveals them.
- Album target nodes without a visible producer edge are not painted on the canvas.
- E2E fixture data remains the test data; full-corpus counts are verified against the local v0.3.0 analysis run.

### Open questions

| Question | Blocking? | Owner | Resolution |
|---|---|---|---|
| Should all albums be visible by default? | No | Cristian | No; 500 by default, All explicit. Approved 2026-11-19. |
| Does the band detail graph receive a limit? | No | Cristian | Yes; producer limit with All default. |
| Should limits be free numeric inputs or presets? | No | Cristian | Numeric with an explicit All control. |

## 11. Validation result

- **Date:** 2026-11-20
- **Verdict:** Validated (revision 3)
- **Evidence:** `tasks.md` records the API reference counts, backend 346 tests, frontend 127 tests, 27 Playwright/axe tests, the performance probe, the selection-stability regression and the documented exceptions.

## 12. References

- [SPEC-016 — v0.3.0 corpus](../016-corpus-expansion/spec.md)
- [Analysis v0.3.0](../../docs/03-data/analysis-v0.3.0.md)
- [QA report](../../docs/01-architecture/qa-report.md)
- [Roadmap](../../docs/00-vision/roadmap.md)
- [API conventions](../../docs/01-architecture/conventions.md)
- [ADR-0006 — read-only API](../../docs/01-architecture/adr/ADR-0006-read-only-api.md)


## 13. Revision history

| Revision | Date | Change |
|---|---|---|
| 1 | 2026-11-19 | Initial full-corpus graph viewing and limits. |
| 2 | 2026-11-20 | Stabilized chart selection so it does not recreate Cytoscape/restart the layout; hid producers outside the selected subgraph by default; prevented disconnected album targets from being painted. No API, schema or data change. |
| 3 | 2026-11-20 | Replaced the producer preset selector with a numeric field (1–1000, All, fallback 100) that commits on blur or Enter. No API or schema change. |
