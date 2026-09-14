# ACA-ARCH-001 — Reference Architecture

**Version:** 0.2  
**Status:** Baseline

## Architectural Principle
ACA separates facts, knowledge, reasoning, actions, verification, and governance.

## Major Planes
1. Source & Observation Plane
2. Engineering Knowledge Plane
3. AI Reasoning Plane
4. Execution Plane
5. Verification Plane
6. Governance Plane

## Core Flow
Repository → Deterministic Analysis → Evidence Model → Engineering Graph → AI Reasoning → Controlled Action → Verification → Governance.

## Knowledge Architecture
- Relational state: projects, scans, tasks, agents, specifications, findings, status, governance.
- Graph: code and architecture relationships.
- Search/semantic: source and engineering-language retrieval.
- Object/evidence store: immutable snapshots, reports, diffs, logs, and test artifacts.

> Graph for relationships. Search for meaning. Relational storage for state. Object storage for evidence.

## ACA Intelligence Layer
ACA Intelligence contains:
- Code Quality Intelligence
- Architecture Intelligence
- Engineering Risk Intelligence
- Engineering Evolution Intelligence

## ACA-CQAI
First-class subsystem covering SOLID, DRY, KISS, YAGNI, GRASP, GoF, Clean Architecture, Hexagonal Architecture, Layered Architecture, DDD, dependency rules, security, performance, concurrency, transactions, API design, database access, error handling, observability, test architecture, legacy hotspots, technical debt, and architecture drift.

## CQAI Pipeline
Source Code → Static/Deterministic Analysis → Evidence Model → Architecture Graph → Quality/Architecture/Risk Analysis → AI Reasoning → Findings & Causes → Recommendations → Impact Analysis → Remediation Plan → Verification.

## Agents
Repository Analyst, Code Intelligence Agent, Runtime/Framework Analyst, Architecture Agent, Specification Agent, Impact Analysis Agent, Implementation Agent, Test Agent, Critic/Verifier, Documentation Agent, and Orchestrator.

The Critic/Verifier is conceptually independent from the implementation agent.

## Execution and Verification
Changes occur in isolated workspaces/branches. Verification includes compilation, tests, static analysis, diff analysis, evidence validation, critic review, and risk assessment.

## Autonomy
Target autonomy is A3: autonomous engineering workflows with explicit human gates. Production-impacting A4 actions require explicit human authorization.

## Architecture Drift
ACA compares intended architecture with actual architecture and reports new, resolved, or worsening drift with evidence, risk, and remediation recommendations.
