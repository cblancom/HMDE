# Tasks — SPEC-003 MusicBrainz ingestion

- **Status:** Implemented (local validation complete; remote CI pending)
- **Spec:** [spec.md](spec.md)
- **Plan:** [plan.md](plan.md)

## 1. Execution order

```text
T-001 ──► T-002 ──► T-003 ──► T-004 ──► T-005 ──► T-006
                                                   │
                                                   ▼
T-007 ──► T-008 ──► T-009 ──► T-010 ──► T-011 ──► T-012
```

T-001 establishes the package and configuration boundary. T-002 and T-003 establish persistence and raw storage. T-004–T-006 implement the client and traversal. T-007–T-010 produce the dataset, report, resume behaviour and operator surface. T-011 completes automated coverage. T-012 performs the controlled full 42-band validation.

## 2. Tasks

### T-001 — Add ingestion configuration, package boundary and CLI skeleton

- **Requirements:** FR-009, NFR-006, NFR-007, NFR-008.
- **Dependencies:** none.
- **Status:** Completed (2026-11-06).
- **Description:** create the `hmde.etl` and `hmde.etl.musicbrainz` packages; add MusicBrainz User-Agent, base URL, timeout and minimum-interval settings; add the CLI entry point and help output without implementing network calls.
- **Done when:** the module resolves, `--help` works, live mode rejects a missing User-Agent, cache-only mode can run without a User-Agent, and the API does not import the new package.
- **Verification:**
  ```bash
  cd backend
  uv run python -m hmde.etl.musicbrainz --help
  uv run pytest tests/unit/test_ingest_config.py tests/unit/test_ingest_cli.py
  uv run ruff check .
  ```
- **Files:** `backend/src/hmde/etl/__init__.py`, `backend/src/hmde/etl/musicbrainz/__init__.py`, `backend/src/hmde/etl/musicbrainz/__main__.py`, `backend/src/hmde/etl/musicbrainz/cli.py`, `backend/src/hmde/core/config.py`, `backend/tests/unit/test_ingest_config.py`, `backend/tests/unit/test_ingest_cli.py`, `.env.example`.
- **Evidence:** 2026-11-06: the ingestion package and `python -m hmde.etl.musicbrainz --help` resolve without runtime settings; live mode rejects a missing User-Agent while cache-only mode proceeds; the parser supports band subsets, maximum-band limits, cache-only and refresh modes. Configuration tests cover defaults, environment parsing, positive numeric values and the one-request-per-second floor. 12 targeted tests and the full backend suite (48 tests) pass; Ruff check/format pass; importing `hmde.main` loads no `hmde.etl` modules.

### T-002 — Create the ingestion schema and migration

- **Requirements:** FR-004, FR-005, NFR-003, NFR-007.
- **Dependencies:** T-001.
- **Status:** Completed (2026-11-06).
- **Description:** add `IngestRun`, `RawResponse` and `IngestError` models and Alembic migration `0004_ingestion_layer`; add status constraints, uniqueness and lookup indexes; keep all E2 canonical tables unchanged.
- **Done when:** the migration applies from empty, downgrades cleanly and the required columns, constraints and indexes exist.
- **Verification:**
  ```bash
  cd backend
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde_test \
    uv run alembic upgrade head
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde_test \
    uv run alembic downgrade base
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde_test \
    uv run alembic upgrade head
  uv run pytest tests/unit/test_ingestion_models.py tests/integration/test_ingestion_migration.py
  ```
- **Files:** `backend/src/hmde/models/ingestion.py`, `backend/src/hmde/models/__init__.py`, `backend/alembic/versions/0004_ingestion_layer.py`, `backend/tests/unit/test_ingestion_models.py`, `backend/tests/integration/test_ingestion_migration.py`.
- **Evidence:** 2026-11-06: `0004_ingestion_layer` adds `ingest_run`, `raw_response` and `ingest_error` with status/finished-at checks, HTTP-status and attempt checks, request/payload uniqueness and lookup indexes. The migration upgraded `0003 → 0004`, downgraded to base and reapplied successfully on the test database; the local `hmde` database is at `0004 (head)`. The migration test confirms the three tables, columns, checks, unique constraint, indexes and FK delete rules, while all E2 canonical tables remain present. Targeted tests: 6 passed. Full backend suite: 54 passed; Ruff check/format pass.

### T-003 — Implement immutable raw storage and request cache

- **Requirements:** FR-004, FR-006, NFR-001, NFR-003.
- **Dependencies:** T-002.
- **Status:** Completed (2026-11-06).
- **Description:** implement canonical request keys, SHA-256 payload hashing, atomic raw-file writes under `data/raw/musicbrainz/`, `raw_response` persistence and cache lookup with corruption detection.
- **Done when:** raw payloads are immutable and content-addressed; cache hits return the original metadata; missing or hash-mismatched payloads are reported; no unrelated files are deleted.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_raw_store.py tests/integration/test_raw_store.py
  ```
- **Files:** `backend/src/hmde/etl/musicbrainz/raw_store.py`, `backend/tests/unit/test_raw_store.py`, `backend/tests/integration/test_raw_store.py`.
- **Evidence:** 2026-11-06: raw payloads are stored atomically as SHA-256 content-addressed JSON files; request keys are deterministic across parameter ordering and include method, URL, normalized params and API version. `RawStore` persists `raw_response`, reuses identical request/payload pairs, preserves changed payloads as new rows and returns the latest cached response. Missing and hash-mismatched files raise explicit errors, unrelated files are preserved and no temporary files remain. Targeted tests: 9 passed. Full backend suite: 63 passed; Ruff check/format pass.

### T-004 — Implement the MusicBrainz HTTP client

- **Requirements:** FR-002, FR-010, NFR-002, NFR-004.
- **Dependencies:** T-001, T-003.
- **Status:** Completed (2026-11-06).
- **Description:** implement the synchronous `httpx` client with mandatory User-Agent, process-wide 1 request/second limiter, 30-second timeout, bounded exponential backoff with jitter, `Retry-After` handling, JSON parsing and integration with raw storage.
- **Done when:** mocked transports prove rate limiting, retry, exhaustion, `429`, `5xx`, timeout and non-retryable `4xx` behaviour; no live network is used in tests.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_musicbrainz_client.py tests/unit/test_rate_limit.py
  uv run ruff check .
  ```
- **Files:** `backend/src/hmde/etl/musicbrainz/client.py`, `backend/src/hmde/etl/musicbrainz/rate_limit.py`, `backend/tests/unit/test_musicbrainz_client.py`, `backend/tests/unit/test_rate_limit.py`, `backend/tests/unit/test_scope_guard.py`, `backend/pyproject.toml`, `backend/uv.lock`.
- **Evidence:** 2026-11-06: the client enforces a mandatory User-Agent, `Accept: application/json`, a process-wide minimum request interval, 30-second default timeout, three attempts, exponential backoff with jitter and `Retry-After` handling. It reuses valid cached responses, supports cache-only misses, stores successful payloads through `RawStore`, parses JSON objects and rejects invalid JSON. MockTransport tests cover success, cache hits/misses, 429, 5xx exhaustion, 404, timeouts and invalid JSON. Rate-limiter tests cover spacing and elapsed-time behaviour. `httpx` is now a runtime dependency. The E2 scope guard was narrowed so network imports are confined to the MusicBrainz client. Targeted tests: 12 passed. Full backend suite: 76 passed; Ruff check/format pass.

### T-005 — Implement seed-list validation and run orchestration

- **Requirements:** FR-001, FR-005, FR-009, NFR-004.
- **Dependencies:** T-002, T-004.
- **Status:** Completed (2026-11-06).
- **Description:** load and validate seed-list v0.1.0, support band/MBID and maximum-count subsets, create and update `ingest_run`, isolate per-band failures and expose stable success/partial/failure status.
- **Done when:** valid input produces a running/completed run; malformed or duplicate input fails before writes; a failed band does not abort successful bands; subset runs are auditable.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_seed_validation.py tests/integration/test_ingest_run.py
  ```
- **Files:** `backend/src/hmde/etl/musicbrainz/cli.py`, `backend/src/hmde/etl/musicbrainz/seed.py`, `backend/tests/unit/test_seed_validation.py`, `backend/tests/integration/test_ingest_run.py`.
- **Evidence:** 2026-11-06: seed-list loading validates version 0.1.0, 42 bands, verified status, MBIDs, subgenre membership, 6 bands per subgenre, unique MBIDs and positive sequence. Selection supports MBID subsets and maximum counts, canonicalizes requested MBIDs and rejects unknown or invalid MBIDs before writing. `IngestRunner` creates a running `ingest_run`, processes each band in an isolated session/transaction, records per-band `IngestError`, continues after failures and finishes as `completed` or `completed_with_errors` with counters and parameters. Targeted tests: 13 passed. Full backend suite: 89 passed; Ruff check/format pass.

### T-006 — Implement MusicBrainz traversal and credit extraction

- **Requirements:** FR-003, NFR-001, NFR-003, NFR-005.
- **Dependencies:** T-005.
- **Status:** Completed (2026-11-06).
- **Description:** implement artist lookups, QID extraction, release-group browsing and canonical filtering, all-release fetching, unique recording lookups, relationship/credit extraction, place relationships and exclusion reasons.
- **Done when:** synthetic payloads produce artists, release-groups, releases, unique recordings, release/recording-scoped credits, QIDs, places and exclusions with raw provenance; all releases and unique recordings are represented.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_musicbrainz_traversal.py tests/integration/test_musicbrainz_traversal.py
  ```
- **Files:** `backend/src/hmde/etl/musicbrainz/traversal.py`, `backend/tests/unit/test_musicbrainz_traversal.py`, `backend/tests/integration/test_musicbrainz_traversal.py`, `backend/tests/fixtures/musicbrainz/`.
- **Evidence:** 2026-11-06: traversal resolves artists and Wikidata QIDs, paginates release-groups, applies canonical album filters, records exclusions with reasons, fetches every release for canonical albums, performs one lookup per unique recording MBID and preserves raw response IDs on every extracted entity. Credits are preserved at release-group, release and recording scope with raw roles/attributes; places retain relation type and scope; tags and genres are captured. Synthetic fixture tests cover entity counts, unique recording lookup, pagination, exclusion reasons and date precision. Integration test exercises the real HTTP client, raw store and traversal with MockTransport and confirms seven raw responses. T-012 later added a bulk browse path for release/recording relationships, with lookup fallback, reducing production request volume while preserving the unique-recording rule. Targeted tests: 10 passed at T-006 time. Full backend suite after T-012: 120 passed; Ruff check/format pass.

### T-007 — Write the versioned extracted dataset and manifest

- **Requirements:** FR-007, NFR-001.
- **Dependencies:** T-006.
- **Status:** Completed (2026-11-06).
- **Description:** write deterministic NDJSON files, stable ordering, dataset version, source snapshot metadata, manifest counts and file checksums; support cache-only replay from raw files.
- **Done when:** the same raw inputs produce byte-identical NDJSON and manifest checksums; every extracted record references a raw response; the dataset can be consumed by E4 without canonical writes.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_ingest_dataset.py tests/integration/test_dataset_replay.py
  ```
- **Files:** `backend/src/hmde/etl/musicbrainz/dataset.py`, `backend/tests/unit/test_ingest_dataset.py`, `backend/tests/integration/test_dataset_replay.py`, `backend/tests/support/extractions.py`.
- **Evidence:** 2026-11-06: dataset writer emits nine deterministic NDJSON files for artists, external IDs, release-groups, releases, recordings, release-recordings, credits, places and exclusions, plus `manifest.json`. Files use stable ordering, exact-record deduplication, compact sorted JSON and raw-response references. Dataset versions combine the UTC source snapshot with a content hash; manifests include seed-list version, source snapshot, code version, schema/API versions, band count, file counts and SHA-256 checksums. Replaying the same extraction into separate roots produced identical versions, file bytes and manifests; writing to the same root is idempotent when the manifest matches. Targeted tests: 5 passed. Full backend suite: 104 passed; Ruff check/format pass.

### T-008 — Generate coverage and failure reports

- **Requirements:** FR-008, NFR-009.
- **Dependencies:** T-006, T-007.
- **Status:** Completed (2026-11-06).
- **Description:** generate `coverage.json` and `report.md` with band, subgenre, decade, release-group exclusion, release, recording, role, scope, cache, request and failure counts, including missing-data wording.
- **Done when:** reports are deterministic for a fixed dataset, include per-band failure details and explicitly state that missing data is not negative evidence.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_ingest_report.py
  ```
- **Files:** `backend/src/hmde/etl/musicbrainz/report.py`, `backend/tests/unit/test_ingest_report.py`, `backend/tests/support/extractions.py`, `backend/src/hmde/etl/musicbrainz/traversal.py`.
- **Evidence:** 2026-11-06: coverage generation reports dataset/run metadata, summary counts, credits by role and scope, exclusions by reason, per-band coverage, subgenre and decade coverage, run counters and structured failures. Producer/co-producer coverage is derived across release-group, release and recording scopes, mapping recordings back to albums through release links. `coverage.json` and `report.md` are deterministic for a fixed extraction and include the explicit statement that missing data is not negative evidence. `BandExtraction` now carries the seed subgenre so reports can group by it. Targeted tests: 3 passed. Full backend suite: 107 passed; Ruff check/format pass.

### T-009 — Implement idempotency, resume, cache-only and refresh modes

- **Requirements:** FR-006, FR-009, NFR-001, NFR-004.
- **Dependencies:** T-003, T-005, T-006, T-007.
- **Status:** Completed (2026-11-06).
- **Description:** make reruns safe, retry only failed bands, reuse cached responses, support cache-only and explicit refresh modes, prevent duplicate raw/extracted records and preserve prior datasets/runs.
- **Done when:** reruns leave extracted entity/credit counts unchanged; resume retries failures only; cache-only makes no network calls; refresh creates new raw responses and a new dataset version without overwriting history.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/integration/test_ingest_idempotency.py tests/integration/test_ingest_resume.py
  ```
- **Files:** `backend/src/hmde/etl/musicbrainz/pipeline.py`, `backend/src/hmde/etl/musicbrainz/cli.py`, `backend/tests/integration/test_ingest_idempotency.py`, `backend/tests/integration/test_ingest_resume.py`, `backend/tests/integration/test_ingest_run.py`.
- **Evidence:** 2026-11-06: `IngestPipeline` connects runner, client, raw store, traversal, dataset and report. It commits partial raw responses before propagating a band failure so a retry reuses successful requests and fetches only missing ones. Raw responses are deduplicated by request/payload, reruns leave dataset bytes/version unchanged, cache-only makes no HTTP calls, and refresh with changed source data adds a raw response and a new dataset version while preserving the previous dataset. Run records store dataset version, source snapshot, output path and raw/entity counters. Targeted tests: 4 passed. Full backend suite: 111 passed; Ruff check/format pass.

### T-010 — Complete the CLI, Compose ingestion profile and documentation

- **Requirements:** FR-009, FR-012, NFR-006, NFR-007, NFR-010.
- **Dependencies:** T-008, T-009.
- **Status:** Completed (2026-11-06).
- **Description:** complete CLI flags and exit codes; add the Compose `ingest` profile with writable `./data:/data`; keep API data read-only; ignore `data/ingestions/`; document environment variables, commands, raw/dataset locations and report usage.
- **Done when:** host and Compose commands run from documented steps; exit codes distinguish success, partial and failure; no API or frontend change is introduced.
- **Verification:**
  ```bash
  cd backend
  uv run python -m hmde.etl.musicbrainz --help
  uv run pytest tests/integration/test_ingest_cli.py
  cd ..
  docker compose config -q
  ```
- **Files:** `backend/src/hmde/etl/musicbrainz/cli.py`, `backend/tests/integration/test_ingest_cli.py`, `compose.yaml`, `.env.example`, `.gitignore`, `README.md`, `AGENTS.md`, `data/README.md`.
- **Evidence:** 2026-11-06: the CLI now loads and validates the seed list, runs `IngestPipeline`, supports `--raw-root`, cache-only, refresh and subset flags, and returns `0` for completed, `2` for completed with band failures and `1` for fatal errors. The Compose `ingest` profile uses the backend image with writable `./data:/data`, while the API keeps its data mount read-only. `data/ingestions/` is ignored. README and AGENTS document host/Compose commands, cache/refresh behavior, output locations, User-Agent configuration and exit codes. CLI tests: 5 passed. The Compose `ingest` profile was also executed in cache-only mode for one band. Full backend suite after later tasks: 120 passed; Ruff check/format and `docker compose config` pass.

### T-011 — Complete tests, scope guards and CI coverage

- **Requirements:** FR-010, FR-011, NFR-007.
- **Dependencies:** T-001 through T-010.
- **Status:** Completed (2026-11-06).
- **Description:** complete mocked/recorded tests, migration checks, API import-boundary and scope guards, canonical-table regression checks and CI execution without live network.
- **Done when:** the full backend suite passes; the API cannot import the ingestion client; OpenAPI and canonical fixture data remain unchanged; CI runs the new tests without network.
- **Verification:**
  ```bash
  cd backend
  uv run ruff check .
  uv run ruff format --check .
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
  TEST_DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde_test \
    uv run pytest
  ```
- **Files:** `backend/tests/unit/`, `backend/tests/integration/`, `.github/workflows/ci.yml`.
- **Evidence:** 2026-11-06: the scope guard now checks both network-import confinement and the API/ETL import boundary; ingestion tests are fully mocked and network-free; pipeline idempotency asserts canonical E2 artist/release-group/credit counts are unchanged; migration and OpenAPI drift checks remain in CI. Full backend suite after T-012: 120 passed; Ruff check/format pass. The remote CI run for E3 remains pending a push.

### T-012 — Run the full 42-band ingestion and validate E3

- **Requirements:** FR-011, FR-012, all acceptance criteria.
- **Dependencies:** T-011.
- **Status:** Completed locally (2026-11-06); remote CI confirmation pending a push.
- **Description:** perform a controlled live 42-band ingestion, run cache-only replay, review counts/coverage/failures/runtime, verify canonical E2 data and API contract are unchanged, and record final evidence.
- **Done when:** all ACs have evidence, the full run and offline replay meet their targets, no canonical/API/frontend changes occurred and SPEC-003 is updated with the result.
- **Verification:**
  ```bash
  cd backend
  MUSICBRAINZ_USER_AGENT="HMDE/0.1 (contact)" \
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run python -m hmde.etl.musicbrainz ingest \
      --seed-list ../data/seed-list.json \
      --output ../data/ingestions/musicbrainz

  MUSICBRAINZ_USER_AGENT="HMDE/0.1 (contact)" \
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run python -m hmde.etl.musicbrainz ingest \
      --seed-list ../data/seed-list.json \
      --output ../data/ingestions/musicbrainz \
      --cache-only

  uv run pytest
  uv run ruff check .
  uv run ruff format --check .
  ```
- **Files:** `specs/003-musicbrainz-ingestion/spec.md`, `specs/003-musicbrainz-ingestion/tasks.md`, `README.md`, `AGENTS.md`, `data/README.md`.
- **Evidence:** 2026-11-06: live ingestion completed 42 bands with 0 failures. Raw store contains 2,001 committed responses; the full run used 414 responses (403 new, 11 reused) and completed in 11m15s. Dataset `mb-20261107T165005Z-52404839c696`: 42 artists, 293 release-groups, 4,280 releases, 8,038 recordings, 54,531 release-recordings, 13,765 deduplicated credits, 6,769 places, 3,007 exclusions and 42 Wikidata QIDs. Cache-only replay completed in ~5s and produced the same dataset version and manifest checksum without network access. Canonical E2 counts stayed at 94 artists, 41 release-groups and 859 credits; OpenAPI drift check found no changes. Full backend suite: 120 passed; Ruff check/format pass. Remote E3 CI remains pending a push.

## 3. Coverage matrix

### Functional requirements

| Requirement | Tasks |
|---|---|
| FR-001 | T-005 |
| FR-002 | T-004 |
| FR-003 | T-006 |
| FR-004 | T-002, T-003 |
| FR-005 | T-002, T-005 |
| FR-006 | T-003, T-009 |
| FR-007 | T-007 |
| FR-008 | T-008 |
| FR-009 | T-001, T-005, T-009, T-010 |
| FR-010 | T-011 |
| FR-011 | T-002, T-011, T-012 |
| FR-012 | T-010, T-012 |

### Non-functional requirements

| Requirement | Tasks |
|---|---|
| NFR-001 | T-003, T-006, T-007, T-009, T-012 |
| NFR-002 | T-004, T-011 |
| NFR-003 | T-002, T-003, T-006 |
| NFR-004 | T-005, T-009 |
| NFR-005 | T-006, T-012 |
| NFR-006 | T-001, T-010 |
| NFR-007 | T-001, T-002, T-011 |
| NFR-008 | T-001, T-006 |
| NFR-009 | T-008 |
| NFR-010 | T-010, T-012 |

## 4. Validation evidence

| Criterion | Result | Evidence |
|---|---|---|
| AC-001 | Passed | CLI validated and processed all 42 seed bands |
| AC-002 | Passed | Client rate-limit, retry and 429 tests |
| AC-003 | Passed | Raw provenance, partial-request durability and offline retrieval tests |
| AC-004 | Passed | Traversal extracts entities, credits, places, QIDs and exclusions |
| AC-005 | Passed | Ingest-run status, counters, dataset and failure logging tests |
| AC-006 | Passed | Rerun idempotency and cache reuse tests |
| AC-007 | Passed | Cache-only replay produced the same dataset version without network |
| AC-008 | Passed | coverage.json/report.md assertions and full-run report |
| AC-009 | Passed | Partial-run failure/resume tests |
| AC-010 | Local pass; remote pending | 120 tests and scope guards pass locally; remote CI requires a push |
| AC-011 | Passed | Canonical E2 counts unchanged; OpenAPI drift check clean |
| AC-012 | Passed | 42-band run 11m15s; cache-only replay ~5s; both under targets |

## 5. Notes

- Accepted extraction policy: all releases for relevant release-groups and every unique recording MBID once.
- Raw payloads live outside Git; only small synthetic fixtures are committed for tests.
- Full live ingestion is a manual validation step; CI must use mocked/recorded responses.
- E3 must not normalize canonical data or change the API/frontend.
- Do not mark a task complete until its verification has been executed and recorded.
- Update `spec.md` or `plan.md` first if an implementation decision changes scope.
