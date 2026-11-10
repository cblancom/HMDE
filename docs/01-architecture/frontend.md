# Frontend: entity explorer

- **Status:** Implemented locally; remote CI pending
- **Stage:** E9
- **Spec:** [SPEC-010](../../specs/010-entity-explorer/spec.md)
- **Design plan:** [plan.md](../../specs/010-entity-explorer/plan.md)

## 1. Routes

| Route | Purpose |
|---|---|
| `/` | Redirects to `/bands` |
| `/bands` | Searchable band ledger with taxonomy, decade and pagination |
| `/bands/:bandId` | Band detail, albums, credits and compact E2 producer view |
| `/albums` | Searchable album ledger |
| `/albums/:albumId` | Album detail, taxonomy and support-aware credits |
| `/producers` | Producer rankings with sort, search and filters |
| `/producers/:producerId` | Producer metrics, community, top albums and bands |
| `/search?q=` | Grouped bounded search |
| `*` | Not-found page |

## 2. Design direction

The interface is a **studio production ledger**, not a generic dashboard.

- Cool galvanized paper (`#E9EBE5`) with petrol structure (`#173D3D`).
- Oxide (`#8F3B28`) marks links, focus and selection; brass (`#7A5A20`) is a restrained secondary accent.
- Bricolage Grotesque carries display/UI; Source Serif 4 carries reading text.
- A persistent index rail and `band — album — producer` signal path are the memorable structural devices.
- Lists are ruled ledgers with no identical rounded-card kit.
- No all-caps eyebrows, middle-dot metadata strings, mono data labels or decorative metal clichés.
- Motion is limited to user-triggered state changes; reduced motion is respected.

Tailwind is deferred. The app uses the existing CSS architecture with custom properties.

## 3. State model

- React Router owns URL state: search, taxonomy, decade, sort and pagination.
- TanStack Query owns server state.
- Changing a filter resets `offset`.
- Browser back/forward restores list views.
- No global state store.

## 4. API clients

Typed modules under `frontend/src/api/` import response types from the generated `schema.d.ts`:

- `bands.ts`
- `albums.ts`
- `artists.ts`
- `producers.ts`
- `search.ts`
- `taxonomy.ts`
- `queryKeys.ts`

No hand-written duplicate entity interfaces.

## 5. Accessibility

- Skip link to `#main-content`.
- Visible oxide focus ring.
- Semantic headings and form labels.
- Table captions and column headers.
- Focusable, horizontally scrollable table wrappers.
- Live result/status announcements.
- Error, empty and not-found states with next actions.
- Reduced-motion media query.
- Cytoscape initialization is guarded when canvas is unavailable.

## 6. Boundary

E9 does not include:

- the full producer graph page (E10);
- producer graph API calls;
- Tailwind, Plotly or a component library;
- backend, API or schema changes;
- writes or authentication.

## 7. Verification

Local checks on 2026-11-10:

- frontend lint, typecheck, **42 tests**, production build;
- backend 313 tests, Ruff and format;
- OpenAPI/type generation;
- `docker compose config -q`;
- no Tailwind/Plotly/UI-kit dependencies;
- no hard-coded taxonomy arrays;
- no producer graph endpoint calls.

Remote CI is pending because no commit or push was performed.
