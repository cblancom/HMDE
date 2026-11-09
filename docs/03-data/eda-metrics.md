# EDA metrics

- **Status:** Active
- **Version:** 0.1.0
- **Date:** 2026-11-09
- **Stage:** E6
- **Spec:** [SPEC-007](../../specs/007-eda-metrics/spec.md)
- **Catalogue:** [`data/metrics/catalogue-v0.1.0.json`](../../data/metrics/catalogue-v0.1.0.json)

## 1. Purpose

E6 describes the normalized corpus before graph construction. It reports distributions, coverage and concentration with explicit denominators and limitations. The result is a versioned JSON/Markdown report; E6 does not add database tables, expose an API or modify normalized data.

## 2. Reproducibility and corpus growth

Every analysis is tied to a normalization run, quality run, dataset version, taxonomy version, metric-catalogue hash and code version. The output path is `data/analysis/<analysis_version>/`, where the version is derived from those inputs. Adding bands creates new dataset/normalization/quality versions and therefore a new analysis directory; old reports are never overwritten.

## 3. Metric families

- Corpus overview and membership.
- Temporal distributions and date precision.
- Album and band taxonomy distributions.
- Role and credit-scope distributions.
- Country, source and batch coverage.
- Producer participation and concentration (top-k and HHI).
- Descriptive co-credit pair frequencies.
- Quality limitations and missing-data visibility.

## 4. Metric rules

- Every count reports a denominator.
- Decades range from 1960s to 2020s; missing dates use `unknown`.
- Parent taxonomy nodes are family roll-ups; only leaves classify albums.
- Producer/co-producer metrics are separate from engineer/mix/mastering.
- Concentration formulas are stated in the catalogue and computed over documented producer album assignments.
- Co-credit frequencies are descriptive, not causal, affinity or centrality measures.
- Small samples are flagged or suppressed according to the metric definition.

## 5. Local full-corpus evidence

The local EDA run is `eda-1267fdcced62b7da`, tied to normalization run `54d66992-643b-49ec-bac4-fe514ea39e94`, quality run `341824ea-5d6f-4279-bae0-f66a1e696e05` and metric catalogue `0.1.0`. It produced 354 metric rows, including 731 albums across 1960s–2020s, 58 quality findings covered by 58 exceptions, producer participation and concentration, and descriptive co-credit frequencies. Report: `data/analysis/eda-1267fdcced62b7da/report.json`.

```bash
cd backend
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
  uv run python -m hmde.analytics run \
    --normalization-run 54d66992-643b-49ec-bac4-fe514ea39e94 \
    --quality-run 341824ea-5d6f-4279-bae0-f66a1e696e05 \
    --taxonomy ../data/taxonomy.json \
    --metric-catalogue ../data/metrics/catalogue-v0.1.0.json \
    --output ../data/analysis
```

Exit code `2` means the report completed with known limitations; it is not a fatal error. Existing analysis versions are immutable; a future corpus expansion creates a new `analysis_version`.

## 6. Missing data

Absence of a credit, date, country, QID or tag is reported as missing coverage. It is not evidence that a person did not participate or that an album has no genre.
