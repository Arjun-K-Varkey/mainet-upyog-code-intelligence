# SPEC-000 — Platform Architecture

## Status

Proposed foundation specification.

## Purpose

Define the architecture and engineering boundaries for an evidence-backed AI Code Intelligence Platform focused initially on Mainet and UPYOG.

## Problem

Enterprise application behavior is distributed across UI artifacts, controllers, services, DAOs/repositories, SQL, database structures, configuration, workflows, and external integrations. Manual reconstruction is slow and error-prone.

The platform must combine deterministic extraction with explicit AI-assisted interpretation while preserving provenance and uncertainty.

## Goals

- Ingest repositories without modifying their source.
- Discover Java, JSP, SQL, configuration, modules, symbols, and dependencies.
- Build a normalized CodeGraph.
- Trace supported flows such as JSP → Controller → Service → DAO → SQL → DB → External System.
- Attach evidence and confidence to material claims.
- Reconcile Mainet and UPYOG capabilities.
- Generate evidence-backed technical specifications and human-readable CodeWiki artifacts.
- Support local AI engineering agents using the same specification/evidence discipline.

## Non-goals for MVP

- Autonomous modification of Mainet/UPYOG source.
- Perfect business-rule understanding.
- Perfect dynamic runtime tracing.
- Generalized multi-language support before Java/JSP/SQL are proven.

## Logical architecture

```text
Source Repository
      ↓
Repository Ingestion
      ↓
AST / Symbol / Dependency Extraction
      ├── JavaParser / Tree-sitter
      ├── SCIP / scip-java
      └── Joern / CPG
      ↓
Normalized Analysis Model
      ↓
CodeGraph + Data Lineage + Workflow Model
      ↓
Evidence / Provenance Layer
      ↓
Knowledge Layer
      ├── Neo4j
      └── Qdrant
      ↓
AI Reasoning Layer
      ├── Trace Engine
      ├── Reconciliation
      ├── Gap Analysis
      ├── Specification Generation
      └── CodeWiki
```

## Core entities

Repository, Commit, File, Module, Package, Class, Interface, Method, Field, JSP, Endpoint, SQL Query, Table, Column, External System, Workflow, Actor, Business Rule, Requirement, Evidence, Trace, Gap, Specification.

## Core relationships

CONTAINS, CALLS, IMPLEMENTS, EXTENDS, REFERENCES, READS, WRITES, MAPS_TO, INVOKES, QUERIES, UPDATES, INTEGRATES_WITH, EVIDENCED_BY, DERIVED_FROM, MATCHES, PARTIALLY_MATCHES, MISSING_IN.

## Confidence

- CONFIRMED — directly supported by deterministic evidence.
- INFERRED — reasonable interpretation not directly established.
- AMBIGUOUS — multiple plausible interpretations.
- CONTRADICTED — evidence conflicts.
- UNKNOWN — insufficient evidence.

## AI architecture

The `.ai/` directory defines the operating contract for Product, Specification, Architecture, Coding, Test, Evidence, and Review roles.

AI is responsible for interpretation, synthesis, planning, and orchestration. Deterministic tools are responsible for extracting source facts wherever possible.

## MVP vertical slice

Demonstrate one real Mainet capability traced end-to-end from JSP/UI entry through Controller, Service, DAO/repository, SQL, database target, and external system where applicable, with evidence for each supported edge and explicit unresolved edges.

## Definition of Done

- Repository ingestion is reproducible.
- Java/JSP/SQL discovery works.
- Core symbols and relationships are represented.
- One real capability is traced end-to-end.
- Evidence and confidence are attached.
- An evidence-backed technical specification is generated.
- Automated tests validate the core path.
