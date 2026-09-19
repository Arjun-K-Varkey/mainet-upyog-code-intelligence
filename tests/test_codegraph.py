import json
import tempfile
import unittest
from pathlib import Path

from src.aca_graph import Edge, Graph, Node, build_from_ingestion
from src.aca_ingestion.scanner import RepositoryScanner


def fixture(root: Path) -> Path:
    (root / "module-a/src/main/java/com/example").mkdir(parents=True)
    (root / "module-a/pom.xml").write_text("<project/>\n", encoding="utf-8")
    (root / "module-a/src/main/java/com/example/App.java").write_text(
        "package com.example;\nclass App {}\n", encoding="utf-8"
    )
    return root


class CodeGraphTests(unittest.TestCase):
    RUN = "RUN"

    def test_node_and_edge_identity_are_stable(self):
        a = Node.create("File", "REPO", "file:src/App.java", analysis_run_id=self.RUN)
        b = Node.create("File", "REPO", "file:src/App.java", analysis_run_id=self.RUN)
        self.assertEqual(a.id, b.id)
        edge1 = Edge.create(a, "CONTAINS", b, analysis_run_id=self.RUN)
        edge2 = Edge.create(a, "CONTAINS", b, analysis_run_id=self.RUN)
        self.assertEqual(edge1.id, edge2.id)

    def test_analysis_run_identity_is_required(self):
        with self.assertRaises(ValueError):
            Node.create("File", "REPO", "file:src/App.java")
        a = Node.create("File", "REPO", "file:a", analysis_run_id=self.RUN)
        with self.assertRaises(ValueError):
            Edge.create(a, "CONTAINS", a)

    def test_graph_validation_and_traversal(self):
        graph = Graph({"id": "REPO"}, None, self.RUN)
        a = Node.create("Module", "REPO", "module:a", analysis_run_id=self.RUN)
        b = Node.create("File", "REPO", "file:a/App.java", analysis_run_id=self.RUN)
        graph.add_node(a)
        graph.add_node(b)
        graph.add_edge(Edge.create(a, "CONTAINS", b, analysis_run_id=self.RUN))
        self.assertEqual(graph.validate(), [])
        self.assertEqual(graph.outgoing(a.id)[0].target, b.id)
        self.assertEqual(graph.incoming(b.id)[0].source, a.id)
        self.assertEqual(graph.neighbors(a.id), [b])
        self.assertEqual(graph.paths(a.id, b.id, 1), [[a.id, b.id]])

    def test_validation_rejects_orphan_and_bad_provenance(self):
        graph = Graph({"id": "REPO"}, None, self.RUN)
        a = Node.create("Module", "REPO", "module:a", analysis_run_id=self.RUN)
        graph.add_node(a)
        graph.add_edge(Edge(
            id="EDGE-BAD", source=a.id, relation="CONTAINS", target="NODE-MISSING",
            repository_id="REPO", provenance="deterministic", analysis_run_id=self.RUN
        ))
        self.assertTrue(any(e["code"] == "ORPHAN_EDGE_TARGET" for e in graph.validate()))

    def test_validation_rejects_missing_analysis_run_even_if_constructed_directly(self):
        graph = Graph({"id": "REPO"}, None, self.RUN)
        a = Node(id="NODE-A", type="Module", repository_id="REPO",
                 canonical_key="module:a", analysis_run_id=None)
        graph.add_node(a)
        self.assertTrue(any(e["code"] == "MISSING_NODE_IDENTITY" for e in graph.validate()))

    def test_ingestion_build_produces_evidence_backed_graph(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = RepositoryScanner().scan(fixture(Path(tmp)))
            graph = build_from_ingestion(result)
            self.assertEqual(graph.validate(), [])
            self.assertTrue(any(n.type == "Repository" for n in graph.nodes.values()))
            self.assertTrue(any(n.type == "Module" for n in graph.nodes.values()))
            self.assertTrue(any(n.type == "Package" and n.properties["name"] == "com.example"
                                for n in graph.nodes.values()))
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
        left = Node.create("File", "REPO", "file:module/App.java", analysis_run_id=self.RUN)
        right = Node.create("File", "REPO", "file:module/App.java", analysis_run_id=self.RUN)
        self.assertEqual(left.id, right.id)

    def test_inferred_edge_requires_confidence(self):
        graph = Graph({"id": "REPO"}, None, self.RUN)
        a = Node.create("Module", "REPO", "module:a", analysis_run_id=self.RUN)
        b = Node.create("Module", "REPO", "module:b", analysis_run_id=self.RUN)
        graph.add_node(a)
        graph.add_node(b)
        graph.add_edge(Edge.create(a, "DEPENDS_ON", b, provenance="inferred",
                                   confidence=0.8, analysis_run_id=self.RUN))
        self.assertEqual(graph.validate(), [])

    def test_inferred_edge_without_confidence_is_invalid(self):
        graph = Graph({"id": "REPO"}, None, self.RUN)
        a = Node.create("Module", "REPO", "module:a", analysis_run_id=self.RUN)
        b = Node.create("Module", "REPO", "module:b", analysis_run_id=self.RUN)
        graph.add_node(a)
        graph.add_node(b)
        graph.add_edge(Edge(id="EDGE-INFERRED", source=a.id, relation="DEPENDS_ON",
                            target=b.id, repository_id="REPO", provenance="inferred",
                            analysis_run_id=self.RUN))
        self.assertTrue(any(e["code"] == "INFERRED_MISSING_CONFIDENCE" for e in graph.validate()))

    def test_inferred_edge_without_evidence_is_invalid(self):
        graph = Graph({"id": "REPO"}, None, self.RUN)
        a = Node.create("Module", "REPO", "module:a", analysis_run_id=self.RUN)
        b = Node.create("Module", "REPO", "module:b", analysis_run_id=self.RUN)
        graph.add_node(a)
        graph.add_node(b)
        graph.add_edge(Edge.create(a, "DEPENDS_ON", b, provenance="inferred",
                                   confidence=0.8, analysis_run_id=self.RUN))
        self.assertTrue(any(e["code"] == "INFERRED_MISSING_EVIDENCE" for e in graph.validate()))

    def test_root_module_contains_root_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pom.xml").write_text("<project/>\n", encoding="utf-8")
            (root / "App.java").write_text("package com.example;\nclass App {}\n", encoding="utf-8")
            result = RepositoryScanner().scan(root)
            graph = build_from_ingestion(result)
            root_module = next(n for n in graph.nodes.values()
                               if n.type == "Module" and n.properties["root"] == ".")
            file_node = next(n for n in graph.nodes.values()
                             if n.type == "File" and n.properties["path"] == "App.java")
            self.assertTrue(any(e.target == file_node.id for e in graph.outgoing(root_module.id, "CONTAINS")))

    def test_read_only_ingestion_to_graph(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture(Path(tmp))
            before = {p.relative_to(root).as_posix(): p.read_bytes()
                      for p in root.rglob("*") if p.is_file()}
            build_from_ingestion(RepositoryScanner().scan(root))
            after = {p.relative_to(root).as_posix(): p.read_bytes()
                     for p in root.rglob("*") if p.is_file()}
            self.assertEqual(before, after)

    def test_node_identity_is_revision_scoped(self):
        v1 = Node.create("File", "REPO", "file:App.java", analysis_run_id="RUN1", revision="REV1")
        v2 = Node.create("File", "REPO", "file:App.java", analysis_run_id="RUN2", revision="REV2")
        self.assertNotEqual(v1.id, v2.id)

    def test_multiple_java_files_share_package_without_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src/A.java").write_text("package com.example;\nclass A {}\n", encoding="utf-8")
            (root / "src/B.java").write_text("package com.example;\nclass B {}\n", encoding="utf-8")
            result = RepositoryScanner().scan(root)
            graph = build_from_ingestion(result)
            packages = [n for n in graph.nodes.values() if n.type == "Package"]
            self.assertEqual(len(packages), 1)
            package_id = packages[0].id
            self.assertEqual(len(graph.outgoing(package_id, "CONTAINS")), 2)
            self.assertEqual(graph.validate(), [])

    def test_serialization_ignores_workspace_path_and_scan_time(self):
        with tempfile.TemporaryDirectory() as left, tempfile.TemporaryDirectory() as right:
            left_root, right_root = Path(left) / "repo", Path(right) / "repo"
            for root in (left_root, right_root):
                (root / "src").mkdir(parents=True)
                (root / "src/App.java").write_text("package com.example;\nclass App {}\n", encoding="utf-8")
            from src.aca_ingestion.scanner import ScanConfig
            config = ScanConfig(repository_id="FIXED-REPO")
            first = build_from_ingestion(RepositoryScanner(config).scan(left_root))
            second = build_from_ingestion(RepositoryScanner(config).scan(right_root))
            self.assertEqual(first.to_json(), second.to_json())

    def test_serialization_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            graph = build_from_ingestion(RepositoryScanner().scan(Path(tmp)))
            restored = Graph.from_dict(json.loads(graph.to_json()))
            self.assertEqual(restored.to_json(), graph.to_json())


if __name__ == "__main__":
    unittest.main()
