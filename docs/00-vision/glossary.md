# Glossary

- **Status:** Draft
- **Version:** 0.1
- **Date:** 2026-11-04

Domain and methodology terms. English identifiers are the ones used in code and the database.

## Music domain

| Term | Definition |
|---|---|
| **Heavy Metal** | Broad set of genres derived from heavy rock; in this project it is used as an umbrella term, not a single genre. |
| **Subgenre** | Analytical category within metal (thrash, death, black, power, doom, progressive, heavy). It is not an objective truth. |
| **Artist** | Person or group that performs, composes or participates in production. MusicBrainz includes both types. |
| **Band / group** | Artist of type group. |
| **Canonical album (`release-group`)** | Abstract work that groups the editions of an album. It is the MVP unit of analysis. |
| **Edition (`release`)** | Concrete physical or digital object of a canonical album. It may have different credits. |
| **Recording** | Recorded track or performance. It can carry credits that are not present at release level. |
| **Credit** | Documented relationship between an artist and a recording, edition or album, with a role and a source. |
| **Credit scope** | Level at which a credit is attached: `release_group`, `release` or `recording`. |
| **Role** | Function performed in production: producer, co-producer, engineer, mix, mastering, etc. |
| **Producer** | Person or group responsible for the artistic and technical direction of a recording. Core role in the MVP. |
| **Co-producer** | Shared production role; analyzed together with producer in the core. |
| **Executive producer** | Financial or strategic supervision role; stored as an extended role. |
| **Engineer** | Technical person responsible for recording or the studio. |
| **Mix** | Person responsible for the final mix. |
| **Mastering** | Person responsible for final processing for distribution. |
| **Studio (`place`)** | Place where recording, mixing or mastering happens. Source coverage may be limited. |
| **Discography** | Set of albums and editions attributed to an artist. |
| **Musical affinity** | Sonic or stylistic similarity between albums. It is not inferred from sharing a producer. |
| **Listener preference** | What music the audience consumes or values. Out of MVP scope. |

## Data and identity

| Term | Definition |
|---|---|
| **Canonical entity** | Normalized record representing a person, group, album or studio inside HMDE. |
| **External identifier** | Identifier of an entity in a source: MBID, Wikidata QID, Discogs ID, etc. |
| **MBID** | MusicBrainz Identifier. Stable UUID of a MusicBrainz entity. |
| **QID** | Wikidata item identifier. |
| **Alias** | Alternative name of an artist or entity. It does not imply a duplicate. |
| **Identity resolution** | Process of deciding whether two records from different sources represent the same entity. |
| **Deduplication** | Controlled removal or merging of duplicate records. |
| **Deterministic match** | Match based on a unique identifier or exact rule, without fuzzy matching. |
| **Quarantine** | Record that cannot be normalized or validated and is kept for review. |
| **Provenance** | Origin of a data point: source, URL, date, version and transformations applied. |
| **Confidence** | Degree of certainty of a credit or mapping. It must be explicit, not implicit. |
| **Absence is not negative** | A missing credit does not prove that the person did not participate. |
| **Confirmed data** | Data backed by an identifiable source. |
| **Inferred data** | Data derived by a rule or model, with evidence and a confidence level. |
| **Conflicting data** | Two sources disagree; both are kept until resolved. |

## Pipeline and analysis

| Term | Definition |
|---|---|
| **Ingestion** | Extraction of data from a source and raw storage with metadata. |
| **Raw data** | Original source response, preserved for traceability. |
| **Normalization** | Transformation of raw data into the canonical model. |
| **Snapshot / dataset version** | Frozen dataset at a point in time, identifiable and reproducible. |
| **Ingest run (`ingest_run`)** | Record of an execution: source, parameters, date, results and errors. |
| **Analysis run (`analysis_run`)** | Record of an analytical computation: dataset, parameters, code version and results. |
| **Bipartite graph** | Graph with two node types (e.g., artists and albums) and credit edges. |
| **Projection** | Derived graph connecting nodes of the same type (e.g., producer–producer). |
| **Centrality** | Measure of a node's structural importance in a network. |
| **Community** | Group of nodes more densely connected to each other than to the rest. |
| **Concentration** | Degree to which activity is distributed among few actors (Gini, HHI). |
| **Subgraph** | Portion of the graph obtained from a seed node and a depth. |
| **Supporting recording ratio** | Share of an album's recordings that support a recording-level credit. |

## Methodology

| Term | Definition |
|---|---|
| **SDD** | Specification-Driven Development: specify before implementing. |
| **Stage** | Broad roadmap phase with its own objectives and deliverables. |
| **Vertical feature** | Capability that crosses data, API and UI, delivered in a verifiable way. |
| **Spec** | Document defining the behavior, scope and acceptance criteria of a feature. |
| **Acceptance criterion** | Verifiable condition that determines whether a feature meets its specification. |
| **ADR** | Architecture Decision Record: record of an architectural decision and its rationale. |
| **Walking skeleton** | Minimal slice that crosses all layers and validates the architecture. |
| **Definition of Ready (DoR)** | Conditions a spec must meet before implementation. |
| **Definition of Done (DoD)** | Conditions a feature must meet to be considered complete. |
| **Stage gate** | Exit criterion that must be met before moving to the next stage. |
