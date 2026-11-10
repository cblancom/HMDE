# Technical and design plan — SPEC-010 Entity explorer

- **Status:** Approved
- **Spec:** [spec.md](spec.md)
- **Tasks:** [tasks.md](tasks.md)
- **Stage:** E9
- **Module:** `web`
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0006](../../docs/01-architecture/adr/ADR-0006-read-only-api.md), [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)

## 1. Solution summary

SPEC-010 turns the E2 band-only frontend into a typed entity explorer for bands, albums and producers. It consumes the validated E8 `/api/v1` contract and keeps E9 read-only: no backend, schema, ingestion or graph-computation changes.

E9 keeps the existing CSS architecture and does **not** introduce Tailwind. It adds a deliberate design layer, typed API clients, URL-driven filters, dynamic taxonomy, shared list/detail components and page-level tests. The full graph canvas remains E10.

```text
E8 read-only API
       │
       ├── bands / artists
       ├── albums / credits
       ├── producers / analytics
       ├── taxonomy / search
       └── analysis-run metadata
       │
       ▼
E9 React explorer
  shell · nav · search · filters · lists · details
       │
       ▼
E10 graph visualization
```

## 2. Audience and design brief

**Subject:** an archive of documented heavy metal production relationships.

**Audience:** researchers, music journalists, students, data-curious fans and crate-digging listeners.

**Primary job:** move from a band, album or producer to the documented credits and related entities without reading like a generic admin dashboard.

The interface should feel like a working production ledger from a studio: dense, ordered, tactile and serious about provenance. It should not use fantasy-metal clichés (skulls, spikes, gothic texture) or generic SaaS dashboard language.

## 3. Design plan

### 3.1 Concept: the studio ledger

The product is presented as a **production ledger**: a place where records, people and credits are indexed. The visual language borrows from studio tracking sheets, tape labels and equipment panels, but stays editorial and legible.

- The list is the primary object, not a card grid.
- Rules, columns and type encode hierarchy.
- One oxide-red accent marks action and selection.
- A galvanized pale-green background keeps the interface from becoming another near-black metal page.
- The visual risk is the persistent index rail and dense ledger typography; everything else stays quiet.

### 3.2 Color tokens

| Token | Hex | Role |
|---|---|---|
| `--paper` | `#E9EBE5` | Page background; cool galvanized off-white |
| `--sheet` | `#F4F4EE` | Raised content sheets; never pure white |
| `--ink` | `#14201E` | Primary text; deep green-black |
| `--petrol` | `#173D3D` | Structural headers and dark panels |
| `--oxide` | `#8F3B28` | Links, focus, selected filters and one accent |
| `--brass` | `#7A5A20` | Secondary status/data accent; used sparingly |
| `--muted` | `#66736D` | Secondary text and metadata |
| `--line` | `#B7BFB8` | Rules and ledger dividers |

Contrast must be validated before implementation. Oxide is for interactive text and small accents, not large body copy. Brass is not used as body text.

### 3.3 Typography

Two families with distinct jobs:

- **Display and UI:** `Bricolage Grotesque Variable` (local `@fontsource-variable` package).
- **Long-form body:** `Source Serif 4 Variable` (local `@fontsource-variable` package).

Rules:

- Display: 700–800, tight tracking, sentence case.
- Body: 400, 1.6–1.7 line-height, maximum line length under 80 characters.
- Tables: Bricolage Grotesque 400/600, numeric columns aligned.
- MBIDs only use the existing monospace treatment.
- No all-caps eyebrow labels.
- No single-word color/italic accent inside headlines.
- No decorative typographic labels above sections.

Type scale:

```text
12 / 14 / 16 / 18 / 24 / 32 / 44 / 64
```

### 3.4 Layout concept

Desktop:

```text
┌──────────────────────────────────────────────────────────────┐
│  HMDE              Bands   Albums   Producers      Search    │
├──────────────────┬───────────────────────────────────────────┤
│  INDEX RAIL      │  Production credits, indexed              │
│                  │  band ─── album ─── producer              │
│  57 bands        │                                           │
│  731 albums      │  [ search / taxonomy / period filters ]   │
│  384 producers   │                                           │
│                  │  ledger table                             │
│  API status      │  row · row · row                          │
└──────────────────┴───────────────────────────────────────────┘
```

Detail:

```text
┌──────────────────┬───────────────────────────────────────────┐
│  metadata        │  title / credit sheet                     │
│  taxonomy        │  albums / credits / related entities      │
│  related links   │                                           │
└──────────────────┴───────────────────────────────────────────┘
```

Mobile:

- Index rail becomes a compact masthead and horizontal navigation.
- Filters stack vertically.
- Tables scroll inside a labeled, focusable container; the page itself never scrolls horizontally.
- Detail metadata moves above the main content.

Alignment is left-aligned. No centered marketing layout. The page starts with the product's real information, not a decorative hero.

### 3.5 Structural language

- Lists are ledgers: column headers, ruled rows, no identical rounded cards.
- Panels are square or nearly square; radius is reserved for inputs and buttons.
- Section boundaries use rules and a petrol header field, not drop shadows.
- The selected row or filter uses an oxide left rule.
- The signal-path line `band ─ album ─ producer` is the one memorable visual device.
- No gradients, noise textures, faux tape, skulls or decorative icon sets.

### 3.6 Motion

- No page-load fade/slide sequence.
- Hover and focus transitions are limited to border/background changes.
- Expand/collapse and filter changes may animate only when they explain the state change.
- `prefers-reduced-motion` disables non-essential transitions.

### 3.7 Copy

- Plain, specific language.
- Sentence case.
- No marketing adjectives.
- Errors explain what failed and what to do next.
- Empty states invite the next action.
- Link text names the destination; no appended arrows.

Examples:

- `Search bands`
- `No producers match these filters.`
- `This album has no documented credits in the current dataset.`
- `Try another decade or clear the taxonomy filter.`

### 3.8 Design review against generic defaults

| Default | Decision |
|---|---|
| Cream background + serif display + terracotta accent | Rejected. Cool galvanized paper, grotesque display and oxide accent; serif is used for reading, not the brand headline. |
| Near-black background + acid accent | Rejected. Light industrial surface with petrol structure. |
| Broadsheet hairline columns | Partially avoided. The ledger is asymmetric, uses a persistent rail, petrol fields and stronger rules; it is not a newspaper grid. |
| SaaS card kit | Rejected. Lists are rows and sheets; cards are not the default container. |
| All-caps eyebrows / middle-dot metadata / mono labels / arrow links | Rejected. Sentence-case labels, definition lists and named links. |
| Decorative texture or metal clichés | Rejected. The only memorable device is the index rail plus signal-path line. |

The design spends its boldness on the left index rail and ledger typography. Everything else stays restrained.

## 4. Architecture and data flow

### 4.1 Application shell

- Existing `App.tsx` becomes the route shell with a shared `AppShell`.
- Primary navigation: Bands, Albums, Producers.
- Global search form navigates to `/search?q=...`.
- API status remains visible but quiet.
- Current `/` redirect stays.

### 4.2 API client modules

Add typed modules under `frontend/src/api/`:

```text
bands.ts       existing, extended filters
albums.ts      list/detail
artists.ts     detail
producers.ts   list/detail
search.ts      grouped search
taxonomy.ts    taxonomy tree
```

All response types come from `components['schemas']` in the generated `schema.d.ts`. Shared URL construction and error handling stay in `client.ts`.

### 4.3 URL state

- Search, taxonomy, decade, period, sort and pagination are URL parameters.
- Each page derives query parameters from `useSearchParams`.
- Updating a filter resets `offset` to zero.
- Browser back/forward restores the view.
- Defaults are omitted from the URL.

### 4.4 Query keys

Examples:

```text
['taxonomy']
['bands', { q, taxonomy, decade, yearFrom, yearTo, limit, offset }]
['band', bandId]
['albums', { q, bandId, producerId, decade, taxonomy, limit, offset }]
['album', albumId]
['producers', { q, decade, taxonomy, sort, order, limit, offset }]
['producer', producerId]
['search', { q, limit }]
```

No global store. TanStack Query owns server state; React Router owns URL state.

## 5. Components and responsibilities

| Component or path | Responsibility |
|---|---|
| `frontend/src/App.tsx` | Route shell and global providers. |
| `frontend/src/components/AppShell.tsx` | Masthead, index rail, nav, search entry, API status. |
| `frontend/src/components/TaxonomySelect.tsx` | Dynamic taxonomy filter. |
| `frontend/src/components/PeriodFilter.tsx` | Decade/year filters. |
| `frontend/src/components/Pagination.tsx` | URL-driven pagination controls. |
| `frontend/src/components/ProducerList.tsx` | Producer ledger. |
| `frontend/src/components/AlbumList.tsx` | Album ledger. |
| `frontend/src/components/EntityLinks.tsx` | Band/album/producer links. |
| `frontend/src/pages/BandsPage.tsx` | Band list. |
| `frontend/src/pages/BandDetailPage.tsx` | Band record sheet. |
| `frontend/src/pages/AlbumsPage.tsx` | Album list. |
| `frontend/src/pages/AlbumDetailPage.tsx` | Album record sheet. |
| `frontend/src/pages/ProducersPage.tsx` | Producer rankings. |
| `frontend/src/pages/ProducerDetailPage.tsx` | Producer record sheet. |
| `frontend/src/pages/SearchPage.tsx` | Grouped results. |
| `frontend/src/index.css` | Tokens, shell, ledger, responsive and accessible states. |

No component library is added. Tailwind is not added.

## 6. API integration

E9 consumes only E8 endpoints:

- `/api/v1/bands`, `/api/v1/bands/{id}`, `/api/v1/bands/{id}/graph` (compact E2 view only);
- `/api/v1/albums`, `/api/v1/albums/{id}`;
- `/api/v1/artists/{id}`;
- `/api/v1/credits`;
- `/api/v1/producers`, `/api/v1/producers/{id}`;
- `/api/v1/search`;
- `/api/v1/taxonomy`;
- `/api/v1/analytics/summary` only if a small context strip is useful; not required for E9.

Producer graph endpoints are not rendered in E9. E10 uses `/producers/{id}/graph`.

## 7. Routing and state details

### Bands

`/bands?q=&subgenre=&decade=&year_from=&year_to=&limit=&offset=`

- Search submit updates `q` and resets offset.
- Taxonomy select updates `subgenre`.
- Period and pagination preserve other filters.

### Albums

`/albums?q=&band_id=&producer_id=&decade=&year_from=&year_to=&subgenre=&limit=&offset=`

- Band and producer links from other pages set their IDs.
- Album detail links back to the band and producers.

### Producers

`/producers?q=&decade=&subgenre=&sort=&order=&limit=&offset=`

- Default sort: `album_count` descending.
- Link to detail uses producer ID.

### Search

`/search?q=`

- Empty query shows a prompt, not an API request.
- Results are grouped and bounded by the API.

## 8. Styling and accessibility

- Existing CSS file remains the single styling entry point.
- Add CSS custom properties for the tokens above.
- Replace hard-coded colors with tokens as pages are touched.
- Remove all-caps table headers and uppercase metadata labels; use sentence case.
- Keep visible `:focus-visible` styling; oxide focus ring.
- Add a skip link to main content.
- Table wrappers remain focusable/scrollable on mobile.
- Live regions announce result counts and error changes.
- Reduced motion disables non-essential transitions.
- Contrast checked for paper/ink, paper/petrol, paper/oxide and petrol/sheet.

## 9. Testing strategy

| Level | What is tested | Evidence |
|---|---|---|
| Unit/components | Filter controls, taxonomy select, pagination, entity links, states. | `frontend/src/**/*.test.tsx` |
| Page | Bands, albums, producers, search, details, URL state, empty/error/404. | Vitest + RTL |
| Contract | Generated types and API client shapes. | `npm run typecheck`, API client tests |
| Accessibility | Labels, captions, focusable controls, live regions, keyboard path. | RTL assertions + manual keyboard review |
| Build | Production build and lint. | `npm run lint`, `npm run build` |
| CI | Frontend checks after push. | GitHub Actions |

Commands:

```bash
cd frontend
npm ci
npm run generate:api
npm run lint
npm run typecheck
npm run test
npm run build
```

## 10. Performance and errors

- List pages fetch only one page.
- Detail pages fetch one primary entity plus only the data the page renders.
- No graph fetch in E9.
- No autocomplete requests per keystroke.
- Loading states do not collapse the layout.
- Error states preserve navigation and offer retry.
- Empty states use the API's documented empty responses, not fake data.
- Avoid waterfalls where independent queries can run in parallel.

## 11. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Design becomes generic dashboard | Ledger rows, index rail, signal line and restrained tokens are explicit testable design choices. |
| CSS specificity conflicts | Reuse existing selectors carefully; add component-scoped classes; avoid element/class collisions. |
| Hard-coded taxonomy returns | Tests assert taxonomy is loaded from the API; remove old `SUBGENRES` array. |
| URL state bugs | One filter update helper per page; tests for back/forward and offset reset. |
| API error crashes | Shared `AsyncState` and not-found handling on every page. |
| Mobile tables break layout | Labeled horizontally scrollable table wrappers; page overflow checks. |
| Accessibility regressions | RTL role/label/focus tests and manual keyboard review. |
| Font dependency adds weight | Only two local variable font packages; no runtime CDN. |
| Scope creep into E10 | Producer graph endpoints are not called; graph canvas work is explicitly out of scope. |
| Test fixtures diverge from API | Generated schema is the source of truth; API mocks use the same field names. |

## 12. Deployment and reversibility

- Add `@fontsource-variable/bricolage-grotesque` and `@fontsource-variable/source-serif-4`.
- No Tailwind, no component library, no backend migration.
- Update `package.json`/lockfile and run `npm ci`.
- If the design direction is rejected, revert the CSS/token layer without data impact.
- Generated API types remain produced from `openapi.json`.

## 13. Traceability requirements → plan → tasks

| Requirement | Plan section | Tasks |
|---|---|---|
| FR-001 | 3.4, 4.1 | T-003 |
| FR-002 | 4.2 | T-002 |
| FR-003 | 5, 7 | T-004 |
| FR-004 | 5, 7 | T-004 |
| FR-005 | 5, 7 | T-005 |
| FR-006 | 5, 7 | T-005 |
| FR-007 | 5, 7 | T-006 |
| FR-008 | 5, 7 | T-006 |
| FR-009 | 7 | T-007 |
| FR-010 | 4.3, 8 | T-004 |
| FR-011 | 7 | T-004, T-005 |
| FR-012 | 7 | T-003, T-004, T-005, T-006 |
| FR-013 | 4.3 | T-003, T-007 |
| FR-014 | 10 | T-008 |
| FR-015 | 8 | T-007 |
| FR-016 | 3.4, 8 | T-007 |
| FR-017 | 1, 11 | T-009 |
| FR-018 | 4.2 | T-002 |
| FR-019 | 6 | T-009 |
| FR-020 | 9 | T-010 |

| Non-functional requirement | Plan section | Tasks |
|---|---|---|
| NFR-001 | 3.4, 7 | T-003, T-004, T-005, T-006 |
| NFR-002 | 8 | T-007 |
| NFR-003 | 10 | T-002, T-005, T-006 |
| NFR-004 | 3.4, 8 | T-007 |
| NFR-005 | 3, 5 | T-001, T-008 |
| NFR-006 | 4.2 | T-002 |
| NFR-007 | 10 | T-008 |
| NFR-008 | 1, 11 | T-009 |
| NFR-009 | 3.7 | T-001, T-010 |
| NFR-010 | 9, 12 | T-010 |

## 14. Approval and next step

This plan and `tasks.md` must be approved together before implementation. The first task is T-001: establish the design tokens, local typefaces and ledger foundation.
