# AI Engineering Agent Contract

This repository is developed using a Product Creation lifecycle and Spec-Driven Development.

## Mission

Build an evidence-backed code intelligence platform for Mainet and UPYOG that can reconstruct software structure and behavior, trace end-to-end flows, reconcile systems, and generate trustworthy technical specifications.

## Operating hierarchy

```text
Product
  ↓
Requirement
  ↓
Specification
  ↓
Acceptance Criteria
  ↓
Architecture
  ↓
Implementation
  ↓
Tests
  ↓
Evidence
  ↓
Review
  ↓
Release
```

## Agent roles

Operational role definitions live under `.ai/agents/`:
- product-agent
- spec-agent
- architecture-agent
- coding-agent
- test-agent
- evidence-agent
- review-agent

## Mandatory policies

Read and follow:
- `.ai/policies/evidence-first.md`
- `.ai/policies/spec-driven.md`
- `.ai/policies/git-safety.md`
- `.ai/policies/source-read-only.md`

## Agent execution rule

An agent must select a Ready work item, read its specification and acceptance criteria, inspect the relevant repository state, implement only the approved scope, test it, collect evidence, review the diff, and report blockers.

Agents must not silently redefine product requirements or convert inference into fact.

## Repository safety

- Do not modify Mainet/UPYOG source merely for analysis.
- Do not commit secrets or credentials.
- Do not declare work complete without validation evidence.
- Prefer branch + commit + pull request for consequential changes.
