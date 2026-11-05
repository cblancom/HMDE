# Technical plan — SPEC-NNN

- **Status:** Draft
- **Spec:** [spec.md](spec.md)
- **Tasks:** [tasks.md](tasks.md)
- **ADRs:** —
- **Module:** —

## 1. Solution summary

How the feature will be implemented, in a few paragraphs. State what is explicitly not included.

## 2. Architecture and data flow

Describe the components involved and the flow between them. Use a small text diagram when it clarifies the design.

```text
…
```

## 3. Components and responsibilities

| Component or path | Responsibility |
|---|---|
| `backend/...` | … |
| `frontend/...` | … |
| `specs/...` | … |

Do not list files that will not change.

## 4. Technical decisions and alternatives

### 4.1 Decision

…

### 4.2 Alternatives considered

| Alternative | Reason for rejection |
|---|---|
| … | … |

## 5. Data model and migrations

- New or modified tables.
- Columns, constraints and indexes.
- Alembic migration and downgrade.
- Provenance, confidence and quarantine fields.
- Dataset or fixture impact.

## 6. API contract

- Endpoints and methods.
- Request and response schemas.
- Pagination, filters and errors.
- Status codes.
- OpenAPI and TypeScript type impact.

## 7. Frontend impact

- Routes and components.
- Server state and caching.
- Loading, error and empty states.
- Filter state in the URL.
- Accessibility and performance limits.

## 8. Error handling and consistency

- Invalid input.
- Empty state.
- External source failure.
- Partial or conflicting data.
- Transaction boundaries and rollback.
- Idempotency.

## 9. Security and trust boundaries

- Authentication and authorization impact.
- Input validation.
- Secrets and configuration.
- CORS and rate limits.
- Source licensing and data exposure.

## 10. Observability

- Logs.
- Run records.
- Quality or coverage reports.
- Metrics or traces, only if justified.

## 11. Testing strategy

| Level | What is tested | Evidence |
|---|---|---|
| Unit | … | `backend/tests/...` |
| Integration | … | … |
| Contract | … | … |
| Frontend | … | … |
| End-to-end | … | … |
| Manual | … | … |

Include the exact verification commands.

## 12. Deployment and reversibility

- Migration order.
- Environment variables.
- Compatibility and rollback.
- Data restoration or cleanup.

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| … | … |

## 14. Traceability requirements → plan → tasks

| Requirement | Plan section | Tasks |
|---|---|---|
| FR-001 | … | T-001 |
| NFR-001 | … | T-002 |
| AC-001 | … | T-001 |

## 15. Approval and next step

This plan must be approved together with `tasks.md` before implementation starts. The first task is …
