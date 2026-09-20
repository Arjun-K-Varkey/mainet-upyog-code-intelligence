# ACA-EVIDENCE-001 — Canonical Evidence Model

**ACA ID:** ACA-004  
**Version:** 0.2  
**Status:** Implementation Ready  
**Capability:** Evidence Intelligence  
**Milestone:** M1  
**Depends on:** ACA-001 Repository Ingestion, ACA-002 CodeGraph, ACA-003 Trace Intelligence

## 1. Purpose

Define the canonical, deterministic representation of observable engineering evidence used by ACA.

Evidence is an input to reasoning, not a reasoning result. It records what a deterministic producer observed or established from a repository revision, analysis run, build/static-analysis result, test result, configuration source, history, or other permitted engineering source.

## 2. Core Principles

1. Evidence precedes AI interpretation.
2. Evidence and derived knowledge are distinct objects.
3. Every evidence record is attributable to a repository revision and analysis run.
4. Evidence identifiers are deterministic for equivalent semantic evidence.
5. Evidence is immutable once an analysis run is completed.
6. Re-analysis creates new records when provenance differs.
7. Evidence must never silently contain secrets or unnecessary sensitive values.
8. Evidence records must be independently serializable and verifiable.

## 3. Canonical Evidence Record

Required fields:

- `id`
- `project_id`
- `repository_id`
- `revision`
- `run_id`
- `type`
- `subject`
- `relation`, when applicable
- `object`, when applicable
- `source`
- `value`
- `status`

Optional field:

- `observed_at`

Canonical source fields:

- `tool`
- `version`
- `file`, when applicable
- `start_line`, when applicable
- `end_line`, when applicable

Evidence type is an extensible machine-readable value. Initial types include:

`source`, `symbol`, `call`, `dependency`, `sql`, `api`, `config`, `test`, `metric`, `history`, `runtime`, `error`, `revision`.

## 4. Identity and Determinism

The evidence ID must be derived from canonical semantic content and must not depend on:

- absolute checkout paths;
- workspace-local paths;
- volatile timestamps;
- object insertion order;
- Python/object memory identity.

The canonical identity input is:

`schema_version + project_id + repository_id + revision + run_id + type + subject + relation + object + source identity + canonical value`

Equivalent records must produce the same ID.

The serialized representation must use stable field ordering and stable ordering for nested maps/lists where order is not semantically meaningful.

## 5. Provenance

Evidence must retain enough provenance to answer:

- which project and repository produced it;
- which revision was analyzed;
- which analysis run produced it;
- which tool and tool version produced it;
- which source file/location supports it, where applicable.

Evidence references used by CodeGraph and Trace must resolve to canonical evidence IDs.

## 6. Status and Lifecycle

Initial evidence statuses:

- **VALID** — evidence is currently applicable to the represented revision/run.
- **STALE** — evidence remains historically valid but no longer represents the current revision/context.
- **INVALID** — evidence was determined to be unusable.
- **REDACTED** — sensitive value was removed or transformed while preserving the existence and provenance of the evidence.

Status transitions must be explicit. The canonical model must not silently mutate evidence content.

## 7. Evidence Value

`value` is structured JSON-compatible data.

The model must support strings, numbers, booleans, null, lists and objects.

Serialization must reject unsupported/non-JSON values rather than coercing them nondeterministically.

Secret-like material must not be persisted as raw values. Producers must provide redacted representations such as:

- `[REDACTED]`
- secret type/category
- presence/absence metadata
- non-sensitive hashes only when required for deterministic correlation.

The canonical model does not attempt to prove that an arbitrary value is or is not a secret; it provides a deterministic redaction boundary and rejects obvious raw secret patterns where required by the implementation contract.

## 8. Validation

Validation must detect at minimum:

- missing required identity/provenance fields;
- invalid evidence type;
- invalid status;
- malformed source metadata;
- invalid line ranges;
- unsupported value types;
- unstable/non-canonical values;
- identity mismatch;
- evidence IDs that do not match canonical identity;
- secret-like raw values in protected fields;
- inconsistent repository/revision/run provenance.

Validation errors must be machine-readable and deterministic.

## 9. Immutability

A completed evidence record is immutable.

The implementation must expose immutable value objects or equivalent behavior. Any lifecycle change must create a new record/version rather than mutating an existing canonical record.

## 10. Knowledge Linkage

The evidence model does not contain AI conclusions.

The intended relationship is:

`Evidence → Finding → Interpretation → Recommendation → Decision`

A Finding/Interpretation may reference one or more evidence IDs. An AI-derived claim without evidence references must not be represented as an observed fact.

## 11. Integration

### Repository Ingestion

Existing SPEC-001 scanner evidence must be mappable into the canonical model without loss of:

- repository ID;
- revision;
- run ID;
- tool version;
- source path;
- evidence type;
- value.

### CodeGraph

Graph node/edge `evidence_refs` resolve to canonical evidence IDs.

### Trace

Trace step `evidence_refs` resolve to canonical evidence IDs. Evidence status and provenance remain independently inspectable.

## 12. Safety

Evidence processing is read-only with respect to analyzed repositories.

It must not:

- execute repository/application code;
- connect to production services or databases;
- modify source files;
- write secrets to canonical evidence;
- rely on network access for canonical serialization.

## 13. Canonical Serialization

Canonical JSON must contain:

- `schema_version`
- `id`
- `project_id`
- `repository_id`
- `revision`
- `run_id`
- `type`
- `subject`
- `relation`
- `object`
- `source`
- `value`
- `observed_at`
- `status`

Null optional fields must be represented consistently.

Round-trip serialization must preserve identity, provenance, value and status.

## 14. Acceptance Criteria

### AC-01 — Complete model
A canonical evidence record represents all required provenance and source metadata.

### AC-02 — Stable identity
Equivalent evidence produces the same ID independent of checkout path and object ordering.

### AC-03 — Provenance
Repository, revision, run, producer and source location are preserved.

### AC-04 — Validation
Malformed evidence is rejected with deterministic machine-readable errors.

### AC-05 — Lifecycle
VALID, STALE, INVALID and REDACTED are explicitly represented.

### AC-06 — Security
Secret-like raw values are rejected or deterministically redacted at the canonical boundary.

### AC-07 — Serialization
Canonical JSON round-trips without loss.

### AC-08 — Integration
CodeGraph/Trace evidence references can resolve to canonical evidence IDs.

### AC-09 — Immutability
Canonical evidence values cannot be mutated in place.

### AC-10 — Determinism
Repeated serialization and equivalent reconstruction produce byte-equivalent canonical JSON.

### AC-11 — Read-only
Evidence creation and validation do not execute or modify the analyzed repository.

### AC-12 — Automated verification
Tests cover valid records, malformed records, identity tampering, provenance, lifecycle states, secret handling, serialization, determinism and immutability.

## 15. Test Strategy

Required tests:

1. Minimal valid evidence record.
2. Full source/provenance record.
3. Deterministic ID across equivalent object ordering.
4. ID independence from absolute source path.
5. ID tampering rejection.
6. Invalid status/type rejection.
7. Invalid source line range rejection.
8. Unsupported value rejection.
9. VALID/STALE/INVALID/REDACTED lifecycle coverage.
10. Secret-like raw value handling.
11. JSON round-trip.
12. Repeated serialization byte equality.
13. Immutable record behavior.
14. Repository/revision/run mismatch rejection.
15. Evidence references usable by graph/trace consumers.

## 16. Implementation Guidance

Use a small canonical evidence package with:

- `Evidence`
- `EvidenceSource`
- `EvidenceValidationError`
- deterministic identity/serialization helpers
- a pure validator

Keep storage backend concerns out of the canonical model. Database/object-store persistence can be introduced later behind an adapter.

## 17. Human Review Gate

No human gate is required for the read-only canonical evidence model.

A human gate is required before:

- production evidence collection;
- runtime/prod data access;
- persistent storage schema changes;
- introduction of external secret-management or data-exfiltration dependencies.

## 18. Definition of Done

1. Implementation-ready specification is versioned.
2. Canonical model is implemented.
3. Validation and deterministic identity are automated.
4. Security/redaction boundary is tested.
5. Serialization is deterministic and lossless.
6. CodeGraph/Trace evidence references remain compatible.
7. CI passes.
8. Verification evidence is recorded.
