# Data directory

This directory contains versioned curated data used by the project.

- `seed-list.json` — machine-readable MVP seed list (v0.1.0). The human-readable rationale is in [`docs/03-data/seed-list.md`](../docs/03-data/seed-list.md).
- `raw/` — local raw snapshots and caches. It is ignored by Git and must not be edited by hand.

The seed list is configuration, not source data. Ingestion datasets must record the seed-list version they used.
