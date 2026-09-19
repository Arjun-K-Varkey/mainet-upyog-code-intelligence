"""Read-only, deterministic repository inventory and evidence generation."""
from __future__ import annotations

import fnmatch, hashlib, json, os, subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
    path: str; kind: str; size: int; sha256: str; line_count: int | None
    generated: bool; vendor: bool; evidence_id: str; package_name: str | None = None

@dataclass(frozen=True)
class ModuleRecord:
    id: str; root: str; module_type: str; descriptors: tuple[str, ...]
    source_roots: tuple[str, ...]; resource_roots: tuple[str, ...]
    parent: str | None; evidence_id: str

@dataclass(frozen=True)
class EvidenceRecord:
    id: str; type: str; subject: str; source_file: str; value: dict
    status: str = "valid"; repository_id: str | None = None
    revision: str | None = None; run_id: str | None = None; tool_version: str | None = None

@dataclass
class ScanResult:
    repository: dict; files: list[FileRecord] = field(default_factory=list)
    modules: list[ModuleRecord] = field(default_factory=list)
    evidence: list[EvidenceRecord] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list); status: str = "success"
    def to_dict(self):
        return {"repository": self.repository, "files": [r.__dict__ for r in self.files],
                "modules": [r.__dict__ for r in self.modules], "evidence": [r.__dict__ for r in self.evidence],
                "errors": self.errors, "status": self.status}
    def to_json(self): return json.dumps(self.to_dict(), indent=2, sort_keys=True)

EXTENSIONS = {".java":"java",".jsp":"jsp",".jspx":"jsp",".tag":"jsp",".tagx":"jsp",
 ".sql":"sql",".xml":"xml",".wsdl":"xml",".xsd":"xml",".js":"javascript",".ts":"typescript",
 ".css":"css",".scss":"scss",".yaml":"yaml",".yml":"yaml",".json":"json",".properties":"properties",
 ".md":"markdown",".html":"html",".htm":"html",".xhtml":"html",".gradle":"gradle",".kts":"gradle",
 ".sh":"shell",".bat":"shell",".conf":"config",".ini":"config"}
SPECIAL_FILES = {"pom.xml":"maven","build.gradle":"gradle","settings.gradle":"gradle","settings.gradle.kts":"gradle","gradle.properties":"gradle"}

def _stable_id(prefix, value): return f"{prefix}-{hashlib.sha256(value.encode()).hexdigest()[:20]}"
def _classification(path): return SPECIAL_FILES.get(path.name.lower(), EXTENSIONS.get(path.suffix.lower(), "other"))
def _path_flag(path, dirs, defaults=()): return bool({p.lower() for p in path.split("/")} & ({d.lower() for d in dirs}|set(defaults)))
def _is_generated(path, c): return _path_flag(path, c.generated_dirs, ("target","build"))
def _is_vendor(path, c): return _path_flag(path, c.vendor_dirs)
def _matches(path, patterns): return any(fnmatch.fnmatch(path,p) or fnmatch.fnmatch(path+"/",p.rstrip("/")+"/") for p in patterns)

def _iter_files(root, c) -> Iterable[Path]:
    for current, dirs, files in os.walk(root, followlinks=c.follow_symlinks):
        rel_current=Path(current).relative_to(root).as_posix(); rel_current="" if rel_current=="." else rel_current
        dirs[:] = sorted(d for d in dirs if d not in c.excluded_dirs and not _matches(f"{rel_current}/{d}" if rel_current else d,c.exclude_paths))
        for name in sorted(files):
            path=Path(current)/name; rel=path.relative_to(root).as_posix()
            if (path.is_symlink() and not c.follow_symlinks) or (c.include_paths and not _matches(rel,c.include_paths)) or _matches(rel,c.exclude_paths): continue
            yield path

def _git_revision(root):
    try:
        r=subprocess.run(["git","rev-parse","HEAD"],cwd=root,capture_output=True,text=True,timeout=2,check=False)
        return r.stdout.strip() if r.returncode==0 else None
    except (OSError, subprocess.SubprocessError): return None

def _detect_vcs(root):
    if (root/".git").exists(): return "git"
    if (root/".hg").exists(): return "mercurial"
    if (root/".svn").exists(): return "subversion"
    return "none"

def _fingerprint(files):
    canonical="\n".join(f"{r.path}\0{r.kind}\0{r.size}\0{r.sha256}\0{r.line_count}\0{r.generated}\0{r.vendor}\0{r.package_name or ''}" for r in sorted(files,key=lambda x:x.path))
    return hashlib.sha256(canonical.encode()).hexdigest()

def _detect_roots(module_root, result):
    source, resource=set(),set(); root=module_root.as_posix()
    for r in result.files:
        if root!="." and not r.path.startswith(root+"/"): continue
        rel=r.path[len(root)+1:] if root!="." else r.path; p=rel.split("/")
        if len(p)>=4 and p[:2]==["src","main"]:
            candidate="/".join(p[:3]); full=f"{root}/{candidate}" if root!="." else candidate
            (resource if p[2]=="resources" else source).add(full)
    return tuple(sorted(source)),tuple(sorted(resource))

def _structural_roots(result):
    roots=set()
    for r in result.files:
        p=r.path.split("/")
        for marker in (("src","main"),("src","test")):
            for i in range(len(p)-1):
                if p[i:i+2]==list(marker): roots.add("/".join(p[:i]) or ".")
    return roots

def _java_package(data: bytes) -> str | None:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    for line in text.splitlines():
        stripped=line.strip()
        if stripped.startswith("package ") and stripped.endswith(";"):
            return stripped[len("package "):-1].strip()
    return None

class RepositoryScanner:
    TOOL_VERSION="aca-ingestion-0.4"
    def __init__(self, config=None): self.config=config or ScanConfig()
    def scan(self, repository):
        root=Path(repository).resolve(strict=True)
        if not root.is_dir(): raise ValueError(f"Repository path is not a directory: {root}")
        revision=_git_revision(root); vcs=_detect_vcs(root); timestamp=datetime.now(timezone.utc).isoformat()
        config_repr=json.dumps({"excluded_dirs":sorted(self.config.excluded_dirs),"include_paths":list(self.config.include_paths),"exclude_paths":list(self.config.exclude_paths),"max_file_size":self.config.max_file_size,"follow_symlinks":self.config.follow_symlinks,"generated_dirs":sorted(self.config.generated_dirs),"vendor_dirs":sorted(self.config.vendor_dirs),"detector_set":list(self.config.detector_set),"repository_id":self.config.repository_id,"version_metadata":self.config.version_metadata},sort_keys=True)
        config_hash=hashlib.sha256(config_repr.encode()).hexdigest(); files=[]; errors=[]
        for path in _iter_files(root,self.config):
            rel=path.relative_to(root).as_posix()
            try:
                size=path.stat().st_size
                if size>self.config.max_file_size: errors.append({"path":rel,"code":"FILE_TOO_LARGE","size":size}); continue
                data=path.read_bytes(); digest=hashlib.sha256(data).hexdigest()
                try: lines=len(data.decode("utf-8").splitlines())
                except UnicodeDecodeError: lines=None; errors.append({"path":rel,"code":"NON_UTF8","message":"UTF-8 line count not safely determinable"})
                kind=_classification(path)
                package_name=_java_package(data) if kind=="java" else None
                evidence_id=_stable_id("EVID",f"file:{rel}:{digest}")
                files.append(FileRecord(rel,kind,size,digest,lines,_is_generated(rel,self.config),_is_vendor(rel,self.config),evidence_id,package_name))
            except (OSError,PermissionError) as exc: errors.append({"path":rel,"code":"UNREADABLE","message":str(exc)})
        files.sort(key=lambda r:r.path); inventory=_fingerprint(files)
        repo_id=self.config.repository_id or _stable_id("REPO",f"revision:{revision or 'content'}:{inventory}")
        workspace_id=_stable_id("WS",f"{repo_id}:{root.name}"); run_id=_stable_id("RUN",f"{repo_id}:{revision or inventory}:{config_hash}:{self.TOOL_VERSION}")
        result=ScanResult({"id":repo_id,"workspace_id":workspace_id,"source_path":root.as_posix(),"vcs":vcs,"revision":revision,"scan_timestamp":timestamp,"tool_version":self.TOOL_VERSION,"configuration_fingerprint":config_hash,"version_metadata":self.config.version_metadata,"analysis_run_id":run_id},files=files,errors=errors)
        if revision:
            revision_evidence_id = _stable_id("EVID", f"revision:{repo_id}:{revision}")
            result.evidence.append(EvidenceRecord(
                revision_evidence_id, "revision", f"revision:{revision}", ".git/HEAD",
                {"revision": revision, "vcs": vcs},
                repository_id=repo_id, revision=revision, run_id=run_id, tool_version=self.TOOL_VERSION,
            ))
        for r in result.files:
            result.evidence.append(EvidenceRecord(r.evidence_id,"source",r.path,r.path,{"classification":r.kind,"size":r.size,"sha256":r.sha256,"generated":r.generated,"vendor":r.vendor,"package_name":r.package_name},repository_id=repo_id,revision=revision,run_id=run_id,tool_version=self.TOOL_VERSION))
        for e in result.errors:
            eid=_stable_id("EVID",f"error:{e['code']}:{e['path']}:{e.get('message','')}:{e.get('size','')}")
            result.evidence.append(EvidenceRecord(eid,"error",e["path"],e["path"],dict(e),status="warning",repository_id=repo_id,revision=revision,run_id=run_id,tool_version=self.TOOL_VERSION))
        result.modules=self._detect_modules(result,repo_id,revision,run_id); result.modules.sort(key=lambda r:r.root)
        if result.errors: result.status="partial_success" if result.files else "failure"
        return result
    def _detect_modules(self,result,repo_id,revision,run_id):
        descriptors={}
        for r in result.files:
            if r.kind in {"maven", "gradle"}: descriptors.setdefault(str(Path(r.path).parent).replace("\\", "/"), []).append(r.path)
        roots=set(descriptors)|_structural_roots(result); modules=[]
        for root in sorted(roots):
            ds=sorted(descriptors.get(root,[])); typ="maven" if any(_classification(Path(x))=="maven" for x in ds) else ("gradle" if ds else "structural")
            candidates=[x for x in roots if x not in {root,"."} and root.startswith(x+"/")]; parent=max(candidates,key=len) if candidates else ("." if root!="." and "." in roots else None)
            src,res=_detect_roots(Path(root),result); value=f"module:{root}:{typ}:{','.join(ds)}:{','.join(src)}:{','.join(res)}:{parent or ''}"; eid=_stable_id("EVID",value); mid=_stable_id("MOD",value)
            modules.append(ModuleRecord(mid,root,typ,tuple(ds),src,res,parent,eid)); result.evidence.append(EvidenceRecord(eid,"config",mid,root,{"module_type":typ,"descriptors":ds,"source_roots":list(src),"resource_roots":list(res),"parent":parent},repository_id=repo_id,revision=revision,run_id=run_id,tool_version=self.TOOL_VERSION))
        return modules
