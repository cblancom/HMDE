# Heavy Metal Data Explorer (HMDE)

HMDE is a public, read-only application for exploring professional production relationships in heavy metal: who produced, recorded, mixed or mastered an album, and how those people, bands, albums and studios connect.

The MVP focuses on 42 bands with studio albums released between 1980 and 2000. The architecture supports growth to 200–500 bands without redesign.

## Status

- **E0:** complete. Documents, MusicBrainz feasibility spike and the 42-band seed list are ready.
- **Application code:** E1 and E2 validated. E3 implemented and locally validated (T-001–T-012).
- **Next work:** confirm E3 in remote CI; no next spec has been started.
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

### Frontend routes

| Route | Purpose |
|---|---|
| `/` | Redirects to `/bands` |
| `/bands` | Band search, subgenre filter and list |
| `/bands/:bandId` | Band detail, credits and producer graph |

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

E2 uses the versioned fixture set `e2-v0.1.0`: 14 bands, 41 albums, 247 recordings and 859 credits. It is loaded explicitly; it is not part of the migrations.

```bash
cd backend
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
  uv run python -m hmde.seed.loader --fixtures ../data/fixtures/e2
```

The loader is idempotent and makes no network calls. Re-running it updates the same deterministic records and adds a new `fixture_load` audit row without duplicating entities.

## E3 MusicBrainz ingestion

E3 ingests the 42-band seed list directly from MusicBrainz. Set a meaningful User-Agent with contact details before a live run:

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

It records every execution in `ingest_run`, respects the one-request-per-second limit and does not modify the canonical E2 tables or the API contract.

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

`0001_baseline` is an empty reversible baseline. `0002_catalog_v0` adds the E2 catalog tables and `0003_credit_target_restrict` tightens credit target delete rules.

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
| [`docs/03-data/seed-list.md`](docs/03-data/seed-list.md) | Final 42-band MVP seed list |
| [`data/seed-list.json`](data/seed-list.json) | Machine-readable seed list |

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
