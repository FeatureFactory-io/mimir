"""Private one-shot staging verification without a second Django interpreter.

The Unix socket is inside the positively owned, mode0700 companion scope. No
HTTP route, application code, provider or browser action is replaced.
"""

from __future__ import annotations

import json
import logging
import os
import re
import socket
import stat
from collections.abc import Callable
from pathlib import Path
from threading import Thread

logger = logging.getLogger(__name__)
_PACKET_LIMIT = 1024
_IO_TIMEOUT_SECONDS = 90
_ACCEPT_TIMEOUT_SECONDS = 660
_FAILURE = b'{"status":"FAILED"}'


def private_path(root: Path, nonce: str) -> Path:
    """Check private process ownership before addressing a socket.

    :param root: Existing mode0700 scope directory; symlinks are forbidden.
    :param nonce: Exactly 32 lowercase hexadecimal owner digits.
    :return: Fixed socket path inside the validated scope.
    :raises ValueError: Identity, directory type, permissions or owner differs.
    """
    if not isinstance(nonce, str) or re.fullmatch(r"[0-9a-f]{32}", nonce) is None:
        raise ValueError("Invalid private verification owner identity.")
    metadata = root.lstat()
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o700
        or (metadata.st_uid, metadata.st_gid) != (os.geteuid(), os.getegid())
    ):
        raise ValueError("Private verification scope ownership differs.")
    return root / "verify.sock"


def packet(value: dict[str, str]) -> bytes:
    """Encode one closed small IPC message without process or database metadata.

    :param value: Internally constructed nonce/status-only message.
    :return: Canonical JSON bytes, e.g. a single exact nonce field.
    """
    return json.dumps(value, separators=(",", ":")).encode("ascii")


def receive(connection: socket.socket) -> bytes:
    """Read one finite packet ending with the sender's write shutdown.

    :param connection: Actual bounded Unix peer connection.
    :return: At most1024 bytes after actual EOF.
    :raises ValueError: Empty or excessive data is received.
    :raises OSError: Peer exchange times out or fails.
    """
    data = bytearray()
    while len(data) <= _PACKET_LIMIT:
        chunk = connection.recv(_PACKET_LIMIT + 1 - len(data))
        if not chunk:
            if not data:
                raise ValueError("Empty private verification packet.")
            return bytes(data)
        data.extend(chunk)
    raise ValueError("Private verification packet exceeded its bound.")


def remove_owned_socket(path: Path, identity: tuple[int, int]) -> None:
    """Remove only the exact inode bound by this worker.

    :param path: Fixed private socket name.
    :param identity: Device/inode recorded after successful bind.
    :return: None; an unexpected replacement is preserved.
    """
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return
    if (metadata.st_dev, metadata.st_ino) == identity and stat.S_ISSOCK(
        metadata.st_mode
    ):
        path.unlink()
    else:
        logger.error("Private verification socket identity changed; retaining path")


def respond(connection: socket.socket, nonce: str, verify: Callable[[], None]) -> None:
    """Execute the original oracle only after this run's exact request matches.

    :param connection: Actual accepted peer inside the private scope.
    :param nonce: This server's immutable owner identity.
    :param verify: Original loaded-worker ORM/mail verification.
    :return: None after a closed success/failure response; errors contain no text.
    """
    response = _FAILURE
    try:
        connection.settimeout(_IO_TIMEOUT_SECONDS)
        if receive(connection) != packet({"nonce": nonce}):
            raise ValueError("Private verification request identity differs.")
        logger.info("Starting same-worker staging database verification")
        verify()
        response = packet({"status": "CASE_VERIFIED", "nonce": nonce})
        logger.info("Same-worker staging database verification passed")
    except Exception:  # noqa: BLE001 -- arbitrary oracle failures must not leak row text.
        logger.info("Same-worker staging database verification failed closed")
    try:
        connection.sendall(response)
    except OSError:
        logger.info("Private verification peer disconnected before confirmation")


def serve(
    listener: socket.socket,
    path: Path,
    nonce: str,
    verify: Callable[[], None],
    identity: tuple[int, int],
) -> None:
    """Serve one attempt and release only this worker's socket.

    :param listener: Already bound mode0600 socket, never a public port.
    :param path: Private socket file to release on completion.
    :param nonce: Immutable manifest nonce.
    :param verify: Original full loaded-worker verification callback.
    :param identity: Bound device/inode captured before the thread handoff.
    :return: None after one attempt or bounded startup inactivity.
    """
    try:
        with listener:
            connection, _ = listener.accept()
            with connection:
                respond(connection, nonce, verify)
    except OSError:
        logger.info("Private staging verification listener failed closed")
    finally:
        remove_owned_socket(path, identity)


def start_server(root: Path, nonce: str, verify: Callable[[], None]) -> Thread:
    """Start one private verification request in the loaded serving process.

    :param root: Private directory owned by this process's effective UID/GID.
    :param nonce: Exact fresh manifest owner identity, for example 32 hex digits.
    :param verify: Original full ORM/mail oracle; errors must fail closed.
    :return: Started daemon worker after the private socket is bound.
    :raises ValueError: Scope, identity or existing socket is unsafe.
    """
    path = private_path(root, nonce)
    if not callable(verify):
        raise TypeError("Private verification callback is not callable.")
    listener = socket.socket(socket.AF_UNIX)
    identity = None
    try:
        listener.bind(str(path))
        metadata = path.lstat()
        identity = (metadata.st_dev, metadata.st_ino)
        os.chmod(path, 0o600)
        listener.settimeout(_ACCEPT_TIMEOUT_SECONDS)
        listener.listen(1)
        server = Thread(
            target=serve, args=(listener, path, nonce, verify, identity), daemon=True
        )
        server.start()
        return server
    except Exception:
        listener.close()
        if identity is not None:
            remove_owned_socket(path, identity)
        raise


def request_verification(root: Path, nonce: str) -> None:
    """Ask the same loaded worker to execute the unchanged final oracle once.

    :param root: Same private scope directory used by the serving worker.
    :param nonce: Exact current manifest owner identity.
    :return: None only after the worker confirms this nonce's real oracle.
    :raises ValueError: Scope, response, identity or verification differs.
    :raises OSError: The bounded local socket exchange fails.
    """
    path = private_path(root, nonce)
    metadata = path.lstat()
    if (
        not stat.S_ISSOCK(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or (metadata.st_uid, metadata.st_gid) != (os.geteuid(), os.getegid())
    ):
        raise ValueError("Private verification socket ownership differs.")
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(_IO_TIMEOUT_SECONDS)
        connection.connect(str(path))
        connection.sendall(packet({"nonce": nonce}))
        connection.shutdown(socket.SHUT_WR)
        response = receive(connection)
    if response != packet({"status": "CASE_VERIFIED", "nonce": nonce}):
        raise ValueError("Same-worker staging verification failed.")


def main() -> None:
    """Dispatch only this owned summary case's stdlib-only local request.

    :return: None after actual same-worker verification succeeds.
    :raises ValueError: Actual mounted phase/case identity is not summary acceptance.
    :raises OSError: The original private request fails or times out.
    """
    manifest = json.loads(Path("/runtime/run.json").read_text())
    if (
        manifest.get("suite_phase") != "summary-acceptance"
        or manifest.get("saga_case") != "summary-acceptance"
    ):
        raise ValueError("Same-worker verification requires the exact summary case.")
    request_verification(Path("/experts-scope"), manifest["nonce"])


if __name__ == "__main__":
    main()
