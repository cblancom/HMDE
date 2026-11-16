# SPEC-014 — Integration, QA and performance

- **Status:** Implemented
- **Validation:** Local E2E, performance, accessibility, security and restore evidence passed; remote CI pending.
- **Stage:** E11
- **Iteration:** MVP
- **Modules:** `platform`, `api`, `web`
- **Date:** 2026-11-14
- **Depends on:** SPEC-010 validated; SPEC-011, SPEC-012 and SPEC-013 validated at E10 closure on 2026-11-14; development Docker Compose; v0.2.0 corpus for performance evidence
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0003](../../docs/01-architecture/adr/ADR-0003-synchronous-sqlalchemy.md), [ADR-0006](../../docs/01-architecture/adr/ADR-0006-read-only-api.md)
- **Plan:** [plan.md](plan.md)
- **Tasks:** [tasks.md](tasks.md)
- **Conventions:** [Engineering conventions](../../docs/01-architecture/conventions.md)
- **Owner:** Cristian

## Revision history

| Revision | Date | Change |
|---|---|---|
| 1 | 2026-11-14 | Initial draft: E11 integration, QA and performance scope with Playwright, deterministic E2E data, accessibility, security and backup-restore evidence |
| 2 | 2026-11-16 | Implementation complete locally: Playwright suite, E2E seed, performance probe, axe/keyboard checks, CI job, security review, restore drill and QA report. Remote CI pending. |

## 1. Context and problem

E10 closed on 2026-11-14. The read-only application now has a validated entity explorer, a global producer overview, bounded producer ego graphs, alternate layouts and selectable force engines. The remaining release risk is not a missing product capability but the absence of integrated evidence across the complete system.

E11 must answer four questions before E12 deploys v0.1:

- Do the critical user flows still work end to end with deterministic data?
- Does the application meet the documented response and interaction targets with the real v0.2.0 corpus?
- Is the main interface usable with a keyboard and assistive technology at the WCAG 2.1 AA baseline?
- Are the security posture and the database backup/restore path adequate for a small public read-only service?

This spec adds verification, test infrastructure and closure documentation. It does not add product features, API behavior, database schema changes or a deployment target. Deployment, TLS and production runbooks remain in E12.

## 2. Users and actors

- **Analytical user:** follows band, album, producer, search and graph flows and expects them to remain usable and accessible.
- **Maintainer/agent:** runs deterministic end-to-end, performance, accessibility, security and restore checks and records evidence.
- **Release owner:** decides whether E11 is closed and whether v0.1 may proceed to E12.
- **Operator:** uses the restore evidence and procedure as the basis for the E12 runbook.

There are no user accounts, roles or authentication.

## 3. User stories and flows

### US-001 — Verify critical exploration flows

As a maintainer, I want repeatable end-to-end checks over the main routes so that a release regression is caught before deployment.

**Expected flow:**

1. Start a disposable database, apply migrations and load deterministic test data.
2. Start the API and the frontend against that database.
3. Exercise band, album, producer, search and graph flows in a real browser.
4. Fail the run on a broken route, missing data, console error or unexpected empty state.

### US-002 — Measure performance against the real corpus

As a release owner, I want measured API and browser timings with the v0.2.0 corpus so that the documented targets are supported by evidence.

**Expected flow:**

1. Run the development stack with the v0.2.0 corpus and a known analysis run.
2. Sample list, detail, search, ego-graph and overview endpoints after warm-up.
3. Load the overview and ego graph in Chromium and record route, canvas and interaction timings.
4. Publish p50/p95 values, environment details and any exception.

### US-003 — Audit accessibility

As an analytical user who relies on keyboard navigation or assistive technology, I want the main routes and graph controls to meet the WCAG 2.1 AA baseline.

**Expected flow:**

1. Scan the main routes with axe using WCAG 2.1 A/AA rules.
2. Complete a keyboard and focus checklist for navigation, filters, tables, panels and graph controls.
3. Verify reduced-motion behavior.
4. Classify and fix critical or serious findings.

### US-004 — Review security and restore a backup

As a release owner, I want a bounded security review and a successful restore drill so that v0.1 does not ship with an avoidable exposure or an untested recovery path.

**Expected flow:**

1. Review CORS, secrets, input validation, read-only boundaries and dependency advisories.
2. Record findings by severity and fix blocking items.
3. Dump the development database, restore it into a temporary database and compare key row counts.
4. Record the procedure, duration and cleanup.

## 4. Functional requirements

### FR-001 — Playwright harness and deterministic data

Add a Playwright end-to-end harness under `frontend/e2e` that runs against a real API and a disposable PostgreSQL database. The test data must be deterministic, versioned in the repository and independent of live MusicBrainz access. The E2E seed must load the historical E2 fixture set and create the analysis data needed by the graph routes through the existing network builders.

**Verification:** `npm run test:e2e` passes from a clean database; the seed command is idempotent; no request leaves the local stack.

### FR-002 — Critical-flow coverage

The E2E suite covers at least:

- band list, search, taxonomy/period filter, band detail, album detail and producer detail;
- album list, album detail and producer credits;
- producer list, producer detail and the producer ego graph with band/album views and physics controls;
- global overview load, bands/albums views, producer top-k, filters, isolated toggle, Force/Bipartite/Community layouts, d3-force/CoSE/fCoSE engines, details and accessible table;
- cross-entity search;
- empty, not-found, API-error, truncated and reduced-motion states.

**Verification:** each flow has at least one Playwright test with stable selectors and explicit assertions.

### FR-003 — Repeatable and isolated E2E execution

The E2E suite must not depend on execution order or shared mutable state. Each test starts from a known route state, the seed is safe to rerun, and failures retain a trace and screenshot. Retries are limited to one in CI and must not hide a reproducible failure.

**Verification:** two consecutive local runs pass; CI artifacts include the Playwright report and traces for failures.

### FR-004 — E2E CI quality gate

Add an `e2e` job to GitHub Actions that provisions PostgreSQL, applies migrations, seeds deterministic data, starts the API and web server and runs Playwright Chromium. The job must complete within 15 minutes and publish its report as an artifact.

**Verification:** the job passes on a pull request and fails on a deliberately broken critical flow during review.

### FR-005 — Performance probe

Add a repeatable performance probe that measures:

- backend list, detail, search and graph endpoints;
- the 500-node producer ego graph;
- the bands and albums overview endpoints;
- browser load and interaction timings for `/graph` and `/producers/:id/graph`.

The probe uses warm-up samples followed by at least 20 measured samples, reports p50 and p95, and records the corpus version, analysis run, API/web URLs and machine details.

**Verification:** `npm run test:perf` writes a report and exits successfully when targets are met or exceptions are recorded.

### FR-006 — Performance targets

On the documented reference environment with the v0.2.0 corpus:

- list, detail and search endpoints: p95 ≤ 300 ms;
- 500-node producer ego graph: p95 ≤ 1 s server-side;
- overview endpoint in both views: p95 ≤ 1.5 s;
- `/graph` becomes interactive with a usable canvas within 5 s on the 968-node albums view;
- graph controls respond within 1 s;
- no blank canvas, unhandled error or frozen page occurs.

Long tasks over 500 ms and finite-layout completion times are recorded even when no threshold applies.

**Verification:** the performance report shows every value and identifies any exception with its cause.

### FR-007 — Accessibility audit

Run automated axe scans with WCAG 2.1 A/AA rules on `/bands`, band detail, `/albums`, album detail, `/producers`, producer detail, `/producers/:id/graph`, `/graph` and `/search`. Complete a manual checklist for keyboard navigation, focus visibility, headings and landmarks, table semantics, form labels, graph-control access and reduced motion.

**Verification:** zero critical or serious axe violations; manual findings classified and either fixed or documented with an accepted severity.

### FR-008 — Security and dependency review

Review at least:

- CORS origins and allowed methods;
- repository secrets and `.env` handling;
- input validation and bounded query parameters;
- read-only API boundaries and absence of authentication bypasses;
- dependency advisories for frontend and backend;
- absence of PII and of secrets in test artifacts.

Critical or high findings block E11 closure. App-level security headers that belong at the reverse proxy are recorded for E12 rather than implemented here.

**Verification:** a completed security checklist, dependency-audit output and zero open critical/high findings.

### FR-009 — Backup and restore drill

Dump the development database with `pg_dump`, restore it into a temporary database, compare row counts for the main catalog, normalization, quality and analysis tables, and remove the temporary database. The development database must not be modified or deleted.

**Verification:** restore completes, counts match, cleanup succeeds and the procedure and duration are recorded.

### FR-010 — QA report and checklists

Publish `docs/01-architecture/qa-report.md` with scope, environment, dataset versions, commands, E2E results, performance tables, accessibility findings, security findings, backup-restore evidence, known issues and a release recommendation. The report contains the performance, accessibility and security checklists required by the roadmap.

**Verification:** the report links to the spec, tasks, CI run and raw artifacts; every acceptance criterion points to evidence.

### FR-011 — Defect handling and release gate

Classify defects found by E11 as P1, P2 or P3. P1 and P2 defects are fixed before closure. P3 defects are documented with an owner and target stage. No new product feature is added to close a QA finding.

**Verification:** the QA report lists every open issue and confirms no P1/P2 remains.

### FR-012 — Documentation and status closure

Update the roadmap, README, `AGENTS.md`, frontend documentation and SDD index with the E11 result and the next E12 step.

**Verification:** documentation review confirms that E11 status, evidence and remaining risks are consistent across the repository.

## 5. Non-functional requirements

### NFR-001 — Deterministic and offline-compatible E2E tests

E2E tests must not call MusicBrainz or any external service. They must pass from a clean checkout with only repository fixtures and a disposable database.

### NFR-002 — CI cost and duration

The E2E job must complete within 15 minutes on the standard GitHub Actions runner. The performance probe is not a required CI job for v0.1.

### NFR-003 — Test-only dependencies

Playwright and axe are development dependencies. No new production dependency is introduced. Dependency approval is part of the SPEC-014 approval gate.

### NFR-004 — No production behavior change

SPEC-014 must not change API contracts, database schema, migrations or user-visible behavior. Stable `data-testid` or accessible selectors may be added where required by tests.

### NFR-005 — Security and privacy

No secret, token, personal data or production database content appears in the repository, test fixtures, reports or CI artifacts.

### NFR-006 — Accessibility baseline

Main routes meet the WCAG 2.1 AA baseline for automated critical/serious checks and for the manual keyboard/focus checklist.

### NFR-007 — Reproducible performance evidence

The performance report records the exact commands, corpus and analysis-run versions, environment and sample count so that another maintainer can repeat it.

### NFR-008 — Test independence

Tests are order-independent, use their own navigation state and clean up temporary data or processes.

## 6. Business rules

- **BR-001:** E2E data is always deterministic repository fixture data, never live ingestion.
- **BR-002:** Performance evidence uses the v0.2.0 corpus and records the analysis run and taxonomy/dataset versions.
- **BR-003:** Critical or high security findings and P1/P2 defects block E11 closure.
- **BR-004:** Critical or serious accessibility findings block E11 closure; moderate/minor findings require a recorded decision.
- **BR-005:** Backup restore operations use a temporary database and never modify or delete the development database.
- **BR-006:** Test artifacts may contain screenshots and traces but never secrets, tokens or personal data.
- **BR-007:** E11 does not add product scope, API behavior or schema changes to make a test pass.

## 7. Edge cases and errors

- Database unavailable, migration failure or seed failure: the E2E run fails with a clear message and does not reuse stale data.
- Port already in use: Playwright reuses an existing local server only outside CI; CI always starts its own.
- Empty or truncated graph response: the UI shows the documented empty/truncated state and the accessible table remains usable.
- API error or 404: the route shows its error/not-found state and supports retry or navigation.
- Reduced motion: the graph starts frozen or completes statically without animation.
- Backup restore name conflict or permission error: the drill aborts before touching the source database and records the failure.
- Dependency audit unavailable due to network: the report records the limitation and the manual review performed.
- axe false positive: the finding is triaged with the rule ID and an explicit decision; it is not silently ignored.
- Performance variance: cold cache and first-run values are discarded; the report records spread and environment.

## 8. Out of scope

- E12 deployment, TLS, reverse proxy, production Compose, runbooks and release tag.
- E13 corpus expansion.
- SPEC-017 and SPEC-018 follow-up layouts and edge routing.
- New product features, API endpoints, response fields or schema changes.
- Firefox and WebKit E2E coverage for v0.1; Chromium is the CI browser.
- Visual regression or screenshot-diff testing.
- Penetration testing, formal WCAG certification or a full accessibility audit by a third party.
- Stress, soak or capacity testing beyond the documented MVP volume.
- Production monitoring, alerting or an SLA.
- Changes to ingestion, normalization, quality or analysis outputs.

## 9. Acceptance criteria

| ID | Criterion | Evidence |
|---|---|---|
| AC-001 | Deterministic E2E data can be created from a clean database and the seed is safe to rerun. | Seed command and two consecutive runs |
| AC-002 | All critical flows in FR-002 pass in Playwright Chromium. | Playwright report |
| AC-003 | The E2E suite runs in CI as a required job within 15 minutes with artifacts. | GitHub Actions job |
| AC-004 | The performance probe records p50/p95 for every FR-005 target and the environment. | Performance report |
| AC-005 | The FR-006 targets are met or every exception is documented with a cause. | Performance report and QA report |
| AC-006 | axe reports zero critical or serious WCAG 2.1 A/AA violations on the main routes. | axe output |
| AC-007 | The manual keyboard, focus and reduced-motion checklist is complete. | QA report checklist |
| AC-008 | The security checklist and dependency review are complete with no open critical/high finding. | QA report and audit output |
| AC-009 | The backup restores into a temporary database with matching key row counts and successful cleanup. | Restore drill evidence |
| AC-010 | The QA report contains the required checklists, known issues and release recommendation. | `docs/01-architecture/qa-report.md` |
| AC-011 | No P1/P2 defect remains open. | QA report |
| AC-012 | Backend and frontend unit, integration, lint, typecheck, test and build checks pass. | Command output |
| AC-013 | No API, schema, migration or production dependency change is introduced. | Diff and dependency review |
| AC-014 | Roadmap, README, AGENTS, frontend docs and SDD index reflect the E11 result. | Documentation review |

## 10. Assumptions and open questions

### Assumptions

- E10 closure evidence is accepted as the baseline; E11 does not re-open E10 scope.
- The historical E2 fixture set is sufficient for deterministic E2E flows; graph routes can be seeded through the existing network builders.
- Chromium is the only required E2E browser for v0.1.
- The full v0.2.0 corpus and the recorded analysis run are available locally for performance evidence.
- The development Docker Compose stack is the reference performance environment until E12 defines production hosting.

### Open questions

| Question | Blocking? | Owner | Resolution |
|---|---|---|---|
| Approve `@playwright/test` and `@axe-core/playwright` as development dependencies? | No | Cristian | Approved and added as development dependencies |
| Approve the new CI `e2e` job? | No | Cristian | Approved and added; remote result pending |
| Use Chromium only for v0.1 E2E? | No | Cristian | Yes; Firefox and WebKit deferred |
| Are the FR-006 performance targets acceptable? | No | Cristian | Yes; one view-switch exception documented in the QA report |
| Use a temporary database for the restore drill? | No | Cristian | Yes; the source database was not modified |

## 11. Validation result

- **Date:** 2026-11-16
- **Verdict:** Implemented locally; not fully validated. Every acceptance criterion has local evidence except AC-003, whose GitHub Actions `e2e` run and required-check setting remain pending.
- **Evidence:** [QA report](../../docs/01-architecture/qa-report.md), [tasks.md](tasks.md) and the local command output recorded there.

## 12. References

- [Constitution](../../constitution.md)
- [AGENTS.md](../../AGENTS.md)
- [Roadmap](../../docs/00-vision/roadmap.md)
- [Architecture overview](../../docs/01-architecture/overview.md)
- [Engineering conventions](../../docs/01-architecture/conventions.md)
- [Frontend explorer](../../docs/01-architecture/frontend.md)
- [Read-only API v1](../../docs/03-data/api-v1.md)
- [SPEC-010 — Entity explorer](../010-entity-explorer/spec.md)
- [SPEC-011 — Graph visualization](../011-graph-visualization/spec.md)
- [SPEC-012 — Graph overview refinements](../012-graph-overview-refinements/spec.md)
- [SPEC-013 — Graph layout modes](../013-graph-layout-modes/spec.md)
