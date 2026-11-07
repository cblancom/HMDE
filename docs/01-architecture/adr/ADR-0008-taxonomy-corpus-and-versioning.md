# ADR-0008 — Album-level taxonomy, corpus lifecycle and period expansion

- **Status:** Accepted
- **Date:** 2026-11-06
- **Deciders:** Cristian, project architecture
- **Related:** [ADR-0004](ADR-0004-release-group-model.md), [ADR-0005](ADR-0005-identity-and-provenance.md), [ADR-0007](ADR-0007-credit-scope-and-recording-level-aggregation.md)

## Context

The original MVP scope used a 42-band corpus with albums released between 1980 and 2000. It also treated subgenre as a single artist-level attribute. Both assumptions become insufficient when the corpus is extended to 1960–2026 and grows beyond the initial sample.

A band can publish albums in different subgenres over its career. Classifying only the artist would either lose that information or force an incorrect single label. In addition, adding bands and genres must not delete historical data or make previous analyses irreproducible.

The corpus needs a manually curated taxonomy, album-level classification, a derived band-level aggregate and explicit versioning for datasets, taxonomies and analyses.

## Decision

1. **Analysis period:** the working corpus scope becomes 1960-01-01 to 2026-12-31. The existing E2 and E3 1980–2000 datasets remain historical artifacts; they are not rewritten.

2. **Corpus growth:** the initial 42 bands remain active. New bands are appended through versioned seed-list batches. A band removed from the active corpus is marked `retired`, not deleted. Retired bands disappear from default listing and search but remain accessible by direct URL and remain in historical datasets and analyses.

3. **Single taxonomy source:** the taxonomy is defined manually in `data/taxonomy.json` and is versioned. No automatic hierarchy is inferred from MusicBrainz tags. Parent/child relationships are curated.

4. **Only leaves are assignable:** an album may receive a subgenre primary or secondary label only from a taxonomy leaf (a node with no children). Parent nodes are families used for grouping, filtering and presentation; they cannot be used as album labels.

5. **Album classification:** each canonical album has exactly one primary leaf and zero or more secondary leaves. Secondary labels are not alternatives to the primary; they add information and must also be leaves.

6. **Band aggregate:** the band-level primary subgenre is derived from its album primary labels over the active analysis period. Ties and exceptions are resolved by an audited manual classification. The filter `subgenre=...` matches the band aggregate primary.

7. **Hierarchical filtering:** filtering by a parent node includes descendant leaves by default. An explicit `include_descendants=false` option may be used for exact matching.

8. **Confidence:** album mappings and band aggregates carry a confidence score and a review status.
   - Low: `< 0.50`; manual review required.
   - Medium: `0.50–0.79`; alert and review queue, non-blocking.
   - High: `>= 0.80`; accepted automatically.
   - Manual classifications have confidence `1.0` and an audit trail.

9. **Versioned history:** ingestion runs, raw responses, extracted datasets, normalized membership and analyses are versioned. Analyses must reference the dataset version and taxonomy version used. A taxonomy change creates a new taxonomy version and does not silently rewrite previous analyses.

10. **No destructive updates:** replacing a band or changing a taxonomy node is carried out through a new seed-list/taxonomy/dataset version. Historical rows and datasets remain available.

## Consequences

**Positive:**

- Album-level genres preserve real stylistic differences across a band's career.
- Parent categories support useful roll-ups without forcing every album into a broad label.
- Manual taxonomy and manual tie-breaking keep the classification auditable.
- Retired bands remain available for historical analysis.
- Dataset and taxonomy versions make analyses reproducible.

**Negative:**

- The taxonomy requires ongoing manual curation.
- Album and band classifications need confidence handling and review queues.
- The period expansion increases ingestion volume and the age range of source data.
- E4 needs additional tables for album labels, membership and versioning.

**Mitigations:**

- Keep the taxonomy initially small and extend it by versions.
- Review only low-confidence cases manually; medium cases generate alerts.
- Reuse cached raw responses when rebuilding datasets.
- Keep historical 1980–2000 datasets untouched.

## Alternatives considered

| Alternative | Reason for rejection |
|---|---|
| Keep classification at artist level only | Loses legitimate album-level genre differences. |
| Use a flat taxonomy | Cannot express families or reliable roll-ups across a 1960–2026 corpus. |
| Infer hierarchy automatically from tags | Too noisy and not auditable; the hierarchy is a product decision. |
| Allow parent nodes as album labels | Makes filters and aggregates ambiguous. |
| Delete retired bands | Destroys historical analyses and provenance. |
| Overwrite canonical rows on each run | Makes previous analyses irreproducible. |
| Review every classification manually | Does not scale; confidence thresholds and queues are required. |

## References

- [Scope](../../00-vision/scope.md)
- [Data model v0](../data-model.md)
- [Taxonomy draft](../../../data/taxonomy.json)
- [Seed list](../../03-data/seed-list.md)
- [Roadmap](../../00-vision/roadmap.md)
