# E11 integration, QA and performance report

- **Status:** Implemented; remote CI passed; documentation closure pending
- **Stage:** E11
- **Date:** 2026-11-16
- **Owner:** Cristian
- **Spec:** [SPEC-014](../../specs/014-integration-qa/spec.md)
- **Plan:** [SPEC-014 plan](../../specs/014-integration-qa/plan.md)
- **Tasks and evidence:** [SPEC-014 tasks](../../specs/014-integration-qa/tasks.md)
- **Scope:** Playwright critical flows, deterministic E2E data, performance, accessibility, security and backup restore for the read-only v0.2.0 application

## 1. Summary and release recommendation

E11 adds an integration and QA layer around the existing application without changing the API contract, schema, migrations, ingestion rules or product behavior. The local evidence supports proceeding to E12: the 26-test Playwright suite, axe scans, keyboard and reduced-motion checks, security review, restore drill and full backend/frontend regression passed. No P1 or P2 defect remains open.

The evidence also records one accepted performance exception, nine moderate development-only dependency advisories and several non-blocking observations. The GitHub Actions `e2e` job passed in remote run 43895517746 on commit 4985ad8. Branch-protection enforcement remains a repository setting that cannot be verified locally, and documentation closure is pending.

**Recommendation:** conditional go to E12 after the `e2e` job is marked as a required check. Do not describe E11 as fully validated until that repository setting is confirmed.

## 2. Changes introduced by E11

- Added Playwright and axe as development dependencies and the `test:e2e` and `test:perf` scripts.
- Added `frontend/playwright.config.ts` and `frontend/playwright.performance.config.ts`.
- Added the deterministic seed at `backend/tests/e2e/seed.py`.
- Added the E2E suite under `frontend/e2e/` with shared console and navigation helpers.
- Added the `e2e` job to `.github/workflows/ci.yml`.
- Scoped Vitest to `src/**/*.{test,spec}.{ts,tsx}` so it does not collect Playwright specs.
- Darkened the shared `--muted` token from `#66736d` to `#5a6661` to meet the contrast baseline.
- Added Playwright report, trace and test-result directories to `frontend/.gitignore`.
- Added this report and updated the roadmap, README, `AGENTS.md`, frontend documentation and SDD index.

No production dependency was added. No file under `backend/src/`, `backend/alembic/` or `openapi.json` changed, and no API, schema, migration or user-visible behavior change was introduced.

## 3. Environment and data

### 3.1 Reference environment

| Item | Value |
|---|---|
| Machine | AMD Ryzen 5 5600G, 12 CPUs, 15,788 MB RAM, Linux |
| Node.js | 20.19.2 |
| npm | 9.2.0 |
| Browser | Chromium 159.0.8154.6 (Playwright 1.65.1) |
| Viewport | 1440×900 |
| Stack | Local development Docker Compose |
| API | `http://localhost:8001` |
| Web | `http://localhost:5173` |
| Database | PostgreSQL 16 on port 5434 |

### 3.2 Corpus and versioned identifiers

| Item | Value |
|---|---|
| Dataset | `mb-20261107T194927Z-0d6cedd5c261` |
| Normalization run | `54d66992-643b-49ec-bac4-fe514ea39e94` |
| Analysis run | `91f39a30-fa51-4d75-a9a2-1b5605bd98c3` |
| Analysis version | `net-a0b7c1f41ac5c92d` |
| Taxonomy | `0.2.0` |
| Graph version | `0.1.0` |
| Overview | 398 band-view nodes / 426 edges; 968 album-view nodes / 1,134 edges |

### 3.3 Deterministic E2E data

The E2E seed uses the historical `data/fixtures/e2` fixture set and the existing network builders. It writes only to a database whose name contains `e2e` and reuses fixed run identifiers, so reruns do not duplicate data.

| Item | Value |
|---|---|
| Database | `hmde_e2e` |
| Seed analysis run | `159752fd-fdf7-4dce-8c5d-fc6ffb7bf8d5` |
| Seed analysis version | `net-a86d9d9691ba6230` |
| Artists | 94 |
| Release groups | 41 |
| Credits | 859 |
| Taxonomy nodes | 23 |
| Graph nodes | 82 |
| Graph edges | 89 |

The seed returned `reused=true` on its second run with identical counts. It refused a database name without `e2e`. The E2E fixture exposes 14 bands, 41 albums and 37 producers through the API.

## 4. Commands

These commands reproduce the evidence. Run them from the repository root unless a working directory is shown.

### 4.1 Install

```bash
cd frontend
npm ci
npx playwright install --with-deps chromium
```

### 4.2 Prepare the disposable E2E database

```bash
cd backend
export DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde_e2e
uv run alembic upgrade head
uv run python -m tests.e2e.seed
```

### 4.3 Run E2E

```bash
cd frontend
npm run test:e2e
CI=true npm run test:e2e
```

Playwright starts the API on `127.0.0.1:8011` and Vite on `127.0.0.1:5183` and points them at `hmde_e2e`. It does not reuse an existing server. In CI it uses one worker and one retry.

### 4.4 Run the performance probe

The development stack with the v0.2.0 corpus and the recorded analysis run must already be running.

```bash
cd frontend
HMDE_WEB_BASE_URL=http://localhost:5173 \
HMDE_API_BASE_URL=http://localhost:8001 \
HMDE_ANALYSIS_RUN=91f39a30-fa51-4d75-a9a2-1b5605bd98c3 \
  npm run test:perf
```

The probe writes and attaches `performance-report.json` under the Playwright test output. The report is regenerated on every run and is not committed.

### 4.5 Run the regression

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run --env-file ../.env pytest

cd ../frontend
npm run lint
npm run typecheck
npm run test
npm run build

cd ..
docker compose config -q
```

`pytest` without the environment file skips the database integration tests. The E11 regression used the environment file and ran 332 tests.

## 5. End-to-end results

The suite contains 26 tests in Chromium:

| Suite | Tests | Coverage |
|---|---:|---|
| `smoke.spec.ts` | 1 | Application shell and API health |
| `explorer.spec.ts` | 5 | Band list, search, taxonomy and decade filters, band detail, album list/detail and credits, producer list/search/detail, cross-entity search |
| `graph.spec.ts` | 5 | Overview bands/albums views, panels, accessible tables, top-k and sorting, isolated toggle, filters, layouts, engines, node details, ego views, role filter and physics controls |
| `states.spec.ts` | 6 | Empty, not-found, retried API 500, truncated overview and ego graphs, reduced motion, keyboard navigation |
| `accessibility.spec.ts` | 9 | axe scans on nine routes |
| **Total** | **26** | |

Results:

- The full suite passed with five parallel workers in 1.8 minutes and in CI mode with one worker in 1.1 minutes.
- The explorer and graph suites passed twice consecutively. The state suite also passed twice. The combined 15-test state and accessibility run passed, including all nine axe scans.
- A deliberately broken critical-flow spec exited with code 1 and produced screenshot, video and trace artifacts. The temporary spec was removed.
- Application console errors fail a test. The only filtered message is the pre-existing `/favicon.ico` 404.
- The graph tests assert a visible canvas, status text or accessible table after load; they do not use fixed sleeps for graph completion.
- The E2E subgenre filter exercises the empty state because the historical fixtures contain no album taxonomy classifications. This is a fixture limitation, not evidence that the production corpus has no subgenres.

The suite is order-independent, starts each test from a known route and never calls MusicBrainz or another external service.

## 6. Performance

The probe runs one warm-up plus 20 measured samples per API endpoint and browser path. It discards warm-up samples, reports min, p50, p95 and max in the attached JSON, and records the environment and versions above.

### 6.1 API p95

Values show the range across two consecutive runs. The server-side target from FR-006 is in the last column.

| Endpoint | p95 range (ms) | Target (ms) | Result |
|---|---:|---:|---|
| Bands list | 9.31–13.90 | 300 | Pass |
| Albums list | 20.60–26.18 | 300 | Pass |
| Producers list | 43.42–112.39 | 300 | Pass |
| Band detail | 19.57–22.90 | 300 | Pass |
| Album detail | 8.00–10.76 | 300 | Pass |
| Producer detail | 30.02–118.75 | 300 | Pass |
| Search | 9.19–9.26 | 300 | Pass |
| Ego graph, depth 2, `max_nodes=500` | 30.67–32.08 | 1,000 | Pass |
| Overview, bands view | 152.50–161.92 | 1,500 | Pass |
| Overview, albums view | 188.62–208.34 | 1,500 | Pass |

### 6.2 Browser timings

| Path or control | p95 range (ms) | Target (ms) | Result |
|---|---:|---:|---|
| `/graph` albums view, interactive canvas | 2,744.09–3,042.66 | 5,000 | Pass |
| Ego graph, interactive canvas | 508.71–545.38 | 5,000 | Pass |
| Overview view switch acknowledgement | 1,145.88–1,153.50 | 1,000 | **Exception** |
| Overview view switch data and canvas settled | 1,238.14–1,250.38 | 5,000 | Pass, context metric |
| Overview Index panel toggle | 667.56–684.06 | 1,000 | Pass |

The view-switch exception has a recorded cause: the 968-node d3-force simulation and the view refetch occupy the main thread while the new view commits. The full switch still settles within the 5-second graph-interactivity target. This is accepted as a P3 observation and does not block E12.

Control measurements use a direct DOM click and wait for the control's acknowledged state. Playwright locator actionability is excluded because it waits for layout stability while d3-force animates; the full settle time is recorded separately.

### 6.3 Graph health and finite layouts

- 20–22 long tasks over 500 ms were observed, with a maximum of 642 ms.
- CoSE completed in 12.8 s and fCoSE in 1.5 s on the overview.
- There was no blank canvas, unhandled error or frozen page.
- No v0.2.0 producer ego graph reaches the 500-node cap. The probe samples the largest depth-2 graph among the ten most credited producers, Scott Burns, with 35 nodes and 52 edges, using `max_nodes=500`. This is a representative bounded measurement, not a 500-node worst case.
- The performance probe is not a CI gate for v0.1.

## 7. Accessibility

### 7.1 Automated axe results

axe ran with the `wcag2a`, `wcag2aa`, `wcag21a` and `wcag21aa` tags after each route reached its loaded state.

| Route | Critical | Serious | Result |
|---|---:|---:|---|
| `/bands` | 0 | 0 | Pass |
| Band detail | 0 | 0 | Pass |
| `/albums` | 0 | 0 | Pass |
| Album detail | 0 | 0 | Pass |
| `/producers` | 0 | 0 | Pass |
| Producer detail | 0 | 0 | Pass |
| `/producers/:id/graph` | 0 | 0 | Pass |
| `/graph` | 0 | 0 | Pass |
| `/search?q=Iron` | 0 | 0 | Pass |

The only accessibility fix required was the shared muted text token. It changed from `#66736d` to `#5a6661`, raising contrast on the paper background from 4.12:1 to 4.98:1.

### 7.2 Manual keyboard, focus and reduced-motion checklist

| Check | Result | Evidence |
|---|---|---|
| Skip link moves focus to `#main-content` | Pass | `states.spec.ts` keyboard test |
| Primary navigation is reachable and operable by keyboard | Pass | Bands, albums and graph navigation via focus and Enter |
| Search and filter inputs have labels and are keyboard operable | Pass | `getByLabel` search and filter checks |
| Graph view, panel and engine controls are reachable | Pass | View switch, Index toggle and CoSE selection by keyboard |
| Graph controls expose pressed state | Pass | `aria-pressed` on view and engine buttons |
| Accessible node and edge tables are reachable and readable | Pass | Disclosure control plus Tab reaches the table wrapper; captions and column headers present |
| Focus is visible on all interactive elements | Pass | Global 3 px oxide `:focus-visible` outline; skip link becomes visible on focus |
| Each route has a level-one heading | Pass | axe route precondition and page checks |
| Landmarks distinguish navigation and main content | Pass | `aside` site navigation, labelled primary `nav` and `main#main-content` |
| Tables use captions and column headers | Pass | Credits, albums-by-producer, bands-by-producer and graph fallback tables |
| Panels toggle without losing keyboard access | Pass | Index/Details buttons with expanded state; panel removal reflected in the DOM |
| Reduced motion freezes force layouts | Pass | “Layout frozen · d3-force”; Freeze disabled and Resume enabled on both graphs |
| Empty, not-found and API-error states keep focusable next actions | Pass | Retry button and route links in `states.spec.ts` |

This is an automated and scripted keyboard review, not a screen-reader certification or a third-party WCAG audit. No critical or serious automated violation remains open.

## 8. Security and dependency review

| Check | Result | Evidence |
|---|---|---|
| CORS origins are explicit and configurable | Pass | `backend/src/hmde/main.py:31`; default local origins in `backend/src/hmde/core/config.py:71` |
| Only GET is allowed by CORS | Pass | Allowed-origin GET echoes the origin; POST preflight advertises only `GET`; unlisted origins receive no allow-origin header |
| Credentials are not allowed | Pass | `allow_credentials=False` |
| API is read-only | Pass | All 20 OpenAPI paths expose GET only; `POST /api/v1/bands` returns 405; no write call in the service layer |
| Query parameters are bounded | Pass | Lists 1–200, search 1–200 and limit 1–50, text filters 50/200 characters, years 1960–2026, graph limits 1–1000/1–500 and edges 1–2000 |
| Invalid input is rejected | Pass | Invalid limits and missing search terms return 422 |
| Secrets are not tracked | Pass | `.env` is ignored and untracked; only `.env.example` is tracked; secret grep found no matches |
| Test artifacts contain no secrets or PII | Pass | No `.env`, database URL, token, key or private data found in reports, screenshots or traces |
| Production frontend dependencies are clean | Pass | `npm audit --omit=dev --audit-level=high` reported 0 vulnerabilities |
| Development frontend dependencies are triaged | Accepted P3 | Full audit reports 9 moderate `minimatch` advisories under ESLint/typescript-eslint; no high or critical |
| Backend dependencies are clean | Pass | `uvx pip-audit` and the project environment `pip-audit` reported no known vulnerabilities; local `hmde-backend` was skipped because it is unpublished |
| TLS and proxy security headers | Deferred | Release prerequisite for E12; not an application-layer gap in E11 |

The `minimatch` advisory chain is development-only. `npm audit fix --force` would downgrade `typescript-eslint`, so the finding is accepted with owner Cristian and a target of the next tooling upgrade.

## 9. Backup and restore drill

The drill dumped the development database in custom format, restored it into the temporary `hmde_restore_e11` database and compared all public table counts. The source database was not modified or deleted.

| Step | Duration |
|---|---:|
| `pg_dump -Fc` | 2.382 s |
| `createdb` | 2.594 s |
| `pg_restore --exit-on-error` | 13.687 s |
| Cleanup | 0.644 s |
| **Total** | **19.308 s** |

| Item | Value |
|---|---|
| Public tables | 38 |
| Source rows | 186,370 |
| Dump size | 10,666,598 bytes |
| Alembic revision | `0007` |
| Restored table counts | 38 of 38 matched exactly |
| Source counts before/after | Identical |
| Temporary database | Dropped |
| Dump file | Removed |
| Other databases | `hmde_e2e` and `hmde_test` untouched |

Key counts included `artist` 1,212, `release_group` 731, `credit` 33,524, `normalization_run` 3, `quality_run` 4, `quality_finding` 232, `quality_exception` 58, `analysis_run` 1, `graph_node` 982 and `graph_edge` 1,577. The procedure and timings are the basis for the E12 restore runbook.

## 10. Defects and known issues

No P1 or P2 defect is open. The following P3 observations are accepted, documented and do not block E11 closure.

| ID | Severity | Issue | Owner | Target |
|---|---|---|---|---|
| E11-01 | P3 | Overview view-switch acknowledgement p95 is 1.15 s against the 1 s control target; the full 968-node switch settles in 1.25 s, within the 5 s graph target | Cristian | E13 graph performance review |
| E11-02 | P3 | Nine moderate development-only `minimatch` advisories in the ESLint/typescript-eslint chain; no production impact | Cristian | Next tooling upgrade |
| E11-03 | P3 | Vite warns that the main JS chunk is 958.20 kB (291.26 kB gzip), above the 500 kB warning threshold | Cristian | E13 performance review |
| E11-04 | P3 | `npm ci` emits an `EBADENGINE` warning for `@redocly/openapi-core` because npm 9.2.0 is below its declared `>=9.5.0`; install and generation still pass | Cristian | Next tooling upgrade |
| E11-05 | P3 | The pre-existing `/favicon.ico` 404 is filtered from headless console checks; it is not introduced by E11 | Cristian | E12 |
| E11-06 | Observation | The E2E subgenre filter can only assert the empty state because the historical E2 fixtures have no album taxonomy classifications | Cristian | E13 corpus expansion |
| E11-07 | Observation | Two local Vitest runs under CPU contention hit the 5 s per-test timeout in 6 and 1 tests respectively; the isolated file and a quiet full rerun passed 118/118. No product assertion failed | Cristian | E12 test stabilization |

Release gates that are not defects:

- The GitHub Actions `e2e` job must pass remotely and be marked as a required check. It was validated locally, including failure behavior, but no push was authorized.
- TLS and reverse-proxy security headers remain E12 prerequisites.

## 11. Acceptance criteria evidence

| Criterion | Result | Evidence |
|---|---|---|
| AC-001 | Pass | Two seed runs with matching counts and `reused=true` |
| AC-002 | Pass | 26 Playwright tests in Chromium; explorer and graph suites passed twice |
| AC-003 | **Partial; remote run passed** | Remote CI run 43895517746 passed on commit 4985ad8; the `e2e` job is not yet confirmed as a required branch-protection check |
| AC-004 | Pass | Attached performance report with environment, versions, samples, min, p50, p95 and max |
| AC-005 | Pass with exception | All targets met except view-switch acknowledgement, documented with cause |
| AC-006 | Pass | axe: zero critical or serious violations on nine routes |
| AC-007 | Pass | Manual checklist in section 7.2 |
| AC-008 | Pass | Security checklist in section 8; no open critical or high finding |
| AC-009 | Pass | 38 of 38 table counts matched; cleanup succeeded; source unchanged |
| AC-010 | Pass | This report |
| AC-011 | Pass | No P1/P2 defect; P3 list in section 10 |
| AC-012 | Pass | Backend 332 tests, Ruff and format; frontend lint, typecheck, 118 tests and build; Compose config |
| AC-013 | Pass | Development-only dependencies; no backend application, schema, migration or OpenAPI change |
| AC-014 | Pass | Roadmap, README, AGENTS, frontend docs, SDD index and SPEC-014 updated |

## 12. Residual risks and E12 prerequisites

- The `e2e` job passed remotely in run 43895517746. Branch protection must make it required; otherwise the gate is advisory.
- The performance evidence comes from one local machine. It is reproducible but not a production capacity claim.
- The 968-node overview has a main-thread cost during view switches. It is usable but remains the largest known interaction cost.
- TLS, reverse-proxy headers and the production restore runbook are E12 deliverables, not E11 gaps.
- The security review is a bounded application review, not a penetration test.

## 13. References and artifacts

- [SPEC-014](../../specs/014-integration-qa/spec.md)
- [SPEC-014 plan](../../specs/014-integration-qa/plan.md)
- [SPEC-014 tasks and raw evidence](../../specs/014-integration-qa/tasks.md)
- [CI workflow](../../.github/workflows/ci.yml)
- [Playwright configuration](../../frontend/playwright.config.ts)
- [Performance configuration](../../frontend/playwright.performance.config.ts)
- [E2E suite](../../frontend/e2e)
- [Deterministic E2E seed](../../backend/tests/e2e/seed.py)
- [Frontend documentation](frontend.md)
- [Roadmap](../00-vision/roadmap.md)

Local Playwright reports, traces, screenshots, videos and `performance-report.json` are generated under `frontend/playwright-report` and `frontend/test-results`. They are ignored by Git and should be uploaded as CI artifacts, not committed.

## 14. SPEC-019 v0.3.0 full-corpus performance review

The SPEC-019 probe ran on 2026-11-20 against analysis run `613a597e-242c-44ab-add3-a95381d23ec3` (`net-78a54051ff047f86`), dataset `mb-20261119T004940Z-9d5e75fdc1b9`, in Chromium 159.0.8154.6 at 1440×900.

### 14.1 API p95

| Endpoint | p95 (ms) | Target (ms) | Result |
|---|---:|---:|---|
| Bands list | 14.03 | 300 | Pass |
| Albums list | 56.66 | 300 | Pass |
| Producers list | 244.03 | 300 | Pass |
| Band detail | 9.50 | 300 | Pass |
| Album detail | 9.03 | 300 | Pass |
| Producer detail | 169.46 | 300 | Pass |
| Search | 12.47 | 300 | Pass |
| Ego graph, depth 2, `max_nodes=2000` | 156.11 | 1,000 | Pass |
| Overview, all bands (`1708` nodes) | 1,033.89 | 1,500 | Pass |
| Overview, default 500 albums (`1944` API nodes; `1401` visible) | 1,029.65 | 1,500 | Pass |
| Overview, all albums (`3719` nodes) | 1,195.87 | 2,000 | Pass |

### 14.2 Browser timings

| Measurement | p95 (ms) | Target (ms) | Result |
|---|---:|---:|---|
| `/graph` all bands navigation | 3,949.26 | 5,000 | Pass |
| `/graph` default 500-album navigation | 4,270.49 | 5,000 | Pass |
| `/graph` all-albums navigation | 6,042.23 | 5,000 | Exception, explicit view |
| View-switch acknowledgement | 1,426.14 | 1,000 | Exception |
| View-switch data and canvas settled | 1,598.22 | 5,000 | Pass |
| Index panel toggle | 654.04 | 1,000 | Pass |
| Ego graph navigation | 851.30 | 5,000 | Pass |

The browser timings above were recorded with the API returning 1,944 default-album nodes; revision 2 now draws 1,401 visible nodes after hiding producers outside the selected subgraph, so the recorded default-album timing is conservative. The overview defaults to the server-generated static bipartite layout for both bands and albums; Force remains an explicit opt-in. Producers with degree zero in the selected subgraph are hidden by default and can be revealed with “Show isolated producers”. Revision 2 also keeps node selection from recreating the graph. The all-bands and default-album views meet the five-second interaction target. The explicit all-albums view remains above target at 6.04 s and is accepted as the measured large-graph exception. The view-switch acknowledgement remains a P3 interaction cost: it refetches and remounts the overview but settles in 1.60 s, within the five-second graph target. With 1,944 nodes, CoSE did not complete within 30 s and fCoSE completed in 34.1 s when Force was explicitly selected; both remain documented finite-layout observations.

### 14.3 Graph health and truncation

- All bands: 509 bands, 1,708 nodes / 1,700 edges, untruncated at `max_nodes=5000` / `max_edges=5000`.
- Default albums: 500 albums, 1,944 API nodes / 1,717 edges, 1,775 albums omitted intentionally. The canvas hides 543 producers outside the selected subgraph, so 1,401 nodes are visible by default.
- All albums: 2,275 graph albums, 3,719 nodes / 4,217 edges, untruncated at the 5,000 cap.
- The overview band index pages the list endpoint to all 509 rows.
- The network has 4,217 producer–album edges, 1,700 producer–band edges and 325 communities.

The performance probe is not a CI gate. Its JSON report is generated under `frontend/test-results` and is ignored by Git. The full regression passed: 27 Playwright tests in Chromium, including nine axe route scans; 346 backend and 127 frontend tests; lint, typecheck and build passed.
