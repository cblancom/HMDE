# SPEC-008 — Graph construction and network analysis

- **Status:** Validated
- **Stage:** E7
- **Iteration:** MVP
- **Module:** `analytics`
- **Date:** 2026-11-09
- **Depends on:** SPEC-007 validated; normalized run `54d66992-643b-49ec-bac4-fe514ea39e94`; quality run `341824ea-5d6f-4279-bae0-f66a1e696e05`; EDA report `eda-1267fdcced62b7da`; E3 dataset `mb-20261107T194927Z-0d6cedd5c261`; [taxonomy](../../data/taxonomy.json) v0.2.0; [ADR-0007](../../docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md); [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0004](../../docs/01-architecture/adr/ADR-0004-release-group-model.md), [ADR-0005](../../docs/01-architecture/adr/ADR-0005-identity-and-provenance.md), [ADR-0007](../../docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md), [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)
- **Plan:** [plan.md](plan.md) (approved).
- **Tasks:** [tasks.md](tasks.md) (validated).
- **Conventions:** [Engineering conventions](../../docs/01-architecture/conventions.md)
- **Owner:** Cristian

## Revision history

| Revision | Date | Change |
|---|---|---|
| 1 | 2026-11-09 | Initial draft; E7 graph snapshots, metrics, communities and temporal analysis |
| 2 | 2026-11-09 | Reframed around producer–album and producer–band views; support-aware edges; identity, solo-artist and self-production rules; NetworkX approved |
| 3 | 2026-11-09 | Technical plan and tasks drafted for review |
| 4 | 2026-11-10 | T-001–T-012 implemented locally; full E7 run completed |
| 5 | 2026-11-10 | Remote CI run 42738375416 passed; SPEC-008 validated |

## 1. Context and problem

E6 validated the exploratory baseline: 57 bands, 731 canonical albums, 32,665 credit contexts and descriptive producer/co-credit statistics. E7 must turn that baseline into reproducible network snapshots without changing the normalized data, the API contract or the frontend.

The product question is producer-centric: **which producers concentrate albums and bands, and how do those producers connect the documented scene?** The graph must therefore make the producer a visible node and must not hide the producer inside an album–album or artist–artist projection.

The corpus contains 384 artists with producer/co-producer credits and 1,134 producer–album assignments across 731 albums. A canvas that mixes album and band nodes is visually saturated and semantically ambiguous. The product therefore uses two separate views over one evidence base:

1. **Producer–Album** — the direct, documented evidence view.
2. **Producer–Band** — a derived concentration and overview view.

The graph must preserve the three credit scopes, the documented role vocabulary and the support level of each producer–album credit. It must avoid inventing edges from missing data and persist every run with dataset, taxonomy, quality and algorithm versions.

E7 is the first stage that writes analytical results to the database. It does not expose them through HTTP; E8 owns the read API and E9/E10 own presentation. NetworkX is approved as the graph library for E7.

```text
normalized albums + credits + taxonomy + quality
        │
        ▼
E7 analysis run
  producer–album evidence layer
  producer–band derived layer
  support metrics · centrality · communities · temporal slices
        │
        ├── analysis_run
        ├── graph_node / graph_edge
        ├── node_metric / producer_metric / temporal_metric
        ├── community / community_membership
        └── JSON/Markdown network report
        │
        ▼
E8 read API (top-k overview, producer ego networks, filtered subgraphs)
        │
        ▼
E10 producer-centric graph views
```

## 2. Users and actors

- **Analyst/developer:** runs graph snapshots, reviews producer concentration, support levels and community results.
- **System actor:** PostgreSQL supplies normalized entities, credits and quality metadata; NetworkX computes graph metrics.
- **Future consumers:** E8 API, E9/E10 UI and E13 expanded-corpus validation.
- **Project owner:** approves graph definitions, algorithm parameters and dependency changes.

There are no end-user roles, authentication or write API in E7. The E7 operator does not build a graph per selected album or band; E7 builds one versioned corpus snapshot.

## 3. Product graph model

### 3.1 Canonical evidence

The only source of edges is a documented credit:

```text
artist with role producer/co-producer ── credit ── canonical album
                                                        │
                                                        └── release_group.artist_id = band/artist
```

- The producer identity is the canonical `artist_id` derived from MBID.
- The album identity is the canonical `release_group.id` derived from MBID.
- The band/artist identity is the canonical `release_group.artist_id`.
- No edge is created from name similarity, missing data or an inference.
- `credited_as` preserves the source's spelling of a credit, but never creates a second node.

### 3.2 View A — Producer–Album

The **Producer–Album** view is the canonical evidence view.

- **Nodes:** `producer` and `album`.
- **Edges:** `produced` from producer to album.
- **Producer:** artist with `producer` or `co-producer` credit on the album.
- **Album metadata:** title, primary band/artist, first release date/year/decade, primary and secondary taxonomy leaves, quality status.
- **Edge metadata:** role, credit scope mix, supporting recording count, album recording count, support ratio, provenance references.
- **Band nodes:** not present. The band is album metadata, not a node in this canvas.
- **Album–album projection:** not a product view.

This view answers:

- Which albums did producer P produce?
- In which decades and subgenres did P concentrate?
- Which producers concentrate album assignments?
- How well supported is each producer–album edge?

### 3.3 View B — Producer–Band

The **Producer–Band** view is derived from the Producer–Album evidence.

- **Nodes:** `producer` and `band/artist`.
- **Edges:** `produced_for` from producer to band/artist.
- **Band/artist:** the canonical primary artist of the album (`release_group.artist_id`), regardless of `Artist.type`.
- **Edge metadata:** distinct album count, role mix, first and last year, album evidence (IDs, titles, years), full/partial support counts.
- **Album nodes:** not present. Albums are edge evidence and expand from the edge.
- **Band–band or album–album projection:** not a product view.

This view answers:

- Which bands/artists did producer P work with?
- Which producers work with the largest number of bands/artists?
- Which producers connect bands/artists across decades and subgenres?
- Which bands/artists share a producer?

### 3.4 Inclusion rules

The graph includes:

- producer and co-producer roles by default;
- all canonical albums in the selected dataset;
- all primary artists of those albums, including solo artists and groups;
- unclassified albums in general views, with their quality status visible;
- documented credits only.

The graph excludes by default:

- executive producer, engineer, mix and mastering roles; these are a future configurable extension;
- album–album and artist–artist product projections;
- inferred, uncertain or missing relationships not present in the normalized credit data.

There is **no `Artist.type = 'group'` filter**. A solo artist such as Rod Stewart and a group such as Led Zeppelin are both eligible; "band" in the UI means "band/artist" or "primary act".

### 3.5 Identity and alias rules

- Node identity is `artist_id`/MBID, never display name.
- `credited_as` is stored and shown as credit-level metadata, not as identity.
- Variants such as "Martin Birch" and "Martin ‘Black Night’ Birch" under the same MBID collapse to one node.
- Two different MBIDs for the same person are not merged automatically. They remain separate and are reported as a quality limitation; automatic fuzzy merging is out of scope.
- Display labels use the canonical artist name; alias variants appear in tooltip/evidence.

### 3.6 Self-produced bands

If a band/artist produces its own album, producer and band/artist share the same `artist_id`.

- One canonical node is used; no duplicate node is created.
- No producer–band self-loop is drawn.
- The node is marked as `group`/self-produced in the Producer–Band view.
- The albums remain in the Producer–Album view and in the Producer–Band edge evidence or a `self_produced_albums` counter.
- Self-produced albums count toward producer album metrics and are disclosed separately from producer–band edges.

### 3.7 Full snapshot versus presentation selection

E7 builds and persists one full snapshot for the selected corpus.

- **E7:** full graph snapshot, all layers and metrics.
- **E8:** top-k rankings, producer/band/album seed selection, filtered subgraphs.
- **E10:** interactive view with top-k overview and producer ego networks.

The E7 CLI may filter an analysis run for reproducibility (role, scope, decade, taxonomy, band/album subset), but the default product snapshot is the full active corpus. A filter or parameter change creates a new `analysis_run`; it does not mutate an existing snapshot.

### 3.8 Visual grammar for E10

E7 must persist the metadata needed by E10. E10 owns the actual rendering.

| Element | Encoding |
|---|---|
| Producer, individual person | Circle, blue |
| Producer, group or self-produced band | Hexagon, orange |
| Producer, unknown artist type | Circle, gray |
| Album | Square, continuous year color scale |
| Band/artist | Rounded rectangle, neutral |
| Album with missing date | Gray/hatched square |
| `producer` edge | Solid line |
| `co-producer` edge | Dashed line |
| Album support level | Edge width/opacity from `support_ratio` |
| Producer–band edge weight | Edge width from distinct album count |

The album year scale must be sequential and colorblind-safe (Cividis, Viridis or equivalent), with a legend from 1960 to 2026 and decade ticks. Color is never the only channel: labels, tooltips and an accessible table alternative must expose the same information.

The Producer–Band overview defaults to a top-k view (initial `k = 20`, configurable) by album count or band/artist count. Selecting a producer opens that producer's ego network in both views. No product view renders all 731 albums and all bands in one canvas.

## 4. User stories and flows

### US-001 — Build the producer–album evidence graph

As an analyst, I want a reproducible producer–album graph so that every producer relationship is backed by a documented credit.

**Expected flow:**

1. The operator selects a normalization run and quality run.
2. The runner loads canonical albums, credits, recordings, band/artist metadata and quality findings.
3. It creates producer and album nodes and role-bearing `produced` edges.
4. It computes support metrics per edge.
5. It persists the layer under an `analysis_run`.
6. The report records dataset, taxonomy, quality, algorithm and code versions.

### US-002 — Derive the producer–band view

As an analyst, I want a producer–band view so that I can see concentration and connections without mixing albums and bands in one canvas.

**Expected flow:**

1. The runner groups producer–album evidence by producer and album primary artist.
2. It creates one `produced_for` edge per producer–band/artist pair.
3. The edge records distinct album count, roles, years and album evidence.
4. Self-produced pairs are represented without a self-loop and are flagged.
5. The edge counts reconcile with the producer–album layer.

### US-003 — Measure support and concentration

As an analyst, I want support-aware edges and concentration metrics so that I do not overstate partial credits.

**Expected flow:**

1. The runner computes supporting recordings and album recordings for each producer–album pair.
2. It stores `support_ratio`, `scope_mix` and `aggregation_basis`.
3. It computes album counts, band/artist counts, top-k and HHI.
4. It reports the distribution of full and partial support.
5. No fixed full-album threshold is invented; the ratio and scope are visible.

### US-004 — Analyze temporal and community structure

As an analyst, I want decade slices and communities so that producer concentration and collaboration structure can be compared over time.

**Expected flow:**

1. The runner groups albums by first-release decade.
2. It computes full-graph and per-decade metrics.
3. It computes communities on an internal producer–producer projection.
4. Communities remain analytical results; they are not a primary product view.
5. Historical runs remain immutable.

### US-005 — Review quality and identity limitations

As an analyst, I want identity and quality limitations visible so that the graph is not overinterpreted.

**Expected flow:**

1. The run records the quality run and approved exceptions.
2. Name variants under one MBID remain one node and show `credited_as`.
3. Potential duplicate names with different MBIDs are reported, never merged by name.
4. Missing credits and self-produced albums remain explicit.
5. The report states that absence is not negative evidence.

### US-006 — Reproduce and extend the graph

As a developer, I want deterministic graph runs so that snapshots can be audited and extended when the corpus grows.

**Expected flow:**

1. The same inputs, parameters and code version reproduce the same graph and metrics.
2. A new corpus or parameter set creates a new analysis run.
3. Old graph snapshots and reports remain readable.
4. No canonical or normalization data is rewritten.

## 5. Functional requirements

### FR-001 — Inputs and analysis-run metadata

The graph run must select and validate:

- normalization run and dataset version;
- quality run and taxonomy version;
- graph algorithm version and parameter set;
- code version and timestamps;
- node/edge counts, failures and output paths.

It must reject missing, mismatched or non-terminal inputs before writing graph data.

**Verification:** input and run-metadata tests.

### FR-002 — Producer–album evidence layer

The default evidence layer must contain:

- one `producer` node per canonical artist with a `producer` or `co-producer` credit;
- one `album` node per canonical album with such a credit;
- one role-bearing `produced` edge per producer–album–role relationship;
- canonical IDs/MBIDs and album decade/taxonomy/quality metadata;
- band/artist metadata on the album, not as a node.

No edge may be created from missing data or name similarity.

**Verification:** graph-construction tests on fixture albums and credits.

### FR-003 — Support-aware edge semantics

Every producer–album edge must record:

- role (`producer` or `co-producer`);
- credit scopes represented;
- supporting recording count;
- album recording count;
- `support_ratio` where the denominator is available;
- `aggregation_basis` and provenance references.

The run must support filtering by role, credit scope, album decade, taxonomy and band/artist. There is no fixed full-album threshold; the ratio and scope are the authoritative support information.

**Verification:** support-ratio, scope-mix and filter tests.

### FR-004 — Producer–band derived layer

The runner must derive a producer–band/artist layer from the producer–album evidence:

- one producer node;
- one band/artist node per canonical album primary artist;
- one `produced_for` edge per producer and band/artist pair;
- edge weight = distinct albums;
- edge evidence = album IDs, titles, years, roles and support classes;
- no album nodes and no duplicate projection edges;
- no self-loop when producer and band/artist share the same `artist_id`.

The layer must reconcile its album evidence with FR-002.

**Verification:** derivation, self-loop, album-evidence and reconciliation tests.

### FR-005 — Producer and graph metrics

At minimum, compute and persist:

- producer album degree and weighted degree;
- producer band/artist degree;
- graph-level node/edge/component counts;
- betweenness centrality for documented graph sizes;
- top-k rankings by album count and band/artist count;
- concentration metrics (HHI and top-k share).

Algorithm names, parameters and approximations must be recorded. Metrics must be descriptive and non-causal.

**Verification:** hand-calculated metric and graph-count tests.

### FR-006 — Community detection

The runner must detect and persist communities using a supported algorithm, initially Louvain or an equivalent deterministic implementation.

Communities are computed on an internal producer–producer projection based on shared albums; they are not a primary graph view.

- Random seed, resolution and implementation must be recorded.
- Community size and membership must be persisted.
- Ties and unstable small communities must be flagged.
- Community labels must not imply affinity or influence.

**Verification:** deterministic community fixture and seed tests.

### FR-007 — Temporal network analysis

The runner must compute network metrics by canonical album decade from 1960s through 2020s, plus an explicit missing-date category for excluded albums.

It must preserve full-graph and per-decade parameters and report missing-date counts.

**Verification:** decade boundary and missing-date tests.

### FR-008 — Persisted analytical schema

The run must persist at least:

- `analysis_run`;
- `graph_node`;
- `graph_edge`;
- `node_metric`;
- `producer_metric` or an equivalent documented artist metric table;
- `temporal_metric`;
- `community`;
- `community_membership`.

Every row must reference the run. Graph edges must identify their layer (`producer_album` or `producer_band`). Node identity must be unique within a run; an artist node may carry both `producer` and `band` roles when relevant.

Old runs and reports must remain immutable.

**Verification:** migration, FK, uniqueness and run-isolation tests.

### FR-009 — Idempotency and graph versioning

Re-running the same inputs and parameters must be idempotent. A changed corpus, taxonomy, quality run, graph definition or parameter set must create a new `analysis_run`. Existing graph snapshots must never be overwritten or deleted.

**Verification:** replay and changed-parameter tests.

### FR-010 — Identity, aliases and artist type

- Nodes are keyed by canonical `artist_id`/MBID.
- `credited_as` never creates a node.
- No inclusion filter uses `Artist.type`.
- Solo artists and groups are both included as band/artist nodes.
- Potential duplicate names with different MBIDs are reported as a data-quality limitation and are not merged by name.
- Self-produced artists use one node and no self-loop.

**Verification:** identity, solo-artist, alias and self-production tests.

### FR-011 — Quality and missing-data handling

The run must:

- load the selected quality run and its approved exceptions;
- report the 24 quarantined and 34 review cases as limitations;
- not invent credits or affiliations for missing data;
- distinguish missing edges from negative relationships;
- avoid silently dropping unclassified albums from non-taxonomy metrics;
- report self-produced albums separately from producer–band edges.

**Verification:** report assertions and exception-count checks.

### FR-012 — Network report

The run must produce JSON and Markdown reports containing:

- dataset, normalization, quality, taxonomy, algorithm and code versions;
- graph counts, filters and parameters by layer;
- top producers by album count and band/artist count;
- support-ratio distribution and partial-credit counts;
- community and temporal summaries;
- identity and quality limitations, including possible duplicate names;
- deterministic ordering and a non-causal interpretation warning.

**Verification:** report snapshot and structured assertions.

### FR-013 — CLI and stable exit codes

A documented CLI must support:

- full graph run;
- explicit normalization and quality runs;
- role, scope, decade, taxonomy and band/album filters;
- algorithm parameters and output selection;
- graph-layer selection for diagnostic runs;
- stable exit codes for success, advisory limitations and fatal errors.

**Verification:** parser, filter and exit-code tests.

### FR-014 — Performance and presentation limits

The graph run must complete for the 57-band corpus within a documented batch window and persist node/edge counts. The report must expose the largest connected component and warn when a layer exceeds safe visualization limits.

E7 persists the full graph. Top-k and ego-network selection are E8/E10 presentation concerns; E7 must not truncate persisted data for presentation convenience.

**Verification:** runtime evidence and size-limit tests.

### FR-015 — Graph view contract

The persisted data must expose enough metadata for E8/E10 to render:

- node role (`producer`, `album`, `band/artist`, including dual roles);
- artist type for producer color/shape;
- album year/decade for the sequential color scale;
- band/artist name and taxonomy for album metadata;
- role and support ratio on producer–album edges;
- album count, years and album evidence on producer–band edges;
- self-produced flags.

The visual contract must support colorblind-safe rendering and an accessible table fallback.

**Verification:** API-ready shape tests and metadata completeness checks.

### FR-016 — Scope boundary

E7 must not:

- change canonical, normalization or quality data;
- re-ingest MusicBrainz or use network access;
- change API endpoints, OpenAPI or frontend code;
- infer causal relationships, affinity or listener preference;
- merge artists or albums beyond E4 identity decisions;
- expose album–album or artist–artist projections as product views.

**Verification:** migration/schema diff, OpenAPI drift, scope guards and code inspection.

## 6. Non-functional requirements

### NFR-001 — Reproducibility

Graphs, metrics and communities must be reproducible from the same inputs, parameters and code version.

### NFR-002 — Performance

A full 57-band graph run should complete within 15 minutes on the development environment. Fixture-level graph tests should complete in ordinary CI time.

### NFR-003 — Determinism

Node/edge ordering, metric ordering and community assignment must be deterministic; random algorithms must use an explicit seed.

### NFR-004 — Data safety

E7 is read-only for canonical and normalization data. Graph tables and reports are append/versioned audit outputs.

### NFR-005 — Compatibility

Python 3.13, PostgreSQL 16, Docker Compose, uv, pytest and Ruff remain supported. NetworkX is approved for E7; its version and integration are fixed in the plan.

### NFR-006 — Security

No secrets, tokens or raw payloads in logs or reports. The batch process has no write HTTP surface.

### NFR-007 — Observability

Runs log phases, graph sizes, metrics, community counts, filters, runtime and failures. Report counters reconcile with persisted rows.

### NFR-008 — Maintainability

Graph logic lives under the analytics boundary and depends on models/db/quality outputs, not API or frontend code.

### NFR-009 — Accessibility and language

All code, documentation, report labels, legends and warnings are in English. Visual encodings must not rely on color alone and must have a table alternative.

## 7. Business rules

- **BR-001:** Edges require documented credits; missing data is not negative evidence.
- **BR-002:** MBID/canonical IDs are the only node identity keys.
- **BR-003:** Producer–album is the evidence layer; producer–band is derived from it.
- **BR-004:** Role and scope filters must be recorded in every run.
- **BR-005:** Community and centrality results are descriptive, not causal or affinity measures.
- **BR-006:** Every analytical row references an `analysis_run`.
- **BR-007:** Graph snapshots are versioned and immutable; corpus changes create new runs.
- **BR-008:** Quality exceptions, missing-date counts and self-produced albums remain visible.
- **BR-009:** E7 does not expose API or frontend features; E8/E9 follow.
- **BR-010:** No analytical result is recomputed implicitly on an API request in E7.
- **BR-011:** No inclusion rule filters on `Artist.type`; solo artists and groups are both eligible.
- **BR-012:** No producer–band self-loop is created for self-produced albums.
- **BR-013:** Album and band nodes are never mixed in the same product canvas.

## 8. Edge cases and errors

- Missing normalization/quality run: fail before graph writes.
- Version mismatch: fail with explicit reason.
- Empty graph or no producer credits: report zero counts and limitations.
- Album with missing date: exclude from decade slices and report; keep in general graph.
- Album without classification: keep in general graph; exclude from taxonomy-specific filters and report.
- Artist with only missing/unknown role: no edge; quarantine/quarantine finding, not an invented edge.
- Duplicate node/edge keys: deduplicate deterministically and report.
- Same name, same MBID: one node; `credited_as` is metadata.
- Same name, different MBIDs: separate nodes plus a quality limitation; no automatic merge.
- Self-produced album: one node, no self-loop, explicit flag.
- Solo artist as album primary artist: included without a group filter.
- Production credit on one recording only: edge is kept with a low support ratio and scope disclosure.
- Projection exceeds safe size: persist with a warning; API limits remain E8.
- Community algorithm instability: record seed/resolution and flag small/unstable communities.
- Interrupted run: mark failed/incomplete; preserve completed rows; rerun idempotently.
- Re-run with different parameters: new analysis run; old rows unchanged.

## 9. Out of scope

- API endpoints, OpenAPI, frontend or UI implementation.
- Re-ingestion, source expansion or raw data changes.
- Album–album and artist–artist product projections.
- Causal inference, influence attribution or listener preferences.
- Album-level classification changes.
- Canonical identity merges beyond E4.
- Automatic fuzzy merging of duplicate MBIDs.
- Full visualization implementation.
- Scheduled production jobs.

## 10. Acceptance criteria

| ID | Criterion | Evidence |
|---|---|---|
| AC-001 | Graph run validates and records normalization, quality, taxonomy, algorithm and code versions. | Input/run tests |
| AC-002 | Producer–album layer nodes and role-bearing edges reconcile with canonical albums and producer/co-producer credits. | Graph construction tests |
| AC-003 | Producer–album edges expose scope mix, supporting recordings, album recordings and `support_ratio`. | Support metric tests |
| AC-004 | Producer–band layer derives one edge per producer and band/artist with album count and evidence. | Derivation tests |
| AC-005 | Producer–band album evidence reconciles with producer–album edges. | Reconciliation tests |
| AC-006 | No band nodes appear in Producer–Album and no album nodes appear in Producer–Band. | Layer contract tests |
| AC-007 | Artist nodes are keyed by `artist_id`/MBID; `credited_as` variants do not create nodes. | Identity/alias tests |
| AC-008 | Solo artists and groups are included; no `Artist.type` inclusion filter exists. | Solo-artist tests and code inspection |
| AC-009 | Self-produced albums produce one node, no self-loop and an explicit flag. | Self-production tests |
| AC-010 | Role, scope, decade, taxonomy and band/album filters are applied and recorded. | Filter tests |
| AC-011 | Degree, weighted degree, betweenness and concentration metrics match hand-calculated fixtures. | Metric tests |
| AC-012 | Community detection is deterministic with recorded seed/resolution and is internal-only. | Community tests |
| AC-013 | Decade metrics cover 1960s–2020s and exclude/report missing dates. | Temporal tests |
| AC-014 | All analytical tables persist nodes, edges, metrics, communities and run references by layer. | Migration/persistence tests |
| AC-015 | Replaying the same inputs is idempotent; changed parameters create a new run. | Replay tests |
| AC-016 | Quality exceptions, duplicate-name risks and self-produced albums appear in the report. | Report/limitation checks |
| AC-017 | Graph view metadata supports producer type, album year, role and support visual encodings. | View-contract tests |
| AC-018 | Top-k and ego-network selections are left to E8/E10; E7 persists the full graph. | API/performance tests |
| AC-019 | CLI supports filters, algorithm parameters and stable exit codes. | CLI tests |
| AC-020 | Full 57-band graph run completes within the documented window and persists results. | Full-run evidence |
| AC-021 | No canonical, normalization, API, OpenAPI or frontend change occurs. | Schema/API/scope checks |
| AC-022 | Full backend tests, Ruff, format and remote CI pass. | Local and CI evidence |

## 11. Assumptions and resolved decisions

### Assumptions

- SPEC-007 remains validated and its EDA definitions inform graph parameters.
- The full corpus is available for batch runs; ordinary CI uses fixtures.
- E7 persists analytical results but does not expose them over HTTP.
- The first graph uses documented credits only and preserves role/scope attributes.

### Resolved decisions

| Decision | Resolution |
|---|---|
| Graph library | NetworkX approved for E7; version and integration fixed in the plan. |
| Product views | Two separate views: Producer–Album and Producer–Band. No mixed album/band canvas. |
| Evidence vs derivation | Producer–Band is derived from Producer–Album; album evidence is preserved. |
| Default roles | `producer` and `co-producer`; extended roles are a future configurable extension. |
| Band/artist definition | `release_group.artist_id`; no `Artist.type = 'group'` filter; solo artists included. |
| Identity | `artist_id`/MBID; `credited_as` is not identity; no name-based merging. |
| Self-produced bands | One node, no self-loop, explicit flag. |
| Support metric | Show `support_ratio`, scope mix and counts; no invented fixed full-album threshold. |
| Overview | Top-k by default (initial `k = 20`), plus selected-producer ego networks. |
| Edge expansion | Producer–Band edges expand to album evidence. |
| Visual encoding | Producer type by shape/color; album year by sequential color; role by edge style; support by width/opacity. |
| Product projections | Album–album and artist–artist projections are not product views; producer–producer is internal for communities. |

### Non-blocking design detail

- The exact color tokens, label placement and collapse behavior of album nodes are E10 design decisions. E7 must expose the metadata; E10 must preserve the semantic encoding and accessibility fallback.

## 12. Validation result

- **Date:** 2026-11-10
- **Verdict:** Validated
- **Evidence:** Full E7 run `net-a0b7c1f41ac5c92d` persisted 1,151 producer–album role edges, 1,134 simple edges, 426 producer–band edges and 78 communities. 286 backend tests, Ruff/format, migration replay, OpenAPI drift and Compose validation passed locally. Remote CI run [42738375416](https://github.com/cblancom/HMDE/actions/runs/42738375416) passed for commit `5001552`. See `tasks.md`.

## 13. References

- [Constitution](../../constitution.md)
- [AGENTS.md](../../AGENTS.md)
- [Vision](../../docs/00-vision/vision.md)
- [Scope](../../docs/00-vision/scope.md)
- [Roadmap](../../docs/00-vision/roadmap.md)
- [Data model v0](../../docs/01-architecture/data-model.md)
- [EDA metrics](../../docs/03-data/eda-metrics.md)
- [Data quality rules](../../docs/03-data/data-quality.md)
- [ADR-0005 — Identity and provenance](../../docs/01-architecture/adr/ADR-0005-identity-and-provenance.md)
- [ADR-0007 — Credit scope](../../docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md)
- [ADR-0008 — Taxonomy, corpus and versioning](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)
- [SPEC-007 — Exploratory analysis](../007-eda-metrics/spec.md)
