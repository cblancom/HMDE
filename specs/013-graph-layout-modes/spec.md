# SPEC-013 — Graph overview layout modes

- **Status:** Implemented
- **Stage:** E10
- **Iteration:** MVP
- **Modules:** `api`, `web`
- **Date:** 2026-11-11
- **Depends on:** SPEC-008 (persisted Louvain communities), SPEC-011 (global overview), SPEC-012 (workspace refinements)
- **ADRs:** [ADR-0001](../../docs/01-architecture/adr/ADR-0001-modular-monolith.md), [ADR-0006](../../docs/01-architecture/adr/ADR-0006-read-only-api.md), [ADR-0008](../../docs/01-architecture/adr/ADR-0008-taxonomy-corpus-and-versioning.md)
- **Plan:** [plan.md](plan.md)
- **Tasks:** [tasks.md](tasks.md)
- **Conventions:** [Engineering conventions](../../docs/01-architecture/conventions.md)
- **Owner:** Cristian

## Revision history

| Revision | Date | Change |
|---|---|---|
| 1 | 2026-11-11 | Initial draft: Force/Bipartite/Community selector with server-generated NetworkX layouts and static controls |
| 2 | 2026-11-12 | T-001–T-005 implemented locally; NetworkX layouts, API coordinates, selector, static controls and headless verification passed |

## 1. Context and problem

The global producer overview at `/graph` is useful but visually dense: the force layout mixes producers, bands and albums into a large cloud, which makes shared hubs, production communities and cross-community links difficult to see. SPEC-012 improved the surrounding workspace, but the graph itself still has only one spatial organization.

This spec adds two additional layout modes:

- **Bipartite:** producers on one side, bands or albums on the other, calculated with NetworkX `bipartite_layout`.
- **Community:** producers and associated bands/albums grouped by the Louvain communities already persisted in E7, arranged with a NetworkX-based community cluster layout.

The current **Force** layout remains the default. Both new layouts are server-generated and static. The user can return to Force to restore live physics.

NetworkX has `bipartite_layout` but no dedicated community layout. The community mode therefore reuses the E7 Louvain partition and builds a deterministic cluster layout from a contracted community graph plus `spring_layout` for community centers.

## 2. Users and actors

- **Primary user:** a researcher exploring the global production network who needs to find structural patterns.
- **System actor:** the read-only FastAPI API, NetworkX layout computation and the persisted E7 analysis run.
- **Frontend actor:** React, TanStack Query, Cytoscape and the existing workspace.
- There are no authentication roles or write permissions in this iteration.

## 3. User stories and flows

### US-001 — Separate producers from bands or albums

As a researcher, I want a bipartite layout so that the two sides of the production relationship are visually separated.

**Expected flow:**

1. The user selects `Bipartite` in the Layout selector.
2. The graph requests the current overview with `layout=bipartite`.
3. Producers appear in a left-hand column and bands/albums in a right-hand column.
4. The layout is static; Freeze/Resume/Reheat are disabled with a clear "Static layout" status.
5. Selecting `Force` restores the live force simulation.

### US-002 — Group the network by production community

As a researcher, I want a community layout so that producers who worked in the same discovered cluster appear together with their associated bands and albums.

**Expected flow:**

1. The user selects `Community`.
2. The graph requests the current overview with `layout=community`.
3. Producers are grouped by their persisted E7 Louvain `community_key`.
4. Bands/albums sit with the community of the majority of their producers.
5. Cross-community shared nodes remain visible as links between clusters.
6. The status explains that the layout is static.

### US-003 — Recover when a layout is unavailable

As a researcher, I want the graph to remain usable if a requested layout cannot be calculated.

**Expected flow:**

1. The requested layout fails or returns incomplete coordinates.
2. The frontend falls back to the Force layout.
3. A non-blocking notice explains that the requested layout was unavailable.
4. Selection, filters, details and the accessible table remain usable.

## 4. Functional requirements

### FR-001 — Layout selector

The global overview must expose a Layout selector with `Force`, `Bipartite` and `Community`. Force is the default. The selected mode is stored in the URL as `layout=force|bipartite|community`, and changing it updates the graph query without leaving `/graph`.

**Verification:** page tests and URL assertions.

### FR-002 — Bipartite layout

The backend must calculate a deterministic bipartite layout over the nodes returned by the overview:

- partition 0: producer nodes;
- partition 1: band or album target nodes;
- producers on the left, targets on the right.

The implementation uses NetworkX `bipartite_layout` with vertical alignment. If NetworkX cannot resolve a disconnected graph, a deterministic two-column fallback is used. Every returned node must have coordinates.

**Verification:** backend unit tests with connected, disconnected and isolated nodes.

### FR-003 — Community layout

The backend must calculate a deterministic community layout:

1. read the persisted Louvain communities for the E7 run;
2. assign each producer to its `community_key`;
3. assign each band/album to the community with the most incident producers (tie broken deterministically);
4. create an `unassigned` group for nodes without community data;
5. position communities with a contracted community graph and `spring_layout` using a fixed seed;
6. place community members deterministically around their community center.

Every returned node must have coordinates. Shared bands/albums may create edges between community clusters.

**Verification:** backend unit tests for majority assignment, unassigned nodes, deterministic output and multi-community targets.

### FR-004 — Layout API contract

`GET /api/v1/graph/producers` must accept an optional `layout=bipartite|community` query parameter. When present, the response includes an additive optional `layout` object:

```json
{
  "algorithm": "bipartite",
  "nodes": [{ "id": "entity-uuid", "x": 0.0, "y": 0.0 }]
}
```

When `layout` is absent, the response and the current Force behavior are unchanged. The endpoint remains read-only and adds no migration or persisted layout artifact.

**Verification:** integration tests and OpenAPI schema tests.

### FR-005 — Static layout behavior

When the response includes layout coordinates, Cytoscape applies them as a static preset layout and fits the graph. Freeze, Resume and Reheat are disabled and the status reads `Static layout`. Node dragging, selection, details, search, resizing and accessible table behavior remain available.

**Verification:** component tests and headless interaction checks.

### FR-006 — Force remains available

Selecting `Force` removes the layout parameter, uses the existing d3-force preset, and re-enables Freeze/Resume/Reheat. No existing force behavior regresses.

**Verification:** existing graph tests plus a new Force-mode test.

### FR-007 — Server and client filter interaction

View, producer selection, decade and subgenre changes recompute the server-selected graph and its layout. Client-only role, search and isolated-producer filters continue to hide nodes after load; they do not recompute server coordinates. The graph must remain usable when hidden nodes were part of the layout calculation.

**Verification:** page tests and documented limitation.

### FR-008 — Fallbacks

- A disconnected bipartite graph uses the deterministic two-column fallback.
- Nodes without community data go to `unassigned`.
- A layout computation error must not fail the overview response; `layout` is omitted.
- If the frontend receives no coordinates or incomplete coordinates for the requested mode, it falls back to Force with a visible notice.

**Verification:** backend failure tests and frontend fallback tests.

### FR-009 — Scope

The new layouts apply only to `/graph`. The producer ego graph at `/producers/:id/graph` and its API response remain unchanged.

**Verification:** route/client scope inspection.

## 5. Non-functional requirements

### NFR-001 — Determinism

For the same analysis run, view, filters, node set and layout mode, the coordinates must be identical across requests. Community and spring calculations use fixed seeds and sorted inputs.

### NFR-002 — Performance

The layout must complete acceptably for the current 398-node bands view and 968-node albums view. The frontend must continue to render and interact with the graph without blocking navigation. Coordinates are returned only when requested.

### NFR-003 — Scope and dependencies

NetworkX is already a backend dependency. This spec adds no new dependency, database table, migration, write operation or graph renderer. The API change is additive.

### NFR-004 — Accessibility and responsive behavior

The selector has a visible label, keyboard focus and an explicit current value. Static-mode controls expose their disabled state and the reason. The graph remains usable with the existing responsive workspace and table fallback. Color is not used to encode communities in this spec.

## 6. Business rules

- **BR-001:** Producer nodes are the left partition; band and album nodes are the right partition.
- **BR-002:** The community partition is the persisted E7 Louvain `community_key` of each producer.
- **BR-003:** A shared band or album is assigned to the community with the highest number of incident producers; ties are broken by community key.
- **BR-004:** Static layouts do not run d3-force. Force is restored only by selecting `Force`.
- **BR-005:** Client-only display filters do not trigger a new server layout; server-selected filters do.

## 7. Edge cases and errors

- Disconnected graph in bipartite mode: deterministic two-column fallback.
- No communities in the analysis run: all nodes go to `unassigned`; the graph still renders.
- Single community: the cluster is centered and members are placed around it.
- Isolated producer: included in its community or `unassigned` cluster.
- Band/album with no producer community: assigned to `unassigned`.
- Layout calculation failure: overview returns without layout; frontend falls back to Force.
- Missing or duplicate coordinates: frontend rejects the layout and falls back to Force.
- Truncated overview: layout only covers the returned/truncated node set; truncation remains visible.
- Static layout while the user changes role or isolated filters: positions remain stable; hidden nodes are simply removed.
- Reduced motion: static layouts have no motion; Force retains the existing frozen start.

## 8. Out of scope

- Changing the producer ego graph or its API.
- New community detection algorithms or new community persistence.
- Recoloring nodes by community or drawing community hulls.
- User-resizable nodes or manual layout editing.
- New dependencies, database schema, migrations or writes.
- Layout persistence across sessions or analysis runs.

## 9. Acceptance criteria

| ID | Criterion | Evidence |
|---|---|---|
| AC-001 | `/graph` has a Force/Bipartite/Community selector with URL state. | Page/URL tests |
| AC-002 | Bipartite returns coordinates for every node, with producer x-coordinates strictly left of target x-coordinates. | Backend unit test |
| AC-003 | Community groups producers by persisted community and assigns shared targets to the majority community. | Backend unit test |
| AC-004 | The overview response includes an optional layout block only when requested. | Integration/OpenAPI tests |
| AC-005 | Static layouts fit the graph and disable Freeze/Resume/Reheat with a clear status. | Component/headless tests |
| AC-006 | Force remains the default and restores live physics after a static layout. | Page/component tests |
| AC-007 | Disconnected, missing-community, missing-coordinate and computation-error cases fall back safely. | Backend/frontend tests |
| AC-008 | Repeating the same layout request returns identical coordinates. | Backend determinism test |
| AC-009 | Both layouts are usable in the current 398/968-node corpus without blocking the page. | Headless performance probe |
| AC-010 | The ego graph and its API remain unchanged. | Scope inspection |
| AC-011 | The existing accessible table, selection, details and resize behavior remain available in static modes. | Component/headless tests |
| AC-012 | Backend/frontend lint, tests, OpenAPI generation and build pass. | Local commands |

## 10. Assumptions and open questions

### Assumptions

- The E7 Louvain communities are the canonical producer communities for this iteration.
- NetworkX `bipartite_layout` and `spring_layout` are sufficient for the MVP; no specialized third-party layout is added.
- Static layouts are acceptable for the two new modes; Force remains the interactive physics mode.
- The layout selector is a `Force`/`Bipartite`/`Community` select, not two independent toggles.
- Client-only display filters do not trigger a server layout recalculation.
- The new spec is `013`; planned E11–E13 placeholder specs move to `014`–`016`.

### Open questions

No blocking question remains. Exact spring constants, cluster radii and visual tuning are plan-level details.

## 11. Validation result

- **Date:** 2026-11-12
- **Verdict:** Implemented locally; remote CI pending. All acceptance criteria have local automated or headless evidence.
- **Evidence:**
  - backend 225 unit and 332 full-suite tests passed; Ruff/format passed; OpenAPI drift unchanged;
  - backend layout tests cover deterministic bipartite ordering, disconnected/isolated nodes, community majority/unassigned handling, single-community/no-edge cases and empty graphs;
  - integration tests cover both layout modes, optional/absent coordinates, invalid values, determinism and a computation-error fallback;
  - frontend lint, typecheck, 98 tests and production build passed;
  - headless Chromium at 1440 px confirmed Force physics, Bipartite left/right columns (producer x 80, album x 920), Community clusters, static status, disabled physics controls and a return to Force; 968 nodes fit the canvas;
  - layout requests at 1440/968 nodes took about 0.16 s for Bipartite and 0.25 s for Community including response transfer.

## 12. References

- [Constitution](../../constitution.md)
- [AGENTS.md](../../AGENTS.md)
- [Roadmap](../../docs/00-vision/roadmap.md)
- [Frontend explorer](../../docs/01-architecture/frontend.md)
- [Producer network analysis](../../docs/03-data/network-analysis.md)
- [Read-only API v1](../../docs/03-data/api-v1.md)
- [SPEC-008 — Network analysis](../008-network-analysis/spec.md)
- [SPEC-011 — Graph visualization](../011-graph-visualization/spec.md)
- [SPEC-012 — Graph overview refinements](../012-graph-overview-refinements/spec.md)
