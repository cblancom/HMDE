# AGENTS.md

Operational instructions for working in this repository.

## 1. Project summary

Heavy Metal Data Explorer (HMDE) is a public, read-only application for exploring professional production relationships in heavy metal. The MVP covers 42 bands with studio albums released between 1980 and 2000, with a growth path to 200–500 bands.

Stack once implementation starts:

- Backend: Python, FastAPI, Pydantic v2, synchronous SQLAlchemy 2.0, psycopg, Alembic.
- Database: PostgreSQL.
- Data and analysis: httpx, Pandas, NetworkX.
- Frontend: React, TypeScript, Vite, TanStack Query, React Router, Tailwind, Cytoscape.js, Plotly.
- Infrastructure: Docker Compose, uv, GitHub Actions.
- Tests: pytest, Vitest, React Testing Library, Playwright (later).

`constitution.md` contains stable principles. `docs/` contains reference material. `specs/` contains active SDD work. `spike/` contains disposable research code and is not production code.

## 2. Current state

- E0 is complete: vision, scope, roadmap, architecture, source evaluation, the MusicBrainz spike and the 42-band seed list are complete.
- The seed list is versioned at `data/seed-list.json` (v0.1.0).
- No application code exists yet. The repository is initialized in E1.
- The next spec is `specs/001-foundations/` (E1), followed by `specs/002-seed-band-explorer/` (E2).
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
├── infra/
├── spike/
└── data/
```

Do not create empty directories or extra layers without a need.

## 4. Canonical commands

No application commands exist yet. They are defined and verified in `specs/001-foundations/`.

After E1, this section must contain the exact commands for:

- Backend sync, format, lint and tests.
- Frontend install, dev, lint, typecheck, tests and build.
- Database migrations.
- Docker Compose development and production.
- Smoke tests.

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
- `Approved`
- `In implementation`
- `Implemented`
- `Validated`
- `Superseded`

`Implemented` means code is complete. `Validated` means acceptance criteria have evidence. Do not use them interchangeably.

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
