# ADR-0007 — Credit scope and recording-level aggregation

- **Status:** Accepted
- **Date:** 2026-11-05
- **Deciders:** Cristian, project architecture
- **Evidence:** [MusicBrainz spike report](../../03-data/spike-report.md)

## Context

MusicBrainz can attach artist relationships to a release-group, a release or a recording. The E0 spike found that production credits are frequently attached to recordings rather than releases:

- 73 of 206 album candidates (35.4%) had a release-level producer credit.
- 105 of 206 (51.0%) had a producer credit only at recording level.
- Among the 178 albums with any producer credit, 59.0% depended on recording-level data.

A model that only reads release-level credits would miss most of the available production data. At the same time, a producer credit on one track is not necessarily equivalent to a full-album production credit.

The project needs a representation that preserves the original scope and supports explicit album-level aggregation without overstating coverage.

## Decision

1. A **credit** can be attached to one of three scopes:
   - `release_group`
   - `release`
   - `recording`
2. Recording-scoped credits store `recording_id` (MBID) and preserve the parent `release_id` and `release_group_id` as context.
3. Album-level credits are a **projection**, not a stored fact. The projection preserves:
   - the source scope of each supporting credit;
   - the number of supporting recordings;
   - the total number of recordings considered;
   - the aggregation rule and confidence.
4. The MVP default includes every credit with at least one supporting recording or release, but exposes `supporting_recording_count` and `supporting_recording_ratio` so analyses can filter for full-album credits.
5. Edge weight in the album-level network can use the number of supporting recordings or a binary flag, depending on the analysis. The chosen weight must be declared in `analysis_run`.
6. The role mapping handles producer attributes explicitly:
   - `producer` → `producer`
   - `producer` + `co` → `co-producer`
   - `producer` + `executive` → `executive producer`
   - `producer` + `assistant` → `assistant producer`
   - `producer` + `additional` → `additional producer`
7. Raw role text and attributes are preserved for traceability.

## Consequences

**Positive:**

- Captures production data that a release-only model would miss.
- Distinguishes full-album from partial-track credits.
- Keeps provenance and avoids inventing an album-level fact.
- Supports different analytical definitions without re-ingestion.

**Negative:**

- Adds a `recording` entity and a scope discriminator to the model.
- Increases ingestion volume and response size.
- Requires an aggregation rule and transparent reporting of support.
- Some analyses may need to choose between binary and weighted edges.

**Mitigations:**

- Fetch recording-level relationships only where needed during the spike; production ingestion can fetch them systematically with caching.
- Store support counts and ratios rather than a single boolean.
- Report the aggregation rule in every analysis run.
- Provide a "full-album" filter for sensitivity analysis.

## Alternatives considered

| Alternative | Reason for rejection |
|---|---|
| Store only release-level credits | Misses 59% of producer-covered albums in the spike |
| Store only release-group-level credits | Nearly no production credits in MusicBrainz |
| Treat any recording credit as a full-album credit | Overstates full-album production |
| Infer missing credits from Wikipedia | Deferred; fragile and license-sensitive |
| Use only the first track as representative | Arbitrary and biased |

## Validation

The decision is based on the E0 spike: 28 bands, 206 album candidates, 178 albums with producer/co-producer credit, 105 of them dependent on recording-level data. The sample is not statistically representative, but the magnitude is large enough to make the scope decision necessary before implementation.

## References

- [MusicBrainz spike report](../../03-data/spike-report.md)
- [ADR-0004 — Release-group as canonical album](ADR-0004-release-group-model.md)
- [Data model v0](../data-model.md)
- [MusicBrainz API — Relationships](https://musicbrainz.org/doc/MusicBrainz_API#Relationships), accessed 2026-11-05.
