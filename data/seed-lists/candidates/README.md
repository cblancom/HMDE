# Candidate pool v0.3.0

- **Status:** Verified; report and batches approved; the pool is not an active seed list
- **Version:** `0.3.0-candidates-02`
- **File:** [`v0.3.0-pool.json`](v0.3.0-pool.json)
- **By country:** [`v0.3.0-by-country.md`](v0.3.0-by-country.md) — human-readable country index with band and proposed genre
- **Generated:** 2026-11-17
- **Target:** 510-band ceiling; 509 verified active bands (57 current + 452 accepted candidates)
- **Verification report:** [`v0.3.0-verification.json`](v0.3.0-verification.json)
- **Spec:** [`specs/016-corpus-expansion/spec.md`](../../../specs/016-corpus-expansion/spec.md)

This directory holds the verified candidate bands for the E13 corpus expansion. All 453 candidates were checked; 452 are accepted and Hellhammer is excluded because it has no studio album. The active pointer now resolves `seed-lists/v0.3.0.json`. The E3 canonical dataset `mb-20261119T004940Z-9d5e75fdc1b9` contains 509 bands, has no duplicate entity MBIDs and reports 7 multi-artist release-group exclusions. E4 normalization is next.

## Contents

The pool contains 453 unique MusicBrainz artists that are not in the v0.2.0 seed list. It covers all 17 assignable taxonomy leaves and six regions. The owner accepted all 453 candidates on 2026-11-17 and approved the verification report, the Hellhammer exclusion and the three batches of 151/151/150. There is no 143-band selection.

On 2026-11-17 the owner reviewed the by-country index and contributed 64 entries. 56 were added; 5 were discarded because they are already active in v0.2.0 (`Accept`, `Entombed`, `Gamma Ray`, `Gojira`, `Helloween`) and 3 because they were already in the pool (`Artillery`, `Dismember`, `Holy Moses`).

| Region | Candidates |
|---|---:|
| Europe (excluding Iberia) | 238 |
| North America | 124 |
| Latin America | 47 |
| Japan | 13 |
| Iberia | 18 |
| Oceania | 13 |
| **Total** | **453** |

`Iberia` covers Spain and Portugal; `Latin America` covers the Americas south of the United States.

| Leaf | Candidates |
|---|---:|
| `black-metal` | 41 |
| `death-metal` | 57 |
| `deathcore` | 10 |
| `djent` | 10 |
| `doom-metal` | 25 |
| `groove-metal` | 14 |
| `hard-rock` | 33 |
| `heavy-metal` | 32 |
| `metalcore` | 15 |
| `nwobhm` | 20 |
| `post-metal` | 13 |
| `power-metal` | 41 |
| `progressive-metal` | 22 |
| `proto-metal` | 20 |
| `sludge-metal` | 15 |
| `stoner-metal` | 28 |
| `thrash-metal` | 57 |

The tables describe the 453-candidate pool. Accepted counts exclude Hellhammer, so `black-metal` drops from 41 to 40 and Europe from 238 to 237.

Matching status after T-002:

- 448 `verified`: the artist name, MBID and country were confirmed against MusicBrainz.
- 5 `verified_country_inferred`: the MBID and artist were confirmed, but the country required a documented inference.

## Batches

The 452 accepted candidates are written to `data/seed-lists/batches/v0.3.0-batch-01.json`, `-02` and `-03`, with 151/151/150 bands. Hellhammer and its exclusion reason are recorded in `data/seed-lists/candidates/v0.3.0-verification.json`. The owner approved the batches on 2026-11-17.

## Fields

| Field | Meaning |
|---|---|
| `candidate_id` | Stable identifier within this pool. |
| `name` | MusicBrainz artist name. |
| `display_name` | Name to use in the seed list when the MusicBrainz name is not the preferred display form. |
| `mbid` | MusicBrainz artist MBID. |
| `country` | Two-letter country code used for the seed list. |
| `country_check` | `verified` or `documented_inference`; added by T-002. |
| `expected_country` | Country expected by the search frame. |
| `heritage_country` | Optional country of origin or members when the band is based elsewhere. It does not replace `country`. |
| `region` | Selection region: Europe, Iberia, Latin America, Japan, North America or Oceania. |
| `proposed_leaf` | Proposed assignable taxonomy leaf. |
| `secondary_leaves` | Other plausible leaves; not used for seed-list membership. |
| `active_from` | First active year when available. |
| `musicbrainz_score` | Search score from the candidate query. |
| `musicbrainz_tags` | Tags returned by MusicBrainz. |
| `match_status` | `verified` or `verified_country_inferred`. |
| `album_check` | Studio-album verification state: `verified` or `rejected`. |
| `studio_album_count` | Number of eligible studio albums released 1960–2026. |
| `earliest_album` | Earliest eligible studio-album release date. |
| `latest_album` | Latest eligible studio-album release date. |
| `relevance_status` | Published-source verification state: `verified` or `rejected`. |
| `wikidata_qid` | Wikidata QID when available. |
| `wikidata_url` | Wikidata URL when available. |
| `wikidata_sitelinks` | Sitelink count when available. |
| `wikipedia_url` | Wikipedia article used as relevance evidence, if any; added by T-002. |
| `relevance_source` | Published source or sources used for relevance; added by T-002. |
| `verified_at` | Verification date; added by T-002. |
| `verification_notes` | Evidence, exclusions or edge-case notes; added by T-002. |
| `source_url` | MusicBrainz artist URL. |
| `notes` | Short evidence or disambiguation note. |

`country_check`, `album_check` and `relevance_status` must be `verified` (or `documented_inference` for country) before a candidate can enter a batch. A candidate with any `rejected` state is excluded and reported.

## Enrichment status

T-002 completed enrichment through MusicBrainz URL relationships and release-group browse. WDQS was not used because it returned `HTTP Error 429: Aggressively rate-limiting to 1 req / min`.

- 430 candidates have a Wikidata QID.
- 14 have a Wikipedia URL.
- 19 use Discogs and 4 use AllMusic as published relevance sources.
- Every candidate has a published source and an album verdict.

## Validation

```bash
python3 - <<'PY'
import json
from collections import Counter
from pathlib import Path

pool = json.loads(Path('data/seed-lists/candidates/v0.3.0-pool.json').read_text())
report = json.loads(Path('data/seed-lists/candidates/v0.3.0-verification.json').read_text())
bands = pool['bands']
mbids = {band['mbid'] for band in bands}

assert pool['version'] == '0.3.0-candidates-02'
assert pool['target_active_bands'] == 510
assert pool['verified_active_bands'] == 509
assert pool['taxonomy_version'] == '0.2.0'
assert pool['pool_size'] == 453
assert len(bands) == pool['pool_size']
assert len(mbids) == pool['pool_size']
assert all(band['proposed_leaf'] in pool['leaf_counts'] for band in bands)
assert sum(pool['leaf_counts'].values()) == pool['pool_size']
assert sum(pool['region_counts'].values()) == pool['pool_size']
assert Counter(band['match_status'] for band in bands) == {
    'verified': 448,
    'verified_country_inferred': 5,
}
assert pool['album_check_counts'] == {'verified': 452, 'rejected': 1}
assert pool['relevance_status_counts'] == {'verified': 453}
assert report['accepted_count'] == 452
assert report['excluded_count'] == 1
assert report['final_active_bands'] == 509
print('candidate pool valid')
PY
```

## Do not

- Do not point `data/seed-list.json` at this file.
- Do not copy the pool into a seed list without excluding failed candidates.
- Do not treat a MusicBrainz search result as proof of relevance.
- Do not guess a country, leaf or album.
- Do not edit the historical seed lists.
