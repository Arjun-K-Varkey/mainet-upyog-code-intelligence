"""Read-only, deterministic repository inventory and evidence generation."""

from __future__ import annotations

import fnmatch
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
    include_paths: tuple[str, ...] = ()
    exclude_paths: tuple[str, ...] = ()
    max_file_size: int = 10 * 1024 * 1024
    follow_symlinks: bool = False
    generated_dirs: frozenset[str] = frozenset({"generated", "gen"})
    vendor_dirs: frozenset[str] = frozenset({"vendor", "third_party", "third-party", "node_modules"})
    detector_set: tuple[str, ...] = ("default",)
    repository_id: str | None = None
    version_metadata: str | None = None


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
    source_roots: tuple[str, ...]
    resource_roots: tuple[str, ...]
    parent: str | None
    evidence_id: str


@dataclass(frozen=True)
class EvidenceRecord:
    id: str
    type: str
    subject: str
    source_file: str
    value: dict
    status: str = "valid"
    repository_id: str | None = None
    revision: str | None = None
    run_id: str | None = None
    tool_version: str | None = None


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
    ".java": "java", ".jsp": "jsp", ".jspx": "jsp", ".tag": "jsp", ".tagx": "jsp",
    ".sql": "sql", ".xml": "xml", ".wsdl": "xml", ".xsd": "xml",
    ".js": "javascript", ".ts": "typescript", ".css": "css", ".scss": "scss",
    ".yaml": "yaml", ".yml": "yaml", ".json": "json", ".properties": "properties",
    ".md": "markdown", ".html": "html", ".htm": "html", ".xhtml": "html",
    ".gradle": "gradle", ".kts": "gradle", ".sh": "shell", ".bat": "shell",
    ".conf": "config", ".ini": "config",
}
SPECIAL_FILES = {"pom.xml": "maven", "build.gradle": "gradle", "settings.gradle": "gradle", "settings.gradle.kts": "gradle", "gradle.properties": "gradle"}


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}-{hashlib.sha256(value.encode('utf-8')).hexdigest()[:20]}"


def _classification(path: Path) -> str:
    return SPECIAL_FILES.get(path.name.lower(), EXTENSIONS.get(path.suffix.lower(), "other"))


def _path_flag(path: str, configured_dirs: frozenset[str], legacy_defaults: tuple[str, ...] = ()) -> bool:
    parts = {part.lower() for part in path.lower().split("/")}
    return bool(parts.intersection({d.lower() for d in configured_dirs}.union(legacy_defaults)))


def _is_generated(path: str, config: ScanConfig) -> bool:
    return _path_flag(path, config.generated_dirs, ("target", "build"))


def _is_vendor(path: str, config: ScanConfig) -> bool:
    return _path_flag(path, config.vendor_dirs)


def _matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(path + "/", pattern.rstrip("/") + "/") for pattern in patterns)


def _iter_files(root: Path, config: ScanConfig) -> Iterable[Path]:
    for current, dirs, files in os.walk(root, followlinks=config.follow_symlinks):
        rel_current = Path(current).relative_to(root).as_posix()
        if rel_current == ".":
            rel_current = ""
        dirs[:] = sorted(
            d for d in dirs
            if d not in config.excluded_dirs
            and not _matches_any((f"{rel_current}/{d}" if rel_current else d), config.exclude_paths)
        )
        for name in sorted(files):
            path = Path(current) / name
            rel = path.relative_to(root).as_posix()
            if not config.follow_symlinks and path.is_symlink():
                continue
            if config.include_paths and not _matches_any(rel, config.include_paths):
                continue
            if _matches_any(rel, config.exclude_paths):
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


def _inventory_fingerprint(files: list[FileRecord]) -> str:
    canonical = "\n".join(
        f"{record.path}\0{record.kind}\0{record.size}\0{record.sha256}\0"
        f"{record.line_count}\0{record.generated}\0{record.vendor}"
        for record in sorted(files, key=lambda item: item.path)
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _detect_roots(module_root: Path, result: ScanResult) -> tuple[tuple[str, ...], tuple[str, ...]]:
    prefixes = set()
    resources = set()
    root = module_root.as_posix()
    for record in result.files:
        if not record.path.startswith(root + "/") if root != "." else False:
            continue
        rel = record.path[len(root) + 1:] if root != "." else record.path
        parts = rel.split("/")
        if len(parts) >= 4 and parts[0:2] == ["src", "main"]:
            candidate = "/".join(parts[:3])
            if parts[2] == "resources":
                resources.add((f"{root}/{candidate}") if root != "." else candidate)
            else:
                prefixes.add((f"{root}/{candidate}") if root != "." else candidate)
    return tuple(sorted(prefixes)), tuple(sorted(resources))


class RepositoryScanner:
    """Scan repository contents without executing repository code."""

    TOOL_VERSION = "aca-ingestion-0.2"

    def __init__(self, config: ScanConfig | None = None):
        self.config = config or ScanConfig()

    def scan(self, repository: str | Path) -> ScanResult:
        root = Path(repository).resolve(strict=True)
        if not root.is_dir():
            raise ValueError(f"Repository path is not a directory: {root}")

        revision = _git_revision(root)
        config_repr = json.dumps({
            "excluded_dirs": sorted(self.config.excluded_dirs),
            "include_paths": list(self.config.include_paths),
            "exclude_paths": list(self.config.exclude_paths),
            "max_file_size": self.config.max_file_size,
            "follow_symlinks": self.config.follow_symlinks,
            "generated_dirs": sorted(self.config.generated_dirs),
            "vendor_dirs": sorted(self.config.vendor_dirs),
            "detector_set": list(self.config.detector_set),
            "repository_id": self.config.repository_id,
            "version_metadata": self.config.version_metadata,
        }, sort_keys=True)
        config_hash = hashlib.sha256(config_repr.encode()).hexdigest()

        files: list[FileRecord] = []
        errors: list[dict] = []
        for path in _iter_files(root, self.config):
            rel = path.relative_to(root).as_posix()
            try:
                size = path.stat().st_size
                if size > self.config.max_file_size:
                    errors.append({"path": rel, "code": "FILE_TOO_LARGE", "size": size})
                    continue
                data = path.read_bytes()
                digest = hashlib.sha256(data).hexdigest()
                try:
                    text = data.decode("utf-8")
                    lines = len(text.splitlines())
                except UnicodeDecodeError:
                    lines = None
                evidence_id = _stable_id("EVID", f"file:{rel}:{digest}")
                files.append(FileRecord(rel, _classification(path), size, digest, lines,
                                        _is_generated(rel, self.config), _is_vendor(rel, self.config), evidence_id))
            except (OSError, PermissionError) as exc:
                errors.append({"path": rel, "code": "UNREADABLE", "message": str(exc)})

        files.sort(key=lambda r: r.path)
        inventory_fingerprint = _inventory_fingerprint(files)
        repository_id = self.config.repository_id or _stable_id("REPO", f"revision:{revision or 'content'}:{inventory_fingerprint}")
        run_id = _stable_id("RUN", f"{repository_id}:{revision or inventory_fingerprint}:{config_hash}:{self.TOOL_VERSION}")
        result = ScanResult(repository={
            "id": repository_id,
            "revision": revision,
            "tool_version": self.TOOL_VERSION,
            "configuration_fingerprint": config_hash,
            "version_metadata": self.config.version_metadata,
        }, files=files, errors=errors)

        result.evidence.extend(
            EvidenceRecord(
                record.evidence_id, "source", record.path, record.path,
                {"classification": record.kind, "size": record.size, "sha256": record.sha256,
                 "generated": record.generated, "vendor": record.vendor},
                repository_id=repository_id, revision=revision, run_id=run_id,
                tool_version=self.TOOL_VERSION,
            )
            for record in result.files
        )
        result.modules = self._detect_modules(root, result, repository_id, revision, run_id)
        result.modules.sort(key=lambda r: r.root)
        if result.errors:
            result.status = "partial_success" if result.files else "failure"
        return result

    def _detect_modules(
        self, root: Path, result: ScanResult, repository_id: str, revision: str | None, run_id: str
    ) -> list[ModuleRecord]:
        descriptors: dict[str, list[str]] = {}
        for record in result.files:
            if record.kind in {"maven", "gradle"}:
                parent = str(Path(record.path).parent).replace("\\", "/")
                descriptors.setdefault(parent, []).append(record.path)
        module_roots = sorted(descriptors)
        modules: list[ModuleRecord] = []
        for module_root in module_roots:
            files = sorted(descriptors[module_root])
            module_type = "maven" if any(_classification(Path(f)) == "maven" for f in files) else "gradle"
            parent = None
            if module_root:
                candidates = [candidate for candidate in module_roots if candidate and candidate != module_root and module_root.startswith(candidate + "/")]
                parent = max(candidates, key=len) if candidates else None
            source_roots, resource_roots = _detect_roots(Path(module_root), result)
            value = f"module:{module_root}:{module_type}:{','.join(files)}:{','.join(source_roots)}:{','.join(resource_roots)}:{parent or ''}"
            evidence_id = _stable_id("EVID", value)
            module_id = _stable_id("MOD", value)
            modules.append(ModuleRecord(module_id, module_root or ".", module_type, tuple(files), source_roots, resource_roots, parent, evidence_id))
            result.evidence.append(EvidenceRecord(
                evidence_id, "config", module_id, module_root or ".",
                {"module_type": module_type, "descriptors": files, "source_roots": list(source_roots),
                 "resource_roots": list(resource_roots), "parent": parent},
                repository_id=repository_id, revision=revision, run_id=run_id,
                tool_version=self.TOOL_VERSION,
            ))
        return modules
