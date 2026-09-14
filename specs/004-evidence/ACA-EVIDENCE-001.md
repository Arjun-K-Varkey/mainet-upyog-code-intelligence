# ACA-EVIDENCE-001 — Canonical Evidence Model

**Version:** 0.1  
**Status:** M1 baseline

## 1. Purpose
Define the canonical representation of facts discovered from repositories, builds, static analysis, runtime/framework analysis, tests, history, and other engineering sources.

## 2. Evidence Principle
Evidence is an observable artifact or deterministic result. It is not an AI conclusion.

Every evidence record must be attributable to a project, repository revision, analysis run, source/tool, and location where applicable.

## 3. Evidence Record

```yaml
Evidence:
  id: EVID-<unique-id>
  project_id: <id>
  repository_id: <id>
  revision: <commit-or-snapshot>
  run_id: <analysis-run>
  type: <source|symbol|call|dependency|sql|api|config|test|metric|history|runtime>
  subject: <entity-id>
  relation: <optional-relation>
  object: <optional-entity-id>
  source:
    tool: <producer>
    version: <producer-version>
    file: <path>
    start_line: <line>
    end_line: <line>
  value: <structured-value>
  observed_at: <timestamp>
  status: valid
```

## 4. Knowledge Linkage
AI-derived findings must reference one or more evidence IDs. A conclusion must not be persisted as an observed fact.

```text
Evidence → Finding → Interpretation → Recommendation → Decision
```

## 5. Confidence
Confidence belongs to derived findings/knowledge, not to raw evidence. Raw evidence records provenance and validity.

## 6. Immutability
Evidence for a completed analysis run is immutable. Re-analysis creates new evidence linked to a new revision/run.

## 7. Invalidation
Evidence may become stale when source revisions change. Staleness must be explicit; historical evidence remains available for comparison and architecture-drift analysis.

## 8. Required Properties
- deterministic provenance
- repository revision
- analysis-run identity
- source location where applicable
- producer/tool identity
- machine-readable type
- validity/staleness state
- stable evidence identifier

## 9. Security
Evidence must not persist secrets, credentials, tokens, or unnecessary sensitive data. Secret-like values should be redacted while preserving the fact that a finding exists.
