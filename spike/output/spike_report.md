# MusicBrainz feasibility spike

- **Date:** 2026-11-05
- **Sample size:** 28 bands
- **Initial full fetch:** 409 network requests, 859.5 seconds (2026-11-05)
- **This analysis run:** 0 network requests, 433 cache hits, 0.2 seconds

## Coverage summary

| Metric | Count | Coverage |
|---|---:|---:|
| Albums in period | 206 | — |
| Albums with producer/co-producer | 178 | 86.4% |
| Producer/co-producer, excluding low-confidence albums | 178 | 89.0% |
| Albums with co-producer | 20 | 9.7% |
| Albums with executive producer | 21 | 10.2% |
| Albums with engineer | 131 | 63.6% |
| Albums with mix | 113 | 54.9% |
| Albums with mastering | 124 | 60.2% |
| Albums with any extended credit | 171 | 83.0% |
| Albums with studio/place | 165 | 80.1% |
| Bands with Wikidata QID | 28 | 100.0% |

## Per-band results

| Band | Subgenre | Albums | Producer/co-producer | Extended credit | Studio | QID |
|---|---|---:|---:|---:|---:|---|
| Iron Maiden | Heavy Metal | 12 | 12 | 10 | 8 | Q42482 |
| Judas Priest | Heavy Metal | 8 | 8 | 7 | 7 | Q83468 |
| Motörhead | Heavy Metal | 12 | 12 | 11 | 10 | Q19697 |
| Black Sabbath | Heavy Metal | 11 | 10 | 10 | 10 | Q47670 |
| Metallica | Thrash Metal | 7 | 7 | 7 | 7 | Q15920 |
| Slayer | Thrash Metal | 8 | 8 | 6 | 6 | Q131231 |
| Megadeth | Thrash Metal | 9 | 9 | 9 | 9 | Q83431 |
| Sepultura | Thrash Metal | 8 | 6 | 5 | 4 | Q239074 |
| Death | Death Metal | 7 | 7 | 7 | 6 | Q192843 |
| Cannibal Corpse | Death Metal | 7 | 6 | 7 | 7 | Q485231 |
| Morbid Angel | Death Metal | 7 | 5 | 6 | 5 | Q309001 |
| At the Gates | Death Metal | 4 | 4 | 4 | 4 | Q540368 |
| Bathory | Black Metal | 9 | 6 | 2 | 4 | Q157201 |
| Mayhem | Black Metal | 3 | 1 | 2 | 2 | Q485116 |
| Emperor | Black Metal | 4 | 2 | 2 | 2 | Q264029 |
| Darkthrone | Black Metal | 8 | 5 | 3 | 5 | Q160119 |
| Helloween | Power Metal | 10 | 9 | 10 | 10 | Q158895 |
| Blind Guardian | Power Metal | 6 | 6 | 5 | 6 | Q152540 |
| Stratovarius | Power Metal | 8 | 8 | 8 | 8 | Q201207 |
| Gamma Ray | Power Metal | 6 | 5 | 5 | 4 | Q154129 |
| Candlemass | Doom Metal | 7 | 7 | 7 | 7 | Q840197 |
| Paradise Lost | Doom Metal | 7 | 6 | 7 | 6 | Q750593 |
| My Dying Bride | Doom Metal | 6 | 3 | 5 | 5 | Q498460 |
| Cathedral | Doom Metal | 5 | 2 | 3 | 2 | Q1050878 |
| Dream Theater | Progressive Metal | 5 | 5 | 5 | 4 | Q162586 |
| Fates Warning | Progressive Metal | 9 | 9 | 9 | 9 | Q754323 |
| Queensrÿche | Progressive Metal | 9 | 6 | 5 | 6 | Q462380 |
| Opeth | Progressive Metal | 4 | 4 | 4 | 2 | Q18557 |

## Low-confidence release-groups

These release-groups are typed as albums in MusicBrainz but have two or fewer releases and/or a title suggesting a demo, single, live, split or compilation. They are included in the main metrics but should be reviewed before ingestion.

| Band | Album | Date | Releases | Reason |
|---|---|---|---:|---|
| Black Sabbath | Come To The Sabbath | 1990 | 1 | two or fewer releases |
| Morbid Angel | Harmony Dies, Vol. 1 | 1994 | 1 | two or fewer releases; title suggests non-studio release |
| Mayhem | From the Darkest Past | 1992 | 2 | two or fewer releases |
| Emperor | Thorns vs. Emperor | 1999 | 4 | title suggests non-studio release |
| Queensrÿche | The Demos | 1990 | 1 | two or fewer releases; title suggests non-studio release |
| Queensrÿche | Nightryder | 1990 | 1 | two or fewer releases |

## Relation type frequencies

| Relation type | Count |
|---|---:|
| instrument | 642 |
| photography | 307 |
| vocal | 279 |
| producer | 273 |
| engineer | 252 |
| mastering | 198 |
| mix | 183 |
| liner notes | 176 |
| design | 93 |
| design/illustration | 67 |
| graphic design | 67 |
| illustration | 62 |
| artwork | 60 |
| misc | 57 |
| art direction | 54 |
| recording | 53 |
| arranger | 33 |
| co-producer | 31 |
| executive producer | 23 |
| artists and repertoire | 17 |
| editor | 15 |
| booking | 12 |
| legal representation | 12 |
| composer | 10 |
| phonographic copyright | 10 |
| additional producer | 7 |
| lyricist | 7 |
| remixer | 6 |
| instrument arranger | 6 |
| copyright | 6 |
| creative direction | 6 |
| lacquer cut | 6 |
| transfer | 6 |
| programming | 6 |
| dedicated to | 5 |
| assistant producer | 5 |
| compiler | 4 |
| performer | 4 |
| sound | 4 |
| conductor | 4 |
| production coordinator | 2 |
| named after release group | 2 |
| booklet editor | 2 |
| instrument technician | 2 |
| audio | 2 |
| publishing | 1 |
| orchestrator | 1 |
| performing orchestra | 1 |
| vocal arranger | 1 |
| samples from artist | 1 |

## Data quality observations

- Albums with truncated release sampling: 0
- Albums that needed recording-level credit inspection: 133
- Albums whose producer credit exists only at recording level: 105
- Low-confidence albums (two or fewer releases and/or suspicious title): 6
- Distinct producers found: 134
- Distinct studios found: 205
- Date precision distribution: {'day': 180, 'month': 11, 'year': 15}
- Bands not found: 0

## Preliminary interpretation

MusicBrainz looks viable as the primary source for the MVP.

Recording-level credits are inspected only for the earliest official release when no release-level producer is found; later editions may add credits. Coverage is therefore conservative.

MusicBrainz stores co-producer and executive producer as attributes on the producer relationship (`co`, `executive`), not as separate relationship types; the spike maps those attributes explicitly.

These thresholds are working hypotheses from `docs/03-data/sources.md`; the sample is stratified but not statistically representative of the entire scene.
