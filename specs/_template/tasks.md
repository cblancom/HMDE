# Tasks — SPEC-NNN

- **Status:** Draft
- **Spec:** [spec.md](spec.md)
- **Plan:** [plan.md](plan.md)

## 1. Execution order

```text
T-001 ──► T-002 ──► T-004
              └───► T-003 ──► T-005
```

State which tasks can run in parallel and which are integration points.

## 2. Tasks

### T-001 — Task title

- **Requirements:** FR-001, NFR-001.
- **Dependencies:** none.
- **Description:** …
- **Done when:** …
- **Verification:**
  ```bash
  command to run
  ```
- **Files:** `path/to/file`, `path/to/test`.
- **Evidence:** Pending.

### T-002 — Task title

- **Requirements:** …
- **Dependencies:** T-001.
- **Description:** …
- **Done when:** …
- **Verification:**
  ```bash
  command to run
  ```
- **Files:** …
- **Evidence:** Pending.

## 3. Coverage matrix

### Functional requirements

| Requirement | Tasks |
|---|---|
| FR-001 | T-001 |
| FR-002 | T-002 |

### Non-functional requirements

| Requirement | Tasks |
|---|---|
| NFR-001 | T-001 |

## 4. Validation evidence

| Criterion | Result | Evidence |
|---|---|---|
| AC-001 | Pending | … |
| AC-002 | Pending | … |

Update this table when the feature is validated. Include commands, outputs, links to tests or manual checks.

## 5. Notes

- Decisions discovered during implementation are reflected first in `spec.md` or `plan.md`.
- Do not mark a task complete unless its verification was executed.
- Record follow-up debt or open issues here.
