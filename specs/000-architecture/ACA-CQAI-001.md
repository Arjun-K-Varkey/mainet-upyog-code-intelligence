# ACA-CQAI-001 — Code Quality & Architecture Intelligence

**Version:** 0.1  
**Status:** Initial specification

## Purpose
Define ACA's first-class capability for evidence-backed code quality, architecture, engineering risk, and technical-debt intelligence.

## Finding Contract
Every material finding should contain:
- Finding ID
- Category and subject
- Detection method
- Evidence references
- Observed/inferred status
- Confidence and severity
- Root cause
- Impacted components
- Recommendation
- Remediation options and risk
- Required tests
- Validation status

## Capability Areas
### Principles
SOLID (SRP/OCP/LSP/ISP/DIP), DRY, KISS, YAGNI, GRASP.

### Patterns
GoF pattern recognition, misuse, and opportunity analysis.

### Architecture
Clean Architecture, Hexagonal Architecture, Layered Architecture, DDD, dependency-direction rules.

### Runtime Risk
Security, performance, concurrency, transactions.

### Interfaces & Data
API design and database-access patterns.

### Reliability
Error handling and observability.

### Testing
Test architecture and regression-safety analysis.

### Evolution
Legacy hotspots, technical debt, architecture drift.

## Detection Strategy
Use deterministic/static analysis wherever a property can be established mechanically. Use AI reasoning for interpretation, architectural intent, causal analysis, prioritization, and recommendations.

## Technical Debt
Quantify debt using structural and historical signals such as complexity, coupling, duplication, architecture violations, security exposure, test weakness, change frequency, defect history, and remediation effort.

## Architecture Drift
Compare intended and observed architecture and track new, resolved, and worsening violations over time.

## Prioritization
Prioritize by severity, confidence, blast radius, change frequency, engineering/business impact, remediation cost, and risk.

## Evaluation
Each capability requires ground-truth datasets and measurable precision, recall, false-positive/negative rates, evidence accuracy, severity accuracy, recommendation quality, and impact-analysis accuracy.
