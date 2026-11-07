# Technical plan — SPEC-003 MusicBrainz ingestion

- **Status:** Approved
- **Spec:** [spec.md](spec.md)
- **Tasks:** [tasks.md](tasks.md)
- **Stage:** E3
- **Module:** `ingestion`
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0002](../../docs/01-architecture/adr/ADR-0002-musicbrainz-primary-source.md), [ADR-0003](../../docs/01-architecture/adr/ADR-0003-synchronous-sqlalchemy.md), [ADR-0004](../../docs/01-architecture/adr/ADR-0004-release-group-model.md), [ADR-0005](../../docs/01-architecture/adr/ADR-0005-identity-and-provenance.md), [ADR-0007](../../docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md)

## 1. Solution summary

E3 adds a batch ingestion CLI for the 42-band seed list. The CLI reads `data/seed-list.json`, resolves each band directly by MBID, fetches MusicBrainz data through a rate-limited client, stores every response as immutable raw JSON, records provenance and run metadata in PostgreSQL, and writes a versioned extracted dataset plus coverage/failure reports.

The accepted extraction policy is:

- Fetch all releases for each canonical album.
- Preserve release status, date, country and edition context.
- Fetch recording-level relationships once for each unique recording MBID across all fetched releases.
- Retain all documented release-level and recording-level production credits.

E3 does not normalize identities, create canonical catalog rows, calculate quality thresholds, expose API endpoints or change the frontend. The canonical E2 fixture data remains intact until E4 replaces it.

## 2. Architecture and data flow

```text
data/seed-list.json
        │
        ▼
Ingestion CLI
  │ validate seed list
  │ create ingest_run
  │ load or fetch cached raw responses
  ▼
MusicBrainz HTTP client
  │ User-Agent
  │ 1 request/second
  │ timeout · retry · Retry-After
  ▼
Raw store                         PostgreSQL
  data/raw/musicbrainz/            ingest_run
  <payload_hash>.json       ◄────► raw_response
                                   ingest_error
        │
        ▼
Traversal / extraction
  artist → release-groups → releases → recordings → relationships
        │
        ▼
Versioned dataset + manifest + coverage/failure report
  data/ingestions/musicbrainz/<dataset_version>/
```

The API process never imports or invokes the ingestion client. Ingestion is exposed only through the CLI or the Compose `ingest` profile.

## 3. Components and responsibilities

| Component or path | Responsibility |
|---|---|
| `backend/src/hmde/core/config.py` | Add MusicBrainz base URL, User-Agent and timeout configuration. |
| `backend/src/hmde/models/ingestion.py` | `IngestRun`, `RawResponse` and `IngestError` models. |
| `backend/src/hmde/etl/__init__.py` | ETL package boundary. |
| `backend/src/hmde/etl/musicbrainz/__init__.py` | MusicBrainz ingestion package. |
| `backend/src/hmde/etl/musicbrainz/cli.py` | CLI parsing, orchestration and exit codes. |
| `backend/src/hmde/etl/musicbrainz/client.py` | MusicBrainz HTTP client, retry policy and cache integration. |
| `backend/src/hmde/etl/musicbrainz/rate_limit.py` | Process-wide one-request-per-second limiter. |
| `backend/src/hmde/etl/musicbrainz/raw_store.py` | Immutable raw payload storage and request-key hashing. |
| `backend/src/hmde/etl/musicbrainz/traversal.py` | Artist, release-group, release, recording and relationship traversal. |
| `backend/src/hmde/etl/musicbrainz/dataset.py` | Extracted NDJSON dataset, manifest and checksums. |
| `backend/src/hmde/etl/musicbrainz/report.py` | Coverage, failure and run summary report. |
| `backend/alembic/versions/0004_ingestion_layer.py` | Ingestion tables, constraints and indexes. |
| `backend/tests/unit/` | Seed validation, rate limiter, retry, cache key, dataset and report tests. |
| `backend/tests/integration/` | Migration, raw persistence, idempotency, resume, cache-only replay and CLI tests. |
| `backend/tests/fixtures/musicbrainz/` | Small reviewed API payloads for tests; no live network. |
| `compose.yaml` | Add an `ingest` one-off profile with writable `./data:/data`; keep API data read-only. |
| `.env.example` | Document `MUSICBRAINZ_USER_AGENT` and optional base URL/timeout settings. |
| `.gitignore` | Ignore `data/ingestions/`; `data/raw/` is already ignored. |
| `README.md`, `AGENTS.md`, `data/README.md` | Document commands, data locations, provenance and validation. |

## 4. Technical decisions and alternatives

### 4.1 Seed input and identity

- Read `data/seed-list.json` v0.1.0.
- Validate exactly 42 verified bands, unique MBIDs and the expected subgenre distribution.
- Resolve artists with `/artist/{mbid}` lookups.
- Never use artist name search for seed resolution.
- Use MBIDs as deterministic source keys; no fuzzy matching.
- Treat a missing or malformed seed list as a fatal validation error before writing data.

### 4.2 MusicBrainz traversal

- Fetch artist metadata and URL relationships; derive the Wikidata QID from a Wikidata URL when present.
- Browse all release-groups for the artist with pagination.
- Filter canonical album candidates after fetching: primary type `album`, no secondary type, first release date in 1980–2000.
- Fetch all releases for every relevant release-group; retain release status, date and country.
- Browse releases with `recordings+recording-level-rels+artist-rels+place-rels` so release and recording relationships arrive in paginated bulk responses.
- Fall back to release and recording lookups only when the browse payload does not contain media/recording relationships.
- Build the unique recording MBID set across all fetched releases and extract each recording once from the browse payload.
- Preserve raw roles and attributes for `producer`, `co`, `executive`, `assistant`, `additional`, `engineer`, `mix`, `mastering` and place relationships.
- Keep excluded release-groups and their exclusion reason in the extracted dataset for auditability.
- Exact `inc` query combinations are verified against the MusicBrainz API during implementation; every request URL and parameter set is recorded in raw provenance.

Planned endpoint families:

```text
/ws/2/artist/{mbid}?inc=url-rels&fmt=json
/ws/2/release-group?artist={mbid}&type=album&limit=100&offset=...&fmt=json
/ws/2/release?release-group={rg_mbid}&inc=recordings+recording-level-rels+artist-rels+place-rels&limit=100&offset=...&fmt=json
/ws/2/release/{mbid}?inc=recordings+artist-rels+place-rels&fmt=json  # fallback only
/ws/2/recording/{mbid}?inc=artist-rels+place-rels&fmt=json          # fallback only
```

### 4.3 Raw storage

- Store the response body as an immutable file under `data/raw/musicbrainz/<payload_hash>.json`.
- Store metadata in `raw_response`: request URL, parameters, request key, entity type, external ID, fetch time, HTTP status, payload hash, raw path, license, API version and first run.
- Use a canonical request key derived from method, URL, normalized query parameters and API version.
- Use the payload hash as the content address.
- Never edit raw files in place.
- Keep changed source responses as additional raw rows with the same request key and a different payload hash.
- Cache-only mode reads raw files and fails on a missing or hash-mismatched file.

### 4.4 HTTP client and rate limit

- Use synchronous `httpx` for deterministic sequential fetching; ADR-0003 permits asynchronous ingestion but does not require it.
- Use one process-wide limiter enforcing a minimum of 1.0 second between request starts.
- Send a mandatory `MUSICBRAINZ_USER_AGENT` with project and contact details.
- Use a 30-second default timeout.
- Retry network errors, `429` and `5xx` with bounded exponential backoff and jitter; at most three attempts.
- Honour `Retry-After` when present.
- Do not retry other `4xx` responses.
- Record every attempt outcome in the run counters and errors.
- Do not fetch in parallel in E3.

### 4.5 Extracted dataset

- Write deterministic NDJSON files:
  - `artists.ndjson`
  - `external_ids.ndjson`
  - `release_groups.ndjson`
  - `releases.ndjson`
  - `recordings.ndjson`
  - `release_recordings.ndjson`
  - `artist_relationships.ndjson`
  - `credits.ndjson`
  - `places.ndjson`
  - `exclusions.ndjson`
- Every record includes its MBID, normalized source fields and `raw_response_id`.
- Deterministic ordering uses MBID, entity type and relationship key.
- `manifest.json` records seed-list version, dataset version, source snapshot time, code version, parameters, counts, file checksums and API version.
- `coverage.json` and `report.md` summarize counts, coverage and failures.
- A cache-only replay of the same raw files must produce byte-identical NDJSON files and the same manifest checksum.

### 4.6 Execution environments

- Host CLI is the primary operator path.
- Add a Compose `ingest` one-off profile using the existing backend image, with a writable `./data:/data` mount and the same database environment.
- Keep the API container’s `data` mount read-only.
- Do not run ingestion during API startup or frontend builds.

### 4.7 Alternatives considered

| Alternative | Reason for rejection |
|---|---|
| Store raw payloads only as JSONB in PostgreSQL | Conflicts with the architecture principle that PostgreSQL is not a schemaless JSON store and makes large payload retention harder to manage. |
| Store raw metadata only in filesystem manifests | Loses queryable run/error/request history and makes provenance checks harder. |
| Fetch only a representative release per album | Would omit documented release-level credits and the accepted extraction policy. |
| Fetch all releases but only producer roles | Would lose engineer, mix, mastering and studio evidence needed by later analyses. |
| Parallel HTTP requests | Increases block risk and violates the one-request-per-second constraint. |
| Use MusicBrainz dumps in E3 | Dumps belong to a later scale phase; the API path is sufficient for 42 bands. |
| Normalize during ingestion | Violates the E3/E4 boundary and mixes raw provenance with canonical identity decisions. |

## 5. Data model and migrations

### 5.1 `ingest_run`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | Run identifier. |
| `seed_list_version` | String(50) | Source list version. |
| `dataset_version` | String(100) nullable | Set when an extracted dataset is written. |
| `status` | String(30) | `running`, `completed`, `completed_with_errors`, `failed`. |
| `started_at` | timestamptz | Run start. |
| `finished_at` | timestamptz nullable | Run completion. |
| `code_version` | String(100) | Git commit or fallback build identifier. |
| `parameters` | JSONB | Seed subset, cache mode, output path and flags. |
| `counters` | JSONB | Requests, cache hits, retries, entities, credits and failures. |
| `output_path` | Text nullable | Extracted dataset directory. |
| `source_snapshot_at` | timestamptz nullable | First successful live fetch time for the dataset. |

Constraints: status check; `finished_at` required when status is terminal; indexes on `status` and `started_at`.

### 5.2 `raw_response`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | Raw response identifier. |
| `first_ingest_run_id` | UUID FK | First run that fetched this payload. |
| `source` | String(50) | `musicbrainz`. |
| `source_entity_type` | String(50) | Artist, release-group, release, recording, relationship type. |
| `external_id` | String(255) | MBID or stable source identifier. |
| `request_key` | String(64) | Canonical request hash. |
| `request_url` | Text | Exact URL. |
| `request_params` | JSONB | Normalized query parameters. |
| `fetched_at` | timestamptz | Response timestamp. |
| `http_status` | Integer | HTTP response code. |
| `payload_hash` | String(64) | SHA-256 of the raw body. |
| `raw_path` | Text | Path relative to the raw root. |
| `license` | String(100) | License applicable to the payload. |
| `api_version` | String(50) | MusicBrainz API version. |

Constraints: unique `(request_key, payload_hash)`; indexes on `request_key`, `(source, external_id)` and `first_ingest_run_id`.

### 5.3 `ingest_error`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | Error identifier. |
| `ingest_run_id` | UUID FK | Run. |
| `band_mbid` | String(36) nullable | Band context. |
| `phase` | String(50) | Seed validation, artist, release-group, release, recording, dataset or report. |
| `request_key` | String(64) nullable | Related request. |
| `error_type` | String(100) | HTTP, timeout, validation or storage error. |
| `message` | Text | Safe message; no secrets or raw payload dumps. |
| `attempts` | Integer | Attempts made. |
| `occurred_at` | timestamptz | Error timestamp. |

Indexes on `ingest_run_id` and `band_mbid`.

### 5.4 Migration

Create `0004_ingestion_layer.py` with all three tables, constraints and indexes. The migration must:

- apply from an empty database;
- downgrade cleanly;
- not modify E2 canonical tables;
- not seed data.

## 6. API contract

No API changes.

- No new endpoints.
- No response schema changes.
- Existing `/health` and `/api/v1/bands` endpoints remain unchanged.
- `openapi.json` must remain unchanged; CI drift detection covers this.
- The API process must not import `hmde.etl.musicbrainz`.

## 7. Frontend impact

No frontend changes.

- No new routes, components, query keys or generated types.
- The E2 band explorer continues to read the canonical fixture data.
- The frontend is not part of the ingestion runtime.

## 8. Error handling and consistency

- Validate the seed list before writing any run or raw data.
- Create the `ingest_run` before the first request; update status and counters as work progresses.
- Isolate failures per band and phase; one failed band does not roll back successful bands.
- A fatal database or configuration error marks the run failed and exits nonzero.
- Partial runs are `completed_with_errors`; they are not presented as complete datasets.
- Retry only transient HTTP/network failures; record exhaustion in `ingest_error`.
- A cache-only run fails on missing or corrupt cache entries rather than bypassing the cache.
- A changed source response creates a new raw row; it never overwrites an old payload.
- Dataset and report writes use a temporary directory and atomic rename where practical.
- Do not delete prior raw payloads, datasets or runs.
- Database writes for a single band/phase use a transaction boundary that leaves completed entities consistent after interruption.

## 9. Security and trust boundaries

- No authentication or write API is introduced.
- `MUSICBRAINZ_USER_AGENT` is configuration, not a secret; it must identify the project and a contact mechanism.
- No tokens or credentials are logged or written to raw files.
- Raw files are local data outside Git and readable only by the operator.
- The API container keeps `./data` read-only; only the `ingest` profile gets write access.
- Source licensing is preserved per raw response. Public display policy is deferred to E12.
- SQL uses parameterized SQLAlchemy statements; no raw user input is interpolated.
- Ingestion cannot be triggered by an HTTP request.

## 10. Observability

- Structured logs include run ID, phase, band MBID, request key, attempt, cache result and final status.
- Logs never include full raw payloads or secrets.
- `ingest_run.counters` captures requests, cache hits, retries, entity counts, credit counts and failures.
- `ingest_error` captures structured failures.
- `report.md` is the human-readable summary; `coverage.json` is machine-readable.
- No metrics or tracing service is added.

## 11. Testing strategy

| Level | What is tested | Evidence |
|---|---|---|
| Unit | Seed validation, request-key hashing, rate limiter, retry policy, cache behavior, dataset ordering/checksums and report counters. | `backend/tests/unit/test_ingest_*.py` |
| Integration | Migration, `ingest_run`/`raw_response`/`ingest_error` persistence, idempotent rerun, resume, cache-only replay and CLI exit codes. | `backend/tests/integration/test_ingestion_*.py` |
| Data fixtures | Representative MusicBrainz payloads for artist, release-group, release, recording, relations, places and errors. | `backend/tests/fixtures/musicbrainz/` |
| Contract | `openapi.json` unchanged; API does not import ingestion modules. | CI and scope tests |
| Frontend | Not affected. | Existing frontend suite |
| Manual | Controlled 42-band live ingestion, cache-only replay and report review. | T-012 evidence |

Commands:

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
TEST_DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde_test \
  uv run pytest
```

The test suite must not call MusicBrainz. Mocked transports or committed synthetic payloads are mandatory.

## 12. Deployment and reversibility

- Apply `0004_ingestion_layer` after `0003_credit_target_restrict`.
- Downgrade drops only ingestion tables and leaves canonical E2 data intact.
- Add `MUSICBRAINZ_USER_AGENT` to environment configuration and `.env.example`.
- Add `data/ingestions/` to `.gitignore`; `data/raw/` is already ignored.
- Add a Compose `ingest` one-off profile with writable `./data:/data`.
- Keep the API service read-only with respect to `./data`.
- Migration rollback is safe because ingestion tables contain no canonical references from E2.
- Full raw datasets are retained locally and are not part of the repository.

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| MusicBrainz rate-limit violation or IP block | Process-wide limiter, sequential requests, User-Agent and retry/`Retry-After` handling. |
| Full recording-level traversal exceeds time budget | Deduplicate recording MBIDs, measure request counts in the report and use the accepted all-releases policy. |
| Source data changes between runs | Content-addressed raw payloads, immutable history, dataset versions and cache-only replay. |
| Large raw storage footprint | Store files outside Git, use content addressing and document retention. |
| Corrupt or missing cache | Hash validation; fail cache-only runs; refetch in live mode. |
| Partial ingestion looks complete | Explicit `completed_with_errors` status and failure report. |
| API gains a network dependency | Import boundary test and scope guard. |
| Ingestion writes canonical data accidentally | Service boundary, tests that assert canonical counts are unchanged and code review. |
| Licensing ambiguity | Preserve license per response; defer public display policy to E12. |
| Scope creep into normalization or graph analysis | E3 layer boundary and out-of-scope list; E4/E7 own those steps. |

## 14. Traceability requirements → plan → tasks

| Requirement | Plan section | Tasks |
|---|---|---|
| FR-001 | 4.1 | T-005 |
| FR-002 | 4.4 | T-004 |
| FR-003 | 4.2 | T-006 |
| FR-004 | 4.3, 5.2 | T-002, T-003 |
| FR-005 | 5.1, 5.3 | T-002, T-005 |
| FR-006 | 4.3, 8 | T-003, T-009 |
| FR-007 | 4.5 | T-007 |
| FR-008 | 4.5, 10 | T-008 |
| FR-009 | 4.6 | T-001, T-005, T-009, T-010 |
| FR-010 | 11 | T-011 |
| FR-011 | 6, 8 | T-002, T-011, T-012 |
| FR-012 | 3, 12 | T-010, T-012 |
| NFR-001 | 4.3, 4.5 | T-003, T-006, T-007, T-009, T-012 |
| NFR-002 | 4.4 | T-004, T-011 |
| NFR-003 | 4.3, 5.2 | T-002, T-003, T-006 |
| NFR-004 | 8 | T-005, T-009 |
| NFR-005 | 4.2, 4.4 | T-006, T-012 |
| NFR-006 | 9, 12 | T-001, T-010 |
| NFR-007 | 3, 11 | T-001, T-002, T-011 |
| NFR-008 | 3, 4 | T-001, T-006 |
| NFR-009 | 10 | T-008 |
| NFR-010 | 3, 10 | T-010, T-012 |
| AC-001 | 4.1 | T-005, T-012 |
| AC-002 | 4.4 | T-004, T-011 |
| AC-003 | 4.3 | T-003, T-011 |
| AC-004 | 4.2 | T-006, T-011 |
| AC-005 | 5.1, 5.3 | T-002, T-005 |
| AC-006 | 8 | T-009 |
| AC-007 | 4.5 | T-007, T-009 |
| AC-008 | 4.5 | T-008 |
| AC-009 | 8 | T-005, T-009 |
| AC-010 | 11 | T-011 |
| AC-011 | 6 | T-002, T-011, T-012 |
| AC-012 | 4.5, 4.6 | T-012 |

## 15. Approval and next step

This plan must be approved together with `tasks.md` before implementation starts. The first task is T-001 (configuration, package boundary and CLI skeleton), followed by the ingestion schema and raw store.
