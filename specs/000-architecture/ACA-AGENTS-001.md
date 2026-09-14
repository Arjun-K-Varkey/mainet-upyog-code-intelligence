# ACA-AGENTS-001 — Agent Specifications

**Version:** 0.1

## Agent Contract
Each agent receives structured task context, retrieves evidence, performs a defined responsibility, returns structured artifacts, includes evidence references and confidence, and enters verification.

## Agents
- **AGENT-000 Orchestrator:** workflow coordination, task assignment, evidence requirements, verification, escalation.
- **AGENT-001 Repository Analyst:** repository structure, modules, builds, dependencies, languages, frameworks, configuration, entry points.
- **AGENT-002 Code Intelligence:** symbols, types, calls, inheritance, annotations, dependencies using deterministic tooling.
- **AGENT-003 Runtime/Framework Analyst:** framework-mediated behavior such as JSP/controller/service/DAO/ORM/API flows and configuration.
- **AGENT-004 Architecture Agent:** logical architecture, layers, boundaries, dependencies, architectural styles, violations, hotspots.
- **AGENT-005 Specification Agent:** requirements plus evidence to specifications, acceptance criteria, and traceability.
- **AGENT-006 Impact Analysis Agent:** direct/indirect API, database, integration, configuration, deployment, and test impacts.
- **AGENT-007 Implementation Agent:** implements specified changes in an isolated workspace; does not reinterpret ambiguous requirements.
- **AGENT-008 Test Agent:** creates and executes tests based on behavior and acceptance criteria.
- **AGENT-009 Critic/Verifier:** independently evaluates evidence, specifications, architecture, code, tests, and recommendations; can reject results.
- **AGENT-010 Documentation Agent:** maintains derived specifications, architecture docs, ADRs, API docs, change summaries, and traceability.

## CQAI Specialists
CQAI may use specialist analyzers/agents for principles, architecture, runtime risk, interfaces/data, reliability, testing, and evolution. Specialists consume shared evidence rather than independently rediscovering facts.
