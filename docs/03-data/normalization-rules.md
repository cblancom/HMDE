# Normalization rules

- **Status:** Active
- **Version:** 0.1.0
- **Date:** 2026-11-08
- **Stage:** E4
- **Spec:** [SPEC-005](../../specs/005-normalization-identity/spec.md)
- **Plan:** [SPEC-005 plan](../../specs/005-normalization-identity/plan.md)
- **Input dataset:** `data/ingestions/musicbrainz/mb-20261107T194927Z-0d6cedd5c261`
- **Taxonomy:** [`data/taxonomy.json`](../../data/taxonomy.json) v0.2.0

## 1. Purpose

This document defines the rules used to normalize the validated E3 v0.2 dataset into canonical PostgreSQL entities. It covers identity, provenance, credits, taxonomy, album classification, band aggregates, membership, review and missing data.

Normalization is a batch process. It does not call MusicBrainz, edit raw responses, change the public API contract or build a review UI.

## 2. Identity and provenance

- MBID is the only automatic identity key.
- Existing canonical rows are reused by MBID.
- New rows use deterministic UUID5 identifiers with a fixed HMDE namespace.
- No fuzzy, name-only or probabilistic merging is allowed.
- Every normalized row references a `source_record` derived from an E3 `raw_response`.
- A canonical row without provenance is invalid.
- Conflicts and malformed identifiers go to the review/quarantine queue.
- E2 fixture rows and provenance remain readable; unrelated rows are not deleted.

## 3. Canonical entities

- Artists, release groups, releases and recordings are loaded from the E3 NDJSON files.
- Release–recording links preserve disc, position and track number.
- External identifiers are stored separately and do not imply identity beyond an exact identifier.
- A canonical album follows ADR-0004: primary type `album`, no secondary type and a date inside the declared period.

## 4. Credits

- Credits preserve their original scope: `release_group`, `release` or `recording`.
- Credited artists that are not seed bands are created as minimal canonical artist stubs by MBID, with name, `type = other` and provenance from the credit response.
- Recording-scope credits are expanded to every canonical release group where the recording appears.
- A recording credit that cannot be linked to an album context is quarantined.
- Role and attribute mapping follows ADR-0007:

| Source role | Source attribute | Normalized role |
|---|---|---|
| `producer` | none | `producer` |
| `producer` | `co` | `co-producer` |
| `producer` | `executive` | `executive-producer` |
| `producer` | `assistant` | `assistant-producer` |
| `producer` | `additional` | `additional-producer` |
| `engineer` | any | `engineer` |
| `mix` | any | `mix` |
| `mastering` | any | `mastering` |

Unmapped attributes stay in the credit attributes and may create a review issue. They are never silently discarded.

## 5. Taxonomy

- Only taxonomy version 0.2.0 is valid for this corpus version.
- Only assignable leaves may classify albums or bands.
- Parent nodes are grouping/filter nodes and cannot be labels.
- Taxonomy versions are immutable once used by a completed normalization run.
- The current `subgenre` projection is synchronized from the active taxonomy version.
- A taxonomy change requires a new taxonomy version and a new classification run.

## 6. Classification inputs

### 6.1 Tag map

[`data/classifications/tag-map-v0.1.0.json`](../../data/classifications/tag-map-v0.1.0.json) maps exact normalized MusicBrainz genre/tag labels to leaves.

Each rule has:

- `source_label`: exact casefolded source label;
- `target_code`: assignable taxonomy leaf;
- `confidence`: score in `[0, 1]`;
- `priority`: lower values win ties after confidence;
- `mapping_rule`: provenance of the rule, currently `exact-label`.

The priority order is a deliberate specificity order: modern/extreme leaves (`deathcore`, `metalcore`, `djent`),
then `post-metal`, sludge, stoner, groove, thrash, black, death, doom, power and progressive; `nwobhm`,
`heavy-metal` and `hard-rock` are fallback families. This prevents broad tags from competing with more
specific leaves. The order is data, not inferred from MusicBrainz.

No substring, fuzzy or generated matching is allowed.

### 6.2 Manual overrides

[`data/classifications/manual-overrides-v0.1.0.json`](../../data/classifications/manual-overrides-v0.1.0.json) contains manual album classifications for problematic cases.

Each override records:

- release-group MBID;
- primary leaf;
- zero or more secondary leaves;
- confidence `1.0`;
- reason;
- reviewer;
- reviewed date.

Manual overrides always take precedence over mapped candidates and are recorded in the normalization report/issue audit.

## 7. Album classification scoring

1. Collect exact matching labels from release-group `genres` and `tags`.
2. For each leaf, keep the maximum confidence from matching rules.
3. Rank leaves by confidence descending, priority ascending and code.
4. A unique top candidate with confidence `>= 0.80` is accepted.
5. A top candidate with confidence `0.50–0.79` is stored for review.
6. No candidate or a top score below `0.50` requires review/quarantine.
7. Equal top confidence and priority is a conflict requiring review.
8. Secondary leaves are other mapped leaves with confidence `>= 0.50`.
9. An album has one primary leaf and zero or more secondary leaves.
10. A manual override replaces the generated result.

Missing tags and missing mappings are reported as missing evidence, not as a negative genre claim.

## 8. Band aggregates

- Count album primary leaves over the active period.
- A unique plurality becomes the band primary leaf.
- On a tie, use the approved seed-list `seed_subgenre_code` when it is among the tied leaves.
- If the band has no classified albums, use the seed-list leaf as a fallback with confidence `0.50`.
- If the album plurality is below the review threshold, use the approved seed-list leaf and mark the aggregate for review.
- Tie/fallback cases create a review issue and remain visible in the report.
- The current `artist_subgenre` projection is rebuilt deterministically; versioned history is retained separately.

## 9. Dataset membership

- `dataset_membership` records dataset version, seed-list version, batch, lifecycle and replacement fields.
- Corpus v0.2 has 57 active bands: 42 from `v0.1.0` and 15 from `v0.2.0-batch-01`.
- Retiring a band never deletes canonical rows, credits, classifications or provenance.
- Historical E2/E3 artifacts remain readable.

## 10. Review, quarantine and missing data

Review and quarantine reasons include:

- missing or malformed MBID;
- missing provenance or raw response;
- invalid taxonomy leaf or parent used as a label;
- no exact tag/genre mapping;
- low or medium confidence;
- ambiguous primary candidate or tie;
- missing recording album context;
- invalid manual override.

Review actions record actor, timestamp, source file/version and before/after values. Missing data is never presented as negative evidence.

## 11. Feedback loop

If the tag map is insufficient, add exact labels and rerun. Do not edit taxonomy v0.2.0 in place. If a taxonomy change is required, create a new taxonomy version and classify against it in a new run.

Manual overrides should remain rare: use them for genuinely ambiguous albums, not to compensate for broad mapping errors that should be fixed in the tag map.
