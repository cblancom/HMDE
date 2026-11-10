# Technical plan — SPEC-009 Read-only API v1

- **Status:** Approved
- **Spec:** [spec.md](spec.md)
- **Tasks:** [tasks.md](tasks.md)
- **Stage:** E8
- **Module:** `api`
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0003](../../docs/01-architecture/adr/ADR-0003-synchronous-sqlalchemy.md), [ADR-0005](../../docs/01-architecture/adr/ADR-0005-identity-and-provenance.md), [ADR-0006](../../docs/01-architecture/adr/ADR-0006-read-only-api.md), [ADR-0007](../../docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md), [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)

## 1. Solution summary

SPEC-009 adds a read-only `/api/v1` contract over the validated canonical corpus and the E7 analytical snapshots. It extends the E2 band API with artists, albums, credits, producers, search, taxonomy, analysis-run metadata, analytics and bounded producer subgraphs.

The API reads persisted data only. It never ingests, normalizes, runs quality checks, builds graphs, recomputes metrics or mutates rows. E7 remains the source of graph layers and metrics; E8 resolves a completed `analysis_run` and shapes read models for E9/E10.

```text
canonical E4/E5 tables                  E7 analytical tables
bands · artists · albums · credits      analysis_run · graph layers
taxonomy · membership                   metrics · communities
            │                                      │
            └──────────────┬───────────────────────┘
                           ▼
                FastAPI /api/v1 read services
        entities · search · taxonomy · analytics
        producer rankings · bounded graph views
                           │
                ┌──────────┴──────────┐
                ▼                     ▼
            E9 explorer           E10 graph UI
```

No new dependency is required. CORS uses Starlette middleware already available through FastAPI.

## 2. Architecture and data flow

### 2.1 Request flow

1. FastAPI validates path/query parameters with Pydantic/FastAPI constraints.
2. The route delegates to a read service.
3. Entity endpoints read canonical E4/E5 tables.
4. Analytics/graph endpoints resolve the selected E7 `analysis_run`.
5. The service performs bounded SQL queries and maps rows to response schemas.
6. The response includes pagination/truncation metadata or analysis-run metadata.
7. No write transaction is opened.

### 2.2 Package layout

```text
backend/src/hmde/api/
├── dependencies.py       analysis-run resolution and common query dependencies
├── pagination.py         limit/offset/sort helpers and response metadata
└── routes/
    ├── bands.py           existing E2 endpoints, extended filters
    ├── artists.py         generic artist detail
    ├── albums.py          album list/detail
    ├── producers.py       producer list/detail and bounded graph views
    ├── credits.py         credit list
    ├── search.py          grouped search
    ├── taxonomy.py        versioned taxonomy
    ├── analytics.py       runs, summary, decades, communities
    └── health.py          existing health

backend/src/hmde/schemas/
├── band.py               extended band schemas
├── artist.py             artist detail
├── album.py              album list/detail and credits
├── producer.py           producer list/detail and metrics
├── graph.py              producer graph views and limits
├── taxonomy.py           taxonomy nodes
└── analytics.py          run metadata, summary, decades, communities

backend/src/hmde/services/
├── catalog.py            existing band services, extended
├── artists.py            artist detail
├── albums.py             album list/detail
├── credits.py            credit filters and support mapping
├── producers.py          producer rankings/detail
├── producer_graph.py     bounded graph retrieval from E7 rows
├── search.py             grouped SQL search
├── taxonomy.py           hierarchy and descendant filters
└── analytics.py          run selection, summary, decades, communities
```

The API layer may import `models`, `db`, `core` and services. It must not import ETL, normalization, quality or graph-construction code.

## 3. Components and responsibilities

| Component or path | Responsibility |
|---|---|
| `backend/src/hmde/api/routes/` | HTTP resources, query validation and status codes. |
| `backend/src/hmde/schemas/` | Pydantic v2 response/request contracts and graph limits. |
| `backend/src/hmde/services/` | Read-only SQL and row-to-schema mapping. |
| `backend/src/hmde/api/dependencies.py` | Resolve latest/explicit completed E7 run. |
| `backend/src/hmde/api/pagination.py` | Shared limit/offset/sort metadata. |
| `backend/src/hmde/core/config.py` | Configurable CORS origins. |
| `backend/src/hmde/main.py` | CORS middleware and router registration. |
| `openapi.json` | Generated contract snapshot. |
| `frontend/src/api/schema.d.ts` | Generated TypeScript contract (no UI changes). |
| `backend/tests/unit/test_api_*.py` | Schema, pagination, run-selection and service tests. |
| `backend/tests/integration/test_api_*.py` | Endpoint, E7 fixture, error, CORS and query-count tests. |
| `README.md`, `AGENTS.md`, `docs/01-architecture/`, `docs/03-data/`, `specs/README.md` | API docs, status and contract references. |

## 4. Technical decisions and alternatives

### 4.1 Preserve E2 endpoints

Existing `/health`, `/api/v1/bands`, `/api/v1/bands/{id}` and `/api/v1/bands/{id}/graph` remain available. New query parameters are optional. Existing response fields are not removed.

Alternative rejected: replacing E2 endpoints. It would break the current frontend and contract tests without product benefit.

### 4.2 Analysis-run resolution

A shared dependency resolves the run:

- explicit `analysis_run` query parameter wins;
- otherwise latest `completed`/`completed_with_limitations` by `finished_at`/`started_at`;
- missing run: `503`;
- explicit id missing: `404`;
- explicit run non-terminal: `409`;
- run metadata is attached to the response `meta`.

Entity endpoints do not require a run. Producer/analytics/graph endpoints do.

Alternative rejected: recomputing the latest graph in the request. It violates E7 and ADR-0001.

### 4.3 Read models and query shape

- Entity services use explicit `select` statements and bounded joins.
- Producer list/detail reads `graph_node`, `producer_metric`, `node_metric`, `community_membership` and `community`.
- Graph views read only the selected layer in `graph_node`/`graph_edge`.
- Evidence JSON is summarized; full evidence is optional and bounded.
- No N+1 loops; graph endpoints use at most a small fixed number of queries.

### 4.4 Separate graph views

`GET /api/v1/producers/{id}/graph?view=albums|bands`:

- `albums`: producer + album nodes, `producer_album` edges only.
- `bands`: producer + band/artist nodes, `producer_band` edges only.
- No mixed album/band response, no album–album projection.
- `limit` selects the seed producer's top neighbors; E10 expands from there.
- `depth` is limited to 2; `max_nodes=500`, `max_edges=2000`.
- Truncation is explicit in `meta.truncated`.

Alternative rejected: one unified graph response. It recreates the mixed-node saturation problem rejected in SPEC-008.

### 4.5 Pagination and sorting

Shared pagination helper:

- `limit` default 20, max 200 for list resources;
- graph `limit` default 20, max 100;
- `offset` >= 0;
- whitelisted sort fields per resource;
- stable ID tie-breaker;
- `total` from a count query.

### 4.6 Retired bands

`dataset_membership` provides lifecycle. Default `/bands` and search exclude retired bands. Direct band detail remains accessible by ID, including historical albums/credits. `include_retired=true` is an explicit list/search option.

### 4.7 Taxonomy filters

- `/taxonomy` returns the selected versioned hierarchy.
- Parent filter requests resolve descendants from `taxonomy_node`.
- Album filters use `release_group_subgenre`; band filters use `artist_subgenre`/aggregate classification.
- Unknown codes return `422` with a clear message.
- Taxonomy version must match the selected run for analytics and the current projection for entity endpoints.

### 4.8 Search

SQL-backed grouped search with `ILIKE` and bounded results:

- bands/artists by name;
- albums by title;
- producers by canonical artist name;
- grouped response sections;
- `limit` overall and per group;
- no external search service.

### 4.9 CORS

Add a configurable `CORS_ORIGINS` setting (comma-separated) and Starlette `CORSMiddleware`:

- development default may include `http://localhost:5173`/`http://127.0.0.1:5173`;
- production uses explicit origins;
- allow credentials only if required; v1 has no auth and no cookies;
- API remains read-only.

### 4.10 OpenAPI and types

- Update `openapi.json` from FastAPI.
- Run `npm run generate:api`.
- CI OpenAPI drift must pass.
- No frontend pages or components are added in E8; only generated types may change.

## 5. Data model and migrations

- No schema change planned.
- Reads:
  - `artist`, `artist_subgenre`, `release_group`, `release`, `recording`, `credit`, `role`, `release_group_subgenre`, `taxonomy_node`, `taxonomy_version`, `dataset_membership`;
  - `analysis_run`, `graph_node`, `graph_edge`, `node_metric`, `producer_metric`, `temporal_metric`, `community`, `community_membership`.
- If measured query plans require an index, it must be additive and approved separately.
- No canonical, normalization, quality or analytical mutation.

## 6. API contract

### 6.1 Resources

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Existing health check |
| GET | `/api/v1/bands` | Band list/search/filter, retired behavior |
| GET | `/api/v1/bands/{band_id}` | Band detail |
| GET | `/api/v1/bands/{band_id}/graph` | Existing E2 one-hop graph |
| GET | `/api/v1/artists/{artist_id}` | Generic canonical artist detail |
| GET | `/api/v1/producers` | Producer ranking/list |
| GET | `/api/v1/producers/{producer_id}` | Producer detail and metrics |
| GET | `/api/v1/producers/{producer_id}/graph` | Bounded `albums`/`bands` view |
| GET | `/api/v1/albums` | Album list/search/filter |
| GET | `/api/v1/albums/{album_id}` | Album detail and credits |
| GET | `/api/v1/credits` | Credit list/filter |
| GET | `/api/v1/search` | Grouped cross-entity search |
| GET | `/api/v1/taxonomy` | Versioned taxonomy |
| GET | `/api/v1/analysis-runs` | E7 run list |
| GET | `/api/v1/analysis-runs/{run_id}` | E7 run detail |
| GET | `/api/v1/analytics/summary` | Graph/support/concentration summary |
| GET | `/api/v1/analytics/decades` | Temporal metrics |
| GET | `/api/v1/communities` | Community list |
| GET | `/api/v1/communities/{key}` | Community detail/members |

### 6.2 Common response shapes

List:

```json
{"items": [], "total": 0, "limit": 20, "offset": 0}
```

Analytics graph:

```json
{
  "nodes": [],
  "edges": [],
  "meta": {
    "view": "bands",
    "analysis_run_id": "...",
    "analysis_version": "net-...",
    "dataset_version": "...",
    "taxonomy_version": "...",
    "graph_version": "...",
    "truncated": false,
    "limits": {"limit": 20, "depth": 1, "max_nodes": 500, "max_edges": 2000}
  }
}
```

Errors remain FastAPI `{"detail": "..."}` in v1.

### 6.3 Limits

- List `limit`: max 200.
- Graph `limit`: max 100.
- Graph `depth`: max 2.
- `max_nodes`: 500.
- `max_edges`: 2000.
- `include_evidence=true` may add bounded album summaries but never raw payloads.

## 7. Frontend impact

No E8 UI.

- Generated `frontend/src/api/schema.d.ts` may change.
- E9 consumes the new contract.
- E10 consumes the graph endpoints and metadata.
- No route/component changes in E8.

## 8. Error handling and consistency

- Invalid path/query: `422`.
- Unknown entity: `404`.
- Invalid taxonomy code/filter combination: `422` or documented empty result; must be consistent.
- No completed run: `503`.
- Explicit missing run: `404`.
- Explicit non-terminal run: `409`.
- Empty result: `200` with `items=[]`/empty graph, except missing run.
- Truncated graph: `200` with `meta.truncated=true`.
- Database error: `503`, no internal detail.
- Retired band direct detail: `200`.
- No write transactions.

## 9. Security and trust boundaries

- Public read-only API; no auth in v1.
- No secrets, raw payloads, SQL or stack traces in responses.
- Query parameters are bounded and whitelisted.
- CORS origins are explicit; no wildcard in production.
- No write routes; route inspection test enforces GET-only.
- Source attribution fields remain available where already present; no new licensing exposure.

## 10. Observability

- Existing structured logging remains.
- Log slow queries/requests and analysis-run selection at info/warn level without payloads.
- Health endpoint remains.
- No new metrics/tracing dependency in E8.

## 11. Testing strategy

| Level | What is tested | Evidence |
|---|---|---|
| Unit | Schemas, pagination, sort whitelists, run selection, taxonomy descendant resolution. | `backend/tests/unit/test_api_*.py` |
| Integration | Bands/artists/albums/credits/search/taxonomy/producers/analytics/graphs; E2 compatibility; E7 fixture run; CORS; errors; retired bands. | `backend/tests/integration/test_api_*.py` |
| Contract | OpenAPI paths/schemas, GET-only, generated TS types. | `test_openapi.py`, `npm run generate:api` |
| Performance | 500-node graph p95 target and bounded query counts. | API performance tests |
| Manual | Full-corpus analysis run and API smoke. | T-010 |
| CI | Migration, OpenAPI drift, backend and frontend checks. | GitHub Actions |

Commands:

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
TEST_DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde_test \
  uv run pytest

cd ../frontend
npm ci
npm run generate:api
npm run lint
npm run typecheck
npm run test
npm run build
```

## 12. Deployment and reversibility

- Add `CORS_ORIGINS` to `.env.example` and runtime settings.
- No migration.
- Update `openapi.json` and generated TypeScript types.
- Restart API; read-only behavior is reversible by reverting routes/middleware.
- No data cleanup or migration rollback is required.

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Breaking E2 frontend/contract | Keep old endpoints and additive fields; contract tests. |
| Mixed graph views | Separate endpoints and node-type tests. |
| Full graph response | Hard limits and truncation metadata. |
| N+1 queries | Explicit queries and query-count tests. |
| Latest run changes unexpectedly | Include run metadata; explicit run override. |
| Retired bands leak into default lists | Dataset membership filters and tests. |
| Taxonomy filter ambiguity | Shared descendant semantics and unknown-code tests. |
| CORS misconfiguration | Explicit origins; no wildcard in production. |
| OpenAPI/TS drift | CI drift check and generated types. |
| E7 snapshot unavailable | `503` with clear error; entity endpoints still work. |

## 14. Traceability requirements → plan → tasks

| Requirement | Plan section | Tasks |
|---|---|---|
| FR-001 | 4.1, 6.1 | T-001, T-003, T-010 |
| FR-002 | 4.2, 6.2 | T-001, T-005, T-006 |
| FR-003 | 4.6, 6.1 | T-003, T-008 |
| FR-004 | 4.3, 6.1 | T-005 |
| FR-005 | 4.3, 6.1 | T-004 |
| FR-006 | 4.3, 6.1 | T-004 |
| FR-007 | 4.8, 6.1 | T-007 |
| FR-008 | 4.7, 6.1 | T-007, T-008 |
| FR-009 | 4.4, 6.2 | T-005 |
| FR-010 | 4.4, 6.3 | T-005, T-009 |
| FR-011 | 4.3, 6.1 | T-005 |
| FR-012 | 4.3, 6.1 | T-006 |
| FR-013 | 4.5, 6.2 | T-002, T-010 |
| FR-014 | 8 | T-002, T-009 |
| FR-015 | 4.10 | T-009 |
| FR-016 | 2, 9 | T-009, T-010 |
| FR-017 | 4.3, 11 | T-010 |
| FR-018 | 4.6 | T-008 |
| FR-019 | 4.9 | T-001, T-009 |
| FR-020 | 6 | T-010, T-011 |

| Non-functional requirement | Plan section | Tasks |
|---|---|---|
| NFR-001 | 4.1 | T-009, T-010 |
| NFR-002 | 4.3, 11 | T-010 |
| NFR-003 | 4.3, 11 | T-005, T-010 |
| NFR-004 | 5, 9 | T-009 |
| NFR-005 | 4.2, 6.2 | T-005, T-006 |
| NFR-006 | 4.8, 9 | T-007, T-009 |
| NFR-007 | 6.2, 8 | T-002, T-009 |
| NFR-008 | 2.2 | T-009 |
| NFR-009 | 1 | T-001, T-010 |
| NFR-010 | 6, 11 | T-010, T-011 |

## 15. Approval and next step

This plan and `tasks.md` must be approved together before implementation. The first task is T-001: add CORS/run-resolution dependencies and the shared API skeleton.
