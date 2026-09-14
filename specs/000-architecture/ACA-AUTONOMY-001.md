# ACA-AUTONOMY-001 — Human Review & Autonomy Policy

**Version:** 0.1  
**Status:** Initial policy

## Operating Model
ACA is human-on-the-loop. Routine engineering work should proceed without repeated permission requests.

## Autonomy Levels
- A0: Observe
- A1: Analyze and recommend
- A2: Execute reversible changes
- A3: Execute autonomous engineering workflows with human gates
- A4: Production-impacting autonomy requiring explicit authorization

**Target:** A3.

## Autonomous Work
Repository indexing, deterministic analysis, documentation, graph construction, test generation/execution, static analysis, specification drafting, backlog maintenance, reversible implementation, verification, and status reporting.

## Mandatory Human Gates
Major architecture decisions; database/schema changes; breaking API/interface changes; security-sensitive changes; major dependency decisions; production-impacting operations; unresolved business rules; irreversible/high-risk actions; final acceptance of significant deliverables.

## Review Package
A human gate must include the decision required, context, evidence, alternatives, recommendation, impact, risk, recovery/rollback plan, and verification status.
