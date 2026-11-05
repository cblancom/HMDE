# ADR-0001 — Modular monolith with API and data CLI

- **Status:** Accepted
- **Date:** 2026-11-04
- **Deciders:** Cristian, project architecture

## Context

The project combines a read API, ingestion and normalization processes, and graph analysis. The team is small and the MVP volume does not justify distributed infrastructure. Even so, the API must not run expensive analyses or call external sources during a request.

## Decision

A **modular monolith** is adopted in a single repository and a single Python package, with two entry points:

1. **FastAPI API** serving data to the frontend.
2. **Data and analysis CLI** for ingestion, normalization, validation and batch computations.

Both share models, configuration and PostgreSQL access, but run as separate processes. Boundaries are enforced through modules and dependency rules:

- `api` does not import `etl` or `analytics`.
- `etl` does not import `api`.
- `analytics` reads normalized data and writes analytical results.
- PostgreSQL is the contract between the batch world and the API.

## Consequences

**Positive:**

- Simple development and deployment.
- Less operational latency and fewer pieces to monitor.
- Straightforward integration tests with a single database.
- A module can be extracted into a service if a real need appears.

**Negative:**

- Coupling risk if boundaries are not respected.
- A change to shared models can affect both API and ETL.
- API and batch share a repository, though not a process.

**Mitigations:**

- Import review in CI or with Ruff.
- Modules with explicit responsibilities.
- No generic abstractions until real duplication exists.
- Split into services only with evidence of scale or independent deployment needs.

## Alternatives considered

| Alternative | Reason for rejection |
|---|---|
| Microservices | Unnecessary operational complexity for the volume and team |
| Separate repositories | Makes atomic changes across model, API and ETL harder |
| API and ETL in the same process | Mixes request cycles with expensive jobs |
| Serverless | Adds provider coupling without a need |

## References

- [Architecture overview](../overview.md)
- [Roadmap](../../00-vision/roadmap.md)
