# Technical plan — SPEC-016

- **Status:** In implementation
- **Spec:** [spec.md](spec.md)
- **Tasks:** [tasks.md](tasks.md)
- **ADRs:** [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md), [ADR-0002](../../docs/01-architecture/adr/ADR-0002-musicbrainz-primary-source.md)
- **Module:** `ingestion`, with `normalization`, `quality`, `analytics`, `api` and `web` verification

## 1. Solution summary

Expand the active corpus from 57 to a 510-band ceiling using the existing versioned seed-list, E3 ingestion, E4 normalization, E5 quality, E6/E7 analysis and read-only API. T-002 verified 452 candidates and excluded Hellhammer, so the verified corpus is 509 bands. The work is data growth plus the smallest code changes required to remove hardcoded corpus assumptions.

The expansion accepts all 453 candidates in `data/seed-lists/candidates/v0.3.0-pool.json`, which already covers all 17 taxonomy leaves and six regions. Candidates were verified individually; failures are excluded and reported. The 452 accepted additions are recorded in three batches of 151, 151 and 150 bands.

The v0.3.0 seed list keeps all 57 v0.2.0 bands active and appends the verified candidates. A new dataset, normalization run, quality run, EDA report and network snapshot are produced. The v0.2.0 dataset and all historical artifacts remain unchanged.

E3 canonicalization writes one row per entity MBID, orders every NDJSON file deterministically and excludes release groups associated with more than one active band. These album-level exclusions are reported with reason `multi_artist_release_group` and do not change the 509-band seed list.

Explicitly not included: expansion beyond 510 bands, E12 deployment, production infrastructure, a taxonomy revision, new sources, a new credit model, automatic fuzzy identity resolution and a UI redesign.

## 2. Architecture and data flow

```text
candidate pool (453)
        │
        ▼
verification (452 accepted, 1 excluded) ──► 3 batch artifacts (151 + 151 + 150)
        │
        ▼
seed list v0.3.0 (509 active) ──► active pointer
        │
        ▼
E3 MusicBrainz ingestion ──► raw cache + canonicalization + dataset + manifest
        │
        ▼
E4 normalization ──► memberships, classifications, credits, quarantine
        │
        ▼
E5 quality ──► findings + exceptions + coverage
        │
        ├──► E6 EDA metrics
        └──► E7 producer network
                    │
                    ▼
          API / frontend performance review
```

The existing modules remain the boundaries:

- `backend/src/hmde/etl/musicbrainz/` owns source access, caching, extraction and dataset manifests.
- `backend/src/hmde/normalization/` owns identity, taxonomy, credits, aggregates and dataset membership.
- `backend/src/hmde/quality/` owns rules, findings, exceptions and coverage.
- `backend/src/hmde/analytics/` owns EDA and network persistence.
- `backend/src/hmde/api/` and `frontend/` are consumers and should need no behavioural rewrite.

## 3. Components and responsibilities

| Component or path | Responsibility |
|---|---|
| `data/seed-lists/candidates/v0.3.0-pool.json` | Versioned 453-band candidate pool; accepted input to verification, not an approved seed list. |
| `data/seed-lists/candidates/v0.3.0-verification.json` | Verification report with accepted/excluded candidates, album and source evidence. Created by T-002. |
| `data/seed-lists/batches/v0.3.0-batch-01.json` | First approved 151-band batch. |
| `data/seed-lists/batches/v0.3.0-batch-02.json` | Second approved 151-band batch. |
| `data/seed-lists/batches/v0.3.0-batch-03.json` | Third approved batch (150 bands). |
| `data/seed-lists/v0.3.0.json` | Append-only seed list with 509 bands and all 57 v0.2.0 bands retained. |
| `data/seed-list.json` | Active-version pointer; moves to v0.3.0 only after validation. |
| `backend/src/hmde/etl/musicbrainz/seed.py` | Existing data-driven v2 seed-list loader; extend only if a real validation gap appears. |
| `backend/src/hmde/normalization/inputs.py` | Version guards currently expect seed list `0.2.0`; update to `0.3.0` and keep taxonomy `0.2.0`. |
| `backend/src/hmde/quality/structural.py` | Replace the `active == 57` membership rule with the active seed-list count. |
| `data/quality/rules-v0.2.0.json` | Quality catalogue version for v0.3.0; membership rule references the active seed-list count. |
| `data/quality/exceptions-v0.3.0.json` | Approved v0.3.0 exception baseline after the quality run. |
| `data/classifications/tag-map-v0.1.0.json` | Reuse if the new tags need no mapping changes; otherwise create a reviewed v0.3.0 tag map. |
| `data/classifications/manual-overrides-v0.1.0.json` | Reuse if no new medium-confidence album overrides are required; otherwise create a reviewed version. |
| `backend/src/hmde/api/routes/producers.py` | Overview and ego-graph caps; change only after measurement. |
| `docs/03-data/seed-list.md` | Record v0.3.0 composition, verification method and limitations. |
| `docs/00-vision/roadmap.md` | Record E13 progress and the E12 pause. |
| `specs/README.md`, `AGENTS.md`, `data/README.md` | Keep the index, current state and data inventory accurate. |
| `backend/tests/`, `frontend/` tests | Update corpus/version assertions and validate the pipeline and product. |

## 4. Technical decisions and alternatives

### 4.1 Decision — accept all 453 candidates

E13 closes on 509 verified active bands: the 57 current bands plus 452 accepted candidates. The owner approved the full pool on 2026-11-17; T-002 excluded Hellhammer because it has no studio album. The former 200-band target and 143-band selection are superseded.

**Rationale:** the owner wants the complete candidate set in the database. The pool already covers all leaves and regions; verifying all candidates is simpler and more complete than maintaining a separate selection step.

### 4.2 Decision — verify all candidates and exclude failures

Every candidate is checked against the final leaf and regional composition in [spec.md](spec.md#fr-002--verified-final-distribution). The final composition is a consequence of verifying 452 candidates, not a selection target. A candidate that fails the album, source or country check is excluded and reported with the reason; it is never silently replaced. Hellhammer is the only exclusion.

**Rationale:** accepting the full pool keeps the owner's scope while preserving the existing evidence rules. The exclusion policy prevents invalid bands from entering the corpus without inventing a replacement.

### 4.3 Decision — three batch artifacts of 151, 151 and 150 bands

The 452 accepted additions are recorded as `151 + 151 + 150`. The batch artifacts are the approval unit and the input to the v0.3.0 seed list.

**Rationale:** three batches preserve the existing approval model and batch IDs. The size is large because the owner approved the full pool, not a stratified subset.

### 4.4 Decision — MusicBrainz for data, URL relationships and published sources for relevance

MusicBrainz remains the source for identity, country and releases. Published relevance is verified through MusicBrainz `url-rels` to Wikidata/Wikipedia first, with Discogs and AllMusic as fallbacks. WDQS is not a dependency because the initial enrichment hit `HTTP 429: Aggressively rate-limiting to 1 req / min`.

**Rationale:** it avoids a slow and rate-limited SPARQL dependency while keeping a published source and a stable identifier for every accepted band. T-002 recorded 430 Wikidata QIDs, 14 Wikipedia URLs, 19 Discogs sources and 4 AllMusic sources.

### 4.5 Decision — no new schema or API contract

No database migration or API contract change is planned. The graph cap is the only possible behavioural change; it is decided after measurement in T-009.

**Rationale:** the data model already supports versioned datasets, taxonomy membership and multiple analysis runs. A migration would add risk without evidence.

### 4.6 Decision — exclude multi-artist release groups and make E3 deterministic

The canonical E3 dataset contains one row per artist, release group, release and recording MBID. A release group associated with more than one active band is excluded with reason `multi_artist_release_group`, together with dependent rows that become orphaned. Every NDJSON file uses a total deterministic order, including a tie-breaker for records with equal primary keys. The coverage report distinguishes extracted records from canonical dataset rows.

**Rationale:** the current release-group model stores one artist per album, so attributing a split album to one band would create a false producer–band relationship. Excluding and reporting the seven groups keeps the model correct without a schema change. Deterministic ordering is required for cache-only replay to produce the same dataset version.

### 4.7 Alternatives considered

| Alternative | Reason for rejection |
|---|---|
| Expand beyond 510 bands | Out of scope; the owner accepted the 453-candidate pool, not a larger corpus. |
| Select only 143 of the 453 candidates | Rejected by the owner on 2026-11-17; the full pool is the accepted scope. |
| Use an unverified subset or top-N | Would discard accepted candidates without a reason and preserve the current bias. |
| Change taxonomy to add leaves | Taxonomy v0.2.0 is fixed; a taxonomy change is a separate spec and ADR. |
| Automatically match names with fuzzy search | Violates the deterministic identity rule and risks wrong bands. |
| Keep the 57-band hardcode | Breaks quality and membership validation at 509. |
| Raise the graph cap immediately | The 1,000/2,000 cap will truncate at 509 bands; keep explicit truncation unless measurements justify a bounded raise. |
| Attribute a multi-artist release group to one canonical artist | Misattributes split albums and creates false producer–band relationships; excluded instead. |
| Add a `release_group_artist` association now | Correct long-term, but it requires a schema migration, API change and separate spec/ADR; out of scope for E13. |
| Add a new data source for missing credits | Out of scope; source expansion requires a separate decision. |

## 5. Data model and migrations

No new tables, columns, constraints or indexes are planned. No Alembic migration is expected.

The existing model already supports:

- versioned seed-list membership (`seed_list_version`, `added_in_version`, batch IDs);
- dataset and normalization runs;
- quality rule/exception versions;
- analysis and network run versions.

Artifact changes are file-based:

- new candidate verification and batch files;
- new seed list v0.3.0;
- new quality rule and exception versions;
- new dataset, normalization, quality and analysis outputs.

If implementation proves a migration is required, stop and record the reason in the spec before adding it. The migration must apply from an empty database and downgrade cleanly.

## 6. API contract

No endpoint, request schema, response schema or status-code change is planned.

The existing overview endpoint keeps `view`, `producer_limit`, `producer_sort`, `order`, `decade`, `subgenre`, `include_isolated`, `include_evidence`, `layout`, `max_nodes` and `max_edges`. The frontend keeps its current routes and query keys.

The only possible change is the server-side default cap or the frontend request limit for the overview. That decision is made in T-009 with measured node and edge counts. If a cap changes, update the API tests and the performance documentation; do not change the response shape.

OpenAPI and TypeScript types should be unchanged. Regenerate them only if the implementation changes a schema or endpoint.

## 7. Frontend impact

Expected impact: none in code.

The current `/graph` page must be exercised with the v0.3.0 analysis run. Verify:

- initial overview load and view switch;
- producer top-k and sort controls;
- decade and leaf filters;
- isolated-producer toggle;
- band and album views;
- producer ego-graph navigation;
- loading, error and empty states;
- keyboard access and the accessible table alternative.

If the measured overview exceeds the cap, prefer keeping the cap and showing explicit truncation over a UI rewrite. A cap or limit change must preserve the route, query keys and accessibility behaviour. Run the existing Vitest, Playwright and axe suites; add a focused regression test only if the cap or truncation behaviour changes.

## 8. Error handling and consistency

- **Candidate verification failure:** reject the candidate and record the reason; do not substitute an unverified band silently.
- **Multi-artist release group:** exclude the group and orphaned dependent rows; report `multi_artist_release_group`; do not choose one artist.
- **Non-deterministic dataset output:** fail the verification check when normal and cache-only runs produce different NDJSON or manifest; fix the ordering rather than accepting the run.
- **MusicBrainz 4xx/5xx or timeout:** retry with `Retry-After`, preserve the error in the ingestion report and fail the band; a failed band blocks dataset publication.
- **Cache miss in `--cache-only`:** fail the band and report it; no network fallback.
- **Interrupted E3 run:** rerun with the same seed list and raw cache; do not publish a partial dataset.
- **Normalization ambiguity:** quarantine and review; no automatic fuzzy merge.
- **Missing tag mapping:** quarantine or add a reviewed mapping; never invent a leaf.
- **Quality blocker:** fix the cause or add an approved exception with a reason and scope.
- **Graph cap exceeded:** return the documented bounded view; do not silently return an unbounded graph.
- **Partial analysis run:** do not point the API or frontend at an incomplete run.

Seed-list creation is append-only. The active pointer moves only after seed-list validation. Historical files are read-only. Database writes remain transactional per run.

## 9. Security and trust boundaries

No authentication or authorization change. The application remains read-only.

- Keep the MusicBrainz User-Agent and one-request-per-second limit.
- Use public Wikipedia/Wikidata APIs with a descriptive User-Agent and bounded requests.
- Do not commit credentials, tokens or personal data.
- Validate all polled JSON before writing canonical artifacts.
- Keep raw responses and provenance; do not edit raw files by hand.
- Do not bypass source rate limits or scrape sources whose terms prohibit it.
- Keep secrets in environment variables; no new secret is expected.

## 10. Observability

Record for every stage:

- candidate pool version and verification report;
- seed-list version and batch IDs;
- dataset ID, manifest, checksums, entity counts and multi-artist exclusion counts;
- normalization run ID and membership counts;
- quality run ID, rule version, exception version and finding counts;
- EDA report ID and network run ID;
- API/frontend performance measurements.

No new tracing or metrics stack is needed. Existing run records and reports are the source of truth. Log the selected analysis run in the frontend performance procedure.

## 11. Testing strategy

| Level | What is tested | Evidence |
|---|---|---|
| Unit | Seed-list schema, 509 bands, append-only membership, final distribution, version guards, dynamic quality membership rule, E3 total ordering, entity uniqueness, multi-artist exclusion, 1,000/2,000 cap helpers | `backend/tests/unit/` |
| Integration | E3 dataset/manifest/cache replay, E4 memberships/classifications, E5 findings/exceptions, E6/E7 run persistence | `backend/tests/integration/` |
| Contract | API responses unchanged for band, album, producer, overview and ego endpoints | `backend/tests/integration/test_api_*` |
| Frontend | Existing routes, graph controls, loading/error states and accessibility | `frontend/src/**/*.test.tsx` |
| End-to-end | `/bands`, `/albums`, `/producers`, `/graph`, `/search` against E2E data | `frontend/e2e/` |
| Manual | Selection review, coverage review, graph-cap decision, report review | `tasks.md` evidence |

Exact commands:

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run --env-file ../.env pytest
```

```bash
cd frontend
npm run lint
npm run typecheck
npm run test
npm run build
npm run test:e2e
npm run test:perf
```

`npm run test:e2e` requires the migrated and seeded `hmde_e2e` database and starts the API on 8011 and Vite on 5183. `npm run test:perf` requires the local v0.2.0/v0.3.0 stack and `HMDE_ANALYSIS_RUN`.

## 12. Deployment and reversibility

There is no production deployment. The work is local and versioned.

Order:

1. Validate the candidate verification and batch files.
2. Write the v0.3.0 seed list and validate it.
3. Run E3 and verify the dataset before normalization.
4. Run E4 and verify memberships before quality.
5. Run E5 and review exceptions before analysis.
6. Run E6/E7 and verify reports.
7. Load the analysis run and run product checks.
8. Update the pointer only after seed-list validation.

Rollback:

- Point `data/seed-list.json` back to `v0.2.0.json`.
- Keep the v0.3.0 dataset and reports as historical artifacts; do not delete them.
- If a code change breaks the pipeline, revert the code and rerun from the last valid dataset.
- No database migration rollback is expected.

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Wikidata/Wikipedia lookup is slow or rate-limited | Prefer MusicBrainz URL relationships, then bounded Wikipedia API calls; record unresolved candidates as rejected, not guessed. |
| Accepted pool over-represents familiar US/UK bands | Record the final 40.1% US/UK share; do not add a selection step that silently drops accepted candidates. |
| 509-band ingestion exceeds the local batch window | Use the existing cache, retry and resume behaviour; record actual duration; do not lower the target silently. |
| NDJSON order changes between identical runs | Use a total deterministic order with a tie-breaker; assert normal and cache-only parity in tests. |
| Multi-artist release groups cannot be represented | Exclude them with `multi_artist_release_group` and report dependent-row counts; do not assign them to one artist. |
| Graph cap is exceeded at 509 bands | Measure first; keep explicit truncation with documented counts unless a bounded raise is justified and tested. |
| New MusicBrainz tags have no mapping | Review and version the tag map; quarantine unmapped records. |
| Quality findings explode at 509 bands | Triage by rule; fix structural causes; approve exceptions only with reasons and scope. |
| Historical data is accidentally changed | Checksum v0.2.0 files before and after; append-only writes; pointer-only switch. |
| Storage growth | Record raw and extracted sizes; prune only disposable caches with explicit authorization. |
| Scope creep into E12 | Keep deployment, TLS, runbooks and release work out of SPEC-016. |

## 14. Traceability requirements → plan → tasks

| Requirement | Plan section | Tasks |
|---|---|---|
| FR-001 | 4.2, 4.4 | T-002 |
| FR-002 | 4.2 | T-001, T-002 |
| FR-003 | 4.3 | T-002 |
| FR-004 | 5, 8, 12 | T-003 |
| FR-005 | 2, 4.6, 8, 10 | T-005, T-005A |
| FR-006 | 3, 8 | T-004, T-006 |
| FR-007 | 3, 8 | T-004, T-007 |
| FR-008 | 2, 10 | T-008 |
| FR-009 | 6, 7 | T-009 |
| FR-010 | 10 | T-003, T-005, T-005A, T-006, T-007, T-008 |
| FR-011 | 3 | T-010 |
| FR-012 | 1, 5, 12 | T-010 |
| NFR-001 | 5, 12 | T-005, T-005A, T-008 |
| NFR-002 | 9 | T-002, T-005 |
| NFR-003 | 10, 13 | T-005, T-005A, T-008 |
| NFR-004 | 5, 13 | T-005, T-005A |
| NFR-005 | 6, 7 | T-009 |
| NFR-006 | 3, 5 | T-004, T-006 |
| NFR-007 | 3 | T-004, T-006 |
| AC-001 | 4.2 | T-002 |
| AC-002 | 4.2, 4.3 | T-001, T-002 |
| AC-003 | 5, 12 | T-003 |
| AC-004 | 2, 4.6, 8 | T-005, T-005A |
| AC-005 | 3, 8 | T-006 |
| AC-006 | 3, 8 | T-007 |
| AC-007 | 2, 10 | T-008 |
| AC-008 | 6, 7 | T-009 |
| AC-009 | 11 | T-010 |
| AC-010 | 3 | T-010 |
| AC-011 | 1, 12 | T-010 |

## 15. Approval and next step

The owner approved the 510-band ceiling, all 453 candidates, the three-batch structure and the exclusion policy on 2026-11-17. T-001 recorded approval; T-002 verified all 453 candidates, accepted 452, excluded Hellhammer and created batches of 151/151/150. The owner approved the verification report and batches on 2026-11-17. T-003 created the 509-band v0.3.0 seed list and moved the active pointer after validation. T-004 made the pipeline guards data-driven.

T-005 executed on 2026-11-19 with 509/509 bands and zero failures, but its dataset was not accepted: cache-only replay was non-deterministic and seven multi-artist release groups produced duplicate entity MBIDs. The owner approved option A on 2026-11-19. T-005A completed: dataset `mb-20261119T004940Z-9d5e75fdc1b9` has 509/509 bands, zero failures, no duplicate entity MBIDs, seven reported multi-artist exclusions and the same dataset version/manifest in normal and cache-only runs. T-006 is next.
