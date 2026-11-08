# Technical plan — SPEC-005 Normalization, identity and provenance

- **Status:** Approved
- **Spec:** [spec.md](spec.md)
- **Tasks:** [tasks.md](tasks.md)
- **Stage:** E4
- **Module:** `normalization`
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0002](../../docs/01-architecture/adr/ADR-0002-musicbrainz-primary-source.md), [ADR-0004](../../docs/01-architecture/adr/ADR-0004-release-group-model.md), [ADR-0005](../../docs/01-architecture/adr/ADR-0005-identity-and-provenance.md), [ADR-0007](../../docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md), [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)

## 1. Solution summary

SPEC-005 adds a dedicated normalization batch path from the validated E3 v0.2 dataset into the canonical PostgreSQL model. The path is idempotent, provenance-preserving and version-aware for taxonomy and dataset membership.

The implementation adds five capabilities:

1. **Canonical load:** artists, release groups, releases, recordings, release–recording links, external IDs and credits are loaded by MBID.
2. **Provenance:** every normalized row links to a source record built from the E3 raw-response row used by the ingested dataset.
3. **Versioned taxonomy:** taxonomy versions and nodes are persisted; current projections keep existing read paths valid.
4. **Hybrid classification:** exact tag/genre mappings classify clear albums; manual overrides handle problematic cases; confidence and review status are stored.
5. **Membership and audit:** dataset membership records the 42 + 15 active bands, and normalization runs/issues/actions are auditable.

The implementation explicitly does not add dependencies, call MusicBrainz during normalization, alter E3 raw data, change public API schemas or build a review UI.

```text
E3 manifest + NDJSON
        │  validate checksums and metadata
        ▼
input validation ──► normalization_run
        │
        ├── source records from raw_response
        ├── canonical entities and links
        ├── credits with scope and role mapping
        ├── taxonomy version + current projection
        ├── album classifications + band aggregates
        ├── dataset membership
        ├── issues / review queue / quarantine
        └── JSON + Markdown report
```

## 2. Architecture and data flow

### 2.1 Execution flow

1. Load and validate the E3 dataset manifest and its referenced files.
2. Load and validate the taxonomy version, tag-map file and manual override file.
3. Create a `normalization_run` row with input hashes and versions.
4. Resolve or create canonical entities by MBID and deterministic UUIDs.
5. Create or reuse source records linked to E3 raw responses.
6. Normalize credits, including recording-to-album context.
7. Persist taxonomy versions/nodes and refresh current projections.
8. Classify albums from exact tag/genre mappings and overrides.
9. Derive band aggregates and create review/quarantine issues.
10. Write dataset membership.
11. Complete the run and write the report.

### 2.2 Package layout

```text
backend/src/hmde/normalization/
├── __init__.py
├── __main__.py          CLI entry point
├── cli.py               arguments, exit codes, orchestration
├── ids.py               deterministic UUID helpers
├── inputs.py            dataset, taxonomy, tag-map and override validation
├── provenance.py        raw_response → source_record mapping
├── entities.py          artists, albums, releases, recordings, links, external IDs
├── credits.py           role/scope normalization and recording context
├── taxonomy.py          versioned taxonomy persistence and projection sync
├── classification.py    tag-map and override classification
├── aggregates.py        band aggregates
├── membership.py        dataset membership and lifecycle
├── issues.py            review queue, quarantine and audit actions
├── report.py            JSON/Markdown report generation
└── pipeline.py          end-to-end run and transaction boundaries
```

The package depends on `core`, `db`, `models` and E3 dataset files. It does not import API, frontend or analytics modules.

## 3. Components and responsibilities

| Component or path | Responsibility |
|---|---|
| `backend/src/hmde/normalization/` | New batch normalization package and CLI. |
| `backend/src/hmde/models/normalization.py` | SQLAlchemy models for runs, issues, taxonomy versions/nodes, classifications and membership. |
| `backend/src/hmde/models/credit.py` | Add nullable provenance fields to `source_record`; keep existing fixture provenance. |
| `backend/src/hmde/models/subgenre.py` | Extend current projections and add historical classification model if kept separate. |
| `backend/alembic/versions/0005_normalization_layer.py` | Additive migration for E4 structures, constraints, indexes and role seed data. |
| `data/classifications/tag-map-v0.1.0.json` | Versioned exact tag/genre-to-leaf mapping. |
| `data/classifications/manual-overrides-v0.1.0.json` | Versioned album primary/secondary overrides with reviewer/date/reason. |
| `docs/03-data/normalization-rules.md` | Human-readable normalization, role, classification, aggregate and review rules. |
| `backend/tests/unit/test_normalization_*.py` | Unit tests for IDs, inputs, classification, credits, aggregates and membership. |
| `backend/tests/integration/test_normalization_*.py` | Migration, replay, provenance, taxonomy and API-boundary tests. |
| `README.md`, `AGENTS.md`, `docs/03-data/seed-list.md`, `docs/01-architecture/er-diagram.md` | Operational commands, current state and physical schema updates. |

## 4. Technical decisions and alternatives

### 4.1 Deterministic identifiers and existing rows

- Existing canonical rows are reused by MBID.
- New row IDs use UUID5 with a fixed HMDE namespace and a stable natural key such as `artist:<mbid>`, `release-group:<mbid>`, `release:<mbid>`, `recording:<mbid>` and `credit:<canonical-credit-key>`.
- Source records use UUID5 from the E3 `raw_response_id`.
- The E2 fixture rows are not deleted; normalization upserts by MBID and keeps unrelated fixture rows.
- Ordering is deterministic in tests and report counts.

Alternative rejected: using the raw MBID as the primary key. It collides conceptually across entity types and loses the existing E2 ID convention.

### 4.2 Provenance model

- Extend `source_record` with nullable `raw_response_id`, `http_status`, `api_version`, `dataset_version` and `ingest_run_id`; make `fixture_version` nullable.
- Every source record created from E3 points to exactly one `raw_response` row.
- Canonical entities, credits, classifications and aggregates reference a `source_record`.
- Missing raw-response rows are fatal before canonical writes because provenance is mandatory.
- Existing E2 fixture source records keep their current values and remain queryable.

Alternative rejected: storing provenance only in JSONB. It weakens relational integrity and makes orphan checks harder.

### 4.3 Versioned taxonomy and current projections

New structures:

- `taxonomy_version`: version, status, source hash, created timestamp, current flag, notes.
- `taxonomy_node`: composite `(taxonomy_version, code)`, name, parent code, assignable, display order.

Rules:

- A taxonomy version is immutable once referenced by a completed normalization run.
- Parent references are self-FKs to the same version; cycles are rejected before persistence.
- Only assignable leaves can be used in album or band classifications.
- The existing `subgenre` table remains the current projection used by E2 read paths; it is synchronized from the current taxonomy version.
- `artist_subgenre` remains the current band projection. Historical aggregates are stored in a versioned classification table.
- `release_group_subgenre` stores album classifications by taxonomy version.

Alternative rejected: adding a `parent_code` column only to `subgenre`. It cannot preserve historical taxonomy versions or explain old classifications.

### 4.4 Canonical load and idempotency

- Read NDJSON files as a stream. The v0.2 volume is small enough to keep indexes in memory.
- Upsert artists, release groups, releases, recordings, release–recording links and external IDs by deterministically derived natural keys.
- Recompute or replace only rows owned by the normalized dataset; never delete unrelated fixture or historical rows.
- Run the logical phases in transactions that leave a recoverable state if interrupted.
- A repeat run with the same input produces the same row keys and counts; a new `normalization_run` row is the only expected append-only difference.

### 4.5 Recording credit album context

E3 recording-scope credits usually have no release-group context:

- Resolve each recording to all release groups where it appears through `release_recordings.ndjson` and `releases.ndjson`.
- Create one normalized credit context per canonical release group.
- Keep the original recording MBID and source response; preserve release context when a single release is relevant.
- Report the number of credits expanded to multiple album contexts.
- Quarantine credits whose recording cannot be linked to a canonical release group.

Current dataset measurement: 28,792 recording credits expand to 29,154 recording-group contexts; the difference is 362 extra contexts.

Alternative rejected: assigning recording credits to the band's first album. It invents album context and would misattribute guest or split credits.

### 4.6 Role and attribute mapping

- Preserve the original E3 role and attributes in `attributes` and mapping evidence.
- Apply the ADR-0007 producer mapping:
  - `producer` → `producer`
  - `producer` + `co` → `co-producer`
  - `producer` + `executive` → `executive-producer`
  - `producer` + `assistant` → `assistant-producer`
  - `producer` + `additional` → `additional-producer`
- Engineer, mix and mastering remain their existing role codes; qualifiers stay in `attributes`.
- Add `assistant-producer` to the controlled role vocabulary if missing.
- Unrecognized attributes do not create new roles automatically; they stay in `attributes` and can create a review issue when they affect the primary normalized role.
- Raw role/attribute data and the mapping rule are retained.

Alternative rejected: dropping qualifiers. It would lose co-producer and executive-producer distinctions required by the project.

### 4.7 Hybrid album classification

Classification inputs:

- `tag-map-v0.1.0.json` contains exact normalized source labels with a target leaf, confidence and priority.
- `manual-overrides-v0.1.0.json` contains release-group overrides with one primary leaf, zero or more secondary leaves, confidence `1.0`, reason, reviewer and reviewed date.
- Both files reference taxonomy version `0.2.0`.

Scoring:

- Match only exact casefolded labels from release-group `genres` and `tags`.
- For each leaf, use the maximum mapped confidence among matched labels, not a sum.
- Rank candidates by confidence descending, then priority ascending, then leaf code.
- A unique top candidate with confidence `>= 0.80` is high-confidence and accepted automatically.
- A top candidate with confidence `0.50–0.79` is medium and gets a review issue.
- No candidate or a top score below `0.50` gets a low/blocking review issue.
- Equal top confidence and equal priority is a conflict and gets a review issue.
- Secondary leaves are other mapped leaves with confidence `>= 0.50`.
- Manual overrides replace generated primary/secondary values and are audited.

Every accepted album has exactly one primary leaf; unresolved albums remain quarantined until an override exists.

Alternative rejected: sum tag frequencies. MusicBrainz tag counts reflect community usage, not album genre strength, and would bias long-lived albums.

### 4.8 Band aggregates

- Aggregate from album primary classifications over the active period.
- Unique plurality becomes the primary band leaf; confidence is supporting albums / classified albums.
- If the band has no classified albums, use the approved seed-list `seed_subgenre_code` as a fallback with confidence `0.50` and a review issue.
- On a tie, use the approved seed-list leaf when it is among the tied leaves; otherwise fall back to the seed-list leaf with a review issue.
- Manual overrides for album classifications can change a later aggregate; the current projection is rebuilt deterministically.
- Historical band aggregates are retained per taxonomy version.

This uses the approved seed-list classification as the audited manual prior and avoids a second override file for bands.

Alternative rejected: silently picking the alphabetically first tie. It is deterministic but not auditable as a product decision.

### 4.9 Review queue, conflicts and audit

- `normalization_issue` stores issue type, entity type/MBID, severity, reason, evidence JSONB, status and run/taxonomy versions.
- Issue keys are deterministic so a rerun updates or closes the same open issue instead of duplicating it.
- `normalization_issue_action` stores apply/review/resolve/quarantine actions with actor, timestamp and before/after values.
- Manual overrides are file-based; applying a new override version records the action and reason in the run/report.
- There is no review UI in E4; the CLI report and issue tables are the operator interface.

### 4.10 API and frontend compatibility

- No API or frontend code changes.
- OpenAPI must not drift.
- The E2 read services continue to query `artist_subgenre`, `subgenre`, `release_group` and `credit`; those tables remain valid.
- Loading the full corpus may change the data returned by existing E2 endpoints, but not their request/response contract.
- Retired-band visibility and new taxonomy filters remain E8 responsibilities.

## 5. Data model and migrations

### 5.1 New tables

| Table | Purpose | Key constraints |
|---|---|---|
| `normalization_run` | One execution of the E4 batch. | UUID PK; dataset version, manifest hash, input versions and counts; status check. |
| `normalization_issue` | Review, conflict and quarantine queue. | UUID PK; deterministic issue key; run FK; status/severity checks; indexes by status/entity. |
| `normalization_issue_action` | Audit trail for issue decisions. | UUID PK; issue FK; actor, action, timestamps and before/after JSONB. |
| `taxonomy_version` | Version metadata. | Version PK; source hash; current flag with a partial unique index. |
| `taxonomy_node` | Versioned hierarchy. | PK `(taxonomy_version, code)`; self-FK parent; assignable flag. |
| `release_group_subgenre` | Versioned album classification. | PK `(release_group_id, taxonomy_version, subgenre_code)`; one primary per album/version enforced by index and transaction checks. |
| `artist_subgenre_classification` | Versioned band aggregate history. | PK `(artist_id, taxonomy_version, subgenre_code)`; primary/confidence/status/mapping rule. |
| `dataset_membership` | Dataset membership and lifecycle. | PK `(dataset_version, artist_id)`; lifecycle check; batch and replacement fields. |

### 5.2 Extended tables

| Table | Change |
|---|---|
| `source_record` | Add nullable E3 provenance columns and make `fixture_version` nullable. |
| `artist_subgenre` | Add current taxonomy version, status, mapping rule and updated timestamp; keep the existing PK and API path. |
| `role` | Add `assistant-producer` if missing; no deletion. |
| `subgenre` | Keep as current taxonomy projection; synchronize names from the current version. |

### 5.3 Constraints and indexes

- Taxonomy leaves only for classification FKs; parent codes are rejected by loader and database checks where practical.
- One primary album classification per `(release_group_id, taxonomy_version)`.
- One primary band aggregate per `(artist_id, taxonomy_version)`.
- Membership lifecycle in `active`/`retired`.
- Run status in `running`/`completed`/`completed_with_review`/`failed`.
- Issue severity in `info`/`medium`/`high`/`blocking`; issue status in `open`/`review`/`accepted`/`rejected`/`quarantined`.
- Indexes on dataset version, taxonomy version, issue status, entity MBID, release group and artist.

### 5.4 Migration and rollback

- Migration `0005_normalization_layer` is additive except for making `fixture_version` nullable.
- Existing E2 rows and E3 tables are preserved.
- Downgrade removes the new E4 tables/columns and seeded role only where safe; normalized canonical rows are not deleted automatically.
- Upgrade and downgrade must work from an empty database and from the current `0004` schema.
- No table rewrite, data deletion or destructive type change.

## 6. API contract

No changes.

- No new endpoints.
- No request/response schema changes.
- No OpenAPI drift.
- Existing E2 endpoints continue to work against canonical tables.
- No canonical data is merged by name, so API identity semantics remain MBID-based.
- E4 does not expose taxonomy-version or classification fields through HTTP.

## 7. Frontend impact

None.

- No routes, components, filters, generated types or visualizations change.
- The frontend remains scoped to the existing E2 contract.
- Type generation and build must remain unchanged.

## 8. Error handling and consistency

- Invalid manifest, checksum, taxonomy, tag map or override: fail before writing.
- Missing raw-response provenance: fail the affected phase and do not write canonical rows for that input.
- Malformed MBID or duplicate canonical key: quarantine and report.
- Recording credit with no album context: quarantine and report.
- Invalid taxonomy leaf or parent code: reject the input.
- Ambiguous album primary: create a blocking review issue; do not accept a primary.
- Ambiguous band aggregate: use the seed-list prior and create a review issue.
- Interrupted run: leave committed phases and mark the run failed/incomplete; rerun idempotently.
- Dataset conflict: never overwrite a different dataset version or delete historical rows.
- Issue replay: update the deterministic open issue; preserve action history.

## 9. Security and trust boundaries

- Batch process only; no write HTTP surface.
- Dataset, taxonomy and classification paths are repository-relative and validated against directory escape.
- No secrets, credentials or tokens are logged.
- Raw responses are read-only; normalization never edits `data/raw/` or `raw_response`.
- Classification input files and their hashes are recorded in the run.
- Public data remains attributable to MusicBrainz; no new source is introduced.

## 10. Observability

- Structured logs include run ID, phase, dataset version, taxonomy version, batch and aggregate counts, issue counts and errors.
- `normalization_run.counters` records input, written, reused, skipped, quarantined, reviewed and failed counts.
- Report files are written outside Git-tracked source data, under the configured normalization output directory.
- The report includes dataset/taxonomy/classification versions, source manifest hash, runtime, counts by entity and role/scope, confidence bands, review reasons and missing-data wording.
- No raw payloads are printed in logs.

## 11. Testing strategy

| Level | What is tested | Evidence |
|---|---|---|
| Unit | UUID determinism, input schemas, taxonomy validation, tag scoring, overrides, role mapping, recording expansion, aggregates, membership. | `backend/tests/unit/test_normalization_*.py` |
| Integration | Migration upgrade/downgrade; taxonomy sync; canonical load; provenance links; idempotent replay; issues/actions; dataset membership; API/OpenAPI unchanged. | `backend/tests/integration/test_normalization_*.py` |
| Contract | OpenAPI drift, E2 API and fixture tests. | Existing suite and `test_openapi.py` |
| Manual | Full v0.2 run, review queue inspection, overrides curation, rerun and report review. | T-011/T-012 evidence |
| CI | Full backend suite without live network. | GitHub Actions |

Commands:

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
TEST_DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde_test \
  uv run pytest
```

No automated test calls MusicBrainz.

## 12. Deployment and reversibility

- Apply migration `0005` before running normalization.
- No new environment variables are required; dataset/taxonomy/classification paths are CLI arguments with documented defaults.
- A failed normalization leaves historical E2/E3 data and prior canonical rows intact.
- Rollback drops E4 structures but does not delete raw data, E3 datasets or E2 fixture files.
- Re-normalizing from the same dataset after rollback is possible.

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Tag mapping is noisy or too broad | Exact matches only; confidence/priority per rule; medium/low review; manual overrides. |
| Manual review grows too large | High-confidence exact mappings; review only ambiguous/unmapped; report volume before accepting. |
| Recording credits lack album context | Resolve via release–recording links; report expanded contexts; quarantine missing links. |
| Existing E2 rows conflict with E4 rows | Reuse by MBID; no deletes; deterministic upsert; report conflicts. |
| Taxonomy projection drifts | Single taxonomy sync transaction and source hash; version immutability. |
| API behaviour changes unexpectedly | No code/contract changes; OpenAPI and E2 tests; data-volume change documented. |
| Duplicate issues on replay | Deterministic issue keys and action audit. |
| Full run too slow | Streaming input, bulk upserts and indexes; 30-minute target. |
| Historical classifications lost | Append-only versioned tables; current projections rebuildable. |

## 14. Traceability requirements → plan → tasks

| Requirement | Plan section | Tasks |
|---|---|---|
| FR-001 | 2.1, 4.4 | T-004 |
| FR-002 | 4.4, 5, 8, 10 | T-002, T-004, T-010 |
| FR-003 | 4.1, 4.3 | T-005 |
| FR-004 | 4.4, 5 | T-005 |
| FR-005 | 4.2, 5, 8 | T-002, T-005 |
| FR-006 | 4.3, 5 | T-002, T-003 |
| FR-007 | 4.7 | T-001, T-007 |
| FR-008 | 4.7, 8 | T-007 |
| FR-009 | 4.8 | T-008 |
| FR-010 | 4.9 | T-007, T-008 |
| FR-011 | 4.5, 4.6 | T-006 |
| FR-012 | 4.8, 5 | T-002, T-009 |
| FR-013 | 2.1, 10 | T-010 |
| FR-014 | 11 | T-012 |
| FR-015 | 4.10, 6, 7 | T-012 |

## 15. Approval and next step

This plan must be approved together with `tasks.md` before implementation starts. The first task is T-001: define and validate the normalization rules and versioned classification inputs.
