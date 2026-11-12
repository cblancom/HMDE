# Read-only API v1 (E8)

- **Status:** Validated for E8; the additive producer overview endpoint is implemented locally for E10 (SPEC-011) with remote CI pending
- **Specs:** [SPEC-009](../../specs/009-read-api/spec.md), [SPEC-011](../../specs/011-graph-visualization/spec.md), [SPEC-013](../../specs/013-graph-layout-modes/spec.md)
- **Base path:** `/api/v1`

## Entity endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | API/database health |
| GET | `/api/v1/bands` | Band list/search with taxonomy, year, decade and retired filters |
| GET | `/api/v1/bands/{band_id}` | Band detail with albums and credits |
| GET | `/api/v1/bands/{band_id}/graph` | E2-compatible one-hop band–producer graph |
| GET | `/api/v1/artists/{artist_id}` | Canonical artist detail |
| GET | `/api/v1/albums` | Album list/search/filter |
| GET | `/api/v1/albums/{album_id}` | Album detail with support-aware credits |
| GET | `/api/v1/credits` | Credit list filtered by album, band, artist, role or scope |
| GET | `/api/v1/search?q=` | Bounded grouped search across bands, albums and producers |
| GET | `/api/v1/taxonomy` | Versioned taxonomy hierarchy |

## Producer and analytics endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/producers` | Producer ranking by albums, bands, betweenness or name |
| GET | `/api/v1/producers/{producer_id}` | Producer metrics, community and top albums/bands |
| GET | `/api/v1/producers/{producer_id}/graph` | Bounded `albums` or `bands` producer graph |
| GET | `/api/v1/graph/producers` | Global producer overview over the E7 graph layers |
| GET | `/api/v1/analysis-runs` | E7 run history |
| GET | `/api/v1/analysis-runs/{run_id}` | E7 run detail |
| GET | `/api/v1/analytics/summary` | Graph/support/concentration summary |
| GET | `/api/v1/analytics/decades` | Temporal metrics by decade |
| GET | `/api/v1/communities` | Community list |
| GET | `/api/v1/communities/{key}` | Community detail and producer members |

## Analysis-run selection

Producer, graph and analytics endpoints use the latest `completed` or `completed_with_limitations` E7 run by default. Pass `analysis_run=<uuid>` to select a specific run. Entity endpoints do not require an E7 run.

If no completed run exists, analytics/graph/producer endpoints return `503`. A requested missing run returns `404`; a non-terminal run returns `409`.

## Graph responses

`GET /api/v1/producers/{producer_id}/graph?view=albums|bands`

- `view=albums`: producer and album nodes only.
- `view=bands`: producer and band/artist nodes only.
- No mixed album/band canvas and no album–album projection.
- `limit`: max 100; `depth`: max 2; `max_nodes`: 500; `max_edges`: 2000.
- `include_evidence=true` adds bounded album evidence.
- Responses include `meta.analysis_run_id`, versions, limits and `truncated`.

## Global producer overview

`GET /api/v1/graph/producers?view=albums|bands`

- `view`: `bands` default; `albums` alternative.
- `producer_limit`: `0` (all) default; positive values select the top-k after sorting.
- `producer_sort`: `album_count`, `band_count`, `betweenness` or `name`; `order`: `asc` or `desc`.
- `decade` and `subgenre` select producers through album credits; the albums view also restricts album targets.
- `include_isolated`: `true` default; `false` omits producer rows with no outgoing producer–band edges.
- `include_evidence`: bounded edge evidence, mainly for band-view role mixes.
- `layout`: optional `bipartite` or `community`; absent means client-side Force.
- `max_nodes`: 1,000; `max_edges`: 2,000.
- `analysis_run`: optional E7 run selection.

The response reuses `ProducerGraphNode` and `ProducerGraphEdge` and adds overview meta with `scope=overview`, `matched_producers`, `selected_producers`, `include_isolated`, `truncated` and the limits. Producer nodes include `album_count`, `band_count`, `betweenness` and `community_key`.

When `layout=bipartite|community` is requested, the response also includes:

```json
"layout": {
  "algorithm": "bipartite",
  "nodes": [{ "id": "entity-uuid", "x": 0.0, "y": 0.0 }]
}
```

- `bipartite` uses NetworkX `bipartite_layout` with producers left and bands/albums right.
- `community` reuses the persisted E7 Louvain communities and cluster positions.
- Coordinates are optional and additive; omitted `layout` keeps the current response shape for Force.
- Layout errors return the graph without coordinates rather than failing the request.

Shared semantics:

- a band or album node appears once and connects to every credited producer;
- album role rows are deduplicated to one edge per producer–album pair (`role` is the single role or `mixed`);
- no producer–producer edges are synthesized.

Current v0.2 corpus:

- bands view: 398 unique nodes / 426 edges (341 producer sources + 57 bands; 384 producer entities because 43 bands also carry the producer role);
- albums view: 968 nodes / 1,134 simple edges (1,151 role rows);
- the API can omit isolated producer rows with `include_isolated=false`; client-side hiding in the albums view also removes their producer nodes and orphaned albums, leaving 893 nodes / 951 edges.

## Pagination and filters

List endpoints use `limit` (default 20, max 200), `offset`, a resource-specific whitelist `sort` and `order`. Invalid values return `422`.

Retired bands are excluded from default lists/search and remain accessible by direct ID. Use `include_retired=true` for explicit inclusion.

## Local verification

- Backend suite: 225 unit tests passed with 107 integration tests skipped; 332 full-suite tests passed with `TEST_DATABASE_URL`.
- Ruff check/format: passed.
- OpenAPI generation includes `/api/v1/graph/producers`, the overview schemas and the optional layout block; generated TypeScript types compile.
- Frontend lint, typecheck, 98 tests and production build: passed.
- Full-corpus overview smoke: 398 nodes / 426 edges in `bands` and 968 nodes / 1,134 edges in `albums`; no truncation at the 1,000-node cap. Layout requests took ~0.16 s (Bipartite) and ~0.25 s (Community) for the 968-node album view.
- E10 remote CI: pending. The last passed E8 run is [42741669410](https://github.com/cblancom/HMDE/actions/runs/42741669410) for commit `bb4ca1a`.
