# ACA-ADR — Architecture Decision Record Index

**Version:** 0.1

## ADR-001 — Evidence Before AI Reasoning
**Accepted.** Deterministic/static evidence precedes AI interpretation wherever feasible.

## ADR-002 — Evidence and Knowledge Are Distinct
**Accepted.** Observed facts and AI-derived conclusions are separate versioned objects.

## ADR-003 — Polyglot Knowledge Layer
**Proposed.** Use relational state, graph relationships, semantic/search retrieval, and immutable evidence storage for their respective strengths.

## ADR-004 — Specialist Agents
**Accepted.** ACA uses specialized agents with explicit contracts rather than one monolithic coding agent.

## ADR-005 — Independent Verification
**Accepted.** The implementation agent is not the final judge of its own output.

## ADR-006 — Human-on-the-Loop
**Accepted.** Routine work proceeds autonomously; defined high-impact actions require human review.

## ADR-007 — ACA-CQAI as First-Class Capability
**Accepted.** Code quality, architecture, engineering risk, technical debt, and drift are core ACA capabilities.

## Pending Decisions
Technology choices for graph, relational state, semantic search, orchestration, parser stack, sandboxing, and deployment should be evaluated against ACA-EVALUATION-001 and a prototype where practical.
