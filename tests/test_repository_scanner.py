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


def test_inventory_is_deterministic(tmp_path):
    root = make_fixture(tmp_path)
    scanner = RepositoryScanner()
    first = scanner.scan(root).to_dict()
    second = scanner.scan(root).to_dict()
    assert first["files"] == second["files"]
    assert first["modules"] == second["modules"]
    assert first["evidence"] == second["evidence"]


def test_classification_and_module_detection(tmp_path):
    result = RepositoryScanner().scan(make_fixture(tmp_path))
    kinds = {record.path: record.kind for record in result.files}
    assert kinds["module-a/pom.xml"] == "maven"
    assert kinds["module-a/src/main/java/com/example/App.java"] == "java"
    assert kinds["module-a/src/main/webapp/index.jsp"] == "jsp"
    assert kinds["module-a/src/main/resources/schema.sql"] == "sql"
    assert result.modules[0].module_type == "maven"


def test_excluded_directory_is_not_scanned(tmp_path):
    result = RepositoryScanner().scan(make_fixture(tmp_path))
    assert all(not record.path.startswith("vendor/") for record in result.files)


def test_hash_and_line_count(tmp_path):
    result = RepositoryScanner().scan(make_fixture(tmp_path))
    record = next(r for r in result.files if r.path.endswith("App.java"))
    assert len(record.sha256) == 64
    assert record.line_count == 1


def test_max_size_is_reported_without_reading_as_source(tmp_path):
    root = make_fixture(tmp_path)
    (root / "large.txt").write_bytes(b"1234567890")
    result = RepositoryScanner(ScanConfig(max_file_size=5)).scan(root)
    assert any(error["code"] == "FILE_TOO_LARGE" for error in result.errors)


def test_output_is_machine_readable(tmp_path):
    result = RepositoryScanner().scan(make_fixture(tmp_path))
    payload = result.to_json()
    assert payload.startswith("{")
    assert '"files"' in payload
    assert '"evidence"' in payload
