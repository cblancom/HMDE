# Physical entity-relationship diagram

- **Status:** Current
- **Date:** 2026-11-08
- **Stage:** E2–E4
- **Schema:** Alembic `0006`

This diagram shows the physical catalog and normalization schema. It includes only real foreign-key relationships. `alembic_version` is omitted because Alembic owns it.

## Diagram

```mermaid
erDiagram
    SOURCE_RECORD ||--o{ ARTIST : "provenance"
    SOURCE_RECORD ||--o{ ARTIST_SUBGENRE : "provenance"
    SOURCE_RECORD ||--o{ RELEASE_GROUP : "provenance"
    SOURCE_RECORD ||--o{ RELEASE : "provenance"
    SOURCE_RECORD ||--o{ RECORDING : "provenance"
    SOURCE_RECORD ||--o{ CREDIT : "provenance"

    ARTIST ||--o{ ARTIST_SUBGENRE : "has subgenre"
    SUBGENRE ||--o{ ARTIST_SUBGENRE : "applied to"

    ARTIST ||--o{ RELEASE_GROUP : "performs"
    RELEASE_GROUP ||--o{ RELEASE : "has editions"

    RELEASE ||--o{ RECORDING_RELEASE : "contains"
    RECORDING ||--o{ RECORDING_RELEASE : "appears on"

    ARTIST ||--o{ CREDIT : "credited"
    ROLE ||--o{ CREDIT : "uses role"
    RELEASE_GROUP ||--o{ CREDIT : "album context"
    RELEASE |o--o{ CREDIT : "edition context"
    RECORDING |o--o{ CREDIT : "recording context"

    TAXONOMY_VERSION ||--o{ TAXONOMY_NODE : "contains"
    TAXONOMY_VERSION ||--o{ NORMALIZATION_RUN : "used by"
    NORMALIZATION_RUN ||--o{ NORMALIZATION_ISSUE : "reports"
    NORMALIZATION_ISSUE ||--o{ NORMALIZATION_ISSUE_ACTION : "audits"
    RELEASE_GROUP ||--o{ RELEASE_GROUP_SUBGENRE : "classified as"
    TAXONOMY_NODE ||--o{ RELEASE_GROUP_SUBGENRE : "labels"
    ARTIST ||--o{ ARTIST_SUBGENRE_CLASSIFICATION : "aggregate history"
    TAXONOMY_NODE ||--o{ ARTIST_SUBGENRE_CLASSIFICATION : "labels"
    ARTIST ||--o{ DATASET_MEMBERSHIP : "member of"
    SOURCE_RECORD ||--o{ RELEASE_GROUP_SUBGENRE : "classification provenance"
    SOURCE_RECORD ||--o{ ARTIST_SUBGENRE_CLASSIFICATION : "aggregate provenance"
    SOURCE_RECORD ||--o{ DATASET_MEMBERSHIP : "membership provenance"

    SOURCE_RECORD {
        uuid id PK
        string source
        string source_entity_type
        string external_id
        string source_url
        datetime fetched_at
        string license
        string payload_hash
        string fixture_version
        uuid raw_response_id FK
        int http_status
        string api_version
        string dataset_version
        uuid ingest_run_id FK
    }

    ARTIST {
        uuid id PK
        string mbid UK
        string name
        string type
        string country
        uuid source_record_id FK
    }

    ARTIST_SUBGENRE {
        uuid artist_id PK,FK
        string subgenre_code PK,FK
        boolean is_primary
        float confidence
        uuid source_record_id FK
        string taxonomy_version FK
        string status
        string mapping_rule
        datetime updated_at
    }

    SUBGENRE {
        string code PK
        string name UK
    }

    RELEASE_GROUP {
        uuid id PK
        string mbid UK
        uuid artist_id FK
        string title
        date first_release_date
        string first_release_precision
        string primary_type
        jsonb secondary_types
        uuid source_record_id FK
    }

    RELEASE {
        uuid id PK
        string mbid UK
        uuid release_group_id FK
        string title
        date release_date
        string release_date_precision
        string country
        string status
        uuid source_record_id FK
    }

    RECORDING {
        uuid id PK
        string mbid UK
        string title
        uuid source_record_id FK
    }

    RECORDING_RELEASE {
        uuid id PK
        uuid release_id FK
        uuid recording_id FK
        string disc
        string position
        string track_number
    }

    ROLE {
        string code PK
        string name
        string category
    }

    CREDIT {
        uuid id PK
        uuid artist_id FK
        string role_code FK
        string scope
        uuid release_group_id FK
        uuid release_id FK
        uuid recording_id FK
        uuid source_record_id FK
        float confidence
        string status
    }

    EXTERNAL_ID {
        uuid id PK
        string entity_type
        uuid entity_id
        string source
        string external_id
        string url
    }

    FIXTURE_LOAD {
        uuid id PK
        string version
        string source
        datetime loaded_at
        int band_count
        int album_count
        int credit_count
    }

    TAXONOMY_VERSION {
        string version PK
        string status
        string source_hash
        string source_path
        boolean is_current
        datetime created_at
    }

    TAXONOMY_NODE {
        string taxonomy_version PK,FK
        string code PK
        string name
        string parent_code FK
        boolean assignable
        int display_order
    }

    NORMALIZATION_RUN {
        uuid id PK
        string dataset_version
        string manifest_sha256
        string seed_list_version
        string taxonomy_version FK
        string tag_map_version
        string overrides_version
        string status
        datetime started_at
        datetime finished_at
        string code_version
        jsonb parameters
        jsonb counters
        text report_path
    }

    NORMALIZATION_ISSUE {
        uuid id PK
        string issue_key UK
        uuid normalization_run_id FK
        string entity_type
        string entity_mbid
        string taxonomy_version FK
        string issue_type
        string severity
        string status
        text reason
        jsonb evidence
    }

    NORMALIZATION_ISSUE_ACTION {
        uuid id PK
        uuid issue_id FK
        string action
        string actor
        text source_file
        jsonb previous_value
        jsonb new_value
        datetime created_at
    }

    RELEASE_GROUP_SUBGENRE {
        uuid release_group_id PK,FK
        string taxonomy_version PK,FK
        string subgenre_code PK,FK
        boolean is_primary
        float confidence
        string status
        string mapping_rule
        uuid source_record_id FK
        jsonb evidence
    }

    ARTIST_SUBGENRE_CLASSIFICATION {
        uuid artist_id PK,FK
        string taxonomy_version PK,FK
        string subgenre_code PK,FK
        boolean is_primary
        float confidence
        string status
        string mapping_rule
        uuid source_record_id FK
        jsonb evidence
    }

    DATASET_MEMBERSHIP {
        string dataset_version PK
        uuid artist_id PK,FK
        string seed_list_version
        string batch_id
        string lifecycle
        string added_in_version
        string retired_in_version
        uuid replaced_by_artist_id FK
        uuid source_record_id FK
    }
```

## How to read it

- `||--o{` means one-to-many with the left side required.
- `|o--o{` means the left side is optional for each credit: only release-scoped credits have a release, and only recording-scoped credits have a recording.
- `PK` is a primary key; `UK` is a unique key; `FK` is a foreign key.

## Relationships

| Relationship | Cardinality | Delete rule |
|---|---|---|
| `source_record` → `artist` | 1:N | `RESTRICT` |
| `source_record` → `artist_subgenre` | 1:N | `RESTRICT` |
| `source_record` → `release_group` | 1:N | `RESTRICT` |
| `source_record` → `release` | 1:N | `RESTRICT` |
| `source_record` → `recording` | 1:N | `RESTRICT` |
| `source_record` → `credit` | 1:N | `RESTRICT` |
| `artist` → `artist_subgenre` | 1:N | `CASCADE` |
| `subgenre` → `artist_subgenre` | 1:N | `RESTRICT` |
| `artist` → `release_group` | 1:N | `RESTRICT` |
| `release_group` → `release` | 1:N | `CASCADE` |
| `release` → `recording_release` | 1:N | `CASCADE` |
| `recording` → `recording_release` | 1:N | `CASCADE` |
| `artist` → `credit` | 1:N | `RESTRICT` |
| `role` → `credit` | 1:N | `RESTRICT` |
| `release_group` → `credit` | 1:N | `CASCADE` |
| `release` → `credit` | 1:N, optional | `RESTRICT` |
| `recording` → `credit` | 1:N, optional | `RESTRICT` |

The `credit.release_id` and `credit.recording_id` foreign keys use `RESTRICT` because the credit scope requires a target when the scope is `release` or `recording`. A target cannot be deleted silently while a credit depends on it.

## Tables without foreign-key relationships

| Table | Why it has no FK |
|---|---|
| `external_id` | Polymorphic: `entity_type` + `entity_id` can point to an artist, album, release or recording. Referential integrity is enforced by the loader, not by a single FK. |
| `fixture_load` | Operational metadata for a fixture load; it does not depend on domain rows. |

## Tables with no outgoing foreign keys

These tables are referenced by other tables but do not reference another table themselves:

- `source_record`
- `role`
- `subgenre`

`source_record` is the provenance root. `role` and `subgenre` are controlled vocabularies.

## Credit scope rules

The `credit` table supports three scopes:

| Scope | Required target | Forbidden target |
|---|---|---|
| `release_group` | `release_group_id` | `release_id`, `recording_id` |
| `release` | `release_id` and `release_group_id` | `recording_id` |
| `recording` | `recording_id` and `release_group_id` | — |

`release_group_id` is always present so every credit can be aggregated at album level. Recording-scoped credits are aggregated later with supporting-recording counts and ratios.

## E4 additions (migration `0005`)

- `taxonomy_version` and `taxonomy_node` preserve versioned taxonomy history; `subgenre` remains the current projection used by E2 read paths.
- `release_group_subgenre` stores versioned album classifications with one primary and optional secondary leaves.
- `artist_subgenre_classification` stores versioned band aggregate history; `artist_subgenre` remains the current projection.
- `dataset_membership` records active/retired membership per dataset.
- `normalization_run`, `normalization_issue` and `normalization_issue_action` record run lifecycle, review queue and audit actions.
- `source_record` gained optional E3 raw-response provenance fields; `recording_release` gained `track_number`.
- These additions do not rewrite historical E2/E3 data.

## E5 quality additions (migration `0006`)

- `quality_rule_catalogue` and `quality_rule` persist versioned quality rule metadata.
- `quality_run` records the selected normalization run, versions, status and counters.
- `quality_finding` records rule results and observations.
- `quality_exception` stores approved rule/entity exceptions with reason, approver and date.
- `quality_metric` stores completeness/coverage numerators, denominators and missing counts.
- Quality tables are read/write only to the quality batch; canonical and normalization tables are untouched.

## Related documents

- [Data model v0](data-model.md)
- [ADR-0004 — Release-group model](adr/ADR-0004-release-group-model.md)
- [ADR-0005 — Identity and provenance](adr/ADR-0005-identity-and-provenance.md)
- [ADR-0007 — Credit scope](adr/ADR-0007-credit-scope-and-recording-level-aggregation.md)
- [ADR-0008 — Taxonomy and corpus versioning](adr/ADR-0008-taxonomy-corpus-and-versioning.md)
- [E2 plan](../../specs/002-seed-band-explorer/plan.md)
