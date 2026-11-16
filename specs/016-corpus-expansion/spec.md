# SPEC-016 — Corpus expansion to 200 bands

- **Status:** Draft
- **Stage:** E13
- **Iteration:** v0.3.0
- **Module:** `ingestion` (primary), with downstream `normalization`, `quality`, `analytics`, `api` and `web` verification
- **Date:** 2026-11-16
- **Depends on:** SPEC-014 remote CI run `43895517746`; seed list v0.2.0; taxonomy v0.2.0; E12 paused by owner
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0002](../../docs/01-architecture/adr/ADR-0002-musicbrainz-primary-source.md), [ADR-0004](../../docs/01-architecture/adr/ADR-0004-release-group-model.md), [ADR-0005](../../docs/01-architecture/adr/ADR-0005-identity-and-provenance.md), [ADR-0007](../../docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md), [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)
- **Plan:** [plan.md](plan.md)
- **Tasks:** [tasks.md](tasks.md)
- **Conventions:** [Engineering conventions](../../docs/01-architecture/conventions.md)
- **Owner:** Cristian

## Revision history

| Revision | Date | Change |
|---|---|---|
| 1 | 2026-11-16 | Initial draft: 200-band v0.3.0 expansion, 397-band candidate pool, target distribution and downstream validation |

## 1. Context and problem

E11 is implemented and remote CI run `43895517746` passed. E12 (production deployment and v0.1 release) is paused by the owner. The project continues locally with the corpus-growth stage E13.

The active v0.2.0 corpus has 57 bands, 731 release groups, 9,236 releases, 16,683 recordings and roughly 32.3k credits. The taxonomy v0.2.0 has 17 assignable leaves. Four leaves (`nwobhm`, `stoner-metal`, `sludge-metal`, `djent`) have no active band, and the geographic distribution is heavily concentrated in the United States (23) and the United Kingdom (11). The global graph already reaches 968 album-view nodes at 57 bands under a 1,000-node cap.

E13 must expand the corpus to 200 active bands without changing the architecture. A later revision may extend the same process to 500 bands. This spec covers the first 200-band target only.

The candidate pool for this spec is [`data/seed-lists/candidates/v0.3.0-pool.json`](../../data/seed-lists/candidates/v0.3.0-pool.json). It contains 397 MusicBrainz-identified candidates across all 17 leaves and six regions. Inclusion in the pool is not approval. The owner approves the final 143 additions.

## 2. Users and actors

- **Owner/curator:** approves the target distribution, the 143-band selection and the quality exception baseline.
- **Data operator/developer:** verifies candidates, runs E3–E7, reviews coverage and records evidence.
- **System actors:** MusicBrainz supplies artist and release data; Wikidata/Wikipedia supply published relevance evidence; PostgreSQL and the raw store persist provenance.
- **Future consumers:** API, frontend, analyses and reports consume the v0.3.0 dataset and its versioned membership.
- **Maintainer/agent:** implements the spec, runs checks and updates documentation.

There are no user accounts, authentication or write API in E13.

## 3. User stories and flows

### US-001 — Select 143 new bands

As the owner, I want a documented, stratified selection of 143 new bands so that the corpus reaches 200 active bands without arbitrary inclusion.

**Expected flow:**

1. The candidate pool is filtered to exclude existing v0.2.0 bands, duplicates and candidates without a stable MBID.
2. Every selected band is verified for country, leaf, at least one studio album in 1960–2026 and at least one published relevance source.
3. The selection meets the approved leaf and regional targets.
4. Accepted and rejected candidates are recorded with reasons.
5. The owner approves the three batch artifacts before ingestion.

### US-002 — Create an append-only v0.3.0 seed list

As a data operator, I want a versioned 200-band seed list so that v0.2.0 remains reproducible.

**Expected flow:**

1. All 57 active v0.2.0 bands remain active and unchanged.
2. The 143 approved bands are appended in three batches.
3. The seed list declares schema 2, version `0.3.0`, taxonomy `0.2.0` and period 1960–2026.
4. The active pointer moves to `v0.3.0`.
5. Historical seed lists and datasets are not modified.

### US-003 — Rebuild the data pipeline for 200 bands

As a data operator, I want to run the existing E3–E7 pipeline so that the expanded corpus has normalized, quality-controlled and analytical results.

**Expected flow:**

1. E3 ingests the 200-band seed list with cache reuse and provenance.
2. E4 normalizes identities, credits, classifications and dataset membership.
3. E5 measures quality and coverage and records approved exceptions.
4. E6 and E7 recompute EDA and producer-network results.
5. Every run records the dataset, seed-list, taxonomy and code versions.

### US-004 — Validate product behaviour at the new volume

As a maintainer, I want measured API and graph behaviour at 200 bands so that the expansion does not silently break the product.

**Expected flow:**

1. The new analysis run is loaded into the local stack.
2. Overview and ego-graph endpoints and routes are measured.
3. The 1,000-node overview cap is reviewed against real node and edge counts.
4. The cap is changed only with measured evidence and a documented exception or acceptance.
5. Existing E2E, accessibility and performance tests remain green or have an explicit exception.

## 4. Functional requirements

### FR-001 — Candidate pool and selection evidence

The expansion must use a versioned candidate pool with at least 300 and at most 400 candidates. Each candidate must record:

- candidate identifier;
- name and MusicBrainz MBID;
- country and region;
- proposed taxonomy leaf;
- MusicBrainz match status;
- active-from year when available;
- source URL;
- relevance status.

The pool must cover all 17 assignable leaves and include candidates from Ibero-America, Spain, Portugal, Japan and Europe, in addition to North America and Oceania.

Selected bands must have:

- a stable, unique MusicBrainz MBID;
- a country and region;
- an assignable taxonomy leaf;
- at least one studio album first released between 1960-01-01 and 2026-12-31;
- at least one published source documenting relevance;
- no duplicate MBID and no overlap with v0.2.0.

**Verification:** JSON schema checks, unique-MBID checks, leaf and region counts, and a reviewed selection report.

### FR-002 — Approved target distribution

The v0.3.0 corpus must contain 200 active bands: the existing 57 plus 143 new bands. The target active distribution is:

| Leaf | Current | Target 200 | New |
|---|---:|---:|---:|
| `heavy-metal` | 9 | 18 | 9 |
| `nwobhm` | 0 | 8 | 8 |
| `hard-rock` | 3 | 12 | 9 |
| `proto-metal` | 1 | 6 | 5 |
| `thrash-metal` | 7 | 22 | 15 |
| `death-metal` | 7 | 22 | 15 |
| `black-metal` | 6 | 18 | 12 |
| `doom-metal` | 6 | 14 | 8 |
| `stoner-metal` | 0 | 10 | 10 |
| `sludge-metal` | 0 | 6 | 6 |
| `power-metal` | 6 | 14 | 8 |
| `progressive-metal` | 7 | 16 | 9 |
| `groove-metal` | 1 | 6 | 5 |
| `metalcore` | 2 | 10 | 8 |
| `deathcore` | 1 | 6 | 5 |
| `djent` | 0 | 6 | 6 |
| `post-metal` | 1 | 6 | 5 |
| **Total** | **57** | **200** | **143** |

The target regional distribution for the 200 active bands is:

| Region | Current | Target 200 | New |
|---|---:|---:|---:|
| Europe (excluding Iberia) | 32 | 110 | 78 |
| North America | 24 | 34 | 10 |
| Latin America | 1 | 31 | 30 |
| Iberia | 0 | 10 | 10 |
| Japan | 0 | 10 | 10 |
| Oceania | 0 | 5 | 5 |
| **Total** | **57** | **200** | **143** |

`Iberia` covers Spain and Portugal; `Latin America` covers the Americas south of the United States. The United States and United Kingdom combined must not exceed 50% of active bands. No taxonomy leaf may exceed 12% of active bands. Regional targets yield to leaf coverage when a region does not contain enough verified candidates.

**Verification:** seed-list distribution assertions and a selection report that explains every deviation.

### FR-003 — Three approved batch artifacts

The 143 additions must be recorded in three batch artifacts of approximately 50, 50 and 43 bands. Each batch artifact must include the exact MBIDs, names, countries, leaves, source URLs, verification dates and selection reasons. The owner approves the batch set before the v0.3.0 seed list is written.

**Verification:** batch count, set difference against v0.2.0, MBID uniqueness and owner approval.

### FR-004 — Append-only seed list v0.3.0

The project must create `data/seed-lists/v0.3.0.json` with:

- `schema_version: 2`;
- `version: "0.3.0"`;
- `taxonomy_version: "0.2.0"`;
- `period_start: "1960-01-01"` and `period_end: "2026-12-31"`;
- `total_bands: 200`;
- three new batch entries;
- all 57 v0.2.0 MBIDs retained as active;
- no duplicate MBIDs, sequences or batch references.

The active pointer `data/seed-list.json` must move to v0.3.0 only after validation. `data/seed-lists/v0.2.0.json` and all earlier files must remain byte-for-byte unchanged.

**Verification:** seed-loader validation, composition test and historical checksum check.

### FR-005 — E3 ingestion for 200 bands

The E3 run must:

- process 200/200 active bands with zero unresolved failures;
- preserve raw responses and request provenance;
- reuse existing cached responses where request keys match;
- produce a new dataset version, manifest, checksums and coverage report;
- record seed-list version, taxonomy version, period and batch IDs;
- reproduce the same dataset version in cache-only mode;
- leave the v0.2.0 dataset unchanged.

**Verification:** ingestion report, manifest checks, cache-only replay and historical dataset checksums.

### FR-006 — E4 normalization and classification

The normalization run must:

- accept seed-list version `0.3.0` and taxonomy `0.2.0`;
- normalize all 200 bands and their related entities;
- create 200 active dataset memberships;
- map or quarantine every raw record;
- maintain deterministic identity resolution with no automatic fuzzy merge;
- review new MusicBrainz tags against the versioned tag map;
- record medium-confidence and quarantine cases;
- produce a reviewed versioned manual-override file when required.

**Verification:** normalization report, orphan checks, membership count, classification coverage and quarantine review.

### FR-007 — E5 quality gate

The quality run must:

- use a versioned rule catalogue and exception baseline for v0.3.0;
- validate membership against the active seed-list band count instead of a hardcoded 57;
- detect all structural defects;
- report completeness and coverage by band, decade, leaf, country, batch and role;
- fail when a blocking finding has no approved exception;
- document known source gaps without treating missing credits as negative evidence.

**Verification:** quality report, exception audit and zero unexcepted blocking findings.

### FR-008 — E6 and E7 analysis

The analysis runs must:

- recompute EDA and the producer–album and producer–band network snapshots;
- persist dataset, seed-list, taxonomy and code versions;
- compare v0.3.0 coverage, concentration and community structure with v0.2.0;
- update the metric catalogue and reports with denominators and limitations.

**Verification:** persisted analysis runs, report metadata and v0.2.0/v0.3.0 comparison.

### FR-009 — API, graph and frontend validation

The API and frontend must be verified against the v0.3.0 analysis run. The review must measure:

- overview band-view and album-view node and edge counts;
- overview endpoint latency;
- `/graph` canvas readiness and view-switch response;
- producer ego-graph behaviour;
- the current 1,000-node cap and 2,000-edge cap.

If the album view exceeds the cap, the implementer must decide between raising the cap to 2,000 nodes, keeping the cap with explicit truncation, or another bounded change. The decision must include measured evidence and update the performance documentation. No UI redesign is included.

**Verification:** performance report, cap-decision record, E2E suite and accessibility checks.

### FR-010 — Reproducibility and provenance

Every new artifact must record its version and source:

- candidate pool version;
- seed-list version;
- batch IDs;
- dataset version;
- taxonomy version;
- tag-map and override versions;
- quality rule and exception versions;
- normalization, quality and analysis run identifiers.

**Verification:** manifest and run metadata inspection.

### FR-011 — Documentation and lifecycle

The change must update:

- `docs/03-data/seed-list.md` with the v0.3.0 composition and limitations;
- `docs/00-vision/roadmap.md` with E13 status and the E12 pause;
- `specs/README.md` with SPEC-016 status and dependency;
- `AGENTS.md` current state;
- `data/README.md` with the candidate-pool location;
- the spec, plan and tasks with evidence.

**Verification:** documentation link check and status review.

### FR-012 — Scope guard

E13 must not:

- deploy to production or resume E12;
- add a new data source, credit model or taxonomy revision;
- delete, rewrite or retire existing bands without a versioned reason;
- add automatic fuzzy identity matching;
- change the API contract in a backwards-incompatible way;
- require a database migration unless implementation evidence proves it necessary.

**Verification:** diff review, migration history and scope checklist.

## 5. Non-functional requirements

### NFR-001 — Reproducibility

The same seed list, taxonomy, tag map, overrides, raw cache and code version must reproduce the same dataset, normalization, quality and analysis outputs.

### NFR-002 — Source compliance

MusicBrainz requests must keep the project User-Agent, one-request-per-second limit, retry and `Retry-After` handling. Wikidata and Wikipedia evidence must come from their public APIs or documented dumps; no source whose terms prohibit access may be scraped.

### NFR-003 — Batch performance

The E3–E7 pipeline must complete within a documented local batch window. The plan budget is one working session per major stage; actual durations and storage are recorded.

### NFR-004 — Storage

The expanded raw cache and extracted datasets must fit the local development disk. The expected raw volume is 2–3 GB for 200 bands; actual size is recorded.

### NFR-005 — Product performance

Existing E11 performance targets remain the baseline. Any graph-cap change must be measured on the reference environment and documented with p50/p95 values.

### NFR-006 — Compatibility

Python 3.13, PostgreSQL 16, uv, Docker Compose, Node 20, React and the current test stacks remain supported. No new production dependency is expected.

### NFR-007 — Maintainability

The implementation must reuse the existing seed loader, ingestion, normalization, quality and analysis modules. New code is limited to data-driven guards, tests and documentation.

## 6. Business rules

- **BR-001:** The v0.3.0 target is 200 active bands. The 500-band target is deferred to a later spec.
- **BR-002:** The 57 v0.2.0 active bands remain active and unchanged.
- **BR-003:** Taxonomy v0.2.0 is fixed for this spec; all 17 assignable leaves must have at least one active band.
- **BR-004:** A band without a stable MBID, a studio album in 1960–2026 and a published relevance source is rejected.
- **BR-005:** The United States and United Kingdom combined must not exceed 50% of active bands.
- **BR-006:** No taxonomy leaf may exceed 12% of active bands.
- **BR-007:** Missing production credits are not negative evidence; coverage is reported with denominators.
- **BR-008:** No identity is merged automatically without deterministic evidence.
- **BR-009:** Historical seed lists, datasets and analyses are never rewritten.
- **BR-010:** A quality blocking finding is closed only by a fix or an approved exception.

## 7. Edge cases and errors

- **Ambiguous MusicBrainz match:** reject the candidate or resolve it manually by MBID; do not guess.
- **Missing country:** require a documented country before selection; do not infer silently.
- **No studio album in the period:** reject the candidate.
- **Duplicate MBID or existing band:** reject the candidate.
- **Retired band:** use lifecycle `retired` and `replaced_by_mbid`; never delete.
- **Interrupted ingestion:** rerun with cache; do not publish a partial dataset.
- **Cache miss in cache-only mode:** fail the affected band and report it.
- **New tag without mapping:** quarantine or add a reviewed tag-map rule; do not invent a leaf.
- **Medium-confidence classification:** record a review exception.
- **Graph cap exceeded:** document truncation or raise the cap with measured evidence.
- **Regional quota conflict:** preserve leaf coverage and document the redistribution.

## 8. Out of scope

- Expanding directly to 500 bands.
- Production deployment, TLS, reverse proxy and E12 runbooks.
- New sources, new credit scopes or a taxonomy revision.
- A UI redesign or new graph layouts.
- Automatic fuzzy identity resolution.
- Database migrations not required by measured evidence.
- Remote CI push without explicit authorization.

## 9. Acceptance criteria

| ID | Criterion | Evidence |
|---|---|---|
| AC-001 | The candidate pool has 300–400 candidates, all 17 leaves and the required regional coverage. | Pool JSON assertions and counts |
| AC-002 | 143 new bands are selected and approved; 200 active bands; no duplicates; target leaf and regional distributions met. | Batch artifacts, selection report and owner approval |
| AC-003 | `data/seed-lists/v0.3.0.json` validates; v0.2.0 is byte-for-byte unchanged; the pointer resolves v0.3.0. | Seed-loader tests and checksum check |
| AC-004 | E3 processes 200/200 bands with zero failures; the dataset is reproducible cache-only; the v0.2.0 dataset is unchanged. | Ingestion report, replay and checksums |
| AC-005 | E4 creates 200 active memberships, maps or quarantines every raw record and reviews classifications. | Normalization report and tests |
| AC-006 | E5 has no unexcepted blocking findings and records approved v0.3.0 exceptions. | Quality report and exception audit |
| AC-007 | E6 and E7 produce versioned reports and a v0.2.0/v0.3.0 comparison. | Analysis runs and reports |
| AC-008 | API and graph performance is measured at 200 bands and the cap decision is documented. | Performance report and cap record |
| AC-009 | Backend and frontend tests, lint, typecheck, build, E2E and accessibility checks pass. | Command outputs |
| AC-010 | Documentation, spec index, roadmap and `AGENTS.md` reflect v0.3.0 and the E12 pause. | Documentation review |
| AC-011 | No production deployment, no E12 work, no new production dependency and no unnecessary migration occur. | Diff and migration review |

## 10. Assumptions and open questions

### Assumptions

- The first target is 200 active bands; 500 remains a later growth step.
- Taxonomy v0.2.0 and the 17 leaves are fixed.
- MusicBrainz remains the data source; Wikidata/Wikipedia provide published relevance evidence.
- E12 remains paused; E13 depends on E11 evidence.
- The candidate pool is pre-selection data, not an approved corpus.

### Open questions

| Question | Blocking? | Owner | Resolution |
|---|---|---|---|
| Does the owner approve the 200-band target and the target distribution? | No | Cristian | Recorded by T-001 before selection |
| Does the owner approve the exact 143-band selection? | No | Cristian | Recorded by T-002 before seed-list creation |
| Should the overview cap move to 2,000 nodes? | No | Cristian | Resolved by T-009 with measured evidence |

## 11. Validation result

- **Date:** —
- **Verdict:** Not validated
- **Evidence:** `tasks.md` validation table

## 12. References

- [Roadmap](../../docs/00-vision/roadmap.md)
- [Scope](../../docs/00-vision/scope.md)
- [Seed list](../../docs/03-data/seed-list.md)
- [Sources](../../docs/03-data/sources.md)
- [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)
- [Candidate pool](../../data/seed-lists/candidates/v0.3.0-pool.json)
- [Candidate pool guide](../../data/seed-lists/candidates/README.md)
- [SPEC-004 corpus v0.2](../004-corpus-v0-2/spec.md)
- [SPEC-014 integration QA](../014-integration-qa/spec.md)
