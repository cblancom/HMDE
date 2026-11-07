# Data directory

This directory contains versioned curated data used by the project.

- `seed-list.json` — machine-readable MVP seed list (v0.1.0). The human-readable rationale is in [`docs/03-data/seed-list.md`](../docs/03-data/seed-list.md).
- `fixtures/e2/` — versioned E2 fixture dataset (`e2-v0.1.0`) for 14 seed bands.
- `raw/` — local raw snapshots and caches. It is ignored by Git and must not be edited by hand.
- `ingestions/` — versioned extracted datasets and coverage reports produced by the ingestion pipeline. It is ignored by Git.

The seed list is configuration, not source data. Ingestion datasets must record the seed-list version they used.
