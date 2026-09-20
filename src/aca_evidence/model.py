"""ACA-EVIDENCE-001 canonical, immutable evidence model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import re
from types import MappingProxyType
from typing import Any, Mapping

SCHEMA_VERSION = "aca-evidence-0.2"
EVIDENCE_TYPES = frozenset({
    "source", "symbol", "call", "dependency", "sql", "api", "config",
    "test", "metric", "history", "runtime", "error", "revision",
})
STATUSES = frozenset({"VALID", "STALE", "INVALID", "REDACTED"})
_SECRET_KEYS = re.compile(r"(?i)(password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token|private[_-]?key)")
_SECRET_VALUE = re.compile(r"(?i)(AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{20,})")


class EvidenceValidationError(ValueError):
    """Raised when canonical evidence violates ACA-EVIDENCE-001."""


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({k: _freeze(value[k]) for k in sorted(value)})
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, tuple):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise EvidenceValidationError(f"UNSUPPORTED_VALUE_TYPE:{type(value).__name__}")


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw(v) for v in value]
    return value


def _canonical(value: Any) -> str:
    try:
        return json.dumps(_thaw(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise EvidenceValidationError(f"NON_CANONICAL_VALUE:{exc}") from exc


@dataclass(frozen=True)
class EvidenceSource:
    tool: str
    version: str
    file: str | None = None
    start_line: int | None = None
    end_line: int | None = None

    def __post_init__(self) -> None:
        if not self.tool or not self.version:
            raise EvidenceValidationError("SOURCE_TOOL_AND_VERSION_REQUIRED")
        if (self.start_line is None) != (self.end_line is None):
            raise EvidenceValidationError("SOURCE_LINE_RANGE_INCOMPLETE")
        if self.start_line is not None and (self.start_line < 1 or self.end_line < self.start_line):
            raise EvidenceValidationError("INVALID_SOURCE_LINE_RANGE")
        if self.file is not None and self.file.startswith(("/", "\\")):
            raise EvidenceValidationError("ABSOLUTE_SOURCE_PATH_NOT_ALLOWED")

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool, "version": self.version, "file": self.file,
            "start_line": self.start_line, "end_line": self.end_line,
        }


@dataclass(frozen=True)
class Evidence:
    id: str
    project_id: str
    repository_id: str
    revision: str
    run_id: str
    type: str
    subject: str
    relation: str | None
    object: str | None
    source: EvidenceSource
    value: Any
    observed_at: str | None
    status: str = "VALID"

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        repository_id: str,
        revision: str,
        run_id: str,
        type: str,
        subject: str,
        source: EvidenceSource,
        value: Any,
        relation: str | None = None,
        object: str | None = None,
        observed_at: str | None = None,
        status: str = "VALID",
    ) -> "Evidence":
        frozen = _freeze(value)
        record = cls(
            id="", project_id=project_id, repository_id=repository_id, revision=revision,
            run_id=run_id, type=type, subject=subject, relation=relation, object=object,
            source=source, value=frozen, observed_at=observed_at, status=status,
        )
        record.require_valid()
        return cls(**{**record.__dict__, "id": record.compute_id()})

    def identity_payload(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION, "project_id": self.project_id,
            "repository_id": self.repository_id, "revision": self.revision,
            "run_id": self.run_id, "type": self.type, "subject": self.subject,
            "relation": self.relation, "object": self.object,
            "source": self.source.to_dict(), "value": _thaw(self.value),
        }

    def compute_id(self) -> str:
        digest = hashlib.sha256(_canonical(self.identity_payload()).encode("utf-8")).hexdigest()
        return f"EVID-{digest[:20]}"

    def validate(self, *, repository_id: str | None = None, revision: str | None = None,
                 run_id: str | None = None) -> list[dict[str, str]]:
        errors: list[dict[str, str]] = []
        def add(code: str) -> None: errors.append({"code": code})
        if not all((self.project_id, self.repository_id, self.revision, self.run_id, self.type, self.subject)):
            add("MISSING_REQUIRED_FIELD")
        if self.type not in EVIDENCE_TYPES:
            add("INVALID_EVIDENCE_TYPE")
        if self.status not in STATUSES:
            add("INVALID_STATUS")
        if self.relation is None and self.object is not None:
            add("OBJECT_WITHOUT_RELATION")
        if self.source.file is not None and self.source.file.startswith(("/", "\\")):
            add("ABSOLUTE_SOURCE_PATH_NOT_ALLOWED")
        try:
            _canonical(self.value)
        except EvidenceValidationError:
            add("INVALID_VALUE")
        if self.status != "REDACTED" and self._contains_secret_like_data():
            add("SECRET_LIKE_VALUE")
        if repository_id is not None and self.repository_id != repository_id:
            add("REPOSITORY_CONTEXT_MISMATCH")
        if revision is not None and self.revision != revision:
            add("REVISION_CONTEXT_MISMATCH")
        if run_id is not None and self.run_id != run_id:
            add("RUN_CONTEXT_MISMATCH")
        if self.id and self.id != self.compute_id():
            add("EVIDENCE_ID_MISMATCH")
        return errors

    def require_valid(self, **context: str) -> None:
        errors = self.validate(**context)
        if errors:
            raise EvidenceValidationError(json.dumps(errors, sort_keys=True))

    def _contains_secret_like_data(self) -> bool:
        def scan(value: Any, key: str | None = None) -> bool:
            if isinstance(value, Mapping):
                for k, v in value.items():
                    if _SECRET_KEYS.search(str(k)) and v not in (None, "", "[REDACTED]"):
                        return True
                    if scan(v, str(k)):
                        return True
                return False
            if isinstance(value, (tuple, list)):
                return any(scan(v, key) for v in value)
            return isinstance(value, str) and bool(_SECRET_VALUE.search(value))
        return scan(self.value)

    def to_dict(self) -> dict[str, Any]:
        self.require_valid()
        return {
            "schema_version": SCHEMA_VERSION, "id": self.id,
            "project_id": self.project_id, "repository_id": self.repository_id,
            "revision": self.revision, "run_id": self.run_id, "type": self.type,
            "subject": self.subject, "relation": self.relation, "object": self.object,
            "source": self.source.to_dict(), "value": _thaw(self.value),
            "observed_at": self.observed_at, "status": self.status,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"

    @classmethod
    def from_dict(cls, raw: dict[str, Any], **context: str) -> "Evidence":
        if raw.get("schema_version") != SCHEMA_VERSION:
            raise EvidenceValidationError("UNSUPPORTED_EVIDENCE_SCHEMA")
        source_raw = raw["source"]
        source = EvidenceSource(**source_raw)
        evidence = cls(
            id=raw["id"], project_id=raw["project_id"], repository_id=raw["repository_id"],
            revision=raw["revision"], run_id=raw["run_id"], type=raw["type"],
            subject=raw["subject"], relation=raw.get("relation"), object=raw.get("object"),
            source=source, value=_freeze(raw.get("value")), observed_at=raw.get("observed_at"),
            status=raw["status"],
        )
        evidence.require_valid(**context)
        return evidence
