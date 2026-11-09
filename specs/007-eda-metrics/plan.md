# Technical plan — SPEC-007 Exploratory analysis and metric definition

- **Status:** Approved
- **Spec:** [spec.md](spec.md)
- **Tasks:** [tasks.md](tasks.md)
- **Stage:** E6
- **Module:** `analytics`
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0004](../../docs/01-architecture/adr/ADR-0004-release-group-model.md), [ADR-0005](../../docs/01-architecture/adr/ADR-0005-identity-and-provenance.md), [ADR-0007](../../docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md), [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)

## 1. Solution summary

SPEC-007 adds a reproducible, report-only exploratory analysis layer over the validated E4/E5 corpus. A CLI loads explicit dataset, normalization, taxonomy, quality and metric-catalogue versions; computes descriptive distributions, coverage, producer participation, concentration and co-credit frequencies with Pandas and read-only SQL; and writes JSON/Markdown artifacts under `data/analysis/`.

E6 adds no database schema and does not expose an API. E7 owns persisted analysis runs and graph metrics. The implementation records enough metadata to reproduce an EDA version and to create a new, non-overwriting analysis when the corpus grows.

```text
normalized E4 tables + quality E5 tables
        │
        ▼
analysis input validation
  dataset · normalization · taxonomy · quality · metric catalogue
        │
        ▼
read-only Pandas dataframes
        │
        ├── overview · temporal · taxonomy · roles
        ├── coverage · limitations
        ├── producer participation · concentration
        └── descriptive co-credit frequencies
        │
        ▼
versioned JSON metrics + Markdown EDA report
```

## 2. Architecture and data flow

1. Resolve explicit normalization run, quality run, taxonomy and metric-catalogue versions.
2. Validate that the quality run belongs to the normalization run and that dataset/taxonomy versions match.
3. Load normalized and quality data into Pandas dataframes using read-only SQL.
4. Compute a deterministic analysis payload from the metric catalogue.
5. Write a versioned report directory and manifest.
6. Never overwrite an existing analysis with different inputs.

### Package layout

```text
backend/src/hmde/analytics/
├── __init__.py
├── __main__.py          CLI entry point
├── cli.py               options, orchestration and exit codes
├── catalogue.py         metric-catalogue loading and validation
├── inputs.py            normalization/quality/version validation
├── loader.py            read-only SQL → Pandas dataframes
├── overview.py          corpus overview
├── temporal.py          decade and precision distributions
├── taxonomy.py          leaf/family and aggregate distributions
├── credits.py           role/scope distributions
├── coverage.py          country/source/batch/band coverage
├── producers.py         producer participation and concentration
├── collaboration.py     descriptive co-credit frequencies
├── limitations.py       quality exceptions and bias narrative
├── metrics.py           metric payload assembly
├── report.py            JSON/Markdown/manifest writer
└── runner.py            end-to-end analysis orchestration
```

The package depends on `models`, `db`, `core` and quality outputs. It must not import API, frontend, ETL or graph code.

## 3. Components and responsibilities

| Component or path | Responsibility |
|---|---|
| `backend/src/hmde/analytics/` | EDA loading, metrics, reports and CLI. |
| `data/metrics/catalogue-v0.1.0.json` | Versioned metric definitions. |
| `docs/03-data/eda-metrics.md` | Metric definitions, formulas, thresholds and limitations. |
| `data/analysis/` | Ignored runtime reports; never tracked. |
| `backend/pyproject.toml` | Add Pandas with owner authorization. |
| `backend/tests/unit/test_analysis_*.py` | Formula, catalogue and report unit tests. |
| `backend/tests/integration/test_analysis_*.py` | CLI, input, persistence and expansion tests. |
| `README.md`, `AGENTS.md`, `docs/README.md`, `docs/00-vision/roadmap.md`, `specs/README.md` | Commands, status and limitations. |

## 4. Technical decisions and alternatives

### 4.1 Report-only E6

- E6 does not create `analysis_run` or metric tables.
- Outputs are versioned JSON/Markdown reports and a manifest.
- E7 owns persisted analytical state and graph metrics.
- Old analysis versions remain readable and are never overwritten.

Alternative rejected: adding `analysis_run` now. It would mix E6 metric definition with E7 graph persistence and require schema churn before the graph model exists.

### 4.2 Explicit versioned inputs

The CLI requires:

- `--normalization-run` UUID;
- `--quality-run` UUID;
- `--taxonomy` path;
- `--metric-catalogue` path;
- `--output` directory.

Validation checks normalization status, quality status, matching normalization run, dataset/taxonomy versions, catalogue version and source hashes.

Alternative rejected: reading the latest database state implicitly. It would make reports irreproducible and silently change results after corpus growth.

### 4.3 Metric catalogue

`data/metrics/catalogue-v0.1.0.json` contains stable metric codes and definitions:

- `EDA-CORPUS-*`: counts and overview;
- `EDA-TIME-*`: decade/date precision;
- `EDA-TAX-*`: leaf/family distributions;
- `EDA-ROLE-*`: role/scope distributions;
- `EDA-COV-*`: coverage by country/source/batch;
- `EDA-PROD-*`: producer participation;
- `EDA-CONC-*`: concentration;
- `EDA-COLLAB-*`: descriptive co-credit frequencies;
- `EDA-LIM-*`: limitations and quality exceptions.

Each definition includes code, name, description, numerator, denominator, unit, scope, filters, interpretation, limitations and minimum sample size where applicable. A catalogue change requires a version change.

### 4.4 Pandas data loading

- Add Pandas to backend dependencies.
- Load only the columns needed by E6 with SQLAlchemy `read_sql`/explicit queries.
- Keep all queries read-only.
- Normalize IDs/codes/dates in dataframes once.
- Use deterministic sorting before writing metrics.
- No network calls and no raw payloads.

Alternative rejected: ad-hoc SQL for every report. Pandas makes distributions and pair aggregation maintainable and testable.

### 4.5 Metric definitions

- Counts always include numerator and denominator.
- Decades include `1960s`–`2020s` and `unknown`; no date imputation.
- Parent taxonomy nodes are roll-ups only; album labels must be leaves.
- Producer/co-producer metrics are separated from engineer/mix/mastering.
- HHI = sum of squared producer shares over distinct credited albums, range `0..1`.
- Top-k share is computed over producer-credited albums, with `k` documented in the catalogue.
- Co-credit pairs count distinct album contexts shared by two credited artists; pairs below the minimum shared-album threshold are suppressed.
- Descriptive co-credit frequencies are explicitly non-causal and non-affinity metrics.

### 4.6 Analysis versioning and corpus growth

- `analysis_version` is a deterministic hash of dataset version, normalization run, taxonomy version, quality run, metric-catalogue hash and code version.
- Output directory: `data/analysis/<analysis_version>/`.
- Manifest records all input versions, hashes, row counts, timestamps and file checksums.
- Same inputs produce the same metric/report content; the generated timestamp is excluded from the reproducibility comparison.
- A corpus expansion produces a new dataset/normalization/quality version and therefore a new analysis version.
- Existing analysis directories are immutable; a content conflict fails instead of overwriting.

### 4.7 Report and CLI

CLI:

```bash
python -m hmde.analytics run \
  --normalization-run 54d66992-643b-49ec-bac4-fe514ea39e94 \
  --quality-run 341824ea-5d6f-4279-bae0-f66a1e696e05 \
  --taxonomy ../data/taxonomy.json \
  --metric-catalogue ../data/metrics/catalogue-v0.1.0.json \
  --output ../data/analysis
```

Exit codes:

- `0`: analysis completed;
- `1`: fatal input/execution error;
- `2`: completed with advisory limitations (for example unstable small samples).

Reports are JSON, Markdown and a manifest. No CSV is required in the first version.

### 4.8 Scope boundary

- No database migration or analytical table.
- No canonical/normalization/quality mutation.
- No API/OpenAPI/frontend.
- No graph construction, centrality, communities or graph snapshots.
- No causal or affinity claims.

## 5. Data model and migrations

- No migration.
- Read-only queries against:
  - normalized entities/credits/classifications/membership;
  - quality findings/exceptions/metrics;
  - taxonomy and reference inputs.
- Runtime output lives outside tracked data under `data/analysis/`.
- Add `data/analysis/` to `.gitignore`.

## 6. API contract

No changes.

- No endpoints.
- No request/response schemas.
- No OpenAPI drift.
- Analysis artifacts are CLI/report only.

## 7. Frontend impact

None.

- No routes, components, generated types or build changes.

## 8. Error handling and consistency

- Missing normalization/quality run: fail before output.
- Version mismatch or invalid catalogue: fail with explicit reason.
- Empty dataset: write zero-count metrics and limitations; never divide by zero.
- Missing dates: `unknown`; no imputation.
- Missing country/QID/credits: report missing coverage.
- Small samples: suppress or flag unstable leaderboards and co-credit pairs.
- Existing analysis version with different content: fail; never overwrite.
- Interrupted run: no completed manifest; rerun safely.
- No network access.

## 9. Security and trust boundaries

- Read-only database access.
- No secrets or raw payloads in reports.
- Output/input paths validated.
- No write HTTP surface.
- Quality and normalization provenance remain visible in report metadata.

## 10. Observability

- Logs include analysis version, dataset/normalization/quality versions, catalogue version, runtime, row counts and output path.
- Report manifest records input hashes, counts, code version and file checksums.
- Generated metrics are reproducible and sorted deterministically.

## 11. Testing strategy

| Level | What is tested | Evidence |
|---|---|---|
| Unit | Metric catalogue, decade/taxonomy/role distributions, concentration formulas, co-credit pairs, limitations. | `backend/tests/unit/test_analysis_*.py` |
| Integration | Input validation, read-only loading, CLI, manifest, no-overwrite, corpus-expansion replay. | `backend/tests/integration/test_analysis_*.py` |
| Contract | OpenAPI drift and no schema/canonical change. | Existing suite and scope tests |
| Manual | Full 57-band EDA run and report review. | T-010 |
| CI | Fixture-level analysis, no full dataset/network. | GitHub Actions |

Commands:

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
TEST_DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde_test \
  uv run pytest
```

## 12. Deployment and reversibility

- Add Pandas dependency and sync the environment.
- No migration.
- Add `data/analysis/` to `.gitignore`.
- Old analysis reports are never deleted or overwritten.
- Removing the code leaves normalized/quality data untouched.

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Corpus expansion overwrites old results | Analysis version is input-derived; existing directories are immutable. |
| Metrics definitions drift | Versioned catalogue; report references catalogue version. |
| Missing data overinterpreted | Denominators, missing counts and limitations in every report. |
| Small-sample leaderboards mislead | Minimum sample thresholds and advisory flags. |
| Pandas query volume becomes slow | Select only required columns; aggregate in SQL where useful; 10-minute full-run target. |
| Analysis accidentally mutates data | Read-only queries and scope guards. |
| Reports contain secrets/raw data | No raw payloads; output validation and review. |
| Full dataset unavailable in CI | Fixture metric tests; full EDA is a manual/batch run. |

## 14. Traceability requirements → plan → tasks

| Requirement | Plan section | Tasks |
|---|---|---|
| FR-001 | 4.2, 4.6 | T-002, T-009 |
| FR-002 | 4.5 | T-004 |
| FR-003 | 4.5 | T-004 |
| FR-004 | 4.5 | T-004 |
| FR-005 | 4.5 | T-004 |
| FR-006 | 4.5 | T-005 |
| FR-007 | 4.5 | T-006 |
| FR-008 | 4.5 | T-006 |
| FR-009 | 4.5 | T-007 |
| FR-010 | 4.5 | T-005 |
| FR-011 | 4.3 | T-001, T-003 |
| FR-012 | 4.7 | T-008 |
| FR-013 | 4.6 | T-008, T-009 |
| FR-014 | 4.8 | T-009, T-010 |

## 15. Approval and next step

This plan must be approved together with `tasks.md` before implementation. The first task is T-001: define the metric catalogue and EDA documentation.
