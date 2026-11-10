# Tasks — SPEC-008 Graph construction and network analysis

- **Status:** Implemented locally; remote CI pending
- **Spec:** [spec.md](spec.md)
- **Plan:** [plan.md](plan.md)

## 1. Execution order

```text
T-001 ─┬─► T-003 ─► T-004 ─► T-005 ─► T-006 ─► T-007 ─► T-008 ─► T-009 ─► T-010 ─► T-011 ─► T-012
T-002 ─┘
```

T-001 and T-002 can run in parallel. T-003 loads read-only evidence. T-004 builds the producer–album layer. T-005 derives producer–band. T-006 computes metrics. T-007 persists runs. T-008 adds reports/CLI. T-009 proves the view contract and scope boundary. T-010 proves fixture/replay behaviour. T-011 runs the full corpus. T-012 closes documentation and CI.

## 2. Tasks

### T-001 — Add NetworkX and validate E7 inputs

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-001, NFR-005.
- **Dependencies:** SPEC-007 validated; plan/tasks approved.
- **Description:** Add the approved NetworkX dependency to the backend, create the `hmde.network` package skeleton (`__init__`, `__main__`, `errors`, `inputs`, `cli` placeholders) and implement network input validation. Validate normalization status, quality status, matching normalization/dataset/taxonomy versions and taxonomy file version. Add `data/network/*/` to `.gitignore`.
- **Done when:** valid runs are accepted; missing/non-terminal/mismatched runs and taxonomy mismatches fail before any write; NetworkX imports in the package; no network or raw-data access occurs.
- **Verification:**
  ```bash
  cd backend
  uv sync
  uv run pytest tests/unit/test_network_inputs.py tests/integration/test_network_inputs.py
  ```
- **Files:** `backend/pyproject.toml`, `backend/uv.lock`, `backend/src/hmde/network/__init__.py`, `errors.py`, `inputs.py`, `.gitignore`, tests.
- **Evidence:** 2026-11-10: NetworkX 3.7 installed and locked; `hmde.network` input validation implemented; `data/network/*/` ignored. Valid, mismatch, taxonomy, and non-terminal tests passed (7).

### T-002 — Add analytical models and migration `0007`

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-008, NFR-004.
- **Dependencies:** Plan approved; can run in parallel with T-001.
- **Description:** Add SQLAlchemy models and an additive migration for `analysis_run`, `graph_node`, `graph_edge`, `node_metric`, `producer_metric`, `temporal_metric`, `community` and `community_membership`. Include status/type/layer checks, support-ratio range, node/edge/metric uniqueness, FKs with `RESTRICT`, indexes and reversible downgrade. Export models from `hmde.models`.
- **Done when:** migration upgrades from empty and `0006`, downgrades cleanly to `0006`, and constraints reject invalid layers, node types, duplicate graph keys and out-of-range support ratios.
- **Verification:**
  ```bash
  cd backend
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run alembic upgrade head
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run alembic downgrade 0006
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run alembic upgrade head
  uv run pytest tests/unit/test_network_models.py tests/integration/test_network_migration.py
  ```
- **Files:** `backend/alembic/versions/0007_analytics_layer.py`, `backend/src/hmde/models/analytics.py`, `backend/src/hmde/models/__init__.py`, tests.
- **Evidence:** 2026-11-10: migration `0007` added `analysis_run`, `graph_node`, `graph_edge`, `node_metric`, `producer_metric`, `temporal_metric`, `community` and `community_membership`; `0006 → 0007 → 0006 → 0007` passed on the test database and `0007` was applied to development. Model and migration tests passed (3).

### T-003 — Load producer credits, album support and quality limitations

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-001, FR-003, FR-011.
- **Dependencies:** T-002.
- **Description:** Implement read-only SQLAlchemy loading of canonical albums, producer/co-producer credits, credit scopes, recording support, album recording counts, band/artist metadata, taxonomy classifications, quality findings/exceptions and potential duplicate labels. Aggregate per producer–album–role support and expose typed rows/dataclasses for graph construction.
- **Done when:** loader returns deterministic rows; support counts/scope mix are computed from existing E4 data; missing denominators remain null with reasons; no canonical mutation or network access; fixtures and full database work.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_network_loader.py tests/integration/test_network_loader.py
  ```
- **Files:** `backend/src/hmde/network/loader.py`, `backend/tests/unit/test_network_loader.py`, `backend/tests/integration/test_network_loader.py`.
- **Evidence:** 2026-11-10: read-only loader implemented for albums, producer/co-producer credits, recording support, quality findings/exceptions and duplicate labels. Unit support tests (4) and fixture loader test (1) passed. Missing denominators remain null; release-group support is full album; release/recording scopes use observed recording coverage.

### T-004 — Build the producer–album evidence layer

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-002, FR-003, FR-010.
- **Dependencies:** T-003.
- **Description:** Build the producer–album NetworkX graph and canonical node/edge records. Use `artist_id`/MBID and `release_group_id` keys, canonical labels, album metadata and role-bearing edges. Collapse roles for simple degree metrics while retaining per-role evidence for persistence. Add `support_ratio`, `scope_mix` and evidence attributes. No band nodes, no name-based identity and no `Artist.type` filter.
- **Done when:** producer and album counts reconcile with source rows; graph has no band nodes; same-MBID aliases produce one node; solo artists are accepted; release-group support records ratio `1.0`; partial recording support records the observed ratio or null with reason.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_network_graph.py tests/unit/test_network_identity.py
  ```
- **Files:** `backend/src/hmde/network/graph.py`, `backend/tests/unit/test_network_graph.py`.
- **Evidence:** 2026-11-10: producer–album builder implemented with canonical artist/album keys, album metadata, per-role edge records and a collapsed NetworkX graph. Tests passed (4) for no band nodes, same-ID identity, solo-artist inclusion, year/decade metadata and role collapsing.

### T-005 — Derive the producer–band/artist layer

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-004, FR-010, FR-015.
- **Dependencies:** T-004.
- **Description:** Derive producer–band/artist edges from the producer–album evidence. Use `release_group.artist_id` without an `Artist.type` filter; aggregate distinct album count, years, role mix, support counts and album evidence. Mark self-produced artists, expose both roles on one node and create no self-loop.
- **Done when:** one edge exists per producer–band pair; weights equal distinct albums; evidence reconciles with the album layer; self-produced albums are counted separately; no album nodes exist in the derived layer; solo and group artists both appear.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_network_derivation.py tests/unit/test_network_self_production.py
  ```
- **Files:** `backend/src/hmde/network/graph.py`, `backend/tests/unit/test_network_graph.py`.
- **Evidence:** 2026-11-10: producer–album builder implemented with canonical artist/album keys, album metadata, per-role edge records and a collapsed NetworkX graph. Tests passed (4) for no band nodes, same-ID identity, solo-artist inclusion, year/decade metadata and role collapsing.

### T-006 — Compute producer, centrality, community and temporal metrics

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-005, FR-006, FR-007.
- **Dependencies:** T-005.
- **Description:** Compute producer album/band degree, weighted degree, betweenness on the producer–band graph, top-k album/band rankings, HHI and producers-to-50%. Detect communities on the internal producer–producer projection (shared albums, seed `42`, resolution `1.0`) and compute per-decade album/band/active-producer/HHI metrics. Persist metric records with parameters, denominators and support/null counts.
- **Done when:** metrics match hand-calculated fixtures; album and band counts reconcile; communities are deterministic and internal-only; decade metrics handle 1960s–2020s and missing dates; no centrality/community product view is created.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_network_metrics.py tests/unit/test_network_communities.py tests/unit/test_network_temporal.py
  ```
- **Files:** `backend/src/hmde/network/metrics.py`, `backend/tests/unit/test_network_metrics.py`, `backend/tests/unit/test_network_communities.py`, `backend/tests/unit/test_network_temporal.py`.
- **Evidence:** 2026-11-10: metrics implemented for album/band degree, weighted degree, betweenness, top-k, HHI, producers-to-50%, support summary, graph counts and decade metrics. Louvain communities use seed `42` and resolution `1.0`. Tests passed (3) for counts/concentration, deterministic communities and temporal exclusions.

### T-007 — Persist analysis runs and analytical rows

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-008, FR-009, FR-012.
- **Dependencies:** T-002, T-006.
- **Description:** Implement the analytical run lifecycle and transactional persistence: start run, write nodes/edges/metrics/communities, finish status, rollback partial rows on failure, compute the deterministic analysis version and reuse a completed run with the same fingerprint. Store counters, parameters, report path and limitations.
- **Done when:** same inputs reuse the completed run; changed parameters/inputs create a new run; completed runs are immutable; failed runs remain auditable; node/edge/metric counts reconcile with the report; no canonical tables are touched.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_network_persistence.py tests/integration/test_network_persistence.py
  ```
- **Files:** `backend/src/hmde/network/persistence.py`, `backend/tests/unit/test_network_persistence.py`, `backend/tests/integration/test_network_persistence.py`.
- **Evidence:** 2026-11-10: deterministic `analysis_version`, run lifecycle, node/edge/metric/community persistence and completed-run reuse implemented. Integration test persisted a fixture network and reconciled nodes, edges, temporal metrics and communities; unit determinism test passed (2).

### T-008 — Add JSON/Markdown reports and the network CLI

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-012, FR-013, FR-015, NFR-007.
- **Dependencies:** T-007.
- **Description:** Implement versioned JSON/Markdown reports under `data/network/<analysis_version>/` and the `python -m hmde.network` CLI with normalization/quality/taxonomy/output options, decade/subgenre/band filters, top-k and stable exit codes. Report versions, layer counts, top producers by albums and bands, support distribution, communities, temporal metrics, identity/quality limitations and non-causal interpretation.
- **Done when:** reports include all required sections; output is deterministic; same inputs are idempotent; invalid inputs exit `1`; disclosed limitations exit `2`; no API/frontend/OpenAPI change occurs.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_network_report.py tests/integration/test_network_cli.py
  ```
- **Files:** `backend/src/hmde/network/report.py`, `cli.py`, `__main__.py`, `runner.py`, tests.
- **Evidence:** 2026-11-10: versioned JSON/Markdown/manifest reports, `python -m hmde.network`, filters, top-k and stable exit codes implemented. Report and CLI tests passed (2); repeated execution reused the completed run.

### T-009 — Prove the view contract and scope boundary

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-014, FR-015, FR-016, NFR-006, NFR-008, NFR-009.
- **Dependencies:** T-008.
- **Description:** Add API-ready view-contract tests for producer type, album year/decade, roles, support ratio, album evidence and self-produced flags. Add scope guards proving no API/OpenAPI/frontend imports, no ETL/network access, no canonical mutation and no album/band node mixing. Assert top-k is not persisted truncation and that persisted full graphs remain available.
- **Done when:** view metadata is complete and deterministic; scope guards pass; OpenAPI is unchanged; no color-only semantic is baked into data; no API/frontend files change.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/unit/test_network_view_contract.py tests/unit/test_network_scope_guard.py
  uv run pytest tests/unit/test_openapi.py
  ```
- **Files:** `backend/tests/unit/test_network_view_contract.py`, `test_network_scope_guard.py`, `backend/src/hmde/network/`, existing OpenAPI tests.
- **Evidence:** 2026-11-10: view-contract tests confirmed producer type, album year/decade, roles, support, album evidence and top-k non-truncation; scope guard confirmed no API/analytics/ETL/HTTP imports. View, scope and OpenAPI tests passed (6).

### T-010 — Add fixture integration, replay and corpus-expansion tests

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-009, FR-011, FR-013, NFR-001, NFR-002.
- **Dependencies:** T-009.
- **Description:** Add fixture-level integration tests over the E2 seeded database plus a synthetic quality run. Cover full network run, report/manifest, idempotent replay, changed-parameter new run, changed dataset version new run, no overwrite of prior runs, missing support denominators, self-produced albums and no network access. Ensure ordinary CI does not require `data/raw/`, `data/ingestions/`, `data/normalization/`, `data/quality/*/` or `data/network/`.
- **Done when:** fixture CI path is green without ignored data; replay is idempotent; changed inputs create new versions; old runs/reports remain untouched; missing data is reported correctly.
- **Verification:**
  ```bash
  cd backend
  uv run pytest tests/integration/test_network_fixture.py tests/integration/test_network_replay.py
  ```
- **Files:** `backend/tests/integration/test_network_fixture.py`, `test_network_replay.py`.
- **Evidence:** 2026-11-10: fixture run produced nodes, edges, communities and a complete JSON/Markdown/manifest report. Replay reused the same run; changed `top_k` and changed dataset version created new immutable versions while the first report remained intact. Tests passed (2).

### T-011 — Run the full E7 graph and review results

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-001–FR-016, NFR-001–NFR-008.
- **Dependencies:** T-010.
- **Description:** Run E7 against normalization run `54d66992-643b-49ec-bac4-fe514ea39e94`, quality run `341824ea-5d6f-4279-bae0-f66a1e696e05` and taxonomy v0.2.0. Review producer–album support, producer–band reconciliation, top producers, self-produced albums, communities, decade metrics and limitations. Record run ID, counts, report path and runtime.
- **Done when:** full run completes within 15 minutes; 384 producer artists, 1,134 producer–album assignments and 731 albums are reconciled or deviations are explained; top-k and support are reviewed; no unexcepted structural issue; report exists under `data/network/<analysis_version>/`.
- **Verification:**
  ```bash
  cd backend
  DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
    uv run python -m hmde.network run \
      --normalization-run 54d66992-643b-49ec-bac4-fe514ea39e94 \
      --quality-run 341824ea-5d6f-4279-bae0-f66a1e696e05 \
      --taxonomy ../data/taxonomy.json \
      --output ../data/network
  ```
- **Files:** runtime analytical tables, `data/network/net-a0b7c1f41ac5c92d/`, `specs/008-network-analysis/tasks.md`.
- **Evidence:** 2026-11-10: full run `91f39a30-fa51-4d75-a9a2-1b5605bd98c3`, version `net-a0b7c1f41ac5c92d`, status `completed_with_limitations`. Producer–album layer: 1,151 role edges, 384 producers, 584 albums; producer–band layer: 426 edges, 341 producers with non-self edges, 57 bands. Support: 246 full, 905 partial, 0 unknown. 78 communities, 62 temporal metric rows. Deviations explained: 147 of 731 albums have no producer/co-producer credit; 43 self-produced producers overlap with band nodes and are excluded from producer–band self-loops. Programmatic runtime: 2.15 s (well under 15 minutes). Report: `data/network/net-a0b7c1f41ac5c92d/report.json`.

### T-012 — Complete documentation, checks and remote CI

- **Status:** Completed locally (2026-11-10); remote CI pending.
- **Requirements:** FR-001–FR-016, NFR-001–NFR-009.
- **Dependencies:** T-011.
- **Description:** Add `docs/03-data/network-analysis.md` with graph definitions, support formulas, identity rules, self-production, view contract, limitations and CLI. Update README/AGENTS/data docs/roadmap/spec index. Run Ruff, format, full PostgreSQL suite, OpenAPI drift and Compose validation. Push only with explicit owner authorization and record remote CI.
- **Done when:** docs describe both views; full suite/Ruff/format/OpenAPI/Compose pass; no canonical/API/frontend change; remote CI passes; spec/tasks evidence and status are updated.
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
- **Files:** `README.md`, `AGENTS.md`, `data/README.md`, `docs/03-data/network-analysis.md`, `docs/README.md`, `docs/00-vision/roadmap.md`, `docs/01-architecture/er-diagram.md`, `specs/README.md`, `specs/008-network-analysis/`, `.gitignore`.
- **Evidence:** 2026-11-10: full backend suite passed 286 tests; Ruff check/format passed; migration replay passed; OpenAPI drift none; `docker compose config -q` passed; full E7 run `net-a0b7c1f41ac5c92d` documented. Remote CI is pending because no commit or push was performed.

## 3. Coverage matrix

### Functional requirements

| Requirement | Tasks |
|---|---|
| FR-001 | T-001, T-003, T-006, T-011 |
| FR-002 | T-003, T-004 |
| FR-003 | T-003, T-004 |
| FR-004 | T-005 |
| FR-005 | T-006 |
| FR-006 | T-006 |
| FR-007 | T-006 |
| FR-008 | T-002, T-007 |
| FR-009 | T-007, T-010 |
| FR-010 | T-004, T-005 |
| FR-011 | T-003, T-008 |
| FR-012 | T-007, T-008 |
| FR-013 | T-008, T-010 |
| FR-014 | T-009, T-011 |
| FR-015 | T-005, T-008, T-009 |
| FR-016 | T-009, T-012 |

### Non-functional requirements

| Requirement | Tasks |
|---|---|
| NFR-001 | T-007, T-010 |
| NFR-002 | T-010, T-011 |
| NFR-003 | T-006, T-010 |
| NFR-004 | T-002, T-007 |
| NFR-005 | T-001, T-012 |
| NFR-006 | T-009, T-012 |
| NFR-007 | T-008, T-012 |
| NFR-008 | T-009, T-012 |
| NFR-009 | T-009, T-012 |

## 4. Validation evidence

| Criterion | Result | Evidence |
|---|---|---|
| AC-001 | Passed | Run/version metadata and input tests |
| AC-002 | Passed | Producer–album construction tests |
| AC-003 | Passed | Support metric tests |
| AC-004 | Passed | Producer–band derivation tests |
| AC-005 | Passed | Layer reconciliation tests |
| AC-006 | Passed | Layer contract tests |
| AC-007 | Passed | Identity/alias tests |
| AC-008 | Passed | Solo-artist/no-type-filter tests |
| AC-009 | Passed | Self-production tests |
| AC-010 | Passed | Filter tests |
| AC-011 | Passed | Metric/concentration tests |
| AC-012 | Passed | Community determinism tests |
| AC-013 | Passed | Temporal tests |
| AC-014 | Passed | Migration/persistence tests |
| AC-015 | Passed | Replay/changed-parameter tests |
| AC-016 | Passed | Report/limitation tests |
| AC-017 | Passed | View-contract tests |
| AC-018 | Passed | Top-k/full-graph persistence tests |
| AC-019 | Passed | CLI tests |
| AC-020 | Passed | Full run net-a0b7c1f41ac5c92d |
| AC-021 | Passed | Scope guards and OpenAPI drift |
| AC-022 | Passed locally; remote CI pending | 286 tests, Ruff, format, Compose |

## 5. Notes

- NetworkX is approved by the owner for E7; do not add other dependencies without approval.
- The full E3 dataset, raw cache and E7 reports are outside Git; CI uses fixtures.
- E7 persists the full graph; E8/E10 select top-k and ego networks.
- E7 does not add API, OpenAPI or frontend changes.
- Do not mark a task complete until its verification has been executed and recorded.
- Completed analysis runs and report directories are immutable.
