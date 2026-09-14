"""Command-line entry point for repository ingestion."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .scanner import RepositoryScanner, ScanConfig


def _output_is_inside_repository(repository: Path, output: Path) -> bool:
    try:
        output.relative_to(repository)
        return True
    except ValueError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a deterministic ACA repository inventory")
    parser.add_argument("repository", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--max-file-size", type=int, default=10 * 1024 * 1024)
    args = parser.parse_args()

    repository = args.repository.resolve()
    output = args.output.resolve()
    if _output_is_inside_repository(repository, output):
        print("Error: output path must be outside the scanned repository", file=sys.stderr)
        return 1

    result = RepositoryScanner(ScanConfig(max_file_size=args.max_file_size)).scan(repository)
    output.write_text(result.to_json() + "\n", encoding="utf-8")
    return 0 if result.status != "failure" else 2


if __name__ == "__main__":
    raise SystemExit(main())
