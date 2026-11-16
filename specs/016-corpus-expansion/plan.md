# Technical plan — SPEC-016

- **Status:** Draft
- **Spec:** [spec.md](spec.md)
- **Tasks:** [tasks.md](tasks.md)
- **ADRs:** [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md), [ADR-0002](../../docs/01-architecture/adr/ADR-0002-musicbrainz-primary-source.md)
- **Module:** `ingestion`, with `normalization`, `quality`, `analytics`, `api` and `web` verification

## 1. Solution summary

Expand the active corpus from 57 to 200 bands using the existing versioned seed-list, E3 ingestion, E4 normalization, E5 quality, E6/E7 analysis and read-only API. The work is data growth plus the smallest code changes required to remove hardcoded corpus assumptions.

The expansion is split into three approved batches of 50, 50 and 43 bands. The selection is drawn from the 397-band candidate pool at `data/seed-lists/candidates/v0.3.0-pool.json`, which already covers all 17 taxonomy leaves and six regions. Selection is stratified by leaf and region; the final 143 bands require owner approval.

The v0.3.0 seed list keeps all 57 v0.2.0 bands active and appends the approved bands. A new dataset, normalization run, quality run, EDA report and network snapshot are produced. The v0.2.0 dataset and all historical artifacts remain unchanged.

Explicitly not included: the 500-band target, E12 deployment, production infrastructure, a taxonomy revision, new sources, a new credit model, automatic fuzzy identity resolution and a UI redesign.

## 2. Architecture and data flow

```text
candidate pool (397)
        │
        ▼
owner-approved selection (143) ──► 3 batch artifacts (50 + 50 + 43)
        │
        ▼
seed list v0.3.0 (200 active) ──► active pointer
        │
        ▼
E3 MusicBrainz ingestion ──► raw cache + dataset + manifest
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
| `data/seed-lists/candidates/v0.3.0-pool.json` | Versioned 397-band candidate pool; input to selection, not an approved seed list. |
| `data/seed-lists/candidates/v0.3.0-selection.json` | Selection report with accepted/rejected candidates, reasons and target checks. Created by T-002. |
| `data/seed-lists/batches/v0.3.0-batch-01.json` | First approved 50-band batch. |
| `data/seed-lists/batches/v0.3.0-batch-02.json` | Second approved 50-band batch. |
| `data/seed-lists/batches/v0.3.0-batch-03.json` | Third approved 43-band batch. |
| `data/seed-lists/v0.3.0.json` | Append-only 200-band seed list with all 57 v0.2.0 bands retained. |
| `data/seed-list.json` | Active-version pointer; moves to v0.3.0 only after validation. |
| `backend/src/hmde/etl/musicbrainz/seed.py` | Existing data-driven v2 seed-list loader; extend only if a real validation gap appears. |
| `backend/src/hmde/normalization/inputs.py` | Version guards currently expect seed list `0.2.0`; update to `0.3.0` and keep taxonomy `0.2.0`. |
| `backend/src/hmde/quality/structural.py` | Replace the `active == 57` membership rule with the active seed-list count. |
| `data/quality/rules-v0.2.0.json` | Quality catalogue version for v0.3.0; membership rule references the active seed-list count. |
| `data/quality/exceptions-v0.3.0.json` | Approved v0.3.0 exception baseline after the quality run. |
| `data/classifications/tag-map-v0.1.0.json` | Reuse if the new tags need no mapping changes; otherwise create a reviewed v0.3.0 tag map. |
| `data/classifications/manual-overrides-v0.1.0.json` | Reuse if no new medium-confidence album overrides are required; otherwise create a reviewed version. |
| `backend/src/hmde/api/routes/producers.py` | Overview and ego-graph caps; change only after measurement. |
| `docs/03-data/seed-list.md` | Record v0.3.0 composition, selection method and limitations. |
| `docs/00-vision/roadmap.md` | Record E13 progress and the E12 pause. |
| `specs/README.md`, `AGENTS.md`, `data/README.md` | Keep the index, current state and data inventory accurate. |
| `backend/tests/`, `frontend/` tests | Update corpus/version assertions and validate the pipeline and product. |

## 4. Technical decisions and alternatives

### 4.1 Decision — 200 bands first, 500 later

E13 closes on 200 active bands. The seed list, pipeline and analyses are rebuilt at that scale. A later spec can repeat the process to 500 with the same batch mechanism.

**Rationale:** 200 is large enough to validate the architecture and patterns, small enough to review and ingest locally, and 397 candidates already provide more than the 143 additions required.

### 4.2 Decision — stratified selection, not top-N

Selection follows the target leaf and regional distributions in [spec.md](spec.md#fr-002--approved-target-distribution). The target leaf table is authoritative; regional targets are floors that yield to leaf coverage when verified candidates are insufficient.

**Rationale:** a simple top-N by popularity would preserve the current US/UK and genre bias and would leave `nwobhm`, `stoner-metal`, `sludge-metal` and `djent` uncovered.

### 4.3 Decision — three batch artifacts

The 143 additions are recorded as `50 + 50 + 43`. The batch artifacts are the approval unit and the input to the v0.3.0 seed list.

**Rationale:** the existing seed list and E3 pipeline already understand batch IDs. Smaller approval units make review and rejection cheaper.

### 4.4 Decision — MusicBrainz for data, MusicBrainz URL relationships and Wikipedia for relevance

MusicBrainz remains the source for identity, country and releases. Published relevance is verified through MusicBrainz `url-rels` to Wikidata/Wikipedia first, then the Wikipedia API. WDQS is not a dependency because the initial enrichment hit `HTTP 429: Aggressively rate-limiting to 1 req / min`.

**Rationale:** it avoids a slow and rate-limited SPARQL dependency while keeping a published source and a stable identifier for every selected band.

### 4.5 Decision — no new schema or API contract

No database migration or API contract change is planned. The graph cap is the only possible behavioural change; it is decided after measurement in T-009.

**Rationale:** the data model already supports versioned datasets, taxonomy membership and multiple analysis runs. A migration would add risk without evidence.

### 4.6 Alternatives considered

| Alternative | Reason for rejection |
|---|---|
| Expand directly to 500 | Too large for one review and local ingestion cycle; 200 validates the process first. |
| Use all 397 candidates | Produces an unbalanced corpus, duplicates the current bias and exceeds the target. |
| Change taxonomy to add leaves | Taxonomy v0.2.0 is fixed; a taxonomy change is a separate spec and ADR. |
| Automatically match names with fuzzy search | Violates the deterministic identity rule and risks wrong bands. |
| Keep the 57-band hardcode | Breaks quality and membership validation at 200. |
| Raise the graph cap immediately | No measured evidence; could hide a product regression. |
| Add a new data source for missing credits | Out of scope; source expansion requires a separate decision. |

## 5. Data model and migrations

No new tables, columns, constraints or indexes are planned. No Alembic migration is expected.

The existing model already supports:

- versioned seed-list membership (`seed_list_version`, `added_in_version`, batch IDs);
- dataset and normalization runs;
- quality rule/exception versions;
- analysis and network run versions.

Artifact changes are file-based:

- new candidate selection and batch files;
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

- candidate pool version and selection report;
- seed-list version and batch IDs;
- dataset ID, manifest and checksums;
- normalization run ID and membership counts;
- quality run ID, rule version, exception version and finding counts;
- EDA report ID and network run ID;
- API/frontend performance measurements.

No new tracing or metrics stack is needed. Existing run records and reports are the source of truth. Log the selected analysis run in the frontend performance procedure.

## 11. Testing strategy

| Level | What is tested | Evidence |
|---|---|---|
| Unit | Seed-list schema, 200 bands, append-only membership, target distributions, version guards, dynamic quality membership rule, 1,000/2,000 cap helpers | `backend/tests/unit/` |
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

1. Validate the candidate selection and batch files.
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
| Selection bias toward familiar US/UK bands | Enforce the target leaf and regional distributions; review deviations in the selection report. |
| 200-band ingestion exceeds the local batch window | Use the existing cache, retry and resume behaviour; record actual duration; do not lower the target silently. |
| Graph cap is exceeded at 200 bands | Measure first; keep explicit truncation or raise the cap with a documented exception and tests. |
| New MusicBrainz tags have no mapping | Review and version the tag map; quarantine unmapped records. |
| Quality findings explode at 200 bands | Triage by rule; fix structural causes; approve exceptions only with reasons and scope. |
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
| FR-005 | 2, 8, 10 | T-005 |
| FR-006 | 3, 8 | T-004, T-006 |
| FR-007 | 3, 8 | T-004, T-007 |
| FR-008 | 2, 10 | T-008 |
| FR-009 | 6, 7 | T-009 |
| FR-010 | 10 | T-003, T-005, T-006, T-007, T-008 |
| FR-011 | 3 | T-010 |
| FR-012 | 1, 5, 12 | T-010 |
| NFR-001 | 5, 12 | T-005, T-008 |
| NFR-002 | 9 | T-002, T-005 |
| NFR-003 | 10, 13 | T-005, T-008 |
| NFR-004 | 5, 13 | T-005 |
| NFR-005 | 6, 7 | T-009 |
| NFR-006 | 3, 5 | T-004, T-006 |
| NFR-007 | 3 | T-004, T-006 |
| AC-001 | 4.2 | T-002 |
| AC-002 | 4.2, 4.3 | T-001, T-002 |
| AC-003 | 5, 12 | T-003 |
| AC-004 | 2, 8 | T-005 |
| AC-005 | 3, 8 | T-006 |
| AC-006 | 3, 8 | T-007 |
| AC-007 | 2, 10 | T-008 |
| AC-008 | 6, 7 | T-009 |
| AC-009 | 11 | T-010 |
| AC-010 | 3 | T-010 |
| AC-011 | 1, 12 | T-010 |

## 15. Approval and next step

This plan and `tasks.md` require owner approval before implementation. The first executable task is T-001 (approve the target and criteria), followed by T-002 (select the 143 bands). No seed-list or pipeline write happens before T-002 approval.
