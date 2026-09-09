# Product Creation Lifecycle

## Purpose

This repository follows a Product Creation lifecycle so that product intent, specifications, architecture, implementation, validation, and release remain traceable.

## Lifecycle

```text
Product Vision
      ↓
Product Requirements
      ↓
Spec Sprint
      ↓
Architecture / Design
      ↓
Engineering
      ↓
Test / Evidence / Validation
      ↓
Review / Acceptance
      ↓
Release
      ↓
Feedback → Next Product Cycle
```

## Engineering state flow

```text
Backlog → Ready → In Progress → Review → Validation → Done
```

## AI operating model

```text
Product Agent
      ↓
Spec Agent
      ↓
Architecture Agent
      ↓
Coding Agent
      ↓
Test Agent
      ↓
Evidence Agent
      ↓
Review Agent
```

These are agent roles. They may initially be executed by one AI engineering runtime.

## Core rules

1. No major implementation without a specification.
2. No specification without acceptance criteria.
3. No AI-generated specification without evidence.
4. No completion without verification evidence.
5. Repository facts must be traceable to source evidence.
6. Inference must be labelled as inference.
7. Mainet/UPYOG source repositories are read-only analysis inputs.
8. Consequential changes go through Git review.

## Definition of Done

An item is Done only when:
- the approved scope is implemented;
- acceptance criteria are satisfied;
- relevant tests pass;
- evidence is recorded;
- material documentation/spec changes are made;
- the diff has been reviewed;
- no blocking defects or unexplained high-risk changes remain.
