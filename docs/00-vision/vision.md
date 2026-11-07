# Project vision

- **Status:** Approved
- **Version:** 0.2
- **Date:** 2026-11-06
- **Stage:** E0

## 1. Problem

Information about who produced, recorded, mixed or mastered a heavy metal album is scattered across databases, wikis, discographies and release credits. It is difficult to answer questions that cross people, bands, albums, studios, subgenres and decades, and even harder to do so with traceability to the origin of each data point.

Existing tools allow users to consult isolated entries, but not to systematically explore the network of professional relationships behind music production. They also rarely distinguish clearly between a documented credit, an inferred data point and a missing one.

## 2. Value proposition

HMDE builds a structured and traceable database of professional production relationships in heavy metal, and exposes it through an exploration and network analysis interface.

The product allows users to:

- Explore bands, albums, producers, engineers and studios.
- Navigate the relationships between them.
- Filter by period, subgenre, role and entity type.
- Visualize collaboration networks.
- Query precomputed metrics and analyses about the structure of those networks.
- See the provenance and confidence level of every credit.

## 3. Users

The primary user is someone with analytical curiosity: a researcher, music journalist, student, data scientist or advanced fan. The product does not assume expertise in databases or graph theory.

They need to:

- Ask exploratory questions without writing SQL.
- Move from a band or producer to related entities.
- Understand which data is documented and which is missing.
- Export or cite results with traceability.

## 4. Research questions

The MVP should make it possible to address, at least exploratorily:

1. Which producers participate most in heavy metal history?
2. Which producers connect different metal subgenres?
3. Which bands have worked with producers in common?
4. Which albums are connected through shared producers, engineers or studios?
5. How do collaboration networks evolve by decade?
6. Do communities of producers, bands and albums emerge?
7. How concentrated is production around certain producers or studios?
8. What relationship exists between professional connections and album characteristics?

Questions 1–7 are the MVP core. Question 8 is addressed only in its relational dimension; acoustic analysis and listener preferences are out of scope.

## 5. Conceptual distinctions

The project must keep three notions separate:

| Notion | What it measures | Typical source | MVP status |
|---|---|---|---|
| Professional relationship | Who worked with whom, on which album and in which role | Production credits | Core |
| Musical affinity | Sonic or stylistic similarity between albums | Audio analysis, tags, criticism | Out of MVP |
| Listener preference | What the audience listens to or values | Plays, ratings, surveys | Out of MVP |

A shared credit does not demonstrate musical affinity, causal influence or preference. The interface and analyses must avoid suggesting those interpretations.

## 6. Principles

- **Traceability:** every normalized data point can be traced back to its source and retrieval date.
- **Explicit uncertainty:** confirmed, inferred, conflicting and missing data are distinguished.
- **Absence is not negative evidence:** a missing credit does not mean the person did not participate.
- **Reproducibility:** ingestions and analyses can be repeated with the same data and parameters.
- **Simplicity:** modular monolith, PostgreSQL and batch processes; no premature distributed infrastructure.
- **Licensing and attribution:** each source's terms are respected and the corresponding attribution is shown.
- **Critical interpretation:** results describe the available sample and coverage, not the entire scene.
- **Vertical delivery:** each stage delivers a verifiable functional slice, not only a technical layer.

## 7. v0.1 success criteria

A first version is useful if it:

- Allows exploration of the active 57-band corpus across the 1960–2026 period, with their albums and available production credits; the corpus grows through versioned batches.
- Allows navigation from a band to its albums, from an album to its producers, and from a producer to their collaborations.
- Shows an interactive professional relationship graph with basic filters and size limits.
- Exposes precomputed metrics for participation, concentration and communities.
- Shows the source and confidence status of every visible credit.
- Includes a coverage and limitations report for the dataset.
- Keeps ingestion, normalization and analyses reproducible.
- Has automated tests and documentation for architecture, data and API.

## 8. Out of scope

- Audio analysis, acoustic similarity and listener preferences.
- User accounts, public contributions and data editing.
- Complete encyclopedic coverage of heavy metal.
- Discogs or Encyclopaedia Metallum integration in the MVP.
- Causal inference or attribution of musical influence.
- Mobile application, internationalization and real-time features.
- Kubernetes, Kafka, Redis, Celery or graph databases.

## 9. Medium-term vision

The design must support growth from dozens to hundreds of bands without changing the architecture: incremental ingestions, dataset versioning, pagination, subgraph limits and precomputed analytical results.

Future extensions — audio analysis, preferences, additional sources, user collaboration — will be evaluated when a concrete need and the data to support them exist.
