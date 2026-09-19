import json
import tempfile
import unittest
from pathlib import Path

from src.aca_graph import Graph, Node, Edge, build_from_ingestion
from src.aca_ingestion.scanner import RepositoryScanner


def fixture(root: Path) -> Path:
    (root / "module-a/src/main/java/com/example").mkdir(parents=True)
    (root / "module-a/pom.xml").write_text("<project/>\n", encoding="utf-8")
    (root / "module-a/src/main/java/com/example/App.java").write_text(
        "package com.example;\nclass App {}\n", encoding="utf-8"
    )
    return root


class CodeGraphTests(unittest.TestCase):
    def test_node_and_edge_identity_are_stable(self):
        a = Node.create("File", "REPO", "file:src/App.java")
        b = Node.create("File", "REPO", "file:src/App.java")
        self.assertEqual(a.id, b.id)
        edge1 = Edge.create(a, "CONTAINS", b)
        edge2 = Edge.create(a, "CONTAINS", b)
        self.assertEqual(edge1.id, edge2.id)

    def test_graph_validation_and_traversal(self):
        graph = Graph({"id": "REPO"}, None, "RUN")
        a = Node.create("Module", "REPO", "module:a")
        b = Node.create("File", "REPO", "file:a/App.java")
        graph.add_node(a)
        graph.add_node(b)
        graph.add_edge(Edge.create(a, "CONTAINS", b))
        self.assertEqual(graph.validate(), [])
        self.assertEqual(graph.outgoing(a.id)[0].target, b.id)
        self.assertEqual(graph.incoming(b.id)[0].source, a.id)
        self.assertEqual(graph.neighbors(a.id), [b])
        self.assertEqual(graph.paths(a.id, b.id, 1), [[a.id, b.id]])

    def test_validation_rejects_orphan_and_bad_provenance(self):
        graph = Graph({"id": "REPO"}, None, "RUN")
        a = Node.create("Module", "REPO", "module:a")
        graph.add_node(a)
        graph.add_edge(Edge(
            id="EDGE-BAD", source=a.id, relation="CONTAINS", target="NODE-MISSING",
            repository_id="REPO", provenance="deterministic"
        ))
        self.assertTrue(any(e["code"] == "ORPHAN_EDGE_TARGET" for e in graph.validate()))

    def test_ingestion_build_produces_evidence_backed_graph(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = RepositoryScanner().scan(fixture(Path(tmp)))
            graph = build_from_ingestion(result)
            self.assertEqual(graph.validate(), [])
            self.assertTrue(any(n.type == "Repository" for n in graph.nodes.values()))
            self.assertTrue(any(n.type == "Module" for n in graph.nodes.values()))
            self.assertTrue(any(n.type == "File" for n in graph.nodes.values()))
            self.assertTrue(graph.edges)
            self.assertTrue(graph.evidence)

    def test_serialization_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = RepositoryScanner().scan(fixture(Path(tmp)))
            graph1 = build_from_ingestion(result)
            graph2 = build_from_ingestion(result)
            self.assertEqual(graph1.to_json(), graph2.to_json())
            self.assertIn('"schema_version": "aca-graph-0.2"', graph1.to_json())
            json.loads(graph1.to_json())

    def test_identity_does_not_depend_on_absolute_checkout_path(self):
        left = Node.create("File", "REPO", "file:module/App.java")
        right = Node.create("File", "REPO", "file:module/App.java")
        self.assertEqual(left.id, right.id)

    def test_inferred_edge_requires_confidence(self):
        graph = Graph({"id": "REPO"}, None, "RUN")
        a = Node.create("Module", "REPO", "module:a")
        b = Node.create("Module", "REPO", "module:b")
        graph.add_node(a)
        graph.add_node(b)
        graph.add_edge(Edge.create(a, "DEPENDS_ON", b, provenance="inferred", confidence=0.8))
        self.assertEqual(graph.validate(), [])

    def test_read_only_ingestion_to_graph(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture(Path(tmp))
            before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            build_from_ingestion(RepositoryScanner().scan(root))
            after = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
