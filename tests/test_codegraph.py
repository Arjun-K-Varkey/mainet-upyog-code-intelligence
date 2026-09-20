import json
import tempfile
import unittest
from pathlib import Path

from src.aca_graph import Edge, Graph, Node, build_from_ingestion
from src.aca_ingestion.scanner import RepositoryScanner
from src.aca_evidence import Evidence, EvidenceRegistry, EvidenceResolver, EvidenceSource


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

    def test_canonical_evidence_resolver_validates_graph_references(self):
        graph = Graph({"id": "REPO"}, "REV1", self.RUN)
        a = Node.create("Module", "REPO", "module:a", analysis_run_id=self.RUN, revision="REV1")
        b = Node.create("File", "REPO", "file:b", analysis_run_id=self.RUN, revision="REV1")
        graph.add_node(a); graph.add_node(b)
        evidence = Evidence.create(project_id="ACA", repository_id="REPO", revision="REV1", run_id=self.RUN, type="source", subject="file:b", source=EvidenceSource("test", "1"), value={"kind": "java"})
        graph.evidence[evidence.id] = evidence.to_dict()
        graph.add_edge(Edge.create(a, "CONTAINS", b, evidence_refs=(evidence.id,), analysis_run_id=self.RUN, revision="REV1"))
        resolver = EvidenceResolver(EvidenceRegistry([evidence]))
        self.assertEqual(graph.validate(resolver), [])
        self.assertTrue(any(e["code"] == "UNRESOLVED_CANONICAL_EVIDENCE" for e in graph.validate(EvidenceResolver(EvidenceRegistry()))))

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
        graph.evidence["E1"] = {"run_id": self.RUN, "source": "test"}
        graph.add_edge(Edge.create(a, "DEPENDS_ON", b, provenance="inferred",
                                   confidence=0.8, evidence_refs=("E1",), analysis_run_id=self.RUN))

    def test_inferred_edge_with_evidence_is_valid(self):
        graph = Graph({"id": "REPO"}, None, self.RUN)
        a = Node.create("Module", "REPO", "module:a", analysis_run_id=self.RUN)
        b = Node.create("Module", "REPO", "module:b", analysis_run_id=self.RUN)
        graph.add_node(a)
        graph.add_node(b)
        graph.evidence["E1"] = {"run_id": self.RUN, "source": "test"}
        graph.add_edge(Edge.create(a, "DEPENDS_ON", b, provenance="inferred",
                                   confidence=0.8, evidence_refs=("E1",), analysis_run_id=self.RUN))
        self.assertEqual(graph.validate(), [])

    def test_edge_rejects_cross_revision_endpoints(self):
        graph = Graph({"id": "REPO"}, "REV1", self.RUN)
        a = Node.create("Module", "REPO", "module:a", analysis_run_id=self.RUN, revision="REV1")
        b = Node.create("Module", "REPO", "module:b", analysis_run_id=self.RUN, revision="REV2")
        graph.add_node(a)
        graph.add_node(b)
        graph.add_edge(Edge(
            id="EDGE-CROSS-REV", source=a.id, relation="DEPENDS_ON", target=b.id,
            repository_id="REPO", provenance="deterministic", analysis_run_id=self.RUN, revision="REV1"
        ))
        self.assertTrue(any(e["code"] == "TARGET_REVISION_MISMATCH" for e in graph.validate()))

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

    def test_nested_module_files_prefer_nested_module(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "module-a/src").mkdir(parents=True)
            (root / "pom.xml").write_text("<project/>\n", encoding="utf-8")
            (root / "module-a/pom.xml").write_text("<project/>\n", encoding="utf-8")
            (root / "App.java").write_text("class RootApp {}\n", encoding="utf-8")
            (root / "module-a/src/App.java").write_text("package com.example;\nclass NestedApp {}\n", encoding="utf-8")
            graph = build_from_ingestion(RepositoryScanner().scan(root))
            nested = next(n for n in graph.nodes.values() if n.type == "Module" and n.properties["root"] == "module-a")
            nested_file = next(n for n in graph.nodes.values() if n.type == "File" and n.properties["path"] == "module-a/src/App.java")
            root_module = next(n for n in graph.nodes.values() if n.type == "Module" and n.properties["root"] == ".")
            root_file = next(n for n in graph.nodes.values() if n.type == "File" and n.properties["path"] == "App.java")
            self.assertTrue(any(e.target == nested_file.id for e in graph.outgoing(nested.id, "CONTAINS")))
            self.assertFalse(any(e.target == nested_file.id for e in graph.outgoing(root_module.id, "CONTAINS")))
            self.assertTrue(any(e.target == root_file.id for e in graph.outgoing(root_module.id, "CONTAINS")))

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

    def test_package_is_reachable_from_owning_module(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "module-a/src/main/java/com/example").mkdir(parents=True)
            (root / "module-a/pom.xml").write_text("<project/>\\n", encoding="utf-8")
            (root / "module-a/src/main/java/com/example/App.java").write_text(
                "package com.example;\\nclass App {}\\n", encoding="utf-8"
            )
            graph = build_from_ingestion(RepositoryScanner().scan(root))
            module = next(n for n in graph.nodes.values()
                          if n.type == "Module" and n.properties["root"] == "module-a")
            package = next(n for n in graph.nodes.values()
                           if n.type == "Package" and n.properties["name"] == "com.example")
            file_node = next(n for n in graph.nodes.values()
                             if n.type == "File" and n.properties["path"].endswith("App.java"))
            self.assertTrue(any(e.target == package.id for e in graph.outgoing(module.id, "CONTAINS")))
            self.assertTrue(any(e.target == file_node.id for e in graph.outgoing(package.id, "CONTAINS")))
            self.assertTrue(graph.paths(module.id, file_node.id, 2))

    def test_serialized_node_id_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            graph = build_from_ingestion(RepositoryScanner().scan(Path(tmp)))
            data = json.loads(graph.to_json())
            data["nodes"][0]["id"] = "NODE-TAMPERED"
            with self.assertRaises(Exception) as ctx:
                Graph.from_dict(data)
            self.assertIn("NODE_ID_MISMATCH", str(ctx.exception))

    def test_serialized_edge_id_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "App.java").write_text("class App {}\\n", encoding="utf-8")
            graph = build_from_ingestion(RepositoryScanner().scan(root))
            data = json.loads(graph.to_json())
            data["edges"][0]["id"] = "EDGE-TAMPERED"
            with self.assertRaises(Exception) as ctx:
                Graph.from_dict(data)
            self.assertIn("EDGE_ID_MISMATCH", str(ctx.exception))

    def test_java_package_parser_handles_comments_and_literals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cases = {
                "Trailing.java": 'package com.trailing; // generated\nclass A {}\n',
                "Block.java": '/* package fake.block; */\npackage com.block;\nclass B {}\n',
                "Literal.java": 'String s = "/* package fake.literal; */";\npackage com.literal;\nclass C {}\n',
            }
            for name, content in cases.items():
                (root / name).write_text(content, encoding="utf-8")
            result = RepositoryScanner().scan(root)
            packages = {r.path: r.package_name for r in result.files if r.kind == "java"}
            self.assertEqual(packages["Trailing.java"], "com.trailing")
            self.assertEqual(packages["Block.java"], "com.block")
            self.assertEqual(packages["Literal.java"], "com.literal")

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
            self.assertTrue(packages[0].evidence_refs)
            self.assertTrue(all(ref in graph.evidence for ref in packages[0].evidence_refs))
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

    def test_git_revision_evidence_and_graph_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "App.java").write_text("class App {}\n", encoding="utf-8")
            import subprocess
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "aca@test"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "ACA Test"], cwd=root, check=True)
            subprocess.run(["git", "add", "App.java"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-m", "fixture"], cwd=root, check=True, capture_output=True)
            result = RepositoryScanner().scan(root)
            self.assertIsNotNone(result.repository["revision"])
            self.assertTrue(any(e.type == "revision" for e in result.evidence))
            graph = build_from_ingestion(result)
            self.assertEqual(graph.validate(), [])

    def test_serialization_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            graph = build_from_ingestion(RepositoryScanner().scan(Path(tmp)))
            restored = Graph.from_dict(json.loads(graph.to_json()))
            self.assertEqual(restored.to_json(), graph.to_json())


if __name__ == "__main__":
    unittest.main()
