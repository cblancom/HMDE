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

E0 and E1 are complete. `001-foundations` is validated; `002-seed-band-explorer` is implemented and locally validated (T-001–T-012 complete). Its remote CI run is pending a push.

| Order | Spec | Stage | Primary module | Scope | Depends on | Status |
|---|---|---|---|---|---|---|
| 001 | [`001-foundations`](001-foundations/spec.md) | E1 | `platform` | Repository, environment, configuration, health, migrations baseline, test harnesses, CI | — | Validated |
| 002 | [`002-seed-band-explorer`](002-seed-band-explorer/spec.md) | E2 | `catalog` | Data model v0, seed fixtures, read API, band explorer, mini-graph | 001 | Implemented |
| 003 | `003-musicbrainz-ingestion` | E3 | `ingestion` | Source client, raw layer, ingestion runs, seed-list extraction | 002 | Pending |
| 004 | `004-normalization-identity` | E4 | `normalization` | Canonical entities, external IDs, role mapping, credit scope, provenance | 003 | Pending |
| 005 | `005-data-quality` | E5 | `quality` | Quality rules, coverage reports, low-confidence review | 004 | Pending |
| 006 | `006-eda-metrics` | E6 | `analytics` | Exploratory analysis and metric definitions | 005 | Pending |
| 007 | `007-network-analysis` | E7 | `analytics` | Graph snapshots, metrics and communities | 006 | Pending |
| 008 | `008-read-api` | E8 | `api` | Read API v1, filters, pagination, subgraphs, precomputed metrics | 002, 004, 007 | Pending |
| 009 | `009-entity-explorer` | E9 | `web` | Band, album and producer exploration UI | 008 | Pending |
| 010 | `010-graph-visualization` | E10 | `web` | Interactive collaboration graph and accessible fallback | 007, 008, 009 | Pending |
| 011 | `011-integration-qa` | E11 | `platform` | End-to-end tests, performance, accessibility and security review | 009, 010 | Pending |
| 012 | `012-release-v0.1` | E12 | `platform` | Deployment, attribution, runbooks and release | 011 | Pending |
| 013 | `013-corpus-expansion` | E13 | `ingestion` | Expansion to 200–500 bands and v1 validation | 012 | Pending |

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

E0 and E1 are complete. SPEC-002 is implemented and locally validated; T-001–T-012 are complete. Confirm E2 in CI after the next push, then start SPEC-003 (E3 MusicBrainz ingestion).
