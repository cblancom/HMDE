# Data quality rules

- **Status:** Active
- **Version:** 0.2.0
- **Date:** 2026-11-19
- **Stage:** E5 / E13 extension
- **Spec:** [SPEC-006](../../specs/006-data-quality/spec.md), extended by [SPEC-016](../../specs/016-corpus-expansion/spec.md)
- **Plan:** [SPEC-006 plan](../../specs/006-data-quality/plan.md), [SPEC-016 plan](../../specs/016-corpus-expansion/plan.md)
- **Normalized run:** `ed8e7e12-c181-4041-ba39-42b2bf655453`
- **Dataset:** `mb-20261119T004940Z-9d5e75fdc1b9`
- **Taxonomy:** 0.2.0

## 1. Purpose

The quality layer measures the validated E4 corpus before analysis. It distinguishes structural defects from source gaps, persists findings and exceptions, and produces reproducible reports.

Quality checks are read-only for canonical and normalization data. E5 does not repair data, call external sources, change the API or build analytical graphs.

## 2. Two-level model

### CI

CI runs structural rules and rule behaviour against PostgreSQL and small fixtures. This path is fast, deterministic and network-free. It does not require `data/raw/`, `data/ingestions/` or `data/normalization/`.

### Full corpus

The full quality run executes against the normalized development database and the real dataset. It persists findings, exceptions and metrics, and writes JSON/Markdown reports. The run records dataset, taxonomy, normalization-run, rule-catalogue and code versions.

The full corpus is intentionally outside Git, so it is a batch gate rather than an ordinary CI step.

## 3. Dimensions

- **Structural:** provenance, FKs, MBIDs, taxonomy leaves, classification primaries, credit targets, membership and run consistency.
- **Completeness:** counts and denominators for dates, country, QIDs, classifications, producer coverage, credits and membership.
- **Validity:** UUIDs, confidence ranges, allowed statuses and taxonomy version alignment.
- **Consistency:** one primary album label, one primary band aggregate, version alignment and lifecycle rules.
- **Coverage:** by band, decade, taxonomy leaf/family, role, scope, country, source and batch.

## 4. Gates

- Structural invariants are blocking.
- A blocking finding without an approved exception blocks strict quality runs.
- Coverage thresholds are advisory in the initial E5 baseline.
- Missing data is reported explicitly and is not negative evidence.

## 5. Rules and exceptions

The versioned rule catalogue is [`data/quality/rules-v0.2.0.json`](../../data/quality/rules-v0.2.0.json) for corpus v0.3.0. It defines stable rule codes, dimensions, severities and remediation guidance. `Q-MEM-001` now compares active memberships with the active seed-list count instead of the hardcoded 57; the v0.1.0 catalogue remains the historical v0.2.0 baseline.

The initial exception baseline is [`data/quality/exceptions-v0.1.0.json`](../../data/quality/exceptions-v0.1.0.json). It contains the owner-approved exceptions for:

- 24 bootleg/live/demo albums without a primary classification;
- 17 medium-confidence album classifications;
- 17 band aggregate review cases.

The v0.3.0 baseline is [`data/quality/exceptions-v0.3.0.json`](../../data/quality/exceptions-v0.3.0.json). It is intentionally empty: the expanded run has no blocking finding, so no blocking exception is required. The 900 album-review and 189 aggregate-review findings remain visible as medium/advisory findings.

Exceptions are visible in reports. They do not delete or downgrade findings.

## 6. Local full-corpus evidence

The initial strict quality run is `341824ea-5d6f-4279-bae0-f66a1e696e05`. It persisted 58 findings, 58 approved exceptions, 20 rules and 51 metrics. All 24 blocking album-classification findings were excepted, no unexcepted blocker remained, and the 34 medium review findings were accepted as baseline exceptions.

```bash
cd backend
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
  uv run python -m hmde.quality run \
    --normalization-run 54d66992-643b-49ec-bac4-fe514ea39e94 \
    --rules ../data/quality/rules-v0.1.0.json \
    --exceptions ../data/quality/exceptions-v0.1.0.json \
    --output ../data/quality --strict
```

The v0.3.0 full run is `288b11ac-9a90-4b4f-bf58-fdd50e1a51ad` against normalization `ed8e7e12-c181-4041-ba39-42b2bf655453`. It persisted 1,089 medium/advisory findings (900 album review and 189 aggregate review), 0 blocking findings, 0 exceptions and 77 coverage/completeness metrics. The strict gate exits `2` because findings remain advisory; it is not blocked. Coverage includes batch, country, decade, taxonomy leaf, role, source, field and credit scope, and missing-data ratios use denominators.

```bash
cd backend
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
  uv run python -m hmde.quality run \
    --normalization-run ed8e7e12-c181-4041-ba39-42b2bf655453 \
    --rules ../data/quality/rules-v0.2.0.json \
    --exceptions ../data/quality/exceptions-v0.3.0.json \
    --output ../data/quality --strict
```

Exit codes: `0` pass, `2` advisory findings, `3` blocked by an unexcepted blocking finding, `1` fatal error.

## 7. Reporting

Reports include:

- quality and normalization run IDs;
- dataset, taxonomy, rule-catalogue and code versions;
- findings by rule, severity and status;
- approved exceptions and reasons;
- completeness and coverage metrics with denominators;
- gate result and runtime;
- explicit missing-data wording.

## 8. Change control

A rule-catalogue change requires a new catalogue version and a new quality run. A taxonomy or dataset change requires a new quality run against that version. Canonical corrections belong to E3/E4 and must not be performed by the quality layer.
