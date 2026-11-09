# Tasks — SPEC-007 Exploratory analysis and metric definition

- **Status:** Implemented locally; remote CI pending
- **Spec:** [spec.md](spec.md)
- **Plan:** [plan.md](plan.md)

## 1. Execution order

```text
T-001 ──► T-002 ──► T-003 ──► T-004 ──► T-005 ──► T-006 ──► T-007 ──► T-008 ──► T-009 ──► T-010
```

T-001 and T-002 define inputs and dependencies. T-003 loads data. T-004–T-007 compute metrics. T-008 adds the versioned report/CLI. T-009 proves CI and corpus-expansion behaviour. T-010 executes the full EDA and closes documentation.

## 2. Tasks

### T-001 — Define the metric catalogue and EDA documentation

- **Status:** Completed (2026-11-09).
- **Requirements:** FR-011, BR-008.
- **Dependencies:** SPEC-006 validated.
- **Description:** Create `data/metrics/catalogue-v0.1.0.json` and `docs/03-data/eda-metrics.md` with stable metric codes, definitions, numerator/denominator, units, scopes, filters, interpretation, limitations and minimum sample thresholds. Cover overview, temporal, taxonomy, roles, coverage, producer, concentration, collaboration and limitation metrics.
- **Done when:** codes are unique; every metric has an exact definition; parent taxonomy nodes are not labeled as albums; concentration and co-credit formulas are explicit; catalogue version is set.
- **Verification:**
  ```bash
  python3 - <<'PY'
  import json
  from pathlib import Path
  data = json.loads(Path('data/metrics/catalogue-v0.1.0.json').read_text())
  codes = [metric['code'] for metric in data['metrics']]
  assert len(codes) == len(set(codes))
  assert data['version'] == '0.1.0'
  required = {'code', 'name', 'description', 'numerator', 'denominator',
              'unit', 'scope', 'filters', 'interpretation', 'limitations'}
  assert all(required <= set(metric) for metric in data['metrics'])
  print('metric catalogue OK')
  PY
  ```
- **Files:** `data/metrics/catalogue-v0.1.0.json`, `docs/03-data/eda-metrics.md`, `data/README.md`.
- **Evidence:** 2026-11-09: created a 20-metric catalogue with unique codes, exact definitions and explicit limitations. Verification script passed.

### T-002 — Add Pandas and analysis input validation

- **Status:** Completed (2026-11-09).
- **Requirements:** FR-001, NFR-003.
- **Dependencies:** T-001.
- **Description:** Add Pandas to backend dependencies. Create `hmde.analytics` package skeleton, metric-catalogue loader and input validation for normalization run, quality run, matching versions, taxonomy and catalogue hashes. Add `data/analysis/` to `.gitignore`.
- **Done when:** valid inputs are accepted; missing/cross-linked/mismatched runs fail before output; catalogue validation rejects malformed definitions; no network is used.
- **Verification:**
  ```bash
  cd backend
  uv sync
  uv run pytest tests/unit/test_analysis_catalogue.py tests/integration/test_analysis_inputs.py
  ```
- **Files:** `backend/pyproject.toml`, `backend/src/hmde/analytics/__init__.py`, `errors.py`, `catalogue.py`, `inputs.py`, `.gitignore`, tests.
- **Evidence:** 2026-11-09: Pandas added; catalogue loader and normalization/quality/version validation implemented; mismatch and duplicate catalogue tests passed (5).

### T-003 — Build the read-only corpus dataframe loader

- **Status:** Completed (2026-11-09).
- **Requirements:** FR-001, FR-002, NFR-004.
- **Dependencies:** T-002.
- **Description:** Add read-only SQL queries that load bands, albums, releases, recordings, credits, album classifications, band aggregates, membership, quality findings/exceptions and taxonomy into Pandas dataframes. Use explicit columns and deterministic ordering.
- **Done when:** all EDA inputs are loaded without mutation; queries work on fixture and full databases; missing values remain missing; no network or raw payload access occurs.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_analysis_loader.py tests/integration/test_analysis_loader.py
  ```
- **Files:** `backend/src/hmde/analytics/loader.py`, `backend/tests/integration/test_analysis_loader.py`.
- **Evidence:** 2026-11-09: read-only Pandas loader now loads active bands, albums, credits, membership, sources, quality findings, exceptions and taxonomy; fixture loader test passed (1).

### T-004 — Implement corpus overview, temporal, taxonomy and role metrics

- **Status:** Completed (2026-11-09).
- **Requirements:** FR-002, FR-003, FR-004, FR-005, BR-003.
- **Dependencies:** T-003.
- **Description:** Implement overview counts, decade/date-precision distributions, album primary/secondary leaf and family roll-ups, band aggregate distribution and credit role/scope distributions. Every metric must carry numerator and denominator.
- **Done when:** 1960s–2020s and `unknown` dates are handled; parent taxonomy nodes are never album labels; role and scope metrics reconcile with credit counts.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_analysis_distributions.py tests/integration/test_analysis_distributions.py
  ```
- **Files:** `backend/src/hmde/analytics/metrics.py`, `backend/tests/unit/test_analysis_distributions.py`.
- **Evidence:** 2026-11-09: overview, decade/precision, leaf/family/secondary taxonomy and role/scope distributions implemented with denominators. Distribution fixture test passed (1).

### T-005 — Implement coverage, bias and limitation metrics

- **Status:** Completed (2026-11-09).
- **Requirements:** FR-006, FR-010, BR-001, BR-002.
- **Dependencies:** T-003, T-004.
- **Description:** Compute coverage by country, source, batch, band, decade and leaf/family; report missing dates, countries, QIDs and credits; include the 24 quarantine, 17 album-review and 17 aggregate-review exceptions and the missing-data interpretation warning.
- **Done when:** coverage uses real denominators; missing data is explicit; quality exceptions are visible; no low coverage is presented as negative evidence.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_analysis_limitations.py tests/integration/test_analysis_limitations.py
  ```
- **Files:** `backend/src/hmde/analytics/metrics.py`, `backend/tests/unit/test_analysis_limitations.py`.
- **Evidence:** 2026-11-09: country/source/batch coverage and missing/quality-exception limitations implemented. Coverage/limitation tests passed (2).

### T-006 — Implement producer participation and concentration

- **Status:** Completed (2026-11-09).
- **Requirements:** FR-007, FR-008, BR-004.
- **Dependencies:** T-003, T-004.
- **Description:** Compute producer/co-producer distinct albums, credits, bands worked with and leaderboards; separate producer metrics from engineer/mix/mastering. Implement top-k share, HHI and producers-to-share with documented denominators and minimum sample thresholds.
- **Done when:** leaderboards disclose denominators and thresholds; producer/co-producer roles are isolated; HHI and top-k match hand-calculated fixture cases.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_analysis_producers.py tests/integration/test_analysis_producers.py
  ```
- **Files:** `backend/src/hmde/analytics/metrics.py`, `backend/tests/unit/test_analysis_producers.py`.
- **Evidence:** 2026-11-09: producer/co-producer participation, top-10 share, HHI and producers-to-50% implemented separately from other roles. Producer tests passed (1).

### T-007 — Implement descriptive co-credit frequencies

- **Status:** Completed (2026-11-09).
- **Requirements:** FR-009, BR-005, BR-006.
- **Dependencies:** T-003, T-004.
- **Description:** Compute pairs of distinct credited artists sharing an album context, top pairs and shared-album frequency distributions, with minimum sample thresholds and by-decade/role breakdowns where stable. Explicitly label results as descriptive, not centrality/community/affinity.
- **Done when:** pairs are deduplicated and deterministic; sample thresholds are disclosed; no graph centrality/community code is introduced; report wording is non-causal.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_analysis_collaboration.py tests/integration/test_analysis_collaboration.py
  ```
- **Files:** `backend/src/hmde/analytics/metrics.py`, `backend/tests/unit/test_analysis_collaboration.py`.
- **Evidence:** 2026-11-09: co-credit pairs require at least two shared albums, are sorted deterministically and are labelled descriptive/non-causal. Collaboration test passed (1).

### T-008 — Add the versioned report, manifest and EDA CLI

- **Status:** Completed (2026-11-09).
- **Requirements:** FR-001, FR-012, FR-013, NFR-001, BR-007.
- **Dependencies:** T-004, T-005, T-006, T-007.
- **Description:** Implement JSON, Markdown and manifest output; derive `analysis_version` from input/catalogue/code hashes; add the `python -m hmde.analytics` CLI with explicit versions and stable exit codes. Ensure same inputs are idempotent and differing content is never overwritten.
- **Done when:** reports include all versions, metrics and limitations; analysis version is deterministic; old directories remain untouched; CLI handles success/advisory/fatal exits.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_analysis_report.py tests/integration/test_analysis_cli.py
  ```
- **Files:** `backend/src/hmde/analytics/report.py`, `runner.py`, `cli.py`, `__main__.py`, `metrics.py`, tests.
- **Evidence:** 2026-11-09: versioned report/manifest and CLI implemented; same inputs reused the same analysis version; report/CLI tests passed (3).

### T-009 — Add CI fixture tests, scope guards and corpus-expansion replay

- **Status:** Completed (2026-11-09).
- **Requirements:** FR-013, FR-014, NFR-002, NFR-006.
- **Dependencies:** T-008.
- **Description:** Add fixture-level metric tests without the full dataset, scope guards for no API/ETL/frontend/graph imports or mutations, and a corpus-expansion test that uses a changed dataset version to assert a new analysis version is created while the previous reports remain untouched.
- **Done when:** CI path runs without ignored data/network; same inputs are deterministic; new dataset versions produce new analysis directories; no canonical/API/frontend/schema changes occur.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_analysis_scope_guard.py tests/integration/test_analysis_expansion.py
  ```
- **Files:** `backend/tests/unit/test_analysis_scope_guard.py`, `backend/tests/unit/test_analysis_expansion.py`.
- **Evidence:** 2026-11-09: scope guard and corpus-expansion replay tests passed (2); changed dataset versions create new analysis directories without rewriting prior reports.

### T-010 — Run the full EDA, document results and close CI

- **Status:** Completed locally (2026-11-09); remote CI pending.
- **Requirements:** FR-001–FR-014, NFR-001–NFR-008.
- **Dependencies:** T-009.
- **Description:** Run E6 against normalization run `54d66992-643b-49ec-bac4-fe514ea39e94` and quality run `341824ea-5d6f-4279-bae0-f66a1e696e05`, review distributions/coverage/concentration/collaboration, update README/AGENTS/docs/roadmap/spec index, run full checks and record remote CI.
- **Done when:** full EDA report and manifest exist with exact versions; limitations are reviewed; full suite/Ruff/format/OpenAPI pass; no schema/API/frontend change; docs describe the metrics and corpus-expansion replay; remote CI passes.
- **Verification:**
  ```bash
  cd backend
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run python -m hmde.analytics run \
      --normalization-run 54d66992-643b-49ec-bac4-fe514ea39e94 \
      --quality-run 341824ea-5d6f-4279-bae0-f66a1e696e05 \
      --taxonomy ../data/taxonomy.json \
      --metric-catalogue ../data/metrics/catalogue-v0.1.0.json \
      --output ../data/analysis

  uv run ruff check .
  uv run ruff format --check .
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
  TEST_DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde_test \
    uv run pytest
  cd ..
  docker compose config -q
  ```
- **Files:** `data/analysis/` runtime artifacts, `README.md`, `AGENTS.md`, `data/README.md`, `docs/03-data/eda-metrics.md`, `docs/README.md`, `docs/00-vision/roadmap.md`, `specs/README.md`, `specs/007-eda-metrics/`, `.gitignore`.
- **Evidence:** 2026-11-09: full EDA `eda-1267fdcced62b7da` completed against normalization run `54d66992-643b-49ec-bac4-fe514ea39e94` and quality run `341824ea-5d6f-4279-bae0-f66a1e696e05` with 354 metric rows; report/manifest generated. Full suite passed 250 tests; Ruff/format, OpenAPI drift and Compose validation passed. Remote CI is pending.

## 3. Coverage matrix

### Functional requirements

| Requirement | Tasks |
|---|---|
| FR-001 | T-002, T-008, T-010 |
| FR-002 | T-003, T-004 |
| FR-003 | T-004 |
| FR-004 | T-004 |
| FR-005 | T-004 |
| FR-006 | T-005 |
| FR-007 | T-006 |
| FR-008 | T-006 |
| FR-009 | T-007 |
| FR-010 | T-005 |
| FR-011 | T-001, T-002 |
| FR-012 | T-008 |
| FR-013 | T-008, T-009 |
| FR-014 | T-009, T-010 |

### Non-functional requirements

| Requirement | Tasks |
|---|---|
| NFR-001 | T-008, T-009 |
| NFR-002 | T-009, T-010 |
| NFR-003 | T-002 |
| NFR-004 | T-003, T-009 |
| NFR-005 | T-010 |
| NFR-006 | T-009 |
| NFR-007 | T-010 |
| NFR-008 | T-001, T-010 |

## 4. Validation evidence

| Criterion | Result | Evidence |
|---|---|---|
| AC-001 | Pending | Input/report metadata tests |
| AC-002 | Passed | Corpus overview metrics |
| AC-003 | Passed | Temporal boundary tests |
| AC-004 | Passed | Taxonomy distribution tests |
| AC-005 | Passed | Role/scope tests |
| AC-006 | Passed | Coverage tests |
| AC-007 | Passed | Producer tests |
| AC-008 | Passed | Concentration formula tests |
| AC-009 | Passed | Collaboration tests |
| AC-010 | Passed | Limitations report |
| AC-011 | Passed | Catalogue tests |
| AC-012 | Passed | CLI/determinism tests |
| AC-013 | Passed | Scope guards and OpenAPI drift |
| AC-014 | Passed locally; remote CI pending | 250 tests, Ruff, format |

## 5. Notes

- E6 is report-only; no migration or analysis tables.
- Pandas is authorized; no additional dependency without approval.
- Full corpus EDA is a batch run because the dataset and raw cache are outside Git.
- Corpus expansion must create a new analysis version and never overwrite an older report.
- Do not mark a task complete until its verification has been executed and recorded.
