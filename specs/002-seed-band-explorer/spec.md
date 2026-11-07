# SPEC-002 — Seed band explorer

- **Status:** Implemented
- **Stage:** E2
- **Iteration:** MVP
- **Module:** `catalog`
- **Date:** 2026-11-06
- **Depends on:** SPEC-001 validated; E0 seed list; [ADR-0004](../../docs/01-architecture/adr/ADR-0004-release-group-model.md), [ADR-0005](../../docs/01-architecture/adr/ADR-0005-identity-and-provenance.md), [ADR-0007](../../docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md)
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0003](../../docs/01-architecture/adr/ADR-0003-synchronous-sqlalchemy.md), [ADR-0004](../../docs/01-architecture/adr/ADR-0004-release-group-model.md), [ADR-0005](../../docs/01-architecture/adr/ADR-0005-identity-and-provenance.md), [ADR-0006](../../docs/01-architecture/adr/ADR-0006-read-only-api.md), [ADR-0007](../../docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md)
- **Plan:** [plan.md](plan.md) (approved)
- **Tasks:** [tasks.md](tasks.md) (implemented)
- **Owner:** Cristian

## Revision history

| Revision | Date | Change |
|---|---|---|
| 1 | 2026-11-06 | Initial draft |
| 2 | 2026-11-06 | Spec approved; plan and tasks drafted |
| 3 | 2026-11-06 | Plan/tasks approved; T-001 implemented |
| 4 | 2026-11-06 | T-002 implemented (E2 fixtures) |
| 5 | 2026-11-06 | T-003 implemented (idempotent fixture loader) |
| 6 | 2026-11-06 | T-004 implemented (band list/search API) |
| 7 | 2026-11-06 | T-005 implemented (band detail API) |
| 8 | 2026-11-06 | T-006 implemented (band graph API) |
| 9 | 2026-11-06 | T-007 implemented (OpenAPI export and generated types) |
| 10 | 2026-11-06 | T-008 implemented (frontend routes and band list) |
| 11 | 2026-11-06 | T-009 implemented (band detail and credits UI) |
| 12 | 2026-11-06 | T-010 implemented (Cytoscape mini graph and fallback) |
| 13 | 2026-11-06 | T-011 implemented (expanded tests and CI) |
| 14 | 2026-11-06 | T-012 implemented (documentation and local E2 validation); remote CI pending |

## 1. Context and problem

E1 built a validated foundation: FastAPI, PostgreSQL, Alembic, a React shell, Docker Compose, tests and CI. The project still has no domain model, no seed data in the database and no domain endpoint or UI beyond the health status.

E2 must prove that the full path works with real, traceable data:

```text
versioned fixtures → PostgreSQL → FastAPI → React → Cytoscape
```

This is a walking skeleton, not the production ingestion pipeline. E3 builds the MusicBrainz ingestion pipeline. E2 uses a small, versioned subset of the existing seed list and fixtures derived from the spike cache.

The goal is to validate the data model, the credit-scope representation, the API contract, generated TypeScript types, the frontend data flow and graph rendering before investing in full ingestion.

## 2. Users and actors

- **End user:** searches for a band, opens its detail, sees albums and production credits, and explores a small band–producer graph.
- **Developer owner:** loads the fixtures, runs the API and frontend, and validates the contract.
- **Implementation agent:** works from this spec, `plan.md`, `tasks.md`, the constitution and ADRs.
- **System:** PostgreSQL, FastAPI, Vite, TanStack Query, React Router and Cytoscape provide the flow.

There is no authentication, user account or write API.

## 3. User stories and flows

### US-001 — Browse and search bands

As a user, I want to browse the seed bands and search by name so that I can find a band quickly.

**Expected flow:**

1. The user opens the band list.
2. The page shows band name, country and subgenre.
3. The user types a name; the list is filtered.
4. The user can filter by subgenre.
5. Selecting a band opens its detail page.

### US-002 — Inspect a band and its albums

As a user, I want to see a band's albums and production credits so that I can understand who worked on its records.

**Expected flow:**

1. The detail page shows the band name, country and subgenre.
2. It lists albums released between 1980 and 2000.
3. Each album shows its year and documented producers/credits.
4. Each credit shows its role and source provenance.
5. Missing credits are shown as unavailable, not as evidence of non-participation.

### US-003 — Explore a mini graph

As a user, I want to see a small band–producer graph so that I can identify shared production relationships.

**Expected flow:**

1. The detail page shows a mini graph with the band and its documented producers.
2. Edges represent documented production credits.
3. The graph has a legend and an accessible table fallback.
4. If no producer credits exist, the graph shows an empty state rather than an error.

### US-004 — Load the E2 dataset

As a developer, I want to load a versioned fixture dataset so that the application can be demonstrated and tested without network ingestion.

**Expected flow:**

1. The fixture files are present in the repository.
2. A documented command loads them into PostgreSQL.
3. Re-running the command is safe and does not duplicate data.
4. The command makes no external network calls.

## 4. Functional requirements

### FR-001 — Domain model v0

The database must support the entities needed by the walking skeleton:

- `artist`: person or group, with MBID, name, type, country and disambiguation.
- `release_group`: canonical album, with MBID, title, first release date, primary type and secondary types.
- `release`: concrete edition, with MBID, release-group reference, date and country.
- `recording`: recorded track with MBID and a relationship to its release context.
- `credit`: artist–recording/release/album relationship with role, scope, source and confidence.
- `role`: controlled vocabulary for production roles.
- `source_record`: provenance for fixture data, including source, external ID, URL, retrieval date, license and payload hash.
- `external_id`: external identifiers such as Wikidata QID.
- `subgenre` and `artist_subgenre`: curated subgenre assignment for seed bands.

Requirements:

- MBIDs are unique within their entity type.
- Credits support `release_group`, `release` and `recording` scope per ADR-0007.
- Album-level credits are derived or explicitly represented with supporting-recording metadata.
- No `Base.metadata.create_all()`; Alembic is the only schema mechanism.
- No domain table is populated by a migration.

**Verification:** migration applies to an empty database, downgrades cleanly and the schema contains the required entities.

### FR-002 — E2 fixture dataset

The repository must contain versioned fixtures for exactly 14 seed bands, two per subgenre:

| Subgenre | Bands |
|---|---|
| Heavy Metal | Iron Maiden, Judas Priest |
| Thrash Metal | Metallica, Slayer |
| Death Metal | Death, Cannibal Corpse |
| Black Metal | Bathory, Mayhem |
| Power Metal | Helloween, Blind Guardian |
| Doom Metal | Candlemass, Paradise Lost |
| Progressive Metal | Dream Theater, Fates Warning |

Each band must have:

- Two or three canonical studio albums first released between 1980 and 2000.
- At least one documented producer or co-producer credit so the mini-graph has edges.
- Albums, editions, recordings and credits needed to demonstrate the model.
- MBIDs, source URLs and retrieval dates for traceability.
- A curated primary subgenre.

Fixtures must be committed and versioned. They must not require network access to load or test.

**Verification:** the fixture manifest reports 14 bands, 2 per subgenre, 2–3 albums per band, and at least one producer/co-producer credit per band.

### FR-003 — Idempotent fixture loader

A documented backend command must load the E2 fixtures into PostgreSQL.

- Re-running it must not create duplicate entities or credits.
- It must identify records by MBID or another deterministic key.
- It must not delete unrelated data.
- It must not call external services.
- It must record the fixture version and load time.

**Verification:** running the loader twice leaves the same entity and credit counts.

### FR-004 — Band list and search API

`GET /api/v1/bands` must return a paginated list of seed bands.

Query parameters:

- `q`: case-insensitive name search.
- `subgenre`: exact subgenre filter.
- `limit`: default 20, maximum 100.
- `offset`: default 0.

Each item must include at least:

- Stable band identifier.
- Name.
- Country.
- Primary subgenre.
- MBID.

Unknown parameters are ignored or rejected consistently; invalid pagination returns `422`.

**Verification:** list, search, filter and pagination are covered by API tests.

### FR-005 — Band detail API

`GET /api/v1/bands/{band_id}` must return:

- Band identity and metadata.
- Primary subgenre.
- Albums in chronological order.
- For each album: title, year, MBID and documented production credits.
- For each credit: artist name, role, scope and source status.

Unknown band IDs return `404` with the standard error shape.

**Verification:** a known band returns albums and credits; an unknown band returns 404.

### FR-006 — Mini graph API

`GET /api/v1/bands/{band_id}/graph` must return a one-hop band–producer graph.

Response must include domain-neutral:

- `nodes`: band and producer nodes with stable IDs, labels and types.
- `edges`: documented production relationships with role and album support.
- `meta`: fixture version or generation timestamp.

Rules:

- Only documented producer/co-producer credits are included in this projection.
- A producer connected to multiple albums appears once; the edge records the album count or supporting albums.
- Unknown band IDs return `404`.
- A band with no producer credits returns the band node and an empty edge list.

**Verification:** known bands return expected nodes/edges; no-credit and unknown cases are covered.

### FR-007 — Frontend routing and data flow

The frontend must add:

- React Router.
- TanStack Query.
- Cytoscape.js.
- Generated TypeScript types from OpenAPI.

Routes:

- `/` or `/bands`: band list/search.
- `/bands/:bandId`: band detail and mini graph.

The list must support search, subgenre filter, loading, error and empty states. Filters should be represented in the URL when shareable. Components must not hard-code API hosts.

**Verification:** component tests cover list, search/filter, detail and error/empty states.

### FR-008 — Band detail and graph UI

The detail page must show:

- Band metadata and subgenre.
- Albums with years and producer/credit information.
- A mini graph with band and producer nodes.
- A legend explaining node and edge types.
- An accessible table fallback listing producers and supporting albums.

The graph must use Cytoscape and must not freeze on the E2 dataset. Tailwind, Plotly and the full graph explorer are deferred.

**Verification:** the graph renders for a seeded band; the fallback table is present and accessible.

### FR-009 — Generated API types

The frontend must use types generated from OpenAPI for API responses.

- No hand-written duplicate response interfaces for domain entities.
- The generation command must be documented.
- Generated artifacts must not be hand-edited.
- CI or the documented local flow must ensure types are current.

**Verification:** the generation command runs and the frontend typecheck passes with generated types.

### FR-010 — Tests and CI

Backend tests must cover:

- Migration from empty database.
- Fixture loading and idempotency.
- Band list/search/filter/pagination.
- Band detail and 404.
- Graph nodes/edges, no-credit graph and 404.
- No network access during tests.

Frontend tests must cover:

- Band list/search.
- Loading, error and empty states.
- Detail rendering.
- Graph fallback and legend.

CI must run the expanded backend and frontend suites.

**Verification:** local checks and the remote CI run pass.

### FR-011 — Documentation and commands

Update `README.md` and `AGENTS.md` with:

- Fixture loading command.
- New API endpoints.
- Frontend routes.
- Test commands.
- Current state and next spec.

**Verification:** commands work from a clean checkout and documentation matches the implementation.

### FR-012 — Scope guard

E2 must not include:

- Live MusicBrainz calls at runtime or in tests.
- The full ingestion/normalization pipeline.
- The full 42-band dataset.
- Graph analytics, communities or centrality.
- Tailwind, Plotly or the full graph explorer.
- Authentication, users or write operations.
- Production deployment.

**Verification:** code and OpenAPI inspection; tests run without external network access.

## 5. Non-functional requirements

### NFR-001 — Reproducibility

Fixtures are versioned, the loader is idempotent and tests do not require network access.

### NFR-002 — Performance

For the E2 dataset, band list and detail endpoints should respond within 500 ms locally. The mini graph should respond within 1 second. The graph should render without freezing the UI.

### NFR-003 — Provenance

Every fixture credit and entity must retain source URL, MBID/external ID, retrieval date and license. Fixture data is not presented as live or complete.

### NFR-004 — Accessibility

The band list, detail and graph must use semantic HTML, keyboard-accessible controls and an accessible table fallback for the graph. State changes must be announced where appropriate.

### NFR-005 — Security

The API remains read-only and public. No secrets are committed or logged. The fixture loader runs locally and does not expose credentials.

### NFR-006 — Maintainability

No generic repository abstraction is added. Services remain use-case oriented. The physical model and API contract are documented in `plan.md`.

### NFR-007 — Compatibility

The flow works with Docker Compose, Python 3.13, Node 20 and PostgreSQL 16.

### NFR-008 — Language

All project content remains in English.

## 6. Business rules

- **BR-001:** E2 uses 14 seed bands, two per subgenre; it is not the full MVP dataset.
- **BR-002:** Fixtures are derived from MusicBrainz and remain traceable; no live ingestion occurs in E2.
- **BR-003:** Credits support release-group, release and recording scope.
- **BR-004:** The absence of a credit is shown as unavailable, never as evidence of non-participation.
- **BR-005:** The API is read-only and versioned under `/api/v1`; `/health` remains operational.
- **BR-006:** Tailwind, Plotly and full graph analytics are deferred.
- **BR-007:** Generated TypeScript types are not hand-edited.
- **BR-008:** Fixture loading must not delete unrelated data.
- **BR-009:** The production ingestion pipeline belongs to E3, not E2.

## 7. Edge cases and errors

- **Empty database:** list returns an empty page; detail returns 404; UI shows an empty state.
- **Fixtures not loaded:** the UI shows an empty state and the API returns valid empty responses.
- **Unknown band:** `404` with the standard error envelope.
- **Invalid pagination:** `422`.
- **Band without producer credits:** detail shows albums with no producer data; graph returns a band node and no edges.
- **Duplicate fixture load:** upsert by deterministic key; no duplicates.
- **Special characters:** `Motörhead`, `Queensrÿche` and similar names search correctly.
- **API unavailable:** frontend shows an error state with retry.
- **Partial credits:** show only documented credits and provenance; do not infer missing roles.
- **Graph with one node:** render the node and an empty-state message.
- **Long album or artist names:** layout does not break.

## 8. Out of scope

- Full 42-band dataset.
- MusicBrainz ingestion and normalization pipeline.
- Data-quality suite, coverage report and quarantine workflow.
- Graph analytics, centrality, communities and temporal analysis.
- Tailwind, Plotly and the full graph explorer.
- Search engine, full-text ranking and faceted search beyond the basic filters.
- Authentication, users and write operations.
- Production deployment.
- Playwright end-to-end tests.

## 9. Acceptance criteria

| ID | Criterion | Evidence |
|---|---|---|
| AC-001 | The E2 migration applies from an empty database and downgrades cleanly. | Migration commands and integration test. |
| AC-002 | Fixtures contain 14 bands, 2 per subgenre, 2–3 albums each and at least one producer/co-producer per band. | Fixture manifest test. |
| AC-003 | Fixture loading is idempotent and makes no network calls. | Loader run twice; counts unchanged; test isolation. |
| AC-004 | `GET /api/v1/bands` supports list, search, subgenre filter and pagination. | API tests. |
| AC-005 | `GET /api/v1/bands/{id}` returns albums and documented credits; unknown IDs return 404. | API tests. |
| AC-006 | `GET /api/v1/bands/{id}/graph` returns band/producer nodes and edges; no-credit and 404 cases work. | API tests. |
| AC-007 | Frontend list/search/filter and detail routes work with loading, error and empty states. | Component tests and manual check. |
| AC-008 | Cytoscape mini graph renders with legend and accessible table fallback. | Component tests and manual check. |
| AC-009 | Frontend uses generated OpenAPI types; no hand-written duplicates. | Generation command and typecheck. |
| AC-010 | Backend and frontend tests pass locally and in CI. | Test output and remote CI run. |
| AC-011 | No live ingestion or external network access occurs in E2. | Test isolation and code inspection. |
| AC-012 | README and AGENTS document fixture loading, endpoints, routes and tests. | Clean-copy command validation. |
| AC-013 | No Tailwind, Plotly, analytics or write API is introduced. | Dependency and OpenAPI inspection. |

## 10. Assumptions and open questions

### Assumptions

- SPEC-001 is validated and CI is green.
- The 14 selected bands are a subset of the validated seed list.
- Fixtures can be derived from the spike raw cache and committed as a versioned artifact.
- React Router, TanStack Query, Cytoscape.js and `openapi-typescript` are added in E2.
- Tailwind and Plotly remain deferred.
- The API exposes stable band identifiers and MBIDs; the exact ID type is decided in `plan.md`.
- The graph is a one-hop band–producer projection; richer graph exploration belongs to E10.
- The fixture loader is a development/test tool, not production ingestion.

### Open questions

| Question | Blocking? | Proposed resolution |
|---|---|---|
| Internal UUID vs MBID as the API band identifier | No | Use a stable internal identifier and expose MBID alongside it; decide in plan. |
| Fixture storage path and loader command name | No | Use versioned files under `data/fixtures/e2/` and a backend module command; decide in plan. |
| Exact OpenAPI type-generation workflow | No | Generate from a committed/exported OpenAPI artifact and verify in CI; decide in plan. |
| Graph response shape | No | Return domain-neutral `nodes`, `edges` and `meta`; frontend maps to Cytoscape. |

No blocking questions for the technical plan.

## 11. Validation result

- **Date:** 2026-11-06
- **Verdict:** Implemented; local validation passed. Remote CI confirmation is pending because no push was performed.
- **Evidence:** `tasks.md` T-001–T-012 evidence, the validation table, backend/frontend test output and the local Compose smoke run.

## 12. References

- [Constitution](../../constitution.md)
- [AGENTS.md](../../AGENTS.md)
- [Scope](../../docs/00-vision/scope.md)
- [Seed list](../../docs/03-data/seed-list.md)
- [Spike report](../../docs/03-data/spike-report.md)
- [Architecture overview](../../docs/01-architecture/overview.md)
- [Data model v0](../../docs/01-architecture/data-model.md)
- [ADR-0004 — Release-group model](../../docs/01-architecture/adr/ADR-0004-release-group-model.md)
- [ADR-0005 — Identity and provenance](../../docs/01-architecture/adr/ADR-0005-identity-and-provenance.md)
- [ADR-0007 — Credit scope](../../docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md)
