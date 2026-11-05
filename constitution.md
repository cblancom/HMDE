# HMDE Constitution

## 1. Purpose

Heavy Metal Data Explorer (HMDE) is a public, read-only application for exploring and analyzing professional production relationships in the heavy metal scene. The MVP covers 42 bands with studio albums released between 1980 and 2000, with a growth path to 200–500 bands.

The project builds a traceable database of credits, artists, albums, editions, recordings and studios, and exposes exploration and network analysis through a React frontend and a FastAPI backend.

Detailed product boundaries live in [`docs/00-vision/scope.md`](docs/00-vision/scope.md). Architectural details live in [`docs/01-architecture/overview.md`](docs/01-architecture/overview.md).

## 2. Product principles

### 2.1 Professional relationships are not musical affinity

The MVP models who worked with whom, on which album, in which role and according to which source. It does not infer musical similarity, influence or listener preference from shared credits.

### 2.2 Provenance is mandatory

Every normalized data point must be traceable to its source, retrieval date, raw payload and license. Raw data is preserved and never edited by hand.

### 2.3 Absence is not negative evidence

A missing credit does not prove that a person did not participate. Coverage gaps are reported; they are not converted into negative claims.

### 2.4 Identity is deterministic

MBID and other exact identifiers are the basis for identity. Automatic fuzzy merging is prohibited in the MVP. Ambiguities go to quarantine or manual review, and every merge leaves an audit trail.

### 2.5 Respect source terms

MusicBrainz is the primary source. Its one-request-per-second limit and User-Agent requirement are mandatory. Discogs and Encyclopaedia Metallum are out of the MVP because their access terms are incompatible with the project's historical snapshot model or are not clearly authorized.

### 2.6 Credit scope is explicit

Credits may be attached to a release-group, a release or a recording. Album-level credits are a projection with supporting-recording counts and ratios, not an invented fact. See [ADR-0007](docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md).

### 2.7 Simplicity first

The system is a modular monolith: FastAPI, synchronous SQLAlchemy, PostgreSQL and batch Python processes. The React frontend consumes the API. There are no microservices, Kubernetes, Kafka, Redis, Celery or graph databases in the MVP.

New dependencies, services or abstractions require a demonstrated need and an ADR when the decision is architectural.

### 2.8 Reproducibility

Ingestions and analyses must be repeatable with the same inputs, parameters and dataset version. Dependencies are locked, migrations are versioned and raw responses are cached or snapshotted.

### 2.9 Language

All project content is written in English: documentation, code, identifiers, API descriptions, UI copy and commit messages. Conversation with the project owner may be in Spanish.

### 2.10 Quality and traceability

Every relevant behavior has automated tests or explicit verification evidence. Requirements, design, tasks and acceptance criteria are traceable. A task is not done because code exists; it is done when its acceptance criteria are verified.

## 3. Work rules

- Follow the SDD workflow: specify → clarify → plan → tasks → implement → validate.
- Do not implement a feature whose `spec.md`, `plan.md` or `tasks.md` is not approved.
- Do not create `plan.md` while the spec has blocking open questions.
- Do not start implementation until `tasks.md` is approved.
- Update the spec first when a decision or scope changes.
- Record architectural decisions in ADRs.
- Do not commit, push, deploy or perform destructive operations without an explicit request and a security confirmation.
- Do not hide failures or modify tests to simulate success.
- Do not add scope to avoid a difficult requirement.

## 4. Minimum quality gates

- Backend: lint, format check and tests pass.
- Frontend: lint, typecheck, tests and build pass.
- Database migrations apply from an empty database and have a working downgrade.
- OpenAPI and generated TypeScript types are up to date.
- Documentation affected by the change is updated.
- No secrets, credentials or personal data are committed.
- The change can be demonstrated end to end.

Exact commands are maintained in [`AGENTS.md`](AGENTS.md) once the application skeleton exists.

## 5. Governance

This constitution changes only when the project's stable principles change. Any change requires justification, explicit approval and review of affected specs and ADRs.

In case of conflict, the precedence order is:

1. Security and data integrity.
2. Provenance, licensing and traceability.
3. Approved specifications and ADRs.
4. Implementation convenience.

`AGENTS.md` contains operational instructions. `specs/` contains active SDD work. `docs/` contains stable reference material. ADRs contain architectural decisions.
