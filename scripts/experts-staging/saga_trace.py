"""Produce explicitly redacted public traces from untouched private acquisitions."""

from __future__ import annotations

import hashlib
import html
import json
import os
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote, quote_plus

_MAX_TRACE_BYTES = 200 * 1024 * 1024
_MAX_MEMBERS = 10000
_MAX_PRIVATE_VALUES = 4096
_MAX_PRIVATE_VALUE_CHARS = 8192
_REDACTED = b"[REDACTED_TEST_SECRET]"


def redact_trace(
    original: Path, public: Path, private_values: set[str]
) -> dict[str, Any]:
    """Redact captured secrets in every member and verify the resulting archive.

    :param original: Untouched private original ZIP, retained outside public export.
    :param public: New public derivative ZIP; never overwrite an acquisition.
    :param private_values: Actual observed secret strings, never returned or logged.
    :return: Safe original/derivative hashes and member replacement counts.
    :raises ValueError: Secret cannot be safely removed or a ZIP path is unsafe.
    :raises FileExistsError: Public destination already exists.
    """
    secrets = validate_inputs(original, public, private_values)
    descriptor, name = tempfile.mkstemp(
        prefix=".saga-public-", suffix=".zip", dir=public.parent
    )
    os.close(descriptor)
    temporary = Path(name)
    try:
        changed, total = write_redacted(original, temporary, secrets)
        verify_redacted(temporary, secrets)
        os.link(temporary, public)
        result = trace_provenance(original, public)
        result.update(redacted_members=changed, members=total)
        return result
    finally:
        temporary.unlink(missing_ok=True)


def trace_provenance(original: Path, public: Path) -> dict[str, Any]:
    """Bind the public derivative to actual untouched private acquisition bytes.

    :param original: Private actual ZIP acquisition.
    :param public: Verified redacted ZIP derivative.
    :return: Safe SHA identities and explicit derivation/retention qualifications.
    """
    return {
        "original_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
        "public_sha256": hashlib.sha256(public.read_bytes()).hexdigest(),
        "public_trace_is_derivative": True,
        "binary_images_unchanged": True,
        "raw_trace_exported": False,
    }


def validate_inputs(
    original: Path, public: Path, values: set[str]
) -> tuple[bytes, ...]:
    """Validate exact input files and nonempty bounded captured private values.

    :param original: Actual untouched ZIP acquisition.
    :param public: New output path in an existing owned directory.
    :param values: Captured actual strings, never exposed by the return metadata.
    :return: Longest-first private byte values for deterministic replacement.
    :raises ValueError: Input type/path/size or captured values are unsafe.
    :raises FileExistsError: The destination already exists.
    """
    if public.exists() or public.is_symlink():
        raise FileExistsError("Public trace evidence already exists.")
    if (
        not original.is_file()
        or original.is_symlink()
        or original.resolve() == public.resolve()
    ):
        raise ValueError("An independent actual original trace file is required.")
    if original.stat().st_size > _MAX_TRACE_BYTES:
        raise ValueError("Bounded actual trace bytes are required.")
    return encode_private_values(values)


def encode_private_values(values: set[str]) -> tuple[bytes, ...]:
    """Validate captured actual private values and order replacements deterministically.

    :param values: Finite private observations retained only in memory.
    :return: Longest-first immutable byte values; never public metadata.
    :raises ValueError: Values are missing, malformed or unbounded.
    """
    if not isinstance(values, set) or not values or len(values) > _MAX_PRIVATE_VALUES:
        raise ValueError("Finite actual private observations are required.")
    if any(
        not isinstance(value, str) or not 8 <= len(value) <= _MAX_PRIVATE_VALUE_CHARS
        for value in values
    ):
        raise ValueError("Captured private values must be bounded strings.")
    variants = {variant for value in values for variant in secret_variants(value)}
    return tuple(
        value.encode()
        for value in sorted(variants, key=lambda value: (-len(value), value))
    )


def secret_variants(value: str) -> set[str]:
    """Cover actual JSON, HTML and form encodings used in browser trace resources.

    :param value: Already validated actual private string.
    :return: Finite raw and encoded variants, retained only in memory.
    """
    return {
        value,
        json.dumps(value, ensure_ascii=True)[1:-1],
        json.dumps(value, ensure_ascii=False)[1:-1],
        html.escape(value),
        quote(value, safe=""),
        quote_plus(value, safe=""),
    }


def write_redacted(
    original: Path, temporary: Path, secrets: tuple[bytes, ...]
) -> tuple[int, int]:
    """Copy every actual member while validating topology and private replacements.

    :param original: Untouched actual acquisition.
    :param temporary: Owned temporary output, never yet public evidence.
    :param secrets: Captured private bytes ordered longest-first.
    :return: Actual changed and total member counts.
    :raises ValueError: Unsafe paths, duplicate entries, size or binary secrets differ.
    """
    changed = 0
    with (
        zipfile.ZipFile(original) as source,
        zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as target,
    ):
        members = source.infolist()
        validate_members(members)
        for member in members:
            raw = source.read(member)
            cleaned = redact_member(raw, secrets)
            changed += int(cleaned != raw)
            target.writestr(member.filename, cleaned)
    return changed, len(members)


def validate_members(members: list[zipfile.ZipInfo]) -> None:
    """Require bounded regular trace resources and closed portable member names.

    :param members: Real source ZIP directory entries.
    :return: None after topology, duplicate and total-size checks pass.
    :raises ValueError: Any archive member is unsafe or oversized.
    """
    names = [member.filename for member in members]
    if not members or len(members) > _MAX_MEMBERS or len(set(names)) != len(names):
        raise ValueError("Trace archive member set is invalid.")
    if sum(member.file_size for member in members) > _MAX_TRACE_BYTES:
        raise ValueError("Trace archive exceeds the bounded uncompressed limit.")
    for member in members:
        path = PurePosixPath(member.filename)
        if path.is_absolute() or ".." in path.parts or "\\" in member.filename:
            raise ValueError("Unsafe trace resource path.")
        if stat.S_ISLNK(member.external_attr >> 16):
            raise ValueError("Trace resources cannot be symbolic links.")


def redact_member(raw: bytes, secrets: tuple[bytes, ...]) -> bytes:
    """Remove every captured private value from text; preserve actual binary pixels.

    :param raw: Actual decompressed trace event, DOM, resource or binary bytes.
    :param secrets: Actual private byte values, never logged.
    :return: Cleaned text or byte-identical binary data.
    :raises ValueError: A binary member contains a captured private value.
    """
    if not any(secret in raw for secret in secrets):
        return raw
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(
            "Private value in a binary trace resource; keep acquisition private."
        ) from error
    for secret in secrets:
        raw = raw.replace(secret, _REDACTED)
    return raw


def verify_redacted(path: Path, secrets: tuple[bytes, ...]) -> None:
    """Scan every public ZIP member and name before its exclusive publication.

    :param path: Fully written temporary derivative archive.
    :param secrets: Actual captured private byte values.
    :return: None only when every decompressed public member is free of them.
    :raises ValueError: Any captured value survives in a name, comment or body.
    """
    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            fields = (member.filename.encode(), member.comment, archive.read(member))
            if any(secret in field for secret in secrets for field in fields):
                raise ValueError("Private value survived trace redaction.")
