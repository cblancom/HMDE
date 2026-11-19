# Tasks — SPEC-016

- **Status:** Implemented
- **Spec:** [spec.md](spec.md)
- **Plan:** [plan.md](plan.md)

## 1. Execution order

```text
T-001 ──► T-002 ──► T-003 ──► T-005 ──► T-005A ──► T-006 ──► T-007 ──► T-008 ──► T-009 ──► T-010
                    └──► T-004 ──┘
```

T-004 can run in parallel with T-005 after T-003. T-005A corrects the E3 dataset before normalization. T-006 needs T-004 and T-005A. T-009 needs T-008. T-011 is conditional on explicit push authorization.

## 2. Pre-work

- **Candidate pool generated:** 2026-11-16; owner additions merged 2026-11-17.
- **File:** `data/seed-lists/candidates/v0.3.0-pool.json`.
- **Version:** `0.3.0-candidates-02`.
- **Evidence:** 453 unique MBIDs; after T-002, 448 `verified` and 5 `verified_country_inferred`; 0 MusicBrainz lookup failures; all 17 leaves represented; region counts Europe 238, North America 124, Latin America 47, Japan 13, Iberia 18 and Oceania 13.
- **Owner decision:** all 453 candidates were accepted for verification. The target is up to 510 active bands (57 current + 453 new). T-002 accepted 452 and excluded Hellhammer, so the verified corpus is 509. Candidates that fail verification are excluded and reported.
- **Enrichment:** T-002 completed published-source and album verification. 430 candidates have Wikidata QIDs, 14 have Wikipedia URLs, 19 use Discogs and 4 use AllMusic. WDQS remains unused.
- **Status:** Verified; verification report and batches approved on 2026-11-17. Not an active seed list yet.

## 3. Tasks

### T-001 — Approve the target and verification criteria

- **Requirements:** FR-002, BR-001–BR-006, AC-002.
- **Dependencies:** none.
- **Description:** Review [spec.md](spec.md) and approve the 510-band target, all 453 candidates, the three batches (151/151/150), the 13% leaf concentration check, the graph truncation policy and the exclusion-and-report rule.
- **Done when:** The owner records approval in `spec.md` or `tasks.md`; any change to the target table is reflected in the spec before verification.
- **Verification:**
  ```bash
  grep -n "Status:\|FR-002\|453 candidates\|510 active" specs/016-corpus-expansion/spec.md
  ```
- **Files:** `specs/016-corpus-expansion/spec.md`, `specs/016-corpus-expansion/tasks.md`.
- **Evidence:** Owner approved 2026-11-17: 510-band target, all 453 candidates, three batches (151/151/150), exclusion-and-report policy and graph truncation.

### T-002 — Verify all 453 candidates and create the three batches

- **Requirements:** FR-001, FR-002, FR-003, NFR-002, AC-001, AC-002.
- **Dependencies:** T-001.
- **Description:** Enrich the 453-band pool with published-source evidence and album checks. For every candidate, verify the MusicBrainz MBID, country, leaf and at least one studio album first released 1960-01-01–2026-12-31. Use MusicBrainz `url-rels` to Wikidata/Wikipedia first, then bounded Wikipedia API calls and Discogs/AllMusic fallbacks. Record `country_check`, `album_check`, `studio_album_count`, `earliest_album`, `latest_album`, `relevance_status`, `wikidata_qid`, `wikipedia_url`, `relevance_source`, `verified_at` and `verification_notes`. Exclude duplicates, existing v0.2.0 bands, unverified countries, ambiguous artists, candidates without a studio album and candidates without a published source. Write the evidence to `v0.3.0-verification.json` and create three batch artifacts of at most 151 bands each when all candidates pass; if a candidate is excluded, the three batches contain the accepted candidates and the exclusion is reported.
- **Done when:** All 453 candidates are accepted or excluded with a reason; the verification report records album, source and country evidence; the three batch artifacts contain the accepted candidates; the owner approves the verification report.
- **Verification:**
  ```bash
  python3 - <<'PY'
  import json
  from collections import Counter
  from pathlib import Path

  pool = json.loads(Path('data/seed-lists/candidates/v0.3.0-pool.json').read_text())
  verification = json.loads(Path('data/seed-lists/candidates/v0.3.0-verification.json').read_text())
  batches = [
      json.loads(Path(f'data/seed-lists/batches/v0.3.0-batch-0{i}.json').read_text())
      for i in (1, 2, 3)
  ]
  active = {band['mbid'] for band in json.loads(Path('data/seed-lists/v0.2.0.json').read_text())['bands']}

  assert 300 <= pool['pool_size'] <= 500
  assert len({band['mbid'] for band in pool['bands']}) == pool['pool_size']

  accepted = verification['accepted']
  excluded = verification['excluded']
  assert len(accepted) + len(excluded) == pool['pool_size']
  assert len({band['mbid'] for band in accepted}) == len(accepted)
  assert all(band['mbid'] not in active for band in accepted)
  assert all(band['album_check'] == 'verified' for band in accepted)
  assert all(band['relevance_status'] == 'verified' for band in accepted)
  assert all(band['country_check'] in {'verified', 'documented_inference'} for band in accepted)
  assert all(band.get('verification_notes') for band in excluded)

  assert len(batches) == 3
  assert sum(len(batch['bands']) for batch in batches) == len(accepted)
  assert all(len(batch['bands']) <= 151 for batch in batches)

  leaf = Counter(band.get('seed_subgenre_code') or band['proposed_leaf'] for band in accepted)
  region = Counter(band['region'] for band in accepted)
  print(dict(sorted(leaf.items())))
  print(dict(sorted(region.items())))
  PY
  ```
- **Files:** `data/seed-lists/candidates/v0.3.0-pool.json`, `data/seed-lists/candidates/v0.3.0-verification.json`, `data/seed-lists/batches/v0.3.0-batch-01.json`, `v0.3.0-batch-02.json`, `v0.3.0-batch-03.json`.
- **Evidence:** 453 candidates checked; 452 accepted and 1 excluded. Hellhammer (`cand-0453`) has no eligible studio album in 1960–2026. 430 candidates use Wikidata, 14 use Wikipedia, 19 use Discogs and 4 use AllMusic as relevance evidence. Batches are 151/151/150. Report: `data/seed-lists/candidates/v0.3.0-verification.json`. Owner approved the verification report, the Hellhammer exclusion and the batches on 2026-11-17. Final verified corpus is 509 active bands.

### T-003 — Create the v0.3.0 seed list and pointer

- **Requirements:** FR-004, FR-010, BR-001, BR-002, BR-004, BR-009, AC-003.
- **Dependencies:** T-002.
- **Description:** Create `data/seed-lists/v0.3.0.json` with schema 2, version `0.3.0`, taxonomy `0.2.0`, period 1960–2026, 509 active bands and three new batches. Retain all 57 v0.2.0 bands and their provenance. Move `data/seed-list.json` to v0.3.0 only after validation. Do not modify v0.1.0 or v0.2.0.
- **Done when:** The seed loader validates the file; total bands equal 57 plus the accepted candidates; the subgenre distribution matches the verification report; every new band references a batch; no MBID or sequence is duplicated; v0.2.0 checksums are unchanged; the active pointer resolves v0.3.0.
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
  verification = json.loads(Path('data/seed-lists/candidates/v0.3.0-verification.json').read_text())
  pointer = json.loads(Path('data/seed-list.json').read_text())
  accepted = verification['accepted']
  expected_total = len(old['bands']) + len(accepted)

  assert seed['schema_version'] == 2
  assert seed['version'] == '0.3.0'
  assert seed['taxonomy_version'] == '0.2.0'
  assert expected_total <= 510
  assert seed['total_bands'] == expected_total
  assert len(seed['bands']) == expected_total
  assert len({band['mbid'] for band in seed['bands']}) == expected_total
  assert {band['mbid'] for band in old['bands']} <= {band['mbid'] for band in seed['bands']}
  expected_leaf = Counter(band['seed_subgenre_code'] for band in old['bands'])
  for band in accepted:
      expected_leaf[band['proposed_leaf']] += 1
  assert Counter(band['seed_subgenre_code'] for band in seed['bands']) == expected_leaf
  assert pointer.get('path') == 'seed-lists/v0.3.0.json' or pointer.get('seed_list') == 'v0.3.0.json'
  after = hashlib.sha256(Path('data/seed-lists/v0.2.0.json').read_bytes()).hexdigest()
  assert before == after
  print('seed list v0.3.0 valid')
  PY
  ```
- **Files:** `data/seed-lists/v0.3.0.json`, `data/seed-list.json`, `data/seed-lists/batches/v0.3.0-batch-*.json`.
- **Evidence:** `v0.3.0.json` validated by the existing v2 seed loader: 509 bands, 509 active, 17 leaves, batches `v0.1.0` 42 + `v0.2.0-batch-01` 15 + `v0.3.0-batch-01` 151 + `-02` 151 + `-03` 150. Pointer resolves `0.3.0`. v0.2.0 checksum unchanged. Targeted tests: 22 passed (`tests/unit/test_seed_v02.py`, `tests/integration/test_seed_versioning.py`); ruff passed.

### T-004 — Make corpus/version guards data-driven

- **Requirements:** FR-006, FR-007, FR-010, NFR-006, NFR-007, AC-005, AC-006.
- **Dependencies:** T-003.
- **Description:** Update `backend/src/hmde/normalization/inputs.py` to accept seed-list `0.3.0` while keeping taxonomy `0.2.0`. Replace the `active == 57` membership check in `backend/src/hmde/quality/structural.py` with the active seed-list count. Create `data/quality/rules-v0.2.0.json` with a dynamic `Q-MEM-001` and update tests that assert 0.2.0/57. Do not add a migration.
- **Done when:** Unit and integration tests cover 57 and 509 bands; the quality rule fails only when membership differs from the active seed list; no test depends on a hardcoded 57 for future corpora.
- **Verification:**
  ```bash
  cd backend
  uv run ruff check .
  uv run ruff format --check .
  uv run pytest tests/unit tests/integration/test_quality_structural.py tests/integration/test_normalization_membership.py
  ```
- **Files:** `backend/src/hmde/normalization/inputs.py`, `backend/src/hmde/quality/inputs.py`, `backend/src/hmde/quality/structural.py`, `backend/src/hmde/quality/runner.py`, `data/quality/rules-v0.2.0.json`, `backend/tests/unit/test_normalization_inputs.py`, `backend/tests/unit/test_quality_catalogue.py`, `backend/tests/unit/test_quality_membership.py`, `backend/tests/integration/test_quality_structural.py`.
- **Evidence:** Normalization accepts seed-list `0.2.0` and `0.3.0` with taxonomy `0.2.0`; quality loads the active seed-list count for the selected run version; `Q-MEM-001` compares active memberships to that count and `rules-v0.2.0.json` has `threshold: null`. Unit suite: 221 passed; integration `test_quality_structural.py` and `test_normalization_membership.py`: 3 passed; ruff check and format passed. No migration.

### T-005 — Run E3 ingestion for 509 bands

- **Requirements:** FR-005, NFR-001–NFR-004, AC-004.
- **Dependencies:** T-003.
- **Description:** Run the existing E3 ingestion against the active v0.3.0 seed list. Preserve the raw cache, manifest, checksums, seed-list version and batch IDs. Do not publish a partial dataset. Replay with `--cache-only` and compare the dataset version and manifest.
- **Done when:** 509/509 bands are processed with zero unresolved failures; a new dataset exists; cache-only replay is stable; the v0.2.0 dataset is unchanged.
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
- **Evidence:** Executed 2026-11-19: 509/509 bands, 0 failures. The initial datasets `mb-20261119T004940Z-a60593217ef1` and `mb-20261119T004940Z-627cc073ab06` are retained as evidence but are not accepted: replay differed only in `recordings.ndjson` order, and the dataset contained 7 multi-artist release groups and 43 duplicate recording MBIDs. T-005A superseded them with the canonical dataset. Raw cache is 1.8 GB.

### T-005A — Make E3 deterministic and exclude multi-artist release groups

- **Status:** Completed 2026-11-19.
- **Requirements:** FR-005, FR-010, NFR-001, NFR-003, NFR-004, AC-004.
- **Dependencies:** T-005.
- **Description:** Make every E3 NDJSON file totally ordered, with a deterministic tie-breaker for records that share the primary sort key. Write one canonical row per artist, release group, release and recording MBID. Exclude release groups associated with more than one active band and remove dependent rows that become orphaned; report them with reason `multi_artist_release_group`. Reconcile or label extracted-record and canonical-row counts in the coverage report. Add regression tests for equal sort keys, shuffled input, duplicate entity MBIDs and cache-only replay. Regenerate the dataset from the existing raw cache; do not use `--refresh`.
- **Done when:** Unit and integration tests prove deterministic ordering and entity uniqueness; the normal run and the cache-only replay produce the same dataset version and byte-identical NDJSON/manifest; 509/509 bands are processed with zero failures; the 7 multi-artist release groups are excluded and reported; duration and storage are recorded; the v0.2.0 dataset is unchanged; no schema migration is added.
- **Verification:**
  ```bash
  cd backend
  uv run ruff check .
  uv run ruff format --check .
  uv run pytest tests/unit/test_ingest_dataset.py

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
- **Files:** `backend/src/hmde/etl/musicbrainz/dataset.py`, `backend/src/hmde/etl/musicbrainz/report.py`, `backend/src/hmde/etl/musicbrainz/pipeline.py`, `backend/tests/unit/test_ingest_dataset.py`, `backend/tests/unit/test_ingest_report.py`, `tasks.md`.
- **Evidence:** Completed 2026-11-19. Dataset `mb-20261119T004940Z-9d5e75fdc1b9`; normal run `64efcc55-0642-4ec1-b622-c47673d90432`, replay `193b6b24-a67f-4bec-a17b-fc2bbbcbd627`; both `completed`, 509/509 bands, 0 failures, 5,941 cached responses and the same dataset version/manifest. Canonical counts: artists 509, external IDs 486, release groups 4,826, releases 31,629, recordings 82,228, release-recordings 381,119, credits 106,981, places 51,005, exclusions 9,317. No duplicate entity MBIDs; 7 `multi_artist_release_group` exclusions. Dataset 155 MB; raw cache 1.8 GB. Unit suite 225 passed; ingestion integration 8 passed; traversal integration 1 passed on a clean test database. `ruff check` and `ruff format --check` passed. No schema migration.

### T-006 — Run E4 normalization for 509 bands

- **Status:** Completed 2026-11-19.
- **Requirements:** FR-006, FR-010, NFR-001, NFR-006, NFR-007, AC-005.
- **Dependencies:** T-004, T-005A.
- **Description:** Review the new tags and album classifications. Reuse the current tag map and overrides if they cover all new records; otherwise create reviewed v0.3.0 versions and record why. Run normalization against the corrected canonical dataset, v0.3.0 seed list and taxonomy 0.2.0. Review memberships, classification confidence, aggregates and quarantine. Excluded multi-artist release groups must not appear as canonical entities.
- **Done when:** 509 active memberships exist; every record included in the canonical dataset is mapped or quarantined; no orphan or duplicate identity is accepted; multi-artist exclusions are reported rather than normalized; classification review is complete; the run records all versions.
- **Verification:**
  ```bash
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run python -m hmde.normalization run \
      --dataset ../data/ingestions/musicbrainz/mb-20261119T004940Z-9d5e75fdc1b9 \
      --taxonomy ../data/taxonomy.json \
      --tag-map ../data/classifications/tag-map-v0.3.0.json \
      --overrides ../data/classifications/manual-overrides-v0.3.0.json \
      --seed-list ../data/seed-list.json \
      --output ../data/normalization
  ```
- **Files:** `data/normalization/` (ignored), `data/classifications/tag-map-v0.3.0.json`, `data/classifications/manual-overrides-v0.3.0.json`, `docs/03-data/normalization-rules.md`, `tasks.md`.
- **Evidence:** Run `ed8e7e12-c181-4041-ba39-42b2bf655453`, `completed_with_review`. Dataset `mb-20261119T004940Z-9d5e75fdc1b9`; taxonomy 0.2.0; tag map/overrides 0.3.0. 509 active memberships for the dataset; 4,826 release groups; classification 3,926 accepted, 900 review, 0 quarantined; 14 overrides applied; 0 credits quarantined. Aggregates: 320 accepted, 189 review, 0 missing. Issues: 1,089 medium review (900 classification, 148 aggregate review, 28 tie, 13 low confidence); no blocking issue. Tag-map v0.3.0 adds 20 exact labels; albums without usable tags use the band seed leaf at confidence 0.50 with review status, and equal candidates use the seed leaf when tied. No excluded multi-artist release group is present. Structural checks and the review queue are recorded for T-007.

### T-007 — Run E5 quality and approve exceptions

- **Status:** Completed 2026-11-19.
- **Requirements:** FR-007, FR-010, BR-010, AC-006.
- **Dependencies:** T-006.
- **Description:** Run the quality gate against the v0.3.0 normalization run, rules v0.2.0 and a new exceptions baseline. Triage each finding; fix structural causes; approve exceptions only with a reason and scope. Compare coverage with v0.2.0.
- **Done when:** The run completes with zero unexcepted blocking findings; every exception is approved; coverage is reported by band, decade, leaf, country, batch and role; missing credits are presented with denominators.
- **Verification:**
  ```bash
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run python -m hmde.quality run \
      --normalization-run ed8e7e12-c181-4041-ba39-42b2bf655453 \
      --rules ../data/quality/rules-v0.2.0.json \
      --exceptions ../data/quality/exceptions-v0.3.0.json \
      --output ../data/quality --strict
  ```
- **Files:** `data/quality/rules-v0.2.0.json`, `data/quality/exceptions-v0.3.0.json`, `docs/03-data/data-quality.md`, `data/quality/` (ignored), `tasks.md`.
- **Evidence:** Quality run `288b11ac-9a90-4b4f-bf58-fdd50e1a51ad`, `completed_with_findings`; normalization `ed8e7e12-c181-4041-ba39-42b2bf655453`; rules 0.2.0; exceptions 0.3.0 (empty). 20 rules and 77 metrics. 1,089 findings: 900 `Q-CLS-002` and 189 `Q-AGG-001`, all medium/advisory; 0 blocking, 0 exceptions and exit code 2. Coverage covers batch, country, decade, taxonomy leaf, role, source, field and credit scope; missing-data metrics use denominators. v0.2.0 comparison: 58 findings (24 blocking excepted, 34 advisory) and 51 metrics. No structural fix or blocking exception was required; review findings remain visible.

### T-008 — Run E6 EDA and E7 network analysis

- **Status:** Completed 2026-11-19.
- **Requirements:** FR-008, FR-010, NFR-001, NFR-003, AC-007.
- **Dependencies:** T-007.
- **Description:** Run E6 and E7 against the v0.3.0 normalization and quality runs. Reuse the metric catalogue if definitions are unchanged; otherwise add a reviewed version. Compare coverage, producer concentration and community structure with v0.2.0. Record all versions and limitations.
- **Done when:** A new EDA report and network snapshot exist; the reports include denominators and limitations; the v0.2.0/v0.3.0 comparison is documented; the analysis run can be loaded by the API.
- **Verification:**
  ```bash
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run python -m hmde.analytics run \
      --normalization-run ed8e7e12-c181-4041-ba39-42b2bf655453 \
      --quality-run 288b11ac-9a90-4b4f-bf58-fdd50e1a51ad \
      --taxonomy ../data/taxonomy.json \
      --metric-catalogue ../data/metrics/catalogue-v0.1.0.json \
      --output ../data/analysis

  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run python -m hmde.network run \
      --normalization-run ed8e7e12-c181-4041-ba39-42b2bf655453 \
      --quality-run 288b11ac-9a90-4b4f-bf58-fdd50e1a51ad \
      --taxonomy ../data/taxonomy.json \
      --output ../data/network
  ```
- **Files:** `data/analysis/`, `data/network/` (ignored), `data/metrics/*` if a new version is required, `docs/03-data/analysis-v0.3.0.md` for the comparison, `tasks.md`.
- **Evidence:** E6 `eda-bd2ef42a54786c67` with 927 metrics; E7 run `613a597e-242c-44ab-add3-a95381d23ec3`, analysis version `net-78a54051ff047f86`, status `completed_with_limitations`. Network: producer_album 3,719 nodes / 4,217 edges / 300 components; producer_band 1,570 nodes / 1,700 edges / 111 components; 325 communities; support full 1,224 / partial 3,060 / unknown 0. v0.2 comparison: EDA 354 metrics; producer_album 968/1,134/67; producer_band 398/426/13; 78 communities. The shared canonical tables retain one legacy release group, one release, five recordings and 3,090 legacy credits outside the v0.3 canonical dataset, so E6/E7 report 4,827 albums and 110,071 credits versus 4,826 and 106,981 in the E3 dataset; this limitation is documented for T-010. The analysis run is persisted and loadable.

### T-009 — Verify API and graph performance at 509 bands

- **Status:** Completed 2026-11-19.
- **Requirements:** FR-009, NFR-005, AC-008.
- **Dependencies:** T-008.
- **Description:** Load the v0.3.0 analysis run into the local stack. Measure overview band/album node and edge counts, overview latency, `/graph` readiness, view-switch response and ego-graph behaviour. At 509 bands the overview is expected to exceed the 1,000-node/2,000-edge cap; keep the cap with explicit truncation unless measurements justify a bounded raise. Record the decision and evidence. Add a regression test only if behaviour changes.
- **Done when:** The new run loads; measurements are recorded; the truncation/cap decision is documented with returned and total counts; E2E and accessibility checks pass; there is no unexplained regression.
- **Verification:**
  ```bash
  cd frontend
  HMDE_ANALYSIS_RUN=<analysis-run-id> npm run test:perf
  npm run test:e2e
  ```
- **Files:** `backend/src/hmde/services/producers.py`, `frontend/e2e/performance.spec.ts`, `docs/01-architecture/qa-report.md`, `docs/03-data/analysis-v0.3.0.md`, `tasks.md`.
- **Evidence:** Performance probe passed with one documented exception. API p95: overview bands 411 ms and albums 486 ms (target 1,500 ms); lists/details/search/ego all within target. Browser p95: graph navigation 2,956 ms (target 5,000), view-switch acknowledgement 2,373 ms (target 1,000; exception), full view settle 2,626 ms (target 5,000), panel toggle 686 ms (target 1,000), ego navigation 681 ms (target 5,000). The 1,000-node/2,000-edge cap is kept with explicit truncation: albums 1,000 nodes/810 edges (295 of 1,444 producers), bands 1,000 nodes/1,125 edges (913 of 1,444). Network has 4,217 producer–album edges, 1,700 producer–band edges and 325 communities. CoSE completed in 10.1 s and fCoSE in 2.0 s. Playwright E2E: 26 tests passed, including nine axe scans. The view-switch exception is documented in the QA report; no cap raise or UI rewrite is justified.

### T-010 — Run the full regression and update documentation

- **Status:** Completed 2026-11-19.
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
- **Files:** `docs/03-data/seed-list.md`, `docs/03-data/analysis-v0.3.0.md`, `docs/03-data/data-quality.md`, `docs/03-data/normalization-rules.md`, `docs/00-vision/roadmap.md`, `specs/README.md`, `AGENTS.md`, `data/README.md`, `specs/016-corpus-expansion/spec.md`, `tasks.md`.
- **Evidence:** Backend: 343 tests passed, `ruff check` and `ruff format --check` passed. Frontend: lint and typecheck passed, 118 Vitest tests passed, production build passed (the existing 958.20 kB chunk warning remains the documented E11-03 P3), 26 Playwright tests passed including nine axe scans, and the performance probe passed with the single documented view-switch exception. `docker compose config -q` passed. Documentation reflects SPEC-016 local implementation, the v0.3.0 dataset/runs, the 900-review classification limitation, the E6/E7 legacy-row limitation, the retained 1,000/2,000 graph cap and the T-011 remote-CI gate. No secrets, unrelated changes, production deployment, new dependency or unnecessary migration were found.

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
| FR-005 | T-005, T-005A |
| FR-006 | T-004, T-006 |
| FR-007 | T-004, T-007 |
| FR-008 | T-008 |
| FR-009 | T-009 |
| FR-010 | T-003, T-005, T-005A, T-006, T-007, T-008 |
| FR-011 | T-010 |
| FR-012 | T-010 |

### Non-functional requirements

| Requirement | Tasks |
|---|---|
| NFR-001 | T-005, T-005A, T-008 |
| NFR-002 | T-002, T-005 |
| NFR-003 | T-005, T-005A, T-008 |
| NFR-004 | T-005, T-005A |
| NFR-005 | T-009 |
| NFR-006 | T-004, T-006 |
| NFR-007 | T-004, T-006 |

## 5. Validation evidence

| Criterion | Result | Evidence |
|---|---|---|
| AC-001 | Passed | 453-candidate pool; all 17 leaves and six regions; pool JSON assertions. |
| AC-002 | Passed | 453 checked; 452 accepted; Hellhammer excluded; 151/151/150 batches; report and batches approved 2026-11-17. |
| AC-003 | Passed | `v0.3.0.json` loader validation; 509 bands; pointer resolves 0.3.0; v0.2.0 checksum unchanged. |
| AC-004 | Passed | T-005A dataset `mb-20261119T004940Z-9d5e75fdc1b9`: 509/509, 0 failures, normal and cache-only same version/manifest, no duplicate entity MBIDs, 7 multi-artist exclusions, v0.2.0 unchanged. |
| AC-005 | Passed | T-006 run `ed8e7e12-c181-4041-ba39-42b2bf655453`: 509 active memberships, 4,826 classified albums, 0 quarantined and 900 review cases recorded. |
| AC-006 | Passed | T-007 run `288b11ac-9a90-4b4f-bf58-fdd50e1a51ad`: 0 blocking, 0 exceptions, 1,089 medium/advisory findings and 77 coverage/completeness metrics. |
| AC-007 | Passed | T-008 E6 `eda-bd2ef42a54786c67` and E7 `net-78a54051ff047f86`; 927 metrics, 4,217/1,700 graph edges, 325 communities and v0.2 comparison recorded with legacy-row limitation. |
| AC-008 | Passed with documented exception | T-009: API/overview within targets, truncation explicit, E2E/axe pass; view-switch acknowledgement p95 2,373 ms over the 1 s control target, full settle 2,626 ms within 5 s. |
| AC-009 | Passed | T-010: backend 343 tests, frontend 118 tests, lint/typecheck/build, 26 E2E and nine axe scans passed. |
| AC-010 | Passed | T-010: SPEC-016, spec index, roadmap, AGENTS, data docs and this task file updated. |
| AC-011 | Passed | T-010 diff review: no production deployment, E12 work, new production dependency or migration. |

## 6. Notes

- The candidate pool is an accepted input, not an approved seed list. Do not point the active seed list at it.
- Wikidata enrichment must use MusicBrainz URL relationships or the Wikipedia API before attempting WDQS again.
- Do not silently drop accepted candidates. Exclude a candidate only for a documented verification failure and report it.
- Do not change taxonomy v0.2.0 in this spec.
- Do not resume E12 or perform production work in this spec.
- Record actual ingestion duration and storage size; the plan budget is one working session per major stage.
- Capture normal-run counters before the cache-only replay: a shared dataset directory is rewritten with the replay's `coverage.json` and `report.md`, even when the dataset version is unchanged.
- Exclude multi-artist release groups from the canonical dataset and report them; do not attribute them to one artist.
- Keep v0.2.0 and earlier artifacts immutable.
