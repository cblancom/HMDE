# Tasks — SPEC-010 Entity explorer frontend

- **Status:** Implemented locally; remote CI pending
- **Spec:** [spec.md](spec.md)
- **Plan:** [plan.md](plan.md)

## 1. Execution order

```text
T-001 ─► T-002 ─► T-003 ─┬─► T-004 ─┐
                         ├─► T-005 ─┤
                         ├─► T-006 ─┼─► T-008 ─► T-009 ─► T-010
                         └─► T-007 ─┘
```

T-001 establishes the visual foundation. T-002 adds the typed client. T-003 builds the shell and shared URL/pagination primitives. T-004–T-007 implement entity pages in parallel after the shell. T-008 handles states/accessibility/responsive polish. T-009 adds scope and quality checks. T-010 closes docs, full checks and CI.

## 2. Tasks

### T-001 — Establish design tokens, local typefaces and ledger foundation

- **Status:** Completed (2026-11-10).
- **Requirements:** NFR-005, NFR-009, FR-016.
- **Dependencies:** SPEC-009 validated; plan/tasks approved.
- **Description:** Add `@fontsource-variable/bricolage-grotesque` and `@fontsource-variable/source-serif-4`. Introduce CSS custom properties for the approved palette, type scale and rules. Add the ledger base styles, skip-link styling, focus treatment and reduced-motion rules. Keep the existing CSS architecture; do not add Tailwind or a component library.
- **Done when:** tokens are used by the shell and existing pages; type roles match the plan; focus is visible; reduced motion is respected; no Tailwind dependency exists.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  npm run build
  ```
- **Files:** `frontend/package.json`, `frontend/package-lock.json`, `frontend/src/index.css`, `frontend/src/main.tsx`, tests.
- **Evidence:** 2026-11-10: added Bricolage Grotesque and Source Serif 4, studio-ledger tokens, responsive shell, skip link, oxide focus and reduced-motion rules. Frontend lint/typecheck/21 tests/build passed.

### T-002 — Add typed API client modules and query helpers

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-002, FR-018, NFR-003, NFR-006.
- **Dependencies:** T-001.
- **Description:** Add typed API modules for albums, artists, producers, taxonomy and search. Extend the bands API filters. Centralize URLSearchParams construction and typed response imports from generated OpenAPI schemas. Add stable query-key helpers.
- **Done when:** no hand-written duplicate domain interfaces exist; all E9 resources use generated schema types; query keys and URL builders are reused.
- **Verification:**
  ```bash
  cd frontend
  npm run generate:api
  npm run typecheck
  npm run test
  ```
- **Files:** `frontend/src/api/albums.ts`, `artists.ts`, `producers.ts`, `search.ts`, `taxonomy.ts`, `bands.ts`, `queryKeys.ts`, `client.ts`, tests.
- **Evidence:** 2026-11-10: generated-schema API modules and stable query keys added; query builders encode API names and omit empty values. Frontend lint/typecheck/24 tests passed.

### T-003 — Build shell, navigation, routes, search entry and pagination

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-001, FR-012, FR-013, NFR-001.
- **Dependencies:** T-002.
- **Description:** Build `AppShell` with masthead, index rail, primary navigation, global search form, API status and skip link. Add routes for albums, producers and search. Add a shared URL-driven pagination component.
- **Done when:** navigation works on all routes; search submit navigates to `/search`; pagination preserves filters; back/forward restores state.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  ```
- **Files:** `frontend/src/App.tsx`, `components/AppShell.tsx`, `components/Pagination.tsx`, `components/SearchBox.tsx`, `pages/NotFoundPage.tsx`, tests.
- **Evidence:** 2026-11-10: studio-ledger shell, primary navigation, global search, route scaffold, skip link and URL-driven pagination added. Shell/pagination tests passed; frontend 27 tests total.

### T-004 — Implement bands list and detail

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-003, FR-004, FR-010, FR-011.
- **Dependencies:** T-003.
- **Description:** Replace the hard-coded subgenre array with the taxonomy API. Add decade/period filters, URL state, result count and pagination to the bands list. Extend the band detail with taxonomy, album/producer links and the retained compact E2 relationship view.
- **Done when:** bands list uses dynamic taxonomy; filters survive navigation; detail links to albums/producers; 404/empty/error states work.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  ```
- **Files:** `pages/BandsPage.tsx`, `pages/BandDetailPage.tsx`, `components/BandList.tsx`, `components/TaxonomySelect.tsx`, `components/PeriodFilter.tsx`, `components/Pagination.tsx`, tests.
- **Evidence:** 2026-11-10: bands list now uses dynamic taxonomy, decade filter, URL pagination and result counts; detail links albums and producer credits. Frontend lint/typecheck/29 tests passed; Cytoscape init is guarded for non-canvas environments.

### T-005 — Implement albums list and detail

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-005, FR-006, FR-011.
- **Dependencies:** T-003.
- **Description:** Add album list/search with band, producer, decade and taxonomy filters. Add album detail with band, date/year, taxonomy, support-aware credits and related entity links.
- **Done when:** album list filters/pagination work; detail renders support values and missing-data language; 404/empty/error states work.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  ```
- **Files:** `pages/AlbumsPage.tsx`, `pages/AlbumDetailPage.tsx`, `components/AlbumList.tsx`, `components/CreditList.tsx`, tests, `App.tsx`.
- **Evidence:** 2026-11-10: album list/search/filter/pagination and album detail with taxonomy and support-aware credits implemented; album/band/producer links added. Frontend lint/typecheck/34 tests passed.

### T-006 — Implement producers list and detail

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-007, FR-008, NFR-003.
- **Dependencies:** T-003.
- **Description:** Add producer ranking/list with sort, search, decade and taxonomy filters. Add producer detail with metrics, community, top albums and top bands/artists, linking to albums and bands. Do not render the graph canvas.
- **Done when:** ranking/sort/pagination work; detail shows metrics and top entities; no producer graph endpoint is called; 404/empty/error states work.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  ```
- **Files:** `pages/ProducersPage.tsx`, `pages/ProducerDetailPage.tsx`, `components/ProducerList.tsx`, tests, `App.tsx`.
- **Evidence:** 2026-11-10: producer rankings with sort/search/decade/taxonomy filters and detail metrics/top albums/bands implemented; no graph endpoint called. Frontend lint/typecheck/38 tests passed.

### T-007 — Implement grouped search

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-009, FR-013.
- **Dependencies:** T-003.
- **Description:** Add `/search?q=` grouped results for bands/artists, albums and producers. Add empty-query prompt, result counts and links. No autocomplete or per-keystroke requests.
- **Done when:** search submit works; grouped results are bounded; empty query does not call the API; loading/empty/error states work.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  ```
- **Files:** `pages/SearchPage.tsx`, `components/SearchResults.tsx`, tests.
- **Evidence:** 2026-11-10: submit-based grouped search with bounded API results, empty-query prompt and grouped links implemented. Frontend lint/typecheck/39 tests passed.

### T-008 — Complete accessibility, responsive and state polish

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-014, FR-015, FR-016, NFR-002, NFR-004, NFR-007.
- **Dependencies:** T-004, T-005, T-006, T-007.
- **Description:** Audit every page for semantic headings, labels, table captions, focus order, live result announcements, error/empty/404/retry states and mobile table behavior. Apply reduced-motion and keyboard checks. Refine ledger CSS specificity and responsive rules.
- **Done when:** keyboard path works; focus is visible; tables are labeled; mobile has no page-level horizontal overflow; all states are covered by tests.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  npm run build
  ```
- **Files:** page/component tests, `frontend/src/index.css`, `components/AsyncState.tsx`, `components/AppShell.tsx`, `components/BandGraph.tsx`, `test/setup.ts`, relevant pages.
- **Evidence:** 2026-11-10: skip link, labeled tables, live result states, focus treatment, reduced motion, responsive overflow and guarded canvas rendering verified. Frontend lint/typecheck/39 tests/build passed.

### T-009 — Add scope guards and design-contract tests

- **Status:** Completed (2026-11-10).
- **Requirements:** FR-017, FR-019, NFR-008, FR-020.
- **Dependencies:** T-008.
- **Description:** Add tests that reject Tailwind/Plotly/component-library additions, verify no new graph canvas or producer graph calls exist, and enforce no backend/API changes. Add design-contract checks for dynamic taxonomy and absence of hard-coded subgenres.
- **Done when:** scope guards pass; no Tailwind/Plotly/graph page exists; no backend diff is introduced; hard-coded subgenres are gone.
- **Verification:**
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm run test
  ```
- **Files:** `frontend/src/scope.test.ts`, `frontend/src/**/*.test.tsx`, package/dependency inspection, `specs/010-entity-explorer/tasks.md`.
- **Evidence:** 2026-11-10: scope tests confirm no Tailwind/Plotly/UI kit, no producer graph calls, no hard-coded taxonomy codes and generated schema usage. Frontend lint/typecheck/42 tests passed.

### T-010 — Complete documentation, full checks and CI

- **Status:** Completed locally (2026-11-10); remote CI pending.
- **Requirements:** FR-020, NFR-009, NFR-010.
- **Dependencies:** T-009.
- **Description:** Document the explorer routes, filters, taxonomy behavior, design tokens and accessibility. Update README/AGENTS/docs/roadmap/spec index. Run full frontend and backend checks, OpenAPI type generation and Compose validation. Push only with explicit authorization and record remote CI.
- **Done when:** docs match the implementation; lint/typecheck/tests/build pass; no scope violations; remote CI passes; spec/tasks evidence and status are updated.
- **Verification:**
  ```bash
  cd frontend
  npm ci
  npm run generate:api
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
- **Files:** `README.md`, `AGENTS.md`, `docs/01-architecture/frontend.md`, `docs/README.md`, `docs/00-vision/roadmap.md`, `specs/README.md`, `specs/010-entity-explorer/`.
- **Evidence:** 2026-11-10: frontend 42 tests, lint, typecheck and build passed; backend 313 tests, Ruff/format, OpenAPI/type generation and Compose passed; documentation updated. Remote CI is pending because no commit or push was performed.

## 3. Coverage matrix

### Functional requirements

| Requirement | Tasks |
|---|---|
| FR-001 | T-003 |
| FR-002 | T-002 |
| FR-003 | T-004 |
| FR-004 | T-004 |
| FR-005 | T-005 |
| FR-006 | T-005 |
| FR-007 | T-006 |
| FR-008 | T-006 |
| FR-009 | T-007 |
| FR-010 | T-004 |
| FR-011 | T-004, T-005 |
| FR-012 | T-003, T-004, T-005, T-006 |
| FR-013 | T-003, T-007 |
| FR-014 | T-008 |
| FR-015 | T-008 |
| FR-016 | T-008 |
| FR-017 | T-009 |
| FR-018 | T-002 |
| FR-019 | T-009 |
| FR-020 | T-009, T-010 |

### Non-functional requirements

| Requirement | Tasks |
|---|---|
| NFR-001 | T-003, T-004, T-005, T-006 |
| NFR-002 | T-008 |
| NFR-003 | T-002, T-006 |
| NFR-004 | T-008 |
| NFR-005 | T-001, T-008 |
| NFR-006 | T-002 |
| NFR-007 | T-008 |
| NFR-008 | T-009 |
| NFR-009 | T-001, T-010 |
| NFR-010 | T-010 |

## 4. Validation evidence

| Criterion | Result | Evidence |
|---|---|---|
| AC-001 | Passed | Navigation tests |
| AC-002 | Passed | Typed client/typecheck |
| AC-003 | Passed | Bands page tests |
| AC-004 | Passed | Band detail tests |
| AC-005 | Passed | Albums page tests |
| AC-006 | Passed | Album detail tests |
| AC-007 | Passed | Producers page tests |
| AC-008 | Passed | Producer detail tests |
| AC-009 | Passed | Search page tests |
| AC-010 | Passed | Dynamic taxonomy tests |
| AC-011 | Passed | URL/period tests |
| AC-012 | Passed | Pagination tests |
| AC-013 | Passed | State tests |
| AC-014 | Passed | Accessibility tests |
| AC-015 | Passed | Responsive check |
| AC-016 | Passed | Scope inspection |
| AC-017 | Passed | Generated types inspection |
| AC-018 | Passed | Main flow tests |
| AC-019 | Passed | 42 frontend tests, lint, typecheck, build |
| AC-020 | Passed locally; remote CI pending | 313 backend tests, frontend checks, Compose |

## 5. Notes

- Tailwind is deferred; use the existing CSS and add tokens only where they reduce repetition.
- Do not add a component library, Plotly or graph canvas.
- Keep the E2 mini graph on band detail; full graph work starts in E10.
- No backend, API or schema changes are part of E9.
- Do not mark a task complete until its verification was executed.
