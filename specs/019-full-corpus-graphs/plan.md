# Technical plan — SPEC-019

- **Status:** Validated
- **Spec:** [spec.md](spec.md)
- **Tasks:** [tasks.md](tasks.md)
- **ADRs:** [ADR-0006](../../docs/01-architecture/adr/ADR-0006-read-only-api.md)
- **Module:** `api`, `web`

## 1. Solution summary

Extend the read-only graph contract so a reader can see the complete band layer by default and explicitly choose a numeric limit for bands or albums. The v0.3.0 all-bands view is 1,708 nodes / 1,700 edges; the album layer is 3,719 nodes / 4,217 edges. The band count includes 245 bands that also have producer roles and share a node.

The default is all 509 bands with all connected producers. The global album view defaults to 500 albums and offers “All” explicitly. Producer ego graphs default to all bands and to 100 albums, with “All” available. The band detail graph defaults to all producers.

The change is additive: new query parameters and response metadata, no schema, no canonical data change and no ingestion/normalization/quality/analysis change. Existing API consumers that omit the new parameters keep current defaults, except that the frontend explicitly requests the new full-corpus settings.

Phase 0, the E2E seed membership fix, is already complete so CI can validate this work.

## 2. Architecture and data flow

```text
PostgreSQL graph layers
        │
        ▼
producer/overview services
  • select producer set
  • select band/album target set
  • apply deterministic target limit
  • apply safety cap and truncation metadata
        │
        ▼
GET /api/v1/graph/producers
GET /api/v1/producers/:id/graph
GET /api/v1/bands/:id/graph
        │
        ▼
React graph pages
  • numeric/All controls in URL
  • request target limits and safety caps
  • render full graph when All is selected
  • show loaded counts and truncation notice
  • page through bands index until total is reached
```

## 3. Components and responsibilities

| Component or path | Responsibility |
|---|---|
| `backend/src/hmde/api/routes/graph.py` | Add `band_limit`/`album_limit`, raise safety-cap ranges and expose metadata. |
| `backend/src/hmde/api/routes/producers.py` | Allow `limit=0` for all ego neighbors and raise ego safety caps. |
| `backend/src/hmde/api/routes/bands.py` | Add an optional producer limit to the band detail graph if confirmed. |
| `backend/src/hmde/services/producers.py` | Deterministic target selection, full-layer selection and truncation metadata. |
| `backend/src/hmde/services/graph.py` | Band detail producer limit and ordering. |
| `backend/src/hmde/schemas/api.py` | Additive limit metadata in graph response schemas. |
| `frontend/src/pages/ProducerOverviewPage.tsx` | Defaults, URL limits, all-band index and full-corpus requests. |
| `frontend/src/components/ProducerOverviewControls.tsx` | Numeric plus All controls for bands and albums. |
| `frontend/src/components/OverviewIndex.tsx` | Show all 509 bands from the paged index. |
| `frontend/src/pages/ProducerGraphPage.tsx` | Defaults and URL controls for ego all/limited neighbors. |
| `frontend/src/components/GraphControls.tsx` | All/numeric neighbor control with Albums/Bands label. |
| `frontend/src/pages/BandDetailPage.tsx` | Producer limit control for the band detail graph. |
| `frontend/e2e/performance.spec.ts` | Full-corpus performance and large-layout evidence. |
| `docs/01-architecture/qa-report.md` | Record full-corpus performance and any exception. |
| `docs/03-data/analysis-v0.3.0.md` | Record graph counts and viewing limitations. |
| `specs/019-full-corpus-graphs/` | Spec, plan and task evidence. |

## 4. Technical decisions and alternatives

### 4.1 Decision — defaults

- Global Bands: all bands.
- Global Albums: 500 albums; All is explicit.
- Producer ego Bands: all neighbors.
- Producer ego Albums: 100 neighbors; All is explicit.
- Band detail: all producers.

**Rationale:** all bands are the primary requirement and fit in 1,708 nodes. Showing all 3,719 album nodes by default would make the initial view unnecessarily expensive; the explicit option preserves access.

### 4.2 Decision — target limits

Add `band_limit` and `album_limit` to the global overview, with `0` meaning all. The selected target set is ordered by aggregate edge weight and stable identifier before applying the limit. The producer limit remains independent.

**Rationale:** a numeric limit must be deterministic and must not depend on database row order.

### 4.3 Decision — safety caps

- Overview: `max_nodes` and `max_edges` ≤ 5,000.
- Producer ego: `max_nodes` ≤ 2,000, `max_edges` ≤ 5,000.
- Band detail: `max_nodes` ≤ 2,000.

The frontend requests the cap needed for the selected limit. The server marks `truncated` only when the safety cap actually omits data.

**Rationale:** the UI target limits handle normal use; safety caps prevent pathological responses.

### 4.4 Decision — large-graph rendering

The overview defaults to the server-generated static bipartite layout for both Bands and Albums. Force remains an explicit opt-in. The measured all-bands and default-album views meet the five-second target with this default; the explicit all-albums view remains a documented exception.

**Rationale:** all bands and albums remain available without paying the Force simulation cost on every load. Force is retained for readers who want it.

### 4.5 Alternatives considered

| Alternative | Reason for rejection |
|---|---|
| Raise the list endpoint limit to 1,000 and request all bands in the index | Changes the established pagination contract; client paging is sufficient. |
| Show all albums by default | Too expensive for the initial view; explicit All preserves access. |
| Raise only `max_nodes` without target limits | Gives no user control and does not solve the index limit. |
| Keep 200-band index and show “200 of 509” | Does not meet “see all bands”. |
| Add a new graph database or precomputed band-only graph | Not needed for this scope; would add architecture without evidence. |
| Remove safety caps | Unbounded responses can exhaust memory and freeze the browser. |

## 5. Data model and migrations

- No new tables, columns, constraints or indexes.
- No Alembic migration.
- No canonical data changes.
- The existing graph nodes, edges, analysis runs and dataset membership remain the source of truth.
- E2E seed membership is already seeded by Phase 0.

## 6. API contract

### 6.1 Global overview

`GET /api/v1/graph/producers`

New optional parameters:

- `band_limit`: integer ≥ 0; `0` = all bands.
- `album_limit`: integer ≥ 0; `0` = all albums.

Changed ranges:

- `max_nodes`: 1–5,000.
- `max_edges`: 1–5,000.

Response metadata additions:

- requested band/album limits;
- returned band/album counts;
- safety limits;
- `truncated` and omitted count.

Existing parameters remain unchanged: `view`, `producer_limit`, `producer_sort`, `order`, `decade`, `subgenre`, `include_isolated`, `include_evidence`, `layout`.

### 6.2 Producer ego graph

`GET /api/v1/producers/{id}/graph`

- Allow `limit=0` for all neighbors.
- Raise `max_nodes` to 2,000 and `max_edges` to 5,000.
- Include the requested/returned neighbor count and truncation metadata.

### 6.3 Band detail graph

`GET /api/v1/bands/{id}/graph`

- Add optional `producer_limit`, `0` = all producers.
- Add `max_nodes` up to 2,000.
- Include the producer count and truncation metadata.

### 6.4 Compatibility

All changes are additive. Omitting the new parameters preserves current defaults. OpenAPI and `frontend/src/api/schema.d.ts` must be regenerated.

## 7. Frontend impact

### Overview

- Add numeric inputs with an “All” checkbox for Bands and Albums.
- Send `band_limit`/`album_limit=0` for All.
- Put limits in URL state.
- Request `max_nodes=5000` and `max_edges=5000` for the overview.
- Fetch bands index pages of 200 until `total` is reached; use all rows.
- Display total bands, returned bands and truncation state.

### Producer ego

- Replace the fixed 20/50/100 selector with All plus a numeric limit.
- Label the selector Albums or Bands according to the active view.
- Request a cap large enough for the selected limit.

### Band detail

- Add a producer limit control with All as the default.
- Show the producer count and any truncation.

### Loading and accessibility

- Preserve loading, error and empty states.
- Keep controls keyboard accessible and labelled.
- Keep the accessible table fallback.
- Report large-graph truncation in text, not only visually.

## 8. Error handling and consistency

- Invalid numeric limits return 422 before graph construction.
- A limit greater than the available total returns all available targets and reports the actual count.
- Empty filtered results preserve the existing empty state.
- If the safety cap is reached, set `truncated=true` and report omitted counts; never silently return a smaller graph.
- No transaction or write behavior changes; the API remains read-only.
- URL state and query keys include all limits so caching cannot return a response for different limits.

## 9. Security and trust boundaries

- No authentication or authorization change.
- Validate all numeric query parameters at the API boundary.
- Keep the API read-only and CORS behavior unchanged.
- Do not expose raw data or provenance that is not already in the graph contract.
- The graph data remains derived from the versioned analysis run.

## 10. Observability

- Record requested limits and returned/omitted counts in graph response metadata.
- Extend the performance report with full-band and default/full-album measurements.
- Record the v0.3.0 reference counts: 509 bands, 1,708/1,700 all-bands nodes/edges, 3,719/4,217 album-layer nodes/edges.
- Link the performance evidence from `docs/01-architecture/qa-report.md`.

## 11. Testing strategy

| Level | What is tested | Evidence |
|---|---|---|
| Unit | Limit parsing, deterministic target selection and metadata | `backend/tests/unit/` |
| Integration | Overview all/limited bands and albums; ego all/limited neighbors; band producer limit; safety caps | `backend/tests/integration/` |
| Contract | OpenAPI and TypeScript regeneration; additive response fields | `test_openapi.py`, generated schema |
| Frontend | Numeric/All controls, URL state, index paging beyond 200 | `frontend/src/**/*.test.tsx` |
| End-to-end | Controls, all-bands view, ego all, band detail limit, truncation notices | `frontend/e2e/` |
| Performance | Full band default, default 500 albums, explicit all albums, layout timings | `frontend/test-results/performance-*/performance-report.json` |
| Manual | v0.3.0 count verification | Local run |

Commands:

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run pytest

cd ../frontend
npm run lint
npm run typecheck
npm run test
npm run build
npm run test:e2e
npm run test:perf
```

## 12. Deployment and reversibility

- No migration order applies.
- No new environment variables.
- The frontend can roll back to `max_nodes=1000` and default limits without a data change.
- The API additions are backward-compatible; reverting the frontend restores the previous graph behavior.
- Do not delete existing analysis runs or graph data.

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Full album view freezes the browser | Default to 500 albums; measure All; use static layout or an explicit warning if needed. |
| Full band view exceeds API target | Measure 1,708/1,700; keep an exception only if documented and accepted. |
| Index loads 509 rows slowly | Page through 200-row responses and reuse the existing list query; virtualize only if measurement requires it. |
| Limits produce confusing target counts | Report requested/returned/omitted counts in the UI. |
| A limit hides bands unexpectedly | Default to All bands; when a producer limit is also set, show the resulting band count. |
| API contract drift | Regenerate OpenAPI and TypeScript types; update contract tests. |

## 14. Traceability requirements → plan → tasks

| Requirement | Plan section | Tasks |
|---|---|---|
| FR-001 | 4.1, 6.1 | T-002, T-003, T-007 |
| FR-002 | 4.2, 6.1 | T-001, T-002 |
| FR-003 | 4.1, 7 | T-003, T-004 |
| FR-004 | 7 | T-003 |
| FR-005 | 6, 7 | T-001, T-003, T-004 |
| FR-006 | 4.3, 6 | T-001, T-002 |
| FR-007 | 5, 6.4 | T-001, T-006 |
| NFR-001 | 4.1, 11 | T-005 |
| NFR-002 | 4.4, 11 | T-005 |
| NFR-003 | 7, 11 | T-004, T-006 |
| NFR-004 | 5 | T-006 |
| NFR-005 | 6.4 | T-001, T-006 |
| AC-001 | 4.1, 6.1 | T-002, T-007 |
| AC-002 | 4.1, 4.2 | T-002, T-005 |
| AC-003 | 7 | T-003, T-004 |
| AC-004 | 7 | T-003 |
| AC-005 | 6.2, 6.3 | T-004 |
| AC-006 | 4.3, 8 | T-001, T-002 |
| AC-007 | 11 | T-005, T-006 |
| AC-008 | 5 | T-006 |
| AC-009 | 6.4, 11 | T-001, T-006, T-007 |

## 15. Approval and next step

Phase 0 and T-001–T-008 are complete. Revision 2 stabilizes selection and filters out-of-subset producers by default. The implementation is validated and the performance exceptions are recorded in the QA report.
