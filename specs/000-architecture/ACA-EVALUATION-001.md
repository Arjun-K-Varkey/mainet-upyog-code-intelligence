# ACA-EVALUATION-001 — Evaluation Framework

**Version:** 0.1  
**Status:** Initial specification

## Goal
Measure whether ACA produces correct, complete, evidence-backed engineering intelligence and safe engineering changes.

## Evaluation Dimensions
- Correctness
- Completeness
- Evidence fidelity
- Confidence calibration
- Severity accuracy
- Recommendation quality
- Impact-analysis accuracy
- Regression safety
- Autonomy
- Human-intervention rate

## Capability Benchmarks
Ground truth is required for repository/code understanding, architecture reconstruction, SOLID, DRY, KISS, YAGNI, GRASP, GoF, Clean Architecture, Hexagonal Architecture, Layered Architecture, DDD, dependency rules, security, performance, concurrency, transactions, API design, database access, error handling, observability, test architecture, legacy hotspots, technical debt, and architecture drift.

## Metrics
Precision, recall, false-positive rate, false-negative rate, evidence accuracy, severity agreement, recommendation usefulness, and impact-analysis miss rate.

## Engineering Change Evaluation
Measure build success, test success, regression rate, requirement coverage, static-analysis delta, architectural-rule delta, human intervention, and rework/rollback frequency.

## Acceptance Principle
A fluent explanation is not a successful result if the underlying engineering conclusion is wrong or unsupported.
