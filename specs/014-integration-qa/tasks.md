# Tasks — SPEC-014 Integration, QA and performance

- **Status:** Implemented
- **Validation:** Local evidence complete; remote CI pending.
- **Spec:** [spec.md](spec.md)
- **Plan:** [plan.md](plan.md)

## 1. Execution order

```text
T-001 ─► T-002 ─┬─► T-003 ─┐
                ├─► T-004 ─┼─► T-010 ─► T-009
                └─► T-005 ─┘             ▲
T-006 ───────────────────────────────────┤
T-007 ───────────────────────────────────┤
T-008 ───────────────────────────────────┘
```

T-001 and T-002 establish the harness and deterministic data. T-003, T-004 and T-005 can run in parallel once the seed exists. T-006, T-007 and T-008 can run in parallel with browser coverage. T-010 adds the CI job and full regression run. T-009 closes the QA report and documentation after every check has evidence.

## 2. Tasks

### T-001 — Add Playwright, axe and browser configuration

- **Status:** Completed.
- **Requirements:** FR-001, NFR-003, AC-002, AC-006.
- **Dependencies:** Owner approval of the SPEC-014 dependencies; SPEC-014 approved.
- **Description:** Add `@playwright/test` and `@axe-core/playwright` as development dependencies. Add `frontend/playwright.config.ts` with Chromium, a desktop viewport, one retry in CI, trace/screenshot/video on failure, and `webServer` entries for the API and Vite. Add `frontend/playwright.performance.config.ts` for an already running local stack. Add `test:e2e` and `test:perf` scripts. Add a focused configuration smoke test that opens `/bands` and asserts the page shell.
- **Done when:** Playwright starts both servers from the configured commands, the smoke test passes, and no production dependency changes.
- **Verification:**
  ```bash
  cd frontend
  npm ci
  npx playwright install --with-deps chromium
  npm run test:e2e -- --grep "page shell"
  npm run lint
  npm run typecheck
  ```
- **Files:** `frontend/package.json`, `frontend/package-lock.json`, `frontend/playwright.config.ts`, `frontend/playwright.performance.config.ts`, `frontend/e2e/smoke.spec.ts`.
- **Evidence:** 2026-11-14 — `npm run test:e2e -- e2e/smoke.spec.ts` passed (1 test, 5.5 s) with Chromium 1255. `npm run lint` and `npm run typecheck` passed. Added `@playwright/test@1.65.1` and `@axe-core/playwright@4.13.0` as development dependencies; 4.14 requires Node 22 and was rejected to preserve Node 20. E2E uses dedicated API port 8011 and web port 5183. No production dependency changed.

### T-002 — Add the deterministic E2E seed

- **Status:** Completed.
- **Requirements:** FR-001, FR-003, NFR-001, NFR-008, AC-001.
- **Dependencies:** T-001.
- **Description:** Add `backend/tests/e2e/seed.py` with a CLI that loads `data/fixtures/e2`, creates one deterministic normalization/quality/analysis run through the existing network builders and prints the analysis run id. Guard the command so it only runs against a database whose name contains `e2e`. Make reruns idempotent. Add a short usage section to the QA report or the backend test documentation rather than a new standalone guide.
- **Done when:** two consecutive seed runs produce the same record counts and the graph endpoints return data for the seeded analysis run.
- **Verification:**
  ```bash
  cd backend
  export DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde_e2e
  uv run alembic upgrade head
  uv run python tests/e2e/seed.py
  uv run python tests/e2e/seed.py
  ```
- **Files:** `backend/tests/e2e/seed.py`, `backend/tests/e2e/__init__.py` if required, `README.md` or QA report usage note.
- **Evidence:** 2026-11-14 — `DATABASE_URL=.../hmde_e2e uv run python tests/e2e/seed.py` ran twice. Both runs returned `analysis_run_id=159752fd-fdf7-4dce-8c5d-fc6ffb7bf8d5`, `analysis_version=net-a86d9d9691ba6230` and `reused=true` on the second run. Counts: 94 artists, 41 release groups, 859 credits, 23 taxonomy nodes, 82 graph nodes and 89 graph edges. `/health`, `/api/v1/bands` and `/api/v1/graph/producers` returned 200. The seed refuses databases whose name does not contain `e2e`.

### T-003 — Add explorer end-to-end flows

- **Status:** Completed.
- **Requirements:** FR-002, FR-003, NFR-008, AC-002.
- **Dependencies:** T-002.
- **Description:** Add Playwright tests for the band list, search, taxonomy/period filters, band detail, album detail, producer detail, album list/detail and cross-entity search. Use accessible roles, labels and known fixture entities. Assert navigation, expected headings, counts or empty states, and absence of application console errors.
- **Done when:** the explorer suite passes twice consecutively and covers every explorer flow in FR-002.
- **Verification:**
  ```bash
  cd frontend
  npm run test:e2e -- e2e/explorer.spec.ts
  npm run test:e2e -- e2e/explorer.spec.ts
  ```
- **Files:** `frontend/e2e/explorer.spec.ts`, test helpers under `frontend/e2e/support/`.
- **Evidence:** 2026-11-14 — `npm run test:e2e -- e2e/explorer.spec.ts` passed twice consecutively (5 tests each, 9.2 s and 9.0 s) against the seeded `hmde_e2e` database and Chromium 1255. Coverage: band list with 14 bands, text search, taxonomy filter (2 heavy-metal bands), decade filter (8 bands in the 1990s), band detail with graph canvas, album list/detail with credits, producer list/search/detail and cross-entity global search. `frontend/e2e/support/console.ts` fails tests on application console errors while ignoring the pre-existing favicon 404.

### T-004 — Add graph end-to-end flows

- **Status:** Completed.
- **Requirements:** FR-002, FR-003, NFR-008, AC-002, AC-005.
- **Dependencies:** T-002.
- **Description:** Add Playwright tests for `/graph` and `/producers/:id/graph`. Cover bands/albums views, producer top-k, decade/subgenre filters, isolated toggle, Force/Bipartite/Community layouts, d3-force/CoSE/fCoSE engines, node details, the accessible table and ego physics controls. Assert the canvas is present and the status text or table reflects completion; avoid fixed sleeps where a state wait works.
- **Done when:** both graph routes pass in Chromium with deterministic data and no blank canvas or unhandled error.
- **Verification:**
  ```bash
  cd frontend
  npm run test:e2e -- e2e/graph.spec.ts
  npm run test:e2e -- e2e/graph.spec.ts
  ```
- **Files:** `frontend/e2e/graph.spec.ts`, `frontend/e2e/support/`.
- **Evidence:** 2026-11-14 — `npm run test:e2e -- e2e/graph.spec.ts` passed twice consecutively (5 tests each, 13.9 s and 13.6 s) against the seeded `hmde_e2e` database. Coverage: overview bands (42 nodes/30 edges/28 producers) and albums (77/59/37) views, collapsible panels, accessible node/edge tables, top-10 producers (16/9/8), album/band/betweenness/name sorting, ascending order (15/8), isolated-producer hiding, producer highlight, 1990s filter (20/13), subgenre empty state, Force/Bipartite/Community layouts, d3-force/CoSE/fCoSE engines, selected producer/band/album details, and the Scott Burns ego graph (3/2 bands, 5/4 albums, 6/5 at depth 2) with fallback tables, role filtering and freeze/resume/reheat controls. The subgenre filter returns an empty state because the E2E fixture has no album taxonomy classifications; the test records that limitation instead of asserting absent data as negative evidence.

### T-005 — Add state, reduced-motion and accessibility checks

- **Status:** Completed.
- **Requirements:** FR-002, FR-007, NFR-006, AC-006, AC-007.
- **Dependencies:** T-002.
- **Description:** Add Playwright tests for empty, not-found, API-error, truncated and reduced-motion states. Add axe scans for `/bands`, band detail, `/albums`, album detail, `/producers`, producer detail, `/producers/:id/graph`, `/graph` and `/search` with WCAG 2.1 A/AA tags. Add keyboard checks for the navigation, filters, tabs/panels, graph controls and accessible table.
- **Done when:** axe reports zero critical or serious violations on the main routes and the state/reduced-motion tests pass.
- **Verification:**
  ```bash
  cd frontend
  npm run test:e2e -- e2e/states.spec.ts e2e/accessibility.spec.ts
  ```
- **Files:** `frontend/e2e/states.spec.ts`, `frontend/e2e/accessibility.spec.ts`, `frontend/e2e/support/`.
- **Evidence:** 2026-11-14 — `npm run test:e2e -- e2e/states.spec.ts e2e/accessibility.spec.ts` passed (15 tests, 20.5 s) and the state suite also passed twice consecutively (6 tests each, 18.7 s and 17.4 s). Coverage: empty band/album/producer/search states, not-found band/album/producer/page states, a retried API 500, truncated overview and ego graphs, reduced-motion frozen d3-force layouts, keyboard skip link, navigation, filters, graph tabs/panels, engine controls and accessible tables. Axe scans with WCAG 2.1 A/AA tags pass on nine routes with zero critical or serious violations. The only fix required was darkening the shared `--muted` token from `#66736d` to `#5a6661`, which raises contrast on the paper background from 4.12:1 to 4.98:1.

### T-006 — Add the performance probe and report

- **Status:** Completed.
- **Requirements:** FR-005, FR-006, NFR-007, AC-004, AC-005.
- **Dependencies:** T-001; local v0.2.0 stack and analysis run.
- **Description:** Add `frontend/e2e/performance.spec.ts` and a `test:perf` script. Sample warm-up plus at least 20 measurements for list, detail, search, ego-graph and overview endpoints. Measure `/graph` and `/producers/:id/graph` navigation, canvas readiness and control response in Chromium. Record corpus version, analysis run, environment and p50/p95/min/max, and attach the JSON result to the Playwright report.
- **Done when:** the probe produces a reproducible report and every FR-006 target is met or explicitly excepted with a cause.
- **Verification:**
  ```bash
  cd frontend
  HMDE_API_BASE_URL=http://localhost:8001 \
  HMDE_WEB_BASE_URL=http://localhost:5173 \
  HMDE_ANALYSIS_RUN=<analysis-run-id> \
    npm run test:perf
  ```
- **Files:** `frontend/e2e/performance.spec.ts`, `frontend/playwright.performance.config.ts`, `frontend/package.json`.
- **Evidence:** 2026-11-14 — `npm run test:perf` passed twice consecutively (2.4 min and 2.3 min) against the local Docker Compose stack. The attached `performance-report.json` records AMD Ryzen 5 5600G, 12 CPUs, 15,788 MB RAM, Node 20.19.2, Chromium 159, 1440×900 viewport, corpus `mb-20261107T194927Z-0d6cedd5c261`, analysis run `91f39a30-fa51-4d75-a9a2-1b5605bd98c3` and graph version `0.1.0`. Each endpoint and browser path used one warm-up plus 20 measured samples. API p95 ranges across the two runs: bands list 9.31–13.9 ms, albums list 20.6–26.18 ms, producers list 43.42–112.39 ms, band detail 19.57–22.9 ms, album detail 8–10.76 ms, producer detail 30.02–118.75 ms, search 9.19–9.26 ms, ego graph 30.67–32.08 ms, overview bands 152.5–161.92 ms and overview albums 188.62–208.34 ms; every API target passed. Browser p95: `/graph` 2744.09–3042.66 ms, ego graph 508.71–545.38 ms, panel toggle 667.56–684.06 ms and full view settle 1238.14–1250.38 ms; all passed. `overview view switch acknowledgement` is the only exception at 1145.88–1153.5 ms versus the 1 s target; cause: the 968-node d3-force simulation and view refetch occupy the main thread while the new view commits. The full switch still settles inside the 5 s interactivity target. CoSE completed in 12.8 s and fCoSE in 1.5 s; 20–22 long tasks over 500 ms were recorded with a 642 ms maximum. No blank canvas or unhandled error occurred. No v0.2.0 producer ego graph reaches 500 nodes; the probe samples the largest depth-2 graph among the ten most credited producers (Scott Burns, 35 nodes and 52 edges) with `max_nodes=500`. `frontend/playwright.performance.config.ts` now pins the reported viewport to 1440×900.
  
### T-007 — Complete the security and dependency review

- **Status:** Completed.
- **Requirements:** FR-008, NFR-005, AC-008.
- **Dependencies:** T-001.
- **Description:** Review CORS configuration and allowed methods, repository secret handling, bounded query validation, read-only routes and dependency advisories. Run `npm audit --omit=dev --audit-level=high` and `uvx pip-audit`. Check that no secret, token, `.env` content or production database content appears in test artifacts. Fix critical/high findings; record proxy-level header work for E12.
- **Done when:** the security checklist is complete and no critical or high finding remains open.
- **Verification:**
  ```bash
  cd frontend
  npm audit --omit=dev --audit-level=high

  cd ../backend
  uvx pip-audit

  cd ..
  git grep -n -I -E "(SECRET|TOKEN|PASSWORD|API_KEY)=" -- ':!*.example' ':!docs/**'
  ```
- **Files:** `docs/01-architecture/qa-report.md`, security checklist section; code only if a blocking finding requires a bounded fix.
- **Evidence:** 2026-11-14 — security checklist complete with no critical or high finding.
  - **CORS and methods:** `backend/src/hmde/main.py:31` adds `CORSMiddleware` only when origins are configured, with `allow_methods=["GET"]` and `allow_credentials=False`. `backend/src/hmde/core/config.py:71` normalizes comma-separated origins and defaults to `http://localhost:5173` and `http://127.0.0.1:5173`. An allowed-origin GET echoes only that origin; a POST preflight returns 400 with `access-control-allow-methods: GET`; an unlisted origin receives no allow-origin header.
  - **Read-only boundary:** all 20 OpenAPI paths expose GET only; `POST /api/v1/bands` returns 405. No authentication or write path exists by design; a service-layer scan found no `commit`, `add`, `delete`, `insert` or `update` writes.
  - **Input validation:** list pagination is 1–200 with `offset >= 0`; search `q` is 1–200 and `limit` 1–50; text filters are capped at 50 or 200 characters; years are 1960–2026; graph depth is 1–2, producer limit 0–1000, nodes 1–1000 (overview) or 1–500 (ego) and edges 1–2000. Invalid limits and missing search terms return 422.
  - **Secrets and artifacts:** `.env` is ignored and untracked; only `.env.example` is tracked. `git grep -n -I -E "(SECRET|TOKEN|PASSWORD|API_KEY)=" -- ':!*.example' ':!docs/**'` found no matches. No key or credential pattern was found in tracked files, and `test-results`/`playwright-report` contain no `.env`, database URL, token or private-key material; E2E artifacts contain only public fixture data.
  - **Dependencies:** `npm audit --omit=dev --audit-level=high` reported 0 vulnerabilities. Full `npm audit --audit-level=high` reported 9 moderate advisories in the dev-only `minimatch` chain under ESLint/typescript-eslint and no high or critical finding; `npm audit fix --force` would downgrade `typescript-eslint`, so the finding is accepted as P3 with owner Cristian and a target of the next tooling upgrade. `uvx pip-audit` and the project-environment `uv run --with pip-audit pip-audit` reported no known vulnerabilities; the local `hmde-backend` package was skipped because it is not published on PyPI.
  - **Deferred:** reverse-proxy security headers and TLS remain E12 prerequisites. No code change was required.

### T-008 — Run the backup and restore drill

- **Status:** Completed.
- **Requirements:** FR-009, AC-009.
- **Dependencies:** Development Compose database with data.
- **Description:** Dump the development database in custom format, create a temporary restore database, restore the dump, compare row counts for the main catalog, normalization, quality, analysis and graph tables, record duration and remove the temporary database. Confirm the development database is unchanged.
- **Done when:** the restore succeeds, key counts match and cleanup succeeds without touching the source database.
- **Verification:**
  ```bash
  docker compose exec -T db pg_dump -U hmde -d hmde -Fc > /tmp/hmde-e11.dump
  docker compose exec -T db createdb -U hmde hmde_restore_e11
  cat /tmp/hmde-e11.dump | docker compose exec -T db pg_restore -U hmde -d hmde_restore_e11
  docker compose exec -T db psql -U hmde -d hmde_restore_e11 -c "SELECT count(*) FROM artist;"
  docker compose exec -T db dropdb -U hmde hmde_restore_e11
  rm /tmp/hmde-e11.dump
  ```
  Compare the same key counts in `hmde` and `hmde_restore_e11`; replace `artist` with the documented key tables.
- **Files:** `docs/01-architecture/qa-report.md`, backup-restore section.
- **Evidence:** 2026-11-14 — the drill ran against the running development Compose database `hmde` and restored into the temporary `hmde_restore_e11` database. The source had 38 public tables, 186,370 rows and Alembic revision `0007`. `pg_dump -Fc` produced a 10,666,598-byte dump in 2.382 s; `createdb` took 2.594 s, `pg_restore --exit-on-error` took 13.687 s and cleanup took 0.644 s (19.308 s total). All 38 table counts matched exactly between source and restore, including `artist` 1,212, `release_group` 731, `credit` 33,524, `normalization_run` 3, `quality_run` 4, `quality_finding` 232, `quality_exception` 58, `analysis_run` 1, `graph_node` 982 and `graph_edge` 1,577. Source counts were identical before and after the drill. The temporary database was dropped, the dump was removed, and `hmde` remained healthy; `hmde_e2e` and `hmde_test` were not touched.

### T-009 — Publish the QA report and close E11 documentation

- **Status:** Completed.
- **Requirements:** FR-010, FR-011, FR-012, NFR-004, AC-010, AC-011, AC-013, AC-014.
- **Dependencies:** T-003, T-004, T-005, T-006, T-007, T-008, T-010.
- **Description:** Write `docs/01-architecture/qa-report.md` with scope, environment, dataset versions, commands, E2E results, performance tables, accessibility findings, security findings, restore evidence, known issues and the release recommendation. Update the roadmap, README, `AGENTS.md`, frontend documentation and SDD index. Confirm no API, schema, migration or production dependency change.
- **Done when:** every acceptance criterion has evidence, no P1/P2 defect remains open, and the E11 status is consistent across the repository.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  npm run build

  cd ../backend
  uv run ruff check .
  uv run ruff format --check .
  uv run pytest

  cd ..
  docker compose config -q
  ```
  plus a documentation link/status review.
- **Files:** `docs/01-architecture/qa-report.md`, `README.md`, `AGENTS.md`, `docs/00-vision/roadmap.md`, `docs/01-architecture/frontend.md`, `specs/README.md`, `specs/014-integration-qa/`.
- **Evidence:** 2026-11-16 — wrote `docs/01-architecture/qa-report.md` with scope, environment, dataset versions, commands, E2E results, performance tables, accessibility and security checklists, restore evidence, known issues, acceptance-criteria evidence and a conditional release recommendation. Updated `README.md`, `AGENTS.md`, `docs/00-vision/roadmap.md`, `docs/01-architecture/frontend.md`, `specs/README.md` and the SPEC-014 spec/plan status. Final checks passed: frontend lint, typecheck, 118 Vitest tests and build; backend Ruff, format and 332 tests with `--env-file ../.env`; `docker compose config -q`; `git diff --check`. An initial combined frontend run timed out under concurrent backend-test load; the isolated file and a clean full rerun passed 118/118. No API, schema, migration or production dependency change was found. The remote `e2e` job and required-check setting remain pending, so E11 is implemented but not fully validated.

### T-010 — Add the CI E2E job and run the full regression

- **Status:** Completed locally; remote CI result pending an authorized push.
- **Requirements:** FR-004, NFR-001, NFR-002, AC-003, AC-012.
- **Dependencies:** T-001, T-002, T-003, T-004, T-005; owner approval for the CI change.
- **Description:** Add an `e2e` job to `.github/workflows/ci.yml` with a PostgreSQL service, backend dependency install, migrations, deterministic seed, frontend dependency install, Chromium install and Playwright execution. Publish the HTML report and traces. Enforce a 15-minute timeout and use one worker in CI. Run the full backend and frontend regression locally.
- **Done when:** the job passes on a pull request, fails on a deliberately broken flow during review, and the complete local regression passes.
- **Verification:**
  ```bash
  # Local full regression
  cd backend
  uv run ruff check .
  uv run ruff format --check .
  uv run pytest

  cd ../frontend
  npm ci
  npm run lint
  npm run typecheck
  npm run test
  npm run build

  cd ..
  docker compose config -q
  ```
  plus the GitHub Actions `e2e` job result.
- **Files:** `.github/workflows/ci.yml`, `frontend/playwright.config.ts`, `backend/tests/e2e/seed.py`, `frontend/vite.config.ts`.
- **Evidence:** 2026-11-14 — added the `e2e` job to `.github/workflows/ci.yml` with a PostgreSQL 16 service for `hmde_e2e`, `uv sync --frozen`, Alembic migration, deterministic seed, `npm ci`, `npx playwright install --with-deps chromium`, `npm run test:e2e`, a 15-minute timeout, one CI worker inherited from the Playwright config, and `playwright-report`/`test-results` artifacts uploaded with `if: always()` for 14 days. `CI=true npm run test:e2e` passed locally with 1 worker (26 tests, 1.1 min) and the earlier 5-worker run passed in 1.8 min, leaving ample margin under the 15-minute job budget. A deliberately broken Playwright spec failed with exit code 1 and produced screenshot, video and trace artifacts, confirming the job command fails on a broken flow. Local full regression: `uv run ruff check .` passed, `uv run ruff format --check .` passed, `uv run --env-file ../.env pytest` passed 332 tests, `npm ci` succeeded, `npm run lint` passed, `npm run typecheck` passed, `npm run test` passed 118 tests, `npm run build` passed and `docker compose config -q` passed. The regression exposed that Vitest was collecting `e2e/*.spec.ts`; `frontend/vite.config.ts` now limits Vitest to `src/**/*.{test,spec}.{ts,tsx}`. No remote CI run was executed because no commit or push was authorized; the `e2e` job result on a pull request remains the only pending T-010 check.

## 3. Coverage matrix

### Functional requirements

| Requirement | Tasks |
|---|---|
| FR-001 | T-001, T-002 |
| FR-002 | T-003, T-004, T-005 |
| FR-003 | T-002, T-010 |
| FR-004 | T-010 |
| FR-005 | T-006 |
| FR-006 | T-006 |
| FR-007 | T-005, T-009 |
| FR-008 | T-007 |
| FR-009 | T-008 |
| FR-010 | T-009 |
| FR-011 | T-009 |
| FR-012 | T-009 |

### Non-functional requirements

| Requirement | Tasks |
|---|---|
| NFR-001 | T-002, T-010 |
| NFR-002 | T-010 |
| NFR-003 | T-001 |
| NFR-004 | T-009, T-010 |
| NFR-005 | T-007 |
| NFR-006 | T-005 |
| NFR-007 | T-006 |
| NFR-008 | T-003, T-004, T-005 |

## 4. Validation evidence

| Criterion | Result | Evidence |
|---|---|---|
| AC-001 | Pass | Two seed runs matched; second returned `reused=true` (T-002) |
| AC-002 | Pass | 26 Playwright tests passed; explorer/graph suites passed twice (T-003–T-005, QA report §5) |
| AC-003 | Pending remote CI | `e2e` job added; CI-mode local run 1.1 min; broken-flow failure produced artifacts (T-010) |
| AC-004 | Pass | Attached report records environment, versions, samples, min/p50/p95/max (T-006, QA report §6) |
| AC-005 | Pass with exception | All targets met except view-switch acknowledgement; cause documented (T-006, QA report §6) |
| AC-006 | Pass | axe: zero critical/serious on nine routes (T-005, QA report §7.1) |
| AC-007 | Pass | Checklist complete (QA report §7.2) |
| AC-008 | Pass | Checklist complete; no critical/high finding (T-007, QA report §8) |
| AC-009 | Pass | 38/38 table counts matched; cleanup succeeded (T-008, QA report §9) |
| AC-010 | Pass | [`qa-report.md`](../../docs/01-architecture/qa-report.md) published |
| AC-011 | Pass | No P1/P2; P3 items recorded (QA report §10) |
| AC-012 | Pass | Backend 332 tests and Ruff/format; frontend lint, typecheck, 118 tests and build; Compose config |
| AC-013 | Pass | Development-only dependencies; no backend application, schema, migration or OpenAPI change |
| AC-014 | Pass | Roadmap, README, AGENTS, frontend docs, SDD index and SPEC-014 updated |

## 5. Notes

- The owner approved the spec, plan, tasks, the two development dependencies and the CI job; implementation is complete locally.
- E2E data is deterministic and must never depend on live MusicBrainz access.
- Performance evidence uses the real v0.2.0 corpus and is not a CI gate.
- Accessibility and security findings are classified; critical/high and P1/P2 items block closure.
- Do not change product behavior, API contracts or the schema to make a test pass.
- Record commands, outputs and artifact links in the QA report and this file when the work is executed.
