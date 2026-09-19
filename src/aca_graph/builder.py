"""Build the initial CodeGraph from ACA-001 ingestion output."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .model import Edge, Graph, Node


def _evidence(record: Any) -> tuple[str, ...]:
    return (record.evidence_id,) if getattr(record, "evidence_id", None) else ()


def _java_package(source_path: Path, relative_path: str) -> str | None:
    try:
        content = (source_path / relative_path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("package ") and stripped.endswith(";"):
            return stripped[len("package "):-1].strip()
    return None


def build_from_ingestion(result: Any) -> Graph:
    repository = result.repository
    repo_id = repository["id"]
    revision = repository.get("revision")
    run_id = next(
        (e.run_id for e in result.evidence if getattr(e, "run_id", None)),
        repository.get("analysis_run_id"),
    )
    if not run_id:
        raise ValueError("SPEC-001 result is missing analysis run identity")

    source_path = Path(repository["source_path"])
    graph = Graph(repository=dict(repository), revision=revision, analysis_run_id=run_id)
    graph.add_evidence(result.evidence)

    repo_node = Node.create(
        "Repository", repo_id, f"repository:{repo_id}",
        properties={"vcs": repository.get("vcs")},
        analysis_run_id=run_id, revision=revision,
    )
    graph.add_node(repo_node)

    if revision:
        revision_node = Node.create(
            "Revision", repo_id, f"revision:{revision}",
            properties={"revision": revision}, analysis_run_id=run_id, revision=revision,
        )
        graph.add_node(revision_node)
        graph.add_edge(Edge.create(
            repo_node, "CONTAINS", revision_node,
            analysis_run_id=run_id, revision=revision,
        ))

    module_nodes: dict[str, Node] = {}
    for module in result.modules:
        node = Node.create(
            "Module", repo_id, f"module:{module.root}",
            properties={
                "root": module.root, "module_type": module.module_type,
                "descriptors": list(module.descriptors),
                "source_roots": list(module.source_roots),
                "resource_roots": list(module.resource_roots),
                "parent": module.parent,
            },
            evidence_refs=_evidence(module), analysis_run_id=run_id, revision=revision,
        )
        graph.add_node(node)
        module_nodes[module.root] = node

    for module in result.modules:
        node = module_nodes[module.root]
        parent = module.parent
        parent_node = module_nodes.get(parent) if parent else None
        graph.add_edge(Edge.create(
            parent_node or repo_node, "CONTAINS", node,
            evidence_refs=_evidence(module), analysis_run_id=run_id, revision=revision,
        ))

    for record in result.files:
        node = Node.create(
            "File", repo_id, f"file:{record.path}",
            properties={
                "path": record.path, "kind": record.kind, "size": record.size,
                "sha256": record.sha256, "line_count": record.line_count,
                "generated": record.generated, "vendor": record.vendor,
            },
            evidence_refs=_evidence(record), analysis_run_id=run_id, revision=revision,
        )
        graph.add_node(node)

        module_root = next(
            (m.root for m in result.modules
             if m.root != "." and (record.path == m.root or record.path.startswith(m.root + "/"))),
            None,
        )
        parent_node = module_nodes.get(module_root) if module_root else repo_node
        graph.add_edge(Edge.create(
            parent_node, "CONTAINS", node,
            evidence_refs=_evidence(record), analysis_run_id=run_id, revision=revision,
        ))

        if record.kind == "java" and record.package_name:
            package = record.package_name
            pkg_node = Node.create(
                "Package", repo_id, f"package:{package}",
                properties={"name": package},
                evidence_refs=(),
                analysis_run_id=run_id, revision=revision,
            )
            graph.add_node(pkg_node)
            graph.add_edge(Edge.create(
                pkg_node, "CONTAINS", node,
                evidence_refs=_evidence(record), analysis_run_id=run_id, revision=revision,
            ))


    return graph
