# MusicBrainz feasibility spike

Disposable research code for E0. It is not part of the product and is not imported by the API or the production ETL.

## Purpose

Measure whether MusicBrainz contains enough production data to support the HMDE MVP, and identify data-model implications before implementation.

## Usage

```bash
python3 spike/spike_musicbrainz.py
```

Useful options:

```bash
python3 spike/spike_musicbrainz.py --band "Iron Maiden"
python3 spike/spike_musicbrainz.py --max-bands 4
python3 spike/spike_musicbrainz.py --no-cache
```

The client enforces a minimum interval of 1.1 seconds between network requests and uses a descriptive User-Agent.

## Inputs and outputs

- `sample.json` — 28-band stratified sample.
- `output/raw/` — cached raw MusicBrainz responses (disposable, outside Git).
- `output/spike_results.json` — structured results and metrics.
- `output/spike_report.md` — generated report.
- `output/collection_metadata.json` — initial full-fetch cost.

The curated project report is `docs/03-data/spike-report.md`.

## Caveats

- The sample is stratified, not random or statistically representative.
- Low-confidence release-groups are flagged heuristically.
- Recording-level credits are inspected on the earliest official release only when no release-level producer is found.
- The raw cache reflects a 2026-11-05 MusicBrainz snapshot.
- Do not use this script as production ingestion code.
