# Project roadmap

- **Status:** Approved
- **Version:** 0.2
- **Date:** 2026-11-06
- **Scope:** from initialization to v0.1 and the later expansion to hundreds of bands

## 1. Sequencing principles

- **Risk-first:** validate sources, coverage and the model first; build product afterward.
- **Vertical slices:** each stage delivers something verifiable end to end, not only a technical layer.
- **One feature, one spec:** specs are written at the start of a feature, not all in advance.
- **Stage gates:** do not move on unless exit criteria are met.
- **No rigid dates:** plan by dependencies and deliverables. Estimates are made per stage with real data.
- **Progressive growth:** the original corpus uses 42 bands and the active v0.2.0 corpus uses 57; the architecture must support 200–500 without redesign while the period expands to 1960–2026.

## 2. Stage summary

| Stage | Phase | Objective | Depends on |
|---|---|---|---|
| E0 | Decisions | Scope, sources, feasibility and architecture | — |
| E1 | Foundations | Reproducible repository and environment | E0 |
| E2 | Foundations | Data model v0 and walking skeleton | E1 |
| E3 | Data | MusicBrainz ingestion for the seed list | E2 |
| E4 | Data | Normalization, identity and provenance | E3 |
| E5 | Data | Quality, coverage and validation | E4 |
| E6 | Analysis | EDA and metric definition | E5 |
| E7 | Analysis | Graphs, metrics and communities | E6 |
| E8 | Product | Read-only API v1 | E2, E4, E7 |
| E9 | Product | Frontend: entity explorer | E8 |
| E10 | Product | Graph visualization | E7, E8, E9 |
| E11 | Closure | Integration, QA and performance | E9, E10 |
| E12 | Closure | Deployment, documentation and v0.1 | E11 |
| E13 | Growth | Expansion to 200–500 bands (v1) | E12 |

## 3. Milestones

| Milestone | Stages | Outcome |
|---|---|---|
| **M0 — Decisions made** | E0 | Scope, sources and architecture approved; MusicBrainz feasibility measured |
| **M1 — Vertical skeleton** | E1–E2 | PostgreSQL → FastAPI → React → minimal graph working with seed data |
| **M2 — Trustworthy data** | E3–E5 | Normalized, traceable dataset with a quality report |
| **M3 — Analytics available** | E6–E7 | Reproducible precomputed metrics and networks |
| **M4 — Product v0.1** | E8–E12 | Public read-only application, tested and documented |
| **M5 — Expanded corpus** | E13 | 200–500 bands with the same pipeline |

## 4. Stages

### E0 — Scope, sources and architecture

- **Objective:** fix the operational scope, evaluate sources and demonstrate that the project is feasible with real data.
- **Scope:** MVP questions, seed list, period, subgenres, inclusion criteria, terms of use, general architecture, glossary, risks and the MusicBrainz spike.
- **Activities:** review official documentation for each source; define the seed list; run a 20–30 band spike; measure credit, studio, date and identifier coverage; write ADRs; review licenses and attribution.
- **Deliverables:** [vision](vision.md), [scope](scope.md), [roadmap](roadmap.md), [glossary](glossary.md), [source evaluation](../03-data/sources.md), [spike report](../03-data/spike-report.md), [seed list](../03-data/seed-list.md), [architecture](../01-architecture/overview.md), [data model v0](../01-architecture/data-model.md), ADRs 0001–0008, SDD templates.
- **Depends on:** nothing.
- **Done when:** scope is approved, sources have a documented decision, the spike demonstrates a viable path, the 42-band seed list is versioned, and no blocking unknowns remain.

### E1 — Repository and environment bootstrap

- **Objective:** provide a reproducible environment and a verifiable technical skeleton.
- **Scope:** monorepo, uv, minimal FastAPI, React + Vite + TypeScript, PostgreSQL in Docker Compose, configuration, logging, healthcheck, lint, formatting, tests and CI.
- **Activities:** review and approve the **SPEC-001** plan and tasks; create the repository structure; configure Ruff, pytest, Vitest, TypeScript and GitHub Actions; document startup; define `.env.example` and configuration conventions; confirm the commands and working boundaries in [conventions](../01-architecture/conventions.md).
- **Deliverables:** working `docker compose up`; `/health` endpoint; initial page; green CI; quick-start README; confirmed engineering conventions; **SPEC-001** implemented.
- **Depends on:** E0.
- **Done when:** a clean clone brings up the environment in under 15 minutes; lint, typecheck, tests and build pass locally and in CI.

### E2 — Data model v0 and walking skeleton

- **Objective:** validate the full architecture with a minimal vertical slice and an initial model.
- **Scope:** core entities, initial migration, seed fixtures, minimal read API, band page and mini-graph.
- **Activities:** consolidate the ERD and data dictionary v0; decide release-group vs release; define credit scopes (release-group, release, recording) and role attributes; create the Alembic migration; load 10–20 bands from the spike; implement list and detail views; render a band–producer graph with Cytoscape; generate TypeScript types from OpenAPI.
- **Deliverables:** schema migratable from scratch; fixtures; OpenAPI v0 contract; band list and detail; mini-graph; end-to-end smoke test; **SPEC-002** validated.
- **Depends on:** E0, E1.
- **Done when:** the PostgreSQL → FastAPI → React → Cytoscape flow works with seed data; migrations apply from scratch; the contract is generated without manual intervention; CI is green.

> The walking skeleton is deliberately minimal. It is neither the final UI nor the final model; it proves that the pieces fit together.

### E3 — MusicBrainz ingestion

- **Objective:** extract the seed dataset with full traceability.
- **Scope:** HTTP client with User-Agent, rate limiting, retries and caching; traversal artist → release-groups → releases → recordings → relationships and credits; raw storage; run logging; period declared by the versioned seed list.
- **Activities:** implement an idempotent ingestion CLI; preserve raw payloads or hash references; record URL, date, status and errors; fetch release-level and recording-level relationships; generate a coverage and failure report; respect the one-request-per-second limit; support versioned seed-list batches.
- **Deliverables:** raw layer; extracted dataset; ingestion report; reproducible CLI; **SPEC-003**. The implemented 1980–2000 dataset remains historical while the expanded 1960–2026 corpus is built as a new version.
- **Depends on:** E2 and source approval in E0.
- **Done when:** ingestion is reproducible and idempotent; every record is traceable to its source; access limits are respected; failures are recorded.

### E4 — Normalization, identity and provenance

- **Objective:** convert raw data into canonical entities without losing traceability.
- **Scope:** entity mapping; MBID as key; external identifier table; aliases; role mapping including producer attributes (`co`, `executive`, `assistant`, `additional`); recording-level credit scope; date precision; conflicts; quarantine; deterministic deduplication; album-level taxonomy and dataset membership.
- **Activities:** document normalization rules; resolve identities by MBID, QID and other identifiers; do not perform automatic fuzzy matching; record provenance and confidence per credit; separate confirmed, inferred and missing data; classify albums with one primary and multiple secondary leaf subgenres; derive band aggregates; preserve retired bands and dataset membership.
- **Deliverables:** normalized tables; rules; identity and deduplication report; taxonomy classification tables; normalization tests; **SPEC-005**.
- **Depends on:** E3.
- **Done when:** every raw record is mapped or quarantined; there are no orphans; deduplication is deterministic and auditable; rules are documented and tested.

### E5 — Data quality and validation

- **Objective:** measure and control quality before analysis.
- **Scope:** completeness, validity, uniqueness, consistency and coverage by decade, subgenre and source; low-confidence release-group and classification review; absence-is-not-negative rules.
- **Activities:** rule catalogue; automated checks; reports; acceptance thresholds; quarantine; confidence thresholds; review queues for low and medium confidence; documentation of limitations.
- **Deliverables:** quality suite; coverage and quality report; agreed thresholds; list of known gaps; **SPEC-006**.
- **Depends on:** E4.
- **Done when:** the suite runs in CI or batch; thresholds are met or exceptions are justified; limitations are documented.

### E6 — Exploratory analysis and metric definition

- **Objective:** understand the data and decide which metrics make sense before building the graph.
- **Scope:** distribution by decade (1960s–2020s), subgenre and role; coverage; most frequent producers; concentration; collaboration frequencies.
- **Activities:** reproducible analyses; reports; formal metric definitions; review of analytical scope; bias identification, including subgenre and decade coverage differences; report taxonomy and dataset versions.
- **Deliverables:** EDA report; metric catalogue; limitations and scope decisions; **SPEC-007**.
- **Depends on:** E5.
- **Done when:** the MVP questions can be answered with the available data and metrics are defined without ambiguity.

### E7 — Graph construction and network analysis

- **Objective:** build network snapshots and persist reproducible analytical results.
- **Scope:** bipartite credit graph, projections, centrality, communities and temporal analysis by decade (1960s–2020s).
- **Activities:** define node and edge types; build the graph from a snapshot; compute metrics; persist `analysis_run`, metrics, communities, dataset version and taxonomy version; review results with control visualizations.
- **Deliverables:** graph builder; results tables; network report; reproducibility metadata; **SPEC-008**.
- **Depends on:** E6.
- **Done when:** a run is reproducible with the same data and parameters; results are persisted and versioned; performance is acceptable for the MVP volume.

### E8 — Read-only API v1

- **Objective:** expose entities, relationships and analytics through a stable contract.
- **Scope:** `/api/v1` for artists, albums, producers, credits, search, filters, pagination and subgraphs; precomputed metric endpoints; taxonomy and period filters; retired-band detail behaviour.
- **Activities:** resource design; pagination and whitelist filters; consistent errors; OpenAPI; contract tests; subgraph depth and size limits; CORS; TypeScript type generation; taxonomy endpoint and hierarchical filter semantics.
- **Deliverables:** API v1; OpenAPI; documentation; contract tests; **SPEC-009**.
- **Depends on:** E2 and E4; analytical endpoints depend on E7.
- **Done when:** the contract is stable; contract tests pass; response times meet the target for the MVP volume; there are no obvious N+1 queries.

### E9 — Frontend: entity explorer

- **Objective:** build the main exploration interface with real data.
- **Scope:** application shell; routing; search; band, album and producer list and detail views; loading, error and empty states; URL filters; dynamic taxonomy, period filters and album-level subgenres.
- **Activities:** Tailwind; React Router; TanStack Query; generated types; responsive design; basic accessibility; consume taxonomy metadata instead of hard-coded subgenre lists.
- **Deliverables:** working explorer; typed client; component tests; main flow; **SPEC-010**.
- **Depends on:** E8.
- **Done when:** the list → detail → relationship flow works end to end; typecheck, lint, tests and build pass.

### E10 — Graph visualization and interaction

- **Objective:** allow exploration of collaboration networks without degrading performance.
- **Scope:** Cytoscape view; layouts; filters by role, decade and hierarchical subgenre; neighbor expansion; node and edge details; legend; accessible table fallback.
- **Activities:** integrate the subgraph endpoint; set node and edge limits; expand on demand; URL state; interaction tests; performance budget; taxonomy-versioned filters.
- **Deliverables:** graph page; interactions; UX and performance documentation; **SPEC-011**.
- **Depends on:** E7, E8 and E9.
- **Done when:** a 500–2000 node subgraph is usable; the interface does not freeze; an accessible table alternative exists.

### E11 — Integration, QA and performance

- **Objective:** validate the complete system before release.
- **Scope:** end-to-end tests, performance, accessibility, basic security, backup restoration and dependency review.
- **Activities:** Playwright for critical flows; simple load tests; accessibility audit; review of CORS, secrets and input validation; restore test.
- **Deliverables:** QA report; fixes; performance report; accessibility and security checklists; **SPEC-012**.
- **Depends on:** E9 and E10.
- **Done when:** critical flows pass; there are no P1/P2 bugs; agreed performance and accessibility targets are met.

### E12 — Deployment, documentation and v0.1 release

- **Objective:** publish a reproducible and documented version.
- **Scope:** production Compose; reverse proxy; TLS; migrations; backups; runbooks; source attribution; release notes.
- **Activities:** deploy to the chosen environment; document operation and rollback; licenses and attribution page; post-deployment smoke test; version tag.
- **Deliverables:** deployed v0.1; runbook; deployment documentation; visible attribution; release notes; **SPEC-013**.
- **Depends on:** E11.
- **Done when:** the application is accessible; deployment is reproducible; rollback is documented; licenses are displayed correctly.

### E13 — Corpus expansion to 200–500 bands (v1)

- **Objective:** expand the dataset without changing the architecture and validate that patterns hold.
- **Scope:** new seed-list batches; re-run ingestion, normalization, quality, analysis and result publication across 1960–2026.
- **Activities:** expand the list using the same criteria; run E3–E5 in batches; compare coverage and bias; recompute analyses with dataset and taxonomy versions; review API and graph performance; update the limitations report.
- **Deliverables:** v1 dataset; coverage report; updated analyses; performance review; **SPEC-014**.
- **Depends on:** E12.
- **Done when:** the expanded corpus passes the same quality gates; API and UI maintain performance; results are documented with their limitations.

## 5. Dependencies and parallelization

### Critical path

`E0 → E1 → E2 → E3 → E4 → E5 → E6 → E7 → E8 → E9 → E10 → E11 → E12 → E13`

### Possible parallel work

- E8 can start with fixtures after E2, without waiting for all ingestion.
- E9 can start once the v1 contract is frozen, even if data is still under review.
- E6 and E7 can overlap with E8/E9 if normalized data is available.
- E10 does not start until the subgraph endpoint and performance limits exist.
- Documentation for each stage is written during the stage, not at the end of the project.

### Unblocking rule

A stage is not finished because code was produced; it is finished when its exit gate is met. If a dependency is unresolved, document the blocker and work on another task that does not require it.

## 6. Stage gate

Before closing any stage:

- [ ] Deliverables exist and have been reviewed.
- [ ] Exit criteria are met or exceptions are justified.
- [ ] Tests pass.
- [ ] Documentation is up to date.
- [ ] New decisions are recorded in an ADR.
- [ ] Risks and limitations are recorded.
- [ ] The next stage has a clear first deliverable.

## 7. Current status

| Stage | Status | Note |
|---|---|---|
| E0 | Completed | Documents, spike, amended ADRs, data-model updates and the 42-band seed list are complete |
| E1 | Completed | SPEC-001 validated; CI green |
| E2 | Validated | SPEC-002 validated; local and remote CI evidence complete |
| E3 | Validated | SPEC-003 and SPEC-004 validated with remote CI. The v0.2.0 corpus has 57 bands, 1960–2026 and a reproducible dataset. |
| E4 | Validated | SPEC-005 normalization, identity, taxonomy, classification, aggregates and membership. Remote CI run 42535752532 passed. |
| E5 | Implemented locally | SPEC-006 quality rules, persisted findings/exceptions/metrics and two-level CI/full-corpus gate. Remote CI pending. |
| E6–E13 | Pending | See [specs/README.md](../../specs/README.md) for the operational spec index |

## 8. Scope growth

Moving from 42 to 200–500 bands is a change in volume, not architecture. To keep it that way:

- Ingestion must be idempotent and batch-operable.
- Each run must record its dataset version, seed-list version and taxonomy version.
- The API must paginate, limit subgraphs and support hierarchical taxonomy filters.
- Analyses must run in batch and be persisted with dataset and taxonomy versions.
- The UI must load data on demand, not the entire graph.
- Quality and coverage must be measured for every batch.
- Retired bands must remain in history but disappear from active listings.

A change of sources, credit model or taxonomy is a scope change and requires an ADR, updated specs and a pipeline re-run.

## 9. Plan risks

| Risk | Stage where detected | Response |
|---|---|---|
| Insufficient credit coverage in MusicBrainz | E0, E3, E5 | Adjust scope, complement with Wikipedia or rethink sources |
| Unsuitable release-group model | E0, E2, E4 | Review ADR-0004 before expanding the corpus |
| Duplicate identities | E4 | Deterministic matching and quarantine |
| Scope creep | All | Explicit seed list and out-of-scope boundaries |
| Graph performance | E7, E10, E13 | Subgraph limits and precomputation |
| Stale documentation | All | Docs in the same PR; review per stage |
| Licensing and attribution | E0, E12 | Legal evaluation and attribution page |
| Over-engineering | All | ADR required for new dependencies |

## 10. Next step

E0–E3 are complete and validated, including the 57-band v0.2.0 corpus and reproducible dataset. E4 is validated as SPEC-005 with remote CI run 42535752532. E5 is implemented locally as SPEC-006; remote CI and formal validation remain. E6 follows as SPEC-007.
