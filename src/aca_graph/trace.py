"""ACA-TRACE-001 deterministic, evidence-backed trace engine."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any

from .model import Edge, Graph, NODE_TYPES, RELATIONS

TRACE_SCHEMA_VERSION = "aca-trace-0.1"
METHODOLOGY_VERSION = "aca-trace-method-0.2"
ANALYZER_VERSION = "aca-trace-analyzer-0.2"
TRACE_STATES = frozenset({"CONFIRMED", "INFERRED", "AMBIGUOUS", "CONTRADICTED", "UNKNOWN"})
PROVENANCE = frozenset({"deterministic", "inferred"})
DIRECTIONS = frozenset({"OUTGOING", "INCOMING", "BOTH"})
BOUNDARY_TYPES = frozenset({
    "UNRESOLVED_PATH", "MISSING_EVIDENCE", "UNSUPPORTED_RELATION",
    "REFLECTION", "DYNAMIC_DISPATCH", "GENERATED_CODE_UNAVAILABLE",
    "EXTERNAL_SYSTEM", "DATABASE_MAPPING_UNRESOLVED", "UNREADABLE_EVIDENCE",
})


class TraceValidationError(ValueError):
    """Raised when a canonical trace violates ACA-TRACE-001."""


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
        if self.max_depth < 1:
            raise ValueError("max_depth must be >= 1")
        if self.max_paths < 1:
            raise ValueError("max_paths must be > 0")
        if set(self.allowed_relations) & set(self.excluded_relations):
            raise ValueError("relationship cannot be both allowed and excluded")


@dataclass(frozen=True)
class TraceStep:
    step_id: str
    sequence: int
    source_node: str
    relation: str
    target_node: str | None
    status: str
    provenance: str
    confidence: float | None
    evidence_refs: tuple[str, ...] = ()
    rationale: str | None = None
    boundaries: tuple[TraceBoundary, ...] = ()
    edge_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id, "sequence": self.sequence,
            "source_node": self.source_node, "relation": self.relation,
            "target_node": self.target_node, "status": self.status,
            "provenance": self.provenance, "confidence": self.confidence,
            "evidence_refs": list(self.evidence_refs), "rationale": self.rationale,
            "boundaries": [b.to_dict() for b in self.boundaries], "edge_id": self.edge_id,
        }


@dataclass(frozen=True)
class CandidatePath:
    steps: tuple[TraceStep, ...]
    status: str
    confidence: float | None
    rationale: str | None = None
    boundaries: tuple["TraceBoundary", ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"steps": [s.to_dict() for s in self.steps], "status": self.status,
                "confidence": self.confidence, "rationale": self.rationale,
                "boundaries": [b.to_dict() for b in self.boundaries]}


@dataclass(frozen=True)
class TraceBoundary:
    boundary_type: str
    at_step: int | None
    status: str
    reason: str
    evidence_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"boundary_type": self.boundary_type, "at_step": self.at_step,
                "status": self.status, "reason": self.reason,
                "evidence_refs": list(self.evidence_refs)}


@dataclass(frozen=True)
class Trace:
    trace_id: str
    repository_id: str
    revision: str | None
    analysis_run_id: str
    origin: str
    target: str | None
    status: str
    confidence: float | None
    methodology_version: str
    analyzer_version: str
    steps: tuple[TraceStep, ...] = ()
    alternatives: tuple[CandidatePath, ...] = ()
    evidence: tuple[str, ...] = ()
    boundaries: tuple[TraceBoundary, ...] = ()
    contradictions: tuple[dict[str, Any], ...] = ()

    def validate(self, graph: Graph | None = None) -> list[dict[str, Any]]:
        errors: list[dict[str, Any]] = []
        def add(code: str, message: str) -> None:
            errors.append({"code": code, "message": message})

        evidence_set = set(self.evidence)

        def validate_steps(steps: tuple[TraceStep, ...], context: str) -> None:
            ids = [s.step_id for s in steps]
            if len(ids) != len(set(ids)):
                add("DUPLICATE_STEP_ID", f"{context} step IDs must be unique")
            sequences = [s.sequence for s in steps]
            if sequences != list(range(1, len(sequences) + 1)):
                add("NON_CONTIGUOUS_SEQUENCE", f"{context} step sequence must start at 1 and be contiguous")
            for step in steps:
                if step.status not in TRACE_STATES:
                    add("INVALID_STEP_STATUS", f"invalid {context} step status: {step.status}")
                if step.provenance not in PROVENANCE:
                    add("INVALID_PROVENANCE", f"invalid {context} provenance: {step.provenance}")
                if step.confidence is not None and not 0 <= step.confidence <= 1:
                    add("STEP_CONFIDENCE_OUT_OF_RANGE", f"{context} step {step.step_id} confidence out of range")
                if step.provenance == "inferred" and step.confidence is None:
                    add("INFERRED_MISSING_CONFIDENCE", f"{context} step {step.step_id} requires confidence")
                if step.provenance == "deterministic" and step.confidence is not None:
                    add("DETERMINISTIC_UNSUPPORTED_CONFIDENCE", f"{context} step {step.step_id} must not carry confidence")
                if step.status in {"INFERRED", "AMBIGUOUS", "CONTRADICTED"} and not step.rationale:
                    add("MISSING_STEP_RATIONALE", f"{context} step {step.step_id} requires rationale")
                if step.status in {"CONFIRMED", "INFERRED", "AMBIGUOUS", "CONTRADICTED"} and not step.evidence_refs:
                    add("MISSING_STEP_EVIDENCE", f"{context} material step {step.step_id} requires evidence")
                if not set(step.evidence_refs).issubset(evidence_set):
                    add("UNRESOLVED_STEP_EVIDENCE", f"{context} step {step.step_id} references evidence not in trace evidence")
                for boundary_index, boundary in enumerate(step.boundaries, 1):
                    if boundary.boundary_type not in BOUNDARY_TYPES:
                        add("INVALID_STEP_BOUNDARY_TYPE", f"{context} step {step.step_id} boundary {boundary_index} has invalid type")
                    if boundary.status not in TRACE_STATES:
                        add("INVALID_STEP_BOUNDARY_STATUS", f"{context} step {step.step_id} boundary {boundary_index} has invalid status")
                    if not boundary.reason:
                        add("MISSING_STEP_BOUNDARY_REASON", f"{context} step {step.step_id} boundary {boundary_index} requires reason")
                    if not set(boundary.evidence_refs).issubset(evidence_set):
                        add("UNRESOLVED_STEP_BOUNDARY_EVIDENCE", f"{context} step {step.step_id} boundary {boundary_index} evidence does not resolve")
                if graph is not None:
                    if graph.find_node(step.source_node) is None:
                        add("MISSING_SOURCE_NODE", f"{context} step {step.step_id} source node does not exist")
                    if step.target_node is not None and graph.find_node(step.target_node) is None:
                        add("MISSING_TARGET_NODE", f"{context} step {step.step_id} target node does not exist")
                    if step.edge_id is not None:
                        edge = graph.edges.get(step.edge_id)
                        if edge is None:
                            add("MISSING_EDGE", f"{context} step {step.step_id} edge does not exist")
                        elif step.target_node is not None:
                            direct = edge.source == step.source_node and edge.target == step.target_node and edge.relation == step.relation
                            reversed_endpoints = edge.target == step.source_node and edge.source == step.target_node and edge.relation == step.relation
                            if not (direct or reversed_endpoints):
                                add("EDGE_ID_MISMATCH", f"{context} step {step.step_id} edge identity does not match endpoints/relation")

        if not self.repository_id:
            add("MISSING_REPOSITORY_ID", "repository_id is required")
        if not self.analysis_run_id:
            add("MISSING_ANALYSIS_RUN_ID", "analysis_run_id is required")
        if graph is not None:
            if self.repository_id != graph.repository["id"]:
                add("REPOSITORY_CONTEXT_MISMATCH", "trace repository does not match graph")
            if self.revision != graph.revision:
                add("REVISION_CONTEXT_MISMATCH", "trace revision does not match graph")
            if graph.find_node(self.origin) is None:
                add("MISSING_ORIGIN_NODE", "trace origin does not exist in graph")
            if self.target is not None and graph.find_node(self.target) is None:
                add("MISSING_TARGET_NODE", "trace target does not exist in graph")

        if self.status not in TRACE_STATES:
            add("INVALID_STATUS", f"unsupported trace status: {self.status}")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            add("TRACE_CONFIDENCE_OUT_OF_RANGE", "trace confidence must be between 0 and 1")
        if not self.origin:
            add("MISSING_ORIGIN", "origin is required")
        if not self.methodology_version or not self.analyzer_version:
            add("MISSING_VERSION", "methodology_version and analyzer_version are required")

        validate_steps(self.steps, "primary")
        for index, alternative in enumerate(self.alternatives, 1):
            if alternative.status not in TRACE_STATES:
                add("INVALID_ALTERNATIVE_STATUS", f"invalid alternative {index} status: {alternative.status}")
            if alternative.confidence is not None and not 0 <= alternative.confidence <= 1:
                add("ALTERNATIVE_CONFIDENCE_OUT_OF_RANGE", f"alternative {index} confidence out of range")
            if alternative.status == "INFERRED" and alternative.confidence is None:
                add("INFERRED_MISSING_CONFIDENCE", f"alternative {index} requires confidence")
            if alternative.status in {"INFERRED", "AMBIGUOUS", "CONTRADICTED"} and not alternative.rationale:
                add("MISSING_ALTERNATIVE_RATIONALE", f"alternative {index} requires rationale")
            if not alternative.steps:
                add("EMPTY_ALTERNATIVE", f"alternative {index} must contain steps")
            validate_steps(alternative.steps, f"alternative {index}")
            for boundary_index, boundary in enumerate(alternative.boundaries, 1):
                if boundary.boundary_type not in BOUNDARY_TYPES:
                    add("INVALID_ALTERNATIVE_BOUNDARY_TYPE", f"alternative {index} boundary {boundary_index} has invalid type")
                if boundary.status not in TRACE_STATES:
                    add("INVALID_ALTERNATIVE_BOUNDARY_STATUS", f"alternative {index} boundary {boundary_index} has invalid status")
                if not boundary.reason:
                    add("MISSING_ALTERNATIVE_BOUNDARY_REASON", f"alternative {index} boundary {boundary_index} requires reason")
                if not set(boundary.evidence_refs).issubset(evidence_set):
                    add("UNRESOLVED_ALTERNATIVE_BOUNDARY_EVIDENCE", f"alternative {index} boundary {boundary_index} evidence does not resolve")

        for boundary in self.boundaries:
            if boundary.boundary_type not in BOUNDARY_TYPES:
                add("INVALID_BOUNDARY_TYPE", f"unsupported boundary type: {boundary.boundary_type}")
            if boundary.status not in TRACE_STATES:
                add("INVALID_BOUNDARY_STATUS", f"unsupported boundary status: {boundary.status}")
            if not boundary.reason:
                add("MISSING_BOUNDARY_REASON", "boundary reason is required")
            if not set(boundary.evidence_refs).issubset(evidence_set):
                add("UNRESOLVED_BOUNDARY_EVIDENCE", "boundary evidence does not resolve")

        for index, contradiction in enumerate(self.contradictions, 1):
            if not isinstance(contradiction, dict):
                add("INVALID_CONTRADICTION", f"contradiction {index} must be an object")
                continue
            claims = contradiction.get("claims")
            refs = contradiction.get("evidence_refs")
            if not isinstance(claims, list) or len(claims) < 2:
                add("CONTRADICTION_MISSING_CLAIMS", f"contradiction {index} requires at least two conflicting claims")
            else:
                for claim_index, claim in enumerate(claims, 1):
                    if not isinstance(claim, dict) or not all(claim.get(k) for k in ("source_node", "relation", "target_node")):
                        add("INVALID_CONTRADICTION_CLAIM", f"contradiction {index} claim {claim_index} is incomplete")
                    claim_refs = claim.get("evidence_refs", []) if isinstance(claim, dict) else []
                    if not claim_refs or not set(claim_refs).issubset(evidence_set):
                        add("UNRESOLVED_CONTRADICTION_EVIDENCE", f"contradiction {index} claim {claim_index} evidence does not resolve")
            if not contradiction.get("affected_step"):
                add("CONTRADICTION_MISSING_AFFECTED_STEP", f"contradiction {index} requires affected_step")
            if not isinstance(refs, list) or not refs or not set(refs).issubset(evidence_set):
                add("UNRESOLVED_CONTRADICTION_EVIDENCE", f"contradiction {index} evidence does not resolve")
            if not contradiction.get("resolution_state"):
                add("CONTRADICTION_MISSING_RESOLUTION", f"contradiction {index} requires resolution_state")

        if self.status == "INFERRED" and self.confidence is None:
            add("INFERRED_MISSING_CONFIDENCE", "inferred trace requires confidence")
        if self.status == "CONTRADICTED" and not self.contradictions:
            add("CONTRADICTION_MISSING_EVIDENCE", "contradicted trace requires contradiction evidence")
        if self.status == "AMBIGUOUS" and not self.alternatives:
            add("AMBIGUITY_MISSING_ALTERNATIVES", "ambiguous trace requires alternatives")
        if self.status == "UNKNOWN" and not self.boundaries:
            add("UNKNOWN_MISSING_BOUNDARY", "unknown trace requires a boundary")

        expected = self.compute_id(
            repository_id=self.repository_id, revision=self.revision,
            origin=self.origin, target=self.target,
            methodology_version=self.methodology_version,
            analyzer_version=self.analyzer_version,
        )
        if self.trace_id != expected:
            add("TRACE_ID_MISMATCH", "trace_id does not match canonical identity")
        return errors

    def require_valid(self, graph: Graph | None = None) -> None:
        errors = self.validate(graph)
        if errors:
            raise TraceValidationError(json.dumps(errors, sort_keys=True))

    @staticmethod
    def compute_id(*, repository_id: str, revision: str | None, origin: str,
                   target: str | None, methodology_version: str,
                   analyzer_version: str) -> str:
        payload = {"schema": TRACE_SCHEMA_VERSION, "repository_id": repository_id,
                   "revision": revision, "origin": origin, "target": target,
                   "methodology_version": methodology_version, "analyzer_version": analyzer_version}
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return f"TRACE-{digest[:20]}"

    def to_dict(self) -> dict[str, Any]:
        self.require_valid()
        return {
            "schema_version": TRACE_SCHEMA_VERSION, "trace_id": self.trace_id,
            "repository_id": self.repository_id, "revision": self.revision,
            "analysis_run_id": self.analysis_run_id, "origin": self.origin,
            "target": self.target, "status": self.status, "confidence": self.confidence,
            "methodology_version": self.methodology_version, "analyzer_version": self.analyzer_version,
            "steps": [s.to_dict() for s in self.steps],
            "alternatives": [a.to_dict() for a in self.alternatives],
            "evidence": list(self.evidence),
            "boundaries": [b.to_dict() for b in self.boundaries],
            "contradictions": list(self.contradictions),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"

    @classmethod
    def from_dict(cls, raw: dict[str, Any], graph: Graph | None = None) -> "Trace":
        if raw.get("schema_version") != TRACE_SCHEMA_VERSION:
            raise TraceValidationError("UNSUPPORTED_TRACE_SCHEMA")
        def boundary(b: dict[str, Any]) -> TraceBoundary:
            return TraceBoundary(
                boundary_type=b["boundary_type"], at_step=b.get("at_step"),
                status=b["status"], reason=b["reason"],
                evidence_refs=tuple(b.get("evidence_refs", []))
            )

        def step(s: dict[str, Any]) -> TraceStep:
            return TraceStep(
                step_id=s["step_id"], sequence=s["sequence"], source_node=s["source_node"],
                relation=s["relation"], target_node=s.get("target_node"), status=s["status"],
                provenance=s["provenance"], confidence=s.get("confidence"),
                evidence_refs=tuple(s.get("evidence_refs", [])), rationale=s.get("rationale"),
                boundaries=tuple(boundary(b) for b in s.get("boundaries", [])), edge_id=s.get("edge_id"),
            )
        trace = cls(
            trace_id=raw["trace_id"], repository_id=raw["repository_id"], revision=raw.get("revision"),
            analysis_run_id=raw["analysis_run_id"], origin=raw["origin"], target=raw.get("target"),
            status=raw["status"], confidence=raw.get("confidence"),
            methodology_version=raw["methodology_version"], analyzer_version=raw["analyzer_version"],
            steps=tuple(step(s) for s in raw.get("steps", [])),
            alternatives=tuple(CandidatePath(
                steps=tuple(step(s) for s in c.get("steps", [])), status=c["status"],
                confidence=c.get("confidence"), rationale=c.get("rationale"),
                boundaries=tuple(boundary(b) for b in c.get("boundaries", [])))
                for c in raw.get("alternatives", [])),
            evidence=tuple(raw.get("evidence", [])),
            boundaries=tuple(TraceBoundary(
                boundary_type=b["boundary_type"], at_step=b.get("at_step"),
                status=b["status"], reason=b["reason"],
                evidence_refs=tuple(b.get("evidence_refs", [])))
                for b in raw.get("boundaries", [])),
            contradictions=tuple(raw.get("contradictions", [])),
        )
        trace.require_valid(graph)
        return trace


class TraceRule:
    """Versioned deterministic rule boundary for candidate classification."""

    name = "canonical-codegraph-edge"
    version = METHODOLOGY_VERSION

    def classify(self, edge: Edge) -> tuple[str, str, float | None]:
        if edge.provenance == "inferred":
            return "INFERRED", "inferred", edge.confidence
        return "CONFIRMED", "deterministic", None


class EvidenceResolver:
    """Resolves graph evidence identities without inventing evidence."""

    def __init__(self, graph: Graph):
        self.graph = graph

    def resolve(self, refs: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sorted(ref for ref in refs if ref in self.graph.evidence))


class ContradictionDetector:
    """Derive contradictions only from explicit evidence claims."""

    def __init__(self, graph: Graph):
        self.graph = graph

    def detect(self, candidates: tuple[CandidatePath, ...]) -> tuple[dict[str, Any], ...]:
        candidate_edge_ids = {
            step.edge_id for candidate in candidates for step in candidate.steps
            if step.edge_id is not None
        }
        results: list[dict[str, Any]] = []
        for evidence_id, record in sorted(self.graph.evidence.items()):
            if not isinstance(record, dict) or record.get("type") != "contradiction":
                continue
            edge_ids = tuple(record.get("edge_ids", ()))
            if len(edge_ids) < 2 or not all(edge_id in self.graph.edges for edge_id in edge_ids):
                continue
            edges = [self.graph.edges[eid] for eid in edge_ids]
            claims = [
                (edge.source, edge.relation, edge.target)
                for edge in edges
            ]
            if not all(edge.id in candidate_edge_ids for edge in edges):
                continue
            results.append({
                "affected_step": record.get("affected_step") or self._derive_affected_step(edges),
                "claims": [
                    {
                        "source_node": edge.source,
                        "relation": edge.relation,
                        "target_node": edge.target,
                        "evidence_refs": sorted(set(edge.evidence_refs) | {evidence_id}),
                    }
                    for edge in edges
                ],
                "evidence_refs": [evidence_id],
                "resolution_state": record.get("resolution_state", "UNRESOLVED"),
                "reason": record.get(
                    "reason",
                    "Explicit evidence identifies conflicting claims.",
                ),
            })
        return tuple(results)


    @staticmethod
    def _derive_affected_step(edges: list[Edge]) -> int | None:
        if not edges:
            return None
        return 1

class BoundaryClassifier:
    """Classifies unresolved boundaries from explicit evidence or deterministic context."""

    _ALIASES = {
        "reflection": "REFLECTION",
        "dynamic_dispatch": "DYNAMIC_DISPATCH",
        "generated_code_unavailable": "GENERATED_CODE_UNAVAILABLE",
        "external_system": "EXTERNAL_SYSTEM",
        "database_mapping_unresolved": "DATABASE_MAPPING_UNRESOLVED",
        "missing_evidence": "MISSING_EVIDENCE",
        "unreadable_evidence": "UNREADABLE_EVIDENCE",
    }

    def classify_no_path(self, request: TraceRequest) -> TraceBoundary:
        return TraceBoundary(
            boundary_type="UNSUPPORTED_RELATION" if request.allowed_relations else "MISSING_EVIDENCE",
            at_step=None,
            status="UNKNOWN",
            reason=(
                "No requested relationship was established by available CodeGraph evidence."
                if request.allowed_relations
                else "No supporting path was established from available CodeGraph evidence."
            ),
        )

    def classify_edge(self, edge: Edge, graph: Graph, sequence: int) -> TraceBoundary | None:
        for ref in sorted(edge.evidence_refs):
            record = graph.evidence.get(ref)
            if not isinstance(record, dict):
                continue
            boundary = record.get("boundary_type") or record.get("boundary")
            if boundary in self._ALIASES:
                return TraceBoundary(
                    boundary_type=self._ALIASES[boundary],
                    at_step=sequence,
                    status="UNKNOWN",
                    reason=record.get("reason", f"Evidence identifies {self._ALIASES[boundary]}."),
                    evidence_refs=(ref,),
                )
        return None


class TraceRuleRegistry:
    """Versioned deterministic rule registry.

    Rules are intentionally generic in ACA-TRACE-001's first implementation.
    Framework-specific JSP/Spring/JPA rules can be registered later without
    changing the canonical trace model.
    """

    def __init__(self, rules: tuple[TraceRule, ...] = (TraceRule(),)):
        self.rules = tuple(sorted(rules, key=lambda rule: (rule.name, rule.version)))

    def classify(self, edge: Edge) -> tuple[str, str, float | None]:
        classifications = [rule.classify(edge) for rule in self.rules]
        if not classifications:
            raise TraceValidationError("NO_TRACE_RULE")
        return classifications[0]

    @property
    def version(self) -> str:
        return "+".join(f"{rule.name}:{rule.version}" for rule in self.rules)


class TraceClassifier:
    """Classifies a candidate set after evidence and boundary analysis."""

    def classify(
        self,
        candidates: tuple[CandidatePath, ...],
        contradictions: tuple[dict[str, Any], ...],
    ) -> tuple[str, tuple[TraceStep, ...], tuple[CandidatePath, ...], float | None]:
        if contradictions:
            return "CONTRADICTED", (), candidates, None
        if not candidates:
            return "UNKNOWN", (), (), None
        if len(candidates) > 1:
            return "AMBIGUOUS", (), candidates, None
        candidate = candidates[0]
        return candidate.status, candidate.steps, (), candidate.confidence


class TraceEngine:
    """Deterministic candidate-path engine plus ACA-TRACE-001 semantic classification."""

    def __init__(self, graph: Graph, rule_registry: TraceRuleRegistry | None = None,
                 classifier: TraceClassifier | None = None):
        graph.require_valid()
        self.graph = graph
        self.rule_registry = rule_registry or TraceRuleRegistry()
        self.classifier = classifier or TraceClassifier()
        self.evidence_resolver = EvidenceResolver(graph)
        self.contradiction_detector = ContradictionDetector(graph)
        self.boundary_classifier = BoundaryClassifier()

    def trace(self, request: TraceRequest) -> Trace:
        self._validate_request(request)
        raw_paths, truncated = self._enumerate_paths(request)
        candidates = tuple(self._candidate_path(nodes, edges) for nodes, edges in raw_paths)
        contradictions = self.contradiction_detector.detect(candidates)

        classified_status, classified_steps, classified_alternatives, classified_confidence = (
            self.classifier.classify(candidates, contradictions)
        )

        if contradictions:
            status, steps, alternatives, confidence = "CONTRADICTED", (), candidates, None
            boundaries = (TraceBoundary(
                boundary_type="UNRESOLVED_PATH", at_step=None, status="CONTRADICTED",
                reason="Conflicting directly evidenced candidate claims remain unresolved.",
                evidence_refs=tuple(sorted({
                    ref for contradiction in contradictions for claim in contradiction["claims"]
                    for ref in claim["evidence_refs"]
                } | {
                    ref for contradiction in contradictions for ref in contradiction.get("evidence_refs", [])
                })),
            ),)
            boundaries = boundaries + self._aggregate_candidate_boundaries(candidates)
        elif not candidates:
            status, steps, alternatives, confidence = "UNKNOWN", (), (), None
            boundaries = (self.boundary_classifier.classify_no_path(request),)
        elif len(candidates) > 1:
            status, steps, alternatives, confidence = "AMBIGUOUS", (), candidates, None
            boundary_list = [TraceBoundary(
                boundary_type="UNRESOLVED_PATH", at_step=None, status="AMBIGUOUS",
                reason="Multiple materially distinct candidate paths remain unresolved.",
                evidence_refs=tuple(sorted({
                    ref for candidate in candidates for step in candidate.steps for ref in step.evidence_refs
                })),
            )]
            boundary_list.extend(self._aggregate_candidate_boundaries(candidates))
            if truncated:
                boundary_list.append(TraceBoundary(
                    boundary_type="UNRESOLVED_PATH", at_step=None, status="AMBIGUOUS",
                    reason="Candidate enumeration reached max_paths; additional candidate paths remain unresolved.",
                ))
            boundaries = tuple(boundary_list)
        else:
            candidate = candidates[0]
            if truncated:
                status, steps, alternatives, confidence = "AMBIGUOUS", (), candidates, None
                boundaries = (
                    TraceBoundary(
                        boundary_type="UNRESOLVED_PATH", at_step=None, status="AMBIGUOUS",
                        reason="Candidate enumeration reached max_paths; additional candidate paths remain unresolved.",
                    ),
                    *self._aggregate_candidate_boundaries(candidates),
                )
            else:
                status, steps, alternatives, confidence = (
                    classified_status, classified_steps, classified_alternatives, classified_confidence
                )
                boundaries = ()
                if status == "UNKNOWN":
                    boundaries = candidate.boundaries or (TraceBoundary(
                        boundary_type="MISSING_EVIDENCE", at_step=next(
                            (step.sequence for step in candidate.steps if not step.evidence_refs), None
                        ),
                        status="UNKNOWN",
                        reason="Material hop lacks resolvable supporting evidence and cannot be confirmed.",
                    ),)

        evidence = self.evidence_resolver.resolve(tuple(sorted({
            ref for candidate in candidates for step in candidate.steps for ref in step.evidence_refs
        })))
        evidence = tuple(sorted(set(evidence) | {
            ref for boundary in boundaries for ref in boundary.evidence_refs
        }))
        trace_id = Trace.compute_id(
            repository_id=self.graph.repository["id"], revision=self.graph.revision,
            origin=request.source_id, target=request.target_id,
            methodology_version=self.rule_registry.version, analyzer_version=ANALYZER_VERSION,
        )
        result = Trace(
            trace_id=trace_id, repository_id=self.graph.repository["id"],
            revision=self.graph.revision, analysis_run_id=self.graph.analysis_run_id,
            origin=request.source_id, target=request.target_id, status=status,
            confidence=confidence, methodology_version=METHODOLOGY_VERSION,
            analyzer_version=ANALYZER_VERSION, steps=steps, alternatives=alternatives,
            evidence=evidence, boundaries=boundaries, contradictions=contradictions,
        )
        result.require_valid(self.graph)
        return result

    def _validate_request(self, request: TraceRequest) -> None:
        source = self.graph.find_node(request.source_id)
        if source is None:
            raise TraceValidationError("MISSING_SOURCE_NODE")
        if source.repository_id != self.graph.repository["id"] or source.revision != self.graph.revision:
            raise TraceValidationError("SOURCE_CONTEXT_MISMATCH")
        if request.target_id is not None:
            target = self.graph.find_node(request.target_id)
            if target is None:
                raise TraceValidationError("MISSING_TARGET_NODE")
            if target.repository_id != self.graph.repository["id"] or target.revision != self.graph.revision:
                raise TraceValidationError("TARGET_CONTEXT_MISMATCH")
        unsupported_relations = (set(request.allowed_relations) | set(request.excluded_relations)) - RELATIONS
        if unsupported_relations:
            raise TraceValidationError("UNSUPPORTED_RELATION_FILTER:" + ",".join(sorted(unsupported_relations)))
        unsupported_types = set(request.allowed_node_types) - NODE_TYPES
        if unsupported_types:
            raise TraceValidationError("UNSUPPORTED_NODE_TYPE_FILTER:" + ",".join(sorted(unsupported_types)))

    def _edges_from(self, node_id: str, direction: str) -> list[tuple[Edge, str, str]]:
        edges = []
        if direction in {"OUTGOING", "BOTH"}:
            edges.extend((edge, edge.target, "OUTGOING") for edge in self.graph.outgoing(node_id))
        if direction in {"INCOMING", "BOTH"}:
            edges.extend((edge, edge.source, "INCOMING") for edge in self.graph.incoming(node_id))
        return sorted(edges, key=lambda item: (item[0].id, item[1], item[2]))

    def _edge_allowed(self, edge: Edge, request: TraceRequest) -> bool:
        if request.allowed_relations and edge.relation not in request.allowed_relations:
            return False
        if edge.relation in request.excluded_relations:
            return False
        source, target = self.graph.find_node(edge.source), self.graph.find_node(edge.target)
        if source is None or target is None:
            return False
        if request.allowed_node_types and (
            source.type not in request.allowed_node_types or target.type not in request.allowed_node_types
        ):
            return False
        return True

    def _enumerate_paths(self, request: TraceRequest) -> tuple[list[tuple[tuple[str, ...], tuple[tuple[Edge, str], ...]]], bool]:
        queue = [((request.source_id,), ())]
        results = []
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
            for edge, next_node, orientation in self._edges_from(current, request.direction):
                if not self._edge_allowed(edge, request) or next_node in node_ids:
                    continue
                queue.append((node_ids + (next_node,), edges + ((edge, orientation),)))
        return results, bool(queue)

    def _candidate_path(self, node_ids: tuple[str, ...], edges: tuple[tuple[Edge, str], ...]) -> CandidatePath:
        steps = []
        confidences = []
        missing_evidence = False
        boundary_found = False
        boundaries = []
        for sequence, (edge, orientation) in enumerate(edges, 1):
            status, provenance, confidence = self.rule_registry.classify(edge)
            evidence = self.evidence_resolver.resolve(tuple(sorted(edge.evidence_refs)))
            boundary = self.boundary_classifier.classify_edge(edge, self.graph, sequence)
            if boundary is not None:
                boundary_found = True
                boundaries.append(boundary)
                status, provenance, confidence = "UNKNOWN", "deterministic", None
            if not evidence:
                missing_evidence = True
                missing_boundary = TraceBoundary(
                    boundary_type="MISSING_EVIDENCE", at_step=sequence,
                    status="UNKNOWN",
                    reason="Material hop lacks resolvable supporting evidence.",
                )
                boundaries.append(missing_boundary)
                status, provenance, confidence = "UNKNOWN", "deterministic", None
            elif confidence is not None and status != "UNKNOWN":
                confidences.append(confidence)
            source_node, target_node = (
                (edge.source, edge.target) if orientation == "OUTGOING"
                else (edge.target, edge.source)
            )
            steps.append(TraceStep(
                step_id=self._step_id(sequence, source_node, edge, orientation),
                sequence=sequence, source_node=source_node,
                relation=edge.relation, target_node=target_node,
                status=status, provenance=provenance, confidence=confidence,
                evidence_refs=evidence,
                boundaries=tuple(b for b in boundaries if b.at_step == sequence),
                edge_id=edge.id,
                rationale=("Explicit boundary evidence prevents asserting this hop."
                           if boundary is not None else
                           "Material hop lacks resolvable supporting evidence."
                           if not evidence else
                           "Canonical CodeGraph relationship established deterministically."
                           if status == "CONFIRMED" else
                           "Canonical CodeGraph relationship is inferred."),
            ))
        if missing_evidence or boundary_found:
            return CandidatePath(steps=tuple(steps), status="UNKNOWN", confidence=None,
                                 rationale="At least one material hop is unresolved by evidence or boundary classification.",
            boundaries=tuple(boundaries),
)
        status = "INFERRED" if confidences else "CONFIRMED"
        confidence = min(confidences) if confidences else None
        return CandidatePath(steps=tuple(steps), status=status, confidence=confidence,
                             rationale=None if status == "CONFIRMED" else "At least one hop is inferred.",
            boundaries=tuple(boundaries),
)

    @staticmethod
    def _step_id(sequence: int, source_node: str, edge: Edge, orientation: str = "OUTGOING") -> str:
        target_node = edge.target if orientation == "OUTGOING" else edge.source
        payload = {"schema": TRACE_SCHEMA_VERSION, "sequence": sequence,
                   "source": source_node, "relation": edge.relation, "target": target_node,
                   "orientation": orientation}
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return f"STEP-{digest[:20]}"


def validate_trace_dict(raw: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        Trace.from_dict(raw)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return [{"code": "INVALID_TRACE", "message": str(exc)}]
    return []
