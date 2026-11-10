# Read-only API v1 (E8)

- **Status:** Implemented locally; remote CI pending
- **Spec:** [SPEC-009](../../specs/009-read-api/spec.md)
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

## Pagination and filters

List endpoints use `limit` (default 20, max 200), `offset`, a resource-specific whitelist `sort` and `order`. Invalid values return `422`.

Retired bands are excluded from default lists/search and remain accessible by direct ID. Use `include_retired=true` for explicit inclusion.

## Local verification

- Backend suite: 313 tests passed.
- Ruff check/format: passed.
- OpenAPI drift check: passed.
- Frontend lint/typecheck/tests/build: passed.
- Full-corpus API smoke: 384 producers; graph response 5 nodes/4 edges in 25.8 ms.
- Remote CI: pending until commit/push.
