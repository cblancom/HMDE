# AGENTS.md

Operational instructions for working in this repository.

## 1. Project summary

Heavy Metal Data Explorer (HMDE) is a public, read-only application for exploring professional production relationships in heavy metal. The canonical E2 fixture dataset covers 42 bands and 1980–2000; the active E3 seed list is v0.3.0 with 509 bands across 1960–2026 and grows through versioned batches.

Stack:

- Backend: Python, FastAPI, Pydantic v2, synchronous SQLAlchemy 2.0, psycopg, Alembic.
- Database: PostgreSQL.
- Data and analysis: httpx, Pandas, NetworkX.
- Frontend: React, TypeScript, Vite, TanStack Query, React Router, custom CSS (Tailwind deferred), Cytoscape.js with cytoscape-d3-force, Plotly.
- Infrastructure: Docker Compose, uv, GitHub Actions.
- Tests: pytest, Vitest, React Testing Library, Playwright and axe (Chromium).

`constitution.md` contains stable principles. `docs/` contains reference material. `specs/` contains active SDD work. `spike/` contains disposable research code and is not production code.

## 2. Current state

- E0 is complete: vision, scope, roadmap, architecture, source evaluation, the MusicBrainz spike and the 42-band seed list are complete.
- `data/seed-list.json` is the active-version pointer to `data/seed-lists/v0.3.0.json` (509 active bands, 1960–2026). `data/seed-lists/v0.2.0.json` (57 bands) and `v0.1.0.json` (42 bands) are immutable archives. The v0.3.0 batches are `151/151/150`; the approved v0.2.0 batch remains `data/seed-lists/batches/v0.2.0-batch-01.json`.
- Backend, frontend, development Docker Compose and CI are implemented. The E1 and E2 remote CI runs passed.
- E1 is complete and SPEC-001 is validated.
- E2 is complete and SPEC-002 is validated; T-001–T-012 are complete.
- E3 is validated; SPEC-003 has T-001–T-012 complete and the remote CI run passed.
- ADR-0008 is accepted. SPEC-004 is validated: taxonomy v0.2.0, 42 + 15 active bands, 1960–2026, data-driven seed validation, expanded-decade reports and corpus metadata in E3 runs. The v0.2.0 dataset is `mb-20261107T194927Z-0d6cedd5c261` and cache-only replay is stable. Remote CI run 42411597186 passed.
- SPEC-005 is validated: canonical load from the v0.2 dataset, versioned taxonomy, hybrid album classification, band aggregates, review/quarantine issues and dataset membership. Local run `54d66992-643b-49ec-bac4-fe514ea39e94` processed 57 bands and 731 albums. Remote CI run 42535752532 passed.
- SPEC-006 is validated: persisted quality rules/runs/findings/exceptions/metrics, structural checks, coverage reports and the two-level CI/full-corpus model. Local quality run `341824ea-5d6f-4279-bae0-f66a1e696e05` has 58 findings covered by 58 approved exceptions and no unexcepted blocker. Remote CI run 42545153696 passed.
- SPEC-007 is validated: versioned EDA over the normalized corpus with distributions, coverage, producer concentration and descriptive co-credit frequencies. Local report `eda-1267fdcced62b7da` has 354 metric rows. Remote CI run 42548567359 passed.
- SPEC-008 is validated: producer–album evidence and derived producer–band/artist layers, persisted analysis runs/nodes/edges/metrics/communities, support-aware edges and versioned reports. Local run `net-a0b7c1f41ac5c92d` has 1,134 simple producer–album edges, 426 producer–band edges and 78 communities. Remote CI run 42738375416 passed. SPEC-009 is validated for E8; remote CI run 42741669410 passed. SPEC-010 is validated for E9; remote CI run 42747146170 passed. E10 was closed and validated on 2026-11-14. SPEC-011, SPEC-012 and SPEC-013 are validated from the recorded local automated, headless and build evidence; the owner accepted that evidence and remote CI was not run for the closure. `/graph` provides the global producer overview with 398 unique band-view nodes / 426 edges and 968 album-view nodes / 1,134 edges, shared band/album nodes, producer top-k/sort, filters, an isolated-producer toggle, overview physics, zoom-decluttered labels, server-generated bipartite and community layouts and a client-side d3-force/CoSE/fCoSE engine selector. The workspace adds a collapsible left index with 384 producer and 57 band rows, equal-height scrollable side panels, a dynamic `#bcd8c2`→`#123c38` year scale, node-type detail panels, a persisted 3rem navigation rail, a full-width shell and graph, collapsible Index/Details panels and `ResizeObserver` canvas resizing. The producer ego graph remains at `/producers/:id/graph` with a 500-node cap and static fallback. No API, schema or migration change was added by the E10 refinements. SPEC-014 is implemented locally and remote CI run 43895517746 passed on commit 4985ad8; documentation closure is pending. It adds a 26-test Playwright Chromium suite over deterministic E2E data, axe scans on nine routes, the `e2e` CI job, a reproducible performance probe, a security and dependency review and a 38-table backup/restore drill. No API, schema, migration or production dependency changed. The QA report is [docs/01-architecture/qa-report.md](docs/01-architecture/qa-report.md). One 968-node view-switch performance exception is documented; documentation closure and the required-check setting remain. SPEC-017 and SPEC-018 remain separate E10 follow-ups in review and are not part of E11.
- SPEC-016 is implemented locally for E13: a 510-band ceiling using all 453 candidates in `data/seed-lists/candidates/v0.3.0-pool.json`. T-002 verified 452 candidates and excluded Hellhammer (no studio album), giving a verified corpus of 509 bands; the three approved batches are 151/151/150. T-003 created `data/seed-lists/v0.3.0.json` (57 + 452 = 509) and moved `data/seed-list.json` to v0.3.0; the loader and version tests pass. T-004 made normalization accept seed-list 0.3.0, made `Q-MEM-001` use the active seed-list count and added `data/quality/rules-v0.2.0.json`. T-005 executed on 2026-11-19 with 509/509 bands and zero failures, but its initial datasets were not accepted: cache-only replay was non-deterministic and 7 multi-artist release groups produced duplicate entity MBIDs. T-005A completed the canonical dataset `mb-20261119T004940Z-9d5e75fdc1b9`: 509/509 bands, zero failures, no duplicate entity MBIDs, 7 reported `multi_artist_release_group` exclusions and the same dataset version/manifest in normal and cache-only runs. T-006 completed normalization run `ed8e7e12-c181-4041-ba39-42b2bf655453`: 509 active memberships, 4,826 classified albums, 3,926 accepted, 900 review, 0 quarantined, with tag map and overrides v0.3.0. T-007 completed quality run `288b11ac-9a90-4b4f-bf58-fdd50e1a51ad`: 0 blocking, 1,089 medium/advisory findings and 77 metrics; the v0.3.0 exception baseline is intentionally empty. T-008 completed EDA `eda-bd2ef42a54786c67` (927 metrics) and network `net-78a54051ff047f86` (4,217 producer–album edges, 1,700 producer–band edges, 325 communities); the comparison and legacy-row limitation are in `docs/03-data/analysis-v0.3.0.md`. T-009 kept the 1,000-node/2,000-edge cap with explicit truncation, passed 26 Playwright tests and nine axe scans, and documented one view-switch acknowledgement exception (p95 2,373 ms over 1 s; full settle 2,626 ms within 5 s). T-010 completed the local regression: 343 backend tests, 118 frontend tests, lint, typecheck, build and all E2E/axe checks passed. SPEC-016 is implemented locally; T-011 remote CI and validation remain pending explicit authorization. The database still serves the v0.2.0 dataset and E12 is paused.
- The current SDD index is [specs/README.md](specs/README.md).

## 3. Target structure

```text
/
├── AGENTS.md
├── README.md
├── constitution.md
├── specs/
│   ├── README.md
│   ├── _template/
│   │   ├── spec.md
│   │   ├── plan.md
│   │   └── tasks.md
│   └── NNN-feature-name/
│       ├── spec.md
│       ├── plan.md
│       └── tasks.md
├── docs/
│   ├── README.md
│   ├── 00-vision/
│   ├── 01-architecture/
│   │   └── adr/
│   └── 03-data/
├── backend/
├── frontend/
├── infra/              Dockerfiles and container assets
├── compose.yaml         Development services
├── spike/
└── data/
```

Do not create empty directories or extra layers without a need.

## 4. Canonical commands

These commands are verified against the repository. `cp .env.example .env` is required for commands that use `--env-file`.

### Backend

```bash
cd backend
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run --env-file ../.env pytest
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde uv run alembic history
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde uv run alembic heads
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde uv run alembic upgrade head
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde uv run alembic downgrade base
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
  uv run python -m hmde.seed.loader --fixtures ../data/fixtures/e2
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
  uv run python -m hmde.openapi --output ../openapi.json
MUSICBRAINZ_USER_AGENT="HMDE/0.1 (contact)" \
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
  uv run python -m hmde.etl.musicbrainz ingest \
    --seed-list ../data/seed-list.json \
    --raw-root ../data/raw/musicbrainz \
    --output ../data/ingestions/musicbrainz

# Reuse cached raw responses without network access.
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
  uv run python -m hmde.etl.musicbrainz ingest \
    --seed-list ../data/seed-list.json \
    --raw-root ../data/raw/musicbrainz \
    --output ../data/ingestions/musicbrainz --cache-only

# Normalize the active E3 dataset into canonical entities and classifications.
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
  uv run python -m hmde.normalization run \
    --dataset ../data/ingestions/musicbrainz/mb-20261119T004940Z-9d5e75fdc1b9 \
    --taxonomy ../data/taxonomy.json \
    --tag-map ../data/classifications/tag-map-v0.3.0.json \
    --overrides ../data/classifications/manual-overrides-v0.3.0.json \
    --seed-list ../data/seed-list.json \
    --output ../data/normalization

# Run the batch quality gate over the normalized corpus.
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
  uv run python -m hmde.quality run \
    --normalization-run ed8e7e12-c181-4041-ba39-42b2bf655453 \
    --rules ../data/quality/rules-v0.2.0.json \
    --exceptions ../data/quality/exceptions-v0.3.0.json \
    --output ../data/quality --strict

# Run E6 exploratory analysis.
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
  uv run python -m hmde.analytics run \
    --normalization-run ed8e7e12-c181-4041-ba39-42b2bf655453 \
    --quality-run 288b11ac-9a90-4b4f-bf58-fdd50e1a51ad \
    --taxonomy ../data/taxonomy.json \
    --metric-catalogue ../data/metrics/catalogue-v0.1.0.json \
    --output ../data/analysis

# Run E7 producer network analysis.
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
  uv run python -m hmde.network run \
    --normalization-run ed8e7e12-c181-4041-ba39-42b2bf655453 \
    --quality-run 288b11ac-9a90-4b4f-bf58-fdd50e1a51ad \
    --taxonomy ../data/taxonomy.json \
    --output ../data/network
```

Unit tests run without PostgreSQL; integration tests require `TEST_DATABASE_URL` and the `hmde_test` database.

### Frontend

```bash
cd frontend
npm ci
npm run dev
npm run lint
npm run typecheck
npm run test
npm run build
npm run generate:api
npm run test:e2e
npm run test:perf
```

`npm run test:e2e` requires a migrated and seeded `hmde_e2e` database; Playwright starts the API on 8011 and Vite on 5183. `npm run test:perf` requires the local v0.2.0 stack and `HMDE_ANALYSIS_RUN`.

### Docker Compose

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
docker compose logs -f
docker compose exec db createdb -U hmde hmde_test
docker compose exec api uv run alembic upgrade head
docker compose exec api uv run alembic current
docker compose exec api uv run alembic downgrade base
docker compose exec api uv run alembic upgrade head
docker compose exec api uv run python -m hmde.seed.loader --fixtures /data/fixtures/e2
docker compose --profile ingest run --rm ingest
docker compose down
```

`docker compose down -v` deletes the PostgreSQL volume and requires explicit authorization.

### API endpoints and routes

API:

- `GET /health`
- `GET /api/v1/bands` with `q`, `subgenre`, `limit`, `offset`
- `GET /api/v1/bands/{band_id}`
- `GET /api/v1/bands/{band_id}/graph`
- `GET /api/v1/graph/producers` with `view`, `producer_limit`, `producer_sort`, `order`, `decade`, `subgenre`, `include_isolated`, `include_evidence`, `layout`, `max_nodes`, `max_edges`

Web:

- `/` redirects to `/bands`
- `/bands` list/search/filter
- `/bands/:bandId` detail, credits and producer graph
- `/albums` and `/albums/:albumId`
- `/producers` and `/producers/:producerId`
- `/producers/:producerId/graph`
- `/graph`
- `/search`

### Host ports

- Web: `5173`
- API: `8001`
- PostgreSQL: `5434`

After E1, this section must contain the exact commands for:

- Backend sync, format, lint and tests.
- Frontend install, dev, lint, typecheck, tests and build.
- Database migrations.
- Docker Compose development and production.
- Smoke tests when a smoke script exists.

Do not assume a command works because it is listed in a document. Verify it against the repository.

## 5. SDD workflow

For each feature:

1. Read `constitution.md`, this file and the relevant spec.
2. Review `spec.md` and resolve ambiguities before planning.
3. Create `plan.md` only when the spec has no blocking questions.
4. Create `tasks.md` with small tasks, dependencies and verifiable outcomes.
5. Obtain approval for spec, plan and tasks.
6. Implement one task or a small related group.
7. Run the applicable tests and verifications.
8. Review the diff before continuing.
9. Record validation evidence in `tasks.md` and update the spec result.
10. Update `specs/README.md` and the current state in this file.

Each spec lives in `specs/NNN-feature-name/`.

## 6. Spec lifecycle

Allowed statuses:

- `Draft`
- `In clarification`
- `Spec approved`
- `Plan/tasks in review`
- `Approved`
- `In implementation`
- `Implemented`
- `Validated`
- `Superseded`

`Spec approved` and `Plan/tasks in review` do not authorize implementation. Only `Approved` does. `Implemented` means code is complete. `Validated` means acceptance criteria have evidence. Do not use them interchangeably.

Specs may be revised while in draft, clarification or approval. After validation, a behavior change requires a new spec or an explicit versioned revision with a changelog.

## 7. Conventions

- All project content is in English: documentation, code, identifiers, API descriptions, UI copy and commit messages.
- Conversation with the project owner may be in Spanish.
- Dates use ISO 8601.
- Requirements use `FR-NNN`, non-functional requirements `NFR-NNN`, business rules `BR-NNN` and acceptance criteria `AC-NNN`.
- Use relative links.
- One source of truth per concern.
- Detailed code style and testing rules live in `docs/01-architecture/conventions.md`.
- Do not add comments unless they explain non-obvious context.

## 8. Boundaries

### Always

- Run the applicable tests and quality checks before closing a task.
- Update documentation in the same change.
- Preserve data provenance and source limits.
- Record architectural decisions in an ADR.
- Keep `tasks.md` and `specs/README.md` current.

### Ask first

- Change the database schema.
- Add a dependency.
- Change CI configuration.
- Change the API contract in a backwards-incompatible way.
- Expand dataset or source scope.
- Introduce a new architectural pattern or service.
- Run destructive migrations or delete data.

### Never

- Commit secrets, tokens or credentials.
- Scrape sources whose terms do not allow it.
- Merge identities automatically without deterministic evidence.
- Delete conflicting data, audit records or failing tests.
- Present missing data as negative evidence.
- Commit, push, deploy or perform destructive operations without an explicit request and a security confirmation.

## 9. Definition of Done

A task is done when:

- Its acceptance criteria and related requirements are met.
- The applicable tests and checks were executed and passed.
- The migration applies from an empty database and can be rolled back, if applicable.
- OpenAPI and TypeScript types are regenerated, if applicable.
- Documentation is updated.
- The diff contains no secrets, unrelated changes or unnecessary complexity.
- `tasks.md` reflects the real state and includes evidence.

## 10. Definition of Ready

A task is ready when:

- The spec is approved and has no blocking questions.
- The plan is approved.
- The task has clear acceptance criteria and verification.
- Dependencies are resolved or explicitly blocked.
- The affected files and contracts are identified.
