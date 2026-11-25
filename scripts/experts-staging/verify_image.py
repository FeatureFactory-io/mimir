"""Verify actual immutable image bytes before Django or a database is opened."""

from __future__ import annotations

import json
from importlib.metadata import version
from pathlib import Path

from contract import validate_source_files


def main() -> None:
    """Validate the trusted Git manifest mounted outside the candidate image.

    :return: None after all selected application bytes match their Git source.
    :raises ValueError: Any image source input differs or has unsafe coverage.
    """
    source = json.loads(Path("/runtime/source.json").read_text())
    validate_source_files(Path("/app"), source["files"])
    record = {
        "source_revision": source["source_revision"],
        "verified_files": len(source["files"]),
        "identity": "digest_and_actual_source_bytes",
    }
    record["runtime_versions"] = {
        name: version(name) for name in ("Django", "anthropic", "playwright", "psycopg")
    }
    record["fixture_sha256"] = source["files"]["test-data/experts/cedar-rfp-01.json"]
    Path("/output/image-source-verification.json").write_text(
        json.dumps(record, indent=2) + "\n"
    )
    Path("/output/source-manifest.json").write_text(json.dumps(source, indent=2) + "\n")
    print(json.dumps(record))


if __name__ == "__main__":
    main()
