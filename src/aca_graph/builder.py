"""Build the initial CodeGraph from ACA-001 ingestion output."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .model import Edge, Graph, Node


def _evidence(record: Any) -> tuple[str, ...]:
    return (record.evidence_id,) if getattr(record, "evidence_id", None) else ()


def build_from_ingestion(result: Any) -> Graph:
    repository = result.repository
    repo_id = repository["id"]
    revision = repository.get("revision")
    run_id = next(
        (e.run_id for e in result.evidence if getattr(e, "run_id", None)),
        None,
    ) or f"RUN-{repo_id}"

    graph = Graph(repository=dict(repository), revision=revision, analysis_run_id=run_id)
    graph.add_evidence(result.evidence)

    repo_node = Node.create(
        "Repository",
        repo_id,
        f"repository:{repo_id}",
        properties={"source_path": repository.get("source_path"), "vcs": repository.get("vcs")},
        analysis_run_id=run_id,
        revision=revision,
    )
    graph.add_node(repo_node)

    if revision:
        revision_node = Node.create(
            "Revision",
            repo_id,
            f"revision:{revision}",
            properties={"revision": revision},
            analysis_run_id=run_id,
            revision=revision,
        )
        graph.add_node(revision_node)
        graph.add_edge(Edge.create(
            repo_node, "CONTAINS", revision_node,
            analysis_run_id=run_id, revision=revision,
        ))

    module_nodes: dict[str, Node] = {}
    for module in result.modules:
        node = Node.create(
            "Module",
            repo_id,
            f"module:{module.root}",
            properties={
                "root": module.root,
                "module_type": module.module_type,
                "descriptors": list(module.descriptors),
                "source_roots": list(module.source_roots),
                "resource_roots": list(module.resource_roots),
                "parent": module.parent,
            },
            evidence_refs=_evidence(module),
            analysis_run_id=run_id,
            revision=revision,
        )
        graph.add_node(node)
        module_nodes[module.root] = node

    for module in result.modules:
        node = module_nodes[module.root]
        parent = module.parent
        if parent and parent in module_nodes:
            graph.add_edge(Edge.create(
                module_nodes[parent], "CONTAINS", node,
                evidence_refs=_evidence(module), analysis_run_id=run_id, revision=revision,
            ))
        else:
            graph.add_edge(Edge.create(
                repo_node, "CONTAINS", node,
                evidence_refs=_evidence(module), analysis_run_id=run_id, revision=revision,
            ))

    file_nodes: dict[str, Node] = {}
    for record in result.files:
        node = Node.create(
            "File",
            repo_id,
            f"file:{record.path}",
            properties={
                "path": record.path,
                "kind": record.kind,
                "size": record.size,
                "sha256": record.sha256,
                "line_count": record.line_count,
                "generated": record.generated,
                "vendor": record.vendor,
            },
            evidence_refs=_evidence(record),
            analysis_run_id=run_id,
            revision=revision,
        )
        graph.add_node(node)
        file_nodes[record.path] = node

        module_root = next(
            (m.root for m in result.modules if m.root != "." and (record.path == m.root or record.path.startswith(m.root + "/"))),
            None,
        )
        parent_node = module_nodes.get(module_root) if module_root else repo_node
        graph.add_edge(Edge.create(
            parent_node, "CONTAINS", node,
            evidence_refs=_evidence(record), analysis_run_id=run_id, revision=revision,
        ))

        if record.kind == "java":
            package = _java_package(record.path, getattr(result, "_file_contents", {}).get(record.path))
            if package:
                pkg_key = f"package:{package}"
                pkg_node = Node.create(
                    "Package", repo_id, pkg_key,
                    properties={"name": package},
                    evidence_refs=_evidence(record),
                    analysis_run_id=run_id, revision=revision,
                )
                graph.add_node(pkg_node)
                graph.add_edge(Edge.create(
                    pkg_node, "CONTAINS", node,
                    evidence_refs=_evidence(record), analysis_run_id=run_id, revision=revision,
                ))

    return graph


def _java_package(path: str, content: str | None) -> str | None:
    if not content:
        return None
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("package ") and stripped.endswith(";"):
            return stripped[len("package "):-1].strip()
    return None
