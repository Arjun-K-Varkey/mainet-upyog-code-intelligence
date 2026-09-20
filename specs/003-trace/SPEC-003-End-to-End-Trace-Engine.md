# SPEC-003 — End-to-End Trace Engine

**ACA ID:** ACA-003  
**Version:** 0.1  
**Status:** Implementation Ready  
**Capability:** Trace / Impact Analysis  
**Milestone:** M1  
**Depends on:** ACA-002 / SPEC-002 CodeGraph

## 1. Objective

Define a deterministic, evidence-backed trace capability over the canonical ACA Engineering Graph.

A trace represents a bounded, queryable path through engineering relationships and preserves the evidence, provenance, confidence and validation state supporting the path.

The first implementation operates on the in-memory deterministic CodeGraph established by SPEC-002. It must not require a graph database, runtime execution or AI reasoning.

The long-term target is application-flow tracing such as:

`JSP → Controller → Service → DAO/Repository → SQL → Database → External System`

but SPEC-003 must only claim relationships that are actually represented by the current graph.

## 2. Scope

SPEC-003 defines:

1. Trace request semantics.
2. Trace result and path models.
3. Deterministic traversal.
4. Relationship filtering.
5. Direction and depth constraints.
6. Repository/revision isolation.
7. Evidence and provenance propagation.
8. Confidence and trace-state semantics.
9. Ambiguous, contradicted and unknown outcomes.
10. Deterministic serialization.
11. Validation.
12. Read-only behavior.
13. Automated verification.

## 3. Non-Goals

SPEC-003 shall not:

- implement a full Java semantic parser;
- infer framework behavior without evidence;
- perform runtime tracing;
- execute analyzed source code;
- require a graph database;
- introduce an LLM or agent for path discovery;
- fabricate edges for unknown relationships;
- automatically modify source code;
- automatically remediate findings;
- claim complete JSP/controller/service/DAO/SQL tracing until the required semantic relationships exist.

## 4. Trace Model

A trace result contains:

- trace schema version;
- trace identifier;
- repository identifier;
- revision;
- analysis-run identity;
- source node;
- target node;
- ordered path nodes;
- ordered path edges;
- aggregate trace state;
- evidence references;
- provenance summary;
- confidence;
- traversal metadata.

A path is an ordered sequence:

`N0 --E1--> N1 --E2--> ... --En--> Nn`

Every edge in a returned path must resolve to a graph edge and every node must resolve to a graph node in the same repository/revision context.

## 5. Trace Request

A trace request shall support:

- source node ID;
- optional target node ID;
- direction: OUTGOING, INCOMING, or BOTH;
- maximum depth;
- optional allowed relationship types;
- optional excluded relationship types;
- optional node-type constraints;
- optional maximum number of returned paths.

Requests must be validated before traversal.

Maximum depth is mandatory or must resolve to a bounded implementation default. Unbounded traversal is not permitted in the initial implementation.

## 6. Deterministic Traversal

Given the same:

- graph schema version;
- repository;
- revision;
- graph content;
- trace request;

the trace engine shall return byte-equivalent canonical results.

Traversal ordering must be deterministic. Node and edge identifiers shall be used as stable tie-breakers whenever multiple valid traversal choices exist.

The engine must not depend on:

- hash-map iteration order;
- filesystem ordering;
- timestamps;
- process identity;
- random values;
- network responses.

## 7. Relationship Semantics

SPEC-003 consumes the relationship semantics established by CodeGraph.

Initially supported relationships include those present in the graph, such as:

- CONTAINS
- DECLARES
- IMPLEMENTS
- EXTENDS
- CALLS
- REFERENCES
- DEPENDS_ON
- INJECTS

The trace engine must treat relationship availability as data, not assumption.

If a requested application-flow relationship is absent, the engine must not invent a substitute edge.

## 8. Trace State

Every trace result has one primary state:

### CONFIRMED

All path relationships are deterministic and supported by valid evidence.

### INFERRED

At least one path relationship is inferred and carries valid evidence and confidence.

### AMBIGUOUS

Multiple materially different candidate paths satisfy the request and available evidence does not establish a unique path.

### CONTRADICTED

Available evidence contains mutually incompatible relationships or evidence states relevant to the requested trace.

### UNKNOWN

The requested relationship/path cannot be established from available evidence.

UNKNOWN is a result state, not permission to create an UNKNOWN graph edge.

## 9. Confidence

Trace confidence is distinct from node/edge identity.

For a path containing only deterministic relationships, confidence is derived as the deterministic maximum state and does not require an arbitrary numeric value.

For inferred paths, confidence must be derived deterministically from the participating inferred relationships according to an explicitly versioned aggregation rule.

The initial implementation may use the minimum confidence of participating inferred edges as the conservative path confidence.

No confidence value may be fabricated merely because a path exists.

## 10. Evidence and Provenance

Every returned trace must retain references to the evidence supporting its path.

For each path edge, the engine shall be able to identify:

- edge identity;
- edge provenance;
- edge evidence references;
- edge confidence when inferred.

Trace-level evidence is the deterministic union of evidence references from the path, emitted in canonical order.

The trace engine must not replace source evidence with an unsupported textual explanation.

## 11. Ambiguity Handling

When multiple candidate paths are materially distinct:

1. Preserve each candidate within configured limits.
2. Mark the result AMBIGUOUS when available evidence cannot establish a unique path.
3. Do not select a winner using heuristics that are not part of the specification.
4. Preserve evidence for each candidate.
5. Apply deterministic ordering to candidates.

A later specification may define domain-specific disambiguation rules.

## 12. Contradiction Handling

A contradiction exists when evidence relevant to a trace supports mutually incompatible claims that cannot both be accepted under the current graph contract.

The trace engine must:

- preserve the conflicting evidence references;
- mark the affected result CONTRADICTED;
- avoid silently choosing one interpretation;
- keep deterministic output ordering.

Contradiction detection must be explicit and testable.

## 13. Unknown Handling

The engine must distinguish:

- no path found;
- relationship not represented;
- evidence insufficient;
- unsupported relationship type.

These conditions may all result in UNKNOWN, but the reason must remain machine-readable.

The engine must never transform absence of evidence into evidence of absence.

## 14. Repository and Revision Isolation

A trace may traverse only nodes and edges belonging to the requested repository and revision context.

Cross-repository or cross-revision paths are rejected unless a later specification explicitly introduces a governed cross-boundary relationship.

This protects trace determinism and prevents accidental contamination from unrelated analyses.

## 15. Validation

The trace engine shall validate:

1. Source node exists.
2. Target node exists when supplied.
3. Source and target belong to the requested graph context.
4. Maximum depth is valid and bounded.
5. Requested relationship types are valid.
6. Every returned path edge exists.
7. Every path edge connects the adjacent path nodes.
8. Evidence references resolve.
9. Inferred edges contain confidence.
10. Deterministic edges do not contain fabricated confidence.
11. Trace identifiers are reproducible.
12. Serialized trace results pass validation before loading.

Validation failures must be machine-readable.

## 16. Trace Identity

A trace identifier shall be derived deterministically from:

- trace schema version;
- repository identity;
- revision;
- source canonical identity;
- target canonical identity when present;
- traversal direction;
- depth;
- relationship filters;
- node filters;
- path-selection constraints.

Volatile analysis timestamps must not participate in semantic trace identity.

## 17. Serialization

The canonical trace representation shall be JSON.

Required top-level fields:

- schema_version
- trace_id
- repository_id
- revision
- analysis_run_id
- request
- source
- target
- paths
- state
- evidence_refs
- provenance
- confidence
- traversal

Paths, nodes, edges and evidence references must use deterministic ordering.

Serialization/deserialization must preserve trace semantics.

## 18. Safety

Trace construction is read-only.

It must not:

- execute repository code;
- invoke build lifecycle hooks;
- modify source files;
- modify Git metadata;
- require network access;
- mutate the CodeGraph.

## 19. Required API Operations

The initial trace API/model shall support:

- trace from source;
- trace from source to target;
- incoming trace;
- outgoing trace;
- bounded bidirectional trace;
- relationship-filtered trace;
- node-type-filtered trace;
- deterministic serialization;
- trace validation.

Implementation-specific APIs are intentionally left to the implementation specification.

## 20. Acceptance Criteria

### AC-01 — Trace model

A trace has a complete machine-readable request, result, path, state, provenance and evidence representation.

### AC-02 — Deterministic traversal

Equivalent graph and request inputs produce equivalent ordered trace results.

### AC-03 — Bounded traversal

Traversal always terminates within configured depth/path limits.

### AC-04 — Evidence preservation

Every returned path retains resolvable evidence references.

### AC-05 — Provenance

Every path edge retains deterministic/inferred provenance and confidence semantics.

### AC-06 — State semantics

CONFIRMED, INFERRED, AMBIGUOUS, CONTRADICTED and UNKNOWN are explicitly represented and testable.

### AC-07 — Context isolation

No path crosses repository or revision boundaries.

### AC-08 — Validation

Malformed requests, invalid paths, unresolved evidence and inconsistent graph context are rejected deterministically.

### AC-09 — Serialization

Equivalent trace results serialize deterministically and survive round-trip validation.

### AC-10 — Safety

Trace execution does not modify or execute the analyzed repository or mutate the graph.

### AC-11 — Automated verification

Tests cover direct paths, multi-hop paths, no-path results, depth limits, relationship filtering, ambiguity, evidence, deterministic ordering, serialization and validation.

## 21. Test Strategy

Required test categories:

- unit tests for trace request/result models;
- direct one-hop trace fixtures;
- multi-hop deterministic fixtures;
- no-path and UNKNOWN fixtures;
- depth-boundary tests;
- relationship-filter tests;
- incoming/outgoing/bidirectional tests;
- evidence/provenance tests;
- inferred-confidence tests;
- ambiguous-path tests;
- contradicted-evidence tests;
- repository/revision isolation tests;
- deterministic serialization golden fixtures;
- malformed serialized trace tests;
- read-only safety tests.

Fixtures must remain small and human-auditable.

## 22. Implementation Guidance

Keep the trace engine independent from parser-specific logic.

Use the existing CodeGraph traversal primitives from SPEC-002 rather than duplicating graph storage or identity logic.

Prefer a dependency-light Python implementation consistent with ACA's current foundation.

Do not introduce a graph database, parser framework or AI runtime as part of SPEC-003.

## 23. Downstream Dependencies

SPEC-004 uses trace evidence and provenance for evidence management.

SPEC-005 uses traces to reconcile Mainet and UPYOG behavior.

SPEC-006 uses traces as evidence for specification generation.

ACA-CQAI uses traces for impact analysis, dependency reasoning and architecture findings.

Future Java parser/symbol/dependency capabilities may add richer graph relationships consumed by the same trace contract.

## 24. Human Review Gates

Human review is required before:

- introducing a persistent graph database;
- introducing a major parser/framework dependency;
- changing the trace contract incompatibly;
- adding production integrations;
- allowing runtime execution or repository mutation.

The initial deterministic in-memory trace implementation does not require a human gate before routine implementation, but final acceptance of the significant deliverable remains governed by ACA's human-on-the-loop policy.

## 25. Traceability

| Requirement | Acceptance | Downstream use |
|---|---|---|
| Trace model | AC-01 | All trace consumers |
| Determinism | AC-02 | Reproducibility |
| Bounded traversal | AC-03 | Safety |
| Evidence | AC-04 | Evidence/CQAI |
| Provenance | AC-05 | Confidence/verification |
| Trace states | AC-06 | Uncertainty handling |
| Context isolation | AC-07 | Multi-analysis safety |
| Validation | AC-08 | Verification |
| Serialization | AC-09 | Persistence/agents |
| Safety | AC-10 | Governance |
| Tests | AC-11 | CI/verification |

## 26. Definition of Done

SPEC-003 is complete only when:

1. This specification is versioned.
2. Trace request/result contracts are implemented.
3. CodeGraph traversal is consumed without duplicated graph identity logic.
4. Deterministic trace ordering is verified.
5. Evidence and provenance are preserved.
6. Uncertainty states are tested.
7. Serialization and validation are tested.
8. Repository/revision isolation is verified.
9. Read-only behavior is verified.
10. CI passes.
11. Verification evidence is recorded.
12. The capability is integrated into the ACA M1 vertical slice.
13. Human acceptance is obtained where a defined human-review gate applies.
