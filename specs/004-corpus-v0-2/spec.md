# SPEC-004 — Corpus v0.2 seed-list expansion

- **Status:** Implemented
- **Stage:** E3
- **Iteration:** MVP
- **Module:** `ingestion`
- **Date:** 2026-11-06
- **Depends on:** SPEC-003 validated; [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md); [taxonomy](../../data/taxonomy.json) v0.2.0; seed list v0.1.0
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0002](../../docs/01-architecture/adr/ADR-0002-musicbrainz-primary-source.md), [ADR-0005](../../docs/01-architecture/adr/ADR-0005-identity-and-provenance.md), [ADR-0007](../../docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md), [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)
- **Plan:** [plan.md](plan.md) (approved)
- **Tasks:** [tasks.md](tasks.md) (implemented locally; remote CI pending)
- **Conventions:** [Engineering conventions](../../docs/01-architecture/conventions.md)
- **Owner:** Cristian

## Revision history

| Revision | Date | Change |
|---|---|---|
| 1 | 2026-11-06 | Initial draft; 15-band corpus v0.2 scope and open questions |
| 2 | 2026-11-06 | Plan and tasks drafted; T-001 batch selection gate defined |
| 3 | 2026-11-06 | Plan/tasks approved; T-001 implemented |
| 4 | 2026-11-06 | T-001–T-008 executed; 57-band dataset and local validation complete; remote CI pending |

## 1. Context and problem

E3 is validated for the historical 42-band, 1980–2000 corpus. ADR-0008 expands the target corpus to 1960–2026, introduces a manually curated hierarchical taxonomy and requires versioned, non-destructive seed-list growth.

The next dataset must retain the 42 active bands, append 15 new bands in a versioned batch, extend album eligibility across 1960–2026 and produce a new E3 raw/extracted dataset. It must not rewrite the validated E3 dataset, replace bands or introduce album-level classification. Album classification and normalization remain E4 responsibilities.

This specification covers the seed-list and ingestion work needed before E4.

## 2. Users and actors

- **Data operator/developer:** curates the 15-band batch, runs the new ingestion and reviews coverage/failures.
- **System actor:** the MusicBrainz API supplies source data; PostgreSQL and the raw store persist execution metadata and payloads.
- **Implementation agent:** works from this spec, the plan, tasks, constitution and ADRs.
- **Future consumers:** E4 normalization, E5 quality and E7 analysis consume the new dataset.

There are no end-user roles, authentication or write API in this spec.

## 3. User stories and flows

### US-001 — Load and validate the expanded seed list

As a data operator, I want a versioned seed list with the original 42 bands plus 15 new bands so that the corpus can grow without losing history.

**Expected flow:**

1. The versioned seed list declares its schema, seed-list version, taxonomy version and period.
2. The original 42 bands remain active.
3. Fifteen new bands are appended in a named batch.
4. Every band has a verified MBID, country, lifecycle state and a leaf `seed_subgenre_code`.
5. The validator accepts the declared version and distribution without hardcoded 42/6 constants.

### US-002 — Rebuild the E3 dataset for 1960–2026

As a data operator, I want to run the existing ingestion pipeline over the expanded period so that the corpus includes albums from 1960–1979 and 2001–2026.

**Expected flow:**

1. The ETL reads the period from the versioned seed list or corpus configuration.
2. Existing raw responses are reused where request keys match.
3. New albums and artists are fetched from MusicBrainz with the existing rate limit and provenance rules.
4. A new dataset and coverage report are written under a new dataset version.
5. The historical E3 1980–2000 dataset remains untouched.

### US-003 — Preserve historical corpus membership

As a data operator, I want the previous 42 bands and dataset to remain available so that historical analyses remain reproducible.

**Expected flow:**

1. The new dataset records its seed-list and taxonomy versions.
2. The 42 original bands remain active in corpus v0.2.
3. No band is deleted.
4. The previous dataset and its manifest remain readable.
5. The report records the expanded decades and new coverage.

## 4. Functional requirements

### FR-001 — Seed-list v0.2.0 schema

The new seed list must be versioned and declare at minimum:

- `schema_version`;
- `version` (v0.2.0);
- `taxonomy_version` (`0.2.0`);
- `period_start` (`1960-01-01`);
- `period_end` (`2026-12-31`);
- batches;
- bands.

Each band must include:

- stable internal identifier when available;
- verified MBID;
- name;
- country;
- `seed_subgenre_code`;
- `batch_id`;
- lifecycle status (`active` or `retired`);
- `replaced_by_mbid` when applicable;
- verification date.

The seed list must be stored in a versioned location; the previous v0.1.0 file must remain available. An active pointer or documented active path must identify the current version.

**Verification:** schema and fixture tests; v0.1.0 remains readable; no destructive rewrite.

### FR-002 — Corpus composition

The expanded seed list must contain:

- the original 42 bands, active;
- 15 new bands, active, in a named batch;
- 57 active bands in total;
- no duplicate MBIDs;
- exact 15 new MBIDs relative to v0.1.0;
- no band removed or silently replaced.

The exact 15-band selection and decade/subgenre distribution must be approved before implementation. The selection must cover the expanded period, especially 1960–1979 and 2001–2026, and use the same source and verification criteria as E0.

**Verification:** manifest counts; set difference between v0.1.0 and v0.2.0 equals the approved 15-band batch.

### FR-003 — Taxonomy validation

- `seed_subgenre_code` must reference an assignable leaf in `data/taxonomy.json` v0.2.0.
- Parent/family nodes must be rejected as seed subgenres.
- The seed list must record the taxonomy version.
- Taxonomy parent relationships must be valid and acyclic.
- Only the approved taxonomy leaves may be used in the batch.

**Verification:** taxonomy validation tests; invalid parent, unknown code and cycle cases fail before ingestion.

### FR-004 — Data-driven seed validation

The E3 validator must remove fixed assumptions about:

- version `0.1.0`;
- exactly 42 bands;
- exactly 6 bands per subgenre.

It must instead validate:

- the declared schema and seed-list version;
- declared period and taxonomy version;
- the declared distribution;
- active/retired lifecycle consistency;
- unique MBIDs and valid sequence values;
- batch membership;
- taxonomy leaf validity.

It must continue to reject malformed, duplicate or unverified bands before writing an `ingest_run`.

**Verification:** unit tests with valid, malformed, duplicate, retired and batch inputs.

### FR-005 — Configurable period

- Album eligibility must use the period declared by the corpus/seed list, not hardcoded 1980/2000 constants.
- Historical E2/E3 1980–2000 datasets remain historical and must not be rewritten.
- The expanded dataset must include canonical albums with first release dates from 1960-01-01 through 2026-12-31.
- Release-group exclusion reasons must remain explicit for not-album, secondary type, missing date and out-of-period cases.

**Verification:** traversal tests with dates before 1980, inside 1980–2000 and after 2000; full-run report.

### FR-006 — Versioned E3 dataset

The new E3 run must write a new dataset with:

- seed-list version v0.2.0;
- taxonomy version v0.2.0;
- declared period;
- dataset version;
- manifest, counts and checksums;
- coverage and failure report.

The dataset must remain an extracted/raw data product; it must not normalize canonical entities or classify albums. E4 owns those steps.

**Verification:** dataset manifest fields; cache-only replay produces the same dataset version; historical dataset remains unchanged.

### FR-007 — Raw reuse and source access

- Existing raw responses must be reused by request key where possible.
- New requests must respect the existing User-Agent, one-request-per-second, retry and `Retry-After` rules.
- Every new response must be stored with provenance.
- The run must be idempotent and resumable.
- The previous raw responses must not be deleted.

**Verification:** idempotency/resume tests; raw response counts; no network in automated tests.

### FR-008 — Coverage by expanded decades

The coverage report must include:

- 1960s, 1970s, 1980s, 1990s, 2000, 2000s, 2010s and 2020s;
- bands, albums, releases and recordings by decade;
- exclusions by reason;
- per-band coverage;
- seed-list and taxonomy versions;
- explicit missing-data wording.

**Verification:** report assertions for the expanded decade labels and metadata.

### FR-009 — Historical preservation

- The validated E3 dataset and its manifest must remain readable.
- The new seed list must not overwrite v0.1.0.
- Band retirement must be represented by lifecycle state, not deletion.
- A new dataset membership must not destroy the previous dataset history.
- No canonical E2 tables are modified by this spec.

**Verification:** checksums/files for the historical dataset; E2 canonical count regression; no destructive migration.

### FR-010 — Tests and CI

Tests must cover:

- seed-list schema and versioning;
- taxonomy leaf validation;
- 42 + 15 composition;
- lifecycle and batch behaviour;
- period boundaries;
- dataset manifest and replay;
- report decades;
- no live network in CI.

**Verification:** full backend suite, Ruff, OpenAPI drift and CI.

### FR-011 — Scope guard

This spec must not include:

- album-level classification in the database;
- confidence scoring for classifications;
- dataset membership implementation in canonical tables;
- API or frontend changes;
- normalization of the new dataset.

Those belong to E4 and later stages.

**Verification:** code inspection and tests; canonical/API contract unchanged.

## 5. Non-functional requirements

### NFR-001 — Reproducibility

The same seed list, raw cache and code version must reproduce the same extracted dataset and manifest checksum.

### NFR-002 — Source compliance

The expanded run must respect MusicBrainz limits and provenance rules. The run must support cache-only reproduction without network access.

### NFR-003 — Performance

The 57-band run must complete within a documented batch window using the existing rate limit and optimized browse strategy. The report records runtime and request counts.

### NFR-004 — Compatibility

Python 3.13, PostgreSQL 16, Docker Compose, uv, pytest and Ruff remain supported. Node is not involved.

### NFR-005 — Security

No secrets, credentials or tokens are committed or logged. The corpus is public and read-only at the API boundary.

### NFR-006 — Language

All code, documentation, reports and error messages are in English.

## 6. Business rules

- **BR-001:** The 42 v0.1.0 bands remain active; 15 new bands are appended.
- **BR-002:** Seed lists are append-only across versions.
- **BR-003:** A band removed from the active corpus is marked retired, not deleted.
- **BR-004:** `seed_subgenre_code` must be an assignable taxonomy leaf.
- **BR-005:** Album-level primary and secondary classification belongs to E4.
- **BR-006:** The historical E3 dataset is immutable.
- **BR-007:** The expanded period is 1960-01-01 to 2026-12-31.
- **BR-008:** No live network calls occur in automated tests.
- **BR-009:** No canonical E2 table is modified by this spec.

## 7. Edge cases and errors

- **Seed-list version mismatch:** fail before writing.
- **Duplicate MBID:** fail before writing.
- **Unknown taxonomy code:** fail validation.
- **Parent taxonomy node used as seed subgenre:** reject.
- **15 new bands do not match approved batch:** fail manifest validation.
- **One of the original 42 bands missing:** fail composition validation.
- **Released album outside 1960–2026:** record exclusion with reason.
- **Cache missing in cache-only mode:** fail the affected band and report it.
- **Partial E3 run:** preserve completed raw responses and report failures.
- **Source 429/5xx/timeout:** use existing retry path.
- **Interrupted run:** preserve prior completed datasets.
- **Taxonomy file invalid:** fail before ingestion.

## 8. Out of scope

- Album-level taxonomy classification.
- Band aggregate classification and confidence.
- Review queues and quality thresholds.
- Canonical normalization and identity resolution.
- API endpoints, frontend UI and graphs.
- Adding the remaining 100+ bands.
- Source expansion beyond MusicBrainz.
- Production deployment.

## 9. Acceptance criteria

| ID | Criterion | Evidence |
|---|---|---|
| AC-001 | Seed list v0.2.0 validates 57 active bands: the original 42 plus 15 new bands. | Seed-list tests and manifest |
| AC-002 | The 15 new MBIDs exactly equal the approved batch and no original MBID is lost. | Set-difference test |
| AC-003 | Every `seed_subgenre_code` is an assignable leaf in taxonomy v0.2.0. | Taxonomy validation tests |
| AC-004 | The validator is data-driven and rejects malformed, duplicate, retired-invalid and parent-node inputs. | Seed validation tests |
| AC-005 | Album eligibility uses 1960–2026 from the seed/corpus configuration. | Period boundary tests |
| AC-006 | A new E3 dataset is written with seed-list, taxonomy, period and dataset versions. | Manifest inspection |
| AC-007 | Cache-only replay reproduces the same dataset version without network access. | Replay test |
| AC-008 | The coverage report includes the expanded decades and versions. | Report assertions |
| AC-009 | The historical E3 dataset remains readable and unchanged. | Checksums and file inspection |
| AC-010 | Full backend suite, Ruff and OpenAPI drift pass locally and in CI. | Test/CI output |
| AC-011 | No canonical E2 table, API contract or frontend changes occur. | Schema/API diff and regression tests |

## 10. Assumptions and open questions

### Assumptions

- ADR-0008 and taxonomy v0.2.0 are approved.
- The 15-band batch will be selected from verified MusicBrainz artists using the same source criteria as E0.
- Existing raw responses and E3 infrastructure are reusable.
- The new spec is executed before E4.
- The historical E2/E3 1980–2000 datasets remain immutable.

### Open questions

| Question | Blocking? | Owner | Resolution |
|---|---|---|---|
| What are the exact 15 new bands and their decade/subgenre/country distribution? | No | Cristian | T-001 selects and records the 15 bands under the approved 3/3/3/3/3 decade distribution. Ingestion cannot start until T-001 and its batch artifact are approved. |
| Should the 15-band batch deliberately cover each expanded decade (1960s, 1970s, 2000s, 2010s, 2020s)? | No | Cristian | Accepted: three new bands from each expanded decade. |
| Which active seed-list path is canonical: versioned directory plus active pointer, or active file with archived versions? | No | Cristian | Accepted: versioned directory plus `data/seed-list.json` active pointer. |
| Do all original 42 bands remain active even if their only albums are outside 1980–2000? | No | Cristian | Accepted: yes; period expansion applies to their full eligible discography. |
| Should the new dataset include a taxonomy version but no album classifications yet? | No | Cristian | Accepted: yes; E4 performs classification. |

## 11. Validation result

- **Date:** 2026-11-06
- **Verdict:** Implemented; local validation passed; remote CI and formal validation pending
- **Evidence:** 157 backend tests passed with PostgreSQL; Ruff check/format and OpenAPI drift checks passed; dataset `mb-20261107T194927Z-0d6cedd5c261` reproduced cache-only; historical dataset checksums unchanged. See `tasks.md`.

## 12. References

- [Constitution](../../constitution.md)
- [AGENTS.md](../../AGENTS.md)
- [Scope](../../docs/00-vision/scope.md)
- [Roadmap](../../docs/00-vision/roadmap.md)
- [Taxonomy](../../data/taxonomy.json)
- [Seed list documentation](../../docs/03-data/seed-list.md)
- [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)
- [SPEC-003](../003-musicbrainz-ingestion/spec.md)
