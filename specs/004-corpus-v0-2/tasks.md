# Tasks — SPEC-004 Corpus v0.2 seed-list expansion

- **Status:** Implemented locally; remote CI pending
- **Spec:** [spec.md](spec.md)
- **Plan:** [plan.md](plan.md)

## 1. Execution order

```text
T-001 ──► T-002 ──► T-003 ──► T-004 ──► T-005 ──► T-006 ──► T-007 ──► T-008
```

T-001 is a mandatory approval gate. No v0.2 ingestion begins until the exact 15-band batch and distribution are approved.

T-002 creates the versioned seed-list files. T-003–T-006 adapt E3 validation, period, report and dataset metadata. T-007 performs the expanded ingestion. T-008 closes tests, CI and documentation.

## 2. Tasks

### T-001 — Curate and approve the 15-band v0.2 batch

- **Requirements:** FR-002, NFR-005.
- **Dependencies:** SPEC-003 validated; ADR-0008 accepted.
- **Status:** Completed (2026-11-06).
- **Description:** select 15 verified MusicBrainz artists: three from the 1960s, three from the 1970s, three from the 2000s, three from the 2010s and three from the 2020s. Record MBID, name, country, leaf `seed_subgenre_code`, source URL, verification date and selection rationale in a batch artifact.
- **Done when:** the batch contains exactly 15 valid, unique MBIDs; the distribution is exactly 3/3/3/3/3 by the five expanded decades; no original 42 band is removed; the owner approves the list.
- **Verification:**
  ```bash
  python3 - <<'PY'
  import json
  from pathlib import Path
  batch = json.loads(Path('data/seed-lists/batches/v0.2.0-batch-01.json').read_text())
  assert len(batch['bands']) == 15
  assert batch['decade_distribution'] == {
      '1960s': 3, '1970s': 3, '2000s': 3, '2010s': 3, '2020s': 3
  }
  print('v0.2 batch OK')
  PY
  ```
- **Files:** `data/seed-lists/batches/v0.2.0-batch-01.json`, `docs/03-data/seed-list.md` (batch rationale).
- **Evidence:** 2026-11-06: approved batch `v0.2.0-batch-01` contains 15 unique verified MBIDs, three per expanded decade (1960s, 1970s, 2000s, 2010s, 2020s). Batch validation passed. The owner approved the list and distribution.

### T-002 — Create the versioned seed-list storage and v0.2.0 input

- **Requirements:** FR-001, FR-002, FR-009, FR-011.
- **Dependencies:** T-001.
- **Status:** Completed (2026-11-06).
- **Description:** archive v0.1.0, create v0.2.0 with the original 42 active bands plus the approved 15-band batch, and introduce an active-version pointer at `data/seed-list.json`. Record schema, taxonomy, period, batch and lifecycle metadata. Keep the v0.1.0 file immutable.
- **Done when:** v0.1.0 remains byte-for-byte available; v0.2.0 validates 57 active bands; the pointer resolves to v0.2.0; no original MBID is lost; no band is duplicated or deleted.
- **Verification:**
  ```bash
  python3 - <<'PY'
  import json
  from pathlib import Path
  pointer = json.loads(Path('data/seed-list.json').read_text())
  assert pointer['active_version'] == '0.2.0'
  seed = json.loads((Path('data') / pointer['path']).read_text())
  assert seed['version'] == '0.2.0'
  assert len(seed['bands']) == 57
  print('seed-list v0.2.0 OK')
  PY
  ```
- **Files:** `data/seed-lists/v0.1.0.json`, `data/seed-lists/v0.2.0.json`, `data/seed-list.json`, `data/seed-lists/batches/v0.2.0-batch-01.json`, `data/README.md`.
- **Evidence:** 2026-11-06: `data/seed-lists/v0.1.0.json` is a byte-for-byte archive of the validated v0.1.0 file. `data/seed-lists/v0.2.0.json` contains 57 active bands with unique MBIDs, schema 2, taxonomy 0.2.0, 1960–2026 period and batch metadata. `data/seed-list.json` resolves to v0.2.0. The set difference is exactly the 15 approved batch MBIDs and all 42 original MBIDs are retained.

### T-003 — Implement taxonomy validation

- **Requirements:** FR-003.
- **Dependencies:** T-002.
- **Status:** Completed (2026-11-06).
- **Description:** add a taxonomy loader/validator for `data/taxonomy.json`: unique codes, valid parent references, acyclic hierarchy, assignable leaves and taxonomy version. Reject parent/family nodes as `seed_subgenre_code`.
- **Done when:** valid taxonomy loads; duplicate codes, missing parents, cycles and non-leaf seed subgenres fail before ingestion.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_taxonomy_validation.py
  ```
- **Files:** `backend/src/hmde/etl/musicbrainz/seed.py`, `backend/tests/unit/test_taxonomy_validation.py`.
- **Evidence:** 2026-11-06: `load_taxonomy` validates the approved 23-node/17-leaf taxonomy. `uv run pytest tests/unit/test_taxonomy_validation.py` passed 6 tests covering the real taxonomy, duplicate codes, missing parents, cycles, assignable parents and non-assignable leaves.

### T-004 — Make seed-list validation data-driven and lifecycle-aware

- **Requirements:** FR-004, FR-007, NFR-002.
- **Dependencies:** T-003.
- **Status:** Completed (2026-11-06).
- **Description:** resolve the active pointer; validate schema/schema version, seed-list version, taxonomy version, period, batches, lifecycle, unique MBIDs, sequence and declared subgenre distribution. Remove hardcoded 42-band and six-per-subgenre assumptions. Preserve subset and maximum-band selection.
- **Done when:** v0.2.0 validates; malformed, duplicate, retired-invalid, parent-node and bad-pointer inputs fail before any `ingest_run`; v0.1.0 still loads.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_seed_validation.py tests/unit/test_seed_v02.py
  ```
- **Files:** `backend/src/hmde/etl/musicbrainz/seed.py`, seed tests.
- **Evidence:** 2026-11-06: active pointer resolves v0.2.0; 57 bands load with taxonomy leaves, batches, period and declared distribution. v0.1.0 still loads. Retired bands are excluded from default selection. `uv run pytest tests/unit/test_seed_validation.py tests/unit/test_seed_v02.py tests/unit/test_taxonomy_validation.py` passed 33 tests covering pointer mismatch/escape, duplicate MBIDs/sequences, unverified bands, unknown/parent taxonomy codes, lifecycle, batch counts, distribution, period and total count failures.

### T-005 — Make period and decade reporting configurable

- **Requirements:** FR-005, FR-008, NFR-003.
- **Dependencies:** T-004.
- **Status:** Completed (2026-11-06).
- **Description:** read 1960–2026 from the seed list/corpus metadata; pass it into traversal and report generation; replace hardcoded 1980/2000 boundaries; group decades dynamically from 1960s through 2020s.
- **Done when:** albums before 1960 and after 2026 are excluded with explicit reasons; albums from 1960s and 2020s are included; reports show all expected decades.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_musicbrainz_traversal.py tests/unit/test_ingest_report.py
  ```
- **Files:** `backend/src/hmde/etl/musicbrainz/traversal.py`, `backend/src/hmde/etl/musicbrainz/report.py`, tests.
- **Evidence:** 2026-11-06: traversal accepts the seed-list period and excludes 1959/2027 while including 1960/1975/2000/2026. Report labels 1960s–2020s dynamically, preserving the historical `2000` label and adding `2000s`. `uv run pytest tests/unit/test_musicbrainz_traversal.py tests/unit/test_ingest_report.py` passed 21 tests.

### T-006 — Add corpus and taxonomy metadata to E3 runs and datasets

- **Requirements:** FR-006, FR-007, NFR-001.
- **Dependencies:** T-005.
- **Status:** Completed (2026-11-06).
- **Description:** pass seed-list version, taxonomy version, period and batch IDs into `IngestRun.parameters` and the dataset manifest; preserve deterministic manifest checksums and cache-only replay.
- **Done when:** new dataset manifest contains all corpus metadata; cache-only replay produces the same dataset version; no database migration is required.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_ingest_dataset.py tests/integration/test_dataset_replay.py
  ```
- **Files:** `backend/src/hmde/etl/musicbrainz/dataset.py`, `backend/src/hmde/etl/musicbrainz/pipeline.py`, `backend/src/hmde/etl/musicbrainz/cli.py`, tests.
- **Evidence:** 2026-11-06: dataset manifests include seed-list version, taxonomy version, period and batch IDs; metadata participates in the dataset checksum. `IngestRun.parameters` records the same metadata. `uv run pytest tests/unit/test_ingest_dataset.py tests/integration/test_dataset_replay.py` passed 8 tests. The later full PostgreSQL-backed suite also passed all pipeline and runner tests.

### T-007 — Run and validate the corpus v0.2 ingestion

- **Requirements:** FR-005, FR-006, FR-007, FR-008, FR-009, NFR-001, NFR-002, NFR-003.
- **Dependencies:** T-006.
- **Status:** Completed (2026-11-06).
- **Description:** run E3 for the 57-band corpus over 1960–2026, reuse cached raw responses, fetch only missing data, write a new dataset and report, and verify the historical E3 dataset remains unchanged.
- **Done when:** 57 bands are processed; failures are reported; the new dataset and report exist; cache-only replay matches; the 1980–2000 dataset is intact; no canonical/API/frontend changes occur.
- **Verification:**
  ```bash
  cd backend
  MUSICBRAINZ_USER_AGENT="HMDE/0.1 (contact)" \
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run python -m hmde.etl.musicbrainz ingest \
      --seed-list ../data/seed-list.json \
      --raw-root ../data/raw/musicbrainz \
      --output ../data/ingestions/musicbrainz

  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run python -m hmde.etl.musicbrainz ingest \
      --seed-list ../data/seed-list.json \
      --raw-root ../data/raw/musicbrainz \
      --output ../data/ingestions/musicbrainz \
      --cache-only
  ```
- **Files:** runtime artifacts under `data/raw/` and `data/ingestions/`; validation notes.
- **Evidence:** 2026-11-06: live run `ee7125c0-1141-4d6d-b5c1-cf222e2a75e6` completed 57/57 bands with 0 failures in 12m58s, reusing 414 raw responses and fetching 488 new ones. Dataset `mb-20261107T194927Z-0d6cedd5c261` contains 57 artists, 731 release groups, 9,236 releases, 16,683 recordings, 32,326 credits, 15,901 places and 3,991 exclusions; the report covers 1960s–2020s. Cache-only run `0a68073d-9482-4662-89e9-237176e056cf` processed 57/57 bands with 0 failures, 0 new raw responses and the same dataset version. The historical dataset `mb-20261107T165005Z-52404839c696` remained byte-for-byte unchanged (12 files hashed).

### T-008 — Complete tests, CI and documentation

- **Requirements:** FR-010, FR-011, NFR-004, NFR-005, NFR-006.
- **Dependencies:** T-007.
- **Status:** Completed locally (2026-11-06); remote CI pending.
- **Description:** complete unit/integration coverage for versioned seed files, taxonomy, lifecycle, period, manifest and replay; run full backend checks and CI; update README/AGENTS/seed-list documentation and validation evidence.
- **Done when:** tests and CI pass; OpenAPI drift is absent; canonical E2 counts are unchanged; documentation describes the new active pointer, batch, taxonomy and period; spec/tasks reflect validation evidence.
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
- **Files:** `backend/tests/`, `README.md`, `AGENTS.md`, `data/README.md`, `docs/03-data/seed-list.md`, `specs/004-corpus-v0-2/`.
- **Evidence:** 2026-11-06: full backend suite passed 157 tests with PostgreSQL; Ruff check and format passed; OpenAPI drift was absent; `docker compose config -q` passed. Added integration coverage for archive immutability, pointer resolution and exact 42+15 composition. Remote GitHub Actions CI was not run because no commit/push was requested.

## 3. Coverage matrix

### Functional requirements

| Requirement | Tasks |
|---|---|
| FR-001 | T-002 |
| FR-002 | T-001, T-002 |
| FR-003 | T-003 |
| FR-004 | T-004 |
| FR-005 | T-005 |
| FR-006 | T-006 |
| FR-007 | T-004, T-006, T-007 |
| FR-008 | T-005, T-007 |
| FR-009 | T-002, T-007 |
| FR-010 | T-008 |
| FR-011 | T-002, T-008 |

### Non-functional requirements

| Requirement | Tasks |
|---|---|
| NFR-001 | T-006, T-007 |
| NFR-002 | T-004, T-007 |
| NFR-003 | T-005, T-007 |
| NFR-004 | T-008 |
| NFR-005 | T-001, T-002, T-008 |
| NFR-006 | T-008 |

## 4. Validation evidence

| Criterion | Result | Evidence |
|---|---|---|
| AC-001 | Passed | v0.2.0 loads 57 active bands; seed tests and dataset manifest `band_count: 57` |
| AC-002 | Passed | `tests/integration/test_seed_versioning.py`: 42 retained; difference equals the approved 15 MBIDs |
| AC-003 | Passed | `tests/unit/test_taxonomy_validation.py`; every seed code is an assignable leaf |
| AC-004 | Passed | `tests/unit/test_seed_v02.py`; malformed, duplicate, retired-invalid, parent-node and pointer failures |
| AC-005 | Passed | `tests/unit/test_musicbrainz_traversal.py`; 1959/2027 excluded, 1960/2026 included |
| AC-006 | Passed | Manifest includes seed-list, taxonomy, period, batch IDs and dataset version |
| AC-007 | Passed | Cache-only run reproduced `mb-20261107T194927Z-0d6cedd5c261` with 0 new responses |
| AC-008 | Passed | Coverage includes 1960s–2020s; report includes versions and status |
| AC-009 | Passed | Historical dataset 12-file checksum set unchanged |
| AC-010 | Passed locally | 157 tests, Ruff, format and OpenAPI drift pass; remote CI pending |
| AC-011 | Passed | OpenAPI drift none; full API/contract and E2 fixture suite passed; no schema migration |

## 5. Notes

- T-001 blocks all implementation until the 15-band list is approved.
- The active pointer is a repository artifact; the versioned seed list remains the source of truth.
- No album-level classification, confidence or canonical membership is implemented here.
- No live network in automated tests.
- Do not mark a task complete until its verification has been executed and recorded.
- Update `spec.md` or `plan.md` first if an implementation decision changes scope.
