# ACA-TOOLS-001 — Tool Contracts

**Version:** 0.1

## Tool Families

### Repository
read_file, list_files, search_code, search_symbol, search_reference.

### Code Intelligence
parse_source, extract_symbols, resolve_type, find_callers, find_callees, build_dependency_graph.

### Database
extract_sql, resolve_table, resolve_column, map_entity_table, build_data_flow.

### Framework
 detect_framework, resolve_controller, resolve_route, resolve_dependency_injection, resolve_configuration, trace_request.

### Knowledge
query_graph, query_evidence, semantic_search, get_architecture, get_specification, get_impact.

### Execution
create_workspace, apply_patch, run_build, run_tests, run_static_analysis, generate_diff.

### Git
create_branch, status, diff, history, commit.

### Governance
calculate_risk, request_review, record_decision, record_audit.

## CQAI Tooling
Static-analysis and architecture-analysis tools should expose deterministic findings as evidence. AI reasoning consumes these results rather than replacing them.

## Tool Security
Tools are capability-scoped. Analysts are read/analyze-only; implementation agents can write only in isolated workspaces and branch-scoped Git; verifiers can read/analyze/test but cannot modify implementation.

## Contract Requirements
Outputs must be structured, attributable to a source/run, deterministic where possible, and suitable for persistence as evidence.
