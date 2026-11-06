# Heavy Metal Data Explorer (HMDE)

HMDE is a public, read-only application for exploring professional production relationships in heavy metal: who produced, recorded, mixed or mastered an album, and how those people, bands, albums and studios connect.

The MVP focuses on 42 bands with studio albums released between 1980 and 2000. The architecture supports growth to 200–500 bands without redesign.

## Status

- **E0:** complete. Documents, MusicBrainz feasibility spike and the 42-band seed list are ready.
- **Application code:** not started. The repository skeleton is built in E1.
- **Next work:** SPEC-001 is in implementation; T-001–T-005 are complete and T-006 is next.
- **Current SDD index:** [`specs/README.md`](specs/README.md).

## What the MVP will provide

- Exploration of bands, albums, producers, engineers and studios.
- Navigation through production credits and shared collaborators.
- Filters by period, subgenre and role.
- Interactive collaboration graphs.
- Precomputed metrics and community analysis.
- Provenance and confidence for every credit.

Out of scope for the MVP: audio analysis, listener preferences, user accounts, complete metal encyclopedia coverage, Discogs, Encyclopaedia Metallum and distributed infrastructure.

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

## Quick start

There is no runnable application yet. Quick-start commands will be added in `specs/001-foundations/` and verified from a clean checkout.

The disposable MusicBrainz spike can be run with:

```bash
python3 spike/spike_musicbrainz.py
```

It requires network access and respects MusicBrainz's one-request-per-second limit. See [`spike/README.md`](spike/README.md).

## Repository layout

```text
constitution.md     Stable project principles
AGENTS.md           Operational instructions for agents
specs/              Active SDD specs, templates and index
docs/               Reference documentation
backend/            Backend application (from E1)
frontend/           React application (from E1)
compose.yaml        Development services (from E1)
infra/              Dockerfiles and container assets (from E1)
data/               Seed list and local raw data
spike/              Disposable MusicBrainz research
```

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
