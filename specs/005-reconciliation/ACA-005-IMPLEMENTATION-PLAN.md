# ACA-005 — Reconciliation Implementation Plan

## 1. Objective

Implement the first deterministic, read-only reconciliation vertical slice defined by `ACA-RECON-001`.

The implementation will consume existing in-memory CodeGraph, Trace, and canonical Evidence contracts. It will not introduce persistence, vector search, LLM inference, runtime tracing, or repository mutation.

## 2. Implementation Sequence

### Phase 1 — Canonical model

Create `src/aca_reconciliation/model.py` containing:

- `RepositoryContext`
- `ReconciliationRequest`
- `CandidateMapping`
- `ReconciliationFinding`
- `ReconciliationResult`
- `ReconciliationValidationError`

Requirements:

- frozen/immutable value semantics where practical;
- deterministic IDs;
- explicit source/target provenance;
- explicit state/provenance semantics;
- canonical JSON serialization;
- deterministic collection ordering.

### Phase 2 — Rule framework

Create a versioned rule abstraction:

- `MappingRule`
- `MappingRuleRegistry`

Initial deterministic rules:

1. canonical identity match;
2. compatible node-type/signature match;
3. structural relationship signal;
4. trace sequence signal;
5. evidence/configuration signal.

Rules return auditable signals rather than directly asserting business equivalence.

### Phase 3 — Mapping engine

Implement:

`source graph → candidate generation → deterministic classification → ambiguity preservation`

Support:

- one-to-one;
- one-to-many;
- many-to-one;
- unresolved candidates.

No silent first-match selection.

### Phase 4 — Structural comparator

Compare mapped CodeGraph content:

- node presence;
- material node properties;
- supported relationships;
- relationship target changes.

Produce deterministic findings for:

- MATCH;
- ADDITION;
- REMOVAL;
- STRUCTURAL_CHANGE;
- RELATIONSHIP_CHANGE;
- AMBIGUOUS_MAPPING;
- CONTRADICTION;
- UNRESOLVED.

### Phase 5 — Trace comparator

Consume compatible Trace objects and compare:

- mapped origins;
- ordered steps;
- relation sequence;
- mapped nodes;
- boundaries;
- alternatives;
- contradictions.

Classify:

- BEHAVIORALLY_ALIGNED;
- BEHAVIORALLY_DIVERGENT;
- BEHAVIORALLY_AMBIGUOUS;
- BEHAVIORALLY_UNRESOLVED.

The comparator must not claim runtime equivalence.

### Phase 6 — Evidence integration

Use the existing canonical EvidenceRegistry/EvidenceResolver.

Validate:

- source evidence belongs to source context;
- target evidence belongs to target context;
- graph/trace references resolve;
- every material finding has supporting evidence or an explicit unresolved boundary.

### Phase 7 — Validation and serialization

Implement:

- complete-result validation;
- ID tamper detection;
- provenance validation;
- confidence/state validation;
- ambiguity/contradiction/boundary validation;
- deterministic JSON serialization;
- round-trip reconstruction.

### Phase 8 — Tests

Build small human-auditable fixtures covering:

1. exact correspondence;
2. source-only artifact;
3. target-only artifact;
4. one-to-many;
5. many-to-one;
6. ambiguity;
7. relationship addition/removal;
8. relationship target change;
9. aligned traces;
10. divergent traces;
11. unresolved trace/evidence;
12. contradiction;
13. analyzer/methodology version differences;
14. checkout-root independence;
15. repeated deterministic execution;
16. malformed/tampered results;
17. read-only behavior.

Tests must assert evidence, state, provenance and stable identity.

## 3. Proposed Package Layout

```text
src/aca_reconciliation/
├── __init__.py
├── model.py
├── rules.py
├── mapping.py
├── structural.py
├── trace.py
├── evidence.py
├── validation.py
└── serialization.py

tests/
└── test_reconciliation.py
```

The implementation may consolidate small modules if doing so reduces unnecessary abstraction; the canonical model should remain isolated from rule implementations.

## 4. Integration Contracts

The implementation should consume, not duplicate:

- `aca_graph.Graph`
- `aca_graph.Trace`
- `aca_evidence.Evidence`
- `aca_evidence.EvidenceRegistry`

The reconciliation package should be exported through `src/aca_reconciliation/__init__.py` and, where appropriate, the ACA package surface.

No changes to CodeGraph or Trace contracts should be required unless implementation exposes a concrete compatibility defect.

## 5. Determinism Rules

For identical:

- source graph;
- target graph;
- supplied traces;
- evidence sets;
- analyzer versions;
- methodology versions;
- request/scope;

the result must have identical:

- mapping IDs;
- finding IDs;
- candidate ordering;
- finding ordering;
- boundary ordering;
- canonical JSON.

No absolute checkout path, timestamp, object identity, or insertion order may affect semantic identity.

## 6. Scope Guardrails

Do not add during the first implementation:

- graph database;
- vector database;
- LLM/embedding dependency;
- runtime instrumentation;
- production connectors;
- automatic code changes;
- migration generation;
- opaque similarity scoring;
- business-equivalence claims.

AI-assisted matching can be added later as a separate inferred-candidate producer.

## 7. Verification Gate

Before implementation PR merge:

1. run the complete test suite;
2. run focused reconciliation tests;
3. verify deterministic output across repeated runs;
4. verify checkout-root independence;
5. verify malformed-input validation;
6. verify evidence provenance;
7. verify read-only behavior;
8. perform independent review;
9. obtain human acceptance only where a defined human gate applies.

## 8. Suggested Implementation PR Sequence

- PR A — canonical reconciliation model + validation + serialization
- PR B — deterministic mapping/rule framework
- PR C — structural reconciliation
- PR D — trace reconciliation + evidence integration
- PR E — integration fixtures, hardening and verification

If the changes remain small and cohesive, PRs A–D may be combined; the canonical model should be established before adding comparison logic.

## 9. Human Review Point

The current specification itself is read-only and does not require a human gate.

A human gate is required before any future implementation that:

- declares business-level equivalence;
- modifies either repository;
- automatically migrates code;
- accesses production systems;
- introduces external data-exfiltration paths.

## 10. Exit Criteria

ACA-005 implementation is ready for downstream use when all ACA-RECON-001 acceptance criteria pass, CI is green, verification evidence is recorded, and the resulting reconciliation artifacts can be consumed by the future specification-generation capability without reinterpretation of canonical provenance.
