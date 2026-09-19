"""Canonical in-memory CodeGraph model with deterministic identity and serialization."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import json
from typing import Any, Iterable

SCHEMA_VERSION = "aca-graph-0.2"
NODE_TYPES = {"Repository","Revision","Module","Package","File","Class","Interface","Method","Field","Annotation"}
RELATIONS = {"CONTAINS","DECLARES","IMPLEMENTS","EXTENDS","CALLS","REFERENCES","DEPENDS_ON","INJECTS"}
PROVENANCE = {"deterministic","inferred"}

def stable_id(prefix: str, canonical_key: str) -> str:
    return f"{prefix}-{hashlib.sha256(canonical_key.encode('utf-8')).hexdigest()[:20]}"

def _require_analysis_run(value: str | None) -> str:
    if not value: raise ValueError("analysis_run_id is required")
    return value

def _identity_context(repository_id: str, revision: str | None) -> str:
    return f"{SCHEMA_VERSION}|{repository_id}|{revision or 'unversioned'}"

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
    def create(cls, node_type: str, repository_id: str, canonical_key: str, *,
               properties: dict[str, Any] | None = None, evidence_refs: Iterable[str] = (),
               provenance: str = "deterministic", analysis_run_id: str | None = None,
               revision: str | None = None) -> "Node":
        run_id = _require_analysis_run(analysis_run_id)
        identity = f"{_identity_context(repository_id, revision)}|{node_type}|{canonical_key}"
        return cls(stable_id("NODE", identity), node_type, repository_id, canonical_key,
                   properties or {}, tuple(sorted(set(evidence_refs))), provenance, run_id, revision)

    def to_dict(self) -> dict[str, Any]:
        return {"id":self.id,"type":self.type,"repository_id":self.repository_id,"revision":self.revision,
                "canonical_key":self.canonical_key,"properties":self.properties,
                "evidence_refs":list(self.evidence_refs),"provenance":self.provenance,
                "analysis_run_id":self.analysis_run_id}

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
    def create(cls, source: Node, relation: str, target: Node, *,
               evidence_refs: Iterable[str] = (), provenance: str = "deterministic",
               confidence: float | None = None, analysis_run_id: str | None = None,
               revision: str | None = None) -> "Edge":
        run_id = _require_analysis_run(analysis_run_id)
        effective_revision = source.revision if revision is None else revision
        identity = f"{_identity_context(source.repository_id,effective_revision)}|{source.canonical_key}|{relation}|{target.canonical_key}"
        return cls(stable_id("EDGE", identity), source.id, relation, target.id, source.repository_id,
                   tuple(sorted(set(evidence_refs))), provenance, confidence, run_id, effective_revision)

    def to_dict(self) -> dict[str, Any]:
        return {"id":self.id,"source":self.source,"relation":self.relation,"target":self.target,
                "repository_id":self.repository_id,"revision":self.revision,"provenance":self.provenance,
                "confidence":self.confidence,"evidence_refs":list(self.evidence_refs),
                "analysis_run_id":self.analysis_run_id}

class GraphValidationError(ValueError):
    pass

@dataclass
class Graph:
    repository: dict[str, Any]
    revision: str | None
    analysis_run_id: str
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: dict[str, Edge] = field(default_factory=dict)
    evidence: dict[str, dict[str, Any]] = field(default_factory=dict)

    def add_node(self, node: Node) -> None:
        if node.id in self.nodes:
            existing = self.nodes[node.id]
            if (existing.type,existing.repository_id,existing.canonical_key,existing.properties,
                existing.provenance,existing.analysis_run_id,existing.revision) != (
                node.type,node.repository_id,node.canonical_key,node.properties,
                node.provenance,node.analysis_run_id,node.revision):
                raise GraphValidationError(f"conflicting node identity: {node.id}")
            self.nodes[node.id] = replace(existing,evidence_refs=tuple(sorted(set(existing.evidence_refs)|set(node.evidence_refs))))
            return
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        if edge.id in self.edges and self.edges[edge.id] != edge:
            raise GraphValidationError(f"duplicate edge id: {edge.id}")
        self.edges[edge.id] = edge

    def add_evidence(self, records: Iterable[Any]) -> None:
        for record in records:
            data = record.__dict__.copy() if hasattr(record,"__dict__") else dict(record)
            self.evidence[data.pop("id")] = data

    def validate(self) -> list[dict[str,str]]:
        errors=[]; seen=set()
        if not self.analysis_run_id: errors.append({"code":"MISSING_GRAPH_ANALYSIS_RUN_ID","id":"graph"})
        for node in self.nodes.values():
            if node.type not in NODE_TYPES: errors.append({"code":"INVALID_NODE_TYPE","id":node.id})
            if not node.id or not node.repository_id or not node.canonical_key or not node.analysis_run_id: errors.append({"code":"MISSING_NODE_IDENTITY","id":node.id})
            if node.provenance not in PROVENANCE: errors.append({"code":"INVALID_NODE_PROVENANCE","id":node.id})
            if node.repository_id != self.repository.get("id"): errors.append({"code":"REPOSITORY_MISMATCH","id":node.id})
            if node.revision != self.revision: errors.append({"code":"REVISION_MISMATCH","id":node.id})
            if node.analysis_run_id != self.analysis_run_id: errors.append({"code":"ANALYSIS_RUN_MISMATCH","id":node.id})
            for ref in node.evidence_refs:
                if ref not in self.evidence: errors.append({"code":"UNRESOLVED_EVIDENCE","id":node.id,"evidence":ref})
        for edge in self.edges.values():
            if edge.source not in self.nodes: errors.append({"code":"ORPHAN_EDGE_SOURCE","id":edge.id})
            if edge.target not in self.nodes: errors.append({"code":"ORPHAN_EDGE_TARGET","id":edge.id})
            if edge.relation not in RELATIONS: errors.append({"code":"INVALID_RELATION","id":edge.id})
            if edge.provenance not in PROVENANCE: errors.append({"code":"INVALID_EDGE_PROVENANCE","id":edge.id})
            if not edge.id or not edge.repository_id or not edge.analysis_run_id: errors.append({"code":"MISSING_EDGE_IDENTITY","id":edge.id})
            if edge.provenance=="deterministic" and edge.confidence is not None: errors.append({"code":"DETERMINISTIC_CONFIDENCE","id":edge.id})
            if edge.provenance=="inferred" and edge.confidence is None: errors.append({"code":"INFERRED_MISSING_CONFIDENCE","id":edge.id})
            if edge.confidence is not None and not 0.0 <= edge.confidence <= 1.0: errors.append({"code":"INVALID_CONFIDENCE","id":edge.id})
            if edge.source in self.nodes and edge.target in self.nodes:
                src,tgt=self.nodes[edge.source],self.nodes[edge.target]
                if src.repository_id!=edge.repository_id or tgt.repository_id!=edge.repository_id: errors.append({"code":"REPOSITORY_MISMATCH","id":edge.id})
                if edge.revision!=self.revision: errors.append({"code":"REVISION_MISMATCH","id":edge.id})
                if edge.analysis_run_id!=self.analysis_run_id: errors.append({"code":"ANALYSIS_RUN_MISMATCH","id":edge.id})
                key=(edge.source,edge.relation,edge.target)
                if key in seen: errors.append({"code":"DUPLICATE_CANONICAL_EDGE","id":edge.id})
                seen.add(key)
            for ref in edge.evidence_refs:
                if ref not in self.evidence: errors.append({"code":"UNRESOLVED_EVIDENCE","id":edge.id,"evidence":ref})
        return errors

    def require_valid(self):
        errors=self.validate()
        if errors: raise GraphValidationError(json.dumps(errors,sort_keys=True))

    def find_node(self,node_id): return self.nodes.get(node_id)
    def outgoing(self,node_id,relation=None): return sorted([e for e in self.edges.values() if e.source==node_id and (relation is None or e.relation==relation)],key=lambda e:e.id)
    def incoming(self,node_id,relation=None): return sorted([e for e in self.edges.values() if e.target==node_id and (relation is None or e.relation==relation)],key=lambda e:e.id)
    def neighbors(self,node_id):
        ids={e.target for e in self.outgoing(node_id)}|{e.source for e in self.incoming(node_id)}
        return sorted((self.nodes[i] for i in ids),key=lambda n:n.id)
    def paths(self,source_id,target_id,max_depth=5):
        if max_depth<0:return []
        paths=[]; queue=[[source_id]]
        while queue:
            path=queue.pop(0); current=path[-1]
            if current==target_id: paths.append(path); continue
            if len(path)-1>=max_depth: continue
            for edge in self.outgoing(current):
                if edge.target not in path: queue.append(path+[edge.target])
        return paths

    def to_dict(self):
        self.require_valid()
        repository={k:v for k,v in self.repository.items() if k not in {"source_path","workspace_id","scan_timestamp"}}
        return {"schema_version":SCHEMA_VERSION,"repository":repository,"revision":self.revision,
                "analysis_run_id":self.analysis_run_id,
                "nodes":[n.to_dict() for n in sorted(self.nodes.values(),key=lambda x:x.id)],
                "edges":[e.to_dict() for e in sorted(self.edges.values(),key=lambda x:x.id)],
                "evidence":[{"id":k,**self.evidence[k]} for k in sorted(self.evidence)]}

    def to_json(self): return json.dumps(self.to_dict(),indent=2,sort_keys=True)+"\n"

    @classmethod
    def from_dict(cls,data):
        if data.get("schema_version")!=SCHEMA_VERSION: raise GraphValidationError("unsupported graph schema version")
        graph=cls(dict(data["repository"]),data.get("revision"),data["analysis_run_id"],
                   evidence={item["id"]:{k:v for k,v in item.items() if k!="id"} for item in data.get("evidence",[])})
        for item in data.get("nodes",[]):
            graph.add_node(Node(item["id"],item["type"],item["repository_id"],item["canonical_key"],
                                item.get("properties",{}),tuple(item.get("evidence_refs",[])),
                                item.get("provenance","deterministic"),item.get("analysis_run_id"),item.get("revision")))
        for item in data.get("edges",[]):
            graph.add_edge(Edge(item["id"],item["source"],item["relation"],item["target"],item["repository_id"],
                                tuple(item.get("evidence_refs",[])),item.get("provenance","deterministic"),
                                item.get("confidence"),item.get("analysis_run_id"),item.get("revision")))
        graph.require_valid(); return graph
