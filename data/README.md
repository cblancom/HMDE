# Data directory

This directory contains versioned curated data used by the project.

- `taxonomy.json` — approved v0.2.0 taxonomy hierarchy; only assignable leaves may be used as seed subgenres.
- `seed-list.json` — active-version pointer. It currently resolves to `seed-lists/v0.3.0.json`; the versioned file is the source of truth.
- `seed-lists/` — immutable versioned seed lists and batch artifacts. `v0.1.0.json` is the validated historical corpus; `v0.2.0.json` adds the approved 15-band batch; `v0.3.0.json` has 509 active bands.
- `seed-lists/batches/v0.3.0-batch-01.json`, `-02`, `-03` — approved 151/151/150 candidate batches. The v0.2.0 batch remains an archive.
- `seed-lists/candidates/` — verified candidate pool for the E13 v0.3.0 expansion. `v0.3.0-pool.json` has 453 MusicBrainz-identified bands across all 17 leaves and six regions; 452 are accepted and one is excluded, giving a 509-band corpus under a 510-band ceiling. The file is not an active seed list. See `seed-lists/candidates/README.md`.
- `classifications/` — versioned exact tag/genre-to-leaf mappings and manual album overrides for E4 normalization.
- `quality/` — versioned quality rule catalogue and initial exception baseline for E5.
- `metrics/` — versioned E6 metric catalogue.
- `analysis/` — generated E6 reports (ignored by Git).
- `network/` — generated E7 producer-network reports (ignored by Git).
- `fixtures/e2/` — versioned E2 fixture dataset (`e2-v0.1.0`) for 14 seed bands.
- `raw/` — local raw snapshots and caches. It is ignored by Git and must not be edited by hand.
- `ingestions/` — versioned extracted datasets and coverage reports produced by the ingestion pipeline. It is ignored by Git.
- `normalization/` — run reports produced by E4 normalization. It is ignored by Git.

The seed list is configuration, not source data. Ingestion datasets must record the seed-list version they used.
