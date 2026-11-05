# Architecture Decision Records

- **Status:** Current index
- **Version:** 0.1
- **Date:** 2026-11-04

ADRs record architectural decisions and their rationale. They are never deleted: if a decision changes, a new ADR is created that supersedes the previous one.

| ADR | Decision | Status |
|---|---|---|
| [ADR-0001](ADR-0001-modular-monolith.md) | Modular monolith with API and data CLI | Accepted |
| [ADR-0002](ADR-0002-musicbrainz-primary-source.md) | MusicBrainz as primary source; limited complementary sources | Accepted |
| [ADR-0003](ADR-0003-synchronous-sqlalchemy.md) | Synchronous SQLAlchemy for the MVP | Accepted |
| [ADR-0004](ADR-0004-release-group-model.md) | Release-group as canonical album | Accepted with amendment by ADR-0007 |
| [ADR-0005](ADR-0005-identity-and-provenance.md) | Deterministic identity and mandatory provenance | Accepted |
| [ADR-0006](ADR-0006-read-only-api.md) | Public read-only API in v0.1 | Accepted |
| [ADR-0007](ADR-0007-credit-scope-and-recording-level-aggregation.md) | Credit scope and recording-level aggregation | Accepted |

## Template

Each ADR must include: title, status, date, context, decision, consequences, alternatives considered and references. It should be brief and explain the **why**, not repeat the implementation.
