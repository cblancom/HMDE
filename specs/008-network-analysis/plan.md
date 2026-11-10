# Technical plan — SPEC-008 Graph construction and network analysis

- **Status:** Approved
- **Spec:** [spec.md](spec.md)
- **Tasks:** [tasks.md](tasks.md)
- **Stage:** E7
- **Module:** `analytics`
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0004](../../docs/01-architecture/adr/ADR-0004-release-group-model.md), [ADR-0005](../../docs/01-architecture/adr/ADR-0005-identity-and-provenance.md), [ADR-0007](../../docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md), [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)

## 1. Solution summary

SPEC-008 adds a persisted, producer-centric network analysis layer over the validated E4/E5 corpus. A batch CLI loads an explicit normalization run, quality run and taxonomy version; builds a **producer–album evidence layer** from documented producer/co-producer credits; derives a **producer–band/artist layer** from the same evidence; computes support, degree, centrality, concentration, community and temporal metrics; persists the run and results in PostgreSQL; and writes JSON/Markdown reports.

E7 introduces NetworkX (approved), one additive migration (`0007`) and eight analytical tables. It does not change canonical or normalization data, does not expose HTTP endpoints and does not render a graph. E8 will read the persisted results and E10 will render the two views.

```text
normalized E4 tables + quality E5 tables + taxonomy
        │
        ▼
network input validation
  dataset · normalization · quality · taxonomy · graph version
        │
        ▼
read-only loader
  producer credits · album recordings · quality limitations
        │
        ├── producer–album evidence layer
        │      └── support ratio · scope mix · provenance
        │
        ├── producer–band/artist derived layer
        │      └── album count · years · album evidence · self-production
        │
        ├── metrics
        │      └── degree · betweenness · HHI/top-k · communities · decades
        │
        ▼
persisted analysis_run + graph_node/edge + metrics + communities
        │
        ▼
versioned JSON/Markdown report in data/network/<analysis_version>/
```

## 2. Architecture and data flow

### 2.1 Execution flow

1. Validate the selected normalization run, quality run and taxonomy version.
2. Compute a deterministic `analysis_version` from inputs, graph definition and code version.
3. Reuse a completed run with the same version; create a new run when the fingerprint differs.
4. Load producer/co-producer credits, album metadata, recording support and quality limitations read-only.
5. Build the producer–album evidence layer and compute per-edge support.
6. Derive the producer–band/artist layer and reconcile its album evidence.
7. Compute node, producer, community and temporal metrics.
8. Persist nodes, edges, metrics and communities in one transaction.
9. Write JSON/Markdown report and finish the run as completed, completed with limitations, or failed.
10. Never rewrite a completed run or report.

### 2.2 Package layout

```text
backend/src/hmde/network/
├── __init__.py
├── __main__.py          CLI entry point
├── cli.py               options, orchestration and exit codes
├── errors.py            domain errors
├── inputs.py            normalization/quality/taxonomy validation
├── loader.py            read-only SQL rows and support aggregates
├── graph.py             producer–album builder and producer–band derivation
├── metrics.py           degree, centrality, concentration, communities, decades
├── persistence.py       analysis-run lifecycle and analytical writes
├── report.py            JSON/Markdown report writer
└── runner.py            end-to-end orchestration
```

The package depends on `models`, `db`, `core` and normalized/quality outputs. It must not import API, frontend, ETL or the E6 report modules.

### 2.3 Why a separate `hmde.network` package

E6 `hmde.analytics` is report-only and does not persist runs. E7 needs a run lifecycle, graph tables, migration and support-aware loading. Keeping it in a separate package avoids turning the E6 CLI into a mixed command and keeps the E7 scope guard simple.

Alternative rejected: extend `hmde.analytics` with persisted graph orchestration. It would couple report-only E6 to database writes and make the CLI ambiguous.

## 3. Components and responsibilities

| Component or path | Responsibility |
|---|---|
| `backend/src/hmde/network/` | E7 input validation, graph building, metrics, persistence, report and CLI. |
| `backend/src/hmde/models/analytics.py` | SQLAlchemy models for analysis runs, graph layers, nodes, edges, metrics, communities. |
| `backend/alembic/versions/0007_analytics_layer.py` | Additive analytical schema migration with reversible downgrade. |
| `backend/pyproject.toml`, `backend/uv.lock` | Add the approved NetworkX dependency. |
| `data/network/` | Ignored runtime reports; never tracked. |
| `docs/03-data/network-analysis.md` | Producer-centric graph definitions, support formulas, limitations and view contract. |
| `backend/tests/unit/test_network_*.py` | Graph, support, identity, metric, report and scope unit tests. |
| `backend/tests/integration/test_network_*.py` | Migration, persistence, CLI, fixture, replay and full-run tests. |
| `README.md`, `AGENTS.md`, `docs/README.md`, `docs/00-vision/roadmap.md`, `specs/README.md` | Operational commands, current state and status. |

## 4. Technical decisions and alternatives

### 4.1 One run, two layers

One `analysis_run` owns both product layers:

- `producer_album`: direct documentary evidence;
- `producer_band`: derived aggregation of the evidence.

The layers share the same artist/album nodes and run metadata. This guarantees reconciliation and avoids two independent snapshots.

Alternative rejected: separate runs per view. It would duplicate versions and allow album and band counts to disagree.

### 4.2 Producer–album layer

Build a simple NetworkX `nx.Graph` for metrics:

- producer node = canonical `artist_id` with `producer`/`co-producer` credit;
- album node = canonical `release_group_id`;
- one simple edge per producer–album pair with `roles`, `support_ratio`, `scope_mix` and evidence;
- no band nodes.

Persist one `graph_edge` row per producer–album–role for audit, while NetworkX metrics collapse roles into one simple edge. Degree counts therefore count albums, not role multiplicities.

### 4.3 Producer–band/artist layer

Derive from the producer–album pairs:

- band/artist = `release_group.artist_id`, regardless of `Artist.type`;
- one simple producer–band edge per pair;
- weight = distinct albums;
- evidence = album IDs, titles, years, role mix and support counts;
- no album nodes;
- no self-loop when producer and band share an `artist_id`.

Self-produced albums remain in the producer–album layer and are counted on the producer node/metric as `self_produced_albums`; they do not create a producer–band edge.

### 4.4 Identity and aliases

- Node identity is `artist_id`/MBID.
- `credited_as` is stored in edge evidence, never used as a node key.
- No name normalization or fuzzy matching creates nodes.
- Display labels use the canonical artist name.
- Potential duplicate labels with different MBIDs are reported as a limitation. They are not merged.

Alternative rejected: group by display name. It is non-deterministic and violates the E4 identity model.

### 4.5 Artist type and solo artists

- No inclusion filter uses `Artist.type`.
- `release_group.artist_id` is the only band/artist source.
- Solo artists and groups appear in the same layer.
- The UI label is “band/artist” rather than “band”.

Alternative rejected: `Artist.type = 'group'`. It would incorrectly exclude valid solo acts and create an artificial product rule.

### 4.6 Support metrics

For each producer–album–role edge:

- `album_recordings`: distinct canonical album recordings from releases;
- `supporting_recordings`: distinct recording IDs carrying that producer/role credit;
- `support_ratio = supporting_recordings / album_recordings`;
- `scope_mix`: counts by `release_group`, `release` and `recording`;
- `aggregation_basis`: `release_group` when a whole-album credit exists, otherwise the observed scopes.

A release-group-scope credit is whole-album support and records ratio `1.0`. Recording-level support uses the observed ratio. No arbitrary full-album threshold is introduced; missing denominators leave `support_ratio` null with a reason.

NetworkX edge weight remains the distinct album count for product degree. Support is a displayed attribute, not silently folded into degree.

### 4.7 Metrics and communities

- Producer–album degree = distinct albums.
- Producer–band degree = distinct bands/artists.
- Weighted degree = sum of simple edge weights by layer.
- Betweenness centrality on the simple producer–band graph.
- Concentration: top-k album share, top-k band share, HHI, producers to 50%.
- Communities: Louvain on an internal producer–producer projection; edge weight = shared albums; seed `42`, resolution `1.0`.
- Temporal metrics: producer album/band counts, active producers, top-k and HHI by decade. Per-decade communities are not computed in v0.1.
- Top-k (`k = 20`) is a report/API/UI selection; persisted node and edge rows are never truncated.

Alternative rejected: album–album or artist–artist product projections. They hide the producer and are not the product question.

### 4.8 Graph versioning and idempotency

- `analysis_version` is a deterministic hash of dataset, normalization run, quality run, taxonomy, graph definition, algorithm parameters and code version.
- A completed run with the same version is reused.
- A changed input or parameter creates a new run and report directory.
- A failed/incomplete attempt is retained for audit; a rerun creates a new attempt.
- Completed runs and report directories are immutable.

### 4.9 CLI

```bash
python -m hmde.network run \
  --normalization-run 54d66992-643b-49ec-bac4-fe514ea39e94 \
  --quality-run 341824ea-5d6f-4279-bae0-f66a1e696e05 \
  --taxonomy ../data/taxonomy.json \
  --output ../data/network
```

Initial filters:

- `--decade`;
- `--subgenre`;
- `--band` (repeatable);
- `--top-k` for report leaderboards (default 20).

Core roles are fixed to `producer` and `co-producer` in v0.1. Extended roles are a future versioned graph definition.

Exit codes:

- `0`: completed;
- `1`: fatal input/execution error;
- `2`: completed with disclosed limitations.

### 4.10 Scope boundary

- No canonical/normalization/quality mutation.
- No MusicBrainz/network access.
- No API, OpenAPI or frontend change.
- No album–album or artist–artist product view.
- No full graph in an HTTP request.
- No automatic identity merging.

## 5. Data model and migrations

### 5.1 New tables

`analysis_run`:

- `id` UUID primary key;
- `analysis_version` string, indexed, not unique (failed attempts may repeat);
- `normalization_run_id`, `quality_run_id` FKs with `RESTRICT`;
- `dataset_version`, `taxonomy_version`, `graph_version`, `code_version`;
- `status` (`running`, `completed`, `completed_with_limitations`, `failed`);
- `started_at`, `finished_at`, `parameters`, `counters`, `report_path`;
- status/finished-at check and run indexes.

`graph_node`:

- `id` UUID primary key;
- `analysis_run_id` FK `RESTRICT`;
- `node_key` (`artist:<uuid>` or `album:<uuid>`);
- `node_type` (`artist`, `album`);
- `entity_id`, `mbid`, `label`;
- `roles` JSONB (for example `["producer"]`, `["producer","band"]`);
- `attributes` JSONB (artist type, album year/decade, band metadata, taxonomy, quality status, self-produced flag);
- unique `(analysis_run_id, node_key)`; indexes by run/type and run/label.

`graph_edge`:

- `id` UUID primary key;
- `analysis_run_id` FK `RESTRICT`;
- `layer_code` (`producer_album`, `producer_band`);
- `source_node_id`, `target_node_id` FKs to `graph_node.id` with `RESTRICT`;
- `role_code` (`producer`, `co-producer`, or `mixed` for producer–band);
- `weight`, `supporting_recordings`, `album_recordings`, `support_ratio`;
- `scope_mix`, `evidence` JSONB;
- unique `(analysis_run_id, layer_code, source_node_id, target_node_id, role_code)`;
- layer/source/target indexes; support-ratio range check.

`node_metric`:

- run, node, layer, metric code, value, numerator, denominator, unit, details;
- unique `(analysis_run_id, node_id, layer_code, metric_code)`.

`producer_metric`:

- run, producer node, metric code, value, numerator, denominator, unit, details;
- unique `(analysis_run_id, producer_node_id, metric_code)`.

`temporal_metric`:

- run, layer, scope type/key, metric code, numerator, denominator, value, unit, details;
- unique `(analysis_run_id, layer_code, scope_type, scope_key, metric_code)`.

`community` and `community_membership`:

- community run, stable community key, algorithm, resolution, size and details;
- membership run, community, producer node;
- unique run/community and run/community/node.

### 5.2 Migration

- Add `backend/alembic/versions/0007_analytics_layer.py`, `down_revision = "0006"`.
- Upgrade creates the tables, constraints and indexes.
- Downgrade drops them in reverse dependency order.
- No canonical or normalization table is altered.
- Run `alembic upgrade head`, downgrade to `0006`, upgrade head, and migration tests.

### 5.3 Persistence transaction

- Create `analysis_run` with `running`.
- Insert graph nodes and edges in deterministic order.
- Insert metrics, communities and memberships.
- Finish the run and persist counters.
- On failure, mark the run `failed` and roll back partial analytical rows.
- A completed run is never deleted or updated.

## 6. API contract

No changes.

- No endpoints, request/response schemas or OpenAPI changes.
- E8 will consume persisted tables; E10 will consume E8.
- OpenAPI drift must remain empty.
- E7 must not import API modules.

## 7. Frontend impact

None in E7.

- No routes, components, generated types or build changes.
- E7 persists the view contract: producer artist type, album year, roles, support ratio, album evidence and self-produced flags.
- E10 owns colors, shapes, layout, top-k selection and accessible fallback.

## 8. Error handling and consistency

- Missing normalization/quality run: fail before writes.
- Non-terminal or mismatched runs: fail with explicit reason.
- Taxonomy/version mismatch: fail.
- No producer credits: persist an empty graph, zero metrics and a limitation; do not fail.
- Missing album date: exclude from decade metrics and report.
- Missing album recordings/denominator: `support_ratio = null` with a reason.
- Duplicate node/edge key: deterministic dedupe; report a counter.
- Same-name different-MBID artists: separate nodes plus a limitation.
- Self-produced album: one node, no self-loop, explicit metric.
- Interrupted run: failed status, no completed report; rerun is safe.
- Existing completed version with different content: fail; never overwrite.
- Non-deterministic community output: block completion if the seed/order checks fail.

## 9. Security and trust boundaries

- Read-only access to canonical, normalization and quality tables.
- No secrets, tokens, raw payloads or external requests in logs/reports.
- The batch process has no HTTP surface.
- Report evidence contains canonical IDs and labels only.
- Identity remains deterministic; no fuzzy merge.
- Missing data is reported as missing, never as a negative credit.

## 10. Observability

- Logs include analysis version, dataset/normalization/quality/taxonomy versions, graph version, code version, runtime, node/edge/metric counts and report path.
- `analysis_run.counters` records source counts, nodes/edges by layer, support-null counts, self-produced albums, communities and limitations.
- Reports reconcile persisted counts with source counts.
- No raw payloads or secrets in logs.

## 11. Testing strategy

| Level | What is tested | Evidence |
|---|---|---|
| Unit | Input validation, support ratio, identity, graph builder, producer–band derivation, self-production, metrics, communities, temporal, report. | `backend/tests/unit/test_network_*.py` |
| Integration | Migration, run lifecycle, persistence, CLI, replay, fixture run, corpus-expansion replay. | `backend/tests/integration/test_network_*.py` |
| Contract | No API/OpenAPI/frontend change; scope guards. | Existing suite and `test_openapi.py` |
| Manual | Full 57-band run, support review, top producers and view metadata. | T-011 |
| CI | Fixture-level network run, no full dataset/network. | GitHub Actions |

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

- Add NetworkX to `backend/pyproject.toml` and refresh `uv.lock` with `uv sync`.
- Apply migration `0007` after `0006`.
- Add `data/network/*/` to `.gitignore`.
- Add `data/README.md` and `docs/03-data/network-analysis.md` documentation.
- Downgrade `0007` removes only analytical tables.
- Old runs/reports remain readable; no canonical data is removed.

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Producer–album and producer–band counts disagree | Derive band edges from album evidence and reconcile in tests/report. |
| Name variants create duplicate nodes | Key by `artist_id`/MBID; `credited_as` is metadata; duplicate-label report only. |
| Solo artists excluded | No `Artist.type` filter; explicit fixture test. |
| Self-produced band creates a self-loop | One node, flagged, no producer–band self-edge; explicit test. |
| Support overstates partial credits | Store ratio, scope mix and counts; no invented full-album threshold. |
| Full graph is visually saturated | Persist full graph; E8/E10 use top-k and ego networks. |
| Album/band nodes mixed again | Separate layer contracts and no album nodes in producer–band or band nodes in producer–album. |
| Community output is unstable | Seed, resolution, implementation version and deterministic checks. |
| NetworkX version changes algorithms | Pin dependency in `uv.lock`; record graph version and code version. |
| Full corpus unavailable in CI | Fixture-level graph tests; full run is a batch gate. |
| Color-only encoding is inaccessible | E7 persists metadata; E10 must add legend, shapes and table fallback. |

## 14. Traceability requirements → plan → tasks

| Requirement | Plan section | Tasks |
|---|---|---|
| FR-001 | 2.1, 4.8 | T-001, T-003, T-007, T-011 |
| FR-002 | 4.2 | T-003, T-004 |
| FR-003 | 4.6 | T-003, T-004 |
| FR-004 | 4.3 | T-005 |
| FR-005 | 4.7 | T-006 |
| FR-006 | 4.7 | T-006 |
| FR-007 | 4.7 | T-006 |
| FR-008 | 5.1, 5.2 | T-002, T-007 |
| FR-009 | 4.8, 5.3 | T-007, T-010 |
| FR-010 | 4.4, 4.5 | T-004, T-005 |
| FR-011 | 4.6, 8 | T-003, T-008 |
| FR-012 | 4.9, 8 | T-007, T-008 |
| FR-013 | 4.9 | T-008 |
| FR-014 | 4.7, 4.9 | T-009, T-011 |
| FR-015 | 5.1, 7 | T-009, T-012 |
| FR-016 | 4.10 | T-009, T-012 |

| Non-functional requirement | Plan section | Tasks |
|---|---|---|
| NFR-001 | 4.8 | T-007, T-010 |
| NFR-002 | 2.1, 11 | T-010, T-011 |
| NFR-003 | 4.7, 4.8 | T-006, T-010 |
| NFR-004 | 5.1, 5.3 | T-002, T-007 |
| NFR-005 | 1, 12 | T-001, T-012 |
| NFR-006 | 9 | T-009, T-012 |
| NFR-007 | 10 | T-008, T-012 |
| NFR-008 | 2.2, 4.10 | T-009, T-012 |
| NFR-009 | 7, 11 | T-009, T-012 |

## 15. Approval and next step

This plan and `tasks.md` must be approved together before implementation. The first task is T-001: add NetworkX, create the `hmde.network` package skeleton and validate E7 inputs.
