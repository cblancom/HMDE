# Technical plan — SPEC-014 Integration, QA and performance

- **Status:** Implemented
- **Validation:** Local evidence complete; remote CI run 43895517746 passed; required-check setting and documentation closure pending.
- **Spec:** [spec.md](spec.md)
- **Tasks:** [tasks.md](tasks.md)
- **Stage:** E11
- **Modules:** `platform`, `api`, `web`
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0003](../../docs/01-architecture/adr/ADR-0003-synchronous-sqlalchemy.md), [ADR-0006](../../docs/01-architecture/adr/ADR-0006-read-only-api.md)

## 1. Solution summary

SPEC-014 adds an integration and QA layer around the existing application without changing product behavior. The layer has five parts:

1. A Playwright Chromium suite over a deterministic, disposable PostgreSQL database seeded from the historical E2 fixtures plus a generated analysis run.
2. A CI job that provisions PostgreSQL, migrates, seeds, starts the API and web server and runs the E2E suite.
3. A Playwright-based performance probe that samples API and browser timings against the local v0.2.0 corpus and writes a reproducible report.
4. An accessibility audit using axe plus a manual keyboard/focus/reduced-motion checklist.
5. A security and dependency review plus a `pg_dump`/`pg_restore` drill recorded in a single QA report.

No production endpoint, schema, migration, ingestion rule, analysis output or UI behavior is added. Stable test selectors may be added when the current accessible selectors are insufficient. Deployment, TLS, proxy headers and production runbooks remain in E12.

## 2. Architecture and data flow

```text
GitHub Actions / local shell
        │
        ├── PostgreSQL service ──► alembic upgrade head
        │                              │
        │                              ▼
        │                    backend/tests/e2e/seed.py
        │                    (E2 fixtures + network builders)
        │                              │
        │                              ▼
        │                    deterministic E2E database
        │                              │
        │              ┌───────────────┴───────────────┐
        │              ▼                               ▼
        │        FastAPI :8001                 Vite :5173
        │              │                               │
        │              └───────────────┬───────────────┘
        │                              ▼
        │                    Playwright Chromium
        │              explorer · graph · a11y · states
        │                              │
        │                              ▼
        │                 HTML report + traces/screenshots

Local Docker Compose (v0.2.0 corpus)
        │
        ├── FastAPI :8001 ──► API performance samples (p50/p95)
        └── Vite :5173 ─────► browser route and interaction timings
                                      │
                                      ▼
                         docs/01-architecture/qa-report.md
```

The E2E path is isolated from the performance path. E2E uses a small deterministic fixture database and is the CI gate. Performance uses the real local v0.2.0 corpus and is a reported measurement, not a CI gate.

## 3. Components and responsibilities

| Component or path | Responsibility |
|---|---|
| `frontend/package.json`, `frontend/package-lock.json` | Add `@playwright/test` and `@axe-core/playwright` as development dependencies and the E2E/performance scripts. |
| `frontend/playwright.config.ts` | Start API and web servers for E2E, set the base URL, trace/screenshot policy, retries and Chromium project. |
| `frontend/playwright.performance.config.ts` | Run the performance project against an already running local stack without starting servers. |
| `frontend/e2e/explorer.spec.ts` | Band, album, producer and search critical flows. |
| `frontend/e2e/graph.spec.ts` | Overview and ego graph flows, layouts, engines, filters and accessible table. |
| `frontend/e2e/states.spec.ts` | Empty, not-found, error, truncated and reduced-motion states. |
| `frontend/e2e/accessibility.spec.ts` | axe scans and keyboard/focus checks. |
| `frontend/e2e/performance.spec.ts` | API and browser samples; attaches the performance JSON to the Playwright report. |
| `backend/tests/e2e/seed.py` | Idempotent deterministic E2E seed using the E2 fixtures and the existing network builders. |
| `.github/workflows/ci.yml` | Add the `e2e` job with PostgreSQL, migrations, seed, Playwright install and report artifacts. |
| `docs/01-architecture/qa-report.md` | Single source for E2E, performance, accessibility, security, restore evidence, known issues and release recommendation. |
| `README.md`, `AGENTS.md`, `docs/00-vision/roadmap.md`, `specs/README.md`, `docs/01-architecture/frontend.md` | E11 status, commands and next-step documentation. |

## 4. Technical decisions and alternatives

### 4.1 Playwright with Chromium only

Playwright is already the project convention for end-to-end tests and is named in the roadmap. Chromium is the CI browser for v0.1; Firefox and WebKit are deferred to avoid a browser matrix without a release requirement.

| Alternative | Reason for rejection |
|---|---|
| Cypress | Not the documented convention; Playwright already covers browser and API request contexts. |
| Manual test script only | Not repeatable and not a CI gate. |
| Chromium, Firefox and WebKit now | Triples CI time without a v0.1 requirement. |

### 4.2 Deterministic E2E database

The E2E job uses a dedicated database seeded from `data/fixtures/e2`. The seed loads the historical catalog fixtures and creates one normalization/quality/analysis run through the same network builders used by integration tests. This keeps the graph routes real without relying on live ingestion or ignored local corpus data.

| Alternative | Reason for rejection |
|---|---|
| Live MusicBrainz ingestion | Network-dependent, slow, rate-limited and non-deterministic. |
| Local ignored v0.2.0 corpus | Not available in CI and not reproducible from a clean checkout. |
| Mock every API response | Does not verify the frontend/API/database integration. |
| Start a separate mock server | Adds a second contract that can drift. |

The seed must refuse to run unless the target database name contains `e2e` and must never read or write the development database.

### 4.3 CI E2E job

The existing CI has backend and frontend jobs. SPEC-014 adds a third `e2e` job that provisions PostgreSQL, runs migrations and the seed, installs Chromium, starts the API and web server through Playwright `webServer`, and runs the suite. The job publishes the HTML report and traces on failure.

| Alternative | Reason for rejection |
|---|---|
| Run E2E only locally | No regression gate for pull requests. |
| Add E2E to the existing frontend job | Mixes unit and browser concerns and makes failures harder to diagnose. |
| Docker Compose inside CI | Slower and less deterministic than service containers and direct processes. |

### 4.4 Performance probe with Playwright

The performance probe is a separate Playwright project. It uses `request` samples for API endpoints and browser navigation for `/graph` and the ego graph. It is not a stress test: it runs warm-up plus at least 20 sequential samples and reports p50/p95. This avoids adding k6, Locust or another runtime.

| Alternative | Reason for rejection |
|---|---|
| k6 or Locust | Extra dependency and operational surface for a small MVP. |
| Backend-only timing | Misses canvas, layout and interaction cost. |
| CI performance gate | Shared runners are too variable for a release threshold. |

### 4.5 Accessibility with axe plus manual checks

axe catches structural violations; the manual checklist covers keyboard order, focus visibility, graph control access, panel behavior and reduced motion. Automated scans alone are not sufficient for WCAG 2.1 AA.

| Alternative | Reason for rejection |
|---|---|
| Automated scan only | Misses keyboard and interaction barriers. |
| Full third-party audit | Outside v0.1 scope and not required for E11. |
| No automated scan | Regressions would be hard to detect. |

### 4.6 Backup restore in a temporary database

The drill uses `pg_dump` and `pg_restore` inside the Compose database container, restores into a temporary database and compares key row counts. The source database is never dropped or modified.

| Alternative | Reason for rejection |
|---|---|
| Restore over the development database | Destructive and against the project boundaries. |
| Use a production database | No production environment exists before E12. |
| Skip the restore test | E11 explicitly requires recovery evidence. |

## 5. Data model and migrations

- No new or modified tables, columns, constraints, indexes or migrations.
- The E2E seed writes only to the disposable `hmde_e2e` database.
- The seed reuses the existing E2 fixture loader and network builder APIs.
- The performance run reuses the existing v0.2.0 database and analysis run.
- The restore drill copies the development database into a temporary database and removes it afterwards.

## 6. API contract

- No endpoint, request schema, response schema, status code or pagination behavior changes.
- The E2E suite exercises the existing `/api/v1` contract through the real API.
- The OpenAPI drift check remains part of backend CI.
- The performance probe records endpoint paths and query parameters but does not add a public API.

## 7. Frontend impact

- Playwright and axe are development-only dependencies.
- No user-visible behavior changes.
- Stable selectors may be added where the current accessible labels are ambiguous; role, label and text selectors remain preferred.
- The E2E suite uses Chromium at a desktop viewport plus one narrow viewport for responsive checks.
- The performance project reuses the existing routes and does not add hidden UI.
- Accessibility fixes discovered by E11 are limited to markup, focus, labels or ARIA corrections; they do not add features.

## 8. Error handling and consistency

- **Database down or migration failure:** the seed and Playwright startup fail before tests run and the report shows the startup error.
- **Seed rerun:** the seed is idempotent; it loads the same deterministic fixture records and does not duplicate the analysis run.
- **Port conflict:** Playwright reuses an existing server only outside CI; CI always starts fresh servers and fails on an occupied port.
- **Test failure:** one retry in CI with trace, screenshot and video on the first failure; two consecutive local passes are required during review.
- **Missing fixture or graph data:** the test fails with the route and response status instead of silently skipping.
- **Performance variance:** warm-up samples are discarded; the report includes sample count, min, p50, p95 and max.
- **Restore failure:** the drill aborts before touching the source database and records the failing command.
- **Audit/network failure:** the report records the limitation and the manual review performed; it is not presented as a pass.

## 9. Security and trust boundaries

- E2E and performance data are public fixture or v0.2.0 corpus data; no personal data is introduced.
- The E2E database is disposable and local/CI-only.
- No secret, token or `.env` content is printed or attached to reports.
- The security review checks CORS origins, allowed methods, input validation, bounded parameters, read-only routes and dependency advisories.
- `npm audit --omit=dev --audit-level=high` and `uvx pip-audit` are reported commands; neither becomes a project dependency.
- Security headers at the reverse proxy are deferred to E12 and recorded as a release prerequisite.
- Test artifacts are retained as CI artifacts, not committed to the repository.

## 10. Observability

- Playwright HTML report, traces and screenshots for failed E2E tests.
- Performance JSON attached to the performance Playwright report and summarized in the QA report.
- axe results summarized by route and rule in the QA report.
- Security and dependency output summarized by command and severity.
- Restore drill command, duration and row-count comparison in the QA report.
- No new production logging, metrics or tracing is added.

## 11. Testing strategy

| Level | What is tested | Evidence |
|---|---|---|
| E2E explorer | Bands, albums, producers, search, filters, details and navigation | `frontend/e2e/explorer.spec.ts` |
| E2E graph | Overview, ego graph, layouts, engines, filters, table and details | `frontend/e2e/graph.spec.ts` |
| E2E states | Empty, not-found, API error, truncated and reduced motion | `frontend/e2e/states.spec.ts` |
| Accessibility | axe WCAG 2.1 A/AA and keyboard/focus checks | `frontend/e2e/accessibility.spec.ts` |
| Performance | API p50/p95 and browser load/interaction timings | `frontend/e2e/performance.spec.ts` |
| Security | CORS, secrets, validation, read-only and dependency review | QA report and audit commands |
| Restore | `pg_dump`/`pg_restore` into a temporary database | QA report |
| Regression | Existing backend and frontend suites | Existing commands |

Exact commands:

```bash
# Install
cd frontend
npm ci
npx playwright install --with-deps chromium

# Deterministic E2E database
cd ../backend
export DATABASE_URL=postgresql+psycopg://hmde:hmde_dev@localhost:5434/hmde_e2e
uv run alembic upgrade head
uv run python tests/e2e/seed.py

# E2E
cd ../frontend
npm run test:e2e

# Performance (local stack with the v0.2.0 corpus already running)
HMDE_API_BASE_URL=http://localhost:8001 \
HMDE_WEB_BASE_URL=http://localhost:5173 \
HMDE_ANALYSIS_RUN=<analysis-run-id> \
  npm run test:perf

# Regression
cd ../backend
uv run ruff check .
uv run ruff format --check .
uv run pytest

cd ../frontend
npm run lint
npm run typecheck
npm run test
npm run build

cd ..
docker compose config -q
```

## 12. Deployment and reversibility

- No migrations or production configuration changes.
- The CI job is additive and can be removed without affecting the application.
- The E2E database and temporary restore database are disposable.
- Playwright and axe are development dependencies and can be removed without a production impact.
- E12 owns production deployment, TLS, reverse proxy, backups and rollback.

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| E2E flakes on layout or animation timing | Use explicit state waits, reduced-motion and static-layout tests, and one retry with traces. |
| Fixture data drifts from the real corpus | Keep E2E assertions structural (routes, counts, labels), not dependent on corpus-wide totals. |
| The E2E job exceeds the CI budget | Chromium only, one worker in CI, focused critical flows and a 15-minute job timeout. |
| Performance numbers vary by machine | Record environment and spread; use p95 and warm samples; allow documented exceptions. |
| axe false positives | Triage by rule and route; record accepted findings with a reason. |
| Security review becomes a pen test | Keep the checklist bounded to configuration, validation, secrets and advisories. |
| Restore drill damages data | Enforce a temporary database and a name guard; never drop or overwrite the development database. |
| Test-only selectors leak into product code | Prefer roles and labels; add `data-testid` only where accessible selectors are not stable. |
| The QA report becomes stale | Record commands and artifact links; update it in the same change as the evidence. |

## 14. Traceability requirements → plan → tasks

| Requirement | Plan section | Tasks |
|---|---|---|
| FR-001 | 4.2, 6, 7 | T-001, T-002 |
| FR-002 | 4.1, 7, 11 | T-003, T-004, T-005 |
| FR-003 | 4.2, 8, 11 | T-002, T-010 |
| FR-004 | 4.3, 11, 12 | T-010 |
| FR-005 | 4.4, 10, 11 | T-006 |
| FR-006 | 4.4, 11 | T-006 |
| FR-007 | 4.5, 11 | T-005, T-009 |
| FR-008 | 9, 11 | T-007 |
| FR-009 | 4.6, 11 | T-008 |
| FR-010 | 3, 10, 11 | T-009 |
| FR-011 | 8, 13 | T-009 |
| FR-012 | 3, 11 | T-009 |
| NFR-001 | 4.2, 8 | T-002, T-010 |
| NFR-002 | 4.3, 13 | T-010 |
| NFR-003 | 4.1, 4.5, 12 | T-001 |
| NFR-004 | 5, 6, 7 | T-010, T-009 |
| NFR-005 | 9 | T-007 |
| NFR-006 | 4.5 | T-005 |
| NFR-007 | 4.4, 10 | T-006 |
| NFR-008 | 8 | T-003, T-004, T-005 |

## 15. Approval and next step

The spec, plan and tasks are drafted for owner review. Implementation is not authorized until the owner approves all three artifacts and the two supporting changes:

- `@playwright/test` and `@axe-core/playwright` as development dependencies;
- the new CI `e2e` job.

After approval, T-001 and T-002 start the E2E harness. T-003–T-005 build the browser coverage, T-006–T-008 run the performance, security and restore checks, T-010 adds the CI job and T-009 closes the QA report and project status.
