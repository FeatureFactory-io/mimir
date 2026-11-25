"""Check all-member trace redaction with real ZIP files and unchanged originals."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path
from urllib.parse import quote_plus

import pytest

_PATH = Path(__file__).resolve().parents[2] / "scripts/experts-staging/saga_trace.py"
_SPEC = importlib.util.spec_from_file_location("experts_saga_trace", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
trace = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(trace)
_SECRET = "fictional-private-value-123456"


def _original(
    root: Path, name: str = "resources/dom.html", content: bytes | None = None
) -> Path:
    """Create a real private source archive with a harmless binary image member.

    :param root: Runner-owned temporary directory.
    :param name: Member to test, e.g. a resource body.
    :param content: Explicit member bytes or a synthetic credential attribute.
    :return: Existing source archive path.
    """
    original = root / "original.zip"
    with zipfile.ZipFile(original, "x") as archive:
        archive.writestr(name, content or f'<input value="{_SECRET}">'.encode())
        archive.writestr("resources/image.png", b"\x89PNG\r\n\x1a\nimage-bytes")
    return original


@pytest.mark.parametrize(
    "member",
    ["trace.trace", "trace.network", "resources/dom.html", "resources/source.py"],
)
def test_redact_trace_with_secret_in_any_member_preserves_original_and_removes_secret(
    tmp_path: Path, member: str
) -> None:
    """Scan event parameters, network, DOM resources and source bodies equally.

    :param tmp_path: Real runner-owned temporary directory.
    :param member: Original member containing the synthetic private value.
    :return: None after exact original and harmless binary member preservation.
    """
    original = _original(tmp_path, member)
    before = original.read_bytes()
    public = tmp_path / "public.zip"
    result = trace.redact_trace(original, public, {_SECRET})
    assert original.read_bytes() == before
    assert result["original_sha256"] == hashlib.sha256(before).hexdigest()
    assert result["redacted_members"] == 1
    with zipfile.ZipFile(public) as archive:
        assert all(
            _SECRET.encode() not in archive.read(name) for name in archive.namelist()
        )
        assert archive.read("resources/image.png") == b"\x89PNG\r\n\x1a\nimage-bytes"


@pytest.mark.parametrize(
    "name",
    ["../secret", "/absolute/path", "resources/../../escape", "resources\\escape"],
)
def test_redact_trace_with_unsafe_archive_member_rejects(
    tmp_path: Path, name: str
) -> None:
    """Refuse unsafe archive topology rather than publish a partial derivative.

    :param tmp_path: Actual runner-owned temporary directory.
    :param name: Deliberately unsafe ZIP member.
    :return: None after unsafe original is rejected.
    """
    original = _original(tmp_path, name)
    with pytest.raises(ValueError):
        trace.redact_trace(original, tmp_path / "public.zip", {_SECRET})


def test_redact_trace_with_secret_in_binary_member_fails_closed(tmp_path: Path) -> None:
    """Do not corrupt or silently publish binary content containing a secret.

    :param tmp_path: Actual runner-owned temporary directory.
    :return: None when the unsafe binary acquisition remains private.
    """
    original = _original(
        tmp_path, "resources/binary.bin", b"\xff\xfe" + _SECRET.encode()
    )
    with pytest.raises(ValueError):
        trace.redact_trace(original, tmp_path / "public.zip", {_SECRET})


def test_redact_trace_with_existing_destination_never_overwrites(
    tmp_path: Path,
) -> None:
    """Preserve already acquired public evidence on a repeated invocation.

    :param tmp_path: Actual runner-owned temporary directory.
    :return: None after exclusive-create rejects overwriting existing bytes.
    """
    original = _original(tmp_path)
    public = tmp_path / "public.zip"
    public.write_bytes(b"original evidence")
    with pytest.raises(FileExistsError):
        trace.redact_trace(original, public, {_SECRET})
    assert public.read_bytes() == b"original evidence"


@pytest.mark.parametrize("encoded", ["json", "form"])
def test_redact_trace_with_escaped_event_or_form_value_removes_encoded_secret(
    tmp_path: Path, encoded: str
) -> None:
    """Remove encoded values as well as their unescaped representation.

    :param tmp_path: Actual runner-owned temporary directory.
    :param encoded: Actual JSON-string or form-value representation.
    :return: None after encoded private value is absent from the derivative.
    """
    secret = 'fictional "private" token with spaces'
    value = json.dumps(secret)[1:-1] if encoded == "json" else quote_plus(secret)
    original = _original(tmp_path, "trace.trace", value.encode())
    public = tmp_path / "public.zip"
    result = trace.redact_trace(original, public, {secret})
    assert result["redacted_members"] == 1
    with zipfile.ZipFile(public) as archive:
        assert value.encode() not in archive.read("trace.trace")
