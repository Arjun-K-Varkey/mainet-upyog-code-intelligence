# SPEC-001 — Repository Ingestion

**ACA ID:** ACA-001  
**Version:** 0.1  
**Status:** Proposed / Implementation Ready  
**Capability:** Repository Intelligence  
**Milestone:** M1

## 1. Objective

Define a deterministic repository-ingestion capability that converts a source repository into a machine-readable inventory and evidence set suitable for downstream CodeGraph, Trace, Evidence, CQAI, architecture reconstruction, and specification-generation capabilities.

The ingestion layer establishes facts. It must not infer business meaning or architectural intent.

## 2. Scope

The initial vertical slice shall:

1. Accept a repository workspace/path as input.
2. Identify repository metadata and scan boundaries.
3. Recursively enumerate source files within the configured scope.
4. Produce stable file metadata.
5. Detect relevant file/language types, initially including Java, JSP, XML, SQL, JavaScript, CSS, YAML, JSON, properties, Markdown, Maven and Gradle descriptors.
6. Identify probable application/module boundaries using deterministic repository structure and build metadata.
7. Record basic source metadata needed by downstream analyzers.
8. Emit machine-readable ingestion output.
9. Emit evidence references for every material observed fact.
10. Produce deterministic results for the same repository snapshot and configuration.

## 3. Non-Goals

The first implementation shall not attempt to:

- fully parse Java semantics;
- construct the complete code/dependency graph;
- trace JSP-to-database execution paths;
- infer business workflows;
- determine architectural intent;
- perform AI-based interpretation;
- modify the analyzed repository;
- execute application code;
- connect to a production database or external service.

These belong to later specifications and controlled execution stages.

## 4. Input Contract

Required inputs:

- repository workspace path;
- scan configuration.

Configuration shall support, at minimum:

- include/exclude paths;
- maximum file size;
- ignored directories;
- symbolic-link policy;
- generated/vendor directory policy;
- supported detector set;
- repository identifier/version metadata when available.

The ingestion implementation must treat the input repository as read-only.

## 5. Output Contract

The ingestion result shall contain at least:

### Repository

- repository identifier;
- source path/workspace identifier;
- detected VCS and revision when available;
- scan timestamp;
- ingestion tool/version;
- configuration fingerprint.

### File Inventory

For each included file:

- stable relative path;
- file type/language classification;
- size;
- content hash;
- line count when safely determinable;
- generated/vendor classification;
- detection evidence reference.

### Module Inventory

For each detected module:

- stable module identifier;
- relative root;
- module type;
- build descriptor(s), if any;
- source/resource roots detected;
- parent module, when deterministically established;
- evidence references.

## 6. Evidence Requirements

Every material ingestion fact must be traceable to an observation. Evidence records should identify:

- evidence identifier;
- source path or repository metadata location;
- observation type;
- observed value;
- extractor/detector version;
- scan/repository revision;
- confidence as applicable;
- timestamp.

The ingestion layer shall use **Observed** status for facts directly established from repository contents or repository metadata. It shall not label deterministic observations as AI inferences.

## 7. Determinism

For identical repository content, revision, configuration, and tool version, ingestion output shall be reproducible apart from explicitly designated volatile metadata such as execution timestamp.

Ordering must be stable. Identifiers derived from repository content/path shall be stable across repeated scans.

## 8. Error Handling

The scanner shall:

- continue where safe when an individual file cannot be read;
- record an evidence-backed ingestion warning/error;
- distinguish inaccessible files from absent files;
- never silently discard a configured path;
- return a scan-level status indicating success, partial success, or failure.

## 9. Safety

The initial scanner must be read-only with respect to the analyzed repository. It must not execute source files, build commands, scripts, lifecycle hooks, or arbitrary repository code.

No network access is required for the initial implementation.

## 10. Acceptance Criteria

### AC-01 — Repository discovery
Given a valid repository workspace, ACA produces a repository-level ingestion result.

### AC-02 — Deterministic file inventory
Repeated scans of the same repository snapshot and configuration produce the same file inventory, classifications, hashes, and stable identifiers.

### AC-03 — File classification
Java, JSP, SQL, XML, Maven/Gradle descriptors, configuration formats, and common web assets are classified deterministically.

### AC-04 — Module detection
Recognizable Maven/Gradle modules and structurally identifiable application modules are represented with stable identifiers and evidence.

### AC-05 — Evidence provenance
Material repository and file facts have evidence references sufficient to locate the underlying source observation.

### AC-06 — Safe failure
Unreadable or malformed files do not cause silent data loss; safe failures are represented in the scan result.

### AC-07 — Read-only operation
The ingestion process does not modify, execute, or build the analyzed repository.

### AC-08 — Machine-readable output
The result can be serialized and consumed by downstream ACA components without requiring human interpretation.

### AC-09 — Verification
Automated tests cover deterministic ordering/identifiers, representative file detection, module detection, hashing, exclusions, unreadable-file handling, and read-only behavior.

## 11. Downstream Dependencies

SPEC-001 provides the factual baseline for:

- SPEC-002 CodeGraph;
- SPEC-003 End-to-End Trace Engine;
- SPEC-004 Evidence Engine;
- SPEC-005 Mainet ↔ UPYOG Reconciliation;
- SPEC-006 Specification Generation;
- ACA-CQAI analysis.

## 12. Implementation Guidance

Prefer a small, deterministic core with explicit interfaces for:

- repository scanner;
- file classifier;
- module detector;
- metadata extractor;
- evidence emitter;
- result serializer.

Keep detector logic independently testable. Avoid premature framework coupling. Parser/static-analysis technology selection for later Java semantic analysis is outside this specification.

## 13. Traceability

| Requirement | Acceptance | Downstream use |
|---|---|---|
| Repository discovery | AC-01 | All capabilities |
| Stable inventory | AC-02, AC-03 | CodeGraph |
| Module model | AC-04 | Architecture/Trace |
| Evidence | AC-05 | Evidence/CQAI |
| Safe scanning | AC-06, AC-07 | Governance |
| Machine-readable model | AC-08 | All downstream agents |
| Verification | AC-09 | CI / Critic |

## 14. Human Review Gate

No human gate is required to implement the initial deterministic scanner provided implementation remains read-only, introduces no production integration, and does not make a major parser/framework dependency decision.

A human gate is required if implementation expands into execution of repository code, production access, schema/database changes, or a major architectural dependency choice.
