# Tasks — SPEC-006 Data quality and validation

- **Status:** Implemented locally; remote CI pending
- **Spec:** [spec.md](spec.md)
- **Plan:** [plan.md](plan.md)

## 1. Execution order

```text
T-001 ──► T-002 ──► T-003 ──► T-004 ──► T-005 ──► T-006 ──► T-007 ──► T-008 ──► T-009 ──► T-010
```

T-001 and T-002 define the rule/exception inputs and persistence layer. T-003–T-007 build the runner. T-008 proves the CI path without the full dataset. T-009 executes the full-corpus quality gate. T-010 closes documentation and CI.

## 2. Tasks

### T-001 — Define the rule catalogue and initial exception baseline

- **Status:** Completed (2026-11-08).
- **Requirements:** FR-002, FR-007, BR-004, BR-009.
- **Dependencies:** SPEC-005 validated.
- **Description:** Create `data/quality/rules-v0.1.0.json`, `data/quality/exceptions-v0.1.0.json` and `docs/03-data/data-quality.md`. Define structural, completeness, validity, consistency and coverage rules with stable codes, dimensions, severities, thresholds and remediation. Register the initial owner-approved exceptions for the 24 quarantined albums, 17 album-review cases and 17 aggregate-review cases.
- **Done when:** rule codes are unique, dimensions/severities are valid, thresholds are explicit, and the baseline contains exactly 58 auditable exceptions with reason, approver and date.
- **Verification:**
  ```bash
  python3 - <<'PY'
  import json
  from pathlib import Path
  rules = json.loads(Path('data/quality/rules-v0.1.0.json').read_text())
  exceptions = json.loads(Path('data/quality/exceptions-v0.1.0.json').read_text())
  codes = [rule['code'] for rule in rules['rules']]
  assert len(codes) == len(set(codes))
  assert rules['version'] == exceptions['catalogue_version']
  assert len(exceptions['exceptions']) == 58
  assert all(item['reason'] and item['approved_by'] and item['approved_at']
             for item in exceptions['exceptions'])
  print('quality inputs OK')
  PY
  ```
- **Files:** `data/quality/rules-v0.1.0.json`, `data/quality/exceptions-v0.1.0.json`, `docs/03-data/data-quality.md`, `data/README.md`.
- **Evidence:** 2026-11-08: created a 20-rule catalogue and 58 owner-approved baseline exceptions (24 `Q-CLS-001`, 17 `Q-CLS-002`, 17 `Q-AGG-001`). Verification script passed.

### T-002 — Add quality models and migration `0006`

- **Requirements:** FR-001, FR-006, NFR-003.
- **Dependencies:** T-001.
- **Status:** Completed (2026-11-08).
- **Description:** Add models and additive migration for `quality_rule_catalogue`, `quality_rule`, `quality_run`, `quality_finding`, `quality_exception` and `quality_metric`, including constraints, indexes and reversible downgrade. No canonical or normalization table changes.
- **Done when:** migration upgrades from empty and `0005`, downgrades cleanly, and unique/check constraints enforce rule, finding, exception and metric invariants.
- **Verification:**
  ```bash
  cd backend
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run alembic upgrade head
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run alembic downgrade 0005
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run alembic upgrade head
  uv run pytest tests/unit/test_quality_models.py tests/integration/test_quality_migration.py
  ```
- **Files:** `backend/alembic/versions/0006_quality_layer.py`, `backend/src/hmde/models/quality.py`, `backend/src/hmde/models/__init__.py`, `backend/tests/unit/test_quality_models.py`, `backend/tests/integration/test_quality_migration.py`.
- **Evidence:** 2026-11-08: migration `0006` added six quality tables; `0006 → 0005 → 0006` passed on development and test databases. Model/migration tests passed (7).

### T-003 — Implement catalogue synchronization and quality-run lifecycle

- **Requirements:** FR-001, FR-002, FR-010.
- **Dependencies:** T-002.
- **Status:** Completed (2026-11-08).
- **Description:** Parse and validate the versioned catalogue, synchronize catalogue/rules to the database, validate the selected normalization run and dataset/taxonomy versions, and create/finish `quality_run` records with counters and input metadata.
- **Done when:** valid catalogues sync idempotently; invalid/duplicate rules fail; missing or mismatched normalization runs fail before quality writes; run lifecycle is deterministic.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_quality_catalogue.py tests/integration/test_quality_run.py
  ```
- **Files:** `backend/src/hmde/quality/catalogue.py`, `inputs.py`, `runner.py`, `backend/tests/unit/test_quality_catalogue.py`, `backend/tests/integration/test_quality_run.py`.
- **Evidence:** 2026-11-08: catalogue parsing/sync and quality-run lifecycle are implemented; 20-rule catalogue loads and validates; quality inputs reject missing/mismatched normalization runs. Catalogue/run tests passed (6).

### T-004 — Implement structural checks

- **Requirements:** FR-003, FR-012, BR-002.
- **Dependencies:** T-003.
- **Status:** Completed (2026-11-08).
- **Description:** Implement read-only structural rules for provenance, FKs/orphans, MBIDs, taxonomy leaves/version alignment, album and aggregate primary uniqueness, credit scope/targets, membership and normalization-run consistency. Persist findings through the common finding interface.
- **Done when:** each defect class produces the expected blocking finding; valid data produces none; checks are deterministic and read-only.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_quality_structural.py tests/integration/test_quality_structural.py
  ```
- **Files:** `backend/src/hmde/quality/structural.py`, `backend/src/hmde/quality/findings.py`, `backend/tests/integration/test_quality_structural.py`.
- **Evidence:** 2026-11-08: structural checks cover provenance, MBID validity/uniqueness, taxonomy leaves, album primary/review gaps, band aggregate review, credit scope and membership. Defect fixture test passed (1).

### T-005 — Compute completeness and coverage metrics

- **Requirements:** FR-004, FR-005, BR-001, BR-003.
- **Dependencies:** T-004.
- **Status:** Completed (2026-11-08).
- **Description:** Compute completeness metrics for provenance, dates, country, QIDs, classification, producer coverage, credits and membership; compute coverage by band, decade, taxonomy leaf/family, role, scope, country, source and batch. Persist numerator, denominator, value, unit and missing counts.
- **Done when:** metrics use real denominators, low coverage is reported as advisory, and missing data is explicitly described as missing evidence.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_quality_metrics.py tests/integration/test_quality_metrics.py
  ```
- **Files:** `backend/src/hmde/quality/metrics.py`, `backend/tests/integration/test_quality_metrics.py`.
- **Evidence:** 2026-11-08: completeness metrics cover provenance, dates, band metadata and producer coverage; coverage metrics cover decade, leaf, role, scope, country, source, batch and missing data. Metric tests passed (1).

### T-006 — Persist findings, exceptions and initial baseline

- **Requirements:** FR-006, FR-007, FR-012, BR-004, BR-009.
- **Dependencies:** T-004, T-005.
- **Status:** Completed (2026-11-08).
- **Description:** Complete deterministic finding persistence, exception loading/matching and gate evaluation. Load the 58 baseline exceptions and ensure they remain visible without deleting findings.
- **Done when:** reruns do not duplicate findings; exceptions match rule/entity across runs; invalid exceptions fail validation; baseline counts are visible in reports and tables.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_quality_exceptions.py tests/integration/test_quality_exceptions.py
  ```
- **Files:** `backend/src/hmde/quality/findings.py`, `backend/src/hmde/quality/exceptions.py`, `backend/tests/unit/test_quality_exceptions.py`, `backend/tests/integration/test_quality_exceptions.py`.
- **Evidence:** 2026-11-08: 58 baseline exceptions load and sync idempotently; gate evaluation distinguishes excepted blocking findings from unexcepted blockers. Exception/gate tests passed (3).

### T-007 — Add quality reports and CLI

- **Requirements:** FR-008, FR-009, NFR-007.
- **Dependencies:** T-006.
- **Status:** Completed (2026-11-08).
- **Description:** Add `python -m hmde.quality` with full/advisory/strict modes, catalogue/exception/output selection and stable exit codes. Write JSON/Markdown reports with versions, findings, exceptions, metrics, gate result and missing-data wording.
- **Done when:** CLI supports pass/advisory/blocked/fatal outcomes; dry/advisory modes do not mask blocking defects; reports are deterministic and secret-free.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_quality_cli.py tests/integration/test_quality_cli.py
  ```
- **Files:** `backend/src/hmde/quality/__main__.py`, `backend/src/hmde/quality/cli.py`, `backend/src/hmde/quality/report.py`, `backend/tests/unit/test_quality_cli.py`, `backend/tests/integration/test_quality_cli.py`.
- **Evidence:** 2026-11-08: quality CLI supports full/advisory/strict modes and JSON/Markdown reports; report/gate/exit-code tests passed (4).

### T-008 — Add CI fixture suite and scope guards

- **Requirements:** FR-010, FR-011, NFR-002, NFR-006.
- **Dependencies:** T-007.
- **Status:** Completed (2026-11-08).
- **Description:** Add fixture-based CI tests for structural rules, findings, exceptions, metrics and reports without the full dataset or network. Add scope guards proving quality does not import API/frontend/ETL/analytics and does not mutate canonical tables.
- **Done when:** CI path runs on test PostgreSQL with fixtures; no ignored data is required; canonical data is unchanged after quality runs; OpenAPI remains unchanged.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_quality_scope_guard.py tests/integration/test_quality_fixture.py
  ```
- **Files:** `backend/tests/unit/test_quality_scope_guard.py`, `backend/tests/integration/test_quality_fixture.py`.
- **Evidence:** 2026-11-08: quality is network-free and does not import API/ETL/analytics; fixture quality run on test PostgreSQL leaves canonical counts unchanged. CI fixture/scope tests passed (2).

### T-009 — Run the full-corpus quality gate

- **Requirements:** FR-001–FR-012, NFR-001–NFR-003.
- **Dependencies:** T-008.
- **Status:** Completed (2026-11-08).
- **Description:** Run the quality suite against normalized run `54d66992-643b-49ec-bac4-fe514ea39e94` and dataset `mb-20261107T194927Z-0d6cedd5c261` in strict mode, persist findings/metrics, register/review the 58 baseline exceptions, and produce the full JSON/Markdown report.
- **Done when:** no unexcepted blocking finding remains; all 58 baseline exceptions are persisted and visible; metrics by band/decade/leaf/role/scope/country/source/batch are present; report and run versions are exact; canonical data remains unchanged.
- **Verification:**
  ```bash
  cd backend
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run python -m hmde.quality run \
      --normalization-run 54d66992-643b-49ec-bac4-fe514ea39e94 \
      --rules ../data/quality/rules-v0.1.0.json \
      --exceptions ../data/quality/exceptions-v0.1.0.json \
      --output ../data/quality --strict
  ```
- **Files:** runtime quality tables, `data/quality/` reports, `data/quality/exceptions-v0.1.0.json` if owner review adds/removes exceptions.
- **Evidence:** 2026-11-08: strict full-corpus run `341824ea-5d6f-4279-bae0-f66a1e696e05` completed with findings: 58 findings, 58 matching exceptions, 24 blocking findings excepted, 0 unexcepted blocking findings, 34 advisory findings, 20 rules and 51 metrics. No unexcepted blocker remained; CLI exit `2` reflects advisory findings rather than a blocked gate. Report: `data/quality/341824ea-5d6f-4279-bae0-f66a1e696e05/report.json`.

### T-010 — Complete tests, documentation, scope guards and CI

- **Requirements:** FR-010–FR-012, NFR-004–NFR-009.
- **Dependencies:** T-009.
- **Status:** Completed locally (2026-11-08); remote CI pending.
- **Description:** Complete unit/integration coverage, update README/AGENTS/data docs/ER diagram/quality rules, run full backend checks, OpenAPI drift and compose validation, and record remote CI evidence.
- **Done when:** full suite, Ruff, format and OpenAPI drift pass; no API/frontend/canonical change; docs describe quality tables, rules, exceptions and two-level gates; remote CI passes after push.
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
- **Files:** `backend/tests/`, `README.md`, `AGENTS.md`, `data/README.md`, `docs/03-data/data-quality.md`, `docs/01-architecture/er-diagram.md`, `docs/README.md`, `docs/00-vision/roadmap.md`, `specs/README.md`, `specs/006-data-quality/`, `.gitignore`.
- **Evidence:** 2026-11-08: full PostgreSQL-backed suite passed 234 tests; Ruff check/format passed; OpenAPI drift was absent; `docker compose config -q` passed; documentation and ER schema updated. Remote CI is pending because no commit/push was requested.

## 3. Coverage matrix

### Functional requirements

| Requirement | Tasks |
|---|---|
| FR-001 | T-003, T-009 |
| FR-002 | T-001, T-003 |
| FR-003 | T-004 |
| FR-004 | T-005 |
| FR-005 | T-005 |
| FR-006 | T-002, T-006 |
| FR-007 | T-001, T-006, T-009 |
| FR-008 | T-007 |
| FR-009 | T-007 |
| FR-010 | T-003, T-008, T-010 |
| FR-011 | T-008, T-010 |
| FR-012 | T-004, T-006, T-009 |

### Non-functional requirements

| Requirement | Tasks |
|---|---|
| NFR-001 | T-003, T-009 |
| NFR-002 | T-008 |
| NFR-003 | T-002, T-008 |
| NFR-004 | T-006, T-010 |
| NFR-005 | T-010 |
| NFR-006 | T-008 |
| NFR-007 | T-007 |
| NFR-008 | T-010 |
| NFR-009 | T-001, T-010 |

## 4. Validation evidence

| Criterion | Result | Evidence |
|---|---|---|
| AC-001 | Passed | Quality migration `0006` upgrade/downgrade |
| AC-002 | Passed | Rule-catalogue tests |
| AC-003 | Passed | Structural defect tests |
| AC-004 | Passed | Completeness metrics |
| AC-005 | Passed | Coverage metrics |
| AC-006 | Passed | Finding/exception persistence |
| AC-007 | Passed | 58 baseline exceptions: 24 + 17 + 17 |
| AC-008 | Passed | JSON/Markdown report tests |
| AC-009 | Passed | CLI exit-code tests |
| AC-010 | Passed locally | CI fixture/scope suite |
| AC-011 | Passed | Full-corpus run 45e0ef56 |
| AC-012 | Passed | Deterministic finding keys and repeat quality runs |
| AC-013 | Passed | Scope guards, canonical no-mutation and OpenAPI drift |
| AC-014 | Passed locally; remote CI pending | 234 tests, Ruff, format |

## 5. Notes

- The full E3 dataset and raw cache remain outside Git; CI uses fixtures.
- Structural rules are blocking; coverage thresholds are advisory in the initial baseline.
- The 24 quarantined albums and 34 review cases are accepted exceptions only when persisted and visible.
- Quality runs never mutate canonical or normalization data.
- Do not mark a task complete until its verification has been executed and recorded.
