# ADR-0004 — Release-group as canonical album

- **Status:** Accepted with amendment by [ADR-0007](ADR-0007-credit-scope-and-recording-level-aggregation.md)
- **Date:** 2026-11-04; amended 2026-11-05
- **Deciders:** Cristian, project architecture
- **Evidence:** [MusicBrainz spike report](../../03-data/spike-report.md)

## Context

MusicBrainz distinguishes between `release-group` (the abstract work, for example the album "Master of Puppets") and `release` (each concrete edition: original vinyl, remastered CD, edition from another country). Credits may vary between editions. Treating each edition as an independent album would duplicate albums and bias metrics; using only the release-group could lose credits that appear only in one edition.

The project needs a stable unit of analysis for questions about albums, producers and decades.

## Decision

1. The **canonical album** is the `release-group` with primary type `album`.
2. All secondary types are excluded: `audio drama`, `audiobook`, `compilation`, `demo`, `dj-mix`, `field recording`, `interview`, `live`, `mixtape/street`, `remix`, `soundtrack` and `spokenword`.
3. The **album date** is the first release date of the `release-group`, with its precision recorded.
4. **Credits are captured at their original scope** — release-group, release or recording — preserving the edition, recording, date and provenance. Recording-level scope is defined in [ADR-0007](ADR-0007-credit-scope-and-recording-level-aggregation.md).
5. Credits are **aggregated to the canonical album** through an explicit rule:
   - each underlying credit is preserved;
   - equivalent credits for the same artist and role within the album are deduplicated;
   - the editions and recordings supporting the credit are preserved;
   - the aggregation basis and supporting-recording ratio are recorded;
   - conflicts are kept and flagged.
6. If a source only provides a release-group-level credit, it may be recorded as an album credit with provenance and confidence.

## Consequences

**Positive:**

- Avoids counting reissues as separate albums.
- Enables temporal analysis with a stable unit.
- Preserves edition and recording richness and provenance.
- Makes album-to-album comparison easier.
- Captures recording-level production credits that a release-only model would miss.

**Negative:**

- Increases model and query complexity.
- Requires deduplication rules across editions and recordings.
- The album date may not match the date of the edition or recording containing the credit.
- Some reissue or partial-track credits may not reflect the original full-album production.
- Ingestion must fetch recording-level relationships.

**Mitigations:**

- Always store `release_id`, `release_group_id`, `recording_id` where applicable, and edition date.
- Allow analyses to filter by "original edition only", "all editions" or "full-album support".
- Report how many credits come from reissues or partial recording support.
- Validate the rule in E2 and E6.

## Spike outcome

The E0 spike covered 28 bands and 206 album candidates:

- 86.4% had a producer/co-producer credit; 89.0% excluding six low-confidence release-groups.
- Only 73 albums (35.4%) had a release-level producer credit.
- 105 albums (51.0%) had a producer credit only at recording level.
- 80.1% had a studio/place credit.
- Six release-groups typed as albums were low-confidence (one/two releases or suspicious title).
- Coverage varied by subgenre (Black Metal 58.3% producer coverage vs Heavy Metal 97.7%).

The release-group model is validated. The spike also shows that recording-level credits are required, hence the amendment by ADR-0007.

## Alternatives considered

| Alternative | Reason for rejection |
|---|---|
| Use each `release` as an album | Duplicates albums and biases metrics |
| Use only `release-group` without editions | Loses credits and provenance |
| Use another source's "master release" | Unnecessary dependency and less stable definition |
| Choose the earliest edition as canonical | Useful as a reference, but does not resolve credits from other editions |

## Remaining validation for E2

- Physical schema for scoped credits and album-level projections.
- Aggregation threshold for treating a recording-level credit as full-album support.
- Handling of low-confidence release-groups.
- Deduplication across editions and recordings.

## References

- [MusicBrainz spike report](../../03-data/spike-report.md)
- [ADR-0007 — Credit scope and recording-level aggregation](ADR-0007-credit-scope-and-recording-level-aggregation.md)
- [MusicBrainz API — Release (Group) Type and Status](https://musicbrainz.org/doc/MusicBrainz_API#Release_.28Group.29_Type_and_Status), accessed 2026-11-04.
- [Data model v0](../data-model.md)
- [Scope](../../00-vision/scope.md)
