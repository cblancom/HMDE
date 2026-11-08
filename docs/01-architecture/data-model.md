# Data model v0

- **Status:** Draft; E2/E3 physical schemas consolidated; E4 normalization implemented locally
- **Version:** 0.2
- **Date:** 2026-11-06
- **Stage:** E0

This document is a conceptual model, not a physical schema. The DDL is defined with Alembic migrations in E2. Its purpose is to fix vocabulary, relationships and provenance decisions before implementation.

## 1. Principles

- Separate **professional relationships** from any notion of affinity or preference.
- Model the credit as a relationship with a role, source and confidence, not as an album attribute.
- Use MBID as the canonical key for MusicBrainz-derived entities.
- Preserve external identifiers without assuming that two records are the same entity.
- Distinguish date, precision and absence.
- Do not delete conflicting data: preserve and flag it.
- Version ingestions, datasets and analytical runs.

## 2. Main entities

| Entity | Purpose | Canonical key | Origin |
|---|---|---|---|
| `artist` | Person or group that performs or produces | Internal `artist_id`; unique `mbid` when available | MusicBrainz |
| `artist_alias` | Alternative names | `alias_id` | MusicBrainz |
| `release_group` | Canonical album | `release_group_id`; `mbid` | MusicBrainz |
| `release` | Concrete edition of an album | `release_id`; `mbid` | MusicBrainz |
| `recording` | Recorded track or performance | `recording_id`; `mbid` | MusicBrainz |
| `credit` | Artist–recording/release/album relationship with a role | `credit_id` | MusicBrainz and future sources |
| `role` | Controlled vocabulary of functions | `role_id` / `code` | HMDE |
| `place` | Studio or recording place | `place_id`; `mbid` | MusicBrainz |
| `genre_tag` | Original source tag or genre | `tag_id` | MusicBrainz |
| `artist_genre_tag` | Original tag associated with an artist | Composite key | MusicBrainz |
| `release_group_genre_tag` | Original tag associated with an album | Composite key | MusicBrainz |
| `subgenre` | Curated taxonomy node with optional parent | `code` | HMDE |
| `artist_subgenre` | Derived artist–subgenre aggregate with confidence | Composite key | HMDE |
| `release_group_subgenre` | Album–subgenre classification; one primary and multiple secondary leaves | Composite key | HMDE |
| `dataset_membership` | Active/retired band membership for a dataset version | Composite key | HMDE |
| `external_id` | Identifier of an entity in another source | `external_id_id` | Multiple |
| `source_record` | Raw record and its provenance | `source_record_id` | Multiple |
| `ingest_run` | Ingestion run | `ingest_run_id` | HMDE |

A `release_group` is considered a **canonical album** only if it has primary type `album` and no secondary type (`live`, `compilation`, `demo`, `remix`, `soundtrack`, etc.). The full rule is in [ADR-0004](adr/ADR-0004-release-group-model.md).

## 3. Relationships

| Relationship | Cardinality | Notes |
|---|---|---|
| Artist – album | N:M via `credit` | An artist may have multiple roles on an album |
| Artist – edition | N:M via `credit` | The credit may be anchored to the edition |
| Artist – recording | N:M via `credit` | The credit may be anchored to a recording |
| Album – edition | 1:N | A release-group groups several releases |
| Album – recording | 1:N | Recordings belong to releases and therefore to an album |
| Album – subgenre | N:M | Curated mapping from tags |
| Album – studio | N:M via credit or place relationship | Subject to coverage |
| Entity – external identifier | 1:N | MBID, QID, Discogs ID, etc. |
| Credit – source | N:1 | Every credit must have provenance |
| Run – raw record | 1:N | Allows an ingestion to be reproduced |

## 4. Credit model

A credit must answer: **who**, **on what**, **in what role**, **according to which source**, **with what confidence** and **at which scope**.

Conceptual attributes:

- `artist_id`: person or group.
- `credit_scope`: `release_group`, `release` or `recording`.
- `release_group_id`: canonical album context.
- `release_id`: edition where the credit appears, when applicable.
- `recording_id`: recording where the credit appears, when applicable.
- `role_id`: normalized role.
- `role_raw`: original role text from the source.
- `role_attributes`: source attributes such as `co`, `executive`, `assistant` or `additional`.
- `source_record_id`: provenance.
- `confidence`: explicit and justifiable value.
- `status`: confirmed, inferred, conflicting or quarantined.
- `credited_as`: name as it appears in the source, if different.
- `attributes`: instrument, studio, notes or other relationship attributes.

Rules:

- The same artist may have multiple credits on the same album with different roles.
- Two sources may provide the same credit; both provenances are preserved or consolidated with traceability.
- A credit from a later edition is not presented as if it belonged to the original album without indicating the edition.
- A recording-level credit applies to that recording, not automatically to every track.
- Album-level credits are a projection. The projection preserves `supporting_recording_count`, `supporting_recording_ratio` and `aggregation_basis`.
- The MVP default includes any credit with at least one supporting recording or release, but analyses can filter by full-album support.
- The absence of a credit does not create a negative record.

MusicBrainz stores `co-producer`, `executive producer`, `assistant producer` and `additional producer` as attributes of the `producer` relationship rather than as separate relationship types. The mapping is recorded in [ADR-0007](adr/ADR-0007-credit-scope-and-recording-level-aggregation.md).

## 5. Identity and deduplication

- `mbid` is unique for MusicBrainz entities.
- `external_id` links a canonical entity to a QID, Discogs ID or other identifier.
- Aliases alone do not create new entities.
- Matching is deterministic: MBID, QID or another exact identifier.
- There is no automatic fuzzy merging in the MVP.
- Ambiguities go to quarantine or a manual review queue.
- A merge must leave an audit trail: absorbed entity, resulting entity, reason and date.

The policy is recorded in [ADR-0005](adr/ADR-0005-identity-and-provenance.md). See the [E2 ER diagram](er-diagram.md) for physical relationships and delete rules.

## 6. Provenance

`source_record` must preserve at minimum:

- Source (`musicbrainz`, `wikidata`, `wikipedia`, etc.).
- Entity type and MBID/external ID.
- Consulted URL.
- Retrieval date and time.
- Payload hash.
- Raw payload location.
- Response code and status.
- License applicable to the record.
- Source API or schema version.
- `ingest_run_id`.

`ingest_run` records parameters, start, end, counters, errors and code version.

## 7. Time

Every relevant date must include precision:

| Field | Example | Precision |
|---|---|---|
| `date_start` | 1986-01-01 | Year |
| `date_end` | 1986-12-31 | Year |
| `date_precision` | `year`, `month`, `day`, `unknown` | — |

Rules:

- The canonical album date is the first release of the `release-group`.
- The edition date is stored separately.
- Decade analyses use the canonical album date and report how many records have sufficient precision.
- Missing dates are not imputed without marking the imputation.

## 8. Subgenres and taxonomy

- The taxonomy is a manually curated, versioned hierarchy in `data/taxonomy.json`.
- Parent nodes are families for grouping and filters; only leaf nodes may be assigned to albums.
- Each canonical album has exactly one primary leaf and zero or more secondary leaves.
- Original MusicBrainz tags are stored; curated mappings connect tags to taxonomy leaves.
- A band may have multiple subgenres across its albums.
- The band-level primary subgenre is derived from album primary labels; ties are resolved by an audited manual classification.
- Album and band classifications carry `confidence`, `status`, `mapping_rule`, `source_record_id` and `taxonomy_version`.
- Filtering by a parent taxonomy node includes descendant leaves by default; exact matching is an explicit option.
- Analyses must declare the taxonomy version and whether they use the band aggregate, album primary or all album labels.

Confidence policy:

| Level | Score | Action |
|---|---:|---|
| Low | `< 0.50` | Manual review required |
| Medium | `0.50–0.79` | Alert and review queue; non-blocking |
| High | `>= 0.80` | Accepted automatically |

Manual classifications have confidence `1.0` and an audit trail.

Historical preservation:

- `dataset_membership` records which bands are active in each dataset version.
- Retiring a band removes it from the active listing/search but preserves its rows, raw data, dataset membership history and analyses.
- A taxonomy or corpus change creates a new taxonomy/seed-list/dataset version; it does not silently rewrite historical classifications or analysis results.

## 9. Analytical layer

Results are not recomputed on every request. They are persisted in versioned tables:

| Conceptual table | Content |
|---|---|
| `analysis_run` | Dataset, parameters, code version, date and status |
| `graph_node` | Snapshot nodes with type and metrics |
| `graph_edge` | Snapshot edges with type and weight |
| `node_metric` | Centrality, degree and other metrics per run |
| `community` | Detected communities and parameters |
| `community_membership` | Node membership in communities |
| `producer_metric` | Participation and concentration aggregates |
| `temporal_metric` | Aggregates by decade or period |

Every analytical row must reference an `analysis_run`. A result without an identifiable run is not valid. Each analysis run must also record its source `dataset_version` and `taxonomy_version`.

## 10. Open questions for E2

- What threshold of `supporting_recording_ratio` defines a full-album credit for each analysis?
- How are duplicate credits across editions and recordings aggregated without losing information?
- How are group artists that act as producers modeled?
- How are studios represented when MusicBrainz uses `place` with different types?
- Which extended roles are visible in the first version?
- How are albums with multiple artists or several lead artists handled?
- What should be done with bands that changed names and share members?
- How is a conflict between sources recorded without blocking visualization?
- What confidence threshold allows an inferred credit to be shown?
- How are low-confidence release-groups (mislabeled demos, singles, splits) quarantined or reviewed?
- What snapshot granularity is adopted for the analytical layer?

These questions are resolved in E2 with spike evidence and reflected in migrations and in the ingestion and normalization specs.
