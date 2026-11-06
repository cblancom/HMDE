# MusicBrainz feasibility spike report

- **Status:** Completed v0.1
- **Date:** 2026-11-05
- **Stage:** E0
- **Sample:** 28 bands, 206 album candidates, 1980–2000
- **Raw evidence:** `spike/output/spike_results.json`, `spike/output/spike_report.md`
- **Script:** `spike/spike_musicbrainz.py`

## 1. Executive summary

MusicBrainz is viable as the primary source for the MVP:

- **86.4%** of album candidates have at least one producer/co-producer credit.
- Excluding six low-confidence release-groups, coverage is **89.0%**.
- **80.1%** have a studio/place credit.
- **83.0%** have at least one extended production credit (engineer, mix or mastering).
- **100%** of sampled bands have a Wikidata QID.
- **100%** of album candidates have at least year-level date precision.

The most important finding is that **producer credits are frequently attached to recordings, not releases**. Only 73 of 206 albums (35.4%) have a release-level producer credit; 105 albums (51.0% of all, 59.0% of the 178 covered albums) have a producer credit only at recording level. A release-only model would therefore miss most of the available production data.

The spike supports proceeding with E0, but the data model and ADRs must be amended before implementation.

## 2. Method

### Sample

The sample is deliberately stratified, not random:

- 4 bands from each of 7 subgenres: Heavy, Thrash, Death, Black, Power, Doom and Progressive Metal.
- 28 bands total.
- 7 countries: GB, US, BR, SE, NO, DE and FI.
- Studio albums with first release between 1980 and 2000.
- Includes difficult cases: long discographies, lineup changes, aliases, many editions, live/compilation releases and short names.

The sample is defined in `spike/sample.json`.

### Collection

For each band, the script:

1. Searches the artist by name and selects the best exact/group match.
2. Fetches the artist's Wikidata QID from MusicBrainz URL relationships.
3. Browses all release-groups of primary type `album` with genres, tags and relationships.
4. Filters to release-groups with no secondary type and first release in 1980–2000.
5. Fetches all releases of each release-group, with artist and place relationships.
6. If no release-level producer is found, inspects recording-level relationships on the earliest official release.
7. Maps producer attributes:
   - `co` → co-producer
   - `executive` → executive producer
   - `assistant` → assistant producer
   - `additional` → additional producer
8. Records date precision, release counts, low-confidence release-groups and coverage metrics.

The client respects MusicBrainz's **one request per second** limit, uses an identifiable User-Agent, and caches raw responses.

### Low-confidence heuristic

A release-group is flagged as low-confidence when it has two or fewer releases and/or a title suggesting a demo, single, live, split or compilation. These candidates are included in the main metrics and listed separately for review.

## 3. Results

### Overall coverage

| Metric | Count | Coverage |
|---|---:|---:|
| Album candidates | 206 | — |
| Producer/co-producer | 178 | 86.4% |
| Producer/co-producer, excluding low-confidence | 178 | 89.0% |
| Co-producer | 20 | 9.7% |
| Executive producer | 21 | 10.2% |
| Engineer | 131 | 63.6% |
| Mix | 113 | 54.9% |
| Mastering | 124 | 60.2% |
| Any extended credit | 171 | 83.0% |
| Studio/place | 165 | 80.1% |
| Bands with Wikidata QID | 28 | 100% |
| Date precision year or better | 206 | 100% |

Date precision distribution: 180 day, 11 month, 15 year, 0 unknown.

### Producer credit scope

| Scope | Albums | Share of all albums | Share of covered albums |
|---|---:|---:|---:|
| Release-level producer | 73 | 35.4% | 41.0% |
| Recording-level only | 105 | 51.0% | 59.0% |
| Any producer/co-producer | 178 | 86.4% | 100% |

### Coverage by subgenre

| Subgenre | Bands | Albums | Producer | Extended | Studio |
|---|---:|---:|---:|---:|---:|
| Heavy Metal | 4 | 43 | 97.7% | 88.4% | 81.4% |
| Thrash Metal | 4 | 32 | 93.8% | 84.4% | 81.2% |
| Death Metal | 4 | 25 | 88.0% | 96.0% | 88.0% |
| Black Metal | 4 | 24 | 58.3% | 37.5% | 54.2% |
| Power Metal | 4 | 30 | 93.3% | 93.3% | 93.3% |
| Doom Metal | 4 | 25 | 72.0% | 88.0% | 80.0% |
| Progressive Metal | 4 | 27 | 88.9% | 85.2% | 77.8% |

### Coverage by decade

| Period | Albums | Producer | Extended | Studio |
|---|---:|---:|---:|---:|
| 1980s | 65 | 93.8% | 86.2% | 87.7% |
| 1990–2000 | 141 | 83.0% | 81.6% | 76.6% |

### Low-confidence release-groups

| Band | Album | Date | Releases | Reason |
|---|---|---|---:|---|
| Black Sabbath | Come To The Sabbath | 1990 | 1 | Two or fewer releases |
| Morbid Angel | Harmony Dies, Vol. 1 | 1994 | 1 | Two or fewer releases; title suggests non-studio |
| Mayhem | From the Darkest Past | 1992 | 2 | Two or fewer releases |
| Emperor | Thorns vs. Emperor | 1999 | 4 | Title suggests split |
| Queensrÿche | The Demos | 1990 | 1 | Two or fewer releases; title suggests demo |
| Queensrÿche | Nightryder | 1990 | 1 | Two or fewer releases |

All six lack a producer credit, so excluding them raises producer coverage from 86.4% to 89.0%.

### Data collection cost

| Metric | Value |
|---|---:|
| Network requests (initial full fetch) | 409 |
| Elapsed time (initial full fetch) | 859.5 s |
| Raw cache files | 445 |
| Raw cache size | 27 MB |
| Distinct producers found | 134 |
| Distinct studios found | 205 |

At the same depth, 500 bands would require roughly 7,300 requests, or about 2.2 hours at one request per second, before retries. This is feasible for batch ingestion but reinforces the need for caching, idempotency and possibly data dumps at larger scale.

## 4. Key findings

1. **MusicBrainz is viable as the primary source.** Producer coverage is well above the provisional 60% threshold.
2. **Recording-level credits are essential.** A release-only model would miss 105 of the 178 producer-covered albums (59%). The credit model must support recording scope and aggregation to the canonical album.
3. **Co-producer and executive producer are attributes, not relationship types.** MusicBrainz stores them as `producer` relationships with attributes `co` and `executive`. The role mapping must handle these attributes explicitly.
4. **Coverage is uneven across subgenres.** Heavy, Thrash, Death and Power Metal have high producer coverage; Black Metal is much lower (58.3% producer, 37.5% extended). Cross-subgenre comparisons must report coverage and may need weighting or caveats.
5. **Some release-groups typed as albums are not studio albums.** Six candidates were flagged by low release count or suspicious titles. The ingestion pipeline needs validation and a review queue for these cases.
6. **Studio coverage is sufficient for the MVP.** 80.1% of albums have at least one studio/place relationship, so studios can be an analytical axis.
7. **Wikidata and date precision are strong in this sample.** All sampled bands have a QID and all album candidates have at least year precision.
8. **API-only ingestion is feasible but slow.** The spike took about 14 minutes for 28 bands. Batch caching and idempotency are mandatory; data dumps should be evaluated for the 200–500 band phase.

## 5. Implications for design

### Credit model

- Add `credit_scope` with values `release_group`, `release` and `recording`.
- Add optional `recording_id` and preserve `release_id` / `release_group_id` as context.
- Treat album-level credits as an aggregation, not a fact: preserve the underlying scope, source and supporting recordings.
- Record `aggregation_basis` and `supporting_recording_count` so analyses can distinguish full-album from partial credits.
- See [ADR-0007](../01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md).

### Role mapping

- `producer` → producer.
- `producer` + `co` → co-producer.
- `producer` + `executive` → executive producer.
- `producer` + `assistant` → assistant producer.
- `producer` + `additional` → additional producer.
- Keep the raw role and attributes for traceability.

### Ingestion

- Fetch release-level and recording-level relationships.
- Use one representative release for recording-level inspection only when release-level credits are missing; this is conservative and should be extended in production.
- Cache raw responses and enforce one request per second.
- Record release-group secondary types when available and apply low-confidence checks.

### Quality and analysis

- Report coverage by subgenre and decade.
- Quarantine or review low-confidence release-groups.
- Do not compare subgenres without stating coverage differences.
- Consider requiring a minimum share of recordings for a recording-level credit to be treated as a full-album credit.

## 6. Decision

Proceed with MusicBrainz as the primary source for the MVP.

[ADR-0004](../01-architecture/adr/ADR-0004-release-group-model.md) has been amended and [ADR-0007](../01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md) has been accepted. The scope and conceptual data model now include recording-level credit scope.

E0 is complete: the final 42-band seed list is available at `data/seed-list.json` and documented in `docs/03-data/seed-list.md`.

Next steps:

1. Commit and push the repository, then verify the remote CI run and mark SPEC-001 Validated.
2. Write and approve SPEC-002 — Seed band explorer using a subset of the seed list.
3. Implement E2.

## 7. Limitations

- The sample is stratified but not statistically representative of the whole scene.
- It over-represents canonical, well-documented bands.
- Recording-level credits are inspected only on the earliest official release when no release-level producer is found; later editions may add credits.
- Low-confidence detection is heuristic, not a definitive studio-album classifier.
- Wikipedia, Discogs and Metallum are not included.
- MusicBrainz data changes over time; this report reflects the 2026-11-05 snapshot.
- Co-producer and executive producer counts depend on attribute mapping; other attribute vocabularies may exist.

## 8. Reproducibility

- Sample: `spike/sample.json`
- Script: `spike/spike_musicbrainz.py`
- Raw responses: `spike/output/raw/`
- Structured results: `spike/output/spike_results.json`
- Generated report: `spike/output/spike_report.md`
- Collection metadata: `spike/output/collection_metadata.json`

Run the full spike with:

```
python3 spike/spike_musicbrainz.py
```

The raw cache is disposable and should not be committed to the main repository. See `spike/README.md` for details.

## 9. Next steps

1. Commit and push the repository, then verify the remote CI run and mark SPEC-001 Validated.
2. Write and approve SPEC-002 — Seed band explorer.
3. Implement E2.
