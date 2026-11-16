# Candidate pool v0.3.0

- **Status:** Pre-selection; not approved for ingestion
- **Version:** `0.3.0-candidates-01`
- **File:** [`v0.3.0-pool.json`](v0.3.0-pool.json)
- **By country:** [`v0.3.0-by-country.md`](v0.3.0-by-country.md) — human-readable country index with band and proposed genre
- **Generated:** 2026-11-16
- **Target:** 200 active bands for seed list v0.3.0
- **Selection spec:** [`specs/016-corpus-expansion/spec.md`](../../../specs/016-corpus-expansion/spec.md)

This directory holds candidate bands for the E13 corpus expansion. A candidate is an input to review, not an approved seed-list entry. The active pointer remains on `seed-lists/v0.2.0.json` until the owner approves the selection and the v0.3.0 seed list validates.

## Contents

The pool contains 397 unique MusicBrainz artists that are not in the active v0.2.0 seed list. It covers all 17 assignable taxonomy leaves and six regions. The pool is intentionally over-complete and not balanced by itself: the target leaf and regional quotas in the spec determine the 143-band selection.

| Region | Candidates |
|---|---:|
| Europe (excluding Iberia) | 204 |
| North America | 124 |
| Latin America | 38 |
| Japan | 11 |
| Iberia | 10 |
| Oceania | 10 |
| **Total** | **397** |

`Iberia` covers Spain and Portugal; `Latin America` covers the Americas south of the United States.

| Leaf | Candidates |
|---|---:|
| `black-metal` | 37 |
| `death-metal` | 48 |
| `deathcore` | 10 |
| `djent` | 10 |
| `doom-metal` | 25 |
| `groove-metal` | 12 |
| `hard-rock` | 28 |
| `heavy-metal` | 20 |
| `metalcore` | 15 |
| `nwobhm` | 20 |
| `post-metal` | 13 |
| `power-metal` | 35 |
| `progressive-metal` | 20 |
| `proto-metal` | 20 |
| `sludge-metal` | 15 |
| `stoner-metal` | 28 |
| `thrash-metal` | 41 |

Matching status:

- 375 `verified`: the artist name, MBID and country were confirmed against MusicBrainz.
- 22 `verified_country_inferred`: the MBID and artist were confirmed, but the country required a documented inference. These need explicit confirmation before selection.

## Fields

| Field | Meaning |
|---|---|
| `candidate_id` | Stable identifier within this pool. |
| `name` | MusicBrainz artist name. |
| `display_name` | Name to use in the seed list when the MusicBrainz name is not the preferred display form. |
| `mbid` | MusicBrainz artist MBID. |
| `country` | Two-letter country code used for the seed list. |
| `expected_country` | Country expected by the search frame. |
| `heritage_country` | Optional country of origin or members when the band is based elsewhere. It does not replace `country`. |
| `region` | Selection region: Europe, Iberia, Latin America, Japan, North America or Oceania. |
| `proposed_leaf` | Proposed assignable taxonomy leaf. |
| `secondary_leaves` | Other plausible leaves; not used for seed-list membership. |
| `active_from` | First active year when available. |
| `musicbrainz_score` | Search score from the candidate query. |
| `musicbrainz_tags` | Tags returned by MusicBrainz. |
| `match_status` | `verified` or `verified_country_inferred`. |
| `album_check` | Studio-album verification state. Currently `pending`. |
| `relevance_status` | Published-source verification state. Currently `pending_manual_review`. |
| `wikidata_qid` | Wikidata QID when verified; currently `null`. |
| `wikidata_url` | Wikidata URL when verified; currently `null`. |
| `wikidata_sitelinks` | Sitelink count when available; currently `null`. |
| `source_url` | MusicBrainz artist URL. |
| `notes` | Short evidence or disambiguation note. |

`album_check` and `relevance_status` must be set to `verified` before a candidate can enter a batch. A candidate with `album_check: "rejected"` or `relevance_status: "rejected"` must not be selected.

## Enrichment status

Wikidata QID enrichment was deferred during pool generation. WDQS returned:

```text
HTTP Error 429: Aggressively rate-limiting to 1 req / min
```

No candidate currently has a verified Wikidata QID or sitelink count. T-002 must use MusicBrainz URL relationships first, then bounded Wikipedia API requests, and record the published source for each selected band.

## Validation

```bash
python3 - <<'PY'
import json
from collections import Counter
from pathlib import Path

pool = json.loads(Path('data/seed-lists/candidates/v0.3.0-pool.json').read_text())
bands = pool['bands']
mbids = {band['mbid'] for band in bands}

assert pool['version'] == '0.3.0-candidates-01'
assert pool['target_active_bands'] == 200
assert pool['taxonomy_version'] == '0.2.0'
assert 300 <= pool['pool_size'] <= 400
assert len(bands) == pool['pool_size']
assert len(mbids) == pool['pool_size']
assert all(band['proposed_leaf'] in pool['leaf_counts'] for band in bands)
assert sum(pool['leaf_counts'].values()) == pool['pool_size']
assert sum(pool['region_counts'].values()) == pool['pool_size']
assert Counter(band['match_status'] for band in bands) == {
    'verified': 375,
    'verified_country_inferred': 22,
}
print('candidate pool valid')
PY
```

## Do not

- Do not point `data/seed-list.json` at this file.
- Do not copy the whole pool into a seed list.
- Do not treat a MusicBrainz search result as proof of relevance.
- Do not guess a country, leaf or album.
- Do not edit the historical seed lists.
