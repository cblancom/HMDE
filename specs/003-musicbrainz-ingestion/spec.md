# SPEC-003 — MusicBrainz ingestion

- **Status:** Validated
- **Stage:** E3
- **Iteration:** MVP
- **Module:** `ingestion`
- **Date:** 2026-11-06
- **Depends on:** SPEC-002 validated; E0 source evaluation; [seed list](../../data/seed-list.json) v0.1.0
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0002](../../docs/01-architecture/adr/ADR-0002-musicbrainz-primary-source.md), [ADR-0003](../../docs/01-architecture/adr/ADR-0003-synchronous-sqlalchemy.md), [ADR-0004](../../docs/01-architecture/adr/ADR-0004-release-group-model.md), [ADR-0005](../../docs/01-architecture/adr/ADR-0005-identity-and-provenance.md), [ADR-0007](../../docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md)
- **Plan:** [plan.md](plan.md) (approved)
- **Tasks:** [tasks.md](tasks.md) (validated)
- **Conventions:** [Engineering conventions](../../docs/01-architecture/conventions.md)
- **Owner:** Cristian

## Revision history

| Revision | Date | Change |
|---|---|---|
| 1 | 2026-11-06 | Initial draft; ingestion scope and open questions |
| 2 | 2026-11-06 | Blocking decisions resolved; plan and tasks drafted |
| 3 | 2026-11-06 | Plan approved; T-001 implemented |
| 4 | 2026-11-06 | T-002 implemented (ingestion schema and migration) |
| 5 | 2026-11-06 | T-003 implemented (immutable raw storage and request cache) |
| 6 | 2026-11-06 | T-004 implemented (MusicBrainz HTTP client) |
| 7 | 2026-11-06 | T-005 implemented (seed-list validation and run orchestration) |
| 8 | 2026-11-06 | T-006 implemented (MusicBrainz traversal and credit extraction) |
| 9 | 2026-11-06 | T-007 implemented (versioned extracted dataset and manifest) |
| 10 | 2026-11-06 | T-008 implemented (coverage and failure reports) |
| 11 | 2026-11-06 | T-009 implemented (idempotency, resume and cache modes) |
| 12 | 2026-11-06 | T-010 implemented (CLI, Compose ingestion profile and docs) |
| 13 | 2026-11-06 | T-011 implemented (tests, scope guards and CI coverage) |
| 14 | 2026-11-06 | T-012 implemented (full 42-band run and local E3 validation); remote CI pending |
| 15 | 2026-11-06 | Corpus-v2 direction documented in ADR-0008; historical E3 dataset unchanged |
| 16 | 2026-11-07 | E3 remote CI passed; SPEC-003 validated |

## 1. Context and problem

E2 validated the PostgreSQL → FastAPI → React → Cytoscape path with a 14-band fixture subset. That subset is suitable for demonstrations and tests, but it is not the production data path: it is derived from the disposable E0 spike cache and covers only one third of the MVP seed list.

E3 must extract the full 42-band seed list from MusicBrainz with complete traceability. The output is a reproducible raw layer and a versioned extracted dataset that E4 can normalize into canonical entities. E3 must not normalize identities, calculate quality thresholds or build analytical graphs; those belong to E4, E5 and E7.

The existing E2 `source_record` table stores provenance metadata but not the raw payload, HTTP status, API version, raw location or ingestion-run reference. E3 must define how those requirements are satisfied without weakening the distinction between raw, normalized and analytical layers.

Source and access decisions are already fixed by [ADR-0002](../../docs/01-architecture/adr/ADR-0002-musicbrainz-primary-source.md) and [sources.md](../../docs/03-data/sources.md): MusicBrainz is the primary source, MBIDs are the canonical keys, the client must send an identifiable User-Agent, respect one request per second and preserve raw data. Credit scope follows [ADR-0007](../../docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md).

```text
data/seed-list.json (42 bands)
        │
        ▼
MusicBrainz API
  User-Agent · 1 request/second · retry · cache
        │
        ▼
raw payloads + provenance + ingest_run
        │
        ▼
versioned extracted dataset + coverage/failure report
```

## 2. Users and actors

- **Data operator/developer:** runs the ingestion CLI, inspects the report and retries failed bands.
- **System actor:** the MusicBrainz API supplies source data; PostgreSQL and the raw store persist results.
- **Implementation agent:** works from this spec, the plan, tasks, constitution and ADRs.
- **Future consumers:** E4 normalization, E5 quality, E7 analysis and the API consume E3 outputs.

There are no end-user roles, authentication or write API in E3. Ingestion is a batch/CLI process, never an HTTP request path.

## 3. User stories and flows

### US-001 — Ingest the seed dataset

As a data operator, I want to ingest the 42 seed bands from MusicBrainz so that the project has a complete, traceable raw dataset.

**Expected flow:**

1. The operator runs the documented ingestion command.
2. The command validates the seed list and creates an `ingest_run`.
3. The client fetches artists, release-groups, releases, recordings, relationships and credits.
4. Each response is stored as raw data with provenance.
5. The command writes a versioned extracted dataset and a coverage/failure report.
6. The run ends with a success, partial-success or failure status.

### US-002 — Resume and rerun safely

As a data operator, I want to rerun an ingestion without duplicating data so that retries and interrupted runs are safe.

**Expected flow:**

1. The operator reruns the command for all bands or a subset.
2. Cached raw responses are reused when they match the request key.
3. Failed bands can be retried without refetching successful ones.
4. No canonical or extracted record is duplicated.
5. A new `ingest_run` records the new execution and its counters.

### US-003 — Audit a data point

As a data operator or future normalization process, I want to trace every extracted record to its source response so that the data can be audited and reprocessed.

**Expected flow:**

1. A record references its source URL, MBID, retrieval time, status, hash, license and ingest run.
2. The raw response can be retrieved without calling MusicBrainz.
3. A changed source response is detectable by hash.
4. Original data is never edited by hand.

### US-004 — Reproduce offline

As a developer, I want to regenerate the extracted dataset from stored raw responses without network access so that analyses and tests are reproducible.

**Expected flow:**

1. The operator runs the ingestion in cache-only mode.
2. No network request is made.
3. The extracted dataset and its manifest checksum match the original run.
4. Missing or corrupt cache entries are reported as errors.

### US-005 — Review coverage and failures

As a data operator, I want a report of coverage, missing data and failures so that I can judge whether the dataset is ready for normalization.

**Expected flow:**

1. The report shows counts by band, subgenre and decade.
2. It reports release-groups considered and excluded, releases, recordings, credits by role and scope, cache hits and retries.
3. It lists failed lookups and bands with partial data.
4. It distinguishes unavailable data from negative evidence.

## 4. Functional requirements

### FR-001 — Seed-list input and validation

The ingestion must consume `data/seed-list.json` (v0.1.0) as its authoritative input.

- It must use artist MBIDs directly; name search is not used to resolve seed bands.
- It must validate the seed-list version, total of 42 bands, verified status and unique MBIDs.
- It must reject a missing, malformed or duplicate seed list before writing any data.
- It must allow an explicit subset of bands for development and retry operations.
- It must never silently skip a seed band.

**Verification:** unit tests cover valid, malformed, duplicate and subset inputs; the full run reports 42 input bands.

### FR-002 — MusicBrainz HTTP client

The ingestion must use a dedicated MusicBrainz client.

- Requests go to the MusicBrainz REST API v2 and request JSON responses.
- Every request includes an identifiable User-Agent with project and contact information.
- The client enforces a global minimum interval of one request per second across the process.
- It applies request timeouts, bounded retries and exponential backoff for network errors, `429` and `5xx` responses.
- It honours `Retry-After` when provided.
- It does not scrape HTML and does not use search-by-name for seed artists.
- It records the API version and request URL used for each response.
- Credentials or secrets, if ever introduced, must come from environment configuration and never appear in logs or raw artifacts.

**Verification:** mocked-transport tests cover rate limiting, retry, exhaustion, `429`, timeout and User-Agent headers; no live network is used in tests.

### FR-003 — Entity traversal and extraction

For each seed band, the ingestion must traverse and extract the entities needed by the MVP model:

- Artist metadata and MBID.
- Artist URL relationships needed to capture the Wikidata QID when documented.
- Release-groups for the artist.
- Canonical album candidates: primary type `album`, no secondary type, first release date between 1980-01-01 and 2000-12-31.
- Releases belonging to each relevant release-group, including release date, country and status when available.
- All releases belonging to each relevant release-group, preserving release status, date and country context.
- Recordings associated with the fetched releases.
- Recording-level relationships extracted once for each unique recording MBID across all fetched releases; bulk browse payloads may be used instead of one request per recording.
- Artist relationships and credit-bearing relationships for production roles, including producer attributes (`co`, `executive`, `assistant`, `additional`), engineer, mix and mastering.
- Place/studio relationships when documented.
- Source tags or genres needed for later curated subgenre mapping.

The traversal must preserve the distinction between release-group, release and recording credit scope. All documented release-level credits are retained with edition context. The traversal must keep enough raw data for E4 to normalize the entities and for E7 to construct the network without returning to MusicBrainz for the same dataset snapshot.

**Verification:** recorded or synthetic MusicBrainz responses produce the expected entities, relationships, credit scopes and attributes for representative bands.

### FR-004 — Raw layer and provenance

Every MusicBrainz response used by extraction must be preserved as immutable raw data with at least:

- Source (`musicbrainz`).
- Source entity type and external ID/MBID.
- Exact request URL.
- Retrieval timestamp.
- HTTP status.
- Payload content hash.
- Raw payload or a stable reference to it.
- Applicable license.
- MusicBrainz API version.
- Ingestion run identifier.
- Request parameters and cache key.

Raw data must not be edited by hand. Re-fetching the same request must be detectable through the cache key and payload hash.

**Verification:** tests assert that every extracted record resolves to raw provenance and that stored payloads are not mutated.

### FR-005 — Ingestion-run logging

Each execution must create an `ingest_run` record with:

- Unique run identifier.
- Seed-list version and run parameters.
- Start and end timestamps.
- Status: running, completed, completed with errors or failed.
- Code version.
- Per-entity and per-band counters.
- Cache hits, network requests, retries and failures.
- Structured error records with band/entity context.
- Dataset version and output location when completed.

**Verification:** tests cover successful, partial and failed runs; each run is queryable and reports accurate counters.

### FR-006 — Idempotency and resume

Ingestion must be safe to rerun.

- Successful raw responses are reused from cache by request key.
- Extracted records are upserted or deduplicated by deterministic source keys.
- Rerunning must not duplicate raw responses or extracted records.
- A new execution may add a new `ingest_run` audit row.
- Failed or missing bands can be retried without refetching successful bands.
- Interrupted runs must leave persisted data in a consistent state.
- Ingestion must not delete unrelated canonical or raw records.

**Verification:** running the same dataset twice leaves extracted counts unchanged; resume tests retry only failed units.

### FR-007 — Versioned extracted dataset

The ingestion must produce a versioned extracted dataset with a manifest.

- The manifest records the dataset version, seed-list version, source snapshot date, run parameters, code version, counts and file checksums.
- The extracted dataset has a documented schema and deterministic ordering.
- It contains enough information for E4 normalization and must not require canonical-table mutation.
- A cache-only replay of the same raw inputs must produce the same manifest checksum.
- The dataset location must be outside Git-controlled source data unless a deliberately small, reviewed fixture is promoted for tests.

**Verification:** a replay from cached raw responses produces byte-identical extracted files and manifest checksum.

### FR-008 — Coverage and failure report

The ingestion must generate a human-readable and machine-readable report containing at least:

- Bands processed and failed.
- Release-groups considered, excluded and excluded by reason.
- Releases, recordings and credits by role.
- Credits by scope: release-group, release and recording.
- Coverage by subgenre and decade.
- Cache hits, network requests, retries and cache misses.
- Missing Wikidata QIDs, dates or studio relationships.
- Per-band failure details and partial-data flags.
- Source snapshot date, dataset version and runtime.
- Explicit wording that missing data is not negative evidence.

**Verification:** report snapshots or structured assertions cover counts, coverage and failure entries.

### FR-009 — Ingestion CLI

A documented CLI must support:

- Full seed-list ingestion.
- Subset ingestion by band or maximum band count.
- Cache-only replay with no network access.
- Retry or resume operation for failed bands.
- Output directory selection.
- Stable exit codes that distinguish success, partial success and failure.

The command must be usable from the host and from the Docker Compose API container with the documented fixture/data mounts.

**Verification:** command tests or integration checks cover full, subset, cache-only and failure exit codes.

### FR-010 — Tests without live network

The ingestion test suite must not call MusicBrainz.

- HTTP behaviour is tested with mocked transports or recorded responses.
- Rate limiting, retry, backoff, cache hits and failure exhaustion are covered.
- Traversal and extraction are covered with representative payloads.
- Idempotency, resume and offline replay are covered.
- CI runs the suite without external network access.

**Verification:** tests pass with network access disabled; no test imports or opens a live MusicBrainz connection.

### FR-011 — Layer boundary

E3 owns the raw and extracted layers only.

- It must not replace or update the E2 canonical catalog tables (`artist`, `release_group`, `release`, `recording`, `credit`, `role`, `subgenre`, `artist_subgenre`).
- It must not normalize identities, merge entities, assign final confidence or quarantine records; those belong to E4/E5.
- It must not expose a new write API or change the existing read API contract.
- It must not modify frontend behaviour.

**Verification:** schema and API diffs show no canonical/API behaviour changes; tests assert the canonical fixture dataset remains intact.

### FR-012 — Documentation and scope guard

The implementation must document:

- Ingestion command and parameters.
- Required User-Agent configuration.
- Cache/raw storage location and retention.
- Dataset and report locations.
- Cache-only replay procedure.
- How to inspect failures and coverage.

It must not add Wikipedia, Discogs or Encyclopaedia Metallum ingestion, automated scheduling or 200–500-band expansion.

**Verification:** documentation review and scope-guard tests.

## 5. Non-functional requirements

### NFR-001 — Reproducibility

The same seed list, raw cache and code version must reproduce the same extracted dataset and manifest checksum. A completed run must not require the network to be replayed.

### NFR-002 — Source compliance

The client must never exceed one request per second, must send a meaningful User-Agent, must honour `Retry-After` and must avoid parallel requests that could bypass the limit. The full 42-band run must be feasible under these constraints.

### NFR-003 — Provenance and licensing

Every raw response and extracted record must preserve source, URL, retrieval date, hash, license, API version and run identifier. Core MusicBrainz data and supplementary data must not be conflated; records that cannot be assigned a license are rejected or quarantined.

### NFR-004 — Resilience

A failure for one band, release or recording must not corrupt completed data. Retries are bounded and recorded. Partial runs have an explicit status and never masquerade as complete datasets.

### NFR-005 — Performance

On the development environment, a cold full 42-band run should complete within 120 minutes while respecting one request per second, excluding excessive source outages. A cache-only replay of the same raw data should complete within 5 minutes. The report must record actual runtime.

### NFR-006 — Security

The ingestion is a local batch process. It must not log secrets, tokens or credentials. Environment configuration is allowed for contact details and optional future credentials. No write endpoint is introduced.

### NFR-007 — Compatibility

The ingestion works with Python 3.13, PostgreSQL 16, Docker Compose and the existing `uv`/`pytest`/Ruff toolchain. It must run on the project’s Node-independent backend path.

### NFR-008 — Maintainability

The ingestion lives under the `etl`/`ingestion` boundary and depends on `models`, `db` and `core`, not on the API. Source-specific behaviour is isolated behind the MusicBrainz client. No generic repository abstraction is introduced.

### NFR-009 — Observability

Logs and the report include run ID, phase, band MBID, request counts, retries, cache hits, failures and final status. Logs must not include secrets or unbounded raw payloads.

### NFR-010 — Language

All code, documentation, report labels and error messages are in English.

## 6. Business rules

- **BR-001:** MusicBrainz is the primary source for E3; no other source is ingested.
- **BR-002:** The input dataset is the 42 verified bands in seed-list v0.1.0.
- **BR-003:** A canonical album is a MusicBrainz release-group with primary type `album`, no secondary type and first release between 1980 and 2000.
- **BR-004:** MBID is the deterministic identifier for MusicBrainz entities; E3 does not perform fuzzy matching.
- **BR-005:** Missing data is not negative evidence. A missing credit, date or QID is reported as missing coverage.
- **BR-006:** Raw source data is immutable and must remain retrievable independently of the normalized layer.
- **BR-007:** Every extracted record and credit must carry provenance and the ingestion run that produced it.
- **BR-008:** The one-request-per-second limit and User-Agent requirement apply to every request.
- **BR-009:** E3 does not normalize, merge or quarantine entities; those are E4/E5 responsibilities.
- **BR-010:** No ingestion occurs during an API request or in frontend/test runtime.
- **BR-011:** Source scope does not expand to Discogs, Metallum or Wikipedia in E3.

## 7. Edge cases and errors

- **Invalid seed list:** reject before any write; report the exact validation error.
- **Unknown artist MBID:** record a per-band failure and continue; the final run is partial.
- **No release-groups or no canonical albums:** complete the band with zero albums and report it.
- **Release-group outside 1980–2000:** retain raw evidence but exclude it from the MVP extracted album set with a reason.
- **Non-studio secondary types:** exclude from canonical albums and record the exclusion reason.
- **Missing or partial dates:** preserve precision; do not impute silently.
- **Missing Wikidata QID:** report it as missing coverage; do not fail the band unless required by a future rule.
- **HTTP 429, 5xx or timeout:** retry with bounded backoff; record exhaustion as a failure.
- **Interrupted run:** leave the previous completed dataset intact; the interrupted run is marked failed or incomplete.
- **Corrupt or missing cache entry:** fail the cache-only run; in live mode, refetch and record the event.
- **Duplicate MBIDs or request keys:** deduplicate deterministically and report the occurrence.
- **Very large release or recording sets:** paginate all results; do not truncate silently.
- **Source changed since the previous run:** create a new raw response/hash and retain both; never overwrite history.
- **Ambiguous role attributes:** preserve raw role and attributes; defer mapping to E4.

## 8. Out of scope

- Canonical entity creation, identity resolution and deduplication (E4).
- Credit confidence thresholds, quality rules, quarantine and acceptance thresholds (E5).
- Graph construction, metrics and communities (E7).
- API endpoints, frontend views or graph visualization (E8–E10).
- Wikidata, Wikipedia, Discogs or Encyclopaedia Metallum ingestion.
- MusicBrainz data dumps, scheduled incremental updates or streaming ingestion.
- Expansion to 200–500 bands (E13).
- User accounts, administration UI or write API.
- Public attribution page and release deployment (E12).

## 9. Acceptance criteria

| ID | Criterion | Evidence |
|---|---|---|
| AC-001 | The CLI validates seed-list v0.1.0 and processes all 42 verified band MBIDs. | CLI tests and full-run report |
| AC-002 | The client sends a meaningful User-Agent, enforces one request per second and handles retries/`Retry-After`. | Mocked-transport tests and request log |
| AC-003 | Every raw response has complete provenance and is immutable and retrievable offline. | Provenance tests and raw-store inspection |
| AC-004 | Traversal extracts artist, release-group, release, recording, place, QID and production-credit data with correct scopes and attributes. | Representative-response integration tests |
| AC-005 | Every execution records an `ingest_run` with parameters, status, counters and errors. | Run-log tests |
| AC-006 | Rerunning the same input does not duplicate raw or extracted records; new runs are audited. | Idempotency and resume tests |
| AC-007 | Cache-only replay produces the same extracted manifest checksum without network access. | Offline replay test |
| AC-008 | A coverage and failure report is generated with band, subgenre, decade, scope and role breakdowns. | Report assertions/snapshot |
| AC-009 | Partial failures are recorded, do not corrupt completed data and can be resumed. | Failure/resume tests |
| AC-010 | The test suite makes no live MusicBrainz requests and passes in CI. | Network guard test and CI output |
| AC-011 | E2 canonical tables and the read API contract remain unchanged. | Schema/API diff and regression tests |
| AC-012 | A cold 42-band run and a cache-only replay meet the documented time targets. | Run report and command output |

## 10. Assumptions and open questions

### Assumptions

- MusicBrainz API v2 remains available under the documented access terms.
- The 42-band seed list and its MBIDs are correct and stable.
- E2 canonical data remains fixture-based until E4 normalization replaces it.
- Raw data may live outside Git under `data/`; only small synthetic fixtures are committed for tests.
- `httpx` is used for the client; asynchronous concurrency may be used only where it does not violate the request limit.
- E3 writes raw/extracted data and may extend provenance schema, but does not populate canonical catalog tables.
- Full live ingestion is a manual/batch validation step; CI uses mocked or recorded payloads.

### Open questions

| Question | Blocking? | Owner | Resolution |
|---|---|---|---|
| Should recording-level relationships be fetched for every unique recording across all fetched releases, or only for a representative release per album? | No | Cristian | Resolved: fetch every unique recording MBID across fetched releases once, deduplicate and record coverage. |
| Should raw payloads live in `data/raw/` with PostgreSQL references, in PostgreSQL JSONB, or both? | No | Cristian/architecture | Resolved by plan: immutable files under `data/raw/musicbrainz/` plus `raw_response` metadata in PostgreSQL. |
| Which release set is authoritative for release-level credits: all releases, official releases only, or the earliest official release? | No | Cristian | Resolved: fetch all releases, preserve status and edition context, and retain all documented release-level credits. |
| Is the extracted dataset stored as JSON/NDJSON files, PostgreSQL tables, or both? | No | Cristian | Resolved by plan: versioned NDJSON files plus manifest; E4 imports them into canonical tables. |
| Should E3 fetch Wikidata QIDs through MusicBrainz URL relationships only, or also call Wikidata directly? | No | Cristian | Resolved: MusicBrainz URL relationships only; direct Wikidata access belongs to a later source extension. |
| Are extended roles (engineer, mix, mastering) part of the required E3 extraction or only producer/co-producer? | No | Cristian | Resolved: extract all documented production relationships and preserve raw roles; filtering belongs to API/analysis. |
| What are the exact retry counts, backoff values and timeout limits? | No | Cristian | Resolved by plan: bounded exponential backoff with jitter, at most three attempts per request. |
| Is a legal/licensing review required before storing supplementary MusicBrainz data, or should E3 restrict itself to core data? | No | Cristian | Resolved: preserve license per response and defer public display policy to E12. |

## 11. Validation result

- **Date:** 2026-11-07
- **Verdict:** Validated.
- **Evidence:** `tasks.md` T-001–T-012 evidence, the validation table, the full 42-band run, cache-only replay, canonical/API regression checks, the local test suite and GitHub Actions run 42396996612 (success) for commit `c6cd92f`.

## 12. Corpus v0.2 note

This specification records E3 as implemented for the historical 42-band, 1980–2000 corpus. [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md) changes the target corpus to 1960–2026 with album-level taxonomy, versioned seed-list batches and non-destructive history.

The implemented E3 dataset remains historical and must not be rewritten. The corpus-v0.2 ingestion will use a new seed-list version, a new dataset version and the taxonomy version defined in [`data/taxonomy.json`](../../data/taxonomy.json). E4 owns album-level classification, band aggregates, confidence handling and dataset membership.

## 13. References

- [Constitution](../../constitution.md)
- [AGENTS.md](../../AGENTS.md)
- [Scope](../../docs/00-vision/scope.md)
- [Roadmap — E3](../../docs/00-vision/roadmap.md)
- [Architecture overview](../../docs/01-architecture/overview.md)
- [Data model v0](../../docs/01-architecture/data-model.md)
- [Source evaluation](../../docs/03-data/sources.md)
- [MusicBrainz spike report](../../docs/03-data/spike-report.md)
- [Seed list](../../data/seed-list.json)
- [ADR-0002 — MusicBrainz as primary source](../../docs/01-architecture/adr/ADR-0002-musicbrainz-primary-source.md)
- [ADR-0005 — Identity and provenance](../../docs/01-architecture/adr/ADR-0005-identity-and-provenance.md)
- [ADR-0007 — Credit scope](../../docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md)
- [SPEC-002 — Seed band explorer](../002-seed-band-explorer/spec.md)
