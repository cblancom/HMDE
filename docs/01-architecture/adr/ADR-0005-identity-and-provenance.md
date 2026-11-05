# ADR-0005 — Deterministic identity and mandatory provenance

- **Status:** Accepted
- **Date:** 2026-11-04
- **Deciders:** Cristian, project architecture

## Context

Music sources contain duplicates, aliases, errors and name variations. An incorrect merge of two artists or albums contaminates every subsequent analysis and is difficult to undo. At the same time, the absence of a credit does not prove that a person did not participate.

The project needs a conservative identity policy and full traceability for every data point.

## Decision

1. **MBID is the canonical key** for MusicBrainz-derived entities.
2. **External identifiers** (QID, Discogs ID, ISNI, etc.) are stored in a separate table and are not assumed equivalent without verification.
3. **Deduplication is deterministic**: MBID, QID or another exact identifier.
4. **No automatic fuzzy matching** in the MVP. Ambiguous matches go to quarantine or manual review.
5. Every merge leaves an **audit record**: absorbed entity, resulting entity, reason, source and date.
6. Every credit has **mandatory provenance**: source, URL, date, hash, license and ingestion run.
7. Every credit has **explicit status and confidence**: confirmed, inferred, conflicting or quarantined.
8. The **absence of a credit does not create a negative record**. It is reported as missing coverage, not as "did not participate".
9. Conflicting data is preserved; it is never silently overwritten.

## Consequences

**Positive:**

- Auditable and reproducible results.
- Less risk of contaminating the network with incorrect merges.
- Data can be reprocessed without calling the source again.
- The UI can honestly show what is known and what is not.

**Negative:**

- More manual work in ambiguous cases.
- The model has more tables and fields.
- Some duplicates remain visible until reviewed.
- Analyses must account for coverage and confidence.

**Mitigations:**

- Prioritize seed-list coverage.
- Measure the quarantine rate in E5.
- Document mapping rules.
- Automate only exact matches.

## Alternatives considered

| Alternative | Reason for rejection |
|---|---|
| Automatic merging by name similarity | High risk of false positives |
| Use only the name as key | Inevitable duplicates and collisions |
| Discard conflicting data | Loses information and traceability |
| Model absence as a negative credit | Incorrect interpretation |

## References

- [Data model v0](../data-model.md)
- [Source evaluation](../../03-data/sources.md)
- [Scope](../../00-vision/scope.md)
