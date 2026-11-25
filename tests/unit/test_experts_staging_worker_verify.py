"""Real private IPC and failure controls for the already loaded staging worker."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

_RUNTIME = Path(__file__).resolve().parents[2] / "scripts/experts-staging"
sys.path.insert(0, str(_RUNTIME))
import remote
import suite_worker_verify as worker

_NONCE = "c" * 32


@pytest.fixture
def scope() -> Iterator[Path]:
    """Return an actual private owned IPC directory, never a database fixture."""
    with tempfile.TemporaryDirectory(prefix="mimir-verify-", dir="/tmp") as directory:
        root = Path(directory)
        root.chmod(0o700)
        os.chown(root, os.geteuid(), os.getegid())
        yield root


def test_request_verification_with_real_socket_executes_original_callback_once(
    scope: Path,
) -> None:
    calls: list[int] = []
    server = worker.start_server(scope, _NONCE, lambda: calls.append(os.getpid()))
    worker.request_verification(scope, _NONCE)
    server.join(timeout=5)
    assert calls == [os.getpid()] and not server.is_alive()
    assert not (scope / "verify.sock").exists()


def test_request_verification_with_original_oracle_failure_rejects(
    scope: Path,
) -> None:
    def reject() -> None:
        raise AssertionError("PRIVATE_DATABASE_ROW_MUST_NOT_LEAVE_PROCESS")

    server = worker.start_server(scope, _NONCE, reject)
    with pytest.raises(ValueError, match="verification failed") as error:
        worker.request_verification(scope, _NONCE)
    server.join(timeout=5)
    assert "PRIVATE_DATABASE" not in str(error.value)
    assert not server.is_alive()


@pytest.mark.parametrize("nonce", ["", "c" * 31, "z" * 32, "C" * 32, 1, None])
def test_start_server_with_invalid_nonce_rejects_before_callback(
    scope: Path,
    nonce: object,
) -> None:
    with pytest.raises(ValueError):
        worker.start_server(scope, nonce, lambda: pytest.fail("must not execute"))
    assert not list(scope.iterdir())


def test_start_server_with_public_scope_rejects(scope: Path) -> None:
    scope.chmod(0o755)
    with pytest.raises(ValueError):
        worker.start_server(scope, _NONCE, lambda: pytest.fail("must not execute"))


def test_start_server_with_symlink_scope_rejects(scope: Path, tmp_path: Path) -> None:
    link = tmp_path / "link"
    link.symlink_to(scope, target_is_directory=True)
    with pytest.raises(ValueError):
        worker.start_server(link, _NONCE, lambda: pytest.fail("must not execute"))


def test_start_server_with_existing_socket_path_preserves_original(scope: Path) -> None:
    path = scope / "verify.sock"
    path.write_bytes(b"ORIGINAL")
    with pytest.raises((ValueError, OSError)):
        worker.start_server(scope, _NONCE, lambda: pytest.fail("must not execute"))
    assert path.read_bytes() == b"ORIGINAL"


@pytest.mark.parametrize(
    "payload",
    [
        b"not-json",
        b"x" * 1025,
        b'{"nonce":"wrong"}',
        json.dumps({"nonce": _NONCE, "extra": True}).encode(),
    ],
)
def test_server_with_untrusted_packet_rejects_without_oracle(
    scope: Path,
    payload: bytes,
) -> None:
    calls: list[bool] = []
    server = worker.start_server(scope, _NONCE, lambda: calls.append(True))
    with socket.socket(socket.AF_UNIX) as client:
        client.settimeout(5)
        client.connect(str(scope / "verify.sock"))
        client.sendall(payload)
        client.shutdown(socket.SHUT_WR)
        result = client.recv(1024)
    server.join(timeout=5)
    assert result == b'{"status":"FAILED"}' and not calls
    assert not server.is_alive()


def test_request_verification_with_false_success_nonce_rejects(scope: Path) -> None:
    listener = socket.socket(socket.AF_UNIX)
    listener.bind(str(scope / "verify.sock"))
    os.chmod(scope / "verify.sock", 0o600)
    listener.listen(1)

    def lie() -> None:
        with listener, listener.accept()[0] as client:
            client.recv(1024)
            client.sendall(b'{"status":"CASE_VERIFIED","nonce":"wrong"}')

    server = threading.Thread(target=lie, daemon=True)
    server.start()
    with pytest.raises(ValueError):
        worker.request_verification(scope, _NONCE)
    server.join(timeout=5)


def test_worker_module_with_isolated_import_does_not_initialize_django() -> None:
    script = f"import sys; sys.path.insert(0,{str(_RUNTIME)!r}); import suite_worker_verify; assert 'django' not in sys.modules"
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-c", script],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode()


@pytest.mark.parametrize(
    "case", ["core", "nomination", "guest-public", "summary-acceptance"]
)
def test_verify_case_effects_with_summary_uses_loaded_worker_only(
    scope: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(remote, "docker", lambda *args: calls.append(args))
    manifest = {"suite_phase": case, "saga_case": case}
    remote.verify_case_effects(scope, {"web": "exact-owned-web"}, manifest)
    prefix = (scope, "exec", "exact-owned-web", "python")
    expected = (
        ("/runtime/suite_worker_verify.py",)
        if case == "summary-acceptance"
        else (
            "manage.py",
            "shell",
            "--no-imports",
            "-c",
            "from suite_runtime import verify; verify()",
        )
    )
    assert calls == [(*prefix, *expected)]
