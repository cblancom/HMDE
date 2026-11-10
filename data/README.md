# Data directory

This directory contains versioned curated data used by the project.

- `taxonomy.json` — approved v0.2.0 taxonomy hierarchy; only assignable leaves may be used as seed subgenres.
- `seed-list.json` — active-version pointer. It currently resolves to `seed-lists/v0.2.0.json`; the versioned file is the source of truth.
- `seed-lists/` — immutable versioned seed lists and batch artifacts. `v0.1.0.json` is the validated historical corpus; `v0.2.0.json` adds the approved 15-band batch.
- `seed-lists/batches/v0.2.0-batch-01.json` — approved batch of 15 new bands, three per expanded decade.
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
