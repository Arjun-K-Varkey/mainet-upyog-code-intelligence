"""Deterministic CodeGraph structural reconciliation for ACA-005."""

from __future__ import annotations

from typing import Any

from src.aca_graph.model import Graph
from .mapping import MappingRuleRegistry
from .model import CandidateMapping, ReconciliationFinding, ReconciliationRequest


class StructuralReconciler:
    """Compare two validated CodeGraph instances without semantic inference."""

    def __init__(self, mapping_registry: MappingRuleRegistry | None = None) -> None:
        self.mapping_registry = mapping_registry or MappingRuleRegistry()

    def reconcile(
        self,
        source_graph: Graph,
        target_graph: Graph,
        request: ReconciliationRequest,
    ) -> tuple[tuple[CandidateMapping, ...], tuple[ReconciliationFinding, ...]]:
        self._validate_contexts(source_graph, target_graph, request)

        source_nodes = tuple(sorted(source_graph.nodes.values(), key=lambda n: n.id))
        target_nodes = tuple(sorted(target_graph.nodes.values(), key=lambda n: n.id))

        mappings: list[CandidateMapping] = []
        for source in source_nodes:
            source_dict = source.to_dict()
            source_candidates = self.mapping_registry.map_nodes(source_dict, (n.to_dict() for n in target_nodes), request)
            for candidate in source_candidates:
                mappings.append(self._with_context_identity(candidate, source_graph, target_graph))

        findings: list[ReconciliationFinding] = []
        by_source: dict[str, list[CandidateMapping]] = {}
        by_target: dict[str, list[CandidateMapping]] = {}
        for mapping in mappings:
            by_source.setdefault(mapping.source_node, []).append(mapping)
            if mapping.target_node is not None:
                by_target.setdefault(mapping.target_node, []).append(mapping)

        matched_sources = set(by_source)
        matched_targets = set(by_target)

        for source in source_nodes:
            candidates = tuple(sorted(by_source.get(source.id, ()), key=lambda m: m.mapping_id))
            if not candidates:
                findings.append(self._finding(
                    "REMOVAL", "CONFIRMED", source.id, None, source, None,
                    source_graph, target_graph, rationale="Source node has no deterministic target mapping.",
                    source_evidence_refs=source.evidence_refs,
                ))
            elif len(candidates) == 1:
                mapping = candidates[0]
                target = target_graph.nodes[mapping.target_node]  # type: ignore[index]
                findings.append(self._finding(
                    "MATCH", "CONFIRMED", source.id, target.id, source, target,
                    source_graph, target_graph,
                    related_mapping_ids=(mapping.mapping_id,),
                    evidence_refs=tuple(sorted(set(source.evidence_refs) | set(target.evidence_refs))),
                    source_evidence_refs=source.evidence_refs,
                    target_evidence_refs=target.evidence_refs,
                ))
            else:
                alternatives = tuple(sorted(m.target_node for m in candidates if m.target_node))
                findings.append(self._finding(
                    "AMBIGUOUS_MAPPING", "AMBIGUOUS", source.id, None, source, None,
                    source_graph, target_graph,
                    rationale="Multiple deterministic candidates remain; no silent selection is permitted.",
                    related_mapping_ids=tuple(m.mapping_id for m in candidates),
                    boundaries=({"type": "AMBIGUOUS_MAPPING", "alternatives": alternatives},),
                    source_evidence_refs=source.evidence_refs,
                ))

        for target in target_nodes:
            if target.id not in matched_targets:
                findings.append(self._finding(
                    "ADDITION", "CONFIRMED", None or "", target.id, None, target,
                    source_graph, target_graph,
                    rationale="Target node has no deterministic source mapping.",
                    target_evidence_refs=target.evidence_refs,
                ))

        findings.extend(self._relationship_findings(source_graph, target_graph, mappings, request))
        return (
            tuple(sorted(mappings, key=lambda m: m.mapping_id)),
            tuple(sorted(findings, key=lambda f: f.finding_id)),
        )

    @staticmethod
    def _validate_contexts(source_graph: Graph, target_graph: Graph, request: ReconciliationRequest) -> None:
        if source_graph.repository.get("id") != request.source_context.repository_id:
            raise ValueError("SOURCE_GRAPH_CONTEXT_MISMATCH")
        if target_graph.repository.get("id") != request.target_context.repository_id:
            raise ValueError("TARGET_GRAPH_CONTEXT_MISMATCH")
        if source_graph.revision != request.source_context.revision:
            raise ValueError("SOURCE_GRAPH_REVISION_MISMATCH")
        if target_graph.revision != request.target_context.revision:
            raise ValueError("TARGET_GRAPH_REVISION_MISMATCH")
        if source_graph.repository.get("id") == target_graph.repository.get("id") and source_graph.revision == target_graph.revision:
            raise ValueError("IDENTICAL_GRAPH_CONTEXTS")

    @staticmethod
    def _finding(category: str, state: str, source_id: str | None, target_id: str | None,
                 source_node: Any, target_node: Any, source_graph: Graph, target_graph: Graph,
                 *, evidence_refs=(), source_evidence_refs=(), target_evidence_refs=(),
                 rationale=None, related_mapping_ids=(), boundaries=()):
        return ReconciliationFinding.create(
            category, state, "deterministic", source_id or "", target_id,
            _context_from_graph(source_graph), _context_from_graph(target_graph),
            reconciliation_id="structural",
            evidence_refs=tuple(evidence_refs),
            source_evidence_refs=tuple(source_evidence_refs),
            target_evidence_refs=tuple(target_evidence_refs),
            rationale=rationale,
            related_mapping_ids=tuple(related_mapping_ids),
            boundaries=tuple(boundaries),
        )

    @staticmethod
    def _relationship_findings(source_graph: Graph, target_graph: Graph,
                               mappings: list[CandidateMapping],
                               request: ReconciliationRequest) -> list[ReconciliationFinding]:
        mapping_by_source = {m.source_node: m for m in mappings if m.target_node and m.state == "CONFIRMED"}
        results: list[ReconciliationFinding] = []
        for edge in sorted(source_graph.edges.values(), key=lambda e: e.id):
            sm = mapping_by_source.get(edge.source)
            tm = mapping_by_source.get(edge.target)
            if not sm or not tm:
                continue
            matching = [
                candidate for candidate in target_graph.edges.values()
                if candidate.relation == edge.relation
                and candidate.source == sm.target_node
                and candidate.target == tm.target_node
            ]
            if matching:
                continue
            results.append(ReconciliationFinding.create(
                "RELATIONSHIP_CHANGE", "CONFIRMED", "deterministic",
                edge.id, None, _context_from_graph(source_graph), _context_from_graph(target_graph),
                reconciliation_id=request.reconciliation_id,
                source_evidence_refs=edge.evidence_refs,
                rationale="Source relationship has no corresponding target relationship.",
                related_mapping_ids=(sm.mapping_id, tm.mapping_id),
                related_edge_ids=(edge.id,),
            ))
        return results


def _context_from_graph(graph: Graph):
    from .model import RepositoryContext
    return RepositoryContext(
        project_id=str(graph.repository.get("project_id", graph.repository.get("id", ""))),
        repository_id=str(graph.repository.get("id", "")),
        revision=graph.revision,
        analysis_run_id=graph.analysis_run_id,
        graph_schema_version="aca-graph-0.2",
    )
