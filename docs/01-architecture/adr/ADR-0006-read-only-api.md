# ADR-0006 — Public read-only API in v0.1

- **Status:** Accepted for v0.1
- **Date:** 2026-11-04
- **Deciders:** Cristian, project architecture

## Context

The first version is an exploration application. There are no requirements for accounts, contributions, editing or writes. Adding authentication and permissions from the start would increase complexity without adding MVP value.

## Decision

- The API is **public and read-only**.
- There is no user authentication or authorization in v0.1.
- All endpoints are exposed under `/api/v1`.
- No writes are accepted from the frontend.
- Ingestion and analyses run outside the API, with controlled environment access.
- Restricted CORS, input validation and edge rate limiting are applied at deployment.
- No user personal data is stored.

## Consequences

**Positive:**

- Small security surface.
- Less development and testing complexity.
- Focus remains on data quality and exploration.

**Negative:**

- Users cannot contribute or correct data.
- If accounts are needed later, authentication, authorization and auditing will have to be introduced.
- Rate limiting must be handled by infrastructure, not by the application.

**Review condition:**

Any write feature, account or private data requires a new ADR and a security review.

## Alternatives considered

| Alternative | Reason for rejection |
|---|---|
| Authentication from the start | No use case justifies it |
| Write API for administration | ETL already covers ingestion |
| GraphQL | REST is sufficient and simpler for this domain |
| Separate backend-for-frontend | Adds a layer without a need |

## References

- [Architecture overview](../overview.md)
- [Scope](../../00-vision/scope.md)
