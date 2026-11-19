# SPEC-016 — Corpus expansion to 510 bands

- **Status:** Implemented
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
| 2 | 2026-11-17 | Owner reviewed 64 entries, added 56 candidates and discarded 8 duplicates; pool is 453 bands and the candidate cap is 300–500. Target and selection rules unchanged. |
| 3 | 2026-11-17 | Owner accepted all 453 candidates, approved 3 batches of 151 and the exclusion-and-report policy. Target is now 510 active bands; the 143-band selection is removed. Leaf concentration and graph truncation rules are adjusted. |
| 4 | 2026-11-17 | T-002 verified all 453 candidates: 452 accepted, Hellhammer excluded for having no studio album. The owner approved the report and batches; the verified corpus is 509 active bands in batches of 151/151/150. The 510-band target remains the ceiling. |
| 5 | 2026-11-19 | T-005 processed 509/509 bands with zero failures. The dataset was not accepted: cache-only replay produced a different dataset version because recordings with equal MBID were ordered non-deterministically, and 7 multi-artist release groups produced duplicate entity MBIDs. The owner approved option A: total deterministic ordering, one canonical row per entity MBID, and exclusion of multi-artist release groups with reason `multi_artist_release_group`. |
| 6 | 2026-11-19 | T-005A regenerated the canonical dataset from cache: `mb-20261119T004940Z-9d5e75fdc1b9`, 509/509 bands, zero failures. Normal and cache-only runs produced the same dataset version and manifest; entity files have no duplicate MBIDs; 7 multi-artist release groups are excluded and reported. T-006 is next. |
| 7 | 2026-11-19 | T-006 completed normalization run `ed8e7e12-c181-4041-ba39-42b2bf655453`: 509 active memberships, 4,826 classified albums, 0 quarantined and 900 review cases. Tag map and overrides v0.3.0 add reviewed labels and use a band-seed review fallback for albums without usable tags. T-007 is next. |
| 8 | 2026-11-19 | T-007 completed quality run `288b11ac-9a90-4b4f-bf58-fdd50e1a51ad`: 0 blocking findings, 1,089 medium/advisory findings and 77 metrics. The v0.3.0 exception baseline is intentionally empty. T-008 is next. |
| 9 | 2026-11-19 | T-008 completed E6 report `eda-bd2ef42a54786c67` (927 metrics) and E7 run `net-78a54051ff047f86`: 4,217 producer–album edges, 1,700 producer–band edges and 325 communities. The v0.2 comparison and the shared-table legacy-row limitation are documented. T-009 is next. |
| 10 | 2026-11-19 | T-009 completed the API/browser performance review, E2E and axe checks. The 1,000-node/2,000-edge cap is kept with explicit truncation (albums 1,000/810; bands 1,000/1,125). One view-switch acknowledgement exception is documented: p95 2,373 ms over the 1 s control target, while the full settle remains 2,626 ms within 5 s. T-010 is next. |
| 11 | 2026-11-19 | T-010 completed the local regression: 343 backend tests, 118 frontend tests, lint, typecheck, build, 26 Playwright tests, nine axe scans and the performance probe passed; the existing chunk warning and one view-switch exception are documented. SPEC-016 is implemented locally; T-011 remote CI remains pending explicit authorization. |

## 1. Context and problem

E11 is implemented and remote CI run `43895517746` passed. E12 (production deployment and v0.1 release) is paused by the owner. The project continues locally with the corpus-growth stage E13.

The active v0.2.0 corpus has 57 bands, 731 release groups, 9,236 releases, 16,683 recordings and roughly 32.3k credits. The taxonomy v0.2.0 has 17 assignable leaves. Four leaves (`nwobhm`, `stoner-metal`, `sludge-metal`, `djent`) have no active band, and the geographic distribution is heavily concentrated in the United States (23) and the United Kingdom (11). The global graph already reaches 968 album-view nodes at 57 bands under a 1,000-node cap.

E13 targets up to 510 active bands by accepting all 453 candidates in the pool. The owner approved this scope on 2026-11-17. T-002 verified 452 candidates; Hellhammer was excluded because it has no studio album, so the verified corpus is 509 active bands. The 200-band target and the 143-band selection are superseded; the 500-band step is also superseded.

The candidate pool for this spec is [`data/seed-lists/candidates/v0.3.0-pool.json`](../../data/seed-lists/candidates/v0.3.0-pool.json). It contains 453 MusicBrainz-identified candidates across all 17 leaves and six regions. All 453 are accepted for verification and ingestion. A candidate that cannot be verified is excluded and reported; it is not silently replaced.

T-005 executed the first v0.3.0 ingestion on 2026-11-19: 509/509 bands processed with zero failures. The produced dataset was not accepted. Cache-only replay changed the order of `recordings.ndjson` because records with the same MBID had no deterministic tie-breaker, and seven release groups were associated with more than one active band, which the single-artist release-group model cannot represent. The owner approved excluding those multi-artist release groups and regenerating the dataset deterministically. T-005A produced `mb-20261119T004940Z-9d5e75fdc1b9`: 509/509 bands, zero failures, one canonical row per entity MBID, seven reported multi-artist exclusions and the same dataset version in normal and cache-only runs. T-006 normalized the dataset into 509 active memberships and classified all 4,826 albums using tag map and overrides v0.3.0; 3,926 classifications are accepted, 900 remain in review and none are quarantined. T-007 quality run has 0 blocking findings, 1,089 medium/advisory findings and 77 coverage/completeness metrics; the v0.3.0 exception baseline intentionally records no blocking exception. T-008 produced EDA report `eda-bd2ef42a54786c67` with 927 metrics and network snapshot `net-78a54051ff047f86` with 4,217 producer–album edges, 1,700 producer–band edges and 325 communities; the v0.2 comparison and legacy-row limitation are documented in [`analysis-v0.3.0.md`](../../docs/03-data/analysis-v0.3.0.md). T-009 kept the 1,000-node/2,000-edge cap with explicit truncation and passed E2E/axe; the only exception is the view-switch acknowledgement (p95 2,373 ms over 1 s) while the full settle remains within 5 s.

## 2. Users and actors

- **Owner/curator:** approves the 510-band ceiling, the verification report and the quality exception baseline.
- **Data operator/developer:** verifies candidates, runs E3–E7, reviews coverage and records evidence.
- **System actors:** MusicBrainz supplies artist and release data; Wikidata/Wikipedia supply published relevance evidence; PostgreSQL and the raw store persist provenance.
- **Future consumers:** API, frontend, analyses and reports consume the v0.3.0 dataset and its versioned membership.
- **Maintainer/agent:** implements the spec, runs checks and updates documentation.

There are no user accounts, authentication or write API in E13.

## 3. User stories and flows

### US-001 — Verify and add 453 new bands

As the owner, I want all 453 accepted candidates verified and added so that the corpus reaches up to 510 active bands with documented evidence.

**Expected flow:**

1. The candidate pool is checked to exclude existing v0.2.0 bands, duplicates and candidates without a stable MBID.
2. Every candidate is verified for country, leaf, at least one studio album in 1960–2026 and at least one published relevance source.
3. A candidate that fails verification is excluded and reported with the reason; the remaining candidates are retained.
4. All accepted candidates are recorded in three batch artifacts.
5. The owner approves the verification report and the three batch artifacts before ingestion.

### US-002 — Create an append-only v0.3.0 seed list

As a data operator, I want a versioned 509-band seed list so that v0.2.0 remains reproducible.

**Expected flow:**

1. All 57 active v0.2.0 bands remain active and unchanged.
2. The verified candidates are appended in three batches of 151, 151 and 150 bands.
3. The seed list declares schema 2, version `0.3.0`, taxonomy `0.2.0` and period 1960–2026.
4. The active pointer moves to `v0.3.0`.
5. Historical seed lists and datasets are not modified.

### US-003 — Rebuild the data pipeline for 509 bands

As a data operator, I want to run the existing E3–E7 pipeline so that the expanded corpus has normalized, quality-controlled and analytical results.

**Expected flow:**

1. E3 ingests the 509-band seed list with cache reuse and provenance.
2. E4 normalizes identities, credits, classifications and dataset membership.
3. E5 measures quality and coverage and records approved exceptions.
4. E6 and E7 recompute EDA and producer-network results.
5. Every run records the dataset, seed-list, taxonomy and code versions.

### US-004 — Validate product behaviour at the new volume

As a maintainer, I want measured API and graph behaviour at 509 bands so that the expansion does not silently break the product.

**Expected flow:**

1. The new analysis run is loaded into the local stack.
2. Overview and ego-graph endpoints and routes are measured.
3. The 1,000-node overview cap is reviewed against real node and edge counts.
4. The cap is kept with explicit truncation unless measured evidence supports a bounded raise.
5. Existing E2E, accessibility and performance tests remain green or have an explicit exception.

## 4. Functional requirements

### FR-001 — Candidate pool and selection evidence

The expansion must use a versioned candidate pool with at least 300 and at most 500 candidates. Each candidate must record:

- candidate identifier;
- name and MusicBrainz MBID;
- country and region;
- proposed taxonomy leaf;
- MusicBrainz match status;
- active-from year when available;
- source URL;
- relevance status.

The pool must cover all 17 assignable leaves and include candidates from Ibero-America, Spain, Portugal, Japan and Europe, in addition to North America and Oceania.

All 453 candidates are accepted for verification. A candidate that fails country, leaf, studio-album or published-source verification is excluded and reported with the reason. No candidate is silently replaced or merged.

Accepted bands must have:

- a stable, unique MusicBrainz MBID;
- a country and region;
- an assignable taxonomy leaf;
- at least one studio album first released between 1960-01-01 and 2026-12-31;
- at least one published source documenting relevance;
- no duplicate MBID and no overlap with v0.2.0.

**Verification:** JSON schema checks, unique-MBID checks, leaf and region counts, and a reviewed selection report.

### FR-002 — Verified final distribution

The v0.3.0 corpus must contain 509 active bands: the existing 57 plus the 452 accepted candidates. Hellhammer is excluded because it has no studio album. The verified composition is:

| Leaf | Current | Accepted | Final |
|---|---:|---:|---:|
| `heavy-metal` | 9 | 32 | 41 |
| `nwobhm` | 0 | 20 | 20 |
| `hard-rock` | 3 | 33 | 36 |
| `proto-metal` | 1 | 20 | 21 |
| `thrash-metal` | 7 | 57 | 64 |
| `death-metal` | 7 | 57 | 64 |
| `black-metal` | 6 | 40 | 46 |
| `doom-metal` | 6 | 25 | 31 |
| `stoner-metal` | 0 | 28 | 28 |
| `sludge-metal` | 0 | 15 | 15 |
| `power-metal` | 6 | 41 | 47 |
| `progressive-metal` | 7 | 22 | 29 |
| `groove-metal` | 1 | 14 | 15 |
| `metalcore` | 2 | 15 | 17 |
| `deathcore` | 1 | 10 | 11 |
| `djent` | 0 | 10 | 10 |
| `post-metal` | 1 | 13 | 14 |
| **Total** | **57** | **452** | **509** |

The verified regional composition is:

| Region | Current | Accepted | Final |
|---|---:|---:|---:|
| Europe (excluding Iberia) | 32 | 237 | 269 |
| North America | 24 | 124 | 148 |
| Latin America | 1 | 47 | 48 |
| Iberia | 0 | 18 | 18 |
| Japan | 0 | 13 | 13 |
| Oceania | 0 | 13 | 13 |
| **Total** | **57** | **452** | **509** |

`Iberia` covers Spain and Portugal; `Latin America` covers the Americas south of the United States. The United States and United Kingdom combined are 204 of 509 active bands (40.1%), below the 50% cap. No taxonomy leaf may exceed 13% of active bands; `thrash-metal` and `death-metal` are each 64 of 509 (12.57%) and `black-metal` is 46 of 509 (9.04%). These are final composition checks, not selection targets.

**Verification:** seed-list distribution assertions and the verification report that explains the Hellhammer exclusion.

### FR-003 — Three approved batch artifacts

The 452 accepted additions must be recorded in three batch artifacts of at most 151 bands each (151/151/150). Each batch artifact must include the exact MBIDs, names, countries, leaves, source URLs, verification dates and selection reasons. The owner approves the verification report and batch set before the v0.3.0 seed list is written.

**Verification:** three batches, set difference against v0.2.0, MBID uniqueness, every candidate verified or excluded with a reason, and owner approval.

### FR-004 — Append-only seed list v0.3.0

The project must create `data/seed-lists/v0.3.0.json` with:

- `schema_version: 2`;
- `version: "0.3.0"`;
- `taxonomy_version: "0.2.0"`;
- `period_start: "1960-01-01"` and `period_end: "2026-12-31"`;
- `total_bands: 509`;
- three new batch entries of 151, 151 and 150 bands;
- all 57 v0.2.0 MBIDs retained as active;
- no duplicate MBIDs, sequences or batch references.

The active pointer `data/seed-list.json` must move to v0.3.0 only after validation. `data/seed-lists/v0.2.0.json` and all earlier files must remain byte-for-byte unchanged.

**Verification:** seed-loader validation, composition test and historical checksum check.

### FR-005 — E3 ingestion for 509 bands

The E3 run must:

- process 509/509 active bands with zero unresolved failures;
- preserve raw responses and request provenance;
- reuse existing cached responses where request keys match;
- produce a new dataset version, manifest, checksums and coverage report;
- record seed-list version, taxonomy version, period and batch IDs;
- write one canonical row per artist, release group, release and recording MBID;
- keep evidence files deterministically ordered;
- exclude release groups associated with more than one active band, together with dependent rows that become orphaned, and report them with reason `multi_artist_release_group`;
- distinguish extracted records from canonical dataset rows in the coverage report;
- reproduce the same dataset version, manifest and NDJSON bytes in cache-only mode;
- leave the v0.2.0 dataset unchanged.

**Verification:** ingestion report, manifest checks, entity-uniqueness checks, multi-artist exclusion audit, cache-only replay and historical dataset checksums.

### FR-006 — E4 normalization and classification

The normalization run must:

- accept seed-list version `0.3.0` and taxonomy `0.2.0`;
- normalize all 509 bands and the canonical related entities included by E3;
- create 509 active dataset memberships;
- map or quarantine every record included in the canonical dataset;
- not normalize release groups excluded by E3; their exclusion is recorded in the ingestion report;
- maintain deterministic identity resolution with no automatic fuzzy merge;
- review new MusicBrainz tags against the versioned tag map;
- when no exact album tag mapping exists, use the band seed leaf at confidence `0.50` with review status; quarantine only when no seed leaf is available;
- resolve equal album candidates with the band seed leaf when it is tied, and record the decision for review;
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

At 509 bands the album view is expected to exceed the cap. Keep the 1,000-node/2,000-edge cap with explicit truncation unless measurement proves a bounded raise is safe. Record the returned and total node/edge counts in the performance documentation. No UI redesign is included.

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
- normalization, quality and analysis run identifiers;
- multi-artist release-group exclusions and their reasons.

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

The same seed list, taxonomy, tag map, overrides, raw cache and code version must reproduce the same dataset version, byte-identical NDJSON and manifest, and the same normalization, quality and analysis outputs.

### NFR-002 — Source compliance

MusicBrainz requests must keep the project User-Agent, one-request-per-second limit, retry and `Retry-After` handling. Wikidata and Wikipedia evidence must come from their public APIs or documented dumps; no source whose terms prohibit access may be scraped.

### NFR-003 — Batch performance

The E3–E7 pipeline must complete within a documented local batch window. The plan budget is one working session per major stage; actual durations and storage are recorded.

### NFR-004 — Storage

The expanded raw cache and extracted datasets must fit the local development disk. The expected raw volume is 6–8 GB for 509 bands; actual size is recorded.

### NFR-005 — Product performance

Existing E11 performance targets remain the baseline. Any graph-cap change must be measured on the reference environment and documented with p50/p95 values.

### NFR-006 — Compatibility

Python 3.13, PostgreSQL 16, uv, Docker Compose, Node 20, React and the current test stacks remain supported. No new production dependency is expected.

### NFR-007 — Maintainability

The implementation must reuse the existing seed loader, ingestion, normalization, quality and analysis modules. New code is limited to data-driven guards, tests and documentation.

## 6. Business rules

- **BR-001:** The v0.3.0 ceiling is 510 active bands. Verification accepted 452 of 453 candidates, so the verified corpus is 509 bands: all 57 current bands plus 452 accepted candidates. The 200-band and 500-band targets are superseded.
- **BR-002:** The 57 v0.2.0 active bands remain active and unchanged.
- **BR-003:** Taxonomy v0.2.0 is fixed for this spec; all 17 assignable leaves must have at least one active band.
- **BR-004:** A band without a stable MBID, a studio album in 1960–2026 and a published relevance source is excluded and reported; it is not silently replaced.
- **BR-005:** The United States and United Kingdom combined must not exceed 50% of active bands.
- **BR-006:** No taxonomy leaf may exceed 13% of active bands; `thrash-metal` and `death-metal` are accepted at 12.55% each.
- **BR-007:** Missing production credits are not negative evidence; coverage is reported with denominators.
- **BR-008:** No identity is merged automatically without deterministic evidence.
- **BR-009:** Historical seed lists, datasets and analyses are never rewritten.
- **BR-010:** A quality blocking finding is closed only by a fix or an approved exception.
- **BR-011:** A release group associated with more than one active band is excluded from the canonical E3 dataset with reason `multi_artist_release_group`; it is not attributed to a single band. Dependent rows that become orphaned are excluded consistently and reported. The 509-band corpus is unchanged.

## 7. Edge cases and errors

- **Ambiguous MusicBrainz match:** reject the candidate or resolve it manually by MBID; do not guess.
- **Missing country:** require a documented country before selection; do not infer silently.
- **No studio album in the period:** exclude the candidate and report the reason.
- **Duplicate MBID or existing band:** exclude the candidate and report it.
- **Multi-artist release group:** exclude the group and orphaned dependent rows; report `multi_artist_release_group`; do not assign the album to one artist.
- **Candidate fails verification:** exclude and report it; never silently replace it.
- **Retired band:** use lifecycle `retired` and `replaced_by_mbid`; never delete.
- **Interrupted ingestion:** rerun with cache; do not publish a partial dataset.
- **Cache miss in cache-only mode:** fail the affected band and report it.
- **New tag without mapping:** add a reviewed tag-map rule; if the album still has no usable mapping, use the band seed leaf as a review fallback; do not invent a leaf.
- **Medium-confidence classification:** record a review exception.
- **Graph cap exceeded:** document truncation or raise the cap with measured evidence.
- **Regional quota conflict:** preserve leaf coverage and document the redistribution.

## 8. Out of scope

- Expanding beyond 510 bands.
- Production deployment, TLS, reverse proxy and E12 runbooks.
- New sources, new credit scopes or a taxonomy revision.
- A UI redesign or new graph layouts.
- Automatic fuzzy identity resolution.
- Database migrations not required by measured evidence.
- Remote CI push without explicit authorization.

## 9. Acceptance criteria

| ID | Criterion | Evidence |
|---|---|---|
| AC-001 | The candidate pool has 300–500 candidates, all 17 leaves and the required regional coverage. | Pool JSON assertions and counts |
| AC-002 | All 453 accepted candidates are verified or excluded with a reason; the resulting corpus has up to 510 active bands, no duplicates and the final leaf/regional distribution recorded. | Batch artifacts, verification report and owner approval |
| AC-003 | `data/seed-lists/v0.3.0.json` validates; v0.2.0 is byte-for-byte unchanged; the pointer resolves v0.3.0. | Seed-loader tests and checksum check |
| AC-004 | E3 processes 509/509 bands with zero failures; normal and cache-only runs produce the same dataset version and byte-identical NDJSON/manifest; no canonical entity MBID is duplicated; multi-artist release groups are excluded and reported; the v0.2.0 dataset is unchanged. | Ingestion report, replay, entity-uniqueness checks and checksums |
| AC-005 | E4 creates 509 active memberships, maps or quarantines every record in the canonical dataset and reviews classifications. | Normalization report and tests |
| AC-006 | E5 has no unexcepted blocking findings and records approved v0.3.0 exceptions. | Quality report and exception audit |
| AC-007 | E6 and E7 produce versioned reports and a v0.2.0/v0.3.0 comparison. | Analysis runs and reports |
| AC-008 | API and graph performance is measured at 509 bands and the cap/truncation decision is documented. | Performance report and cap record |
| AC-009 | Backend and frontend tests, lint, typecheck, build, E2E and accessibility checks pass. | Command outputs |
| AC-010 | Documentation, spec index, roadmap and `AGENTS.md` reflect v0.3.0 and the E12 pause. | Documentation review |
| AC-011 | No production deployment, no E12 work, no new production dependency and no unnecessary migration occur. | Diff and migration review |

## 10. Assumptions and open questions

### Assumptions

- The ceiling is 510 active bands; verification yielded 509: all 57 current bands plus 452 accepted candidates.
- All 453 candidates were accepted for verification; failures are excluded and reported, not replaced. Hellhammer is excluded for having no studio album.
- Taxonomy v0.2.0 and the 17 leaves are fixed.
- MusicBrainz remains the data source; Wikidata/Wikipedia, Discogs and AllMusic provide published relevance evidence.
- E12 remains paused; E13 depends on E11 evidence.
- The candidate pool is accepted input, not yet an approved seed list.
- The release-group model supports one artist per album; split or collaborative albums are excluded from the canonical dataset and reported.

### Open questions

| Question | Blocking? | Owner | Resolution |
|---|---|---|---|
| Does the owner approve the 510-band target and all 453 candidates? | No | Cristian | Approved 2026-11-17; recorded by T-001 |
| What happens to candidates that fail verification? | No | Cristian | Excluded and reported; approved 2026-11-17 |
| Does Hellhammer remain despite having no studio album? | No | Cristian | No; excluded 2026-11-17. The verified corpus is 509 bands. |
| How should multi-artist release groups be handled? | No | Cristian | Excluded and reported with reason `multi_artist_release_group`; option A approved 2026-11-19. |
| Should the overview cap move above 1,000 nodes? | No | Cristian | Keep the cap with explicit truncation unless measured evidence supports a bounded raise; resolved by T-009 |

## 11. Validation result

- **Date:** 2026-11-19
- **Verdict:** Implemented locally; remote validation pending T-011 authorization
- **Evidence:** `tasks.md` validation table, `docs/01-architecture/qa-report.md` and `docs/03-data/analysis-v0.3.0.md`

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
