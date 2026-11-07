# E2 Entity-Relationship Diagram

- **Status:** Current
- **Date:** 2026-11-06
- **Stage:** E2
- **Schema:** Alembic `0003` (`credit` target FKs use `RESTRICT`)

This diagram shows the physical E2 catalog schema. It includes only real foreign-key relationships. `alembic_version` is omitted because Alembic owns it.

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

## Related documents

- [Data model v0](data-model.md)
- [ADR-0004 — Release-group model](adr/ADR-0004-release-group-model.md)
- [ADR-0005 — Identity and provenance](adr/ADR-0005-identity-and-provenance.md)
- [ADR-0007 — Credit scope](adr/ADR-0007-credit-scope-and-recording-level-aggregation.md)
- [E2 plan](../../specs/002-seed-band-explorer/plan.md)
