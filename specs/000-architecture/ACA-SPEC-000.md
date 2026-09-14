# ACA-SPEC-000 — Master Specification

**Version:** 0.2  
**Status:** Baseline

## Mission
AI Code Architect (ACA) is a production-grade, specification-first engineering system for understanding, reconstructing, evaluating, designing, and safely evolving large software systems.

> Deterministic evidence first → structured engineering knowledge → AI reasoning → independent verification → controlled change.

## Initial Target
Large Java enterprise applications, including legacy Java web applications, JSP/Servlets, Spring/Spring Boot, Hibernate/JPA, JDBC/SQL, relational databases, REST/SOAP integrations, Maven/Gradle, and configuration-heavy systems.

## Capability Families
1. Repository Intelligence
2. Code Intelligence
3. Runtime/Framework Intelligence
4. Architecture Reconstruction
5. Engineering Knowledge Graph
6. Semantic Intelligence
7. **ACA-CQAI — Code Quality & Architecture Intelligence**
8. Agentic Engineering
9. Safe Engineering Evolution

## Evidence Principle
ACA distinguishes **Observed, Inferred, Assumed, and Unknown**. Important conclusions retain evidence references, provenance, confidence, and validation state.

## ACA-CQAI
ACA-CQAI is a first-class capability family covering:
- SOLID: SRP, OCP, LSP, ISP, DIP
- DRY, KISS, YAGNI, GRASP
- GoF pattern detection, misuse, and opportunities
- Clean, Hexagonal, Layered Architecture and DDD
- Dependency-direction rules and architecture drift
- Security, performance, concurrency, and transactions
- API design and database access
- Error handling and observability
- Test architecture
- Legacy hotspots and technical debt

CQAI findings must capture detection, evidence, interpretation, severity, confidence, impact, recommendation, remediation, and verification requirements.

## Engineering Workflow
Requirement → Specification → Impact Analysis → Design → Implementation → Tests → Verification → Human Gate → Accepted Change.

## Human-on-the-loop
Routine, reversible, testable work may proceed autonomously. Human review is mandatory for major architecture decisions, database/schema changes, breaking interfaces, security-sensitive changes, major dependency decisions, production-impacting operations, unresolved business rules, irreversible/high-risk actions, and final acceptance of significant deliverables.

## MVP Acceptance Criterion
ACA must reconstruct an evidence-backed engineering model and use it to evaluate architecture, code quality, engineering risk, and technical debt.
