# Tasks — SPEC-005 Normalization, identity and provenance

- **Status:** Validated
- **Spec:** [spec.md](spec.md)
- **Plan:** [plan.md](plan.md)

## 1. Execution order

```text
T-001 ──► T-002 ──► T-003 ──► T-004 ──► T-005 ──► T-006
                                      └──► T-009 ──► T-010 ──► T-011 ──► T-012
T-006 ──► T-007 ──► T-008 ───────────────────────────────────────────────►
```

T-001 is the first gate and T-002 requires it. T-003 requires T-002. T-004 requires T-002 and T-003. T-009 requires T-005. T-011 is the first full-corpus validation point.

## 2. Tasks

### T-001 — Define normalization rules and versioned classification inputs

- **Requirements:** FR-007, BR-003, BR-006, BR-007.
- **Dependencies:** Plan/tasks approved.
- **Status:** Completed (2026-11-08).
- **Description:** Create `docs/03-data/normalization-rules.md`, `data/classifications/tag-map-v0.1.0.json` and `data/classifications/manual-overrides-v0.1.0.json`. Define exact label matching, confidence/priority scoring, album override schema and reviewer/date fields. The tag map must cover the exact MusicBrainz labels needed by the 57-band corpus and target only assignable taxonomy leaves. The initial override file may be empty but must validate.
- **Done when:** rules document the identity, provenance, credit, taxonomy, classification, aggregate, review and missing-data policies; the tag map has unique normalized labels, valid leaves, confidence in `[0,1]` and integer priorities; the override schema validates.
- **Verification:**
  ```bash
  python3 - <<'PY'
  import json
  from pathlib import Path
  taxonomy = json.loads(Path('data/taxonomy.json').read_text())
  leaves = {n['code'] for n in taxonomy['nodes'] if n['assignable']}
  tag_map = json.loads(Path('data/classifications/tag-map-v0.1.0.json').read_text())
  overrides = json.loads(Path('data/classifications/manual-overrides-v0.1.0.json').read_text())
  assert tag_map['taxonomy_version'] == overrides['taxonomy_version'] == taxonomy['version']
  labels = [rule['source_label'] for rule in tag_map['rules']]
  assert len(labels) == len(set(labels))
  assert all(rule['target_code'] in leaves for rule in tag_map['rules'])
  assert all(0 <= rule['confidence'] <= 1 for rule in tag_map['rules'])
  assert all(isinstance(rule['priority'], int) for rule in tag_map['rules'])
  assert overrides['overrides'] == []
  print('classification inputs OK')
  PY
  ```
- **Files:** `docs/03-data/normalization-rules.md`, `data/classifications/tag-map-v0.1.0.json`, `data/classifications/manual-overrides-v0.1.0.json`, `data/README.md`.
- **Evidence:** 2026-11-08: rules document created; tag map validates against all 17 assignable leaves. It started with 43 rules and was expanded to 48 during T-011 to cover tuning labels; the manual override schema is valid and now contains reviewed exceptions. Verification script passed.

### T-002 — Add the E4 schema, models and migration

- **Requirements:** FR-002, FR-005, FR-006, FR-012, NFR-005.
- **Dependencies:** T-001.
- **Status:** Completed (2026-11-08).
- **Description:** Add SQLAlchemy models and Alembic migration `0005_normalization_layer` for `normalization_run`, `normalization_issue`, `normalization_issue_action`, `taxonomy_version`, `taxonomy_node`, `release_group_subgenre`, `artist_subgenre_classification` and `dataset_membership`. Extend `source_record` with E3 provenance columns, make `fixture_version` nullable, extend `artist_subgenre` with current taxonomy/status/mapping metadata, and seed the `assistant-producer` role if missing. Add constraints, indexes and reversible downgrade.
- **Done when:** migration upgrades from empty and from `0004`, downgrades cleanly, existing fixture rows remain readable, and the one-primary constraints are enforceable.
- **Verification:**
  ```bash
  cd backend
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run alembic upgrade head
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run alembic downgrade 0004
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run alembic upgrade head
  uv run pytest tests/unit/test_normalization_models.py tests/integration/test_normalization_migration.py
  ```
- **Files:** `backend/alembic/versions/0005_normalization_layer.py`, `backend/src/hmde/models/normalization.py`, `backend/src/hmde/models/artist.py`, `backend/src/hmde/models/credit.py`, `backend/src/hmde/models/subgenre.py`, `backend/src/hmde/models/__init__.py`, tests.
- **Evidence:** 2026-11-08: migration `0005` upgraded the development and test databases; `0005 → 0004 → 0005` round trip passed. New model/migration tests passed (11), and the full PostgreSQL-backed suite passed (168). `assistant-producer` is seeded as controlled role reference data; the E2 fixture role-count assertion was relaxed to permit additive controlled vocabulary while preserving fixture counts for all other entities.

### T-003 — Implement taxonomy version persistence and projection sync

- **Status:** Completed (2026-11-08).
- **Requirements:** FR-006, BR-003, BR-009.
- **Dependencies:** T-002.
- **Description:** Add a normalization taxonomy loader that validates `data/taxonomy.json`, computes a source hash, creates an immutable `taxonomy_version`, persists `taxonomy_node` rows and refreshes the current `subgenre` projection. Reject duplicate codes, missing parents, cycles, non-assignable leaves and version/hash drift.
- **Done when:** taxonomy v0.2.0 syncs idempotently; the existing `subgenre` read path keeps returning valid names; a changed taxonomy cannot overwrite an existing used version; invalid hierarchies fail before writes.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_normalization_taxonomy.py tests/integration/test_normalization_taxonomy.py
  ```
- **Files:** `backend/src/hmde/normalization/taxonomy.py`, `backend/tests/unit/test_normalization_taxonomy.py`, `backend/tests/integration/test_normalization_taxonomy.py`.
- **Evidence:** 2026-11-08: taxonomy v0.2.0 syncs 23 nodes and 17 leaves idempotently, sets a single current version, refreshes the `subgenre` projection and rejects content drift for an existing version. Unit and PostgreSQL integration tests passed (8).

### T-004 — Validate E3 input and create the normalization-run skeleton

- **Status:** Completed (2026-11-08).
- **Requirements:** FR-001, FR-002, NFR-001, NFR-002.
- **Dependencies:** T-002, T-003.
- **Description:** Build input validation for the E3 manifest, checksums, dataset/seed-list/taxonomy versions, period, NDJSON schema and classification files. Create the `normalization_run` lifecycle with counters, input hashes and dry-run mode that validates without writing canonical data.
- **Done when:** valid v0.2 input is accepted; missing, stale, corrupt and mismatched inputs fail before canonical writes; a dry run creates no canonical rows; run status transitions are correct.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_normalization_inputs.py tests/integration/test_normalization_run.py
  ```
- **Files:** `backend/src/hmde/normalization/inputs.py`, `backend/src/hmde/normalization/pipeline.py`, `backend/tests/unit/test_normalization_inputs.py`, `backend/tests/integration/test_normalization_run.py`, `backend/tests/fixtures/normalization/mini-dataset/`.
- **Evidence:** 2026-11-08: manifest/checksum/schema validation, tag-map and override validation, persisted-run lifecycle and dry-run mode tested. A dry run writes run metadata only and no canonical rows; missing taxonomy is rejected. Input/run tests passed (7).

### T-005 — Normalize canonical entities and provenance

- **Status:** Completed (2026-11-08).
- **Requirements:** FR-003, FR-004, FR-005, NFR-001.
- **Dependencies:** T-004.
- **Description:** Load artists, release groups, releases, recordings, release–recording links and external IDs. Reuse existing rows by MBID, generate deterministic UUID5 IDs for new rows, create/reuse source records from E3 `raw_response` rows, and link every canonical row to provenance. Keep E2 fixture rows intact.
- **Done when:** the 57-band corpus loads with counts reconciling to the manifest; duplicate MBIDs and missing raw responses quarantine/fail explicitly; rerunning creates no duplicate canonical rows; no canonical row lacks provenance.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/integration/test_normalization_entities.py
  ```
- **Files:** `backend/src/hmde/normalization/ids.py`, `provenance.py`, `entities.py`, `backend/tests/integration/test_normalization_entities.py`.
- **Evidence:** 2026-11-08: deterministic UUID5 IDs, source-record creation from E3 raw responses, canonical artist/group/release/recording/link/external-ID loading, recording-to-album mapping and MBID upserts are implemented. Idempotent replay and missing-provenance failure tests passed (3).

### T-006 — Normalize credits, roles and recording context

- **Status:** Completed (2026-11-08).
- **Requirements:** FR-011, BR-001, BR-002, BR-008.
- **Dependencies:** T-005.
- **Description:** Normalize E3 credits, map roles and producer attributes per ADR-0007, preserve scope/targets/attributes/credited_as/source provenance, resolve recording-scope credits to release-group contexts through release–recording links, and quarantine unmapped roles or missing contexts.
- **Done when:** all E3 credits are accounted for; recording context expansion is reported; role/attribute mapping is deterministic; no unmatched credit is silently dropped.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_normalization_credits.py tests/integration/test_normalization_credits.py
  ```
- **Files:** `backend/src/hmde/normalization/credits.py`, `backend/tests/unit/test_normalization_credits.py`, `backend/tests/integration/test_normalization_credits.py`.
- **Evidence:** 2026-11-08: credits preserve scope, attributes and provenance; recording credits resolve to album contexts; producer qualifiers map per ADR-0007; credited artists absent from the seed band file are created as minimal canonical stubs; idempotent replay passed. Unit/integration tests passed (4).

### T-007 — Implement hybrid album classification

- **Requirements:** FR-007, FR-008, FR-010, BR-003, BR-004, BR-006, BR-007.
- **Dependencies:** T-003, T-005, T-006.
- **Description:** Implement exact tag/genre matching, confidence/priority scoring, primary/secondary selection, manual override precedence and review/quarantine issues. Persist `release_group_subgenre` rows with taxonomy version, evidence, mapping rule and provenance. Enforce one primary leaf per album and version.
- **Done when:** clear albums classify automatically; medium/low/unmapped/tie cases create issues; overrides apply with confidence `1.0`; every accepted album has one primary leaf and leaf-only secondaries; parent nodes are rejected.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_normalization_classification.py tests/integration/test_normalization_classification.py
  ```
- **Files:** `backend/src/hmde/normalization/classification.py`, `issues.py`, `backend/tests/integration/test_normalization_classification.py`.
- **Evidence:** 2026-11-08: exact-label scoring, high/medium/low handling, tie/conflict issues, override precedence, taxonomy-version classification rows and one-primary constraints are implemented. Classification tests passed (5).

### T-008 — Derive band aggregates and maintain review audit

- **Requirements:** FR-009, FR-010, BR-005, BR-010.
- **Dependencies:** T-007.
- **Description:** Derive band primary aggregates from album primary labels, apply the approved seed-list leaf for ties/fallbacks, persist versioned aggregate history and refresh the current `artist_subgenre` projection. Create review issues for empty/tie cases and record issue actions.
- **Done when:** all active bands have an aggregate or an explicit blocking issue; unique plurality, tie, fallback and override cases are deterministic; historical aggregates are retained per taxonomy version; current `artist_subgenre` remains readable.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_normalization_aggregates.py tests/integration/test_normalization_aggregates.py
  ```
- **Files:** `backend/src/hmde/normalization/aggregates.py`, `issues.py`, `backend/tests/unit/test_normalization_aggregates.py`, `backend/tests/integration/test_normalization_aggregates.py`.
- **Evidence:** 2026-11-08: majority, review, tie, fallback and missing aggregate cases produce versioned history and refresh the current `artist_subgenre` projection. Aggregate and review-issue tests passed (7).

### T-009 — Record dataset membership and lifecycle

- **Requirements:** FR-012, BR-010.
- **Dependencies:** T-005.
- **Description:** Load v0.2 dataset membership from the seed list: 42 base bands from `v0.1.0`, 15 from `v0.2.0-batch-01`, all active. Preserve replacement/retirement fields for future versions without deleting canonical rows.
- **Done when:** membership contains exactly 57 active bands with correct batch IDs; replay is idempotent; historical membership and fixture data remain readable.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_normalization_membership.py tests/integration/test_normalization_membership.py
  ```
- **Files:** `backend/src/hmde/normalization/seed.py`, `backend/src/hmde/normalization/membership.py`, `backend/tests/integration/test_normalization_membership.py`.
- **Evidence:** 2026-11-08: a local seed-membership loader keeps normalization independent of the ETL package; active membership rows are keyed by dataset and artist, preserve seed-list version, batch, lifecycle and provenance, and reject seed bands without canonical artists. Membership tests passed (2).

### T-010 — Add the CLI, reports and dry-run/rebuild modes

- **Requirements:** FR-013, FR-002, NFR-008.
- **Dependencies:** T-009.
- **Description:** Add `python -m hmde.normalization` with full run, dry-run, explicit dataset/taxonomy/tag-map/override selection and stable exit codes. Generate JSON and Markdown reports with counts, versions, confidence bands, issue/quarantine reasons, role/scope coverage, runtime and missing-data wording.
- **Done when:** CLI runs from the host, dry-run performs no canonical writes, exit codes distinguish success/completed-with-review/failure, and reports are complete and secret-free.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_normalization_cli.py tests/integration/test_normalization_cli.py
  ```
- **Files:** `backend/src/hmde/normalization/__main__.py`, `cli.py`, `report.py`, `backend/tests/unit/test_normalization_cli.py`, `backend/tests/integration/test_normalization_cli.py`.
- **Evidence:** 2026-11-08: CLI supports full run and dry-run with stable exit codes; the end-to-end mini run writes JSON/Markdown reports, classification, aggregates, membership and issue data. CLI/report tests passed (4); full PostgreSQL-backed suite passed 208 tests; Ruff and format passed.

### T-011 — Run the full v0.2 normalization and curate problem cases

- **Requirements:** FR-001–FR-013, NFR-001–NFR-003.
- **Dependencies:** T-010.
- **Description:** Run the full 57-band v0.2 normalization against PostgreSQL, inspect the report/review queue, curate `manual-overrides-v0.1.0.json` only for problematic albums, rerun until all accepted albums have a primary classification, and verify all active bands have aggregates.
- **Done when:** full counts reconcile with the E3 manifest; every album is accepted or explicitly quarantined; all 57 bands have an aggregate; override decisions are recorded; rerun produces no duplicates; report is reviewed.
- **Verification:**
  ```bash
  cd backend
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run python -m hmde.normalization run \
      --dataset ../data/ingestions/musicbrainz/mb-20261107T194927Z-0d6cedd5c261 \
      --taxonomy ../data/taxonomy.json \
      --tag-map ../data/classifications/tag-map-v0.1.0.json \
      --overrides ../data/classifications/manual-overrides-v0.1.0.json
  ```
- **Files:** runtime database rows, `data/classifications/tag-map-v0.1.0.json`, `data/classifications/manual-overrides-v0.1.0.json`, `data/normalization/`.
- **Evidence:** 2026-11-08: full run `54d66992-643b-49ec-bac4-fe514ea39e94` completed with review in 18.4s. It loaded 57 bands, 731 release groups, 9,236 releases, 16,683 recordings, 112,375 links, 32,665 credit contexts and 57 memberships; 0 credits were quarantined. 690 albums were accepted, 17 are in review, 24 bootleg/live/demo release groups are explicitly quarantined, and all 57 bands have an aggregate (40 accepted, 17 review). 13 manual overrides were applied. Tag-map priority tuning removed 304 primary-classification conflicts. Report: `data/normalization/54d66992-643b-49ec-bac4-fe514ea39e94/report.json`.

### T-012 — Complete tests, scope guards, docs and CI

- **Status:** Completed (2026-11-08).
- **Requirements:** FR-014, FR-015, NFR-004–NFR-010.
- **Dependencies:** T-011.
- **Description:** Complete unit/integration coverage, add scope-guard tests for API/frontend/analysis boundaries, update README/AGENTS/data docs/ER diagram, run full backend checks and remote CI, and update the spec/tasks validation evidence.
- **Done when:** full suite, Ruff, format and OpenAPI drift pass; no frontend or API contract change; CI passes; documentation describes normalization, classification, overrides and review behaviour.
- **Verification:**
  ```bash
  cd backend
  uv run ruff check .
  uv run ruff format --check .
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
  TEST_DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde_test \
    uv run pytest
  cd ..
  docker compose config -q
  ```
- **Files:** `backend/tests/`, `README.md`, `AGENTS.md`, `data/README.md`, `docs/03-data/normalization-rules.md`, `docs/01-architecture/er-diagram.md`, `docs/01-architecture/data-model.md`, `docs/README.md`, `docs/00-vision/roadmap.md`, `specs/README.md`, `specs/005-normalization-identity/`.
- **Evidence:** 2026-11-08: added normalization scope-guard coverage; full PostgreSQL-backed suite passed 210 tests; Ruff check/format passed; OpenAPI drift was absent; `docker compose config -q` passed; README, AGENTS, data docs, roadmap, spec index and ER diagram updated. Remote GitHub Actions CI run [42535752532](https://github.com/cblancom/HMDE/actions/runs/42535752532) passed for commit `683e022`.

## 3. Coverage matrix

### Functional requirements

| Requirement | Tasks |
|---|---|
| FR-001 | T-004, T-011 |
| FR-002 | T-002, T-004, T-010 |
| FR-003 | T-005 |
| FR-004 | T-005 |
| FR-005 | T-002, T-005 |
| FR-006 | T-002, T-003 |
| FR-007 | T-001, T-007 |
| FR-008 | T-007 |
| FR-009 | T-008 |
| FR-010 | T-007, T-008 |
| FR-011 | T-006 |
| FR-012 | T-002, T-009 |
| FR-013 | T-010 |
| FR-014 | T-012 |
| FR-015 | T-012 |

### Non-functional requirements

| Requirement | Tasks |
|---|---|
| NFR-001 | T-004, T-005, T-011 |
| NFR-002 | T-004, T-010, T-011 |
| NFR-003 | T-011 |
| NFR-004 | T-005, T-012 |
| NFR-005 | T-002, T-012 |
| NFR-006 | T-012 |
| NFR-007 | T-001, T-010 |
| NFR-008 | T-010 |
| NFR-009 | T-012 |
| NFR-010 | T-012 |

## 4. Validation evidence

| Criterion | Result | Evidence |
|---|---|---|
| AC-001 | Passed | Migration `0005` upgrade/downgrade and schema tests |
| AC-002 | Passed | Full normalization counts reconcile with E3 manifest |
| AC-003 | Passed | Repeat full runs reused 32,665 credit contexts and created no duplicate entities |
| AC-004 | Passed | MBID identity tests and full run quarantine report |
| AC-005 | Passed | Source-record/provenance tests and full run orphan checks |
| AC-006 | Passed | Taxonomy persistence/projection tests |
| AC-007 | Passed | Classification-input tests |
| AC-008 | Passed | Classification tests |
| AC-009 | Passed | Classification constraints and review tests |
| AC-010 | Passed | Aggregate tests |
| AC-011 | Passed | Membership tests |
| AC-012 | Passed | Credit tests |
| AC-013 | Passed | CLI/report tests |
| AC-014 | Passed | OpenAPI drift, scope guards and canonical contract tests |
| AC-015 | Passed | 210 tests, Ruff, format and remote CI run 42535752532 |

## 5. Notes

- T-001 and T-002 are the first gate; no canonical writes begin before both are complete.
- T-011 is the only task that may require owner review of problematic album classifications.
- The seed-list leaf is the audited prior for band aggregate ties and fallbacks; album overrides remain the only new manual classification file.
- No task may change API schemas, frontend behaviour, E3 raw data or historical datasets.
- Do not mark a task complete until its verification has been executed and recorded.
