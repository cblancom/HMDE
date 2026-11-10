# SPEC-007 — Exploratory analysis and metric definition

- **Status:** Validated
- **Stage:** E6
- **Iteration:** MVP
- **Module:** `analytics`
- **Date:** 2026-11-09
- **Depends on:** SPEC-006 validated; normalized run `54d66992-643b-49ec-bac4-fe514ea39e94`; quality run `341824ea-5d6f-4279-bae0-f66a1e696e05`; E3 dataset `mb-20261107T194927Z-0d6cedd5c261`; [taxonomy](../../data/taxonomy.json) v0.2.0
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0004](../../docs/01-architecture/adr/ADR-0004-release-group-model.md), [ADR-0005](../../docs/01-architecture/adr/ADR-0005-identity-and-provenance.md), [ADR-0007](../../docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md), [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)
- **Plan:** [plan.md](plan.md) (approved)
- **Tasks:** [tasks.md](tasks.md) (validated)
- **Conventions:** [Engineering conventions](../../docs/01-architecture/conventions.md)
- **Owner:** Cristian

## Revision history

| Revision | Date | Change |
|---|---|---|
| 1 | 2026-11-09 | Initial draft; E6 exploratory scope, Pandas authorization and report-only persistence decision |
| 2 | 2026-11-09 | Spec approved; technical plan and tasks drafted for review |
| 3 | 2026-11-09 | T-001–T-010 implemented locally; full EDA report completed; remote CI pending |
| 4 | 2026-11-09 | Remote CI run 42548567359 passed; SPEC-007 validated |

## 1. Context and problem

E5 validated the normalized corpus and its quality gates. The available corpus contains 57 seed bands, 731 canonical albums, 9,236 releases, 16,683 recordings and 32,665 credit contexts. The quality run has 58 approved exceptions: 24 quarantined bootleg/live/demo albums, 17 album classifications in review and 17 band aggregates in review.

Before building a graph or exposing analytical metrics, the project needs to understand what the normalized data actually supports. E6 must describe distributions, coverage, concentration and collaboration frequencies, identify bias and limitations, and define the metrics that E7 and E8 will later persist and expose.

The following decisions are fixed for this spec:

- Pandas may be added as a backend dependency for reproducible tabular analysis.
- E6 is **report-only**: it will not add database tables. E7 owns persistent `analysis_run` and graph/metric storage.
- Analysis is executed through a reproducible CLI that writes versioned JSON and Markdown reports under `data/analysis/`.
- The full 57-band corpus is analyzed. Known quality exceptions are reported as limitations, not hidden or treated as negative evidence.
- E6 may compute descriptive co-credit frequencies, but not graph centrality, communities or graph snapshots; those belong to E7.

```text
normalized E4 tables + quality report
        │
        ▼
E6 analysis CLI (Pandas + SQL)
  distributions · coverage · producer participation
  concentration · descriptive collaboration frequencies
        │
        ├── versioned metric catalogue
        ├── JSON metrics/results
        └── Markdown EDA report
        │
        ▼
E7 graph and persisted analytical metrics
```

E6 does not change canonical data, the API, the frontend or the database schema.

## 2. Users and actors

- **Analyst/developer:** runs the EDA, reviews distributions and defines metrics.
- **System actor:** PostgreSQL supplies normalized entities, credits, taxonomy and quality exceptions; Pandas performs local tabular aggregation.
- **Future consumers:** E7 graph construction, E8 analytical API, E9/E10 presentation and E5/E6 feedback loops.
- **Project owner:** reviews scope, metric definitions and limitations.

There are no end-user roles, authentication or write API in E6.

## 3. User stories and flows

### US-001 — Understand the corpus shape

As an analyst, I want a reproducible overview of the corpus so that I know which bands, albums, credits and periods are available.

**Expected flow:**

1. The CLI loads the selected dataset, taxonomy and quality run versions.
2. It computes counts and distributions by band, album, release, recording, decade, taxonomy leaf/family, role, scope, country, source and batch.
3. It reports denominators and missing values.
4. The result is written as versioned JSON and Markdown artifacts.

### US-002 — Identify coverage and bias

As an analyst, I want coverage differences by decade and subgenre so that I do not overinterpret the sample.

**Expected flow:**

1. Coverage metrics compare bands, albums and credits by decade and taxonomy leaf/family.
2. Missing dates, missing classifications and quarantined albums are reported explicitly.
3. Known quality exceptions are included in the limitation narrative.
4. The report states that absence is not negative evidence.

### US-003 — Describe producer participation

As an analyst, I want producer participation and concentration statistics so that later graph metrics have a defensible baseline.

**Expected flow:**

1. The analysis counts distinct albums and credits by producer/co-producer.
2. It reports leaderboards with denominators and minimum sample rules.
3. It computes concentration measures such as top-k share and HHI with explicit definitions.
4. It separates production roles from engineering, mix and mastering.

### US-004 — Describe collaborations without building the graph

As an analyst, I want descriptive co-credit frequencies so that E7 can choose graph definitions.

**Expected flow:**

1. The analysis computes counts of pairs of credited artists sharing an album or recording context.
2. It reports the most frequent pairs and the distribution of shared-album counts.
3. It labels these as descriptive co-occurrences, not causal influence or affinity.
4. It does not compute centrality, communities or graph snapshots.

### US-005 — Define metrics before implementation

As a project owner, I want a formal metric catalogue so that E7/E8 implement stable, unambiguous definitions.

**Expected flow:**

1. Each metric has a stable code, name, definition, numerator, denominator, unit, scope, filters and interpretation.
2. Metric versions are independent from dataset and taxonomy versions.
3. The EDA report references the catalogue version.
4. Ambiguous metrics are listed as open decisions, not implemented silently.

### US-006 — Reproduce the analysis

As a developer, I want to rerun the same EDA from the same inputs so that results are auditable.

**Expected flow:**

1. The run records dataset, taxonomy, quality run, metric catalogue and code versions.
2. The same inputs produce the same result files.
3. No network access is required.
4. A changed input or metric catalogue creates a new analysis version.

## 4. Functional requirements

### FR-001 — Analysis inputs and version metadata

The analysis must require:

- a completed normalized run;
- the corresponding E3 dataset version;
- taxonomy version;
- quality run or quality report version;
- metric-catalogue version;
- code version and run timestamp.

It must reject missing, incomplete or version-mismatched inputs before writing results.

**Verification:** input-validation tests and report metadata assertions.

### FR-002 — Corpus overview

The analysis must report, with denominators:

- active seed bands and canonical albums;
- releases, recordings and release–recording links;
- credits by role and scope;
- taxonomy leaves represented in album classifications;
- dataset batches and membership counts.

**Verification:** metric tests and full-corpus report inspection.

### FR-003 — Temporal distributions

The analysis must report albums and credits by decade from 1960s through 2020s, including an explicit `unknown` bucket for missing dates. It must report date precision.

**Verification:** boundary tests for 1960, 1979, 1980, 2000, 2026 and missing dates.

### FR-004 — Taxonomy distributions

The analysis must report:

- album primary labels by leaf;
- secondary labels by leaf;
- band aggregates by leaf;
- leaf-to-family roll-ups;
- classification review/quarantine counts.

Parent/family counts may be derived, but parent nodes must not be presented as album labels.

**Verification:** taxonomy roll-up and label tests.

### FR-005 — Role and scope distributions

The analysis must report credits by:

- role code;
- scope (`release_group`, `release`, `recording`);
- role category;
- role/scope combinations;
- supporting-album and supporting-recording context where available.

**Verification:** role/scope metric tests.

### FR-006 — Country, source and batch coverage

The analysis must report coverage by:

- band country;
- source;
- dataset batch;
- normalized membership.

Missing country or source values must be explicit.

**Verification:** coverage metric tests and full report review.

### FR-007 — Producer participation

The analysis must report producer/co-producer participation with:

- distinct credited artists;
- credited albums;
- credit contexts;
- bands worked with;
- top-k leaderboards;
- minimum sample or denominator disclosure.

The analysis must distinguish producer/co-producer from engineer, mix and mastering.

**Verification:** producer leaderboard and role-isolation tests.

### FR-008 — Concentration metrics

The analysis must define and compute concentration measures with documented formulas, at minimum:

- top-k share of albums or credits;
- Herfindahl–Hirschman Index (HHI);
- number of producers required to reach a stated share.

Concentration is computed over documented denominators and explicitly excludes missing credits from negative interpretation.

**Verification:** hand-calculated fixture cases and formula assertions.

### FR-009 — Descriptive collaboration frequencies

The analysis must report descriptive co-credit frequencies:

- pairs of credited artists sharing an album context;
- most frequent pairs;
- distribution of shared-album counts;
- co-credit frequencies by decade and role where sample size allows.

These are descriptive co-occurrences, not network centrality, communities or causal relationships. Sample-size thresholds must be disclosed.

**Verification:** pair-count fixture tests and report wording assertions.

### FR-010 — Coverage, bias and limitations

The analysis must produce a limitations section covering at least:

- 24 quarantined bootleg/live/demo albums;
- 17 album classifications in review;
- 17 band aggregates in review;
- missing dates, countries, QIDs or credits;
- uneven coverage by decade, subgenre and country;
- the difference between documented, inferred and missing data.

**Verification:** report assertions and exception-count checks.

### FR-011 — Versioned metric catalogue

A versioned metric catalogue must define each E6 metric with:

- stable code;
- name and description;
- numerator and denominator;
- unit;
- scope and filters;
- interpretation;
- known limitations;
- catalogue version.

The catalogue is a repository artifact (JSON) and the EDA report references its version.

**Verification:** catalogue schema/unique-code tests.

### FR-012 — EDA CLI and reports

A documented CLI must support:

- full E6 analysis;
- explicit dataset, taxonomy, quality run and metric catalogue selection;
- output directory selection;
- JSON and Markdown reports;
- stable exit codes.

The output must include run metadata, counts, distributions, coverage, concentration, collaboration summaries, limitations and metric definitions.

**Verification:** CLI tests and report snapshot/structured assertions.

### FR-013 — Determinism and reproducibility

The same database snapshot, dataset/taxonomy/quality versions, metric catalogue and code version must produce the same metrics and report content. Ordering must be deterministic. No network calls are allowed.

**Verification:** double-run comparison and network-free tests.

### FR-014 — Scope boundary

E6 must not:

- add database tables or migrations;
- modify canonical, normalization, quality or taxonomy data;
- expose API endpoints or change OpenAPI;
- change frontend routes, components or generated types;
- build graph snapshots, centrality, communities or network metrics;
- make causal claims.

E7 owns persisted analysis runs and graph metrics. E6 output is report-only.

**Verification:** migration/schema diff, OpenAPI drift, scope guards and code inspection.

## 5. Non-functional requirements

### NFR-001 — Reproducibility

Analysis inputs, metric catalogue, dataset, taxonomy, quality run and code versions must be recorded, and results must be reproducible.

### NFR-002 — Performance

A full 57-band EDA run should complete within 10 minutes on the development environment. CI fixture analyses should complete within ordinary test time.

### NFR-003 — Dependencies

Pandas is authorized for E6. Any further dependency requires explicit approval and an ADR or documented justification.

### NFR-004 — Data safety

E6 is read-only for normalized and quality data. Generated reports live outside tracked source data.

### NFR-005 — Compatibility

Python 3.13, PostgreSQL 16, Docker Compose, uv, pytest and Ruff remain supported. No Node dependency is introduced.

### NFR-006 — Security

No secrets, credentials or raw payloads are logged or written to reports. The CLI has no write HTTP surface.

### NFR-007 — Maintainability

Analysis code lives under the `analytics` boundary and depends on models/db and quality outputs, not API or frontend code. Metric definitions are explicit and independently versioned.

### NFR-008 — Language

All code, documentation, reports, metric definitions and limitations are in English.

## 6. Business rules

- **BR-001:** Missing data is not negative evidence.
- **BR-002:** E6 analyzes the full 57-band corpus and reports known quality exceptions explicitly.
- **BR-003:** Album taxonomy labels are leaves; parent nodes are roll-ups only.
- **BR-004:** Producer/co-producer metrics are distinct from engineer/mix/mastering metrics.
- **BR-005:** Co-credit frequencies are descriptive, not causal or affinity measures.
- **BR-006:** E6 does not build graph centrality, communities or snapshots; E7 owns them.
- **BR-007:** E6 does not add database schema or persist metrics in tables.
- **BR-008:** The metric catalogue is versioned and referenced by every report.
- **BR-009:** Analyses state dataset, taxonomy, quality run and catalogue versions.
- **BR-010:** No API, frontend or OpenAPI change belongs to E6.

## 7. Edge cases and errors

- Missing/incomplete normalized or quality run: fail before writing reports.
- Dataset/taxonomy/quality/catalogue version mismatch: fail with explicit reason.
- Empty corpus or empty subset: report zeros and denominators; do not divide by zero.
- Missing album dates: use `unknown`; do not impute.
- Missing country/QID: report missing coverage.
- Quarantined albums: exclude from classified-album metrics and report counts.
- Review classifications/aggregates: include with status and disclose exceptions.
- Very small producer or collaboration samples: suppress or flag unstable leaderboards.
- Duplicate or ambiguous metric definitions: reject catalogue.
- Full dataset unavailable in CI: run fixture-level metric tests; full run is a batch operation.
- Interrupted run: do not publish partial report as complete.
- Changed metric catalogue: new analysis version.

## 8. Out of scope

- Database schema changes or persisted analytical tables.
- API endpoints, OpenAPI, frontend or UI.
- Graph construction, centrality, communities or temporal network metrics.
- Causal inference or attribution of influence.
- Audio analysis, listener preferences or ratings.
- Source expansion or re-ingestion.
- Full corpus committed to Git or fetched by CI.
- Statistical significance claims beyond the available sample.

## 9. Acceptance criteria

| ID | Criterion | Evidence |
|---|---|---|
| AC-001 | Analysis validates and records dataset, taxonomy, quality and metric-catalogue versions. | Input/report tests |
| AC-002 | Corpus overview reports bands, albums, releases, recordings, credits and taxonomy coverage with denominators. | Metric tests |
| AC-003 | Temporal distribution covers 1960s–2020s and `unknown` dates with precision. | Boundary tests |
| AC-004 | Taxonomy distributions use leaf labels and family roll-ups without treating parents as album labels. | Taxonomy tests |
| AC-005 | Credits are reported by role, scope and role/scope combination. | Metric tests |
| AC-006 | Coverage is reported by country, source, batch and membership. | Coverage tests |
| AC-007 | Producer/co-producer participation and leaderboards are separated from other roles. | Producer tests |
| AC-008 | Top-k, HHI and producer-share metrics use documented formulas and denominators. | Formula tests |
| AC-009 | Descriptive co-credit frequencies include sample thresholds and non-causal wording. | Pair/wording tests |
| AC-010 | The limitations section reports the 24/17/17 quality exceptions and missing-data coverage. | Report assertions |
| AC-011 | Metric catalogue is versioned, unique and referenced by the report. | Catalogue tests |
| AC-012 | Full EDA CLI produces deterministic JSON/Markdown reports and exits with stable codes. | CLI/double-run tests |
| AC-013 | No database schema, canonical data, API, OpenAPI or frontend change occurs. | Migration/API/scope tests |
| AC-014 | Full backend tests, Ruff, format and remote CI pass. | Local and CI evidence |

## 10. Assumptions and open questions

### Assumptions

- SPEC-006 remains validated and the normalized/quality databases are available for the full run.
- Pandas may be added as an approved dependency.
- E6 analysis output is report-only; E7 owns persisted analysis tables.
- The full corpus is analyzed with quality exceptions disclosed.
- CI can test metrics with fixtures but cannot run the full ignored dataset.

### Open questions

| Question | Blocking? | Owner | Resolution |
|---|---|---|---|
| Exact minimum sample threshold for producer and collaboration leaderboards | No | Plan / E6 baseline | Define in the plan and report it in every metric. |
| Whether E6 should emit CSV in addition to JSON/Markdown | No | Plan | JSON/Markdown are required; CSV may be added if useful. |
| Which concentration denominator is primary for concentration metrics | No | Plan | Define and document album-count and credit-count variants. |
| Whether any E6 metric should be persisted for E7 reuse | No | E7 plan | E6 is report-only; E7 decides persistence. |

No blocking question remains for planning.

## 11. Validation result

- **Date:** 2026-11-09
- **Verdict:** Validated
- **Evidence:** Full EDA report `eda-1267fdcced62b7da` contains 354 metric rows for 57 bands and 731 albums, with known quality limitations disclosed. 250 tests passed; Ruff/format, OpenAPI drift and Compose validation passed. Remote CI run [42548567359](https://github.com/cblancom/HMDE/actions/runs/42548567359) passed for commit `bed26b5`. See `tasks.md`.

## 12. References

- [Constitution](../../constitution.md)
- [AGENTS.md](../../AGENTS.md)
- [Vision](../../docs/00-vision/vision.md)
- [Scope](../../docs/00-vision/scope.md)
- [Roadmap](../../docs/00-vision/roadmap.md)
- [Data model v0](../../docs/01-architecture/data-model.md)
- [Normalization rules](../../docs/03-data/normalization-rules.md)
- [Data quality rules](../../docs/03-data/data-quality.md)
- [Seed list documentation](../../docs/03-data/seed-list.md)
- [ADR-0007 — Credit scope](../../docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md)
- [ADR-0008 — Taxonomy, corpus and versioning](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)
- [SPEC-006 — Data quality](../006-data-quality/spec.md)
