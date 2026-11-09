# Technical plan — SPEC-006 Data quality and validation

- **Status:** Approved
- **Spec:** [spec.md](spec.md)
- **Tasks:** [tasks.md](tasks.md)
- **Stage:** E5
- **Module:** `quality`
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0002](../../docs/01-architecture/adr/ADR-0002-musicbrainz-primary-source.md), [ADR-0004](../../docs/01-architecture/adr/ADR-0004-release-group-model.md), [ADR-0005](../../docs/01-architecture/adr/ADR-0005-identity-and-provenance.md), [ADR-0007](../../docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md), [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)

## 1. Solution summary

SPEC-006 adds a read-only quality layer over the validated E4 normalized corpus. It evaluates structural integrity, completeness, validity, consistency and coverage; persists rules, runs, findings, exceptions and metrics; and produces JSON/Markdown reports.

The implementation has two execution levels:

1. **CI quality suite:** structural rules and rule behaviour against PostgreSQL and small fixtures. It is fast, deterministic, network-free and blocking.
2. **Full-corpus quality run:** a CLI/batch execution against the real normalized database, persisting findings and metrics for the exact dataset, taxonomy and rule-catalogue versions.

The full E3 dataset and raw cache remain outside Git. E5 never mutates canonical normalized data, never re-ingests MusicBrainz, never changes API/frontend contracts and never builds graph metrics.

```text
canonical E4 tables + normalization issues
        │
        ▼
versioned rule catalogue + exception baseline
        │
        ▼
quality runner
  structural rules · completeness metrics · coverage metrics
        │
        ├── quality_run
        ├── quality_finding + quality_exception
        ├── quality_metric
        └── JSON / Markdown report
        │
        ▼
CI gate (fixtures) + full-corpus batch gate (real data)
```

## 2. Architecture and data flow

### 2.1 CI flow

1. Load the versioned rule catalogue.
2. Validate catalogue schema and rule codes.
3. Run structural checks against a test database seeded with canonical and normalization fixtures.
4. Inject defects in tests and assert the matching blocking findings.
5. Run deterministic metric/report tests.
6. Fail CI on structural defects, invalid catalogue rules or non-deterministic output.

### 2.2 Full-corpus flow

1. Resolve the selected normalization run and dataset/taxonomy versions.
2. Load or synchronize the rule catalogue and exception baseline.
3. Create a `quality_run`.
4. Run structural checks and persist findings.
5. Compute completeness and coverage metrics; persist `quality_metric` rows.
6. Apply approved exceptions to finding/gate evaluation.
7. Write JSON/Markdown reports.
8. Finish the run with pass, advisory-only or blocked status.

### 2.3 Package layout

```text
backend/src/hmde/quality/
├── __init__.py
├── __main__.py          CLI entry point
├── cli.py               arguments, exit codes, orchestration
├── inputs.py            normalization/dataset/catalogue validation
├── catalogue.py         rule-catalogue parser and database sync
├── runner.py            quality-run lifecycle and phase orchestration
├── structural.py        structural rule implementations
├── metrics.py           completeness and coverage metrics
├── findings.py          finding persistence and idempotency
├── exceptions.py        exception baseline loading and gate evaluation
├── report.py            JSON/Markdown reports
└── queries.py           reusable read-only SQL/Alchemy queries
```

The package depends on `core`, `db`, `models` and `data/quality/` inputs. It must not import API, frontend, ETL or analytics modules.

## 3. Components and responsibilities

| Component or path | Responsibility |
|---|---|
| `backend/src/hmde/quality/` | Quality rule engine, metrics, findings, exceptions, CLI and reports. |
| `backend/src/hmde/models/quality.py` | SQLAlchemy models for catalogues, rules, runs, findings, exceptions and metrics. |
| `backend/alembic/versions/0006_quality_layer.py` | Additive quality schema migration. |
| `data/quality/rules-v0.1.0.json` | Versioned rule catalogue. |
| `data/quality/exceptions-v0.1.0.json` | Owner-approved initial exception baseline. |
| `docs/03-data/data-quality.md` | Human-readable quality dimensions, rules, gates and limitations. |
| `backend/tests/unit/test_quality_*.py` | Catalogue, structural rules, metrics and gate unit tests. |
| `backend/tests/integration/test_quality_*.py` | Migration, persistence, exceptions, CLI and fixture integration tests. |
| `README.md`, `AGENTS.md`, `data/README.md`, `docs/01-architecture/er-diagram.md` | Operational commands, data paths, current state and physical schema. |

## 4. Technical decisions and alternatives

### 4.1 Persisted quality tables

The user selected persisted tables rather than report-only findings.

New structures:

- `quality_rule_catalogue`: version, source hash, source path, status and load time.
- `quality_rule`: catalogue version + rule code, name, dimension, severity, entity scope, description, threshold, remediation and display order.
- `quality_run`: normalization run, dataset, taxonomy, rule-catalogue version, code version, status, timestamps, parameters, counters and report path.
- `quality_finding`: run, rule, deterministic finding key, entity, severity, status, observed/expected values, details and timestamps.
- `quality_exception`: rule + entity scope, reason, approver, approval date, status and optional expiry; unique per rule/entity.
- `quality_metric`: run, metric code, dimension, scope type/key, numerator, denominator, value, unit and details.

Alternative rejected: report-only findings. They would not support audit, exception matching or future cross-run analysis.

### 4.2 Versioned catalogue and exception inputs

- Rule catalogue and exception baseline are versioned JSON files under `data/quality/`.
- The catalogue has a stable version, schema version and unique rule codes.
- The exception baseline references rule code + entity type + MBID, not a transient finding UUID, so exceptions remain valid across reruns.
- The database stores a snapshot of rule metadata and the exception registry for audit.
- A catalogue change requires a version change and a new quality run.

### 4.3 Structural checks

Structural rules are implemented in Python/SQLAlchemy as read-only queries. Initial blocking rules cover:

- canonical row provenance;
- foreign-key/orphan integrity;
- MBID format and uniqueness;
- taxonomy leaf validity and version alignment;
- one primary album classification per album/taxonomy version;
- one primary band aggregate per band/taxonomy version;
- credit scope/target consistency;
- dataset membership and lifecycle consistency;
- normalization-run completeness and version alignment;
- duplicate canonical entities/classifications.

Defect tests will insert invalid rows inside rollback transactions and assert the exact rule codes.

### 4.4 Completeness and coverage

- Metrics are query-based and store numerator, denominator, value, unit and missing count.
- Completeness covers provenance, dates, country, QIDs, classification, producer coverage, credits and membership.
- Coverage covers band, decade, taxonomy leaf/family, role, scope, country, source and batch.
- Initial coverage thresholds are advisory; structural invariants are hard.
- Missing data is reported explicitly and never interpreted as negative evidence.

### 4.5 Exceptions and gate semantics

- A blocking finding without an approved exception blocks the quality gate.
- An exception records acceptance; it does not delete or downgrade the finding.
- Exceptions are versioned, owner-approved and visible in every report.
- Initial exceptions: 24 quarantined bootleg/live/demo albums, 17 medium album classifications and 17 medium aggregate cases.
- Review status is still reported even when excepted.

### 4.6 Two-level execution model

- CI runs structural checks and metrics against fixtures/test PostgreSQL.
- Ordinary CI does not require `data/raw/`, `data/ingestions/` or `data/normalization/`.
- The full-corpus quality run is a documented CLI/batch command against the normalized development database.
- Full run reports and tables include exact dataset, taxonomy, normalization-run, catalogue and code versions.
- A future CI job may provision a versioned dataset artifact; the rules and storage do not change.

### 4.7 Reports and CLI

CLI:

```bash
python -m hmde.quality run \
  --normalization-run 54d66992-643b-49ec-bac4-fe514ea39e94 \
  --rules ../data/quality/rules-v0.1.0.json \
  --exceptions ../data/quality/exceptions-v0.1.0.json \
  --output ../data/quality
```

Modes:

- default/advisory: report findings; fail only on fatal errors;
- `--strict`: fail on unexcepted blocking findings;
- `--output` selects ignored report storage.

Exit codes:

- `0`: pass;
- `2`: completed with advisory findings;
- `3`: blocked by unexcepted blocking findings;
- `1`: fatal configuration/execution error.

Reports are JSON and Markdown and include versions, counts, findings, exceptions, metrics, gate result and missing-data wording.

### 4.8 Scope boundary and idempotency

- Quality code is read-only for canonical and normalization tables.
- No API, frontend, graph, ETL or source-code changes.
- Repeated runs with the same inputs produce the same finding keys and metrics; a new run ID is the only append.
- Quality tables are append/update audit tables; historical runs are not deleted.

Alternative rejected: building quality checks inside API startup or request paths. Quality is batch, not runtime.

## 5. Data model and migrations

### 5.1 New tables

| Table | Purpose | Key constraints |
|---|---|---|
| `quality_rule_catalogue` | Versioned rule catalogue metadata. | Version PK; source hash/path; status. |
| `quality_rule` | Rule snapshot per catalogue version. | PK `(catalogue_version, code)`; dimension/severity checks. |
| `quality_run` | One quality execution. | UUID PK; normalization-run/catalogue FKs; status/timestamps; counters. |
| `quality_finding` | Persisted rule result. | UUID PK; run/rule FKs; deterministic key unique per run; severity/status checks. |
| `quality_exception` | Approved acceptance of a rule/entity finding. | UUID PK; rule/entity key unique; approver/date/reason required. |
| `quality_metric` | Completeness/coverage metric value. | UUID PK; run FK; metric code/scope unique per run. |

### 5.2 Constraints and indexes

- Rule dimension in `structural`, `completeness`, `validity`, `consistency`, `coverage`.
- Rule severity in `blocking`, `high`, `medium`, `info`.
- Run status in `running`, `completed`, `completed_with_findings`, `blocked`, `failed`.
- Finding status in `open`, `accepted`, `exceptional`, `quarantined`, `resolved`.
- Unique finding key per run/rule/entity.
- Unique exception per catalogue/rule/entity MBID.
- Indexes by run, rule, severity/status, entity MBID and metric code/scope.

### 5.3 Migration and rollback

- Additive migration `0006_quality_layer`.
- No changes to canonical, taxonomy, classification, membership or normalization tables.
- Upgrade and downgrade from an empty database and from `0005`.
- Downgrade removes only quality tables; normalized data remains intact.

## 6. API contract

No changes.

- No new endpoints.
- No request/response schema changes.
- No OpenAPI drift.
- Quality data is batch-only and not exposed through HTTP in E5.

## 7. Frontend impact

None.

- No routes, components, filters or generated types.
- No frontend build change.

## 8. Error handling and consistency

- Missing normalization run or dataset metadata: fail before creating a quality run.
- Invalid/duplicate rule catalogue: reject before running rules.
- Invalid exception (missing approver/date/reason): reject.
- Unsupported rule implementation: fail as a catalogue/configuration error.
- Orphan/provenance defects: persist finding and mark gate blocked unless excepted.
- Full dataset absent in CI: skip full-corpus integration and use fixtures; never fetch it.
- Interrupted run: mark failed/incomplete; preserve completed findings/metrics; rerun idempotently.
- Duplicate finding key: update the row within the same run rather than duplicate.
- Exception for a missing entity: keep the exception in review/quarantine state; report it.

## 9. Security and trust boundaries

- Read-only database queries for canonical/normalization data.
- Quality tables are write-only from the batch process.
- No secrets, raw payloads or tokens in reports/logs.
- Paths for catalogue, exceptions and reports are validated.
- No network access and no external source calls.
- No write HTTP surface.

## 10. Observability

- Logs include quality run ID, normalization run, dataset/taxonomy versions, rule count, finding counts, exception counts, gate result and runtime.
- `quality_run.counters` records rules, findings by severity, exceptions, metrics and blocked status.
- Reports and quality tables provide full audit evidence.
- Metrics/report files are stored under ignored `data/quality/`.

## 11. Testing strategy

| Level | What is tested | Evidence |
|---|---|---|
| Unit | Rule catalogue, checks, metrics, exception matching, gate evaluation, exit codes. | `backend/tests/unit/test_quality_*.py` |
| Integration | Migration, run lifecycle, persistence, idempotency, exceptions, CLI, scope guards. | `backend/tests/integration/test_quality_*.py` |
| Contract | OpenAPI drift and canonical data unchanged. | Existing suite and `test_openapi.py` |
| Manual | Full-corpus quality batch run and report review. | T-009 |
| CI | Fixture structural suite, network-free. | GitHub Actions |

Commands:

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
TEST_DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde_test \
  uv run pytest
```

No quality test calls an external source.

## 12. Deployment and reversibility

- Apply migration `0006` before the first quality run.
- Add `data/quality/` to `.gitignore`.
- No environment variables are required; catalogue, exceptions and output are CLI arguments with documented defaults.
- Downgrade removes quality tables only.
- Full quality reports and tables can be regenerated from the same normalized dataset and catalogue.

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Quality rules duplicate or contradict E4 validation | Define rules from normalized invariants; structural rules are explicit and independently tested. |
| Full dataset unavailable in CI | Two-level model; fixtures in CI, full-corpus batch run for evidence. |
| Coverage thresholds fail due source gaps | Advisory initially; exceptions and denominators in reports. |
| Initial exception set becomes stale | Versioned baseline; re-evaluate on new dataset/taxonomy version. |
| Quality checks mutate data by mistake | Read-only queries and scope guards. |
| Finding duplication on rerun | Deterministic finding keys per run/rule/entity. |
| Report becomes misleading | Show denominators, missing counts and exception status. |
| Migration conflicts with E4 schema | Additive migration from `0005`; no canonical changes. |

## 14. Traceability requirements → plan → tasks

| Requirement | Plan section | Tasks |
|---|---|---|
| FR-001 | 4.1, 4.6, 5 | T-003 |
| FR-002 | 4.2, 5 | T-001, T-003 |
| FR-003 | 4.3 | T-004 |
| FR-004 | 4.4 | T-005 |
| FR-005 | 4.4 | T-005 |
| FR-006 | 4.1, 4.5, 5 | T-002, T-006 |
| FR-007 | 4.5, 4.6 | T-001, T-006 |
| FR-008 | 4.7 | T-007 |
| FR-009 | 4.7 | T-007 |
| FR-010 | 4.6 | T-008, T-010 |
| FR-011 | 4.8 | T-008, T-010 |
| FR-012 | 4.8 | T-004, T-006, T-009 |

## 15. Approval and next step

This plan must be approved together with `tasks.md` before implementation starts. The first task is T-001: define the rule catalogue and initial exception baseline.
