"""Deterministic, evidence-backed tracing over the ACA CodeGraph."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Iterable

from .model import Edge, Graph, GraphValidationError, Node

TRACE_SCHEMA_VERSION = "aca-trace-0.1"
TRACE_STATES = {"CONFIRMED", "INFERRED", "AMBIGUOUS", "CONTRADICTED", "UNKNOWN"}
DIRECTIONS = {"OUTGOING", "INCOMING", "BOTH"}


@dataclass(frozen=True)
class TraceRequest:
    source_id: str
    target_id: str | None = None
    direction: str = "OUTGOING"
    max_depth: int = 5
    allowed_relations: tuple[str, ...] = ()
    excluded_relations: tuple[str, ...] = ()
    allowed_node_types: tuple[str, ...] = ()
    max_paths: int = 100

    def __post_init__(self) -> None:
        if not self.source_id:
            raise ValueError("source_id is required")
        if self.direction not in DIRECTIONS:
            raise ValueError(f"invalid direction: {self.direction}")
        if self.max_depth < 0:
            raise ValueError("max_depth must be >= 0")
        if self.max_paths <= 0:
            raise ValueError("max_paths must be > 0")
        if self.allowed_relations and self.excluded_relations:
            overlap = set(self.allowed_relations) & set(self.excluded_relations)
            if overlap:
                raise ValueError(f"relationship both allowed and excluded: {sorted(overlap)}")


@dataclass(frozen=True)
class TracePath:
    node_ids: tuple[str, ...]
    edge_ids: tuple[str, ...]
    state: str
    confidence: float | None
    evidence_refs: tuple[str, ...]
    provenance: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "node_ids": list(self.node_ids),
            "edge_ids": list(self.edge_ids),
            "state": self.state,
            "confidence": self.confidence,
            "evidence_refs": list(self.evidence_refs),
            "provenance": list(self.provenance),
        }


@dataclass(frozen=True)
class TraceResult:
    trace_id: str
    request: TraceRequest
    repository_id: str
    revision: str | None
    analysis_run_id: str
    paths: tuple[TracePath, ...]
    state: str
    evidence_refs: tuple[str, ...]
    provenance: tuple[str, ...]
    confidence: float | None
    reason: str | None = None

    def to_dict(self) -> dict:
        request = {
            "source_id": self.request.source_id,
            "target_id": self.request.target_id,
            "direction": self.request.direction,
            "max_depth": self.request.max_depth,
            "allowed_relations": list(self.request.allowed_relations),
            "excluded_relations": list(self.request.excluded_relations),
            "allowed_node_types": list(self.request.allowed_node_types),
            "max_paths": self.request.max_paths,
        }
        return {
            "schema_version": TRACE_SCHEMA_VERSION,
            "trace_id": self.trace_id,
            "repository_id": self.repository_id,
            "revision": self.revision,
            "analysis_run_id": self.analysis_run_id,
            "request": request,
            "source": self.request.source_id,
            "target": self.request.target_id,
            "paths": [p.to_dict() for p in self.paths],
            "state": self.state,
            "evidence_refs": list(self.evidence_refs),
            "provenance": list(self.provenance),
            "confidence": self.confidence,
            "reason": self.reason,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


class TraceValidationError(ValueError):
    pass


class TraceEngine:
    """Read-only deterministic traversal over a validated CodeGraph."""

    def __init__(self, graph: Graph):
        graph.require_valid()
        self.graph = graph

    def trace(
        self,
        request: TraceRequest,
    ) -> TraceResult:
        self._validate_request(request)
        paths = self._enumerate_paths(request)
        trace_paths = tuple(self._make_path(path_nodes, path_edges) for path_nodes, path_edges in paths)

        if not trace_paths:
            state = "UNKNOWN"
            reason = "NO_PATH"
            confidence = None
        elif len(trace_paths) > 1:
            state = "AMBIGUOUS"
            reason = "MULTIPLE_CANDIDATE_PATHS"
            confidence = self._aggregate_confidence(trace_paths)
        elif trace_paths[0].state == "INFERRED":
            state = "INFERRED"
            reason = None
            confidence = trace_paths[0].confidence
        else:
            state = "CONFIRMED"
            reason = None
            confidence = None

        evidence = tuple(sorted({ref for path in trace_paths for ref in path.evidence_refs}))
        provenance = tuple(sorted({value for path in trace_paths for value in path.provenance}))
        trace_id = self._trace_id(request)

        return TraceResult(
            trace_id=trace_id,
            request=request,
            repository_id=self.graph.repository["id"],
            revision=self.graph.revision,
            analysis_run_id=self.graph.analysis_run_id,
            paths=trace_paths,
            state=state,
            evidence_refs=evidence,
            provenance=provenance,
            confidence=confidence,
            reason=reason,
        )

    def _validate_request(self, request: TraceRequest) -> None:
        source = self.graph.find_node(request.source_id)
        if source is None:
            raise TraceValidationError("source node does not exist")
        if request.target_id is not None and self.graph.find_node(request.target_id) is None:
            raise TraceValidationError("target node does not exist")
        if request.allowed_relations:
            invalid = set(request.allowed_relations) - set(self.graph.edges[e].relation for e in self.graph.edges)
            if invalid:
                raise TraceValidationError(f"unsupported relationship types: {sorted(invalid)}")
        if request.excluded_relations:
            invalid = set(request.excluded_relations) - set(self.graph.edges[e].relation for e in self.graph.edges)
            if invalid:
                raise TraceValidationError(f"unsupported relationship types: {sorted(invalid)}")
        if request.allowed_node_types:
            unknown = set(request.allowed_node_types) - {
                node.type for node in self.graph.nodes.values()
            }
            if unknown:
                raise TraceValidationError(f"unsupported node types: {sorted(unknown)}")
        if source.repository_id != self.graph.repository["id"] or source.revision != self.graph.revision:
            raise TraceValidationError("source node is outside graph context")
        if request.target_id:
            target = self.graph.find_node(request.target_id)
            assert target is not None
            if target.repository_id != self.graph.repository["id"] or target.revision != self.graph.revision:
                raise TraceValidationError("target node is outside graph context")

    def _edges_from(self, node_id: str, direction: str) -> list[tuple[Edge, str]]:
        result: list[tuple[Edge, str]] = []
        if direction in {"OUTGOING", "BOTH"}:
            result.extend((edge, edge.target) for edge in self.graph.outgoing(node_id))
        if direction in {"INCOMING", "BOTH"}:
            result.extend((edge, edge.source) for edge in self.graph.incoming(node_id))
        return sorted(result, key=lambda item: (item[0].id, item[1]))

    def _edge_allowed(self, edge: Edge, request: TraceRequest) -> bool:
        if request.allowed_relations and edge.relation not in request.allowed_relations:
            return False
        if edge.relation in request.excluded_relations:
            return False
        target = self.graph.find_node(edge.target)
        source = self.graph.find_node(edge.source)
        if target is None or source is None:
            return False
        if request.allowed_node_types and (
            target.type not in request.allowed_node_types
            or source.type not in request.allowed_node_types
        ):
            return False
        return True

    def _enumerate_paths(self, request: TraceRequest) -> list[tuple[tuple[str, ...], tuple[Edge, ...]]]:
        queue: list[tuple[tuple[str, ...], tuple[Edge, ...]]] = [((request.source_id,), ())]
        results: list[tuple[tuple[str, ...], tuple[Edge, ...]]] = []

        while queue and len(results) < request.max_paths:
            node_ids, edges = queue.pop(0)
            current = node_ids[-1]
            if request.target_id is not None and current == request.target_id and edges:
                results.append((node_ids, edges))
                continue
            if request.target_id is None and edges:
                results.append((node_ids, edges))
            if len(edges) >= request.max_depth:
                continue

            for edge, next_node in self._edges_from(current, request.direction):
                if not self._edge_allowed(edge, request):
                    continue
                if next_node in node_ids:
                    continue
                queue.append((node_ids + (next_node,), edges + (edge,)))

        return results

    def _make_path(self, node_ids: tuple[str, ...], edges: tuple[Edge, ...]) -> TracePath:
        inferred = [edge for edge in edges if edge.provenance == "inferred"]
        state = "INFERRED" if inferred else "CONFIRMED"
        confidence = min(edge.confidence for edge in inferred) if inferred else None
        evidence = tuple(sorted({ref for edge in edges for ref in edge.evidence_refs}))
        provenance = tuple(sorted({edge.provenance for edge in edges}))
        return TracePath(node_ids, tuple(edge.id for edge in edges), state, confidence, evidence, provenance)

    @staticmethod
    def _aggregate_confidence(paths: Iterable[TracePath]) -> float | None:
        values = [path.confidence for path in paths if path.confidence is not None]
        return min(values) if values else None

    def _trace_id(self, request: TraceRequest) -> str:
        payload = {
            "schema": TRACE_SCHEMA_VERSION,
            "repository": self.graph.repository["id"],
            "revision": self.graph.revision,
            "source": request.source_id,
            "target": request.target_id,
            "direction": request.direction,
            "max_depth": request.max_depth,
            "allowed_relations": sorted(request.allowed_relations),
            "excluded_relations": sorted(request.excluded_relations),
            "allowed_node_types": sorted(request.allowed_node_types),
            "max_paths": request.max_paths,
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return f"TRACE-{digest[:20]}"

    @staticmethod
    def from_json(data: str) -> TraceResult:
        raw = json.loads(data)
        if raw.get("schema_version") != TRACE_SCHEMA_VERSION:
            raise TraceValidationError("unsupported trace schema version")
        request_raw = raw["request"]
        request = TraceRequest(
            source_id=request_raw["source_id"],
            target_id=request_raw.get("target_id"),
            direction=request_raw["direction"],
            max_depth=request_raw["max_depth"],
            allowed_relations=tuple(request_raw.get("allowed_relations", [])),
            excluded_relations=tuple(request_raw.get("excluded_relations", [])),
            allowed_node_types=tuple(request_raw.get("allowed_node_types", [])),
            max_paths=request_raw["max_paths"],
        )
        if raw.get("state") not in TRACE_STATES:
            raise TraceValidationError("invalid trace state")
        result = TraceResult(
            trace_id=raw["trace_id"],
            request=request,
            repository_id=raw["repository_id"],
            revision=raw.get("revision"),
            analysis_run_id=raw["analysis_run_id"],
            paths=tuple(
                TracePath(
                    tuple(path["node_ids"]),
                    tuple(path["edge_ids"]),
                    path["state"],
                    path.get("confidence"),
                    tuple(path.get("evidence_refs", [])),
                    tuple(path.get("provenance", [])),
                )
                for path in raw.get("paths", [])
            ),
            state=raw["state"],
            evidence_refs=tuple(raw.get("evidence_refs", [])),
            provenance=tuple(raw.get("provenance", [])),
            confidence=raw.get("confidence"),
            reason=raw.get("reason"),
        )
        expected_id = hashlib.sha256(
            json.dumps({
                "schema": TRACE_SCHEMA_VERSION,
                "repository": result.repository_id,
                "revision": result.revision,
                "source": request.source_id,
                "target": request.target_id,
                "direction": request.direction,
                "max_depth": request.max_depth,
                "allowed_relations": sorted(request.allowed_relations),
                "excluded_relations": sorted(request.excluded_relations),
                "allowed_node_types": sorted(request.allowed_node_types),
                "max_paths": request.max_paths,
            }, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:20]
        if result.trace_id != f"TRACE-{expected_id}":
            raise TraceValidationError("TRACE_ID_MISMATCH")
        if result.state == "CONFIRMED" and any(path.state != "CONFIRMED" for path in result.paths):
            raise TraceValidationError("CONFIRMED trace contains inferred path")
        return result
