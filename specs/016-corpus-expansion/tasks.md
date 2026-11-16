# Tasks — SPEC-016

- **Status:** Draft
- **Spec:** [spec.md](spec.md)
- **Plan:** [plan.md](plan.md)

## 1. Execution order

```text
T-001 ──► T-002 ──► T-003 ──► T-005 ──► T-006 ──► T-007 ──► T-008 ──► T-009 ──► T-010
                    └──► T-004 ──┘
```

T-004 can run in parallel with T-005 after T-003. T-006 needs both T-004 and T-005. T-009 needs T-008. T-011 is conditional on explicit push authorization.

## 2. Pre-work

- **Candidate pool generated:** 2026-11-16.
- **File:** `data/seed-lists/candidates/v0.3.0-pool.json`.
- **Version:** `0.3.0-candidates-01`.
- **Evidence:** 397 unique MBIDs; 375 `verified` and 22 `verified_country_inferred`; 0 MusicBrainz lookup failures; all 17 leaves represented; region counts Europe 204, North America 124, Latin America 38, Japan 11, Iberia 10 and Oceania 10.
- **Limitation:** Wikidata QIDs are not populated. WDQS returned `HTTP Error 429: Aggressively rate-limiting to 1 req / min`; all `relevance_status` values are `pending_manual_review`. T-002 must complete published-source verification before selection.
- **Status:** Input ready; not an approved seed list.

## 3. Tasks

### T-001 — Approve the target and selection criteria

- **Requirements:** FR-002, BR-001–BR-006, AC-002.
- **Dependencies:** none.
- **Description:** Review [spec.md](spec.md) and approve the 200-band target, the leaf distribution, the regional floors, the US/UK cap, the 12% leaf cap and the candidate verification rules.
- **Done when:** The owner records approval in `spec.md` or `tasks.md`; any change to the target table is reflected in the spec before selection.
- **Verification:**
  ```bash
  grep -n "Status:\|FR-002\|Target 200" specs/016-corpus-expansion/spec.md
  ```
- **Files:** `specs/016-corpus-expansion/spec.md`, `specs/016-corpus-expansion/tasks.md`.
- **Evidence:** Pending owner approval.

### T-002 — Verify candidates and select 143 bands

- **Requirements:** FR-001, FR-002, FR-003, NFR-002, AC-001, AC-002.
- **Dependencies:** T-001.
- **Description:** Enrich the 397-band pool with published-source evidence and album checks. For every candidate, verify the MusicBrainz MBID, country, leaf and at least one studio album first released 1960-01-01–2026-12-31. Use MusicBrainz `url-rels` to Wikidata/Wikipedia first, then bounded Wikipedia API calls. Record `wikidata_qid`, `wikipedia_url`, `relevance_source`, `studio_album_count`, `earliest_album`, `latest_album`, `album_check` and `relevance_status`. Reject duplicates, existing v0.2.0 bands, unverified countries, ambiguous artists, candidates without a studio album and candidates without a published source.
- **Done when:** 143 unique bands are selected across three batches of 50, 50 and 43; the leaf table in `spec.md` is met; regional floors are met or documented; every acceptance and rejection has a reason; the owner approves the selection.
- **Verification:**
  ```bash
  python3 - <<'PY'
  import json
  from collections import Counter
  from pathlib import Path

  pool = json.loads(Path('data/seed-lists/candidates/v0.3.0-pool.json').read_text())
  selection = json.loads(Path('data/seed-lists/candidates/v0.3.0-selection.json').read_text())

  assert 300 <= pool['pool_size'] <= 400
  assert len({band['mbid'] for band in pool['bands']}) == pool['pool_size']

  selected = selection['selected']
  assert len(selected) == 143
  assert len({band['mbid'] for band in selected}) == 143
  assert all(band['mbid'] not in {x['mbid'] for x in json.loads(Path('data/seed-lists/v0.2.0.json').read_text())['bands']} for band in selected)
  assert all(band['album_check'] == 'verified' for band in selected)
  assert all(band['relevance_status'] == 'verified' for band in selected)

  leaf = Counter(band.get('seed_subgenre_code') or band['proposed_leaf'] for band in selected)
  region = Counter(band['region'] for band in selected)
  print(dict(sorted(leaf.items())))
  print(dict(sorted(region.items())))
  PY
  ```
- **Files:** `data/seed-lists/candidates/v0.3.0-pool.json`, `data/seed-lists/candidates/v0.3.0-selection.json`, `data/seed-lists/batches/v0.3.0-batch-01.json`, `v0.3.0-batch-02.json`, `v0.3.0-batch-03.json`.
- **Evidence:** Pending.

### T-003 — Create the v0.3.0 seed list and pointer

- **Requirements:** FR-004, FR-010, BR-001, BR-002, BR-004, BR-009, AC-003.
- **Dependencies:** T-002.
- **Description:** Create `data/seed-lists/v0.3.0.json` with schema 2, version `0.3.0`, taxonomy `0.2.0`, period 1960–2026, 200 bands and three new batches. Retain all 57 v0.2.0 bands and their provenance. Move `data/seed-list.json` to v0.3.0 only after validation. Do not modify v0.1.0 or v0.2.0.
- **Done when:** The seed loader validates the file; total bands and subgenre distribution are correct; every new band references a batch; no MBID or sequence is duplicated; v0.2.0 checksums are unchanged; the active pointer resolves v0.3.0.
- **Verification:**
  ```bash
  python3 - <<'PY'
  import hashlib
  import json
  from collections import Counter
  from pathlib import Path

  before = hashlib.sha256(Path('data/seed-lists/v0.2.0.json').read_bytes()).hexdigest()
  seed = json.loads(Path('data/seed-lists/v0.3.0.json').read_text())
  old = json.loads(Path('data/seed-lists/v0.2.0.json').read_text())
  pointer = json.loads(Path('data/seed-list.json').read_text())

  assert seed['schema_version'] == 2
  assert seed['version'] == '0.3.0'
  assert seed['taxonomy_version'] == '0.2.0'
  assert seed['total_bands'] == 200
  assert len(seed['bands']) == 200
  assert len({band['mbid'] for band in seed['bands']}) == 200
  assert {band['mbid'] for band in old['bands']} <= {band['mbid'] for band in seed['bands']}
  assert Counter(band['seed_subgenre_code'] for band in seed['bands']) == {
      'heavy-metal': 18, 'nwobhm': 8, 'hard-rock': 12, 'proto-metal': 6,
      'thrash-metal': 22, 'death-metal': 22, 'black-metal': 18, 'doom-metal': 14,
      'stoner-metal': 10, 'sludge-metal': 6, 'power-metal': 14,
      'progressive-metal': 16, 'groove-metal': 6, 'metalcore': 10,
      'deathcore': 6, 'djent': 6, 'post-metal': 6,
  }
  assert pointer.get('path') == 'seed-lists/v0.3.0.json' or pointer.get('seed_list') == 'v0.3.0.json'
  after = hashlib.sha256(Path('data/seed-lists/v0.2.0.json').read_bytes()).hexdigest()
  assert before == after
  print('seed list v0.3.0 valid')
  PY
  ```
- **Files:** `data/seed-lists/v0.3.0.json`, `data/seed-list.json`, `data/seed-lists/batches/v0.3.0-batch-*.json`.
- **Evidence:** Pending.

### T-004 — Make corpus/version guards data-driven

- **Requirements:** FR-006, FR-007, FR-010, NFR-006, NFR-007, AC-005, AC-006.
- **Dependencies:** T-003.
- **Description:** Update `backend/src/hmde/normalization/inputs.py` to accept seed-list `0.3.0` while keeping taxonomy `0.2.0`. Replace the `active == 57` membership check in `backend/src/hmde/quality/structural.py` with the active seed-list count. Create `data/quality/rules-v0.2.0.json` with a dynamic `Q-MEM-001` and update tests that assert 0.2.0/57. Do not add a migration.
- **Done when:** Unit and integration tests cover 57 and 200 bands; the quality rule fails only when membership differs from the active seed list; no test depends on a hardcoded 57 for future corpora.
- **Verification:**
  ```bash
  cd backend
  uv run ruff check .
  uv run ruff format --check .
  uv run pytest tests/unit tests/integration/test_quality_structural.py tests/integration/test_normalization_membership.py
  ```
- **Files:** `backend/src/hmde/normalization/inputs.py`, `backend/src/hmde/quality/structural.py`, `data/quality/rules-v0.2.0.json`, affected backend tests.
- **Evidence:** Pending.

### T-005 — Run E3 ingestion for 200 bands

- **Requirements:** FR-005, NFR-001–NFR-004, AC-004.
- **Dependencies:** T-003.
- **Description:** Run the existing E3 ingestion against the active v0.3.0 seed list. Preserve the raw cache, manifest, checksums, seed-list version and batch IDs. Do not publish a partial dataset. Replay with `--cache-only` and compare the dataset version and manifest.
- **Done when:** 200/200 bands are processed with zero unresolved failures; a new dataset exists; cache-only replay is stable; the v0.2.0 dataset is unchanged.
- **Verification:**
  ```bash
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
      --output ../data/ingestions/musicbrainz --cache-only
  ```
- **Files:** `data/raw/musicbrainz/`, `data/ingestions/musicbrainz/` (ignored by Git), `tasks.md`.
- **Evidence:** Pending: dataset ID, band count, failure count, replay result, duration and size.

### T-006 — Run E4 normalization for 200 bands

- **Requirements:** FR-006, FR-010, NFR-001, NFR-006, NFR-007, AC-005.
- **Dependencies:** T-004, T-005.
- **Description:** Review the new tags and album classifications. Reuse the current tag map and overrides if they cover all new records; otherwise create reviewed v0.3.0 versions and record why. Run normalization against the new dataset, v0.3.0 seed list and taxonomy 0.2.0. Review memberships, classification confidence, aggregates and quarantine.
- **Done when:** 200 active memberships exist; every raw record is mapped or quarantined; no orphan or duplicate identity is accepted; classification review is complete; the run records all versions.
- **Verification:**
  ```bash
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run python -m hmde.normalization run \
      --dataset ../data/ingestions/musicbrainz/<dataset-id> \
      --taxonomy ../data/taxonomy.json \
      --tag-map ../data/classifications/tag-map-v0.1.0.json \
      --overrides ../data/classifications/manual-overrides-v0.1.0.json \
      --seed-list ../data/seed-list.json \
      --output ../data/normalization
  ```
- **Files:** `data/normalization/` (ignored), `data/classifications/*` if a new version is required, `tasks.md`.
- **Evidence:** Pending: normalization run ID, membership count, classification coverage, quarantine count, version set.

### T-007 — Run E5 quality and approve exceptions

- **Requirements:** FR-007, FR-010, BR-010, AC-006.
- **Dependencies:** T-006.
- **Description:** Run the quality gate against the v0.3.0 normalization run, rules v0.2.0 and a new exceptions baseline. Triage each finding; fix structural causes; approve exceptions only with a reason and scope. Compare coverage with v0.2.0.
- **Done when:** The run completes with zero unexcepted blocking findings; every exception is approved; coverage is reported by band, decade, leaf, country, batch and role; missing credits are presented with denominators.
- **Verification:**
  ```bash
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run python -m hmde.quality run \
      --normalization-run <normalization-run-id> \
      --rules ../data/quality/rules-v0.2.0.json \
      --exceptions ../data/quality/exceptions-v0.3.0.json \
      --output ../data/quality --strict
  ```
- **Files:** `data/quality/rules-v0.2.0.json`, `data/quality/exceptions-v0.3.0.json`, `data/quality/` (ignored), `tasks.md`.
- **Evidence:** Pending: quality run ID, findings, exceptions, blockers, coverage summary.

### T-008 — Run E6 EDA and E7 network analysis

- **Requirements:** FR-008, FR-010, NFR-001, NFR-003, AC-007.
- **Dependencies:** T-007.
- **Description:** Run E6 and E7 against the v0.3.0 normalization and quality runs. Reuse the metric catalogue if definitions are unchanged; otherwise add a reviewed version. Compare coverage, producer concentration and community structure with v0.2.0. Record all versions and limitations.
- **Done when:** A new EDA report and network snapshot exist; the reports include denominators and limitations; the v0.2.0/v0.3.0 comparison is documented; the analysis run can be loaded by the API.
- **Verification:**
  ```bash
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run python -m hmde.analytics run \
      --normalization-run <normalization-run-id> \
      --quality-run <quality-run-id> \
      --taxonomy ../data/taxonomy.json \
      --metric-catalogue ../data/metrics/catalogue-v0.1.0.json \
      --output ../data/analysis

  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run python -m hmde.network run \
      --normalization-run <normalization-run-id> \
      --quality-run <quality-run-id> \
      --taxonomy ../data/taxonomy.json \
      --output ../data/network
  ```
- **Files:** `data/analysis/`, `data/network/` (ignored), `data/metrics/*` if a new version is required, `tasks.md`.
- **Evidence:** Pending: EDA report ID, network run ID, edge/node/community counts, comparison summary.

### T-009 — Verify API and graph performance at 200 bands

- **Requirements:** FR-009, NFR-005, AC-008.
- **Dependencies:** T-008.
- **Description:** Load the v0.3.0 analysis run into the local stack. Measure overview band/album node and edge counts, overview latency, `/graph` readiness, view-switch response and ego-graph behaviour. Decide whether to keep the 1,000-node cap with truncation or raise it to 2,000. Record the decision and evidence. Add a regression test only if behaviour changes.
- **Done when:** The new run loads; measurements are recorded; the cap decision is documented; E2E and accessibility checks pass; there is no unexplained regression.
- **Verification:**
  ```bash
  cd frontend
  HMDE_ANALYSIS_RUN=<analysis-run-id> npm run test:perf
  npm run test:e2e
  ```
- **Files:** `backend/src/hmde/api/routes/producers.py` only if the cap changes, `frontend/` tests only if truncation changes, `docs/01-architecture/qa-report.md` or `docs/01-architecture/performance.md`, `tasks.md`.
- **Evidence:** Pending: node/edge counts, p50/p95 latency, view-switch timing, cap decision.

### T-010 — Run the full regression and update documentation

- **Requirements:** FR-011, FR-012, AC-009, AC-010, AC-011.
- **Dependencies:** T-009.
- **Description:** Run all backend and frontend checks. Update the seed-list document, roadmap, specs index, `AGENTS.md`, `data/README.md`, candidate-pool guide, spec result and this task file. Review the diff for secrets, unrelated changes, production work, new dependencies and unnecessary migrations.
- **Done when:** All checks pass or have an explicit documented exception; documentation reflects the real state; the diff contains no secrets or scope creep; the spec is ready for validation.
- **Verification:**
  ```bash
  cd backend
  uv run ruff check .
  uv run ruff format --check .
  uv run pytest
  uv run --env-file ../.env pytest

  cd ../frontend
  npm run lint
  npm run typecheck
  npm run test
  npm run build
  npm run test:e2e
  ```
- **Files:** `docs/03-data/seed-list.md`, `docs/00-vision/roadmap.md`, `specs/README.md`, `AGENTS.md`, `data/README.md`, `specs/016-corpus-expansion/spec.md`, `tasks.md`.
- **Evidence:** Pending.

### T-011 — Remote CI after explicit authorization

- **Requirements:** AC-009, AC-010.
- **Dependencies:** T-010.
- **Description:** Only after explicit owner authorization, commit and push the change, wait for the remote CI run and record the run ID. Do not force-push or change branch protection without authorization.
- **Done when:** The authorized remote run passes or its failure is recorded with a fix plan.
- **Verification:**
  ```bash
  git status
  git diff --stat
  # commit and push only after explicit authorization
  gh run list --limit 5
  ```
- **Files:** Git history and CI evidence.
- **Evidence:** Pending authorization.

## 4. Coverage matrix

### Functional requirements

| Requirement | Tasks |
|---|---|
| FR-001 | T-002 |
| FR-002 | T-001, T-002 |
| FR-003 | T-002 |
| FR-004 | T-003 |
| FR-005 | T-005 |
| FR-006 | T-004, T-006 |
| FR-007 | T-004, T-007 |
| FR-008 | T-008 |
| FR-009 | T-009 |
| FR-010 | T-003, T-005, T-006, T-007, T-008 |
| FR-011 | T-010 |
| FR-012 | T-010 |

### Non-functional requirements

| Requirement | Tasks |
|---|---|
| NFR-001 | T-005, T-008 |
| NFR-002 | T-002, T-005 |
| NFR-003 | T-005, T-008 |
| NFR-004 | T-005 |
| NFR-005 | T-009 |
| NFR-006 | T-004, T-006 |
| NFR-007 | T-004, T-006 |

## 5. Validation evidence

| Criterion | Result | Evidence |
|---|---|---|
| AC-001 | Pending | Candidate pool generated; selection verification pending T-002. |
| AC-002 | Pending | T-001, T-002. |
| AC-003 | Pending | T-003. |
| AC-004 | Pending | T-005. |
| AC-005 | Pending | T-006. |
| AC-006 | Pending | T-007. |
| AC-007 | Pending | T-008. |
| AC-008 | Pending | T-009. |
| AC-009 | Pending | T-010. |
| AC-010 | Pending | T-010. |
| AC-011 | Pending | T-010. |

## 6. Notes

- The candidate pool is a pre-selection artifact. Do not point the active seed list at it.
- Wikidata enrichment must use MusicBrainz URL relationships or the Wikipedia API before attempting WDQS again.
- Do not lower the 200-band target silently. If the selection cannot meet a target, record the deviation and get owner approval.
- Do not change taxonomy v0.2.0 in this spec.
- Do not resume E12 or perform production work in this spec.
- Record actual ingestion duration and storage size; the plan budget is one working session per major stage.
- Keep v0.2.0 and earlier artifacts immutable.
