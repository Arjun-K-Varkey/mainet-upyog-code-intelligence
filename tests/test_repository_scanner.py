import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.aca_ingestion.cli import main as cli_main
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
    def test_ac01_repository_discovery_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = RepositoryScanner().scan(make_fixture(Path(tmp)))
            self.assertEqual(result.status, "success")
            self.assertTrue(result.repository["id"])
            self.assertTrue(result.repository["workspace_id"])
            self.assertTrue(result.repository["source_path"])
            self.assertIn(result.repository["vcs"], {"git", "mercurial", "subversion", "none"})
            self.assertTrue(result.repository["scan_timestamp"])

    def test_ac02_determinism_and_stable_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_fixture(Path(tmp)); scanner = RepositoryScanner()
            first, second = scanner.scan(root).to_dict(), scanner.scan(root).to_dict()
            for result in (first, second): result["repository"].pop("scan_timestamp", None)
            self.assertEqual(first, second)
            self.assertEqual(first["files"], sorted(first["files"], key=lambda item: item["path"]))

    def test_ac03_classification(self):
        with tempfile.TemporaryDirectory() as tmp:
            kinds = {r.path: r.kind for r in RepositoryScanner().scan(make_fixture(Path(tmp))).files}
            expected = {"module-a/pom.xml":"maven","module-a/src/main/java/com/example/App.java":"java","module-a/src/main/webapp/index.jsp":"jsp","module-a/src/main/resources/schema.sql":"sql","module-a/src/main/resources/app.properties":"properties","module-a/src/main/resources/config.yaml":"yaml","module-a/src/main/webapp/app.js":"javascript","module-a/src/main/webapp/schema.xml":"xml"}
            for path, kind in expected.items(): self.assertEqual(kinds[path], kind)

    def test_ac04_module_metadata_and_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = RepositoryScanner().scan(make_fixture(Path(tmp)))
            module = next(m for m in result.modules if m.root == "module-a")
            self.assertEqual(module.module_type, "maven")
            self.assertIn("module-a/src/main/java", module.source_roots)
            self.assertIn("module-a/src/main/resources", module.resource_roots)
            self.assertIsNone(module.parent)

    def test_ac04_structural_module_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            (root / "app/src/main/java/example").mkdir(parents=True)
            (root / "app/src/main/java/example/App.java").write_text("class App {}\n", encoding="utf-8")
            result = RepositoryScanner().scan(root)
            module = next(m for m in result.modules if m.root == "app")
            self.assertEqual(module.module_type, "structural")
            self.assertIn("app/src/main/java", module.source_roots)

    def test_ac05_evidence_provenance_and_error_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_fixture(Path(tmp)); (root / "large.txt").write_bytes(b"1234567890")
            result = RepositoryScanner(ScanConfig(max_file_size=5)).scan(root)
            self.assertTrue(result.evidence)
            self.assertTrue(any(e.status == "warning" for e in result.evidence))
            for evidence in result.evidence:
                self.assertEqual(evidence.repository_id, result.repository["id"])
                self.assertIsNotNone(evidence.run_id)
                self.assertEqual(evidence.tool_version, result.repository["tool_version"])

    def test_ac06_safe_failure_and_partial_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_fixture(Path(tmp)); (root / "large.txt").write_bytes(b"1234567890")
            result = RepositoryScanner(ScanConfig(max_file_size=5)).scan(root)
            self.assertTrue(any(e["code"] == "FILE_TOO_LARGE" for e in result.errors))
            self.assertEqual(result.status, "partial_success")

    def test_ac07_read_only_and_no_repository_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_fixture(Path(tmp)); before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            (root / "execute.sh").write_text("touch SHOULD_NOT_EXIST\n", encoding="utf-8")
            RepositoryScanner().scan(root)
            after = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            self.assertNotIn("SHOULD_NOT_EXIST", {p.name for p in root.iterdir()})
            self.assertEqual(before | {"execute.sh": b"touch SHOULD_NOT_EXIST\n"}, after)

    def test_ac07_cli_rejects_output_inside_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_fixture(Path(tmp))
            output = root / "inventory.json"
            with patch("sys.argv", ["aca-ingestion", str(root), "--output", str(output)]):
                self.assertEqual(cli_main(), 1)
            self.assertFalse(output.exists())

    def test_ac08_json_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = RepositoryScanner().scan(make_fixture(Path(tmp))); decoded = json.loads(result.to_json())
            self.assertIsInstance(decoded, dict); self.assertEqual(len(decoded["files"]), len(result.files)); self.assertEqual(len(decoded["modules"]), len(result.modules)); self.assertEqual(len(decoded["evidence"]), len(result.evidence))

    def test_ac09_repeatability_and_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); left, right = make_fixture(base / "left"), make_fixture(base / "right")
            self.assertEqual(RepositoryScanner().scan(left).to_dict()["repository"]["id"], RepositoryScanner().scan(right).to_dict()["repository"]["id"])

    def test_include_exclude_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = RepositoryScanner(ScanConfig(include_paths=("module-a/src/main/**",), exclude_paths=("**/resources/**",))).scan(make_fixture(Path(tmp)))
            paths = {r.path for r in result.files}; self.assertIn("module-a/src/main/java/com/example/App.java", paths); self.assertNotIn("module-a/src/main/resources/schema.sql", paths); self.assertNotIn("excluded/skip.java", paths)

    def test_generated_and_vendor_policies(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = RepositoryScanner().scan(make_fixture(Path(tmp)))
            self.assertTrue(next(r for r in result.files if r.path.endswith("Generated.java")).generated)
            self.assertTrue(next(r for r in result.files if r.path == "vendor/ignored.java").vendor)

    def test_hash_and_line_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = next(r for r in RepositoryScanner().scan(make_fixture(Path(tmp))).files if r.path.endswith("App.java"))
            self.assertEqual(len(record.sha256), 64); self.assertEqual(record.line_count, 1)


if __name__ == "__main__": unittest.main()
