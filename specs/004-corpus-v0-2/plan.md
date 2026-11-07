# Technical plan — SPEC-004 Corpus v0.2 seed-list expansion

- **Status:** Approved
- **Spec:** [spec.md](spec.md)
- **Tasks:** [tasks.md](tasks.md)
- **Stage:** E3
- **Module:** `ingestion`
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0002](../../docs/01-architecture/adr/ADR-0002-musicbrainz-primary-source.md), [ADR-0005](../../docs/01-architecture/adr/ADR-0005-identity-and-provenance.md), [ADR-0007](../../docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md), [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)

## 1. Solution summary

SPEC-004 prepares the corpus-v0.2 input and ingestion dataset before E4. It preserves the validated 42-band, 1980–2000 corpus as active history, adds a curated 15-band batch, extends album eligibility to 1960–2026 and makes the E3 seed-list and ingestion metadata data-driven.

The output is a new versioned seed list (v0.2.0), a new E3 extracted dataset and coverage report, and an unchanged historical E3 dataset. Album-level taxonomy classification, band aggregates, confidence and dataset membership are explicitly deferred to SPEC-005 (E4).

The 15 new bands are selected manually. The approved distribution is three new bands for each expanded decade: 1960s, 1970s, 2000s, 2010s and 2020s. The exact MBIDs are selected in T-001 and must be approved before ingestion.

## 2. Architecture and data flow

```text
data/seed-lists/v0.1.0.json          (immutable historical archive)
data/seed-lists/v0.2.0.json          (42 active + 15 new active)
data/seed-list.json                  (active-version pointer)
data/taxonomy.json                   (approved taxonomy v0.2.0)
        │
        ▼
E3 seed validation
  schema · versions · lifecycle · taxonomy leaves · period
        │
        ▼
MusicBrainz traversal
  raw cache reuse · new 1960s/1970s/2000s–2020s data
        │
        ▼
new raw responses + new extracted dataset
  manifest · coverage report · historical dataset preserved
```

No canonical catalog tables or API contracts change in this spec.

## 3. Components and responsibilities

| Component or path | Responsibility |
|---|---|
| `data/seed-lists/v0.1.0.json` | Immutable archive of the validated 42-band seed list. |
| `data/seed-lists/v0.2.0.json` | New seed list with 42 active bands plus 15 new bands. |
| `data/seed-list.json` | Active-version pointer consumed by default CLI commands. |
| `data/taxonomy.json` | Approved taxonomy v0.2.0; seed subgenres must be leaves. |
| `backend/src/hmde/etl/musicbrainz/seed.py` | Data-driven schema, lifecycle, batch, period and taxonomy validation. |
| `backend/src/hmde/etl/musicbrainz/traversal.py` | Period-driven canonical album filtering. |
| `backend/src/hmde/etl/musicbrainz/report.py` | Dynamic decade grouping from 1960s through 2020s. |
| `backend/src/hmde/etl/musicbrainz/dataset.py` | Dataset manifest with seed-list version, taxonomy version and period. |
| `backend/src/hmde/etl/musicbrainz/pipeline.py` | Pass corpus metadata into the run and dataset output. |
| `backend/tests/unit/` | Seed, taxonomy, period, dataset and report tests. |
| `backend/tests/integration/` | Versioned seed storage, replay and ingestion tests. |
| `README.md`, `AGENTS.md`, `data/README.md`, `docs/03-data/seed-list.md` | Corpus v0.2 commands and lifecycle documentation. |

## 4. Technical decisions and alternatives

### 4.1 Seed-list storage

- Archive v0.1.0 as `data/seed-lists/v0.1.0.json`.
- Store v0.2.0 as `data/seed-lists/v0.2.0.json`.
- Keep `data/seed-list.json` as an active-version pointer, for example:
  ```json
  {"active_version": "0.2.0", "path": "seed-lists/v0.2.0.json"}
  ```
- The loader resolves the pointer relative to the pointer file.
- Existing commands can keep using `--seed-list ../data/seed-list.json`.
- The pointer must not contain the corpus itself; the versioned file is the source of truth.

### 4.2 Seed-list schema

The v0.2.0 file contains:

- `schema_version: 2`;
- `version: "0.2.0"`;
- `taxonomy_version: "0.2.0"`;
- `period_start` and `period_end`;
- `batches`;
- `bands`, each with MBID, name, country, `seed_subgenre_code`, `batch_id`, lifecycle status and verification date.

Fixed constants for 42 bands and six per subgenre are removed. The declared distribution is validated against the actual data.

### 4.3 15-band batch

- Three new bands from the 1960s.
- Three from the 1970s.
- Three from the 2000s.
- Three from the 2010s.
- Three from the 2020s.
- All original 42 bands remain active and unchanged.
- Every new MBID is verified against MusicBrainz before ingestion.
- Every new band uses an approved taxonomy leaf as `seed_subgenre_code`.
- The exact list is recorded in a batch artifact and approved in T-001 before T-002 writes v0.2.0.

### 4.4 Taxonomy validation

- Load `data/taxonomy.json` once.
- Reject unknown codes.
- Reject parent/family nodes as seed subgenres.
- Validate parent references and cycles.
- Record the taxonomy version in the seed list and dataset manifest.
- Do not classify albums in this spec; that is E4.

### 4.5 Period and decades

- Period comes from the seed list.
- The traversal rejects albums before 1960 or after 2026 with `out_of_period`.
- The report groups decades dynamically:
  - 1960s, 1970s, 1980s, 1990s, 2000, 2000s, 2010s, 2020s.
- Existing 1980–2000 dataset stays immutable.

### 4.6 Dataset metadata

The new dataset manifest adds:

- `seed_list_version: "0.2.0"`;
- `taxonomy_version: "0.2.0"`;
- `period_start: "1960-01-01"`;
- `period_end: "2026-12-31"`;
- `batch_ids`;
- existing content checksums and counts.

`IngestRun.parameters` records the same metadata. No ingestion-table schema migration is required.

### 4.7 Alternatives considered

| Alternative | Reason for rejection |
|---|---|
| Edit `data/seed-list.json` in place | Destroys the historical v0.1.0 input and breaks reproducibility. |
| Keep hardcoded 42/6 validation | Cannot support 15 new bands or future batches. |
| Use artist subgenre for seed validation without taxonomy | Parent nodes and unknown labels would enter the corpus. |
| Add 100+ bands now | Too much data churn before E4 validates classification and normalization. |
| Classify albums in this spec | Mixes E3 corpus preparation with E4 normalization. |
| Store all seed bands in the pointer | Duplicates the source of truth and creates drift. |

## 5. Data model and migrations

- No database migration.
- `ingest_run.parameters` remains JSONB and records corpus metadata.
- No canonical table writes.
- No E4 tables are added here.
- The dataset manifest is a file-level schema change only.
- Historical raw responses and datasets remain untouched.

## 6. API contract

No API changes.

- Existing `/health` and `/api/v1/bands` behaviour remains as validated in E2.
- `openapi.json` must not drift.
- The API continues to serve existing canonical fixture data until E4/E8/E9 replace it.
- The new E3 dataset is not exposed by the API in this spec.

## 7. Frontend impact

None.

- No routes, components, generated types or filters change.
- The current frontend remains scoped to the E2 dataset.

## 8. Error handling and consistency

- Invalid active pointer: fail before reading bands.
- Missing or unsupported schema version: fail.
- Version mismatch between pointer and target: fail.
- Duplicate MBIDs: fail.
- Missing original 42 bands: fail.
- Fewer or more than 15 new bands: fail.
- New band outside approved batch: fail manifest validation.
- Parent taxonomy node: reject.
- Invalid cycle or missing parent: reject.
- Out-of-period albums: exclude with reason.
- Cache miss in cache-only mode: fail the affected band and report it.
- Interrupted run: preserve completed raw responses and previous datasets.
- Dataset conflict: never overwrite a historical dataset.

## 9. Security and trust boundaries

- No new secrets.
- The User-Agent remains mandatory for live ingestion.
- The active pointer contains only repository-relative paths.
- Path traversal outside `data/seed-lists/` is rejected.
- The ingestion continues to respect MusicBrainz access limits.
- No API write path is introduced.

## 10. Observability

- `ingest_run.parameters` includes seed-list, taxonomy and period metadata.
- Report includes seed-list version, taxonomy version, period and batch IDs.
- Logs include the resolved seed-list version and dataset version.
- Failures remain structured and free of secrets.

## 11. Testing strategy

| Level | What is tested | Evidence |
|---|---|---|
| Unit | Pointer resolution, schema, lifecycle, taxonomy leaves, batch counts, period boundaries, dynamic decade labels. | `backend/tests/unit/test_seed_v02.py`, `test_taxonomy_validation.py` |
| Integration | Versioned seed files, archive immutability, data-driven validation, dataset metadata, historical dataset preservation. | `backend/tests/integration/test_seed_versioning.py`, `test_corpus_v02_ingestion.py` |
| Contract | OpenAPI unchanged; canonical E2 counts unchanged. | Existing contract/regression tests |
| Manual | Controlled 57-band ingestion, cache-only replay and report review. | T-007/T-008 evidence |

Commands:

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde \
TEST_DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde_test \
  uv run pytest
```

No live network in automated tests.

## 12. Deployment and reversibility

- Add versioned seed files without deleting v0.1.0.
- Keep the active pointer reversible to v0.1.0.
- The new ingestion creates a new dataset; old datasets remain.
- No database migration is required.
- If validation fails, the pointer can remain on v0.1.0 and E3 remains usable.

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Exact 15-band selection is biased or unverified | T-001 uses explicit coverage targets, MBID verification and owner approval. |
| Taxonomy parent used as a seed subgenre | Loader validates leaves against the approved taxonomy. |
| Active pointer drift | Pointer stores only a path/version; the versioned file is authoritative. |
| Period expansion adds unexpected volume | Reuse raw cache; run in batch; report requests/runtime. |
| Historical dataset overwritten | Dataset writer rejects conflicts and preserves prior versions. |
| Seed-list schema breaks E3 defaults | Loader resolves the pointer while keeping the existing CLI path. |
| E4 work starts too early | Explicit scope guard and no canonical/classification changes in this spec. |

## 14. Traceability requirements → plan → tasks

| Requirement | Plan section | Tasks |
|---|---|---|
| FR-001 | 4.1, 4.2 | T-002 |
| FR-002 | 4.3 | T-001, T-002 |
| FR-003 | 4.4 | T-003 |
| FR-004 | 4.2, 4.4 | T-004 |
| FR-005 | 4.5 | T-005 |
| FR-006 | 4.6 | T-006 |
| FR-007 | 8 | T-004, T-007 |
| FR-008 | 4.5 | T-005 |
| FR-009 | 5, 12 | T-002, T-007 |
| FR-010 | 11 | T-008 |
| FR-011 | 5, 6, 7 | T-002, T-008 |
| NFR-001 | 4.6, 12 | T-006, T-007 |
| NFR-002 | 4.5, 8 | T-004, T-007 |
| NFR-003 | 4.5 | T-005, T-007 |
| NFR-004 | 11 | T-008 |
| NFR-005 | 9 | T-001, T-002 |
| NFR-006 | 3 | T-008 |

## 15. Approval and next step

This plan was approved together with `tasks.md` before implementation. T-001 was the mandatory batch-selection gate; the 15-band list and distribution are approved, and the v0.2.0 implementation is complete locally.
