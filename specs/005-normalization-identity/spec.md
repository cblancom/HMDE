# SPEC-005 — Normalization, identity and provenance

- **Status:** Implemented
- **Stage:** E4
- **Iteration:** MVP
- **Module:** `normalization`
- **Date:** 2026-11-08
- **Depends on:** SPEC-004 validated; E3 dataset `mb-20261107T194927Z-0d6cedd5c261`; [taxonomy](../../data/taxonomy.json) v0.2.0; [ADR-0005](../../docs/01-architecture/adr/ADR-0005-identity-and-provenance.md); [ADR-0007](../../docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md); [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0002](../../docs/01-architecture/adr/ADR-0002-musicbrainz-primary-source.md), [ADR-0004](../../docs/01-architecture/adr/ADR-0004-release-group-model.md), [ADR-0005](../../docs/01-architecture/adr/ADR-0005-identity-and-provenance.md), [ADR-0007](../../docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md), [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)
- **Plan:** [plan.md](plan.md) (approved)
- **Tasks:** [tasks.md](tasks.md) (implemented locally; remote CI pending)
- **Conventions:** [Engineering conventions](../../docs/01-architecture/conventions.md)
- **Owner:** Cristian

## Revision history

| Revision | Date | Change |
|---|---|---|
| 1 | 2026-11-08 | Initial draft; E4 scope and resolved normalization decisions |
| 2 | 2026-11-08 | Spec approved; technical plan and tasks drafted for review |
| 3 | 2026-11-08 | Plan/tasks approved; T-001 and T-002 completed |
| 4 | 2026-11-08 | T-003–T-006 completed: taxonomy sync, input validation, canonical entities and credits |
| 5 | 2026-11-08 | T-007–T-010 completed: classification, aggregates, membership and CLI/report |
| 6 | 2026-11-08 | T-011 completed: full 57-band normalization with 58 review/quarantine issues |
| 7 | 2026-11-08 | T-012 completed locally: tests, docs, scope guards and OpenAPI checks; remote CI pending |

## 1. Context and problem

E2 proved the PostgreSQL → FastAPI → React → Cytoscape path with a 14-band canonical fixture subset. E3 now provides a validated, versioned extracted dataset for the full corpus: `mb-20261107T194927Z-0d6cedd5c261`, with 57 artists, 731 canonical albums, 9,236 releases, 16,683 recordings and 32,303 deduplicated credit rows across 1960–2026.

The project does not yet have a production normalization path from that dataset into canonical entities. The E2 canonical tables are populated from fixtures, the taxonomy is not stored with version history, album-level subgenres do not exist in the database, and dataset membership/lifecycle is not represented. E4 must close that gap without losing provenance or rewriting E3/E2 history.

The following implementation constraints are agreed:

- classification is hybrid: deterministic mappings handle clear cases, and manual review is reserved for problematic cases;
- taxonomy versions and their nodes are persisted without overwriting historical classifications;
- the full v0.2 corpus is normalized, not only the 14-band E2 fixture;
- manual overrides live in versioned files under `data/classifications/` and have an audit trail.

```text
E3 dataset manifest + NDJSON
        │
        ▼
normalization run
  identity · provenance · roles · taxonomy · membership
        │
        ├── canonical entities and credits
        ├── album classifications and band aggregates
        ├── review queue and quarantine
        └── normalization report
        │
        ▼
versioned canonical dataset membership
```

This spec stops at normalized data. It does not expose new API fields, change the frontend, build quality metrics or construct analytical graphs.

## 2. Users and actors

- **Data operator/developer:** runs normalization, reviews problematic classifications and inspects the report.
- **System actor:** PostgreSQL stores canonical data, taxonomy versions, classifications and run metadata; the E3 dataset supplies extracted source data.
- **Implementation agent:** works from this spec, the plan, tasks, constitution and ADRs.
- **Future consumers:** E5 quality rules, E7 analysis, E8 API and E9 frontend consume normalized data.

There are no end-user roles, authentication or write API in E4. Normalization is a local batch process.

## 3. User stories and flows

### US-001 — Normalize the full corpus

As a data operator, I want to load the complete E3 v0.2 dataset into canonical tables so that the project moves beyond fixture data.

**Expected flow:**

1. The operator selects a validated E3 dataset and a taxonomy version.
2. Normalization resolves artists, albums, releases, recordings and credits by MBID.
3. Every canonical row carries provenance to the extracted record and its raw response.
4. A normalization run records counts, status, dataset version, taxonomy version and code version.
5. The run is idempotent and can be replayed from the same dataset.

### US-002 — Resolve identities deterministically

As a data operator, I want exact identity resolution so that entities are not merged by guesswork.

**Expected flow:**

1. A known MBID is reused when the canonical entity already exists.
2. A missing MBID is quarantined or reported; no fuzzy, name-only or probabilistic merge is performed.
3. Conflicting MBIDs or impossible mappings are written to quarantine with an explicit reason.
4. Re-running creates no duplicate canonical entities.

### US-003 — Classify albums with a hybrid strategy

As a data operator, I want clear albums classified automatically and problematic albums reviewed, so that classification is scalable and auditable.

**Expected flow:**

1. Exact normalized MusicBrainz tags/genres are mapped through a versioned mapping file.
2. Clear cases become high-confidence album classifications.
3. Ambiguous, conflicting or unmapped albums enter the review queue.
4. Manual overrides are read from a versioned file and applied with confidence `1.0`.
5. Every canonical album ends with one primary leaf and zero or more secondary leaves.

### US-004 — Derive band aggregates

As an analysis consumer, I want a band-level primary subgenre so that existing filters remain meaningful.

**Expected flow:**

1. The aggregate is derived from album primary classifications over the active analysis period.
2. A deterministic majority determines the primary leaf.
3. A tie or an exception is resolved by an audited manual override.
4. The aggregate stores confidence, status, taxonomy version and mapping rule.

### US-005 — Preserve membership and lifecycle

As a data operator, I want dataset membership to be versioned so that bands can be added or retired without deleting history.

**Expected flow:**

1. The normalized v0.2 dataset records 57 active bands and their batches.
2. A retired band remains in history but is not active in later membership.
3. Historical E2 fixtures and E3 datasets remain available.
4. Normalization never deletes unrelated canonical rows or raw responses.

### US-006 — Review and audit problematic cases

As a data operator, I want a review queue and an audit trail so that exceptions are visible and reproducible.

**Expected flow:**

1. Low-confidence, ambiguous or conflicting cases are listed with reason and evidence.
2. Accepting or overriding a classification records the operator action and source file/version.
3. A report summarizes accepted, reviewed, quarantined and missing classifications.
4. Missing data is reported as missing, not as negative evidence.

## 4. Functional requirements

### FR-001 — Dataset input and validation

Normalization must consume a validated E3 extracted dataset and reject invalid input before writing canonical data.

- Read `manifest.json` and verify dataset version, file checksums, band count, source snapshot and dataset metadata.
- Require seed-list version `0.2.0`, taxonomy version `0.2.0` and the declared 1960–2026 period for the v0.2 dataset.
- Require the corresponding seed list and active taxonomy to be readable.
- Reject stale, incomplete or checksum-mismatched datasets.
- Do not re-fetch MusicBrainz data during normalization.

**Verification:** unit/integration tests cover valid, missing, stale, corrupted and mismatched manifests.

### FR-002 — Normalization run and idempotency

Each normalization execution must create a `normalization_run` record containing:

- unique run identifier;
- E3 dataset version and source manifest hash;
- seed-list and taxonomy versions;
- code version, start/end timestamps and status;
- input counts, normalized counts, quarantined counts, reviewed counts and failures;
- output report location.

Re-running the same dataset and taxonomy version must be idempotent: no duplicate canonical rows, no duplicate classifications and no loss of provenance. A new run may add a new audit row. Failed or interrupted runs must preserve completed work and never present partial output as complete.

**Verification:** replay twice and compare counts; interrupt/resume tests; run-status tests.

### FR-003 — Deterministic identity resolution

Canonical identities are resolved by exact MBID only.

- Artists, release groups, releases and recordings use MBID as the deterministic external key.
- Existing canonical rows with the same MBID are reused, not duplicated.
- MBIDs found in multiple entity types, malformed MBIDs and conflicting canonical mappings are quarantined.
- No fuzzy matching, name-only merging or probabilistic identity resolution is allowed.
- External identifiers are preserved and linked to the canonical entity without implying identity beyond the exact identifier.

**Verification:** duplicate, conflicting, missing and malformed MBID tests; no duplicate canonical rows after replay.

### FR-004 — Canonical entity normalization

Normalization must load the full v0.2 corpus into canonical entities:

- 57 artists;
- 731 canonical albums (`release_group` rows);
- 9,236 releases;
- 16,683 recordings;
- release–recording links from `release_recordings.ndjson`;
- credit rows derived from E3 credits with role, scope, target, attributes, confidence, status and provenance;
- external identifiers for entities where E3 supplies them.

The normalized counts must reconcile with the E3 manifest and report. Differences caused by explicit deduplication or quarantine must be reported and justified. Canonical albums must follow [ADR-0004](../../docs/01-architecture/adr/ADR-0004-release-group-model.md): primary type `album`, no secondary type, within the declared period.

**Verification:** count reconciliation, spot checks and orphan checks against the E3 manifest.

### FR-005 — Provenance and source records

Every normalized entity, credit, classification and aggregate must be traceable to its origin.

- Canonical rows reference a `source_record` or equivalent provenance row with source, source entity type, external ID/MBID, URL, retrieval time, HTTP status, payload hash, license, API version, ingest-run/dataset version and raw response reference.
- A canonical row must not exist without provenance.
- Provenance is append-only; re-normalization may add a new run link but must not erase prior provenance.
- E2 fixture provenance must remain readable; E4 must not silently delete unrelated source records.

**Verification:** no orphan queries; provenance assertions for every normalized table; historical fixture provenance remains readable.

### FR-006 — Versioned taxonomy persistence

The database must store the approved taxonomy with version history.

- Persist taxonomy versions and nodes, including code, name, parent code, assignability, source hash and version status.
- Only assignable leaves may be used for album or band classifications.
- Parent references and cycles are validated before persistence.
- The current taxonomy projection must preserve existing E2 read paths such as `subgenre.code` and `subgenre.name`.
- A taxonomy version is immutable after it is used by a normalization run.
- A taxonomy change creates a new version; it does not rewrite historical classifications.

**Verification:** migration tests; leaf-only, parent, cycle and version-immutability tests; existing catalog queries still work.

### FR-007 — Versioned classification inputs

Classification inputs must be versioned files that reference a taxonomy version.

- Provide a deterministic tag/genre-to-leaf mapping file under `data/classifications/` for v0.1.0.
- Provide a manual overrides file under `data/classifications/` for v0.1.0; it may be empty, but its schema must be valid.
- Each mapping entry records the normalized source label, target leaf code, confidence contribution and mapping rule identifier.
- Each override records the release-group MBID, primary leaf, secondary leaves, confidence `1.0`, reason, reviewer and date.
- Inputs with unknown leaves, duplicate keys, invalid MBIDs, taxonomy version mismatches or ambiguous primary assignments fail validation.

**Verification:** schema tests for valid, empty and malformed mapping/override files.

### FR-008 — Hybrid album classification

Album classification must combine deterministic mappings, confidence and manual review.

- Match only exact normalized tags/genres against the versioned mapping file; no substring, fuzzy or generated matching.
- High-confidence cases (`>= 0.80`) are accepted automatically.
- Medium-confidence cases (`0.50–0.79`) are persisted as non-blocking alerts in the review queue.
- Low-confidence cases (`< 0.50`) and unmapped albums require manual review.
- Manual overrides take precedence and have confidence `1.0`.
- Every classified album has exactly one primary leaf and zero or more secondary leaves; secondary labels must also be leaves.
- Conflicting primary candidates or ties must not be resolved arbitrarily; they are quarantined/reviewed.
- Classification stores `taxonomy_version`, `confidence`, `status`, `mapping_rule`, evidence and provenance.

**Verification:** high/medium/low, override, tie, conflict, no-tag and parent-node tests; album constraints.

### FR-009 — Album and band aggregate outputs

For each canonical album, store its primary and secondary leaf classifications. For each active band, derive:

- a primary leaf from album primary classifications over the active analysis period;
- supporting album counts and confidence;
- review status and taxonomy version;
- a deterministic mapping-rule identifier.

A band aggregate tie or exception requires a manual override. The band aggregate must remain compatible with the existing `artist_subgenre` read path while retaining taxonomy version history.

**Verification:** aggregate majority, tie, override, empty and period-boundary tests.

### FR-010 — Review queue, conflicts and quarantine

Problematic data must be visible and auditable.

- Review queue entries include reason, entity MBID, candidate labels, evidence, confidence, taxonomy version and status.
- Conflicts are preserved; the system must not delete the losing classification.
- Quarantine reasons include missing MBID, invalid taxonomy leaf, ambiguous primary, invalid override, provenance failure and dataset mismatch.
- Review actions record actor, timestamp, source file/version and previous/new values.
- Missing tags or missing mappings are reported as missing evidence, not as a negative classification.

**Verification:** queue, conflict, quarantine and audit tests; missing-data wording in the report.

### FR-011 — Credit and role normalization

Normalization must preserve the E3 credit model.

- Map MusicBrainz roles and attributes to the controlled role vocabulary without losing the original role or attributes.
- Preserve release-group, release and recording scope and their target IDs.
- Preserve `credited_as`, confidence, status and source provenance.
- Producer attributes such as `co`, `executive`, `assistant` and `additional` must be represented consistently with [ADR-0007](../../docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md).
- Duplicate source credits may be consolidated only when the exact same MBID, role, scope, target and provenance are equivalent; the consolidation rule and counts must be reported.
- Credits that cannot be mapped are quarantined, not silently dropped.

**Verification:** role/attribute mapping, scope, deduplication, conflict and orphan tests.

### FR-012 — Dataset membership and lifecycle

Normalization must record dataset membership separately from entity existence.

- `dataset_membership` records dataset version, artist, seed-list version, batch ID, lifecycle state, replacement MBID when applicable and addition/retirement versions.
- The v0.2 membership contains 57 active bands, with 42 from v0.1.0 and 15 from `v0.2.0-batch-01`.
- Historical memberships remain queryable.
- Retiring a band must not delete its canonical rows, credits, classifications or provenance.
- No E2 or E3 historical artifact is rewritten by membership changes.

**Verification:** 42 + 15 membership test; retired fixture test; historical artifact checks.

### FR-013 — Normalization CLI and report

A documented CLI must support:

- full v0.2 normalization;
- validation/dry-run mode without writes;
- rebuilding the same dataset idempotently;
- selecting an explicit dataset, taxonomy and classification input version;
- stable exit codes for success, completed-with-review and fatal failure.

The report must include counts by entity, classification status, confidence band, review queue, quarantine reason, role and scope; dataset/taxonomy versions; runtime; and explicit missing-data language. It must not expose secrets.

**Verification:** CLI tests, report assertions and a full local run.

### FR-014 — Tests without live network

E4 tests must not call MusicBrainz or any external source.

- Tests use the v0.2 dataset fixture or a small checked-in subset with checksums.
- Identity, classification, overrides, taxonomy versions, provenance, membership and replay are covered.
- A full-data integration test is allowed only against a local PostgreSQL database with the dataset available.
- CI does not require network access beyond package installation.

**Verification:** full backend suite with network disabled; CI passes.

### FR-015 — Boundary with API, frontend and analysis

E4 owns normalization only.

- Do not add or change public API endpoints, request/response schemas or OpenAPI fields.
- Do not change frontend routes, components, filters or generated types.
- Do not build graph metrics, analytical runs or quality thresholds; those belong to E5–E7.
- Do not re-ingest MusicBrainz or mutate raw responses.
- Existing E2 read paths may continue reading canonical tables; their contract and query semantics must remain valid. New taxonomy and classification data is not exposed as a new API contract in this spec.

**Verification:** OpenAPI drift check, frontend diff, scope-guard tests and canonical fixture tests.

## 5. Non-functional requirements

### NFR-001 — Reproducibility and determinism

The same E3 dataset, taxonomy version, classification inputs and code version must produce the same normalized rows, classifications, aggregates and report. Ordering and generated IDs must be deterministic.

### NFR-002 — Idempotency

Repeated and interrupted normalization runs must not duplicate entities, credits, classifications, membership rows or provenance.

### NFR-003 — Performance

A full 57-band normalization run should complete within 30 minutes on the development environment, excluding database provisioning and external downloads. The report records actual runtime.

### NFR-004 — Provenance and auditability

Every normalized row must have an auditable source. Review decisions and manual overrides must be attributable and reversible through a later version, never by silent mutation.

### NFR-005 — Data safety

No destructive migration, no deletion of E2/E3 history, no deletion of conflicting classifications and no overwriting of raw payloads.

### NFR-006 — Compatibility

Python 3.13, PostgreSQL 16, Docker Compose, uv, pytest and Ruff remain supported. No Node dependency is introduced.

### NFR-007 — Security

No secrets or credentials are committed or logged. Dataset paths and classification inputs are validated. The batch process has no write HTTP surface.

### NFR-008 — Observability

Runs produce structured logs and a report with run ID, dataset version, taxonomy version, counts, quarantine/review totals, failures and runtime.

### NFR-009 — Maintainability

Normalization lives under the `normalization` boundary and depends on existing models/db/ingestion outputs, not on API or frontend code. Source-specific logic remains isolated.

### NFR-010 — Language

All code, documentation, reports, error messages and review reasons are in English.

## 6. Business rules

- **BR-001:** MBID is the only automatic identity key in E4.
- **BR-002:** No fuzzy, name-only or probabilistic merging is allowed.
- **BR-003:** Only assignable taxonomy leaves may classify albums or bands.
- **BR-004:** Each canonical album has exactly one primary leaf and zero or more secondary leaves.
- **BR-005:** A band aggregate is derived from album primary labels; ties require audited manual resolution.
- **BR-006:** Confidence bands follow ADR-0008: low `< 0.50`, medium `0.50–0.79`, high `>= 0.80`; manual overrides use `1.0`.
- **BR-007:** Manual review is reserved for problematic cases; clear high-confidence mappings are automatic.
- **BR-008:** Missing tags, mappings or credits are missing evidence, not negative evidence.
- **BR-009:** Taxonomy and membership versions are immutable once used; changes require a new version.
- **BR-010:** Retired bands remain in history and historical datasets remain readable.
- **BR-011:** E4 does not change the public API contract or frontend behavior.
- **BR-012:** No source data is re-fetched during normalization.

## 7. Edge cases and errors

- Dataset manifest missing, stale, incomplete or checksum-mismatched: fail before writing.
- Taxonomy version mismatch or invalid hierarchy: fail before writing.
- Unknown or parent taxonomy leaf in a mapping or override: reject the input.
- Album has no tags/genres or no mapping: quarantine/review, no invented label.
- Album maps to multiple leaves with equal confidence: quarantine/review, no arbitrary primary.
- Manual override names a different primary than the mapping: override wins and is audited.
- Duplicate MBID across entity types or conflicting canonical rows: quarantine and report.
- Canonical row exists from E2 fixtures: reuse by MBID where compatible; never delete unrelated rows.
- Credit has an unmapped role/attribute: preserve original data and quarantine the normalized credit.
- Normalization is interrupted: completed rows remain committed and the run is marked failed/incomplete.
- Replay sees a changed E3 dataset: reject unless the dataset is explicitly selected and versioned.
- Taxonomy or seed-list file changes after a run: historical classification versions remain intact.

## 8. Out of scope

- API endpoint or response-schema changes.
- Frontend routes, components, filters or generated TypeScript types.
- Graph construction, metrics, communities or temporal analysis.
- E5 data-quality thresholds, dashboards or review UI.
- MusicBrainz re-ingestion, source expansion or raw-cache changes.
- Alias normalization when the E3 dataset does not contain aliases.
- Studio/place canonicalization; E3 place relationships remain extracted for a later spec.
- Automated fuzzy matching, LLM classification or inferred identity merges.
- Expansion beyond the 57-band v0.2 corpus.
- Production deployment or scheduling.

## 9. Acceptance criteria

| ID | Criterion | Evidence |
|---|---|---|
| AC-001 | Migration creates all E4 taxonomy, classification, provenance, membership and run structures from an empty database and rolls back cleanly. | Migration test and downgrade/upgrade |
| AC-002 | The full v0.2 dataset is normalized and canonical counts reconcile with the E3 manifest; differences are explicitly reported. | Integration normalization test and report |
| AC-003 | Replaying the same dataset is idempotent and produces no duplicate canonical rows or classifications. | Double-run test |
| AC-004 | Identity resolution uses MBID only; malformed, conflicting and missing identities are quarantined. | Identity tests |
| AC-005 | Every normalized row has provenance; no canonical orphans exist. | Orphan and provenance queries |
| AC-006 | Taxonomy versions and nodes are persisted; only assignable leaves are used; historical versions remain immutable and readable. | Taxonomy tests |
| AC-007 | Tag-map and override inputs are versioned, validated and auditable. | Input-validation tests |
| AC-008 | High-confidence albums classify automatically; medium cases queue; low/unmapped cases require review; overrides use `1.0`. | Classification tests |
| AC-009 | Every album has one primary leaf and only leaf secondaries; ties/conflicts are quarantined. | Album constraints and review tests |
| AC-010 | Every active band has an aggregate with taxonomy version, confidence, status and mapping rule; ties are explicit. | Aggregate tests |
| AC-011 | Membership records 42 v0.1.0 + 15 batch bands as 57 active in v0.2.0; retired behavior is represented without deletion. | Membership tests |
| AC-012 | Credits preserve role, scope, targets, attributes, confidence and provenance; unmapped cases are quarantined. | Credit tests |
| AC-013 | The CLI supports full run, dry run and replay with documented exit codes; the report includes counts, versions and missing-data wording. | CLI and report tests |
| AC-014 | No public API, OpenAPI or frontend change occurs; E2 contract tests and E3 historical artifacts remain valid. | OpenAPI drift, frontend diff and regression tests |
| AC-015 | Full backend tests, Ruff, format and CI pass without live external network calls. | Local and remote CI evidence |

## 10. Assumptions and open questions

### Assumptions

- The E3 dataset `mb-20261107T194927Z-0d6cedd5c261` and its raw responses remain available and immutable.
- Taxonomy v0.2.0 is approved and referenced by seed-list v0.2.0.
- E2 fixture files remain historical; canonical rows may be reused/upserted by MBID but unrelated rows are not deleted.
- Classification inputs live under `data/classifications/` and reference the taxonomy version.
- High-confidence automatic mapping is deterministic and exact; manual review is the exception path, not the default.
- E5 will consume the review/quarantine outputs; E4 does not build a review UI.
- Place/studio and alias normalization are deferred because E3 does not provide the required canonical alias data and E4 scope excludes studio canonicalization.

### Open questions

| Question | Blocking? | Owner | Resolution |
|---|---|---|---|
| Exact confidence formula and tag-map schema | No | Implementation plan | Define in `plan.md`; must respect ADR-0008 thresholds and exact-match rules. |
| Whether the existing `subgenre` table becomes a view or a maintained current projection | No | Implementation plan | Preserve the E2 read path; exact representation belongs in the migration plan. |
| Whether duplicate credits are consolidated at load or at read time | No | Implementation plan | Preserve provenance either way; report the rule and counts. |
| How to model review-queue rows and manual actions | No | Implementation plan | Define tables/statuses in the plan; no review UI in E4. |

No blocking question remains for planning. The next step is `plan.md`, followed by `tasks.md` and explicit approval.

## 11. Validation result

- **Date:** 2026-11-08
- **Verdict:** Implemented; local validation passed; remote CI and formal validation pending
- **Evidence:** 210 backend tests passed with PostgreSQL; Ruff check/format, OpenAPI drift and compose validation passed. Full run `54d66992-643b-49ec-bac4-fe514ea39e94` produced 57 bands, 731 albums and 32,665 credit contexts. See `tasks.md`.

## 12. References

- [Constitution](../../constitution.md)
- [AGENTS.md](../../AGENTS.md)
- [Scope](../../docs/00-vision/scope.md)
- [Roadmap](../../docs/00-vision/roadmap.md)
- [Data model v0](../../docs/01-architecture/data-model.md)
- [E2 ER diagram](../../docs/01-architecture/er-diagram.md)
- [Taxonomy](../../data/taxonomy.json)
- [Seed list documentation](../../docs/03-data/seed-list.md)
- [ADR-0004 — Release-group model](../../docs/01-architecture/adr/ADR-0004-release-group-model.md)
- [ADR-0005 — Identity and provenance](../../docs/01-architecture/adr/ADR-0005-identity-and-provenance.md)
- [ADR-0007 — Credit scope](../../docs/01-architecture/adr/ADR-0007-credit-scope-and-recording-level-aggregation.md)
- [ADR-0008 — Taxonomy, corpus and versioning](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)
- [SPEC-003 — MusicBrainz ingestion](../003-musicbrainz-ingestion/spec.md)
- [SPEC-004 — Corpus v0.2](../004-corpus-v0-2/spec.md)
