# Heavy Metal Data Explorer (HMDE)

HMDE is a public, read-only application for exploring professional production relationships in heavy metal: who produced, recorded, mixed or mastered an album, and how those people, bands, albums and studios connect.

The canonical E2 fixture dataset covers 42 bands and 1980–2000. The active E3 seed list now contains 57 bands across 1960–2026 and grows through versioned batches toward 200–500 bands without redesign.

## Status

- **E0:** complete. Documents, MusicBrainz feasibility spike and the 42-band seed list are ready.
- **Application code:** E1, E2 and E3 validated. SPEC-003 and T-001–T-012 complete; remote CI run 42396996612 passed.
- **Corpus v0.2:** SPEC-004 validated. The active seed list is v0.2.0 (57 bands, 1960–2026), the approved batch adds 15 bands, and dataset `mb-20261107T194927Z-0d6cedd5c261` was reproduced cache-only. Remote CI run 42411597186 passed.
- **Normalization v0.2:** SPEC-005 validated. The normalized corpus has 57 bands, 731 albums, 32,665 credit contexts and 57 band aggregates. The review queue contains 24 explicitly quarantined bootleg/live/demo albums and 34 medium-review classifications/aggregates. Remote CI run 42535752532 passed.
- **Data quality v0.1:** SPEC-006 validated. Structural checks found no unexcepted blocker: 58 findings (24 album quarantine, 17 album review, 17 aggregate review) are covered by 58 approved exceptions; 51 completeness/coverage metrics were persisted. Remote CI run 42545153696 passed.
- **EDA v0.1:** SPEC-007 validated. The report `eda-1267fdcced62b7da` analyzes 57 bands, 731 albums, 32,665 credit contexts, taxonomy distributions, producer concentration and descriptive co-credit frequencies. Remote CI run 42548567359 passed.
- **Network v0.1:** SPEC-008 validated. The full run `net-a0b7c1f41ac5c92d` persists producer–album and producer–band layers: 1,134 simple producer–album edges, 1,151 role records, 426 producer–band edges and 78 communities. Remote CI run 42738375416 passed.
- **API v1:** SPEC-009 validated. Entity, producer, analytics, taxonomy, search and bounded graph endpoints are available under `/api/v1`. Remote CI run 42741669410 passed.
- **Explorer v0.1:** SPEC-010 implemented locally. Band, album, producer and search views use the E8 API and existing CSS; Tailwind is deferred. Remote CI is pending.
- **Current SDD index:** [`specs/README.md`](specs/README.md).

## What the MVP will provide

- Exploration of bands, albums, producers, engineers and studios.
- Navigation through production credits and shared collaborators.
- Filters by period, subgenre and role.
- Interactive collaboration graphs.
- Precomputed metrics and community analysis.
- Provenance and confidence for every credit.

Out of scope for the MVP: audio analysis, listener preferences, user accounts, complete metal encyclopedia coverage, Discogs, Encyclopaedia Metallum and distributed infrastructure.

## Requirements

For the main flow:

- Docker and Docker Compose.
- A local checkout of this repository.

For running backend or frontend outside containers:

- Python 3.13 and uv.
- Node.js 20 and npm.
- PostgreSQL 16, or the `db` service from Docker Compose.

## Quick start with Docker

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec api uv run alembic upgrade head
docker compose exec api uv run python -m hmde.seed.loader --fixtures /data/fixtures/e2
docker compose ps
```

The first startup applies the schema and loads the versioned E2 fixtures. All three services should become healthy.

| Service | URL |
|---|---|
| Web shell | http://127.0.0.1:5173 |
| API | http://127.0.0.1:8001 |
| API health | http://127.0.0.1:8001/health |
| OpenAPI | http://127.0.0.1:8001/docs |
| PostgreSQL | `127.0.0.1:5434` |

The API container listens on port `8000` internally and PostgreSQL on `5432`; only the host ports above are published. All published ports bind to `127.0.0.1`.

### API endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | API and database health |
| `GET` | `/api/v1/bands` | List/search bands with `q`, `subgenre`, `limit` and `offset` |
| `GET` | `/api/v1/bands/{band_id}` | Band metadata, albums and aggregated credits |
| `GET` | `/api/v1/bands/{band_id}/graph` | One-hop band–producer graph |
| `GET` | `/api/v1/producers` | Producer rankings and filters |
| `GET` | `/api/v1/producers/{producer_id}/graph` | Bounded producer–album or producer–band graph |
| `GET` | `/api/v1/albums` | Album list/search |
| `GET` | `/api/v1/analytics/summary` | E7 graph/support summary |

See [API v1](docs/03-data/api-v1.md) for the full resource list.

### Frontend routes

| Route | Purpose |
|---|---|
| `/` | Redirects to `/bands` |
| `/bands` | Band search, subgenre filter and list |
| `/bands/:bandId` | Band detail, credits and producer graph |
| `/albums` | Album list/search |
| `/albums/:albumId` | Album detail and credits |
| `/producers` | Producer rankings |
| `/producers/:producerId` | Producer detail and metrics |
| `/search` | Grouped search |

See [Frontend explorer](docs/01-architecture/frontend.md) for routes and design notes.

Stop the environment without deleting data:

```bash
docker compose down
```

`docker compose down -v` deletes the PostgreSQL volume and is not part of the normal flow.

## Local development

Start PostgreSQL first:

```bash
docker compose up -d db
```

### Backend

```bash
cd backend
uv sync
uv run --env-file ../.env uvicorn hmde.main:app --reload --port 8001
```

If you do not want to use `--env-file`, pass `DATABASE_URL` explicitly:

```bash
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
  uv run uvicorn hmde.main:app --reload --port 8001
```

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

Vite runs on `http://127.0.0.1:5173` and proxies `/health` and `/api` to `http://localhost:8001` by default. Inside Compose it targets `http://api:8000`.

### OpenAPI types

The committed `openapi.json` is the API contract snapshot. Regenerate it from the backend, then generate the ignored frontend types:

```bash
cd backend
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
  uv run python -m hmde.openapi --output ../openapi.json

cd ../frontend
npm run generate:api
```

`npm run dev`, `npm run typecheck` and `npm run build` regenerate `src/api/schema.d.ts` automatically. Do not edit that file by hand.

## E2 seed data

E2 uses the historical versioned fixture set `e2-v0.1.0`: 14 bands, 41 albums, 247 recordings and 859 credits, all from 1980–2000. It is loaded explicitly; it is not part of the migrations and will not be rewritten by corpus v0.2.

```bash
cd backend
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
  uv run python -m hmde.seed.loader --fixtures ../data/fixtures/e2
```

The loader is idempotent and makes no network calls. Re-running it updates the same deterministic records and adds a new `fixture_load` audit row without duplicating entities.

## E3 MusicBrainz ingestion

E3 ingests the active seed list directly from MusicBrainz. `data/seed-list.json` is an active-version pointer to the 57-band v0.2.0 corpus (1960–2026); `data/seed-lists/v0.1.0.json` remains the immutable 42-band historical archive. Set a meaningful User-Agent with contact details before a live run:

```bash
cd backend
MUSICBRAINZ_USER_AGENT="HMDE/0.1 (you@example.com)" \
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
  uv run python -m hmde.etl.musicbrainz ingest \
    --seed-list ../data/seed-list.json \
    --raw-root ../data/raw/musicbrainz \
    --output ../data/ingestions/musicbrainz
```

The command writes:

- immutable raw responses under `data/raw/musicbrainz/`;
- a versioned NDJSON dataset under `data/ingestions/musicbrainz/<dataset_version>/`;
- `coverage.json` and `report.md` inside that dataset directory.

It records every execution in `ingest_run`, respects the one-request-per-second limit and does not modify the canonical E2 tables or the API contract. The validated v0.2.0 run processed 57 bands with 0 failures: 731 release groups, 9,236 releases, 16,683 recordings, 32,326 credits and 3,991 exclusions. Dataset `mb-20261107T194927Z-0d6cedd5c261` was reproduced with `--cache-only` without changing its version.

Reuse cached responses without network access:

```bash
MUSICBRAINZ_USER_AGENT="HMDE/0.1 (you@example.com)" \
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
  uv run python -m hmde.etl.musicbrainz ingest \
    --seed-list ../data/seed-list.json \
    --cache-only
```

Force fresh requests and a new dataset version when source data changes:

```bash
MUSICBRAINZ_USER_AGENT="HMDE/0.1 (you@example.com)" \
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
  uv run python -m hmde.etl.musicbrainz ingest \
    --seed-list ../data/seed-list.json \
    --refresh
```

With Docker Compose, set `MUSICBRAINZ_USER_AGENT` in `.env` and use the `ingest` profile:

```bash
docker compose --profile ingest run --rm ingest
```

For cache-only inside Compose, override the service command:

```bash
docker compose --profile ingest run --rm ingest \
  uv run --frozen python -m hmde.etl.musicbrainz ingest \
  --seed-list /data/seed-list.json --raw-root /data/raw/musicbrainz \
  --output /data/ingestions/musicbrainz --cache-only
```

Exit codes: `0` completed, `2` completed with band failures, `1` fatal configuration or execution error.

## E4 normalization

E4 normalizes the active E3 dataset into canonical PostgreSQL entities, album-level taxonomy classifications, band aggregates and dataset membership. It does not call MusicBrainz, change the API contract or modify the frontend.

```bash
cd backend
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
  uv run python -m hmde.normalization run \
    --dataset ../data/ingestions/musicbrainz/mb-20261107T194927Z-0d6cedd5c261 \
    --taxonomy ../data/taxonomy.json \
    --tag-map ../data/classifications/tag-map-v0.1.0.json \
    --overrides ../data/classifications/manual-overrides-v0.1.0.json \
    --seed-list ../data/seed-list.json \
    --output ../data/normalization
```

The command writes versioned JSON/Markdown reports under `data/normalization/<run_id>/`, records a `normalization_run`, and exits with `0` completed, `2` completed with review, or `1` fatal error. `--dry-run` validates inputs without writing canonical rows. The validated local run `54d66992-643b-49ec-bac4-fe514ea39e94` processed 57 bands and 731 albums; 690 albums were accepted, 17 are in review and 24 bootleg/live/demo release groups were explicitly quarantined.

## E5 data quality

E5 measures the normalized corpus without changing it. It checks structural invariants, completeness and coverage, persists findings/exceptions/metrics, and writes JSON/Markdown reports.

```bash
cd backend
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
  uv run python -m hmde.quality run \
    --normalization-run 54d66992-643b-49ec-bac4-fe514ea39e94 \
    --rules ../data/quality/rules-v0.1.0.json \
    --exceptions ../data/quality/exceptions-v0.1.0.json \
    --output ../data/quality --strict
```

The full-corpus run is a batch operation because the E3 dataset and raw cache are not in Git. CI runs structural checks against fixtures. Exit codes are `0` pass, `2` advisory findings, `3` blocked by an unexcepted blocking finding, and `1` fatal error. The initial quality run `341824ea-5d6f-4279-bae0-f66a1e696e05` persisted 58 findings, 58 approved exceptions and 51 metrics; no blocking finding was left unexcepted.

## E6 exploratory analysis

E6 produces a report-only EDA over explicit normalized and quality runs. It writes versioned JSON/Markdown reports under `data/analysis/<analysis_version>/` without modifying the database.

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

The local report `eda-1267fdcced62b7da` contains 354 metric rows, including decade/taxonomy distributions, producer participation/concentration and descriptive co-credit pairs. Exit code `2` indicates completed with disclosed limitations. New corpus versions create new analysis directories; old reports are never overwritten.

## E7 producer network analysis

E7 builds persisted, producer-centric graph layers over explicit normalized and quality runs. It writes `analysis_run`, node/edge/metric/community rows and versioned reports under `data/network/<analysis_version>/`.

```bash
cd backend
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
  uv run python -m hmde.network run \
    --normalization-run 54d66992-643b-49ec-bac4-fe514ea39e94 \
    --quality-run 341824ea-5d6f-4279-bae0-f66a1e696e05 \
    --taxonomy ../data/taxonomy.json \
    --output ../data/network
```

The local run `net-a0b7c1f41ac5c92d` produced 968 producer–album nodes, 1,134 simple edges (1,151 role edges), 398 producer–band nodes and 426 band edges. It found 78 communities and 62 temporal metric rows. Exit code `2` indicates completed with disclosed limitations. See [producer network analysis](docs/03-data/network-analysis.md).

## Test database

Integration tests require an isolated `hmde_test` database. Create it once with the Compose database running:

```bash
docker compose exec db createdb -U hmde hmde_test
```

If it already exists, `createdb` reports that and the database can be reused.

## Tests and quality

### Backend

Unit tests run without PostgreSQL; integration tests are skipped when `TEST_DATABASE_URL` is absent.

```bash
cd backend
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Full suite with the test database:

```bash
cd backend
uv run --env-file ../.env pytest
```

Or with explicit variables:

```bash
cd backend
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
TEST_DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde_test \
  uv run pytest
```

### Frontend

```bash
cd frontend
npm ci
npm run lint
npm run typecheck
npm run test
npm run build
```

### Continuous integration

`.github/workflows/ci.yml` runs migration checks, OpenAPI drift detection, backend tests with a PostgreSQL service and the full frontend checks on push and pull request. The E2 run passed in GitHub Actions.

## Migrations

With Docker Compose:

```bash
docker compose exec api uv run alembic upgrade head
docker compose exec api uv run alembic current
docker compose exec api uv run alembic downgrade base
docker compose exec api uv run alembic upgrade head
```

From the host:

```bash
cd backend
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
  uv run alembic upgrade head
```

`0001_baseline` is an empty reversible baseline. `0002_catalog_v0` adds the E2 catalog tables and `0003_credit_target_restrict` tightens credit target delete rules. `0004`–`0007` add ingestion, normalization, quality and analytical graph tables.

## Troubleshooting

### A port is already in use

Change `API_PORT`, `WEB_PORT` or `DB_PORT` in `.env` and restart:

```bash
docker compose up -d
```

The default host ports are `8001`, `5173` and `5434` to avoid collisions with other local projects.

### The API reports that `DATABASE_URL` is missing

Copy `.env.example` to `.env` and run the backend from `backend/` with `--env-file ../.env`, or pass `DATABASE_URL` explicitly.

### `/health` returns 503

PostgreSQL is unavailable. Check the database service:

```bash
docker compose ps
docker compose logs db
docker compose start db
```

### Integration tests are skipped

Create `hmde_test` and set `TEST_DATABASE_URL`:

```bash
docker compose exec db createdb -U hmde hmde_test
cd backend
uv run --env-file ../.env pytest
```

### The frontend cannot reach the API

Check that the API is healthy and that the proxy target is correct:

```bash
curl http://127.0.0.1:8001/health
```

Inside Compose, `VITE_API_PROXY_TARGET` must be `http://api:8000`. Outside Compose, the default is `http://localhost:8001`.

### A container is unhealthy

```bash
docker compose ps
docker compose logs api
docker compose logs web
docker compose logs db
```

### `npm ci` fails

Use Node.js 20 and ensure `frontend/package-lock.json` exists. Do not edit the lockfile manually.

## Documentation

| Document | Purpose |
|---|---|
| [`constitution.md`](constitution.md) | Stable principles and governance |
| [`AGENTS.md`](AGENTS.md) | Operational instructions, current state and boundaries |
| [`specs/README.md`](specs/README.md) | Capability map and spec index |
| [`docs/00-vision/vision.md`](docs/00-vision/vision.md) | Problem, users and research questions |
| [`docs/00-vision/scope.md`](docs/00-vision/scope.md) | MVP boundaries and dataset |
| [`docs/00-vision/roadmap.md`](docs/00-vision/roadmap.md) | Long-term stage plan |
| [`docs/01-architecture/overview.md`](docs/01-architecture/overview.md) | Architecture and stack |
| [`docs/01-architecture/data-model.md`](docs/01-architecture/data-model.md) | Conceptual data model v0 |
| [`docs/01-architecture/adr/README.md`](docs/01-architecture/adr/README.md) | Architecture decisions |
| [`docs/03-data/sources.md`](docs/03-data/sources.md) | Source evaluation |
| [`docs/03-data/spike-report.md`](docs/03-data/spike-report.md) | MusicBrainz feasibility results |
| [`docs/03-data/seed-list.md`](docs/03-data/seed-list.md) | Historical 42-band seed list and active 57-band v0.2.0 corpus |
| [`docs/03-data/normalization-rules.md`](docs/03-data/normalization-rules.md) | E4 identity, provenance, credit, taxonomy and classification rules |
| [`docs/03-data/data-quality.md`](docs/03-data/data-quality.md) | E5 quality dimensions, gates and exception baseline |
| [`docs/03-data/eda-metrics.md`](docs/03-data/eda-metrics.md) | E6 exploratory metric catalogue and analysis rules |
| [`data/seed-list.json`](data/seed-list.json) | Active-version pointer; versioned files live in `data/seed-lists/` |

## Repository layout

```text
constitution.md     Stable project principles
AGENTS.md           Operational instructions for agents
specs/              Active SDD specs, templates and index
docs/               Reference documentation
backend/            Backend application
frontend/           React application
compose.yaml        Development services
infra/              Dockerfiles and container assets
data/               Seed list and local raw data
spike/              Disposable MusicBrainz research
```

## MusicBrainz spike

The disposable feasibility spike can be run with:

```bash
python3 spike/spike_musicbrainz.py
```

It requires network access and respects MusicBrainz's one-request-per-second limit. See [`spike/README.md`](spike/README.md).

## SDD workflow

1. Specify the capability in `spec.md`.
2. Clarify open questions.
3. Design the solution in `plan.md`.
4. Break it down in `tasks.md`.
5. Implement incrementally.
6. Validate with evidence.
7. Update the spec index and operational state.

A feature is not implemented before its spec, plan and tasks are approved. See [`AGENTS.md`](AGENTS.md) for the operational workflow.

## Language

All project content is written in English. Conversation with the project owner may be in Spanish.
