# ACA-GRAPH-001 — Canonical Engineering Graph Model

**Version:** 0.1  
**Status:** M1 baseline

## 1. Purpose
Define the canonical graph representation connecting source-code structure, runtime/framework relationships, data, interfaces, architecture, tests, findings, and engineering history.

## 2. Node Families
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

## 3. Relationship Families
Examples:
- CONTAINS
- DECLARES
- IMPLEMENTS
- EXTENDS
- CALLS
- REFERENCES
- DEPENDS_ON
- INJECTS
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

## 4. Relationship Contract
Every important relationship should carry evidence references, provenance, confidence when inferred, and analysis-run identity.

```yaml
Edge:
  id: EDGE-<id>
  source: <node-id>
  relation: CALLS
  target: <node-id>
  provenance: <deterministic|inferred>
  confidence: <optional>
  evidence: [EVID-...]
  run_id: <analysis-run>
```

## 5. Graph Principles
1. Deterministic relationships are preferred over inferred relationships.
2. Inferred relationships must be explicitly marked.
3. Historical revisions must remain queryable.
4. Graph traversal must support impact analysis and architecture-drift analysis.
5. The graph is complementary to semantic retrieval; it is not a replacement for search/vector retrieval.

## 6. Required Queries
The implementation must eventually support:
- callers/callees
- dependency paths
- module dependency cycles
- API-to-code-to-data tracing
- entity-to-table mapping
- change blast radius
- architecture-rule violations
- intended-vs-actual architecture comparison
- CQAI finding context
