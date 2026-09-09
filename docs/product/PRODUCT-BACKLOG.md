# Initial Product Backlog

The GitHub Project is the collaboration/control plane. These items define the initial product sequence.

| ID | Epic | Item | Priority | Phase |
|---|---|---|---|---|
| EPIC-000 | Product Foundation | SPEC-000 Architecture | P0 | Specification |
| EPIC-001 | Repository Intelligence | SPEC-001 Repository Ingestion | P0 | Specification |
| EPIC-002 | Code Intelligence Graph | SPEC-002 CodeGraph | P0 | Specification |
| EPIC-003 | Trace Engine | SPEC-003 End-to-End Trace | P0 | Specification |
| EPIC-004 | Evidence Engine | SPEC-004 Evidence | P0 | Specification |
| EPIC-005 | Mainet ↔ UPYOG | SPEC-005 Reconciliation | P1 | Specification |
| EPIC-006 | Specification Generator | SPEC-006 Spec Generation | P1 | Specification |

## Delivery sequence

SPEC-000 → SPEC-001 → SPEC-002 → SPEC-003 → SPEC-004 → SPEC-005 → SPEC-006

Each item follows:

```text
Specification → Acceptance Criteria → Issue → Implementation → Tests → Evidence → PR → Acceptance
```
