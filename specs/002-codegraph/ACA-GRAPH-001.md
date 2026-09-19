# ACA-GRAPH-001 — Canonical Engineering Graph Model

**ACA ID:** ACA-002  
**Version:** 0.2  
**Status:** Implementation Ready  
**Capability:** Engineering Knowledge Graph  
**Milestone:** M1  
**Depends on:** ACA-001 / SPEC-001 Repository Ingestion

## 1. Objective

Define and implement a canonical, deterministic engineering graph that converts the factual output of repository ingestion and later deterministic analyzers into queryable nodes and relationships.

The CodeGraph is an engineering knowledge model. It must preserve provenance and distinguish deterministic observations from inferred relationships.

The graph is not the source of truth for raw source files. It references source/evidence identities established by ingestion and later analyzers.

## 2. Scope

The initial implementation shall support:

1. Repository, revision, module, package, file, class, interface, method, field and annotation nodes.
2. Deterministic containment and declaration relationships derived from repository structure and supported source analysis.
3. Stable node identity derived from repository/revision and canonical semantic identity.
4. Evidence-backed relationships.
5. Deterministic graph serialization.
6. Validation of node and edge references.
7. Basic graph traversal required by downstream trace and CQAI capabilities.
8. Explicit representation of relationship provenance and confidence.
9. Preservation of analysis-run identity.
10. A versioned graph schema that can evolve without silently changing historical meaning.

Initial implementation does not require a graph database. An in-memory canonical model plus deterministic JSON serialization is sufficient for the first vertical slice.

## 3. Non-Goals

The initial implementation shall not attempt to:

- perform complete Java semantic parsing;
- infer runtime behavior without evidence;
- resolve every dynamic dispatch relationship;
- construct a production graph database;
- perform vector/semantic retrieval;
- infer business workflows;
- modify the analyzed repository;
- execute repository code;
- connect to production systems;
- automatically remediate findings.

Those capabilities belong to later specifications.

## 4. Canonical Node Model

Every node shall contain at least:

- `id`
- `type`
- `repository_id`
- `revision` when available
- `canonical_key`
- `properties`
- `evidence_refs`
- `provenance`
- `analysis_run_id`

### Initial node types

- Repository
- Revision
- Module
- Package
- File
- Class
- Interface
- Method
- Field
- Annotation

Reserved node types for later capabilities:

- API/Endpoint
- Service
- Entity/DTO
- Database
- Table
- Column
- SQL Statement
- External System
- Configuration
- Test
- Architecture Component
- CQAI Finding
- Specification Element

Reserved types may exist in the schema but do not need producers in the initial implementation.

## 5. Canonical Edge Model

Every edge shall contain:

- `id`
- `source`
- `relation`
- `target`
- `repository_id`
- `revision` when available
- `provenance`
- `confidence` when inferred
- `evidence_refs`
- `analysis_run_id`

### Initial relationship types

- CONTAINS
- DECLARES
- IMPLEMENTS
- EXTENDS
- CALLS
- REFERENCES
- DEPENDS_ON
- INJECTS

Reserved relationship types for later analyzers:

- EXPOSES
- CONSUMES
- MAPS_TO
- READS
- WRITES
- EXECUTES_SQL
- CONNECTS_TO
- CONFIGURED_BY
- TESTS
- VIOLATES
- IMPACTS
- DERIVED_FROM

## 6. Provenance Contract

Provenance is mandatory.

Allowed values:

- `deterministic`
- `inferred`

Deterministic relationships are directly established by supported source/build/repository evidence.

Inferred relationships must:

- identify the evidence used;
- carry a confidence value;
- remain distinguishable from deterministic facts;
- never be serialized as deterministic facts.

The graph must be compatible with ACA's evidence states:

- Observed
- Inferred
- Assumed
- Unknown

Unknown relationships must not be fabricated as edges.

## 7. Stable Identity

Node and edge identifiers must be deterministic for the same repository revision, tool/schema version, and canonical identity.

Canonical keys should avoid absolute workspace paths where possible.

Examples:

`file:<relative-path>`

`class:<module>:<fully-qualified-name>`

`method:<class>:<signature>`

`module:<relative-root>`

An edge identity shall be derived from canonical source identity, relation type, canonical target identity, and relevant revision/schema context.

Changing the absolute checkout location must not change semantic node identity.

## 8. Relationship Constraints

The implementation shall validate:

1. Every edge source exists.
2. Every edge target exists.
3. Node IDs are unique.
4. Edge IDs are unique.
5. Repository/revision ownership is consistent.
6. Evidence references resolve to known evidence records when evidence is required.
7. Deterministic relationships do not carry fabricated confidence.
8. Inferred relationships carry provenance and confidence.
9. Duplicate canonical edges are rejected or deterministically deduplicated.
10. Serialization preserves graph semantics.

## 9. Integration With SPEC-001

SPEC-001 is the factual input boundary.

The first CodeGraph builder consumes:

- repository metadata;
- revision;
- module inventory;
- file inventory;
- evidence records.

At minimum it shall produce:

Repository → Module → Package/File structure

and corresponding evidence-backed containment relationships.

Java semantic nodes and relationships should be introduced behind explicit analyzer interfaces so that parser technology can be selected independently.

## 10. Required Queries

The graph API/model must eventually support:

- callers/callees;
- dependency paths;
- module dependency cycles;
- API-to-code-to-data tracing;
- entity-to-table mapping;
- change blast radius;
- architecture-rule violations;
- intended-vs-actual architecture comparison;
- CQAI finding context.

The initial implementation must provide the minimum traversal primitives needed for:

- node lookup;
- outgoing edges;
- incoming edges;
- direct neighbors;
- bounded path traversal.

## 11. Determinism

Given identical:

- repository revision;
- ingestion output;
- analyzer version;
- graph schema version;

the graph must produce identical canonical nodes, edges, ordering and serialized content.

Volatile timestamps must not participate in semantic identity.

## 12. Serialization Contract

The initial canonical serialization shall be JSON.

Required top-level fields:

- schema_version
- repository
- revision
- analysis_run_id
- nodes
- edges
- evidence

Nodes and edges must be emitted in stable canonical order.

Serialization/deserialization must preserve all required identity, provenance and evidence information.

## 13. Validation

The implementation must provide deterministic validation that reports:

- orphan edges;
- duplicate node IDs;
- duplicate edge IDs;
- unresolved evidence;
- invalid provenance;
- missing required identity fields;
- inconsistent repository/revision ownership.

Validation failures must be machine-readable.

## 14. Safety

CodeGraph construction must be read-only with respect to the analyzed repository.

It must not:

- execute source code;
- execute build lifecycle hooks;
- modify source files;
- modify repository metadata;
- require network access for the initial implementation.

## 15. Acceptance Criteria

### AC-01 — Canonical node model
The implementation represents the defined initial node families with stable identifiers and required metadata.

### AC-02 — Canonical edge model
The implementation represents defined relationships with source/target identity, provenance, evidence and analysis-run identity.

### AC-03 — Stable identity
Equivalent repository content and revision produce identical semantic node and edge IDs regardless of checkout location.

### AC-04 — Evidence linkage
Material graph facts retain resolvable evidence references to upstream ingestion/analyzer observations.

### AC-05 — Deterministic serialization
Equivalent inputs produce byte-equivalent canonical JSON apart from explicitly excluded volatile metadata.

### AC-06 — Graph validation
Invalid references, duplicate identities, missing required metadata and invalid provenance are detected deterministically.

### AC-07 — Ingestion integration
SPEC-001 repository/module/file output can be consumed to produce a valid initial graph without human interpretation.

### AC-08 — Traversal
The graph supports node lookup, incoming/outgoing adjacency, direct neighbors and bounded traversal.

### AC-09 — Read-only behavior
Graph construction does not execute or modify the analyzed repository.

### AC-10 — Automated verification
Tests cover identity stability, graph construction, evidence linkage, validation, deterministic serialization, traversal and read-only behavior.

## 16. Test Strategy

Required test categories:

- unit tests for node/edge models;
- golden fixtures for canonical serialization;
- determinism tests across repeated scans and different checkout roots;
- validation tests for malformed graphs;
- evidence-linkage tests;
- integration tests using SPEC-001 output;
- safety/read-only tests.

A graph fixture must be small enough to make expected nodes and relationships human-auditable.

## 17. Implementation Guidance

Use explicit interfaces for:

- GraphBuilder
- NodeFactory
- EdgeFactory
- IdentityProvider
- EvidenceResolver
- GraphValidator
- GraphSerializer
- GraphTraversal

Keep parser-specific logic outside the canonical graph model.

The first implementation should favor a small, dependency-light Python model consistent with the existing ACA-001 ingestion implementation. A graph database should not be introduced until query requirements and evaluation evidence justify it.

## 18. Downstream Dependencies

SPEC-003 uses CodeGraph for end-to-end trace construction.

SPEC-004 uses graph relationships and evidence for evidence management.

SPEC-005 uses CodeGraph for Mainet ↔ UPYOG structural and behavioral reconciliation.

SPEC-006 uses CodeGraph plus evidence for specification generation.

ACA-CQAI uses CodeGraph for architecture, quality and dependency analysis.

## 19. Human Review Gate

No human gate is required for the initial in-memory/deterministic implementation.

A human gate is required before:

- introducing a production graph database;
- introducing a major parser/framework dependency;
- changing persistent graph/schema contracts in a breaking way;
- adding production integrations;
- making security-sensitive execution changes.

## 20. Traceability

| Requirement | Acceptance | Downstream use |
|---|---|---|
| Canonical nodes | AC-01 | All graph consumers |
| Canonical edges | AC-02 | Trace/CQAI |
| Stable identity | AC-03 | Incremental analysis/history |
| Evidence | AC-04 | Evidence/CQAI |
| Serialization | AC-05 | Persistence/agents |
| Validation | AC-06 | Verification |
| Ingestion integration | AC-07 | M1 vertical slice |
| Traversal | AC-08 | Trace/impact analysis |
| Safety | AC-09 | Governance |
| Tests | AC-10 | CI/Critic |

## 21. Definition of Done

SPEC-002 is complete only when:

1. The implementation-ready specification is versioned.
2. The canonical graph model is implemented.
3. SPEC-001 output can populate the graph.
4. Deterministic identity and serialization are verified.
5. Validation and traversal are tested.
6. Evidence references are preserved.
7. CI passes.
8. Verification evidence is recorded.
9. The resulting capability is integrated into the ACA M1 vertical slice.
10. Human acceptance is obtained where a defined human-review gate applies.
