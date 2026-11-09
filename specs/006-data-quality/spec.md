# SPEC-006 — Data quality and validation

- **Status:** Implemented
- **Stage:** E5
- **Iteration:** MVP
- **Module:** `quality`
- **Date:** 2026-11-08
- **Depends on:** SPEC-005 validated; normalized corpus run `54d66992-643b-49ec-bac4-fe514ea39e94`; E3 dataset `mb-20261107T194927Z-0d6cedd5c261`; [taxonomy](../../data/taxonomy.json) v0.2.0; [ADR-0005](../../docs/01-architecture/adr/ADR-0005-identity-and-provenance.md); [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0002](../../docs/01-architecture/adr/ADR-0002-musicbrainz-primary-source.md), [ADR-0004](../../docs/01-architecture/adr/ADR-0004-release-group-model.md), [ADR-0005](../../docs/01-architecture/adr/ADR-0005-identity-and-provenance.md), [ADR-0007](../../docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md), [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)
- **Plan:** [plan.md](plan.md) (approved)
- **Tasks:** [tasks.md](tasks.md) (implemented locally; remote CI pending)
- **Conventions:** [Engineering conventions](../../docs/01-architecture/conventions.md)
- **Owner:** Cristian

## Revision history

| Revision | Date | Change |
|---|---|---|
| 1 | 2026-11-08 | Initial draft; E5 quality dimensions, persisted findings and two-level CI model |
| 2 | 2026-11-08 | Spec approved; technical plan and tasks drafted for review |
| 3 | 2026-11-08 | T-001–T-010 implemented locally; full quality run completed; remote CI pending |

## 1. Context and problem

E4 validated the canonical corpus: 57 seed bands, 731 albums, 9,236 releases, 16,683 recordings, 32,665 credit contexts, 1,341 album-classification rows and 57 band aggregates. The validated normalization run is `54d66992-643b-49ec-bac4-fe514ea39e94`.

That run also exposes known gaps:

- 24 bootleg/live/demo release groups are explicitly quarantined from classification;
- 17 albums are in medium-confidence review;
- 17 bands have an aggregate in review;
- 58 normalization issues remain by design;
- source coverage varies by band, decade and subgenre.

The project needs a repeatable quality layer before E6 analyses. It must distinguish structural defects from expected source gaps, make exceptions explicit and auditable, measure coverage, and prevent missing data from being interpreted as negative evidence.

The real E3 dataset and raw cache are intentionally ignored by Git. CI cannot run quality checks over the full corpus unless the data is provisioned separately. The accepted model is two-level:

1. **CI quality suite:** structural invariants and rule behaviour against PostgreSQL and small versioned fixtures. This is a hard gate.
2. **Full-corpus quality run:** an operator/batch execution against the real normalized dataset and taxonomy, with persisted quality tables and reports. It is reproducible by dataset/taxonomy/code version but is not initially part of CI.

```text
canonical E4 tables + normalization issues
        │
        ▼
quality rule catalogue
  structural · completeness · validity · consistency · coverage
        │
        ├── quality_run
        ├── quality_finding + quality_exception
        ├── quality_metric
        └── JSON / Markdown report
        │
        ▼
CI hard gate (fixtures) + full-corpus batch gate (real data)
```

E5 measures and reports. It does not repair normalized data, change the API contract or build analytical graphs.

## 2. Users and actors

- **Data operator/developer:** runs the quality suite, reviews findings and approves exceptions.
- **System actor:** PostgreSQL supplies canonical data, taxonomy, classifications, membership and normalization issues; the quality runner persists findings and metrics.
- **Implementation agent:** works from this spec, the plan, tasks, constitution and ADRs.
- **Future consumers:** E6 exploratory analysis, E7 graph construction, E8 API and E9 frontend use quality reports and approved exceptions.

There are no end-user roles, authentication or write API in E5. Quality checks are batch/CLI processes.

## 3. User stories and flows

### US-001 — Run structural quality checks

As a data operator, I want hard structural checks so that invalid normalized data cannot feed analyses.

**Expected flow:**

1. The operator selects a normalization run or dataset version.
2. The quality runner validates FKs, uniqueness, provenance, taxonomy leaves, classification primaries, aggregate primaries, credit targets and membership.
3. Blocking findings are persisted when defects exist.
4. The run fails its quality gate if any blocking finding is not covered by an approved exception.

### US-002 — Measure completeness and coverage

As an analyst, I want completeness and coverage metrics so that I understand which questions the data can answer.

**Expected flow:**

1. The runner computes metrics by band, decade, taxonomy leaf, role, scope, country and source.
2. It reports denominators and missing counts, not only percentages.
3. Coverage limitations are visible in the report.
4. Advisory thresholds do not fail CI during the first E5 baseline.

### US-003 — Review findings and exceptions

As a data operator, I want persistent findings and an exception registry so that known gaps are explicit and auditable.

**Expected flow:**

1. Findings are stored with rule, entity, observed/expected values, severity and status.
2. The initial 24 quarantined albums, 17 album-review cases and 17 aggregate-review cases are registered as approved exceptions with reasons.
3. An exception requires approver, date and scope.
4. The same finding is not duplicated across repeated runs.

### US-004 — Reproduce a quality run

As a developer, I want quality runs to reference exact versions so that a report can be reproduced.

**Expected flow:**

1. Every quality run records dataset version, taxonomy version, normalization run, rule-catalogue version and code version.
2. Re-running the same inputs produces the same findings and metrics.
3. A changed rule catalogue or dataset creates a new quality run.
4. Reports are stored under the configured quality output path and never edit canonical data.

### US-005 — Use the two-level quality gate

As a maintainer, I want fast CI checks without committing the full dataset.

**Expected flow:**

1. CI runs structural rules and rule behaviour against fixtures.
2. CI fails on structural defects, invalid rules or non-deterministic outputs.
3. The full-corpus quality command runs against the real normalized database.
4. Full-corpus structural findings and approved exceptions determine the batch gate.
5. Coverage metrics are reported as advisory evidence, not as an automatic CI failure.

## 4. Functional requirements

### FR-001 — Quality inputs and run identity

The quality runner must validate and record:

- normalization run identifier;
- E3 dataset version and seed-list version;
- taxonomy version and tag-map/override versions;
- code version and quality rule-catalogue version;
- start/end timestamps and terminal status;
- input row counts and rule count.

A quality run must not start against a missing, stale or version-mismatched normalization run.

**Verification:** input-validation and run-metadata tests.

### FR-002 — Versioned quality rule catalogue

Quality rules must be defined in a versioned catalogue with:

- stable rule code;
- name and dimension (`structural`, `completeness`, `validity`, `consistency`, `coverage`);
- severity (`blocking`, `high`, `medium`, `info`);
- scope/entity type;
- description and expected invariant;
- threshold or metric definition when applicable;
- remediation guidance;
- rule version.

Rules are code/config artifacts, not ad-hoc SQL embedded in reports. A rule change requires a catalogue version change.

**Verification:** catalogue schema, uniqueness and version tests.

### FR-003 — Structural integrity checks

Structural rules must detect at least:

- orphan canonical rows or broken FKs;
- canonical rows without `source_record` provenance;
- duplicate or malformed MBIDs;
- duplicate canonical artist/album/release/recording identities;
- taxonomy references that are unknown or not assignable leaves;
- more than one primary album classification per album/taxonomy version;
- more than one primary band aggregate per band/taxonomy version;
- album classifications or aggregates without a taxonomy version;
- credit scope/target inconsistencies;
- membership rows whose lifecycle is inconsistent;
- missing active-band membership;
- normalization runs marked complete with missing required summary data.

Any unexcepted structural finding is blocking.

**Verification:** tests that inject each defect and assert a blocking finding.

### FR-004 — Completeness metrics

The suite must measure at least:

- canonical rows with provenance;
- albums with dates and date precision;
- bands with country and Wikidata QID;
- albums with at least one primary classification;
- albums with producer/co-producer credits;
- bands with an aggregate;
- credits with role, scope and target;
- memberships with batch and seed-list version;
- counts of missing values by entity and field.

Metrics must expose numerator, denominator, unit and missing count.

**Verification:** metric tests with controlled fixtures and full-corpus report inspection.

### FR-005 — Coverage metrics

The suite must report coverage by:

- band;
- decade (1960s–2020s);
- taxonomy leaf and parent family;
- role and credit scope;
- country;
- source;
- dataset batch.

Coverage must show denominators and must not present low coverage as negative evidence. Full-corpus coverage is advisory in the initial E5 baseline.

**Verification:** coverage metric tests and report assertions.

### FR-006 — Persisted findings and exceptions

Quality results must be persisted in tables:

- `quality_rule` or equivalent rule metadata;
- `quality_run`;
- `quality_finding`;
- `quality_exception`;
- `quality_metric`.

Findings must include run, rule, entity type/ID/MBID, severity, status, observed value, expected value, details and timestamps. Findings are idempotent per run/rule/entity key. Exceptions reference a finding or rule/entity scope and record reason, approver and approval date.

**Verification:** migration, uniqueness, idempotency and exception-audit tests.

### FR-007 — Initial exception baseline

The first full quality run must register the known E4 baseline as exceptions, not hide it:

- 24 quarantined bootleg/live/demo release groups;
- 17 medium-confidence album classifications;
- 17 medium-confidence band aggregate cases;
- any additional finding explicitly approved by the owner.

Exceptions must have a reason and must be visible in the report. An exception does not delete the finding.

**Verification:** baseline exception test and exception counts in the report.

### FR-008 — Quality report

The suite must write JSON and Markdown reports containing:

- run and version metadata;
- counts by dimension, severity and status;
- findings grouped by rule and entity type;
- approved exceptions and their reasons;
- completeness and coverage metrics with denominators;
- blocking-gate result;
- missing-data wording;
- runtime and rule count.

Reports must not contain secrets or raw payloads.

**Verification:** report snapshot/structured assertions.

### FR-009 — Quality CLI and exit codes

A documented CLI must support:

- full quality run against a selected normalization run/dataset;
- rule catalogue selection;
- output directory selection;
- strict mode that fails on unexcepted blocking findings;
- advisory mode that reports without failing;
- stable exit codes for pass, advisory findings, blocking findings and fatal errors.

**Verification:** parser, exit-code and end-to-end fixture tests.

### FR-010 — Two-level execution model

- CI must run structural rules and rule behaviour against fixtures/test PostgreSQL without network access.
- CI must not require `data/raw/`, `data/ingestions/` or `data/normalization/`.
- Full-corpus quality execution must be a documented batch/CLI operation against the provisioned normalized database.
- Full-corpus findings must be persisted and reported with exact dataset/taxonomy versions.
- The model must allow a future CI job to provision a versioned dataset artifact without redesigning the rules.

**Verification:** CI fixture tests, full-run evidence and documentation review.

### FR-011 — Scope boundary: measure, do not mutate

E5 must not:

- modify canonical entities, credits, classifications, aggregates or membership;
- delete or rewrite normalization issues;
- re-ingest MusicBrainz or fetch external sources;
- change API schemas, endpoints or OpenAPI;
- change frontend routes, components or generated types;
- build graph metrics, communities or analytical runs.

Corrections belong to E3/E4 or a new dataset/classification version.

**Verification:** scope-guard tests, OpenAPI drift check and canonical-data diff.

### FR-012 — Determinism and idempotency

The same normalized dataset, taxonomy, rule catalogue and code version must produce the same findings and metrics. Repeated runs must not duplicate findings or exceptions. A rule or data version change creates a new quality run.

**Verification:** double-run and ordering tests.

## 5. Non-functional requirements

### NFR-001 — Reproducibility

Quality runs and reports must record all input versions and be reproducible from the normalized database and rule catalogue.

### NFR-002 — Two-level performance

CI structural checks should complete with the backend suite in ordinary CI time. A full 57-band quality run should complete within 10 minutes on the development environment.

### NFR-003 — Data safety

E5 is read-only for canonical and normalization data. Quality tables are append/update audit tables; historical findings are not silently deleted.

### NFR-004 — Provenance and auditability

Every finding and exception must be attributable to a quality run, rule version, entity and approver where applicable.

### NFR-005 — Compatibility

Python 3.13, PostgreSQL 16, Docker Compose, uv, pytest and Ruff remain supported. No Node dependency is introduced.

### NFR-006 — Security

No secrets or credentials are committed or logged. Reports and logs must not contain raw payloads or tokens. The batch process has no write HTTP surface.

### NFR-007 — Observability

Runs log rule counts, findings by severity, exceptions, metrics, runtime and final gate result. Reports capture the same information.

### NFR-008 — Maintainability

Quality logic lives under the `quality` boundary and depends on models/db and versioned rule inputs. Rules are isolated, testable and independently versioned.

### NFR-009 — Language

All code, documentation, reports, error messages and exception reasons are in English.

## 6. Business rules

- **BR-001:** Missing data is not negative evidence.
- **BR-002:** Structural invariants are mandatory; unexcepted structural defects block the quality gate.
- **BR-003:** Coverage metrics are advisory during the initial E5 baseline.
- **BR-004:** Every finding and exception is persisted and auditable.
- **BR-005:** Quality runs never mutate normalized or analytical data.
- **BR-006:** The full E3 dataset and raw cache remain outside Git and outside ordinary CI.
- **BR-007:** CI uses fixtures and test PostgreSQL for structural rules.
- **BR-008:** A quality run references dataset, taxonomy, normalization-run, rule-catalogue and code versions.
- **BR-009:** An exception does not delete or downgrade a finding; it records an approved acceptance.
- **BR-010:** A rule or data version change requires a new quality run.
- **BR-011:** No API, frontend or graph change is part of E5.
- **BR-012:** Corrections create new E3/E4 versions; E5 only reports.

## 7. Edge cases and errors

- Normalization run missing or not complete: fail before creating a quality run.
- Dataset/taxonomy/rule version mismatch: fail with explicit reasons.
- Empty canonical database: report zero metrics and blocking completeness findings; do not fabricate coverage.
- Full dataset absent in CI: skip full-corpus tests and run fixture rules; never fail for the absence of ignored data.
- Rule catalogue duplicate code or invalid dimension/severity: reject the catalogue.
- Finding repeats across runs: reuse deterministic key within the run; preserve prior runs.
- Exception without approver/date/reason: reject.
- Exception references a missing finding/entity: quarantine the exception for review.
- Structural finding with no exception: gate fails in strict mode.
- Coverage below advisory threshold: report as info/medium; do not fail CI.
- Interrupted quality run: mark incomplete/failed and preserve completed findings.
- Taxonomy or rule catalogue changes: new run; previous reports remain readable.

## 8. Out of scope

- Automatic remediation or data cleaning.
- Re-ingestion from MusicBrainz or any external source.
- Changing E3/E4 data, classifications or membership.
- API endpoint or schema changes.
- Frontend routes, components or generated types.
- Graph construction, metrics or communities.
- E6 exploratory analysis and metric definition.
- Full dataset committed to Git or fetched by ordinary CI.
- Statistical significance or causal claims.

## 9. Acceptance criteria

| ID | Criterion | Evidence |
|---|---|---|
| AC-001 | Quality tables and constraints migrate from an empty database and roll back cleanly. | Migration and downgrade tests |
| AC-002 | A versioned rule catalogue validates dimensions, severities, thresholds and unique rule codes. | Rule tests |
| AC-003 | Structural checks detect missing provenance, orphans, duplicate MBIDs, invalid taxonomy leaves, credit-scope defects and duplicate primaries. | Defect-injection tests |
| AC-004 | Completeness metrics expose numerator, denominator and missing counts. | Metric tests |
| AC-005 | Coverage metrics report by band, decade, taxonomy leaf/family, role, scope, country and source. | Coverage tests |
| AC-006 | Findings and exceptions persist with run, rule, entity, reason, approver and date. | Persistence/audit tests |
| AC-007 | The initial 24 album quarantine, 17 album-review and 17 aggregate-review exceptions are registered and visible. | Full-run report and exception counts |
| AC-008 | JSON/Markdown reports include versions, findings, exceptions, metrics, gate result and missing-data wording. | Report tests |
| AC-009 | CLI supports full/advisory/strict modes with stable exit codes. | CLI tests |
| AC-010 | CI runs structural checks against fixtures without the full dataset or network. | CI logs |
| AC-011 | Full-corpus quality run persists findings and metrics for the normalized dataset with exact versions. | Full-run evidence |
| AC-012 | Replaying the same inputs is deterministic and does not duplicate findings. | Double-run tests |
| AC-013 | No canonical, API, OpenAPI, frontend or graph change occurs. | Scope guards and OpenAPI drift |
| AC-014 | Full backend tests, Ruff, format and local CI pass; remote CI passes after push. | Test and CI evidence |

## 10. Assumptions and open questions

### Assumptions

- SPEC-005 remains validated and the normalized database is available for full quality runs.
- The full E3 dataset and raw cache remain ignored by Git.
- Structural invariants are the only initial hard gates; coverage thresholds are advisory.
- The 24 quarantined albums and 34 review classifications/aggregates are accepted initial exceptions once registered.
- Quality findings are persisted in tables and reports.

### Open questions

| Question | Blocking? | Owner | Resolution |
|---|---|---|---|
| Exact initial coverage thresholds and target values | No | Plan / E5 baseline | Define after the first full quality report; keep advisory. |
| Exception expiry or re-review cadence | No | Plan | Define in `plan.md`; initial exceptions remain valid until a new dataset/taxonomy version. |
| Whether a future CI job provisions a dataset artifact | No | Later | Current model runs structural rules in CI and full quality as a batch. |
| Exact names of quality tables beyond the minimum in FR-006 | No | Plan | Finalize in the migration plan. |

No blocking question remains for planning.

## 11. Validation result

- **Date:** 2026-11-08
- **Verdict:** Implemented; local validation passed; remote CI and formal validation pending
- **Evidence:** 234 backend tests passed with PostgreSQL; Ruff check/format, OpenAPI drift and compose validation passed. Quality run `341824ea-5d6f-4279-bae0-f66a1e696e05` persisted 58 findings, 58 approved exceptions, 20 rules and 51 metrics with no unexcepted blocking finding. See `tasks.md`.

## 12. References

- [Constitution](../../constitution.md)
- [AGENTS.md](../../AGENTS.md)
- [Scope](../../docs/00-vision/scope.md)
- [Roadmap](../../docs/00-vision/roadmap.md)
- [Data model v0](../../docs/01-architecture/data-model.md)
- [ER diagram](../../docs/01-architecture/er-diagram.md)
- [Normalization rules](../../docs/03-data/normalization-rules.md)
- [Seed list documentation](../../docs/03-data/seed-list.md)
- [ADR-0005 — Identity and provenance](../../docs/01-architecture/adr/ADR-0005-identity-and-provenance.md)
- [ADR-0008 — Taxonomy, corpus and versioning](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)
- [SPEC-005 — Normalization, identity and provenance](../005-normalization-identity/spec.md)
