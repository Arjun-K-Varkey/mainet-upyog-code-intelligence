# ACA-TRACE-001 — Evidence-Backed End-to-End Trace Model

**ACA ID:** ACA-003  
**Version:** 0.1  
**Status:** Implementation Ready  
**Capability:** Trace Intelligence  
**Milestone:** M1  
**Depends on:** ACA-001 Repository Ingestion, ACA-002 CodeGraph

## 1. Objective

Define a deterministic, evidence-backed trace capability for reconstructing application execution/data paths across heterogeneous enterprise application layers.

The primary target path is:

`JSP → Controller → Service → DAO/Repository → SQL → Database → External System`

ACA must distinguish facts established directly by deterministic analysis from inferred, ambiguous, contradicted, and unknown relationships.

A trace is a structured engineering claim, not merely a graph path. Every material hop must retain provenance and evidence.

## 2. Scope

The initial trace model shall support:

- trace requests anchored at a known source node or artifact;
- ordered trace steps;
- graph relationships used as trace evidence;
- deterministic and inferred hops;
- confidence metadata;
- trace status;
- alternative/ambiguous paths;
- contradictions;
- unknown/unresolved hops;
- evidence references;
- analysis-run identity;
- reproducible trace results;
- trace summaries suitable for downstream specification, CQAI and impact analysis.

The initial implementation should prioritize the Java/JSP enterprise path while keeping the model extensible to REST/SOAP, messaging and configuration-driven integrations.

## 3. Non-Goals

The initial implementation shall not:

- claim runtime execution when only static evidence exists;
- invent missing hops;
- infer business intent without evidence;
- guarantee complete tracing of reflection/dynamic proxies/generated code;
- execute application code;
- connect to production systems;
- modify the analyzed repository;
- automatically remediate code;
- replace the canonical CodeGraph.

## 4. Trace Concepts

### 4.1 Trace

A Trace represents a reproducible analysis result connecting an origin to a target or an unresolved endpoint.

Required fields:

- trace_id
- repository_id
- revision
- analysis_run_id
- origin
- target, when resolved
- status
- confidence
- steps
- evidence_refs
- analyzer_version
- methodology_version

### 4.2 Trace Step

A Trace Step represents one hop between two engineering entities.

Required fields:

- step_id
- sequence
- source_node
- relation
- target_node, when known
- status
- provenance
- confidence
- evidence_refs
- rationale, when inferred or ambiguous

### 4.3 Trace Status

Allowed statuses:

- **CONFIRMED** — supported by deterministic evidence.
- **INFERRED** — supported by evidence but requires interpretation.
- **AMBIGUOUS** — multiple materially plausible paths exist and cannot be deterministically resolved.
- **CONTRADICTED** — available evidence conflicts with the proposed relationship.
- **UNKNOWN** — required evidence is absent or insufficient.

These statuses apply to both complete traces and individual steps.

## 5. Provenance and Confidence

Allowed provenance:

- deterministic
- inferred

Deterministic means the relationship is directly established by supported source/build metadata, AST analysis, explicit configuration, or an existing canonical graph relationship.

Inferred means the relationship is derived by a documented rule from available evidence but is not directly established.

Confidence is required for inferred steps and recommended for trace-level summaries.

Confidence must not override status. A high-confidence inference remains an inference.

ACA must never convert UNKNOWN or AMBIGUOUS evidence into a confirmed relationship solely because a heuristic produces a plausible candidate.

## 6. Evidence Contract

Every trace step must reference the evidence supporting the hop.

Evidence may originate from:

- source file and source location;
- CodeGraph node/edge;
- Java/JSP structural analysis;
- annotations;
- Spring/XML configuration;
- Maven/Gradle metadata;
- SQL statements;
- JDBC/JPA/Hibernate mappings;
- REST/SOAP client declarations;
- messaging configuration;
- deterministic naming or binding rules.

Evidence references must resolve to ACA evidence records or graph evidence identities.

A trace without supporting evidence must be represented as UNKNOWN rather than asserted as fact.

## 7. Deterministic Tracing Methodology

The trace engine shall operate in stages:

1. Resolve the origin node/artifact.
2. Identify eligible outgoing graph relationships.
3. Apply deterministic framework/language binding rules.
4. Collect evidence for each candidate hop.
5. Construct candidate paths.
6. Eliminate candidates contradicted by stronger evidence.
7. Classify remaining paths.
8. Produce the trace and alternatives.
9. Record unresolved/unknown boundaries.
10. Serialize a deterministic result.

Deterministic rules must have stable precedence and must be versioned.

## 8. Candidate and Ambiguity Model

A trace engine must preserve materially different candidate paths rather than silently selecting one.

For an ambiguous hop, the result shall contain:

- candidate paths;
- evidence for each candidate;
- confidence per candidate when inferred;
- reason deterministic resolution failed;
- unresolved boundary.

A deterministic selection is permitted only when the rule set establishes a reproducible winner.

## 9. Contradiction Handling

Contradictions must be explicit.

Examples include:

- graph relationship conflicts with source configuration;
- two incompatible mappings are both directly established;
- an expected target is absent while a conflicting target is explicitly configured.

Contradicted evidence must not be silently discarded.

The trace result shall identify:

- conflicting claims;
- supporting evidence for each;
- affected step;
- resolution state.

## 10. Trace Boundaries

The engine must explicitly record boundaries such as:

- missing source file;
- unresolved dynamic dispatch;
- reflection;
- generated code not available;
- external service with no local contract;
- database mapping not discovered;
- inaccessible/unreadable evidence.

A boundary becomes UNKNOWN unless sufficient evidence supports an INFERRED or AMBIGUOUS classification.

## 11. Canonical Trace Identity

Trace IDs must be deterministic for equivalent:

- repository;
- revision;
- origin;
- target;
- methodology version;
- analyzer version.

Step IDs must be deterministic from the trace identity and canonical step position/content.

Absolute checkout paths must not affect trace identity.

## 12. Determinism

For identical repository revision, CodeGraph, evidence set, analyzer versions and methodology configuration, the trace result must be byte-equivalent apart from explicitly volatile metadata.

Candidate ordering, evidence ordering and step ordering must be stable.

## 13. Required Query Capabilities

The trace API must eventually support:

- JSP to controller;
- controller to service;
- service to DAO/repository;
- DAO/repository to SQL;
- SQL to table/database;
- application to external system;
- reverse tracing from database/API to callers;
- bounded traces;
- alternative paths;
- unresolved boundaries;
- evidence lookup for any trace step.

## 14. Integration With CodeGraph

The trace engine consumes CodeGraph rather than creating an independent structural universe.

Trace steps should reference canonical node and edge IDs.

Where the CodeGraph contains a deterministic edge, the trace engine may use that edge directly as evidence.

Where no graph edge exists, a trace analyzer may produce a candidate only if its rule explicitly defines how the evidence is established.

## 15. Machine-Readable Contract

The canonical serialized form shall contain:

- schema_version
- trace_id
- repository_id
- revision
- analysis_run_id
- origin
- target
- status
- confidence
- methodology_version
- analyzer_version
- steps
- alternatives
- evidence
- boundaries

Each step shall contain:

- step_id
- sequence
- source_node
- relation
- target_node
- status
- provenance
- confidence
- evidence_refs
- rationale

## 16. Validation

Validation shall detect:

- duplicate trace/step IDs;
- invalid status;
- invalid provenance;
- missing source nodes;
- unresolved required evidence;
- non-contiguous step sequence;
- confidence outside the allowed range;
- inferred steps without confidence;
- deterministic steps carrying unsupported confidence;
- contradictory status without contradiction evidence;
- ambiguous status without alternatives/evidence;
- trace identity instability.

Validation errors must be machine-readable.

## 17. Safety

Trace construction must be read-only.

It must not:

- execute repository code;
- build the application;
- call production services;
- access production databases;
- modify source files or repository metadata.

## 18. Acceptance Criteria

### AC-01 — Trace model
A trace and trace step can represent the complete required metadata.

### AC-02 — Status semantics
CONFIRMED, INFERRED, AMBIGUOUS, CONTRADICTED and UNKNOWN are explicitly supported and semantically distinguishable.

### AC-03 — Evidence
Every material trace step has resolvable supporting evidence or is classified UNKNOWN.

### AC-04 — Deterministic methodology
Equivalent inputs produce the same candidate ordering, classifications and trace result.

### AC-05 — Ambiguity
Multiple unresolved candidates are preserved rather than silently collapsed.

### AC-06 — Contradiction
Conflicting evidence is retained and exposed in the trace result.

### AC-07 — CodeGraph integration
Trace steps reference canonical CodeGraph nodes/edges where available.

### AC-08 — Stable identity
Equivalent traces produce stable IDs independent of absolute checkout location.

### AC-09 — Boundaries
Unresolved reflection, dynamic dispatch, missing generated code and external boundaries are explicitly represented.

### AC-10 — Validation
Invalid traces and steps are rejected or reported deterministically.

### AC-11 — Serialization
Canonical JSON round-trips without loss of trace identity, evidence, status or provenance.

### AC-12 — Read-only behavior
Tracing does not execute or modify the analyzed repository.

### AC-13 — Automated verification
Tests cover confirmed, inferred, ambiguous, contradicted and unknown traces; evidence linkage; determinism; validation; serialization; and safety.

## 19. Test Strategy

Required fixtures shall include:

1. Simple JSP → Controller → Service chain.
2. Service → DAO → SQL relationship.
3. SQL → table mapping.
4. Multiple candidate service implementations.
5. Contradictory configuration.
6. Reflection/dynamic dispatch boundary.
7. Missing evidence.
8. External-system boundary.
9. Repeated runs and different checkout roots.
10. Malformed trace inputs.

Tests must assert evidence and status, not merely path existence.

## 20. Implementation Guidance

Use explicit components:

- TraceRequest
- Trace
- TraceStep
- CandidatePath
- TraceAnalyzer
- TraceRule
- EvidenceResolver
- TraceClassifier
- TraceValidator
- TraceSerializer

Keep framework-specific rules behind a versioned rule interface.

Do not hard-code Spring/JSP assumptions into the canonical trace model.

The first implementation should consume the existing in-memory CodeGraph and introduce a small deterministic rule engine. Parser/framework technology should remain independently replaceable.

## 21. Downstream Dependencies

SPEC-004 uses trace results and their evidence relationships.

SPEC-005 uses traces for Mainet ↔ UPYOG reconciliation.

SPEC-006 uses traces for specification generation and traceability.

ACA-CQAI uses traces for architecture and engineering-risk analysis.

Impact analysis uses trace traversal for change blast-radius computation.

## 22. Human Review Gate

No human gate is required for the initial deterministic trace model and read-only implementation.

A human gate is required before:

- production runtime tracing;
- production database/service access;
- a major framework-analysis dependency;
- execution of repository/application code;
- breaking changes to persistent trace contracts.

## 23. Definition of Done

SPEC-003 is complete only when:

1. The implementation-ready specification is versioned.
2. Trace model and status semantics are implemented.
3. CodeGraph integration works.
4. Evidence linkage is verified.
5. Ambiguity and contradiction are preserved.
6. Deterministic identity and serialization are verified.
7. Validation is automated.
8. CI passes.
9. Verification evidence is recorded.
10. The trace capability is integrated into the M1 vertical slice.
