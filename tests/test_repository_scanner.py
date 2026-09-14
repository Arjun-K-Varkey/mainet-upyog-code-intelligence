import json
import tempfile
import unittest
from pathlib import Path

from src.aca_ingestion.scanner import RepositoryScanner, ScanConfig


def make_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "module-a/src/main/java/com/example").mkdir(parents=True)
    (root / "module-a/src/main/webapp").mkdir(parents=True)
    (root / "module-a/src/main/resources").mkdir(parents=True)
    (root / "vendor").mkdir()
    (root / "module-a/pom.xml").write_text("<project/>\n", encoding="utf-8")
    (root / "module-a/src/main/java/com/example/App.java").write_text("class App {}\n", encoding="utf-8")
    (root / "module-a/src/main/webapp/index.jsp").write_text("<%-- test --%>\n", encoding="utf-8")
    (root / "module-a/src/main/resources/schema.sql").write_text("select 1;\n", encoding="utf-8")
    (root / "vendor/ignored.java").write_text("class Ignored {}\n", encoding="utf-8")
    return root


class RepositoryScannerTests(unittest.TestCase):
    def test_inventory_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_fixture(Path(tmp))
            scanner = RepositoryScanner()
            first = scanner.scan(root).to_dict()
            second = scanner.scan(root).to_dict()
            self.assertEqual(first["files"], second["files"])
            self.assertEqual(first["modules"], second["modules"])
            self.assertEqual(first["evidence"], second["evidence"])
            self.assertEqual(first["repository"], second["repository"])

    def test_classification_and_module_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = RepositoryScanner().scan(make_fixture(Path(tmp)))
            kinds = {record.path: record.kind for record in result.files}
            self.assertEqual(kinds["module-a/pom.xml"], "maven")
            self.assertEqual(kinds["module-a/src/main/java/com/example/App.java"], "java")
            self.assertEqual(kinds["module-a/src/main/webapp/index.jsp"], "jsp")
            self.assertEqual(kinds["module-a/src/main/resources/schema.sql"], "sql")
            self.assertEqual(result.modules[0].module_type, "maven")

    def test_vendor_path_is_classified_as_vendor(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = RepositoryScanner().scan(make_fixture(Path(tmp)))
            record = next(r for r in result.files if r.path == "vendor/ignored.java")
            self.assertTrue(record.vendor)

    def test_hash_and_line_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = RepositoryScanner().scan(make_fixture(Path(tmp)))
            record = next(r for r in result.files if r.path.endswith("App.java"))
            self.assertEqual(len(record.sha256), 64)
            self.assertEqual(record.line_count, 1)

    def test_max_size_is_reported_without_reading_as_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_fixture(Path(tmp))
            (root / "large.txt").write_bytes(b"1234567890")
            result = RepositoryScanner(ScanConfig(max_file_size=5)).scan(root)
            self.assertTrue(any(error["code"] == "FILE_TOO_LARGE" for error in result.errors))

    def test_output_is_machine_readable_and_round_trips_as_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = RepositoryScanner().scan(make_fixture(Path(tmp)))
            decoded = json.loads(result.to_json())
            self.assertIsInstance(decoded, dict)
            self.assertIn("files", decoded)
            self.assertIn("evidence", decoded)

    def test_same_content_in_different_paths_has_same_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            left = make_fixture(base / "left")
            right = make_fixture(base / "right")
            self.assertEqual(
                RepositoryScanner().scan(left).to_dict()["repository"]["id"],
                RepositoryScanner().scan(right).to_dict()["repository"]["id"],
            )

    def test_evidence_contains_repository_run_and_tool_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = RepositoryScanner().scan(make_fixture(Path(tmp)))
            self.assertTrue(result.evidence)
            for evidence in result.evidence:
                self.assertEqual(evidence.repository_id, result.repository["id"])
                self.assertIsNotNone(evidence.run_id)
                self.assertEqual(evidence.tool_version, result.repository["tool_version"])


if __name__ == "__main__":
    unittest.main()
