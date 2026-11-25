"""Admit only the two byte-bound proofs from the reviewed core-only CI artifact.

The workflow downloads fixed artifact14995828139 through GitHub's authenticated
API. This module performs no network requests and never extracts other media.
Successful proof admission authorizes an explicit bounded trial, not staging UAT.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import logging
import os
import stat
import zipfile
from pathlib import Path

LOGGER = logging.getLogger(__name__)
MAX_ARCHIVE_BYTES = 20 * 1024 * 1024
ARCHIVE_SHA256 = "ddd99b7ae73c9a6241fa72f433aac1283457c6b8f7433c5dfa074ae2ac7c9ac7"
PROOF_MEMBERS = {
    "benchmark-result.json": (
        10908,
        "13d50049c9361802038992873da696ad058fa9e04d4d2cf2077ebd8cd7defb4d",
    ),
    "benchmark-source.json": (
        1815,
        "9543610b70d5e80a261866beda67a86a3b6f8547954026334ea286dcaf8750e9",
    ),
}


def _archive_bytes(path: Path) -> bytes:
    """Read one regular, owned, unlinked artifact through a non-following handle.

    :param path: Downloaded original ZIP path.
    :return: Exact immutable verified bytes.
    :raises ValueError: File ownership, bounds, stability or digest differs.
    :raises OSError: File cannot be opened safely.
    """
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_uid != os.geteuid()
            or not 0 < before.st_size <= MAX_ARCHIVE_BYTES
        ):
            raise ValueError("Resource artifact must be a bounded owned regular file")
        payload = stream.read(MAX_ARCHIVE_BYTES + 1)
        after = os.fstat(stream.fileno())
    stable_fields = (
        "st_dev",
        "st_ino",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
        "st_nlink",
        "st_uid",
        "st_mode",
    )
    if (
        any(getattr(before, field) != getattr(after, field) for field in stable_fields)
        or len(payload) != before.st_size
        or hashlib.sha256(payload).hexdigest() != ARCHIVE_SHA256
    ):
        raise ValueError("Resource artifact differs from reviewed immutable CI proof")
    return payload


def _proof_members(payload: bytes) -> dict[str, bytes]:
    """Read only named, length-bounded members after the whole-ZIP digest passed.

    :param payload: Verified artifact ZIP bytes.
    :return: Two exact reviewed JSON byte strings.
    :raises ValueError: A proof member is duplicated, oversized or altered.
    :raises zipfile.BadZipFile: The verified archive is invalid.
    """
    values = {}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = archive.namelist()
        for name, (length, digest) in PROOF_MEMBERS.items():
            if names.count(name) != 1 or archive.getinfo(name).file_size != length:
                raise ValueError("Resource proof member identity or length differs")
            value = archive.read(name)
            if hashlib.sha256(value).hexdigest() != digest:
                raise ValueError("Resource proof member differs from reviewed bytes")
            values[name] = value
    return values


def _write_members(directory: Path, values: dict[str, bytes]) -> None:
    """Write exclusively through the newly created output directory handle.

    :param directory: New private output directory.
    :param values: Previously verified closed member map.
    :raises OSError: A destination exists or cannot be written safely.
    :return: None after both exact files are flushed to disk.
    """
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for name, value in values.items():
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
            handle = os.open(name, flags, 0o600, dir_fd=descriptor)
            with os.fdopen(handle, "wb") as stream:
                stream.write(value)
                stream.flush()
                os.fsync(stream.fileno())
    finally:
        os.close(descriptor)


def extract_proof(archive: Path, output: Path) -> None:
    """Export the fixed measurement JSONs without overwriting existing material.

    :param archive: Original downloaded ZIP; no substituted caller digest.
    :param output: New private directory under an existing parent.
    :return: None after both exact byte-bound proofs are written.
    :raises TypeError: Source or destination is not a Path.
    :raises ValueError: Immutable proof bytes are invalid.
    :raises OSError: Source or destination cannot be handled safely.
    :example: extract_proof(Path('original.zip'), Path('measured-resource-proof'))
    """
    if not isinstance(archive, Path) or not isinstance(output, Path):
        raise TypeError("Resource proof source and output must be Paths")
    LOGGER.info("Verifying fixed core-only CI measurement before proof export")
    values = _proof_members(_archive_bytes(archive))
    output.mkdir(mode=0o700)
    _write_members(output, values)
    LOGGER.info("Exported two immutable measurement proofs; staging remains pending")


def main() -> None:
    """Validate one original artifact selected by the fixed workflow.

    :return: None after exact JSON proofs are safely exported.
    :raises SystemExit: Arguments or proof admission fail.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    extract_proof(args.archive, args.output)


if __name__ == "__main__":
    main()
