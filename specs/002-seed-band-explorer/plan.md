# Technical plan — SPEC-002 Seed band explorer

- **Status:** Approved
- **Spec:** [spec.md](spec.md)
- **Tasks:** [tasks.md](tasks.md)
- **Stage:** E2
- **Module:** `catalog`
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0003](../../docs/01-architecture/adr/ADR-0003-synchronous-sqlalchemy.md), [ADR-0004](../../docs/01-architecture/adr/ADR-0004-release-group-model.md), [ADR-0005](../../docs/01-architecture/adr/ADR-0005-identity-and-provenance.md), [ADR-0006](../../docs/01-architecture/adr/ADR-0006-read-only-api.md), [ADR-0007](../../docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md)

## 1. Solution summary

E2 completes a vertical walking skeleton:

```text
versioned fixtures → PostgreSQL → FastAPI → React → Cytoscape
```

The dataset is a committed, versioned subset of 14 seed bands (2 per subgenre), derived from the existing MusicBrainz spike cache. A backend loader upserts the fixtures into PostgreSQL. A read-only API exposes band list/search, band detail and a one-hop band–producer graph. The React frontend uses React Router, TanStack Query and Cytoscape to browse the data.

E2 does not run live ingestion. E3 builds the production MusicBrainz ingestion pipeline and replaces fixtures with ingested data.

## 2. Architecture and data flow

```text
data/fixtures/e2/*.json
        │
        ▼
Fixture loader (backend CLI)
        │  upsert by deterministic UUID / MBID
        ▼
PostgreSQL
        │
        ▼
FastAPI /api/v1/bands
        │  list, detail, graph
        ▼
React + TanStack Query + React Router
        │
        ├── band list/search
        ├── band detail and credits
        └── Cytoscape mini graph
```

Type flow:

```text
FastAPI OpenAPI → openapi.json → openapi-typescript → frontend types
```

## 3. Components and responsibilities

### Backend

| Path | Responsibility |
|---|---|
| `backend/src/hmde/models/__init__.py` | Export model classes. |
| `backend/src/hmde/models/artist.py` | Artist and external ID models. |
| `backend/src/hmde/models/catalog.py` | Release-group, release, recording and track models. |
| `backend/src/hmde/models/credit.py` | Credit, role and provenance models. |
| `backend/src/hmde/models/subgenre.py` | Subgenre and artist-subgenre models. |
| `backend/src/hmde/models/fixture.py` | Fixture-load metadata. |
| `backend/src/hmde/schemas/band.py` | Band list/detail Pydantic schemas. |
| `backend/src/hmde/schemas/graph.py` | Graph node/edge schemas. |
| `backend/src/hmde/services/catalog.py` | Band list, detail and credit aggregation. |
| `backend/src/hmde/services/graph.py` | Band–producer projection. |
| `backend/src/hmde/api/routes/bands.py` | `/api/v1/bands` endpoints. |
| `backend/src/hmde/api/routes/graph.py` or bands route | Graph endpoint. |
| `backend/src/hmde/seed/loader.py` | Idempotent fixture loader CLI. |
| `backend/src/hmde/openapi.py` | Export `openapi.json` without a running server. |
| `backend/alembic/versions/0002_catalog_v0.py` | E2 schema migration. |
| `backend/tests/integration/test_catalog_api.py` | List/detail/graph API integration tests. |
| `backend/tests/integration/test_fixture_loader.py` | Fixture counts and idempotency. |
| `backend/tests/integration/conftest.py` | Test database migration, cleanup and fixture loading. |

### Fixture generation

| Path | Responsibility |
|---|---|
| `scripts/build_e2_fixtures.py` | One-off builder that reads the spike cache and writes versioned E2 fixtures. |
| `data/fixtures/e2/manifest.json` | Fixture version, source snapshot, counts and checksums. |
| `data/fixtures/e2/artists.json` | 14 bands and subgenre assignments. |
| `data/fixtures/e2/release_groups.json` | Canonical albums. |
| `data/fixtures/e2/releases.json` | Editions used for provenance and credits. |
| `data/fixtures/e2/recordings.json` | Recordings used by recording-scoped credits. |
| `data/fixtures/e2/credits.json` | Credits with role, scope, confidence and source. |
| `data/fixtures/e2/source_records.json` | Source URLs, MBIDs, retrieval dates and licenses. |

The builder is a development tool. It is not imported by the API or the loader. The generated fixture files are committed and are the only data input for E2.

### Frontend

| Path | Responsibility |
|---|---|
| `frontend/src/main.tsx` | QueryClientProvider and BrowserRouter. |
| `frontend/src/App.tsx` | Routes for band list and band detail. |
| `frontend/src/pages/BandsPage.tsx` | Search, subgenre filter and band list. |
| `frontend/src/pages/BandDetailPage.tsx` | Band metadata, albums, credits and mini graph. |
| `frontend/src/components/BandList.tsx` | Accessible band table/list. |
| `frontend/src/components/CreditList.tsx` | Album credits with role, scope and source status. |
| `frontend/src/components/BandGraph.tsx` | Cytoscape mini graph and table fallback. |
| `frontend/src/components/AsyncState.tsx` | Loading, error and empty states. |
| `frontend/src/api/client.ts` | Existing fetch wrapper, extended for API errors. |
| `frontend/src/api/bands.ts` | Typed API functions for list/detail/graph. |
| `frontend/src/api/schema.d.ts` | Generated OpenAPI types; not hand-edited. |
| `frontend/src/index.css` | Minimal CSS for list, detail and graph. |
| `frontend/src/**/*.test.tsx` | Component tests with mocked fetch. |

### Infrastructure and documentation

| Path | Responsibility |
|---|---|
| `openapi.json` | Reviewed OpenAPI contract snapshot generated by the backend. |
| `frontend/package.json` | Adds Router, Query, Cytoscape and type generation scripts. |
| `.github/workflows/ci.yml` | Adds migration/OpenAPI checks and expanded tests. |
| `README.md` | Fixture loading, API endpoints, routes and tests. |
| `AGENTS.md` | Current state and verified commands. |

## 4. Technical decisions and alternatives

### 4.1 IDs and identity

- Every canonical entity uses an internal UUID primary key.
- MBIDs are unique external identifiers, not primary keys.
- Fixture IDs are deterministic UUIDv5 values derived from MBIDs or stable credit keys. This makes loader upserts idempotent without relying on name matching.
- The API exposes internal UUIDs and MBIDs.
- No fuzzy identity resolution in E2.

### 4.2 Schema

- SQLAlchemy 2.0 declarative models; Alembic migration `0002_catalog_v0`.
- PostgreSQL UUID, Date, JSONB, String and Float/Numeric columns.
- Check constraints for artist type, credit scope and credit status.
- Indexes on MBIDs, foreign keys, artist name and credit target fields.
- No `Base.metadata.create_all()`.

### 4.3 Credit scopes

Per ADR-0007:

- `credit.scope` is `release_group`, `release` or `recording`.
- `release_group_id` is always present for album aggregation.
- `release_id` is present for release-scoped credits.
- `recording_id` is present for recording-scoped credits.
- Check constraints reject combinations that contradict the scope.
- The API aggregates recording-scoped credits to an album with `supporting_recording_count` and `recording_count`.
- A release-scoped credit is treated as full-album support.
- No absence is converted into a negative credit.

### 4.4 Fixtures

- 14 bands, 2 per subgenre.
- 2–3 albums per band; at least one documented producer/co-producer credit per band.
- Fixtures are built from the spike cache; no live network calls during loading or tests.
- The builder chooses albums with documented producer credits where possible and records the selection rule in the manifest.
- Every fixture entity and credit carries source provenance.
- Fixture version: `e2-v0.1.0`.

### 4.5 Loader

- CLI: `uv run python -m hmde.seed.loader --fixtures ../data/fixtures/e2`.
- Uses deterministic UUIDs and `session.merge` or PostgreSQL upsert.
- Re-running is safe and leaves counts unchanged.
- Does not delete unrelated records.
- Writes a `fixture_load` row with version, timestamp and counts.
- Refuses to run if the fixture manifest version is invalid.

### 4.6 API

- Prefix `/api/v1`.
- `GET /api/v1/bands` with `q`, `subgenre`, `limit`, `offset`.
- `GET /api/v1/bands/{band_id}` with albums and aggregated credits.
- `GET /api/v1/bands/{band_id}/graph` with one-hop band–producer nodes/edges.
- UUID path parameters; invalid UUIDs return `422`.
- Unknown bands return `404` with FastAPI's standard `{"detail": ...}` error.
- Pagination response: `items`, `total`, `limit`, `offset`.
- Search is case-insensitive via `ILIKE`; diacritics are preserved.
- No N+1 queries; use selectinload or explicit joins.

### 4.7 OpenAPI and generated types

- Backend command `uv run python -m hmde.openapi --output ../openapi.json` writes the contract without a running server.
- `openapi.json` is committed as a reviewed contract snapshot so the frontend can build without a running backend.
- `frontend` script `generate:api` runs `openapi-typescript ../openapi.json -o src/api/schema.d.ts`.
- `pretypecheck`, `predev` and `prebuild` generate the types automatically.
- `src/api/schema.d.ts` is generated and ignored by Git; it is never hand-edited.
- The backend CI job verifies that regenerating `openapi.json` produces no diff.

This is a deliberate exception to the general rule that generated artifacts are not committed: the OpenAPI snapshot is a reviewable contract artifact, while generated TypeScript remains untracked.

### 4.8 Frontend

- React Router for `/bands` and `/bands/:bandId`.
- TanStack Query for server state.
- Cytoscape for the mini graph.
- Plain CSS; Tailwind is deferred to E9.
- URL search params for search and subgenre filters.
- Accessible table fallback for the graph.
- No global state library.
- No Plotly.

### 4.9 Alternatives considered

| Alternative | Reason for rejection |
|---|---|
| Use MBID as the database primary key | Couples canonical identity to one source and complicates future merges. |
| Load the full 42-band dataset in E2 | Expands fixture work and delays the walking skeleton. |
| Use live MusicBrainz calls during fixtures/tests | Violates reproducibility and makes tests network-dependent. |
| Commit generated TypeScript types | Generated code should remain untracked; a reviewed OpenAPI snapshot is sufficient. |
| Introduce Tailwind in E2 | Not needed for the walking skeleton; product styling belongs to E9. |
| Use a separate graph database | PostgreSQL + Cytoscape are sufficient for one-hop graphs. |
| Build the full ingestion pipeline now | E3 owns ingestion and normalization. |

## 5. Data model and migrations

### 5.1 Tables

| Table | Key columns |
|---|---|
| `source_record` | `id`, `source`, `source_entity_type`, `external_id`, `source_url`, `fetched_at`, `license`, `payload_hash`, `fixture_version` |
| `external_id` | `id`, `entity_type`, `entity_id`, `source`, `external_id`, `url` |
| `artist` | `id`, `mbid` unique, `name`, `sort_name`, `type`, `country`, `disambiguation`, `source_record_id` |
| `subgenre` | `code` PK, `name` |
| `artist_subgenre` | `artist_id`, `subgenre_code`, `is_primary`, `confidence`, `source_record_id` |
| `release_group` | `id`, `mbid` unique, `artist_id`, `title`, `first_release_date`, `first_release_precision`, `primary_type`, `secondary_types`, `disambiguation`, `source_record_id` |
| `release` | `id`, `mbid` unique, `release_group_id`, `title`, `release_date`, `release_date_precision`, `country`, `status`, `source_record_id` |
| `recording` | `id`, `mbid` unique, `title`, `source_record_id` |
| `recording_release` | `release_id`, `recording_id`, `disc`, `position` |
| `role` | `code` PK, `name`, `category` |
| `credit` | `id`, `artist_id`, `role_code`, `scope`, `release_group_id`, `release_id`, `recording_id`, `source_record_id`, `confidence`, `status`, `credited_as`, `attributes` |
| `fixture_load` | `id`, `version`, `source`, `loaded_at`, `band_count`, `album_count`, `credit_count` |

### 5.2 Constraints

- `artist.type` in `person`, `group`, `other`.
- `credit.scope` in `release_group`, `release`, `recording`.
- Scope consistency:
  - `release_group`: `release_id` and `recording_id` are null.
  - `release`: `release_id` is not null and `recording_id` is null.
  - `recording`: `recording_id` is not null.
- `credit.status` in `confirmed`, `inferred`, `conflicting`, `quarantined`.
- `confidence` between 0 and 1.
- Unique `(release_id, recording_id)` on `recording_release`.
- Unique `(artist_id, subgenre_code)` on `artist_subgenre`.
- Unique MBIDs per entity type.

### 5.3 Indexes

- Lower-case artist name for search.
- `release_group.artist_id`, `release_group.first_release_date`.
- `release.release_group_id`.
- `credit.release_group_id`, `credit.artist_id`, `credit.recording_id`, `credit.role_code`.
- `recording_release.release_id`, `recording_release.recording_id`.

### 5.4 Migration

`0002_catalog_v0` creates the tables, constraints and indexes. It contains no seed data. `downgrade()` drops the E2 tables in dependency order. It must apply and revert on an empty database.

`0003_credit_target_restrict` changes the `credit.release_id` and `credit.recording_id` foreign keys from `SET NULL` to `RESTRICT`, matching the scope check constraints. See the [ER diagram](../../docs/01-architecture/er-diagram.md).

## 6. Fixtures and loader

### 6.1 Builder

`scripts/build_e2_fixtures.py`:

1. Loads the 14 selected band entries from the seed list.
2. Reads the spike raw cache and indexes responses by URL.
3. Selects 2–3 studio albums per band, preferring albums with documented producer/co-producer credits.
4. Extracts release-group, release, recording, role and credit data.
5. Maps MusicBrainz producer attributes (`co`, `executive`, `assistant`, `additional`) to role codes.
6. Generates deterministic UUIDv5 IDs.
7. Writes versioned JSON files and a manifest with counts and checksums.
8. Does not modify the database.

The builder is run manually when fixtures need regeneration. The resulting files are committed.

### 6.2 Fixture manifest

The manifest records:

- Fixture version.
- Source snapshot date.
- Band count and subgenre distribution.
- Album count and per-band album count.
- Credit count by scope and role.
- Source URL count.
- Checksums of fixture files.
- Selection notes for bands with limited producer coverage.

### 6.3 Loader

`hmde.seed.loader`:

- Reads the manifest and fixture files.
- Validates version and entity references.
- Upserts source records, artists, subgenres, albums, releases, recordings, tracks, roles and credits.
- Uses deterministic IDs and natural keys.
- Writes `fixture_load` counts.
- Fails on missing references or duplicate MBIDs.
- Makes no network requests.

## 7. API contract

### 7.1 Band list

`GET /api/v1/bands?q=&subgenre=&limit=20&offset=0`

Response:

```json
{
  "items": [
    {
      "id": "uuid",
      "mbid": "uuid",
      "name": "Iron Maiden",
      "country": "GB",
      "subgenre": "Heavy Metal",
      "album_count": 3
    }
  ],
  "total": 14,
  "limit": 20,
  "offset": 0
}
```

### 7.2 Band detail

`GET /api/v1/bands/{band_id}`

Response:

```json
{
  "id": "uuid",
  "mbid": "uuid",
  "name": "Iron Maiden",
  "country": "GB",
  "subgenre": "Heavy Metal",
  "albums": [
    {
      "id": "uuid",
      "mbid": "uuid",
      "title": "Iron Maiden",
      "year": 1980,
      "first_release_date": "1980-04-14",
      "credits": [
        {
          "artist_id": "uuid",
          "artist_name": "Martin Birch",
          "role": "producer",
          "role_name": "Producer",
          "scope": "recording",
          "supporting_recording_count": 9,
          "recording_count": 9,
          "confidence": 1.0,
          "status": "confirmed"
        }
      ]
    }
  ]
}
```

### 7.3 Mini graph

`GET /api/v1/bands/{band_id}/graph`

Response:

```json
{
  "nodes": [
    {"id": "band-uuid", "label": "Iron Maiden", "type": "band"},
    {"id": "artist-uuid", "label": "Martin Birch", "type": "producer"}
  ],
  "edges": [
    {
      "source": "band-uuid",
      "target": "artist-uuid",
      "type": "produced",
      "role": "producer",
      "album_count": 2,
      "albums": ["Iron Maiden", "Killers"]
    }
  ],
  "meta": {"fixture_version": "e2-v0.1.0"}
}
```

Rules:

- Only producer/co-producer credits appear.
- One node per producer.
- One edge per band–producer pair with album support.
- No producer credits: band node only.
- Unknown band: `404`.

## 8. Frontend impact

### 8.1 Providers and routes

- `QueryClientProvider` and `BrowserRouter` in `main.tsx`.
- `/` redirects to `/bands`.
- `/bands` list/search.
- `/bands/:bandId` detail.

### 8.2 Band list

- Search input and subgenre select.
- URL search params for `q` and `subgenre`.
- Loading, error, empty and result states.
- Table or semantic list with links.

### 8.3 Band detail

- Band metadata.
- Albums in chronological order.
- Credit list per album with role, scope and source status.
- Mini graph and legend.
- Table fallback with producers and supporting albums.
- Loading, error and not-found states.

### 8.4 Graph

- Cytoscape instance created when data is available.
- Nodes styled by type; edges labeled by role.
- Container destroyed on unmount.
- Limit: E2 graph is one-hop and small; no WebGL or clustering.
- Accessible table always rendered or available via disclosure.

### 8.5 Styling

- Minimal CSS, responsive layout, visible focus and sufficient contrast.
- Tailwind deferred to E9.

## 9. Error handling and consistency

- **Unknown band:** `404`.
- **Invalid UUID:** `422`.
- **Invalid pagination:** `422`.
- **Empty database:** empty list, detail 404, UI empty state.
- **No producer credits:** band node and empty edge list; UI empty graph state.
- **Fixture load failure:** transaction rollback; no partial dataset.
- **Duplicate fixture load:** upsert, no duplicates.
- **Missing fixture references:** loader fails before writing.
- **Frontend API failure:** error state with retry.
- **Query cancellation:** TanStack Query handles unmount; Cytoscape is destroyed.
- **No network:** tests use fixtures only.

## 10. Security and trust boundaries

- Read-only public API; no auth.
- No secrets in fixtures or logs.
- Loader runs locally with `DATABASE_URL`.
- No user input interpolated into raw SQL; SQLAlchemy parameterized queries.
- Pagination limits prevent unbounded responses.
- Graph depth fixed to one hop.
- Fixture provenance is visible in the UI where practical.

## 11. Observability

- Loader logs version, counts and upserts without credentials.
- API logs unhandled errors; no secrets.
- Fixture version is returned in graph metadata.
- README documents fixture version and snapshot date.
- No metrics or tracing in E2.

## 12. Testing strategy

| Level | Coverage |
|---|---|
| Unit | Role mapping, credit aggregation, response serialization, fixture validation. |
| Integration | Migration, loader idempotency, list/search/detail/graph with PostgreSQL. |
| Contract | OpenAPI paths and schemas; generated type check. |
| Frontend | List/search, detail, loading/error/empty, graph fallback, URL filters. |
| CI | Migrations, backend tests, OpenAPI drift, frontend checks. |
| Manual | Full Compose flow with fixtures loaded and browser exploration. |

Commands:

```bash
cd backend
uv run alembic upgrade head
uv run python -m hmde.seed.loader --fixtures ../data/fixtures/e2
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run python -m hmde.openapi --output ../openapi.json

cd ../frontend
npm ci
npm run generate:api
npm run lint
npm run typecheck
npm run test
npm run build
```

## 13. Deployment and reversibility

- E2 remains a development Compose flow.
- Fixtures are loaded explicitly; they are not part of migrations.
- `alembic downgrade base` removes the E2 schema.
- Re-running the loader is safe.
- No production deployment or production data changes in E2.
- `openapi.json` is regenerated and checked in CI.

## 14. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Fixture builder cannot extract enough credit detail from cache | Use release-level credits where recording-level data is absent; document coverage; select albums with documented credits. |
| Recording-level aggregation is misinterpreted as full-album credit | Return supporting counts and ratios; UI labels scope; tests cover both scopes. |
| Generated OpenAPI drifts | CI regenerates and fails on diff. |
| Frontend types drift | `pretypecheck`/`prebuild` generate from the committed contract. |
| Cytoscape performance or lifecycle leaks | One-hop small graph, destroy on unmount, component tests. |
| Loader duplicates data | Deterministic UUIDs and upserts; idempotency test. |
| Test database contamination | Migration/cleanup fixtures; separate `TEST_DATABASE_URL`. |
| Search with diacritics | Preserve case-insensitive search with actual diacritics; document limitation. |
| Scope creep into E3 ingestion | Explicit scope guard and no network calls. |

## 15. Traceability requirements → plan → tasks

| Requirement | Plan section | Tasks |
|---|---|---|
| FR-001 | 4.4, 5 | T-001 |
| FR-002 | 4.4, 6 | T-002 |
| FR-003 | 6.3 | T-003 |
| FR-004 | 7.1 | T-004 |
| FR-005 | 7.2 | T-005 |
| FR-006 | 7.3 | T-006 |
| FR-007 | 8.1–8.3 | T-008, T-009 |
| FR-008 | 8.4–8.5 | T-010 |
| FR-009 | 4.7 | T-007 |
| FR-010 | 12 | T-011 |
| FR-011 | 13 | T-012 |
| FR-012 | 1, 9 | T-012 |
| NFR-001 | 4.4, 6 | T-002, T-003 |
| NFR-002 | 7 | T-004, T-005, T-006, T-011 |
| NFR-003 | 4.4, 10 | T-002, T-003, T-012 |
| NFR-004 | 8.4 | T-010 |
| NFR-005 | 10 | T-003, T-012 |
| NFR-006 | 4 | T-001, T-004 |
| NFR-007 | 13 | T-012 |
| NFR-008 | 3 | T-012 |

## 16. Approval and next step

This plan is a draft. It must be reviewed and approved together with `tasks.md` before implementation starts. The first task is T-001.
