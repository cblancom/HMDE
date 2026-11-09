# SDD specifications

- **Status:** Active index
- **Version:** 0.2
- **Date:** 2026-11-05

This directory contains the active Specification-Driven Development work. The long-term stage plan lives in [`docs/00-vision/roadmap.md`](../docs/00-vision/roadmap.md). This index tracks capability boundaries, spec status and dependencies.

## Capability map

| Module id | Responsibility | Depends on |
|---|---|---|
| `platform` | Repository, environment, configuration, database foundation, CI, logging | — |
| `catalog` | Artists, albums, editions, recordings, credits and roles | `platform` |
| `ingestion` | Source clients, raw layer, source records and ingestion runs | `platform` |
| `normalization` | Identity resolution, role mapping and provenance | `catalog`, `ingestion` |
| `quality` | Data-quality rules, coverage metrics and quarantine | `normalization` |
| `analytics` | Graph construction, metrics and communities | `normalization`, `quality` |
| `api` | Read-only HTTP contract and subgraphs | `catalog`, `analytics` |
| `web` | Entity explorer and graph visualization | `api` |

Build order: `platform → catalog → ingestion → normalization → quality → analytics → api → web`. Catalog and ingestion may advance in parallel after the platform foundation; the API may start with fixtures before analytics is complete.

## Spec index

E0, E1 and E2 are complete. `001-foundations` and `002-seed-band-explorer` are validated. SPEC-003 and SPEC-004 are validated. SPEC-005 is validated for E4 normalization, identity, album taxonomy and provenance. Remote CI run 42535752532 passed. SPEC-006 is validated for E5 data quality and validation. Remote CI run 42545153696 passed. SPEC-007 is in draft for E6 exploratory analysis and metric definition; its plan and tasks are the next gate.

| Order | Spec | Stage | Primary module | Scope | Depends on | Status |
|---|---|---|---|---|---|---|
| 001 | [`001-foundations`](001-foundations/spec.md) | E1 | `platform` | Repository, environment, configuration, health, migrations baseline, test harnesses, CI | — | Validated |
| 002 | [`002-seed-band-explorer`](002-seed-band-explorer/spec.md) | E2 | `catalog` | Data model v0, seed fixtures, read API, band explorer, mini-graph | 001 | Validated |
| 003 | [`003-musicbrainz-ingestion`](003-musicbrainz-ingestion/spec.md) | E3 | `ingestion` | Source client, raw layer, ingestion runs, seed-list extraction | 002 | Validated |
| 004 | [`004-corpus-v0-2`](004-corpus-v0-2/spec.md) | E3 | `ingestion` | 15-band corpus v0.2 seed list, 1960–2026 period and new E3 dataset | 003 | Validated |
| 005 | [`005-normalization-identity`](005-normalization-identity/spec.md) | E4 | `normalization` | Canonical entities, album-level taxonomy, role mapping, credit scope, provenance, dataset lifecycle | 004 | Validated |
| 006 | [`006-data-quality`](006-data-quality/spec.md) | E5 | `quality` | Quality rules, coverage reports, low-confidence review | 005 | Validated |
| 007 | [`007-eda-metrics`](007-eda-metrics/spec.md) | E6 | `analytics` | Exploratory analysis and metric definitions | 006 | Draft |
| 008 | `008-network-analysis` | E7 | `analytics` | Graph snapshots, metrics and communities | 007 | Pending |
| 009 | `009-read-api` | E8 | `api` | Read API v1, filters, pagination, subgraphs, precomputed metrics | 002, 005, 008 | Pending |
| 010 | `010-entity-explorer` | E9 | `web` | Band, album and producer exploration UI | 009 | Pending |
| 011 | `011-graph-visualization` | E10 | `web` | Interactive collaboration graph and accessible fallback | 008, 009, 010 | Pending |
| 012 | `012-integration-qa` | E11 | `platform` | End-to-end tests, performance, accessibility and security review | 010, 011 | Pending |
| 013 | `013-release-v0.1` | E12 | `platform` | Deployment, attribution, runbooks and release | 012 | Pending |
| 014 | `014-corpus-expansion` | E13 | `ingestion` | Expansion to 200–500 bands and v1 validation | 013 | Pending |

The index is updated when a spec is created, approved, implemented or validated. A spec that is split or superseded keeps its number and is marked accordingly.

## Spec lifecycle

| Status | Meaning |
|---|---|
| `Draft` | Being written; not ready for planning |
| `In clarification` | Open questions must be resolved before `plan.md` |
| `Spec approved` | Spec content approved; plan and tasks not yet approved |
| `Plan/tasks in review` | Plan and tasks drafted; awaiting approval |
| `Approved` | Spec, plan and tasks approved; implementation may start |
| `In implementation` | Work in progress |
| `Implemented` | Code and migration work are complete |
| `Validated` | Acceptance criteria have recorded evidence |
| `Superseded` | Replaced by another spec or versioned revision |

`Implemented` does not mean `Validated`.

Specs may be revised while in draft, clarification or approval. After validation, a behavior change requires a new spec or an explicit versioned revision with a changelog.

## Workflow and gates

1. **Specify:** write `spec.md` with context, requirements and acceptance criteria.
2. **Clarify:** resolve ambiguities and edge cases. No `plan.md` while blocking questions remain.
3. **Plan:** write `plan.md` with architecture, components, data/API impact, tests and risks.
4. **Tasks:** write `tasks.md` with dependencies, verification and expected evidence.
5. **Approve:** the human approves spec, plan and tasks.
6. **Implement:** one task or a small related group at a time.
7. **Validate:** execute checks, record evidence in `tasks.md`, update the spec result and this index.

Do not implement a feature whose spec or tasks are not approved. Do not change scope silently; update the spec first.

## Granularity

- One spec is one cohesive, verifiable capability.
- It may touch database, ETL, API and UI when they form one vertical slice.
- Split when acceptance criteria can be shipped and verified independently, or when the spec cannot be reviewed in one sitting.
- There is no hard page or acceptance-criteria limit. As a heuristic, 5–12 acceptance criteria is reasonable; more is a signal to consider splitting.
- Do not create specs per layer ("the table", "the endpoint", "the screen") when they form one capability.

## Naming convention

```
specs/
  001-foundations/
    spec.md
    plan.md
    tasks.md
  002-seed-band-explorer/
  ...
```

The directory uses a three-digit sequence and a short English kebab-case name. The document ID is `SPEC-NNN`. Numbers are never reused.

Templates are in [`_template/`](_template/).

## Traceability

- Functional requirements: `FR-NNN`.
- Non-functional requirements: `NFR-NNN`.
- Business rules: `BR-NNN`.
- Acceptance criteria: `AC-NNN`.
- `plan.md` maps requirements to plan sections.
- `tasks.md` maps requirements to tasks and records verification evidence.
- Every acceptance criterion has at least one test, check or explicit manual verification.

## Next step

E0, E1 and E2 are complete. SPEC-002, SPEC-003 and SPEC-004 are validated. SPEC-005 is validated. SPEC-006 is validated. SPEC-007 is in draft for E6; its plan and tasks are the next gate.
