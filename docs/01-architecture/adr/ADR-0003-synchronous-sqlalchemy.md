# ADR-0003 — Synchronous SQLAlchemy for the MVP

- **Status:** Accepted
- **Date:** 2026-11-04
- **Deciders:** Cristian, project architecture

## Context

The API is read-only and the expected volume is modest: tens of thousands of credits and hundreds of bands. The team wants simplicity, clear tests and a single data-access path shared by the API and ETL. FastAPI supports synchronous endpoints executed in a thread pool, which is sufficient for this case.

## Decision

- Use **SQLAlchemy 2.0 in synchronous mode** with the `psycopg` driver for API, ETL and analysis.
- FastAPI endpoints that access the database are synchronous and run in the thread pool.
- `httpx` may be used asynchronously **only** for external ingestion, where concurrency adds value.
- Do not maintain two drivers or two session configurations for the same schema.

## Consequences

**Positive:**

- Less debugging and testing complexity.
- A single session and transaction pattern for all processes.
- Less risk of locks or connection leaks from misuse of `async`.
- Performance is adequate for the MVP volume.

**Negative:**

- API concurrency is limited by the thread pool.
- A slow query can occupy a thread.
- If traffic grows significantly, the model will need review.

**Review condition:**

Asynchronous mode will be reconsidered if E11 measurements show thread-pool saturation or latencies incompatible with the targets. The decision will be recorded in a new ADR.

## Alternatives considered

| Alternative | Reason for rejection |
|---|---|
| Async SQLAlchemy | Additional complexity without demonstrated need |
| Raw SQL | Loses typing and model maintainability |
| Two drivers (sync ETL, async API) | Duplicates configuration and increases divergence risk |

## References

- [Architecture overview](../overview.md)
- [Testing strategy](../overview.md#13-testing-strategy)
