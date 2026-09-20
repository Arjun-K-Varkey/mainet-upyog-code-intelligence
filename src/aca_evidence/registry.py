"""Read-only in-memory canonical Evidence registry and resolver."""
from __future__ import annotations
from typing import Iterable
from .model import Evidence, EvidenceValidationError

class EvidenceRegistry:
    """Deterministic index of canonical Evidence records."""
    def __init__(self, records: Iterable[Evidence] = ()) -> None:
        self._records: dict[str, Evidence] = {}
        for record in records:
            self.add(record)

    def add(self, record: Evidence) -> None:
        if not isinstance(record, Evidence):
            raise EvidenceValidationError("INVALID_EVIDENCE_RECORD")
        record.require_valid()
        existing = self._records.get(record.id)
        if existing is not None and existing.to_json() != record.to_json():
            raise EvidenceValidationError("DUPLICATE_EVIDENCE_ID")
        self._records[record.id] = record

    def contains(self, evidence_id: str) -> bool:
        return evidence_id in self._records

    def get(self, evidence_id: str) -> Evidence | None:
        return self._records.get(evidence_id)

    def require(self, evidence_id: str) -> Evidence:
        record = self.get(evidence_id)
        if record is None:
            raise EvidenceValidationError(f"UNRESOLVED_EVIDENCE:{evidence_id}")
        return record

    def resolve(self, evidence_refs: Iterable[str], *, repository_id: str | None = None,
                revision: str | None = None, run_id: str | None = None) -> tuple[str, ...]:
        resolved = []
        for evidence_id in sorted(set(evidence_refs)):
            record = self.require(evidence_id)
            record.require_valid(repository_id=repository_id, revision=revision, run_id=run_id)
            resolved.append(record.id)
        return tuple(resolved)

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._records))

class EvidenceResolver:
    """Resolver interface backed by an EvidenceRegistry."""
    def __init__(self, registry: EvidenceRegistry):
        self.registry = registry

    def resolve(self, evidence_refs: Iterable[str], **context: str | None) -> tuple[str, ...]:
        return self.registry.resolve(evidence_refs, **context)

    def get(self, evidence_id: str) -> Evidence | None:
        return self.registry.get(evidence_id)
