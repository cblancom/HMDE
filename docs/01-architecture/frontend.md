# Frontend: entity explorer

- **Status:** E9 validated; E10 graph implemented locally; headless physics, spacing and album-label checks passed; manual interaction and remote CI pending
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
| `/producers/:producerId/graph` | Producer graph, album/band views and force physics |
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

## 6. Graph views

E10 adds a producer graph page with two separate views:

- `view=bands`: producer and band/artist nodes.
- `view=albums`: producer and album nodes.

The page uses the bounded E8 graph endpoint, `cytoscape-d3-force` and the same studio-ledger visual system. Physics can be frozen, resumed or reheated; it pauses when the tab is hidden and starts frozen under `prefers-reduced-motion`.

The force layout must pass `linkId: (node) => node.id`. d3-force links carry canonical UUID endpoints, while its default accessor assumes array indices; omitting the accessor throws `node not found: <uuid>` and, because the layout starts inside a React effect, can unmount the root and blank the page. If a layout cannot start, the component catches the error, applies a static `breadthfirst` layout and freezes physics so the page and table fallback remain available.

Neighbors use type-sized collision radii, stronger repulsion and a link distance computed from the loaded node count and canvas height (180–300, capped to avoid clipping), so they spread around the producer instead of bunching. The canvas grows with the viewport (`clamp(32rem, 65vh, 48rem)`). Album titles are always visible below the node with wrapping and a subtle background; selection adds a border and details, not the label.

Client-side filters cover role, and decade/taxonomy in the album view. Band-view decade/taxonomy controls are disabled because E8 band nodes do not carry album taxonomy/year metadata. API truncation remains visible.

The v0.1 cap is 500 nodes and 2,000 edges. A table fallback lists the loaded nodes and edges.

## 7. Boundary

E10 does not include:

- E8 API or schema changes;
- Tailwind, Plotly or a component library;
- a new graph renderer;
- backend changes, writes or authentication;
- Playwright, performance, accessibility audit or deployment (E11);
- corpus expansion (E13).

## 8. Verification

Local checks on 2026-11-10:

- frontend lint, typecheck, **62 tests**, production build;
- headless Chromium smoke on the `bands` and `albums` graph views (populated root, physics running, table fallback, no console errors); the runtime probe confirmed centered, evenly spaced neighbors and visible album labels;
- backend 313 tests, Ruff and format;
- OpenAPI/type generation;
- `docker compose config -q`;
- no Tailwind/Plotly/UI-kit dependencies;
- no hard-coded taxonomy arrays;
- graph API calls limited to the E8 endpoint.

The last passed remote GitHub Actions CI run [42747146170](https://github.com/cblancom/HMDE/actions/runs/42747146170) covers SPEC-010; SPEC-011 remote CI is pending.
