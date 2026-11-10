# SPEC-010 — Entity explorer frontend

- **Status:** Validated
- **Stage:** E9
- **Iteration:** MVP
- **Module:** `web`
- **Date:** 2026-11-10
- **Depends on:** SPEC-009 validated; read-only API v1; [ADR-0006](../../docs/01-architecture/adr/ADR-0006-read-only-api.md)
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0006](../../docs/01-architecture/adr/ADR-0006-read-only-api.md), [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)
- **Plan:** [plan.md](plan.md) (approved).
- **Tasks:** [tasks.md](tasks.md) (validated).
- **Conventions:** [Engineering conventions](../../docs/01-architecture/conventions.md)
- **Owner:** Cristian

## Revision history

| Revision | Date | Change |
|---|---|---|
| 1 | 2026-11-10 | Initial draft; E9 entity explorer with existing CSS and Tailwind deferred |
| 2 | 2026-11-10 | Design/technical plan and tasks drafted for review |
| 3 | 2026-11-10 | T-001–T-010 implemented locally; frontend/backend checks passed |
| 4 | 2026-11-10 | Remote CI run 42747146170 passed; SPEC-010 validated |

## 1. Context and problem

E8 validated a read-only `/api/v1` contract for bands, artists, albums, credits, producers, search, taxonomy, analysis runs, analytics and bounded producer graphs. The current frontend is still the E2 walking skeleton: it has a band list, band detail, hard-coded subgenre options and a one-hop band–producer mini graph.

E9 must turn that skeleton into the main entity explorer. Users must be able to move from a band to its albums and producers, from an album to its band and credits, and from a producer to their top albums, bands and metrics without writing SQL or knowing the API. E9 consumes E8; it does not add batch processing, API endpoints, database changes or the full graph visualization.

```text
                    E8 read-only /api/v1
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
    bands/artists       albums/credits     producers/analytics
        │                  │                  │
        └──────────────────┼──────────────────┘
                           ▼
                  E9 React entity explorer
       lists · detail · search · taxonomy filters · URLs
                           │
                           ▼
                  E10 graph visualization
```

## 2. Goals and non-goals

### Goals

- Build a coherent application shell and navigation for bands, albums and producers.
- Replace hard-coded subgenre options with the versioned taxonomy endpoint.
- Provide list, detail, search, filter and pagination flows using E8.
- Make list/detail URLs shareable and filter state URL-driven.
- Cover loading, error, empty and not-found states consistently.
- Keep the interface responsive and keyboard accessible.
- Use generated OpenAPI types and typed API client modules.
- Preserve the existing visual direction and CSS architecture.

### Non-goals

- Full graph visualization, graph filters or node expansion; E10 owns that.
- An album–album or artist–artist graph UI.
- Tailwind migration or adoption.
- Plotly charts or statistical dashboards.
- Authentication, writes, user accounts or editing.
- New API endpoints, database changes or batch jobs.
- Full-text search engine, autocomplete or faceted analytics.
- Playwright end-to-end suite; E11 owns integration QA.
- Production deployment; E12 owns release operations.

## 3. Users and actors

- **Analytical user:** explores bands, albums and producers and follows documented relationships.
- **Music researcher/journalist/fan:** finds an entity and reviews credits, taxonomy and metrics.
- **Frontend developer:** implements typed pages, query state and tests.
- **E10 consumer:** reuses the shell, entity links and visual language for graph views.

No authentication or user-specific state exists.

## 4. Routes and information architecture

| Route | Purpose |
|---|---|
| `/` | Redirects to `/bands` |
| `/bands` | Searchable/filterable band list |
| `/bands/:bandId` | Band detail, albums, credits and compact producer relationships |
| `/albums` | Searchable/filterable album list |
| `/albums/:albumId` | Album detail, taxonomy and support-aware credits |
| `/producers` | Ranked/filterable producer list |
| `/producers/:producerId` | Producer metrics, community and top albums/bands |
| `/search?q=...` | Grouped cross-entity search results |
| `*` | Not-found page with navigation back to bands |

The shell includes the application title, primary navigation (`Bands`, `Albums`, `Producers`), a global search entry point and the existing API status indicator.

## 5. Product behavior

### 5.1 Bands

List:

- search by name;
- taxonomy filter from `/api/v1/taxonomy`, including parent categories;
- decade and period filters;
- pagination;
- result count and empty state;
- retired bands excluded by default; no retired toggle is required in E9.

Detail:

- band name, country, MBID, primary subgenre and album count;
- albums with year/date and taxonomy;
- credits grouped by album and role;
- links to album and producer details;
- compact existing one-hop producer relationship view, retained until E10 replaces/augments it.

### 5.2 Albums

List:

- search by title;
- filters for band, producer, decade and taxonomy;
- pagination and total count.

Detail:

- album title, band, year/date and MBID;
- primary and secondary taxonomy;
- support-aware credits with role, scope and counts;
- links to band and producer details;
- explicit missing-data language; no credit is presented as negative evidence.

### 5.3 Producers

List:

- ranking by album count, band count, betweenness or name;
- search by producer name;
- decade and taxonomy filters;
- pagination and total count.

Detail:

- producer name, country and artist type;
- album count, band count, self-produced albums and betweenness;
- community label when available;
- top albums and top bands/artists;
- links to album and band/artist details;
- no graph canvas in E9; the graph view belongs to E10.

### 5.4 Search

- Global search entry in the shell.
- `/search?q=...` shows grouped bands/artists, albums and producers.
- Bounded results from `/api/v1/search`.
- Empty, loading and error states.
- No autocomplete or debounced typeahead in E9; submit-based search keeps the implementation small and predictable.

### 5.5 Taxonomy and period filters

- Taxonomy options come from `/api/v1/taxonomy`; no hard-coded subgenre list.
- Parent categories include descendants according to E8 semantics.
- Period filters use the E8 `decade`, `year_from` and `year_to` parameters where the resource supports them.
- Invalid or stale URL filter values produce a clear empty/error state, not a crash.

## 6. Technical direction

### 6.1 Styling

Tailwind is **deferred**. E9 extends the existing CSS and reuses current components and class patterns.

- No Tailwind dependency or migration.
- Add shared CSS variables/tokens only where they reduce repetition.
- Preserve the current dark visual direction.
- Extract reusable UI components rather than duplicating markup.

Alternative rejected: adopting Tailwind in E9. The existing stylesheet is 436 lines with 58 rules; migration cost is larger than the benefit at this scale. Tailwind may be revisited if UI complexity, contributor count or design-system needs grow.

### 6.2 Data fetching

- TanStack Query for server state.
- Typed API modules under `frontend/src/api/` generated from OpenAPI types.
- Stable query keys derived from resource and URL state.
- URL as source of truth for search, filters, sort and pagination.
- No global state library.
- No request waterfalls where a detail page needs one primary entity plus independent secondary data.

### 6.3 Components

Reuse/extend:

- `AsyncState` for loading/error/empty;
- `BandList`, `CreditList`, `BandGraph`;
- new list/detail components for albums and producers;
- shared filter, taxonomy and pagination controls;
- shared entity links.

## 7. Functional requirements

### FR-001 — Application shell and navigation

The app must provide persistent navigation for bands, albums, producers, search and not-found handling, with the API status visible.

**Verification:** shell/nav tests and route tests.

### FR-002 — Typed API client

The frontend must consume generated OpenAPI types and typed API functions for bands, artists, albums, credits, producers, taxonomy, search and analytics used by E9.

**Verification:** typecheck and API client tests.

### FR-003 — Bands list

The bands page must support search, taxonomy, decade/period filters, pagination, result counts and empty/error states.

**Verification:** page tests with URL state.

### FR-004 — Band detail

The band detail must show metadata, albums, taxonomy, credits and links to albums/producers; it must preserve the compact E2 relationship view until E10.

**Verification:** detail tests and 404 test.

### FR-005 — Albums list

The albums page must support search and filters by band, producer, decade and taxonomy, with pagination and empty states.

**Verification:** album list tests.

### FR-006 — Album detail

The album detail must show band, date/year, primary/secondary taxonomy, support-aware credits and links to related entities.

**Verification:** album detail tests.

### FR-007 — Producers list

The producers page must show ranking metrics and support sorting, search, decade/taxonomy filters and pagination.

**Verification:** producer list tests.

### FR-008 — Producer detail

The producer detail must show available metrics, community, top albums and top bands/artists with links; it must not render the full graph canvas.

**Verification:** producer detail tests.

### FR-009 — Grouped search

The search page must render grouped and bounded results for bands/artists, albums and producers from `/api/v1/search`.

**Verification:** search page tests.

### FR-010 — Dynamic taxonomy

All subgenre controls must use `/api/v1/taxonomy`; hard-coded subgenre arrays must be removed.

**Verification:** grep/API client tests and taxonomy filter tests.

### FR-011 — Period filters

Band and album views must expose supported decade/year filters and preserve them in the URL.

**Verification:** URL and filter tests.

### FR-012 — Pagination

List pages must use API `limit`/`offset`, expose previous/next controls and preserve filters across pages.

**Verification:** pagination tests.

### FR-013 — URL state

Search, filters, sort and pagination must be shareable URL state; browser back/forward must restore the view.

**Verification:** router/URL tests.

### FR-014 — States and errors

Every page must handle loading, empty, 404, API error and retry states consistently.

**Verification:** component/page tests.

### FR-015 — Accessibility

The UI must use semantic headings, form labels, table captions/headers, visible focus, keyboard-operable controls, live result announcements and an accessible not-found/error experience.

**Verification:** RTL accessibility assertions and manual keyboard review.

### FR-016 — Responsive behavior

Lists, filters, detail metadata and credit tables must remain usable on narrow screens without horizontal page breakage.

**Verification:** component tests and manual responsive check.

### FR-017 — Scope boundary

E9 must not add Tailwind, Plotly, full graph visualization, authentication, writes, backend endpoints or schema changes.

**Verification:** dependency, route and scope inspection.

### FR-018 — Generated contract

E9 must use the generated API schema; no new hand-written duplicate entity interfaces.

**Verification:** `npm run generate:api`, typecheck and code inspection.

### FR-019 — Backend compatibility

E9 must consume E8 as-is. If the contract needs to change, update SPEC-009 or create a versioned revision before changing the frontend.

**Verification:** no API code changes in the E9 diff.

### FR-020 — Tests and checks

E9 must include component/page tests for the main flows and pass lint, typecheck, tests and production build.

**Verification:** local and CI commands.

## 8. Non-functional requirements

### NFR-001 — Usability

A user must be able to go from a list to a detail and then to a related entity without dead ends.

### NFR-002 — Accessibility

WCAG-oriented basics: semantics, labels, focus visibility, keyboard operation, contrast and non-color-only state cues.

### NFR-003 — Performance

Pages should request only the visible page and required detail data; no full graph or unbounded list fetch. Avoid duplicate queries and unnecessary waterfalls.

### NFR-004 — Responsiveness

The layout must work from 320px upward; tables may scroll within a labeled container, but the page itself must not.

### NFR-005 — Maintainability

Reuse existing components and CSS; extract shared components only when repeated.

### NFR-006 — Contract safety

Generated types are the source of truth; no hand-edited generated files.

### NFR-007 — Reliability

API errors and empty results must not crash routes; retries remain explicit.

### NFR-008 — No scope creep

No new styling framework or charting library in E9.

### NFR-009 — Language

All UI copy and code identifiers are in English.

### NFR-010 — Reproducibility

The frontend build must not require a live API or external network at build time.

## 9. Business rules

- **BR-001:** E9 is read-only; no writes, accounts or editing.
- **BR-002:** Missing credits are not negative evidence.
- **BR-003:** Taxonomy filters come from the API and include parent descendants.
- **BR-004:** Retired bands are absent from default lists/search but direct URLs remain accessible.
- **BR-005:** Producer metrics and community labels are descriptive, not causal.
- **BR-006:** The producer graph canvas is deferred to E10; E9 may retain the existing E2 mini graph only.
- **BR-007:** Tailwind is deferred; E9 uses the existing CSS.
- **BR-008:** Search is submit-based and bounded; no autocomplete.
- **BR-009:** URL state is the source of truth for filters and pagination.
- **BR-010:** No backend/API/schema changes are part of E9.
- **BR-011:** Generated TypeScript types are not edited by hand.
- **BR-012:** The frontend must not render the entire graph or fetch unbounded lists.

## 10. Edge cases and errors

- API unavailable: page-level error with retry; shell remains usable.
- Empty database: lists show empty states; detail returns 404.
- Unknown band/album/producer ID: not-found state with navigation back.
- Invalid URL filter: visible error or safe empty state; no crash.
- Taxonomy endpoint unavailable: filters show a recoverable error and the list remains usable.
- Producer with no bands/albums: explicit empty states, not an error.
- Album without taxonomy/date: show unknown/unclassified labels.
- No search query: prompt for a query; no request.
- API truncation in producer graph: not rendered in E9.
- Very long names: wrap/truncate without breaking layout.
- Browser back/forward: restore filters and pagination.

## 11. Out of scope

- E10 graph visualization, graph filters, expansion, album-year color scale.
- Tailwind, Plotly, charting dashboards or a design-system package.
- Playwright/end-to-end, performance load tests and deployment.
- Authentication, user accounts, writes, editing or contributions.
- New API endpoints or database migrations.
- Full-text search engine, autocomplete or advanced ranking.
- Mobile native application or internationalization.

## 12. Acceptance criteria

| ID | Criterion | Evidence |
|---|---|---|
| AC-001 | Shell provides navigation to bands, albums, producers and search. | Navigation tests |
| AC-002 | Typed API client uses generated schemas for E9 resources. | Typecheck/tests |
| AC-003 | Bands list supports search, taxonomy, period, pagination and URL state. | Page tests |
| AC-004 | Band detail shows albums, credits, taxonomy and related links. | Page tests |
| AC-005 | Albums list supports search/filter/pagination. | Page tests |
| AC-006 | Album detail shows band, taxonomy and support-aware credits. | Page tests |
| AC-007 | Producers list supports ranking, filters, sorting and pagination. | Page tests |
| AC-008 | Producer detail shows metrics, community and top albums/bands. | Page tests |
| AC-009 | Search page renders grouped bounded results. | Page tests |
| AC-010 | Subgenre controls use `/api/v1/taxonomy`; no hard-coded list remains. | Code/API tests |
| AC-011 | Period filters work and persist in URLs. | URL tests |
| AC-012 | Pagination preserves filters and updates URL. | Pagination tests |
| AC-013 | Loading, empty, 404, error and retry states exist. | Page tests |
| AC-014 | Keyboard/focus/labels/captions are covered. | Accessibility tests |
| AC-015 | Layout works at narrow widths. | Responsive/manual check |
| AC-016 | No Tailwind, Plotly, graph canvas, writes or backend changes. | Scope inspection |
| AC-017 | No hand-written duplicate entity interfaces. | Code inspection |
| AC-018 | Main list → detail → related flow works. | RTL/main flow tests |
| AC-019 | Lint, typecheck, tests and build pass. | Local/CI evidence |
| AC-020 | Remote CI passes. | CI evidence |

## 13. Assumptions and resolved decisions

### Assumptions

- SPEC-009 remains validated and its `/api/v1` contract is stable.
- The active dataset remains 57 bands for E9.
- Existing CSS and components are sufficient for the explorer.
- E10 will own the full production graph UI.

### Resolved decisions

| Decision | Resolution |
|---|---|
| Tailwind | Deferred; reuse existing CSS. |
| E2 mini graph | Keep as a compact relationship view until E10. |
| Producer graph page | Deferred to E10. |
| Search | Submit-based grouped search; no autocomplete. |
| State management | TanStack Query plus URL state; no global store. |
| Taxonomy | Dynamic from API; parent filters include descendants. |
| Retired bands | Hidden by default; direct detail URLs remain accessible. |
| Pagination | API `limit`/`offset` reflected in URL. |
| Styling migration | None in E9. |
| Backend changes | None. |

### Open questions

No blocking question remains for planning. Exact component split, mobile table behavior and label wording are plan-level details.

## 14. Validation result

- **Date:** 2026-11-10
- **Verdict:** Validated
- **Evidence:** 42 frontend tests, lint, typecheck and production build passed; backend 313 tests, Ruff/format, OpenAPI/type generation and Compose passed. No Tailwind/Plotly/UI kit, no producer graph calls and no hard-coded taxonomy arrays. Remote CI run [42747146170](https://github.com/cblancom/HMDE/actions/runs/42747146170) passed for commit `afb5c04`. See `tasks.md`.

## 15. References

- [Constitution](../../constitution.md)
- [AGENTS.md](../../AGENTS.md)
- [Vision](../../docs/00-vision/vision.md)
- [Scope](../../docs/00-vision/scope.md)
- [Roadmap](../../docs/00-vision/roadmap.md)
- [Architecture overview](../../docs/01-architecture/overview.md)
- [Read-only API v1](../../docs/03-data/api-v1.md)
- [ADR-0006 — Read-only API](../../docs/01-architecture/adr/ADR-0006-read-only-api.md)
- [ADR-0008 — Taxonomy and corpus versioning](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)
- [SPEC-009 — Read-only API v1](../009-read-api/spec.md)
