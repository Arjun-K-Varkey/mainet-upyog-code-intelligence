# ACA-RECON-001 — Mainet ↔ UPYOG Reconciliation

**ACA ID:** ACA-005  
**Version:** 0.1  
**Status:** Implementation Ready  
**Capability:** Repository Reconciliation Intelligence  
**Milestone:** M1  
**Depends on:** ACA-001 Repository Ingestion, ACA-002 CodeGraph, ACA-003 Trace Intelligence, ACA-004 Evidence Intelligence

## 1. Objective

Define a deterministic, evidence-backed reconciliation capability for comparing two independently analyzed implementations of related enterprise software, with the initial target being Mainet and UPYOG.

Reconciliation is not a textual diff and is not a claim that two implementations are equivalent merely because names or structures appear similar. It produces explicit, reviewable engineering claims about correspondence, divergence, absence, addition, and unresolved mapping between two repository analyses.

The primary result is:

`Mainet analysis + UPYOG analysis → candidate mappings → reconciled findings → evidence-backed report`

The capability must preserve the distinction between:

- directly observed correspondence;
- deterministically established equivalence or difference;
- inferred correspondence;
- ambiguous correspondence;
- contradicted correspondence;
- unknown/unresolved correspondence.

## 2. Scope

The initial implementation shall support:

1. Comparing two repository analyses at a common canonical abstraction level.
2. Matching repository, revision, module, package, file, class, interface, method, field, and supported API/endpoint representations when available.
3. Comparing CodeGraph structure and relationships.
4. Comparing trace structures where compatible traces exist.
5. Linking every material reconciliation finding to canonical Evidence.
6. Preserving one-to-one, one-to-many, many-to-one, and unresolved candidate mappings.
7. Detecting additions, removals, structural changes, relationship changes, and trace-level behavioral differences.
8. Producing deterministic machine-readable reconciliation results.
9. Preserving provenance for both source repositories.
10. Supporting bounded comparison so large repositories can be analyzed incrementally.
11. Producing summaries suitable for downstream specification generation, impact analysis, CQAI, and human review.
12. Remaining read-only with respect to both analyzed repositories.

The first implementation shall operate on already-produced in-memory CodeGraph, Trace, and Evidence objects. It shall not require a persistent graph database, vector database, LLM, runtime tracing system, or production integration.

## 3. Non-Goals

The initial implementation shall not:

- claim business-level functional equivalence without evidence;
- infer that similarly named components implement the same business requirement;
- execute either repository/application;
- access production databases or services;
- modify either repository;
- silently choose between materially ambiguous mappings;
- replace CodeGraph, Trace, or Evidence;
- introduce semantic/vector retrieval as a mandatory dependency;
- require a graph database;
- automatically migrate Mainet code to UPYOG or vice versa;
- automatically generate or apply remediation;
- determine organizational ownership or business intent;
- treat textual similarity alone as behavioral equivalence.

## 4. Terminology

### 4.1 Source side and target side

A reconciliation compares two independently analyzed repository contexts:

- **source** — the repository/context being compared from;
- **target** — the repository/context being compared against.

The implementation must not assume that Mainet is always the source. The request must explicitly identify both repository contexts and their roles.

### 4.2 Candidate mapping

A CandidateMapping represents a possible correspondence between a source artifact and a target artifact.

Possible mapping states:

- CONFIRMED
- INFERRED
- AMBIGUOUS
- CONTRADICTED
- UNKNOWN

A candidate is not equivalent to a final reconciliation finding. Multiple candidates may remain for one source or target artifact.

### 4.3 Reconciliation finding

A ReconciliationFinding is the canonical result of comparing two artifacts, relationships, or traces.

Finding categories initially include:

- MATCH
- ADDITION
- REMOVAL
- STRUCTURAL_CHANGE
- RELATIONSHIP_CHANGE
- BEHAVIORAL_DIVERGENCE
- BEHAVIORAL_MATCH
- AMBIGUOUS_MAPPING
- CONTRADICTION
- UNRESOLVED

These categories describe observed comparison results; they are not severity rankings.

### 4.4 Comparison scope

A reconciliation request may constrain comparison by:

- repository/module;
- package;
- file;
- node type;
- relation type;
- trace origin/target;
- bounded traversal depth;
- explicit node IDs;
- explicit evidence/run contexts.

## 5. Repository Context Model

A reconciliation requires two complete provenance contexts.

Each context shall contain at least:

- project_id;
- repository_id;
- revision;
- analysis_run_id;
- graph schema version;
- trace methodology/analyzer versions when traces are supplied;
- evidence schema version when evidence is supplied.

The two contexts may use different revisions, analyzer versions, or methodologies.

The result must retain both contexts and must never merge their provenance into a single repository identity.

A reconciliation result shall be invalid if:

- either repository identity is missing;
- either revision is missing where the underlying analysis requires it;
- source and target contexts are accidentally identical when the request requires two distinct repositories;
- supplied graph/trace/evidence provenance does not match its declared context.

## 6. Canonical Comparison Model

The canonical reconciliation model shall contain:

### ReconciliationRequest

- reconciliation_id
- source_context
- target_context
- scope
- comparison_mode
- mapping_policy
- analyzer_version
- methodology_version

### CandidateMapping

- mapping_id
- source_node
- target_node
- state
- provenance
- confidence when inferred
- evidence_refs
- rationale
- mapping_signals
- alternatives when ambiguous

### ReconciliationFinding

- finding_id
- category
- state
- source_subject
- target_subject when resolved
- source_context
- target_context
- evidence_refs
- source_evidence_refs
- target_evidence_refs
- rationale
- related_mapping_ids
- related_trace_ids
- related_edge_ids
- boundaries
- confidence when inferred

### ReconciliationResult

- schema_version
- reconciliation_id
- source_context
- target_context
- request
- mappings
- findings
- summaries
- boundaries
- contradictions
- analyzer_version
- methodology_version

All canonical collections must have deterministic ordering.

## 7. Mapping Identity

Mapping identity must be deterministic.

A mapping ID shall be derived from:

- reconciliation schema version;
- source repository/revision;
- target repository/revision;
- source canonical identity;
- target canonical identity;
- mapping methodology version.

Absolute checkout paths, timestamps, object identity, and insertion order must not participate in mapping identity.

A source artifact mapped to multiple targets must produce distinct mapping IDs.

## 8. Matching Strategy

Matching shall be staged and deterministic.

### Stage 1 — Exact canonical identity

Use stable canonical identities where both repositories expose a compatible identity.

Examples:

- exact normalized API path + HTTP method;
- exact fully qualified class identity where repository/module context establishes compatibility;
- exact method signature under a confirmed class mapping.

### Stage 2 — Structural signals

Compare deterministic structural properties such as:

- node type;
- normalized package/module position;
- class/interface relationships;
- method signatures;
- field signatures;
- annotations;
- declared dependencies;
- incoming/outgoing relationship sets.

### Stage 3 — Trace signals

When traces are available, compare:

- origin/target roles;
- ordered node-type sequences;
- relation sequences;
- endpoint/data targets;
- boundary types;
- evidence-backed path structure.

Trace similarity may establish an inferred mapping but must not by itself be represented as a confirmed business-equivalence claim.

### Stage 4 — Evidence-backed semantic signals

Evidence records may be used to compare:

- API declarations;
- configuration bindings;
- SQL/data access relationships;
- external integration declarations;
- explicit migration or compatibility metadata.

### Stage 5 — Ambiguity preservation

If multiple materially plausible candidates remain and deterministic rules cannot select a winner:

- preserve all candidates;
- mark the mapping AMBIGUOUS;
- record supporting evidence for each candidate;
- record why deterministic resolution failed.

The implementation must never silently select the first candidate.

## 9. Normalization

Normalization must be deterministic and separately versioned.

Allowed normalization may include:

- path separator normalization;
- package/file path normalization;
- identifier normalization where explicitly configured;
- whitespace-insensitive signature comparison where semantics are unchanged;
- HTTP method/path normalization;
- generic type formatting normalization where safely deterministic.

Normalization must not:

- erase meaningful method parameters;
- collapse distinct overloaded methods;
- remove namespace/module distinctions without an explicit rule;
- transform business names into assumed equivalence;
- modify source artifacts.

Every normalized comparison must retain the original canonical identities.

## 10. Structural Reconciliation

Structural reconciliation compares CodeGraph content.

Initial comparisons shall include:

### Node presence

For each supported node:

- present in both;
- source-only;
- target-only;
- unresolved mapping.

### Node attributes

Compare material canonical properties while excluding volatile metadata.

### Relationships

Compare supported graph relations:

- CONTAINS
- DECLARES
- IMPLEMENTS
- EXTENDS
- CALLS
- REFERENCES
- DEPENDS_ON
- INJECTS

Where later graph producers provide additional relations, the reconciliation engine may consume them through the same generic relation contract.

Relationship comparison must distinguish:

- relationship present in both;
- source-only relationship;
- target-only relationship;
- conflicting target relationship;
- unresolved endpoint mapping.

## 11. Behavioral Reconciliation

Behavioral reconciliation is evidence-backed structural trace comparison, not runtime equivalence.

When compatible traces exist, the engine shall compare:

1. origin mapping;
2. ordered trace steps;
3. relation types;
4. mapped source/target nodes;
5. evidence supporting each hop;
6. boundaries;
7. alternative paths;
8. contradiction records.

Initial behavioral outcomes:

- BEHAVIORALLY_ALIGNED
- BEHAVIORALLY_DIVERGENT
- BEHAVIORALLY_AMBIGUOUS
- BEHAVIORALLY_UNRESOLVED

A behavioral divergence finding must identify the first deterministically established divergence where possible and retain the supporting evidence.

If a trace cannot be compared because required mappings/evidence are absent, the result must be UNRESOLVED rather than divergent.

## 12. Evidence Contract

Every material reconciliation finding must reference evidence.

Evidence may include:

- source CodeGraph nodes/edges;
- target CodeGraph nodes/edges;
- source Trace steps;
- target Trace steps;
- canonical Evidence records;
- source locations;
- API/configuration/SQL evidence;
- deterministic mapping signals.

The reconciliation engine must preserve source and target evidence separately.

No evidence-backed finding may be serialized as a deterministic fact if its supporting inputs are only inferred.

## 13. Status and Provenance

Allowed state values:

- CONFIRMED
- INFERRED
- AMBIGUOUS
- CONTRADICTED
- UNKNOWN

Allowed provenance values:

- deterministic
- inferred

Rules:

- CONFIRMED requires deterministic supporting evidence.
- INFERRED requires evidence and confidence.
- AMBIGUOUS requires alternatives and supporting evidence.
- CONTRADICTED requires explicit conflicting evidence.
- UNKNOWN requires an unresolved boundary or insufficient evidence.
- Confidence must never convert an inferred result into CONFIRMED.

## 14. Contradictions

Contradictions must be preserved rather than discarded.

Examples:

- source mapping points to one target while explicit target configuration establishes another;
- two target components independently satisfy the same deterministic mapping criteria;
- trace evidence indicates incompatible paths;
- graph structure conflicts with explicit configuration evidence.

A contradiction record shall include:

- contradiction_id;
- affected mapping/finding;
- competing claims;
- evidence_refs for each claim;
- resolution state.

## 15. Boundaries

The engine shall explicitly represent unresolved comparison boundaries, including:

- source artifact unavailable;
- target artifact unavailable;
- unsupported node type;
- unsupported relation;
- dynamic dispatch;
- reflection;
- generated code unavailable;
- missing trace;
- missing evidence;
- incompatible analyzer versions;
- incompatible methodology versions;
- external system boundary;
- unresolved database mapping;
- inaccessible source evidence.

Boundaries must not be converted into divergence merely because a comparison cannot be completed.

## 16. Deterministic Methodology

The canonical reconciliation process shall be:

1. Validate source and target contexts.
2. Validate supplied CodeGraph, Trace, and Evidence provenance.
3. Establish comparison scope.
4. Normalize comparison identities using the active methodology version.
5. Generate deterministic candidate mappings.
6. Score/classify candidates only through versioned deterministic rules.
7. Preserve material alternatives.
8. Reconcile node presence and attributes.
9. Reconcile graph relationships.
10. Reconcile compatible traces.
11. Detect contradictions.
12. classify findings.
13. Record unresolved boundaries.
14. Resolve evidence references.
15. Sort mappings/findings/boundaries deterministically.
16. Serialize canonical result.
17. Validate the complete result.

The engine must expose methodology and analyzer versions in every result.

## 17. Confidence

Confidence is permitted only for INFERRED mappings/findings and candidate alternatives where the methodology supports it.

Confidence shall:

- be within the canonical range 0.0–1.0;
- be deterministic for identical inputs;
- never be presented as a probability of business equivalence;
- never override AMBIGUOUS, CONTRADICTED, or UNKNOWN state semantics.

The initial implementation should favor explicit deterministic signals over opaque scoring.

## 18. Validation

Validation shall detect at minimum:

- duplicate reconciliation IDs;
- duplicate mapping/finding IDs;
- invalid repository contexts;
- source/target provenance mismatch;
- invalid state/provenance;
- inferred records without confidence;
- confidence outside range;
- ambiguous mappings without alternatives;
- contradicted findings without contradiction evidence;
- unknown findings without boundaries;
- unresolved evidence references;
- references to missing graph nodes/edges;
- references to incompatible trace contexts;
- non-deterministic collection ordering;
- identity mismatch;
- unsupported schema versions.

Validation failures must be machine-readable and deterministic.

## 19. Serialization

Canonical JSON shall contain:

- schema_version;
- reconciliation_id;
- source_context;
- target_context;
- request;
- mappings;
- findings;
- summaries;
- boundaries;
- contradictions;
- analyzer_version;
- methodology_version.

Equivalent reconciliation inputs must produce byte-equivalent canonical output apart from explicitly excluded volatile metadata.

Absolute checkout paths must not affect semantic identity.

## 20. Required Query Capabilities

The initial API/model should support:

- compare repositories;
- compare selected modules;
- compare selected node types;
- resolve a source node to target candidates;
- list source-only artifacts;
- list target-only artifacts;
- list structural changes;
- list relationship changes;
- compare traces;
- retrieve evidence for a finding;
- inspect ambiguous mappings;
- inspect contradictions;
- inspect unresolved boundaries.

A later persistence layer may add indexed queries without changing the canonical model.

## 21. Safety

Reconciliation must be read-only.

It must not:

- execute source code;
- execute builds;
- call production services;
- access production databases;
- modify either repository;
- modify graph/trace/evidence source records;
- write raw secrets;
- require network access for canonical comparison.

## 22. Acceptance Criteria

### AC-01 — Dual-context model
Source and target repository/revision/run provenance are explicit and independently preserved.

### AC-02 — Canonical mapping
Candidate mappings have stable IDs, explicit state, provenance, evidence and deterministic ordering.

### AC-03 — Structural reconciliation
Supported CodeGraph nodes and relationships can be compared deterministically.

### AC-04 — Behavioral reconciliation
Compatible traces can be compared without claiming runtime equivalence.

### AC-05 — Evidence linkage
Every material finding retains resolvable source/target evidence.

### AC-06 — Ambiguity preservation
Materially different candidate mappings are preserved rather than silently collapsed.

### AC-07 — Contradiction preservation
Conflicting claims and their evidence remain visible.

### AC-08 — Unknown boundaries
Missing or unsupported evidence produces explicit unresolved boundaries.

### AC-09 — Stable identity
Equivalent reconciliation inputs produce stable IDs independent of checkout paths and object ordering.

### AC-10 — Deterministic serialization
Equivalent inputs produce byte-equivalent canonical JSON.

### AC-11 — Validation
Malformed and provenance-inconsistent results are rejected deterministically.

### AC-12 — Read-only safety
The engine does not execute or modify analyzed repositories.

### AC-13 — Automated verification
Tests cover exact matches, additions, removals, structural changes, relationship changes, ambiguous mappings, contradictions, behavioral alignment/divergence, unknown boundaries, evidence linkage, determinism, serialization and safety.

## 23. Test Strategy

Required fixtures:

1. Exact module/class correspondence.
2. Source-only class/module.
3. Target-only class/module.
4. One-to-many mapping.
5. Many-to-one mapping.
6. Ambiguous same-signature candidates.
7. Structural relationship addition/removal.
8. Relationship target change.
9. Matching trace with different implementation identities.
10. Trace divergence at a deterministic step.
11. Missing trace/evidence boundary.
12. Contradictory mapping evidence.
13. Different analyzer versions.
14. Different checkout roots.
15. Repeated reconciliation runs.
16. Malformed/tampered reconciliation records.

Tests must assert state, provenance, evidence, identity and deterministic ordering, not merely candidate counts.

## 24. Implementation Guidance

Use explicit components:

- ReconciliationRequest
- RepositoryContext
- CandidateMapping
- ReconciliationFinding
- ReconciliationResult
- MappingRule
- MappingRuleRegistry
- StructuralComparator
- RelationshipComparator
- TraceComparator
- EvidenceResolver
- ContradictionDetector
- BoundaryClassifier
- ReconciliationValidator
- ReconciliationSerializer

Keep mapping rules independent of the canonical result model.

The first implementation should be a small Python package consuming existing:

- `aca_graph.Graph`
- `aca_graph.Trace`
- `aca_evidence.EvidenceRegistry`

No new persistence technology is required.

The initial rule set should be deterministic and auditable. Avoid embedding an LLM into the canonical reconciliation path. AI-assisted semantic matching may be introduced later as an explicitly INFERRED candidate producer with evidence, confidence, versioning, and human-review controls.

## 25. Integration

### SPEC-001

Repository/revision/module/file identities provide the initial comparison boundary.

### SPEC-002

CodeGraph supplies canonical nodes, relationships, provenance and evidence references.

### SPEC-003

Trace supplies ordered execution/data-path claims and unresolved boundaries.

### SPEC-004

Canonical Evidence supplies independently verifiable provenance for reconciliation findings.

### Downstream

SPEC-006 will consume reconciliation findings when generating specifications and traceability artifacts.

ACA-CQAI may consume reconciliation findings for architecture drift, duplication, legacy divergence, and technical-debt analysis.

Impact analysis may use reconciliation mappings to identify cross-repository change relationships.

## 26. Human Review Gate

No human gate is required for the initial read-only, deterministic reconciliation model.

A human review gate is required before:

- declaring business-level functional equivalence;
- using reconciliation to automatically migrate or modify code;
- introducing production repository/service access;
- introducing external data-exfiltration or secret-management dependencies;
- making breaking changes to persistent reconciliation contracts.

## 27. Definition of Done

ACA-005 is complete only when:

1. This implementation-ready specification is versioned.
2. Canonical source/target repository contexts are implemented.
3. Deterministic mapping rules are implemented and versioned.
4. Structural reconciliation is implemented.
5. Trace reconciliation is implemented.
6. Evidence linkage is verified.
7. Ambiguity, contradiction and unknown boundaries are preserved.
8. Stable identity and deterministic serialization are verified.
9. Validation is automated.
10. Read-only safety is verified.
11. CI passes.
12. Verification evidence is recorded.
13. The capability is integrated into the M1 repository-to-evidence vertical slice.
14. Human acceptance is obtained where a defined human-review gate applies.
