# MVP scope

- **Status:** Approved; seed list v0.1.0 completed in E0
- **Version:** 0.1
- **Date:** 2026-11-04
- **Stage:** E0

## 1. MVP definition

The MVP is an **explorer of professional production relationships in heavy metal between 1980 and 2000**, built from public data, with source traceability and network visualization.

The MVP does not aim to cover the entire scene. It aims to demonstrate that the architecture, data model and pipeline can answer real questions with a bounded and documented dataset.

## 2. Growth horizon

| Phase | Bands | Goal |
|---|---:|---|
| MVP | 42 | Validate the full flow and data quality |
| v1 | 200–500 | Analyze patterns with reasonable statistical power |
| Long term | Thousands | Broad coverage, subject to sources and licenses |

The architecture must support growth without structural changes. Expansion happens in batches of the seed list, with idempotent ingestions and versioned datasets.

## 3. Unit of analysis

- **Canonical album:** MusicBrainz `release-group` with primary type `album`, excluding all secondary types: `audio drama`, `audiobook`, `compilation`, `demo`, `dj-mix`, `field recording`, `interview`, `live`, `mixtape/street`, `remix`, `soundtrack` and `spokenword`.
- **Edition:** MusicBrainz `release`. Credits may be captured at release-group, edition or recording level and aggregated to the canonical album with provenance. Credit scope is defined in [ADR-0007](../01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md).
- **Album date:** first release date of the `release-group`. It is included if it falls within 1980–2000.
- **Credits from later editions:** retained if they add information, but tagged with the edition date. Analyses must be able to filter by edition, recording or canonical album.
- **Recording-level credits:** retained on their source recording and projected to the album with supporting-recording counts and ratios; a credit on one track is not assumed to apply to the whole album.

This decision is recorded in [ADR-0004](../01-architecture/adr/ADR-0004-release-group-model.md) and is validated in E0/E2.

## 4. Period

- From 1980-01-01 to 2000-12-31, based on the first release date of the canonical album.
- Available precision is preserved: day, month, year or unknown.
- Albums without a usable date are excluded from temporal analyses but may be retained with a quality flag.
- Reissues are not excluded if they document credits from the original album; their date and provenance are recorded.

## 5. Subgenres

Initial curated taxonomy, provisional until E0 validation:

1. Heavy Metal
2. Thrash Metal
3. Death Metal
4. Black Metal
5. Power Metal
6. Doom Metal
7. Progressive Metal

A residual `other` category is added for bands that do not fit the list, and `unclassified` for data without sufficient evidence. These are analytical categories, not objective labels.

MusicBrainz uses collaborative and noisy genres and tags. Original tags are stored and a curated mapping table maps them to the taxonomy above. A band may have more than one subgenre; analyses must support multi-label assignment and document the assignment rule.

## 6. Included entities

| Entity | Description | MVP core |
|---|---|---|
| Artist | Person or group participating in production or performance | Yes |
| Band / group | Artist of type group | Yes |
| Canonical album | `release-group` of type album | Yes |
| Edition | Concrete `release` | Yes, for provenance |
| Recording | Recorded track that may carry credits | Yes, for credit scope |
| Credit | Relationship between an artist and a recording/edition/album with a role | Yes |
| Role | Producer, co-producer, engineer, mix, mastering, etc. | Yes |
| Studio | Recording or mixing place when documented | Yes, with limited coverage |
| Subgenre | Curated label derived from tags | Yes |
| Source | Origin record and conditions | Yes |
| External ID | MBID, QID and others | Yes |

## 7. Credit roles

Three levels are distinguished:

| Level | Roles | MVP use |
|---|---|---|
| Core | `producer`, `co-producer` | Primary network and metrics analysis |
| Extended | `executive producer`, `engineer`, `mix`, `mastering` | Stored and visible; secondary analyses |
| Other | arrangements, programming, design, etc. | Out of MVP unless part of the same credit |

The absence of a role is not interpreted as absence of participation. Every credit preserves the source's original role and its mapping to the controlled vocabulary.

MusicBrainz represents `co-producer`, `executive producer`, `assistant producer` and `additional producer` as attributes of the `producer` relationship, not as separate types. The mapping is defined in [ADR-0007](../01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md).

## 8. Sources

| Source | Use | Decision |
|---|---|---|
| MusicBrainz | Entities, MBID, release-groups, releases and relationships | Primary source |
| Wikidata | External identifiers and links between entities | Complementary identifier source |
| Wikipedia | Historical context and credits when MusicBrainz is insufficient | Complementary, subject to CC BY-SA |
| Discogs | Additional credits | Deferred; does not meet the historical snapshot requirement |
| Encyclopaedia Metallum | Metal-specific data | Excluded until review and permission |

The detailed evaluation and terms are in [03-data/sources.md](../03-data/sources.md).

## 9. Seed list

The seed list is a versioned artifact produced in E0. It must satisfy:

### Inclusion criteria

1. Artist primarily associated with one of the in-scope subgenres.
2. At least one studio album with first release between 1980 and 2000.
3. Stable and verifiable MusicBrainz identifier (MBID).
4. Presence in at least one published source documenting relevance; the list is not based on personal preference.
5. Deliberate distribution by subgenre, decade and country, not an arbitrary ranking.

### Exclusion criteria

- Bands without a studio album in the period.
- Projects with only demos, live releases or compilations.
- Artists not associated with heavy metal or its subgenres.
- Duplicate or unresolvable entities.
- Bands with insufficient data to identify the canonical album.

### Size and composition

- MVP: 42 bands. See the [seed list](../03-data/seed-list.md).
- v1: 200–500 bands.
- The list, selection source, date and MBID are documented.
- The list can grow in batches; ingestion history is not rewritten.

Bands are not required to have documented production credits. Excluding them would introduce bias. Coverage is measured and reported.

## 10. In scope for the MVP

- MusicBrainz ingestion for the seed list.
- Normalization of artists, albums, editions, credits, roles and subgenres.
- Provenance, confidence and quarantine.
- Quality and coverage report.
- Exploratory analysis and descriptive metrics.
- Graph construction and precomputed network metrics.
- Read-only API with entities, search, filters and subgraphs.
- Exploration and visualization frontend.
- Tests, CI and documentation.
- Reproducible v0.1 deployment.

## 11. Out of scope for the MVP

- Audio analysis and acoustic similarity.
- Listener preferences, ratings and plays.
- User accounts, writes and contributions.
- Complete coverage of worldwide discography.
- Bands outside the period or without a studio album.
- Discogs and Metallum integration.
- Automatic fuzzy deduplication.
- Scheduled incremental updates.
- Kubernetes, Kafka, Redis, Celery, Neo4j.
- Mobile application and internationalization.

## 12. Assumptions

- MusicBrainz contains enough production credits for a significant subset of the sample. The E0 spike found 86.4% producer/co-producer coverage across 206 album candidates.
- MBID is stable and serves as the canonical key for MusicBrainz-derived entities.
- MusicBrainz genre tags are useful as a signal, not as truth.
- The MVP volume does not require distributed processing.
- The project is public and read-only in its first version.
- Attribution and licenses can be satisfied with a credits page and per-record metadata.

## 13. Pending decisions

- Acceptable coverage thresholds for considering the dataset useful.
- Handling of bands with multiple lineups and aliases.
- Support threshold for treating a recording-level credit as a full-album credit.
- Minimum studio coverage for including studios in analyses.
- Dataset update and versioning policy.
- Final terms for using Wikipedia as a complementary source.

## 14. Change control

A change to the period, seed list, subgenre taxonomy, core roles or sources requires:

1. Updating this document.
2. Recording the decision in an ADR if it affects architecture or the model.
3. Adjusting affected specs.
4. Re-running ingestion and analyses if the dataset changes.

Scope is not expanded for convenience during implementation. It is documented and approved first.
