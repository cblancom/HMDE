# Producer network analysis (E7)

- **Status:** Validated
- **Stage:** E7
- **Spec:** [SPEC-008](../../specs/008-network-analysis/spec.md)
- **Migration:** `0007_analytics_layer`
- **Local run:** `91f39a30-fa51-4d75-a9a2-1b5605bd98c3` / `net-a0b7c1f41ac5c92d`

## 1. Purpose

E7 turns the validated E4/E5 corpus into reproducible producer-centric network snapshots. It answers the product question directly: **which producers concentrate albums and bands/artists, and how do those producers connect the documented scene?**

The analysis is batch-only in E7. It writes PostgreSQL analytical tables and versioned JSON/Markdown reports; it does not expose HTTP endpoints or render graphs. E8 reads the persisted results and E10 renders the two views.

## 2. Two product views over one evidence base

### 2.1 Producer–Album

The evidence layer is a bipartite graph:

```text
producer ── produced ── album
```

- Producer nodes are canonical artists with `producer` or `co-producer` credits.
- Album nodes are canonical albums with at least one such credit.
- The album carries band/artist metadata, year, decade, taxonomy and quality status.
- Band/artist nodes are not present in this layer.
- One persisted edge exists per producer–album–role; the NetworkX metric graph collapses roles to one simple edge.

This view answers which albums a producer made, the support of each credit, and album concentration by decade/subgenre.

### 2.2 Producer–Band/Artist

The derived layer aggregates the evidence:

```text
producer ── produced_for ── band/artist
```

- Band/artist is the canonically credited primary artist of the album (`release_group.artist_id`).
- `Artist.type` is **not** an inclusion filter. Solo artists and groups are both eligible.
- Album nodes are not present; albums are edge evidence.
- Edge weight is the number of distinct albums.
- Self-produced albums use one node and do not create a self-loop.

This view answers which bands/artists a producer worked with and which producers connect the largest number of acts.

Album–album and artist–artist projections are not product views. A producer–producer projection is computed internally only for community detection.

## 3. Supporting evidence on producer–album edges

Each persisted producer–album–role edge stores:

| Field | Meaning |
|---|---|
| `supporting_recordings` | Distinct recordings supporting the credit |
| `album_recordings` | Distinct recordings in the canonical album |
| `support_ratio` | `supporting_recordings / album_recordings` |
| `scope_mix` | Count of credits by `release_group`, `release`, `recording` |
| `evidence` | Credit IDs, source-record IDs, `credited_as` variants and statuses |

A release-group-scope credit is whole-album support and records `support_ratio = 1.0`. Recording-level support uses the observed ratio. If the denominator is unavailable, the ratio is `null`; no threshold is invented and no partial credit is silently treated as full-album support.

Expanded corpus run support distribution:

- full: 246 edge rows;
- partial: 905 edge rows;
- unknown: 0 edge rows.

## 4. Identity, aliases and artist type

- Node identity is `artist_id`/MBID, never display name.
- `credited_as` preserves the source spelling but never creates a node.
- Same-name aliases under one MBID collapse to one node.
- Different MBIDs with the same label remain separate and are reported as a quality limitation; E7 never merges by name.
- No `Artist.type = 'group'` filter exists. The UI label is “band/artist”.
- A self-produced band and its producer share one node with roles `band` and `producer`; self-produced album counts are disclosed separately and excluded from producer–band edges.

## 5. Metrics

| Family | Examples |
|---|---|
| Degree | Producer album degree, band/artist degree, weighted degree |
| Centrality | Normalized betweenness on the producer–band graph |
| Concentration | Top-k share, HHI, producers to 50% |
| Participation | Album count, band/artist count, self-produced album count |
| Communities | Louvain on the internal producer–producer projection, seed `42`, resolution `1.0` |
| Temporal | Active producers, albums, bands, producer–band edges, top-k share and HHI by decade |

Top-k (`k = 20` by default) is a report/API/UI selection. E7 persists the full graph; it never truncates graph rows for presentation.

## 6. Visual contract for E10

E7 persists the metadata; E10 owns the rendering.

| Element | Encoding |
|---|---|
| Individual producer | Circle, blue |
| Group/self-produced producer | Hexagon, orange |
| Unknown producer type | Circle, gray |
| Album | Square with continuous year color (Cividis/Viridis) |
| Band/artist | Rounded rectangle, neutral |
| Missing album year | Gray/hatched |
| `producer` edge | Solid |
| `co-producer` edge | Dashed |
| Album support | Edge width/opacity from `support_ratio` |
| Producer–band weight | Edge width from distinct album count |

The year scale runs from 1960 to 2026 with decade ticks. Color is never the only channel; tooltips, labels and the accessible table must expose the same values. Producer–Band opens as a top-k overview and expands a producer into an ego network; album and band nodes are never mixed in one canvas.

## 7. Persistence

Migration `0007` adds:

- `analysis_run`;
- `graph_node`;
- `graph_edge`;
- `node_metric`;
- `producer_metric`;
- `temporal_metric`;
- `community`;
- `community_membership`.

Every row references an `analysis_run`. Graph nodes are unique by run and canonical key; artists and albums may appear in both layers without duplication. Completed runs and report directories are immutable.

## 8. CLI and output

```bash
cd backend
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
  uv run python -m hmde.network run \
    --normalization-run 54d66992-643b-49ec-bac4-fe514ea39e94 \
    --quality-run 341824ea-5d6f-4279-bae0-f66a1e696e05 \
    --taxonomy ../data/taxonomy.json \
    --output ../data/network
```

Options: `--top-k`, `--decade`, `--subgenre` and repeatable `--band`. Exit codes are `0` completed, `2` completed with limitations and `1` fatal error.

Reports are written to `data/network/<analysis_version>/` as `report.json`, `report.md` and `manifest.json`. `data/network/` is ignored by Git.

The local expanded-corpus run produced:

- analysis version `net-a0b7c1f41ac5c92d`;
- producer–album: 968 nodes, 1,134 simple edges (1,151 role edges);
- producer–band: 398 nodes, 426 edges;
- 78 communities;
- 62 temporal metric rows;
- 58 approved quality exceptions, 24 unclassified albums and 3 possible duplicate-label cases.

The 147 albums without producer/co-producer credits are absent from the producer–album graph; 43 self-produced producers overlap with band nodes and are excluded from producer–band self-loops. These are documented coverage conditions, not negative evidence.

## 9. Limitations

- Missing credits are not evidence that a producer did not participate.
- Recording-level credits may cover only part of an album; use `support_ratio` and scope.
- The graph describes documented professional relationships, not musical affinity, influence or listener preference.
- Producer–band edges are derived from album credits, not a direct source relationship.
- Duplicate labels with different MBIDs remain a source/identity limitation.
- The corpus is 57 bands; results are not representative of all heavy metal.
- Full-corpus runs are local batch operations; CI uses fixtures.

## 10. Verification

Local checks on 2026-11-10:

- full backend suite: 286 tests passed;
- Ruff check and format: passed;
- migration `0007` upgrade/downgrade/upgrade: passed;
- OpenAPI drift: none;
- `docker compose config -q`: passed;
- full E7 run completed with limitations disclosed.

Remote GitHub Actions CI run [42738375416](https://github.com/cblancom/HMDE/actions/runs/42738375416) passed for commit `5001552`.
