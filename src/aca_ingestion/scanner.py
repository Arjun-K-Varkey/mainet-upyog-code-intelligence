"""Read-only, deterministic repository inventory and evidence generation."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ScanConfig:
    excluded_dirs: frozenset[str] = frozenset({".git", ".idea", ".vscode", "node_modules", "target", "build", "dist"})
    max_file_size: int = 10 * 1024 * 1024
    follow_symlinks: bool = False


@dataclass(frozen=True)
class FileRecord:
    path: str
    kind: str
    size: int
    sha256: str
    line_count: int | None
    generated: bool
    vendor: bool
    evidence_id: str


@dataclass(frozen=True)
class ModuleRecord:
    id: str
    root: str
    module_type: str
    descriptors: tuple[str, ...]
    evidence_id: str


@dataclass(frozen=True)
class EvidenceRecord:
    id: str
    type: str
    subject: str
    source_file: str
    value: dict
    status: str = "valid"


@dataclass
class ScanResult:
    repository: dict
    files: list[FileRecord] = field(default_factory=list)
    modules: list[ModuleRecord] = field(default_factory=list)
    evidence: list[EvidenceRecord] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    status: str = "success"

    def to_dict(self) -> dict:
        return {
            "repository": self.repository,
            "files": [r.__dict__ for r in self.files],
            "modules": [r.__dict__ for r in self.modules],
            "evidence": [r.__dict__ for r in self.evidence],
            "errors": self.errors,
            "status": self.status,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


EXTENSIONS = {
    ".java": "java", ".jsp": "jsp", ".jspx": "jsp", ".tag": "jsp",
    ".sql": "sql", ".xml": "xml", ".js": "javascript", ".ts": "typescript",
    ".css": "css", ".scss": "scss", ".yaml": "yaml", ".yml": "yaml",
    ".json": "json", ".properties": "properties", ".md": "markdown",
    ".html": "html", ".htm": "html", ".xhtml": "html",
    ".gradle": "gradle", ".kts": "gradle",
}
SPECIAL_FILES = {"pom.xml": "maven", "build.gradle": "gradle", "settings.gradle": "gradle", "settings.gradle.kts": "gradle", "gradle.properties": "gradle"}


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}-{hashlib.sha256(value.encode('utf-8')).hexdigest()[:20]}"


def _classification(path: Path) -> str:
    return SPECIAL_FILES.get(path.name.lower(), EXTENSIONS.get(path.suffix.lower(), "other"))


def _is_generated(path: str) -> bool:
    lowered = path.lower()
    return any(token in lowered.split("/") for token in ("generated", "gen", "target", "build"))


def _is_vendor(path: str) -> bool:
    lowered = path.lower()
    return any(token in lowered.split("/") for token in ("vendor", "third_party", "third-party", "node_modules"))


def _iter_files(root: Path, config: ScanConfig) -> Iterable[Path]:
    for current, dirs, files in os.walk(root, followlinks=config.follow_symlinks):
        dirs[:] = sorted(d for d in dirs if d not in config.excluded_dirs)
        for name in sorted(files):
            path = Path(current) / name
            if not config.follow_symlinks and path.is_symlink():
                continue
            yield path


def _git_revision(root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
            text=True, timeout=2, check=False
        )
        if completed.returncode == 0:
            return completed.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


class RepositoryScanner:
    """Scan repository contents without executing repository code."""

    TOOL_VERSION = "aca-ingestion-0.1"

    def __init__(self, config: ScanConfig | None = None):
        self.config = config or ScanConfig()

    def scan(self, repository: str | Path) -> ScanResult:
        root = Path(repository).resolve(strict=True)
        if not root.is_dir():
            raise ValueError(f"Repository path is not a directory: {root}")

        revision = _git_revision(root)
        config_repr = json.dumps({
            "excluded_dirs": sorted(self.config.excluded_dirs),
            "max_file_size": self.config.max_file_size,
            "follow_symlinks": self.config.follow_symlinks,
        }, sort_keys=True)
        config_hash = hashlib.sha256(config_repr.encode()).hexdigest()
        result = ScanResult(repository={
            "id": _stable_id("REPO", str(root)),
            "workspace": str(root),
            "revision": revision,
            "tool_version": self.TOOL_VERSION,
            "configuration_fingerprint": config_hash,
        })

        for path in _iter_files(root, self.config):
            rel = path.relative_to(root).as_posix()
            try:
                size = path.stat().st_size
                if size > self.config.max_file_size:
                    result.errors.append({"path": rel, "code": "FILE_TOO_LARGE", "size": size})
                    continue
                data = path.read_bytes()
                digest = hashlib.sha256(data).hexdigest()
                try:
                    text = data.decode("utf-8")
                    lines = len(text.splitlines())
                except UnicodeDecodeError:
                    lines = None
                evidence_id = _stable_id("EVID", f"file:{rel}:{digest}")
                record = FileRecord(rel, _classification(path), size, digest, lines,
                                    _is_generated(rel), _is_vendor(rel), evidence_id)
                result.files.append(record)
                result.evidence.append(EvidenceRecord(
                    evidence_id, "source", record.path,
                    record.path,
                    {"classification": record.kind, "size": size, "sha256": digest,
                     "generated": record.generated, "vendor": record.vendor}
                ))
            except (OSError, PermissionError) as exc:
                result.errors.append({"path": rel, "code": "UNREADABLE", "message": str(exc)})

        result.files.sort(key=lambda r: r.path)
        result.modules = self._detect_modules(root, result)
        result.modules.sort(key=lambda r: r.root)
        if result.errors:
            result.status = "partial_success" if result.files else "failure"
        return result

    def _detect_modules(self, root: Path, result: ScanResult) -> list[ModuleRecord]:
        descriptors: dict[str, list[str]] = {}
        for record in result.files:
            if record.kind in {"maven", "gradle"}:
                parent = str(Path(record.path).parent).replace("\\", "/")
                descriptors.setdefault(parent, []).append(record.path)
        modules: list[ModuleRecord] = []
        for module_root, files in sorted(descriptors.items()):
            module_type = "maven" if any(_classification(Path(f)) == "maven" for f in files) else "gradle"
            value = f"module:{module_root}:{module_type}:{','.join(sorted(files))}"
            evidence_id = _stable_id("EVID", value)
            module_id = _stable_id("MOD", value)
            modules.append(ModuleRecord(module_id, module_root or ".", module_type, tuple(sorted(files)), evidence_id))
            result.evidence.append(EvidenceRecord(
                evidence_id, "config", module_id, module_root or ".",
                {"module_type": module_type, "descriptors": sorted(files)}
            ))
        return modules
