# SPEC-009 — Read-only API v1

- **Status:** Implemented
- **Stage:** E8
- **Iteration:** MVP
- **Module:** `api`
- **Date:** 2026-11-10
- **Depends on:** SPEC-002 validated; SPEC-005 validated; SPEC-008 validated; [ADR-0006](../../docs/01-architecture/adr/ADR-0006-read-only-api.md); E7 analysis tables and reports
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0003](../../docs/01-architecture/adr/ADR-0003-synchronous-sqlalchemy.md), [ADR-0005](../../docs/01-architecture/adr/ADR-0005-identity-and-provenance.md), [ADR-0006](../../docs/01-architecture/adr/ADR-0006-read-only-api.md), [ADR-0007](../../docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md), [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)
- **Plan:** [plan.md](plan.md) (draft).
- **Tasks:** [tasks.md](tasks.md) (draft).
- **Conventions:** [Engineering conventions](../../docs/01-architecture/conventions.md)
- **Owner:** Cristian

## Revision history

| Revision | Date | Change |
|---|---|---|
| 1 | 2026-11-10 | Initial draft; read-only v1 entity, graph, analytics, taxonomy and run-selection contract |
| 2 | 2026-11-10 | Technical plan and tasks drafted for review |
| 3 | 2026-11-10 | T-001–T-011 implemented locally; full API checks passed; remote CI pending |

## 1. Context and problem

E7 validated a persisted producer-centric analytical corpus: `analysis_run`, graph nodes and edges for `producer_album` and `producer_band`, producer/node metrics, temporal metrics and communities. The current HTTP API is the E2 walking skeleton: it exposes only the 14-band fixture-oriented band list/detail and a one-hop band–producer graph.

E8 must expose the full normalized and analytical corpus through a stable, paginated, read-only `/api/v1` contract. It must let E9 build band, album and producer exploration and let E10 render producer–album and producer–band graphs without recomputing analytics during a request.

The API is read-only. It does not ingest, normalize, run quality checks, build graphs, write data or change E7 snapshots. Expensive work stays in batch jobs; E8 only reads persisted results.

```text
canonical E4/E5 tables                  E7 analytical tables
bands · albums · credits · taxonomy     analysis_run · graph layers
            │                                      │
            └──────────────┬───────────────────────┘
                           ▼
                    FastAPI /api/v1
         entities · search · metrics · subgraphs
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
          E9 explorer              E10 graph views
```

## 2. Goals and non-goals

### Goals

- Expose bands/artists, albums, producers, credits, taxonomy and analysis-run metadata.
- Provide deterministic search, filtering, pagination and ordering.
- Provide producer rankings (top-k) by albums and bands.
- Provide producer ego-network subgraphs for the two E7 views, with hard size limits.
- Expose precomputed producer, temporal and community metrics.
- Keep the E2 band endpoints backwards compatible while extending them.
- Generate OpenAPI and TypeScript types without manual drift.
- Meet the MVP performance targets with no obvious N+1 queries.

### Non-goals

- Writes, authentication, user accounts or public contributions.
- Recomputing E7 graphs, metrics or communities per request.
- Serving the entire graph in one response.
- Frontend pages, graph rendering or visual design.
- Ingesting external sources or serving raw source payloads.
- Changing canonical or analytical data.
- Full-text search engine infrastructure or graph databases.

## 3. Users and actors

- **Public reader:** explores bands, albums, producers, credits and metrics without authentication.
- **E9 frontend:** consumes typed entity, list and taxonomy endpoints.
- **E10 graph client:** consumes bounded producer graph subgraphs and node/edge metadata.
- **Analyst/developer:** inspects analysis-run metadata and reproducibility fields.
- **System actor:** PostgreSQL supplies canonical, quality and analytical tables.

## 4. API conventions

### 4.1 Versioning and compatibility

- Base path: `/api/v1`.
- Existing E2 endpoints remain available:
  - `GET /health`
  - `GET /api/v1/bands`
  - `GET /api/v1/bands/{band_id}`
  - `GET /api/v1/bands/{band_id}/graph`
- New parameters are optional; existing consumers must keep working.
- A breaking change requires a new API version or a new spec.
- Responses use JSON and snake_case field names, consistent with the current FastAPI schemas.

### 4.2 Pagination and ordering

List endpoints use:

```text
?limit=20&offset=0&sort=<whitelisted>&order=asc|desc
```

- `limit`: default `20`, minimum `1`, maximum `200`.
- `offset`: minimum `0`.
- `sort`: resource-specific whitelist; default deterministic order.
- `order`: `asc` or `desc`; default depends on the resource.
- Responses include `items`, `total`, `limit`, `offset`.
- Invalid pagination or sort fields return `422`.
- Ordering always includes a stable ID tie-breaker.

### 4.3 Analysis-run selection

Analytics, producers, graph and community endpoints need an E7 run:

- Default: latest `completed` or `completed_with_limitations` run by `finished_at`.
- Optional query parameter: `analysis_run=<uuid>`.
- The response `meta` includes `analysis_run_id`, `analysis_version`, `dataset_version`, `taxonomy_version`, `graph_version`, `finished_at`.
- If no completed run exists, analytics/graph/producer endpoints return `503`.
- A requested run that does not exist or is not completed returns `404` or `409`.
- Entity endpoints (`bands`, `albums`, `artists`, `credits`, `taxonomy`) continue to work from canonical data without an E7 run.

### 4.4 Errors

- `400`: invalid filter combination.
- `404`: entity, community or analysis run not found.
- `409`: requested analysis run is not usable/terminal.
- `422`: request validation, pagination or whitelist failure.
- `503`: database unavailable or no completed analysis run.
- Errors use the FastAPI `{"detail": ...}` shape unless a versioned error envelope is added by a later spec.
- Error messages must not expose SQL, secrets, raw payloads or stack traces.

## 5. Resource contract

### 5.1 Health

`GET /health` remains the operational health endpoint.

### 5.2 Bands

`GET /api/v1/bands` (existing, extended)

- Filters: `q`, `subgenre`, `decade`, `year_from`, `year_to`, `include_retired`.
- Pagination, deterministic ordering by name/ID.
- Retired bands are excluded by default.
- `subgenre` accepts a leaf or parent taxonomy code; parent filters include descendants.
- Response includes `id`, `mbid`, `name`, `country`, `subgenre`, `album_count`.

`GET /api/v1/bands/{band_id}` (existing, extended)

- Returns band metadata, albums, documented credits and taxonomy.
- `include_retired` is not needed for direct detail; a retired band remains accessible by ID.
- Albums include year/date, primary/secondary taxonomy, producer credits and support counts.
- Unknown band: `404`.

`GET /api/v1/bands/{band_id}/graph` (existing)

- Preserved for E2 compatibility as a one-hop band–producer graph.
- New graph work should use producer-centric endpoints below.
- Unknown band: `404`.

### 5.3 Artists and producers

`GET /api/v1/artists/{artist_id}`

- Canonical artist detail for any artist type.
- Includes canonical name, MBID, type, country, aliases/credited-as summary if available, and links/resource IDs for band/producer views.
- Unknown artist: `404`.

`GET /api/v1/producers`

- Lists artists with `producer`/`co-producer` credits in the selected E7 run.
- Filters: `q`, `decade`, `subgenre`, `analysis_run`.
- Sort: `album_count` (default), `band_count`, `betweenness`, `name`.
- Includes `producer_id`, `name`, `album_count`, `band_count`, `self_produced_albums`, `betweenness`, `community_key`.
- Top-k is a pagination/sort concern; no unbounded full-graph response.

`GET /api/v1/producers/{producer_id}`

- Producer metadata and selected-run metrics.
- Includes top albums and bands/artists, self-produced album count, community, support summary and analysis metadata.
- Unknown producer: `404`.

### 5.4 Albums

`GET /api/v1/albums`

- Filters: `q`, `band_id`, `producer_id`, `decade`, `year_from`, `year_to`, `subgenre`, `include_unclassified`.
- Pagination and deterministic ordering by release date/title/ID.
- Response includes album ID/MBID/title, band/artist summary, year, taxonomy, producer count and credit count.

`GET /api/v1/albums/{album_id}`

- Album detail with band/artist, release date, taxonomy, recorded credits and support counts.
- Credits include artist, role, scope, supporting recordings, album recordings, support ratio, confidence and status.
- Unknown album: `404`.

### 5.5 Credits

`GET /api/v1/credits`

- Filters: `album_id`, `band_id`, `artist_id`, `role`, `scope`, `analysis_run`.
- Pagination and deterministic ordering.
- Credit rows identify artist, album, role, scope, support counts/ratio, confidence and source status.
- No raw source payloads or unrestricted evidence dumps.

### 5.6 Search and taxonomy

`GET /api/v1/search?q=...`

- Searches bands/artists, albums and producers with a bounded result limit.
- Returns grouped result sections with stable IDs, labels and resource type.
- No SQL injection, no unbounded wildcard scans and no external search service.

`GET /api/v1/taxonomy`

- Returns the selected taxonomy version, nodes, parent relationships and `assignable` flags.
- Parent filtering semantics are documented and shared with `/bands` and `/albums`.
- Version mismatch with the selected analysis run is rejected.

### 5.7 Analysis runs and analytics

`GET /api/v1/analysis-runs`

- Lists E7 runs with version, status, dataset/taxonomy/graph versions, timestamps and report path.
- Read-only metadata; no report file streaming in v1.

`GET /api/v1/analysis-runs/{analysis_run_id}`

- Returns one run or `404`.

`GET /api/v1/analytics/summary`

- Returns graph counts, support summary, concentration metrics, top producers, community count and selected-run metadata.

`GET /api/v1/analytics/decades`

- Returns temporal metrics by decade for both layers.

`GET /api/v1/communities`

- Lists communities for the selected run, ordered deterministically.
- Filters: `analysis_run`, `limit`, `offset`.

`GET /api/v1/communities/{community_key}`

- Returns community metadata and producer members.
- Unknown community: `404`.

## 6. Producer graph contract

### 6.1 Separate views

`GET /api/v1/producers/{producer_id}/graph?view=albums|bands`

- `view=albums` returns producer + album nodes and `producer_album` edges.
- `view=bands` returns producer + band/artist nodes and `producer_band` edges.
- Album and band nodes are never mixed in one response.
- The selected producer is included even if it has no edges, with a clear empty-edge result.
- `view=albums`/`view=bands` are the only product views; no album–album or artist–artist endpoint.

### 6.2 Subgraph limits

Query parameters:

- `view`: required or defaults to `bands`; documented default.
- `limit`: top-k/ego selection, default `20`, maximum `100`.
- `depth`: `1` by default, maximum `2`.
- `max_nodes`: default `500`, maximum `500`.
- `max_edges`: default `2000`, maximum `2000`.
- `include_evidence`: optional; when true, include bounded album evidence summaries.

Responses must include:

- `nodes`: ID, entity ID, node type, label, roles, year/decade, artist type, taxonomy and self-produced flags.
- `edges`: source, target, layer, role/role mix, weight, support ratio/counts, album count and evidence summary.
- `meta`: view, analysis run/version, dataset/taxonomy/graph versions, limits and `truncated`.

If limits would be exceeded, return a deterministic subset and `meta.truncated=true`; never silently return an unbounded graph.

### 6.3 Top-k overview

The producer list/analytics endpoints provide top-k by album count, band count or betweenness. E10 opens a top-k producer–band overview and expands a selected producer into an ego network. The API does not render the full 731-album graph.

## 7. Functional requirements

### FR-001 — API version and compatibility

E8 must serve all new resources under `/api/v1` and preserve the existing E2 endpoints and their required response fields.

**Verification:** contract tests for old and new endpoints.

### FR-002 — Analysis-run selection

All analytics/graph/producer endpoints must resolve an explicit or latest completed E7 run, include run metadata and handle missing/non-terminal runs with documented errors.

**Verification:** run-selection and error tests.

### FR-003 — Band and artist reads

The API must expose band list/detail and generic artist detail, including taxonomy, albums and documented credits, with retired-band behavior.

**Verification:** entity tests for active, retired and unknown records.

### FR-004 — Producer reads and rankings

The API must expose producer list/detail with album count, band count, self-produced count, betweenness, community and top albums/bands, sorted deterministically and paginated.

**Verification:** producer ranking/detail tests.

### FR-005 — Album reads

The API must expose album list/detail with band/artist, date, taxonomy, producer references, credit support and pagination.

**Verification:** album list/detail/filter tests.

### FR-006 — Credit reads

The API must expose paginated credits filtered by album, band, artist, role, scope and run, with support fields but no raw payloads.

**Verification:** credit filter and support tests.

### FR-007 — Search

The API must provide bounded search across bands/artists, albums and producers, returning grouped, stable results.

**Verification:** search relevance/shape/limit tests.

### FR-008 — Taxonomy

The API must expose versioned taxonomy nodes and apply the same parent/leaf filter semantics to bands and albums.

**Verification:** taxonomy hierarchy and filter tests.

### FR-009 — Producer graph views

The API must return separate `albums` and `bands` producer graphs with correct node types, edge layers, roles, weights and evidence.

**Verification:** graph view contract tests.

### FR-010 — Subgraph limits

The API must enforce limit/depth/max_nodes/max_edges, return deterministic truncation metadata and never return the full graph.

**Verification:** boundary/truncation tests.

### FR-011 — Top-k rankings

The API must expose top-k producer rankings by album count, band count and betweenness with documented defaults and maxima.

**Verification:** ranking tests.

### FR-012 — Analytics and communities

The API must expose analysis-run metadata, graph/support summary, decade metrics and community membership from E7.

**Verification:** analytics/community tests.

### FR-013 — Pagination and filters

All list endpoints must support whitelisted pagination/filter/sort parameters, stable ordering and total counts.

**Verification:** pagination/filter/sort tests.

### FR-014 — Errors

The API must return documented `400`, `404`, `409`, `422` and `503` responses without internal details.

**Verification:** error contract tests.

### FR-015 — OpenAPI and TypeScript

The OpenAPI document must describe all resources, parameters, limits and errors; the generated TypeScript types must match it.

**Verification:** OpenAPI drift and frontend type generation tests.

### FR-016 — Read-only behavior

The API must have no write routes, no ingestion calls, no graph recomputation and no mutation of canonical/analytical data.

**Verification:** scope guard, route inspection and read-only tests.

### FR-017 — Performance

The API must meet the MVP response targets and avoid N+1 queries for list/detail/graph responses.

**Verification:** representative timings and query-count tests.

### FR-018 — Retired bands

Retired bands must be excluded from default list/search, remain accessible by direct detail URL and remain in historical analysis/API responses when specifically selected.

**Verification:** retired-band tests.

### FR-019 — CORS and public access

The API must allow the configured frontend origin in development and production without exposing write capabilities or secrets.

**Verification:** CORS tests and deployment configuration review.

### FR-020 — Documentation

The API must document endpoint semantics, limits, run selection, graph views, taxonomy filtering and retired-band behavior.

**Verification:** docs review and link checks.

## 8. Non-functional requirements

### NFR-001 — Contract stability

The v1 contract must be additive and deterministic; breaking changes require a new version/spec.

### NFR-002 — Performance

500-node subgraphs should meet p95 ≤ 1 second server-side; list/detail endpoints should meet the existing E2/API targets for the MVP volume.

### NFR-003 — No N+1

Graph and list services must use bounded, explicit queries; repeated per-row queries are not acceptable.

### NFR-004 — Data safety

E8 is read-only. It must never mutate canonical, normalization, quality or analysis rows.

### NFR-005 — Reproducibility metadata

Graph/analytics responses must identify the E7 run and dataset/taxonomy/graph versions.

### NFR-006 — Security

No secrets, raw payloads or stack traces in responses. Query parameters and sort/filter fields are whitelisted.

### NFR-007 — Accessibility of contract

Error and truncation metadata must be explicit enough for accessible UI fallbacks and table alternatives.

### NFR-008 — Maintainability

API services live under `hmde.api`/`hmde.services`; no ETL, normalization or graph-construction imports.

### NFR-009 — Compatibility

Python 3.13, FastAPI, Pydantic v2, synchronous SQLAlchemy, PostgreSQL 16 and the existing Compose setup remain supported.

### NFR-010 — Language

All API documentation, field names and error messages are in English.

## 9. Business rules

- **BR-001:** The API is public and read-only; no writes or authentication in v1.
- **BR-002:** Canonical identity is `artist_id`/MBID; names never merge identities.
- **BR-003:** Analytics/graph responses use a single selected E7 run.
- **BR-004:** Latest completed run is the default; explicit run selection is supported.
- **BR-005:** The full graph is never returned in one response.
- **BR-006:** Producer graphs expose separate album and band views; node types are never mixed.
- **BR-007:** Producer–band edges are derived evidence; album evidence remains available.
- **BR-008:** Missing credits are not negative evidence.
- **BR-009:** Taxonomy parent filters include descendants; leaf assignment rules remain E4 rules.
- **BR-010:** Retired bands are excluded from default lists but accessible by direct ID.
- **BR-011:** No expensive E7 computation occurs inside an HTTP request.
- **BR-012:** Pagination, sort and filter inputs are whitelisted and bounded.
- **BR-013:** OpenAPI is generated from the code and is the HTTP contract source of truth.
- **BR-014:** E7 reports and raw source payloads are not streamed by the API in v1.

## 10. Edge cases and errors

- No completed E7 run: analytics/graph/producer endpoints return `503`; entity endpoints still work.
- Requested analysis run missing: `404`.
- Requested analysis run failed/running: `409`.
- Producer with no edges: return the seed node and empty edges, not an error.
- Producer with only self-produced albums: no producer–band edge; self-produced count and node roles reflect it.
- Album without date: serialized as null; excluded from decade filters.
- Album without taxonomy: visible in general albums; excluded from taxonomy filters; `include_unclassified` controls inclusion.
- Retired band in default list: excluded; direct detail: `200`.
- Unknown taxonomy/subgenre code: `422` or documented empty result; decide consistently.
- `limit` over maximum: `422`.
- `max_nodes`/`max_edges` overflow: deterministic truncation with `meta.truncated=true`.
- Duplicate labels with different MBIDs: returned as distinct entities; no name merge.
- Database unavailable: `503` with no internal details.
- No full graph request: bounded response or documented rejection.

## 11. Out of scope

- Writes, authentication, accounts or moderation.
- Frontend routes, components or graph rendering.
- Recomputing E7 runs, metrics or communities.
- Streaming raw E7 report files or raw source payloads.
- New dataset ingestion or taxonomy changes.
- Graph database, Elasticsearch or external search services.
- Complete discography beyond the active corpus.
- Mobile application or internationalization.

## 12. Acceptance criteria

| ID | Criterion | Evidence |
|---|---|---|
| AC-001 | Existing `/health` and E2 band endpoints remain compatible. | Contract tests |
| AC-002 | Latest completed analysis run is selected by default; explicit run selection works. | Run-selection tests |
| AC-003 | Missing/non-terminal runs return documented errors. | Error tests |
| AC-004 | Band/artist list/detail include taxonomy, albums and credits. | Entity tests |
| AC-005 | Producer list/detail expose rankings, metrics, community and self-produced counts. | Producer tests |
| AC-006 | Album list/detail expose band, date, taxonomy and support-aware credits. | Album tests |
| AC-007 | Credit filters and pagination work for album/band/artist/role/scope. | Credit tests |
| AC-008 | Search returns bounded grouped results across entities. | Search tests |
| AC-009 | Taxonomy endpoint and parent/leaf filters share semantics. | Taxonomy tests |
| AC-010 | Producer–album and producer–band graph responses have correct node types and layers. | Graph tests |
| AC-011 | Graph limits and truncation metadata are enforced. | Limits tests |
| AC-012 | Top-k rankings by albums, bands and betweenness work. | Ranking tests |
| AC-013 | Analytics summary, decades and communities use E7 data. | Analytics tests |
| AC-014 | Pagination, sorting and whitelisted filters are deterministic. | Pagination tests |
| AC-015 | Error statuses and messages match the contract. | Error tests |
| AC-016 | OpenAPI and TypeScript types are generated without drift. | OpenAPI/type tests |
| AC-017 | API is read-only and never recomputes E7 results. | Scope/route tests |
| AC-018 | Retired bands are hidden by default and accessible by direct ID. | Retired-band tests |
| AC-019 | 500-node subgraph meets the p95 target and list endpoints avoid N+1. | Performance tests |
| AC-020 | CORS allows the configured frontend origin without write exposure. | CORS tests |
| AC-021 | API documentation covers endpoints, limits, runs, taxonomy and retired bands. | Docs review |
| AC-022 | Full backend tests, Ruff, format, OpenAPI drift and remote CI pass. | Local/CI evidence |

## 13. Assumptions and resolved decisions

### Assumptions

- SPEC-008 remains validated and its analytical tables are available.
- The active corpus is 57 bands; the contract must scale to 200–500.
- E8 uses the existing modular monolith and synchronous SQLAlchemy.
- E9/E10 need a stable, typed contract before UI implementation.
- No new schema is expected; measured additive indexes may be proposed separately.

### Resolved decisions

| Decision | Resolution |
|---|---|
| API version | `/api/v1`; existing E2 endpoints remain compatible. |
| Default run | Latest `completed`/`completed_with_limitations` by `finished_at`; explicit `analysis_run` override. |
| Graph views | Separate `albums` and `bands` endpoints; no mixed canvas and no album–album projection. |
| Top-k/ego | Producer rankings and bounded ego networks; no full graph response. |
| Limits | `limit` max 100 for graph selection; `max_nodes` 500; `max_edges` 2000; depth max 2. |
| Retired bands | Hidden by default; direct detail remains accessible. |
| Writes | None in E8. |
| Frontend | Deferred to E9/E10. |
| Schema | No schema changes planned; additive indexes require measured justification and approval. |
| Search | Bounded SQL-backed search; no external search service. |

### Open questions

No blocking question remains for planning. Exact response field names and service decomposition are plan-level details; they must preserve the contract and limits above.

## 14. Validation result

- **Date:** 2026-11-10
- **Verdict:** Implemented; local validation passed; remote CI pending
- **Evidence:** 313 backend tests passed; frontend lint/typecheck/21 tests/build passed; OpenAPI regenerated and drift-free; full-corpus API smoke passed with 384 producers and a 25.8 ms bounded graph response. Remote CI is pending because no commit or push was performed. See `tasks.md`.

## 15. References

- [Constitution](../../constitution.md)
- [AGENTS.md](../../AGENTS.md)
- [Vision](../../docs/00-vision/vision.md)
- [Scope](../../docs/00-vision/scope.md)
- [Roadmap](../../docs/00-vision/roadmap.md)
- [Data model v0](../../docs/01-architecture/data-model.md)
- [Producer network analysis](../../docs/03-data/network-analysis.md)
- [ADR-0003 — Synchronous SQLAlchemy](../../docs/01-architecture/adr/ADR-0003-synchronous-sqlalchemy.md)
- [ADR-0006 — Read-only API](../../docs/01-architecture/adr/ADR-0006-read-only-api.md)
- [ADR-0007 — Credit scope](../../docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md)
- [ADR-0008 — Taxonomy and corpus versioning](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)
- [SPEC-002 — Seed band explorer](../002-seed-band-explorer/spec.md)
- [SPEC-008 — Network analysis](../008-network-analysis/spec.md)
