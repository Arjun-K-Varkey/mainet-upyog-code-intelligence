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
    (root / "module-a/src/test/java/com/example").mkdir(parents=True)
    (root / "module-a/generated").mkdir(parents=True)
    (root / "vendor").mkdir()
    (root / "excluded").mkdir()
    (root / "module-a/pom.xml").write_text("<project/>\n", encoding="utf-8")
    (root / "module-a/src/main/java/com/example/App.java").write_text("class App {}\n", encoding="utf-8")
    (root / "module-a/src/main/webapp/index.jsp").write_text("<%-- test --%>\n", encoding="utf-8")
    (root / "module-a/src/main/resources/schema.sql").write_text("select 1;\n", encoding="utf-8")
    (root / "module-a/src/main/resources/app.properties").write_text("a=b\n", encoding="utf-8")
    (root / "module-a/src/main/resources/config.yaml").write_text("a: b\n", encoding="utf-8")
    (root / "module-a/src/main/webapp/app.js").write_text("console.log('x');\n", encoding="utf-8")
    (root / "module-a/src/main/webapp/schema.xml").write_text("<x/>\n", encoding="utf-8")
    (root / "module-a/generated/Generated.java").write_text("class Generated {}\n", encoding="utf-8")
    (root / "module-a/src/test/java/com/example/Test.java").write_text("class Test {}\n", encoding="utf-8")
    (root / "vendor/ignored.java").write_text("class Ignored {}\n", encoding="utf-8")
    (root / "excluded/skip.java").write_text("class Skip {}\n", encoding="utf-8")
    return root


class RepositoryScannerTests(unittest.TestCase):
    def test_ac01_repository_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = RepositoryScanner().scan(make_fixture(Path(tmp)))
            self.assertEqual(result.status, "success")
            self.assertTrue(result.repository["id"])

    def test_ac02_determinism_and_stable_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_fixture(Path(tmp))
            scanner = RepositoryScanner()
            first = scanner.scan(root).to_dict()
            second = scanner.scan(root).to_dict()
            self.assertEqual(first, second)
            self.assertEqual(first["files"], sorted(first["files"], key=lambda item: item["path"]))

    def test_ac03_classification(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = RepositoryScanner().scan(make_fixture(Path(tmp)))
            kinds = {record.path: record.kind for record in result.files}
            expected = {
                "module-a/pom.xml": "maven",
                "module-a/src/main/java/com/example/App.java": "java",
                "module-a/src/main/webapp/index.jsp": "jsp",
                "module-a/src/main/resources/schema.sql": "sql",
                "module-a/src/main/resources/app.properties": "properties",
                "module-a/src/main/resources/config.yaml": "yaml",
                "module-a/src/main/webapp/app.js": "javascript",
                "module-a/src/main/webapp/schema.xml": "xml",
            }
            for path, kind in expected.items():
                self.assertEqual(kinds[path], kind)

    def test_ac04_module_metadata_and_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = RepositoryScanner().scan(make_fixture(Path(tmp)))
            self.assertEqual(len(result.modules), 1)
            module = result.modules[0]
            self.assertEqual(module.module_type, "maven")
            self.assertEqual(module.root, "module-a")
            self.assertIn("module-a/src/main/java", module.source_roots)
            self.assertIn("module-a/src/main/resources", module.resource_roots)
            self.assertIsNone(module.parent)

    def test_ac05_evidence_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = RepositoryScanner().scan(make_fixture(Path(tmp)))
            self.assertEqual(len(result.evidence), len(result.files) + len(result.modules))
            for evidence in result.evidence:
                self.assertEqual(evidence.repository_id, result.repository["id"])
                self.assertIsNotNone(evidence.run_id)
                self.assertEqual(evidence.tool_version, result.repository["tool_version"])
                self.assertTrue(evidence.source_file)

    def test_ac06_safe_failure_and_partial_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_fixture(Path(tmp))
            (root / "large.txt").write_bytes(b"1234567890")
            result = RepositoryScanner(ScanConfig(max_file_size=5)).scan(root)
            self.assertTrue(any(error["code"] == "FILE_TOO_LARGE" for error in result.errors))
            self.assertEqual(result.status, "partial_success")

    def test_ac07_read_only_and_no_repository_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_fixture(Path(tmp))
            before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            (root / "execute.sh").write_text("touch SHOULD_NOT_EXIST\n", encoding="utf-8")
            scanner = RepositoryScanner()
            scanner.scan(root)
            after = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            self.assertNotIn("SHOULD_NOT_EXIST", {p.name for p in root.iterdir()})
            self.assertEqual(before | {"execute.sh": b"touch SHOULD_NOT_EXIST\n"}, after)

    def test_ac08_json_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = RepositoryScanner().scan(make_fixture(Path(tmp)))
            decoded = json.loads(result.to_json())
            self.assertIsInstance(decoded, dict)
            self.assertEqual(len(decoded["files"]), len(result.files))
            self.assertEqual(len(decoded["modules"]), len(result.modules))
            self.assertEqual(len(decoded["evidence"]), len(result.evidence))

    def test_ac09_repeatability_and_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            left = make_fixture(base / "left")
            right = make_fixture(base / "right")
            self.assertEqual(
                RepositoryScanner().scan(left).to_dict()["repository"]["id"],
                RepositoryScanner().scan(right).to_dict()["repository"]["id"],
            )

    def test_include_exclude_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_fixture(Path(tmp))
            config = ScanConfig(include_paths=("module-a/src/main/**",), exclude_paths=("**/resources/**",))
            result = RepositoryScanner(config).scan(root)
            paths = {record.path for record in result.files}
            self.assertIn("module-a/src/main/java/com/example/App.java", paths)
            self.assertNotIn("module-a/src/main/resources/schema.sql", paths)
            self.assertNotIn("excluded/skip.java", paths)

    def test_generated_and_vendor_policies(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = RepositoryScanner().scan(make_fixture(Path(tmp)))
            generated = next(r for r in result.files if r.path.endswith("Generated.java"))
            vendor = next(r for r in result.files if r.path == "vendor/ignored.java")
            self.assertTrue(generated.generated)
            self.assertTrue(vendor.vendor)

    def test_hash_and_line_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = RepositoryScanner().scan(make_fixture(Path(tmp)))
            record = next(r for r in result.files if r.path.endswith("App.java"))
            self.assertEqual(len(record.sha256), 64)
            self.assertEqual(record.line_count, 1)


if __name__ == "__main__":
    unittest.main()
