""""Deterministic ACA-005 candidate mapping rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .model import CandidateMapping, ReconciliationRequest


@dataclass(frozen=True)
class MappingRule:
    name: str
    version: str
    signal: str

    def apply(
        self,
        source_node: Mapping[str, Any],
        target_nodes: Iterable[Mapping[str, Any]],
        request: ReconciliationRequest,
    ) -> tuple[CandidateMapping, ...]:
        candidates = []
        source_id = str(source_node["id"])
        source_type = source_node.get("type")
        source_key = source_node.get("canonical_key", source_id)
        for target in target_nodes:
            if target.get("type") != source_type:
                continue
            target_id = str(target["id"])
            target_key = target.get("canonical_key", target_id)
            if source_key != target_key:
                continue
            candidates.append(
                CandidateMapping.create(
                    source_id,
                    target_id,
                    reconciliation_id=request.reconciliation_id,
                    methodology_version=request.methodology_version,
                    state="CONFIRMED",
                    provenance="deterministic",
                    mapping_signals=(self.signal,),
                    evidence_refs=tuple(sorted(set(source_node.get("evidence_refs", ())) | set(target.get("evidence_refs", ())))),
                    source_repository_id=request.source_context.repository_id,
                    source_revision=request.source_context.revision,
                    target_repository_id=request.target_context.repository_id,
                    target_revision=request.target_context.revision,
                )
            )
        return tuple(sorted(candidates, key=lambda item: item.mapping_id))


@dataclass(frozen=True)
class StructuralSignalRule(MappingRule):
    """Match deterministic structural identities exposed by graph producers.

    Only explicit structural properties are used. Absence of a supported
    signature is intentionally treated as no match.
    """

    def apply(
        self,
        source_node: Mapping[str, Any],
        target_nodes: Iterable[Mapping[str, Any]],
        request: ReconciliationRequest,
    ) -> tuple[CandidateMapping, ...]:
        source_props = source_node.get("properties") or {}
        source_type = source_node.get("type")
        source_signature = (
            source_props.get("normalized_signature")
            or source_props.get("signature")
            or source_props.get("api_signature")
        )
        if not source_signature:
            return ()
        candidates = []
        for target in target_nodes:
            if target.get("type") != source_type:
                continue
            target_props = target.get("properties") or {}
            target_signature = (
                target_props.get("normalized_signature")
                or target_props.get("signature")
                or target_props.get("api_signature")
            )
            if target_signature != source_signature:
                continue
            candidates.append(CandidateMapping.create(
                str(source_node["id"]), str(target["id"]),
                reconciliation_id=request.reconciliation_id,
                methodology_version=request.methodology_version,
                state="INFERRED",
                provenance="inferred",
                confidence=0.8,
                mapping_signals=(self.signal,),
                evidence_refs=tuple(sorted(set(source_node.get("evidence_refs", ())) | set(target.get("evidence_refs", ())))),
                rationale="Deterministic structural signature matched; semantic equivalence is not asserted.",
                source_repository_id=request.source_context.repository_id,
                source_revision=request.source_context.revision,
                target_repository_id=request.target_context.repository_id,
                target_revision=request.target_context.revision,
            ))
        return tuple(sorted(candidates, key=lambda item: item.mapping_id))


class MappingRuleRegistry:
    """Apply mapping rules as an ordered, staged strategy.

    Rule order is semantic precedence, not merely execution order. Once a
    higher-precedence rule produces candidates, weaker rules are not allowed
    to add competing candidates for the same source node. This preserves
    deterministic precedence while still retaining ambiguity among candidates
    produced by the winning stage.
    """

    def __init__(self, rules: Iterable[MappingRule] | None = None) -> None:
        self._rules = tuple(rules or (
            MappingRule("exact-canonical-identity", "0.1", "EXACT_CANONICAL_IDENTITY"),
            StructuralSignalRule("structural-signature", "0.1", "STRUCTURAL_SIGNATURE"),
        ))

    @property
    def version(self) -> str:
        return "+".join(f"{r.name}@{r.version}" for r in self._rules)

    def map_nodes(
        self,
        source_node: Mapping[str, Any],
        target_nodes: Iterable[Mapping[str, Any]],
        request: ReconciliationRequest,
    ) -> tuple[CandidateMapping, ...]:
        targets = tuple(target_nodes)
        for rule in self._rules:
            candidates = rule.apply(source_node, targets, request)
            if candidates:
                return tuple(sorted(candidates, key=lambda item: item.mapping_id))
        return ()
"