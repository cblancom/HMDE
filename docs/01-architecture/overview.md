# Architecture overview

- **Status:** Approved in essence; details pending E2
- **Version:** 0.1
- **Date:** 2026-11-04
- **Stage:** E0

## 1. Goals and constraints

The architecture must allow the system to:

- Ingest data from external sources with traceability and respect for their limits.
- Normalize and validate entities and relationships.
- Run expensive graph analyses outside the HTTP request cycle.
- Serve a fast read API and an interactive frontend.
- Grow from dozens to hundreds of bands without redesign.
- Remain understandable for a small team.

Constraints:

- One primary developer, supported by agents.
- Python for backend, data and analysis.
- PostgreSQL as persistent storage.
- No distributed infrastructure in the MVP.
- Documentation and code in the same repository.

## 2. Architectural style

A **modular monolith** with two entry points is adopted:

1. **HTTP API** (FastAPI), read-only, serving the frontend.
2. **Data and analysis CLI**, running ingestion, normalization, validation and batch computations.

Both share the same Python package and database schema, but they do not share processes or request cycles. PostgreSQL is the integration contract between the batch world and the API.

No microservices are used. Logical separation is achieved through modules and dependency rules, not independent deployments. The decision is recorded in [ADR-0001](adr/ADR-0001-modular-monolith.md).

## 3. Context and components

```
External sources
  MusicBrainz · Wikidata · (Wikipedia)
        │
        ▼
  Ingestion CLI ──► raw data + origin metadata
        │
        ▼
  Normalization and identity
        │
        ▼
  PostgreSQL
    ├── normalized layer
    └── analytical layer
        │
        ├──► FastAPI API ──► React frontend
        │
        └──► Batch analysis (NetworkX) ──► persisted results
```

| Component | Responsibility | Must not do |
|---|---|---|
| Ingestion | Consume sources, respect limits, store raw data and metadata | Normalize complex business rules |
| Normalization | Map to canonical entities, resolve identity, record provenance | Call the API or frontend |
| Quality | Measure coverage, validity and consistency; produce reports | Correct data without a trace |
| Analysis | Build graphs and compute metrics; persist results | Run inside an HTTP request |
| API | Serve entities, relationships, search and subgraphs | Ingest, normalize or compute expensive metrics |
| Frontend | Present data and enable exploration; manage UI state | Duplicate backend business rules |
| PostgreSQL | Persistence, referential integrity, queries and search | Be a schemaless JSON store |

## 4. Data flow

1. **Raw:** the source response is stored with URL, date, hash and status.
2. **Normalized:** canonical entities, credits, roles and external identifiers are created or updated.
3. **Analytical:** graph snapshots are built and metrics and communities are computed.
4. **Service:** the API reads entities and already-persisted results.
5. **Presentation:** the frontend queries the API, caches with TanStack Query and renders tables, detail pages and graphs.

The API never calls MusicBrainz during a request. If external search is needed in the future, it will be implemented as an ingestion or explicit cache process, not as a synchronous user dependency.

## 5. Modules and boundaries

Proposed repository structure (created in E1):

```
backend/
  src/hmde/
    api/          routers, HTTP dependencies, errors
    core/         configuration, logging, cross-cutting utilities
    db/           session, declarative base, migrations
    models/       SQLAlchemy models
    schemas/      Pydantic input/output schemas
    services/     API use cases
    etl/          ingestion, normalization, quality
    analytics/    batch graphs and metrics
  tests/
frontend/
  src/
    api/          generated client and queries
    components/
    pages/
    hooks/
docs/             stable reference documentation
specs/            active SDD specs and templates
spike/            disposable research code
infra/
  compose/
data/             local raw data, outside Git
```

Dependency rules:

- `api` may depend on `services`, `schemas` and `db`; not on `etl` or `analytics`.
- `etl` may depend on `models`, `db` and `core`; not on `api`.
- `analytics` reads the normalized layer and writes the analytical layer; not on `api`.
- `models` does not depend on `api` or `etl`.
- The frontend does not import Python code; it consumes OpenAPI.

No generic repository layer is created over SQLAlchemy. API services encapsulate queries and use cases; SQLAlchemy handles persistence. If a query is complex, it is isolated in a function in the relevant module, not in a universal abstraction.

## 6. Technology

### Adopted in the MVP

| Technology | Use |
|---|---|
| Python + uv | Backend, ETL and analysis; reproducible environment |
| FastAPI + Pydantic v2 | API and schema validation |
| Synchronous SQLAlchemy 2.0 + psycopg | Persistence; decision in [ADR-0003](adr/ADR-0003-synchronous-sqlalchemy.md) |
| Alembic | Reviewed and versioned migrations |
| PostgreSQL | Relational data, integrity and search with `tsvector`/trigrams |
| httpx | Ingestion HTTP client with limits and retries |
| Pandas | Transformation and exploratory analysis for the MVP |
| NetworkX | Graphs, centrality and communities |
| pytest | Backend and data tests |
| Ruff | Python lint and formatting |
| React + TypeScript + Vite | Frontend |
| TanStack Query | Server state and caching |
| React Router | Navigation |
| Tailwind CSS | Styling |
| Cytoscape.js | Graph visualization |
| Plotly | Statistical and temporal charts |
| Docker Compose | PostgreSQL, backend and development profiles |
| GitHub Actions | CI |
| `openapi-typescript` | TypeScript type generation from OpenAPI |

### Deferred until a need exists

| Technology | Reason |
|---|---|
| Polars | Only if volume or Pandas performance justifies it |
| SciPy / scikit-learn | Only if a concrete metric requires them |
| BeautifulSoup | Only if HTML extraction is approved; prefer APIs |
| Playwright | Added in E11 for end-to-end tests |
| Vitest / React Testing Library | Added in E9 for frontend tests |
| Redis / Celery | No asynchronous user jobs in the MVP |
| Neo4j | PostgreSQL + NetworkX are enough for the expected volume |
| Airflow / Prefect / Dagster | An idempotent CLI and a Makefile are enough |
| Kubernetes | Docker Compose is enough for v0.1 |

### Excluded from the MVP

- Kafka and streaming architectures.
- Microservices.
- Graph databases.
- Elasticsearch/OpenSearch.
- Streamlit as the product interface.
- Discogs and Encyclopaedia Metallum as sources.

## 7. Data layers

| Layer | Content | Retention |
|---|---|---|
| Raw | Original responses, URL, date, hash, status | Permanent for traceability |
| Normalized | Canonical entities, credits, roles, external IDs, genres | Permanent |
| Analytical | Graph snapshots, metrics, communities and runs | Versioned by `analysis_run` |
| Service | Read queries and aggregates | Derived; not a source of truth |

Raw and normalized layers are separated so data can be reprocessed without calling the source again. Raw data is never edited by hand.

## 8. API principles

- `/api/v1` prefix from the first endpoint.
- Read-only in the MVP; no user authentication.
- Mandatory pagination on collections; explicit maximum limit.
- Whitelisted filters and Pydantic validation.
- Errors with a consistent structure and stable code.
- OpenAPI as the contract; TypeScript types are generated, not hand-written.
- Subgraphs with maximum depth and size; never serve the entire graph.
- Search with PostgreSQL; no external engine is added.
- CORS restricted to the frontend origin.
- Rate limiting at the edge (reverse proxy) when published.

The read-only decision is recorded in [ADR-0006](adr/ADR-0006-read-only-api.md).

## 9. Frontend principles

- Filter and navigation state lives in the URL when it is shareable.
- TanStack Query handles caching, retries and loading states.
- API types are generated from OpenAPI; they are not duplicated by hand.
- Heavy routes (graph, charts) are lazy-loaded.
- Cytoscape is used with node limits and expansion on demand.
- Plotly is reserved for statistical and temporal charts.
- Every graph visualization has an accessible table alternative.
- The UI visually distinguishes confirmed, inferred and missing data.

## 10. Provisional non-functional requirements

| Requirement | Initial target |
|---|---|
| Entity and list latency | p95 ≤ 300 ms with the MVP dataset |
| 500-node subgraph | p95 ≤ 1 s server-side |
| Graph interactivity | 500 nodes fluid; 2000 nodes with limits and expansion |
| Scalability | 200–500 bands and tens of thousands of credits without architecture change |
| Reproducibility | Repeatable ingestions and analyses with parameters and dataset version |
| Accessibility | WCAG 2.1 AA baseline on main flows; audit in E11 |
| Availability | No SLA for v0.1 |
| Security | Read-only, no PII, secrets outside the repository |

Targets are validated in E11 and adjusted with real measurements.

## 11. Security and privacy

- No user personal data is stored; the MVP has no accounts.
- Artist data is public information from the music domain.
- Secrets and tokens live in environment variables; `.env` is outside Git.
- Input validation on every endpoint.
- Restricted CORS and security headers at the proxy.
- Dependencies reviewed and updated periodically.
- External sources are consumed with an identifiable User-Agent and rate limits.

## 12. Observability

- Structured logging with level, timestamp, component and request ID.
- Ingestion (`ingest_run`) and analysis (`analysis_run`) run records.
- Minimum operational metrics: duration, processed records, errors and quarantine.
- No distributed tracing or Prometheus in the MVP.
- Quality and coverage reports are part of data observability.

## 13. Testing strategy

| Level | What it covers |
|---|---|
| Unit | Normalization, role mapping, identity rules, calculations |
| Integration | Repositories, migrations and endpoints against real PostgreSQL |
| Contract | API responses against OpenAPI |
| Data | Ingestion fixtures and quality rules |
| Frontend | Components and loading/error/empty states |
| End-to-end | Critical flows in E11 |
| Performance | Subgraphs and main endpoints in E11 |

PostgreSQL runs in Docker Compose locally and as a CI service. Integration tests use transactions with rollback.

## 14. Deployment

- Docker Compose for PostgreSQL, backend and production frontend.
- Reverse proxy with TLS in the deployment environment.
- Alembic migrations as an explicit deployment step.
- PostgreSQL backups and a restore test in E11.
- No Kubernetes, autoscaling or provider-specific managed services in v0.1.

## 15. Open decisions

- Raw data storage: JSONB table versus files with database metadata.
- Exact aggregation rule for credits across editions of the same album.
- Final subgraph and pagination limits.
- Exact versus fuzzy search strategy.
- Dataset snapshot format and frequency.
- Whether a full-text index is actually needed versus trigrams.

These will be resolved in E2, E7 or E8 as appropriate, with an ADR if the decision is structural.

## 16. References

- [Data model v0](data-model.md)
- [Engineering conventions](conventions.md)
- [ADR-0001 — Modular monolith](adr/ADR-0001-modular-monolith.md)
- [ADR-0002 — MusicBrainz as primary source](adr/ADR-0002-musicbrainz-primary-source.md)
- [ADR-0003 — Synchronous SQLAlchemy](adr/ADR-0003-synchronous-sqlalchemy.md)
- [ADR-0004 — Release-group model](adr/ADR-0004-release-group-model.md)
- [ADR-0005 — Identity and provenance](adr/ADR-0005-identity-and-provenance.md)
- [ADR-0006 — Read-only API](adr/ADR-0006-read-only-api.md)
- [ADR-0007 — Credit scope and recording-level aggregation](adr/ADR-0007-credit-scope-and-recording-level-aggregation.md)
- [Source evaluation](../03-data/sources.md)
- [MusicBrainz spike report](../03-data/spike-report.md)
