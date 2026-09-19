"""Canonical in-memory CodeGraph model with deterministic identity and serialization."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Iterable


SCHEMA_VERSION = "aca-graph-0.2"
NODE_TYPES = {
    "Repository", "Revision", "Module", "Package", "File", "Class",
    "Interface", "Method", "Field", "Annotation",
}
RELATIONS = {
    "CONTAINS", "DECLARES", "IMPLEMENTS", "EXTENDS", "CALLS",
    "REFERENCES", "DEPENDS_ON", "INJECTS",
}
PROVENANCE = {"deterministic", "inferred"}


def stable_id(prefix: str, canonical_key: str) -> str:
    return f"{prefix}-{hashlib.sha256(canonical_key.encode('utf-8')).hexdigest()[:20]}"


@dataclass(frozen=True)
class Node:
    id: str
    type: str
    repository_id: str
    canonical_key: str
    properties: dict[str, Any] = field(default_factory=dict)
    evidence_refs: tuple[str, ...] = ()
    provenance: str = "deterministic"
    analysis_run_id: str | None = None
    revision: str | None = None

    @classmethod
    def create(
        cls,
        node_type: str,
        repository_id: str,
        canonical_key: str,
        *,
        properties: dict[str, Any] | None = None,
        evidence_refs: Iterable[str] = (),
        provenance: str = "deterministic",
        analysis_run_id: str | None = None,
        revision: str | None = None,
    ) -> "Node":
        return cls(
            id=stable_id("NODE", f"{node_type}:{canonical_key}"),
            type=node_type,
            repository_id=repository_id,
            canonical_key=canonical_key,
            properties=properties or {},
            evidence_refs=tuple(sorted(set(evidence_refs))),
            provenance=provenance,
            analysis_run_id=analysis_run_id,
            revision=revision,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "repository_id": self.repository_id,
            "revision": self.revision,
            "canonical_key": self.canonical_key,
            "properties": self.properties,
            "evidence_refs": list(self.evidence_refs),
            "provenance": self.provenance,
            "analysis_run_id": self.analysis_run_id,
        }


@dataclass(frozen=True)
class Edge:
    id: str
    source: str
    relation: str
    target: str
    repository_id: str
    evidence_refs: tuple[str, ...] = ()
    provenance: str = "deterministic"
    confidence: float | None = None
    analysis_run_id: str | None = None
    revision: str | None = None

    @classmethod
    def create(
        cls,
        source: Node,
        relation: str,
        target: Node,
        *,
        evidence_refs: Iterable[str] = (),
        provenance: str = "deterministic",
        confidence: float | None = None,
        analysis_run_id: str | None = None,
        revision: str | None = None,
    ) -> "Edge":
        canonical = f"{source.canonical_key}|{relation}|{target.canonical_key}|{revision or ''}"
        return cls(
            id=stable_id("EDGE", canonical),
            source=source.id,
            relation=relation,
            target=target.id,
            repository_id=source.repository_id,
            evidence_refs=tuple(sorted(set(evidence_refs))),
            provenance=provenance,
            confidence=confidence,
            analysis_run_id=analysis_run_id,
            revision=revision,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "relation": self.relation,
            "target": self.target,
            "repository_id": self.repository_id,
            "revision": self.revision,
            "provenance": self.provenance,
            "confidence": self.confidence,
            "evidence_refs": list(self.evidence_refs),
            "analysis_run_id": self.analysis_run_id,
        }


class GraphValidationError(ValueError):
    """Raised when a graph violates the canonical graph contract."""


@dataclass
class Graph:
    repository: dict[str, Any]
    revision: str | None
    analysis_run_id: str
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: dict[str, Edge] = field(default_factory=dict)
    evidence: dict[str, dict[str, Any]] = field(default_factory=dict)

    def add_node(self, node: Node) -> None:
        if node.id in self.nodes and self.nodes[node.id] != node:
            raise GraphValidationError(f"duplicate node id: {node.id}")
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        if edge.id in self.edges and self.edges[edge.id] != edge:
            raise GraphValidationError(f"duplicate edge id: {edge.id}")
        self.edges[edge.id] = edge

    def add_evidence(self, records: Iterable[Any]) -> None:
        for record in records:
            data = record.__dict__.copy() if hasattr(record, "__dict__") else dict(record)
            evidence_id = data.pop("id")
            self.evidence[evidence_id] = data

    def validate(self) -> list[dict[str, str]]:
        errors: list[dict[str, str]] = []
        seen_canonical: set[tuple[str, str, str]] = set()

        for node in self.nodes.values():
            if node.type not in NODE_TYPES:
                errors.append({"code": "INVALID_NODE_TYPE", "id": node.id})
            if not node.id or not node.repository_id or not node.canonical_key:
                errors.append({"code": "MISSING_NODE_IDENTITY", "id": node.id})
            if node.provenance not in PROVENANCE:
                errors.append({"code": "INVALID_NODE_PROVENANCE", "id": node.id})
            for ref in node.evidence_refs:
                if ref not in self.evidence:
                    errors.append({"code": "UNRESOLVED_EVIDENCE", "id": node.id, "evidence": ref})

        for edge in self.edges.values():
            if edge.source not in self.nodes:
                errors.append({"code": "ORPHAN_EDGE_SOURCE", "id": edge.id})
            if edge.target not in self.nodes:
                errors.append({"code": "ORPHAN_EDGE_TARGET", "id": edge.id})
            if edge.relation not in RELATIONS:
                errors.append({"code": "INVALID_RELATION", "id": edge.id})
            if edge.provenance not in PROVENANCE:
                errors.append({"code": "INVALID_EDGE_PROVENANCE", "id": edge.id})
            if edge.provenance == "deterministic" and edge.confidence is not None:
                errors.append({"code": "DETERMINISTIC_CONFIDENCE", "id": edge.id})
            if edge.provenance == "inferred" and edge.confidence is None:
                errors.append({"code": "INFERRED_MISSING_CONFIDENCE", "id": edge.id})
            if edge.source in self.nodes and edge.target in self.nodes:
                src, tgt = self.nodes[edge.source], self.nodes[edge.target]
                if src.repository_id != edge.repository_id or tgt.repository_id != edge.repository_id:
                    errors.append({"code": "REPOSITORY_MISMATCH", "id": edge.id})
                key = (edge.source, edge.relation, edge.target)
                if key in seen_canonical:
                    errors.append({"code": "DUPLICATE_CANONICAL_EDGE", "id": edge.id})
                seen_canonical.add(key)
            for ref in edge.evidence_refs:
                if ref not in self.evidence:
                    errors.append({"code": "UNRESOLVED_EVIDENCE", "id": edge.id, "evidence": ref})

        return errors

    def require_valid(self) -> None:
        errors = self.validate()
        if errors:
            raise GraphValidationError(json.dumps(errors, sort_keys=True))

    def find_node(self, node_id: str) -> Node | None:
        return self.nodes.get(node_id)

    def outgoing(self, node_id: str, relation: str | None = None) -> list[Edge]:
        return sorted(
            [e for e in self.edges.values() if e.source == node_id and (relation is None or e.relation == relation)],
            key=lambda e: e.id,
        )

    def incoming(self, node_id: str, relation: str | None = None) -> list[Edge]:
        return sorted(
            [e for e in self.edges.values() if e.target == node_id and (relation is None or e.relation == relation)],
            key=lambda e: e.id,
        )

    def neighbors(self, node_id: str) -> list[Node]:
        ids = {e.target for e in self.outgoing(node_id)} | {e.source for e in self.incoming(node_id)}
        return sorted((self.nodes[i] for i in ids), key=lambda n: n.id)

    def paths(self, source_id: str, target_id: str, max_depth: int = 5) -> list[list[str]]:
        if max_depth < 0:
            return []
        paths: list[list[str]] = []
        queue: list[list[str]] = [[source_id]]
        while queue:
            path = queue.pop(0)
            current = path[-1]
            if current == target_id:
                paths.append(path)
                continue
            if len(path) - 1 >= max_depth:
                continue
            for edge in self.outgoing(current):
                if edge.target not in path:
                    queue.append(path + [edge.target])
        return paths

    def to_dict(self) -> dict[str, Any]:
        self.require_valid()
        return {
            "schema_version": SCHEMA_VERSION,
            "repository": self.repository,
            "revision": self.revision,
            "analysis_run_id": self.analysis_run_id,
            "nodes": [n.to_dict() for n in sorted(self.nodes.values(), key=lambda x: x.id)],
            "edges": [e.to_dict() for e in sorted(self.edges.values(), key=lambda x: x.id)],
            "evidence": [{"id": k, **self.evidence[k]} for k in sorted(self.evidence)],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"
