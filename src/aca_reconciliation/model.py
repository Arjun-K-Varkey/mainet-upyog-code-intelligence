"""ACA-005 canonical reconciliation model.

This module contains only deterministic, provenance-aware value objects and
serialization/validation helpers. It deliberately does not perform matching.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping

SCHEMA_VERSION = "aca-recon-0.1"
STATES = frozenset({"CONFIRMED", "INFERRED", "AMBIGUOUS", "CONTRADICTED", "UNKNOWN"})
PROVENANCE = frozenset({"deterministic", "inferred"})
CATEGORIES = frozenset({
    "MATCH", "ADDITION", "REMOVAL", "STRUCTURAL_CHANGE", "RELATIONSHIP_CHANGE",
    "BEHAVIORAL_DIVERGENCE", "BEHAVIORAL_MATCH", "AMBIGUOUS_MAPPING",
    "CONTRADICTION", "UNRESOLVED",
})


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _id(prefix: str, payload: Any) -> str:
    return f"{prefix}-{hashlib.sha256(_canonical(payload).encode()).hexdigest()[:20]}"


@dataclass(frozen=True)
class RepositoryContext:
    project_id: str
    repository_id: str
    revision: str | None
    analysis_run_id: str
    graph_schema_version: str
    trace_methodology_version: str | None = None
    trace_analyzer_version: str | None = None
    evidence_schema_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id, "repository_id": self.repository_id,
            "revision": self.revision, "analysis_run_id": self.analysis_run_id,
            "graph_schema_version": self.graph_schema_version,
            "trace_methodology_version": self.trace_methodology_version,
            "trace_analyzer_version": self.trace_analyzer_version,
            "evidence_schema_version": self.evidence_schema_version,
        }


@dataclass(frozen=True)
class ReconciliationRequest:
    reconciliation_id: str
    source_context: RepositoryContext
    target_context: RepositoryContext
    scope: Mapping[str, Any] | None = None
    comparison_mode: str = "STRUCTURAL_AND_TRACE"
    mapping_policy: str = "DETERMINISTIC"
    analyzer_version: str = "aca-recon-analyzer-0.1"
    methodology_version: str = "aca-recon-method-0.1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "reconciliation_id": self.reconciliation_id,
            "source_context": self.source_context.to_dict(),
            "target_context": self.target_context.to_dict(),
            "scope": dict(self.scope or {}),
            "comparison_mode": self.comparison_mode,
            "mapping_policy": self.mapping_policy,
            "analyzer_version": self.analyzer_version,
            "methodology_version": self.methodology_version,
        }


@dataclass(frozen=True)
class CandidateMapping:
    mapping_id: str
    source_node: str
    target_node: str | None
    state: str
    provenance: str
    confidence: float | None = None
    evidence_refs: tuple[str, ...] = ()
    rationale: str | None = None
    mapping_signals: tuple[str, ...] = ()
    alternatives: tuple[str, ...] = ()

    @classmethod
    def create(cls, source_node: str, target_node: str | None, *,
               reconciliation_id: str, methodology_version: str, state: str,
               provenance: str, confidence: float | None = None,
               source_repository_id: str | None = None, source_revision: str | None = None,
               target_repository_id: str | None = None, target_revision: str | None = None,
               evidence_refs: tuple[str, ...] = (), rationale: str | None = None,
               mapping_signals: tuple[str, ...] = (), alternatives: tuple[str, ...] = ()) -> "CandidateMapping":
        payload = {
            "schema": SCHEMA_VERSION, "reconciliation_id": reconciliation_id,
            "methodology": methodology_version,
            "source_repository_id": source_repository_id,
            "source_revision": source_revision,
            "target_repository_id": target_repository_id,
            "target_revision": target_revision,
            "source": source_node, "target": target_node,
        }
        return cls(_id("MAP", payload), source_node, target_node, state, provenance,
                   confidence, tuple(sorted(set(evidence_refs))), rationale,
                   tuple(sorted(set(mapping_signals))), tuple(sorted(set(alternatives))))

    def to_dict(self) -> dict[str, Any]:
        return {"mapping_id": self.mapping_id, "source_node": self.source_node,
                "target_node": self.target_node, "state": self.state,
                "provenance": self.provenance, "confidence": self.confidence,
                "evidence_refs": list(self.evidence_refs), "rationale": self.rationale,
                "mapping_signals": list(self.mapping_signals), "alternatives": list(self.alternatives)}


@dataclass(frozen=True)
class ReconciliationFinding:
    finding_id: str
    category: str
    state: str
    provenance: str
    source_subject: str
    target_subject: str | None
    source_context: RepositoryContext
    target_context: RepositoryContext
    evidence_refs: tuple[str, ...] = ()
    source_evidence_refs: tuple[str, ...] = ()
    target_evidence_refs: tuple[str, ...] = ()
    rationale: str | None = None
    related_mapping_ids: tuple[str, ...] = ()
    related_trace_ids: tuple[str, ...] = ()
    related_edge_ids: tuple[str, ...] = ()
    boundaries: tuple[Mapping[str, Any], ...] = ()
    confidence: float | None = None

    @classmethod
    def create(cls, category: str, state: str, provenance: str, source_subject: str,
               target_subject: str | None, source_context: RepositoryContext,
               target_context: RepositoryContext, *, reconciliation_id: str,
               evidence_refs: tuple[str, ...] = (), source_evidence_refs: tuple[str, ...] = (),
               target_evidence_refs: tuple[str, ...] = (), rationale: str | None = None,
               related_mapping_ids: tuple[str, ...] = (), related_trace_ids: tuple[str, ...] = (),
               related_edge_ids: tuple[str, ...] = (), boundaries: tuple[Mapping[str, Any], ...] = (),
               confidence: float | None = None) -> "ReconciliationFinding":
        payload = {
            "schema": SCHEMA_VERSION, "reconciliation_id": reconciliation_id,
            "category": category,
            "source_repository_id": source_context.repository_id,
            "source_revision": source_context.revision,
            "target_repository_id": target_context.repository_id,
            "target_revision": target_context.revision,
            "source": source_subject, "target": target_subject,
        }
        return cls(_id("FND", payload), category, state, provenance, source_subject, target_subject,
                   source_context, target_context, tuple(sorted(set(evidence_refs))),
                   tuple(sorted(set(source_evidence_refs))), tuple(sorted(set(target_evidence_refs))),
                   rationale, tuple(sorted(set(related_mapping_ids))),
                   tuple(sorted(set(related_trace_ids))), tuple(sorted(set(related_edge_ids))),
                   tuple(dict(b) for b in boundaries), confidence)

    def to_dict(self) -> dict[str, Any]:
        return {"finding_id": self.finding_id, "category": self.category, "state": self.state,
                "provenance": self.provenance, "source_subject": self.source_subject,
                "target_subject": self.target_subject, "source_context": self.source_context.to_dict(),
                "target_context": self.target_context.to_dict(), "evidence_refs": list(self.evidence_refs),
                "source_evidence_refs": list(self.source_evidence_refs),
                "target_evidence_refs": list(self.target_evidence_refs), "rationale": self.rationale,
                "related_mapping_ids": list(self.related_mapping_ids),
                "related_trace_ids": list(self.related_trace_ids),
                "related_edge_ids": list(self.related_edge_ids),
                "boundaries": [dict(b) for b in self.boundaries], "confidence": self.confidence}


@dataclass(frozen=True)
class ReconciliationResult:
    reconciliation_id: str
    source_context: RepositoryContext
    target_context: RepositoryContext
    request: ReconciliationRequest
    mappings: tuple[CandidateMapping, ...] = ()
    findings: tuple[ReconciliationFinding, ...] = ()
    summaries: Mapping[str, Any] | None = None
    boundaries: tuple[Mapping[str, Any], ...] = ()
    contradictions: tuple[Mapping[str, Any], ...] = ()
    analyzer_version: str = "aca-recon-analyzer-0.1"
    methodology_version: str = "aca-recon-method-0.1"

    def to_dict(self) -> dict[str, Any]:
        self.require_valid()
        return {"schema_version": SCHEMA_VERSION, "reconciliation_id": self.reconciliation_id,
                "source_context": self.source_context.to_dict(),
                "target_context": self.target_context.to_dict(), "request": self.request.to_dict(),
                "mappings": [m.to_dict() for m in sorted(self.mappings, key=lambda x: x.mapping_id)],
                "findings": [f.to_dict() for f in sorted(self.findings, key=lambda x: x.finding_id)],
                "summaries": dict(self.summaries or {}),
                "boundaries": [dict(x) for x in sorted(self.boundaries, key=_canonical)],
                "contradictions": [dict(x) for x in sorted(self.contradictions, key=_canonical)],
                "analyzer_version": self.analyzer_version, "methodology_version": self.methodology_version}

    def to_json(self) -> str:
        return _canonical(self.to_dict()) + "\n"

    def validate(self) -> list[dict[str, Any]]:
        errors: list[dict[str, Any]] = []
        if not self.reconciliation_id:
            errors.append({"code": "MISSING_RECONCILIATION_ID"})
        if self.source_context.repository_id == self.target_context.repository_id and self.source_context.revision == self.target_context.revision:
            errors.append({"code": "IDENTICAL_REPOSITORY_CONTEXTS"})
        if self.request.reconciliation_id != self.reconciliation_id:
            errors.append({"code": "REQUEST_CONTEXT_MISMATCH"})
        for mapping in self.mappings:
            if mapping.state not in STATES: errors.append({"code": "INVALID_MAPPING_STATE", "id": mapping.mapping_id})
            if mapping.provenance not in PROVENANCE: errors.append({"code": "INVALID_MAPPING_PROVENANCE", "id": mapping.mapping_id})
            if mapping.provenance == "inferred" and mapping.confidence is None:
                errors.append({"code": "INFERRED_MISSING_CONFIDENCE", "id": mapping.mapping_id})
            if mapping.confidence is not None and not 0 <= mapping.confidence <= 1:
                errors.append({"code": "INVALID_CONFIDENCE", "id": mapping.mapping_id})
            if mapping.state == "AMBIGUOUS" and not mapping.alternatives:
                errors.append({"code": "AMBIGUOUS_MISSING_ALTERNATIVES", "id": mapping.mapping_id})
            if mapping.state == "UNKNOWN" and mapping.target_node is not None:
                errors.append({"code": "UNKNOWN_HAS_TARGET", "id": mapping.mapping_id})
        ids = [m.mapping_id for m in self.mappings]
        if len(ids) != len(set(ids)): errors.append({"code": "DUPLICATE_MAPPING_ID"})
        fids = [f.finding_id for f in self.findings]
        if len(fids) != len(set(fids)): errors.append({"code": "DUPLICATE_FINDING_ID"})
        for finding in self.findings:
            if finding.category not in CATEGORIES: errors.append({"code": "INVALID_FINDING_CATEGORY", "id": finding.finding_id})
            if finding.state not in STATES: errors.append({"code": "INVALID_FINDING_STATE", "id": finding.finding_id})
            if finding.provenance not in PROVENANCE: errors.append({"code": "INVALID_FINDING_PROVENANCE", "id": finding.finding_id})
            if finding.provenance == "inferred" and finding.confidence is None:
                errors.append({"code": "INFERRED_MISSING_CONFIDENCE", "id": finding.finding_id})
            if finding.confidence is not None and not 0 <= finding.confidence <= 1:
                errors.append({"code": "INVALID_CONFIDENCE", "id": finding.finding_id})
            if finding.state == "AMBIGUOUS" and not finding.boundaries and not finding.rationale:
                errors.append({"code": "AMBIGUOUS_MISSING_CONTEXT", "id": finding.finding_id})
            if finding.state == "UNKNOWN" and not finding.boundaries:
                errors.append({"code": "UNKNOWN_MISSING_BOUNDARY", "id": finding.finding_id})
            if finding.state == "CONTRADICTED" and not self.contradictions:
                errors.append({"code": "CONTRADICTED_MISSING_RECORD", "id": finding.finding_id})
        return errors

    def require_valid(self) -> None:
        errors = self.validate()
        if errors: raise ValueError(_canonical(errors))
