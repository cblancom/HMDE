# ADR-0002 — MusicBrainz as primary source

- **Status:** Accepted
- **Date:** 2026-11-04
- **Deciders:** Cristian, project architecture

## Context

The project needs stable identifiers, music entities, albums, editions and production relationships. Candidate sources have very different coverage, licenses and access terms. The primary source must allow the project to build a traceable and reproducible database without relying on fragile scraping.

## Decision

1. **MusicBrainz is the primary source** for artists, release-groups, releases, relationships and credits.
2. **MBID is the canonical key** for MusicBrainz-derived entities.
3. **Wikidata** is used as a complementary source for external identifiers and links between entities.
4. **Wikipedia** remains a future complementary source, only if MusicBrainz coverage is insufficient, using its API and respecting CC BY-SA.
5. **Discogs is deferred** and is not part of the MVP.
6. **Encyclopaedia Metallum is excluded** until its terms are reviewed and, if applicable, explicit permission is obtained.

The full evaluation is in [03-data/sources.md](../../03-data/sources.md).

## Rationale

- MusicBrainz offers an explicit relational model, stable MBIDs and typed relationships between artists, releases, release-groups and places.
- Its API allows a bounded subset without downloading the full database.
- The core data license is CC0, which facilitates reuse; attribution is maintained for transparency and traceability even though it is not an obligation of that license.
- Discogs has valuable data, but its API terms restrict caching and the age of displayed data, which conflicts with a historical snapshot.
- Metallum does not publish an official API, and automated access is not clearly authorized.

## Consequences

**Positive:**

- Model and traceability aligned with the source.
- Lower legal risk than scraping.
- Ingestions can be reproduced and snapshots preserved.

**Negative:**

- Production credit coverage may be uneven.
- The one-request-per-second limit makes ingestion slow.
- Genre tags are noisy and do not equal an objective taxonomy.
- Data may change over time; versioning is required.

**Mitigations:**

- Coverage spike in E0 before committing to scope.
- Coverage measurement per album, decade and subgenre in E5.
- Preservation of raw data and retrieval dates.
- Use of credit confidence and status.
- Plan to complement with Wikipedia only if the data justifies it.

## MusicBrainz operational constraints

- Maximum one request per second.
- Meaningful, identifiable User-Agent.
- Free non-commercial use; commercial use requires contacting MetaBrainz.
- Core data CC0; supplementary data CC BY-NC-SA 3.0.
- Entity-link limits and pagination in the API.

## Alternatives considered

| Alternative | Reason for rejection |
|---|---|
| Discogs as primary source | Cache restrictions, restricted data and API limits |
| Metallum as primary source | No official API and unverified access terms |
| Wikipedia as primary source | Unstructured text, fragile extraction and share-alike license |
| Wikidata as primary source | Excellent for IDs, but insufficient credit coverage |

## Validation

The E0 spike (28 bands, 206 album candidates) found 86.4% producer/co-producer coverage, 80.1% studio coverage and 100% Wikidata QID coverage. The result validates MusicBrainz as the primary source for the MVP, subject to the coverage limitations documented in the [spike report](../../03-data/spike-report.md).

## References

- [MusicBrainz API](https://musicbrainz.org/doc/MusicBrainz_API), accessed 2026-11-04.
- [MusicBrainz Data License](https://musicbrainz.org/doc/About/Data_License), accessed 2026-11-04.
- [Wikidata Licensing](https://www.wikidata.org/wiki/Wikidata:Licensing), accessed 2026-11-04.
- [Discogs API Terms of Use](https://support.discogs.com/hc/articles/360009334593-API-Terms-of-Use), accessed 2026-11-04.
- [Source evaluation](../../03-data/sources.md)
