"""Private loopback HTTP responder for real provider-SDK unit transport."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import cast

import httpx

_MAX_BODY_BYTES = 64 * 1024
_SOCKET_TIMEOUT_SECONDS = 3
_SHUTDOWN_TIMEOUT_SECONDS = 3
_POLL_SECONDS = 0.01


class _ProviderServer(ThreadingHTTPServer):
    """Own the unit policy and one random loopback listener."""

    def __init__(self, respond: Callable[[httpx.Request], httpx.Response]) -> None:
        """Bind only a private local endpoint after validating the response policy.

        :param respond: Unit response policy. Example: lambda request: httpx.Response(200).
        :return: None after binding an ephemeral loopback port.
        :raises TypeError: The response policy is not callable.
        :raises OSError: The private socket cannot be allocated.
        """
        if not callable(respond):
            raise TypeError("A callable unit provider response policy is required.")
        self.respond = respond
        super().__init__(("127.0.0.1", 0), _ProviderHandler)


class _ProviderHandler(BaseHTTPRequestHandler):
    """Translate actual HTTP bytes to the SDK-independent unit response policy."""

    def setup(self) -> None:
        """Bound an accepted connection before reading request headers or body.

        :return: None after normal request-handler setup.
        :raises OSError: An accepted socket cannot be configured.
        """
        self.request.settimeout(_SOCKET_TIMEOUT_SECONDS)
        super().setup()

    def do_POST(self) -> None:
        """Serve one bounded real request without exposing unit credentials.

        :return: None after emitting a complete HTTP response.
        :raises OSError: The caller disconnects or the bounded socket times out.
        """
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 <= length <= _MAX_BODY_BYTES:
            self.send_error(413)
            return
        server = cast(_ProviderServer, self.server)
        request = httpx.Request("POST", self.path, content=self.rfile.read(length))
        response = server.respond(request)
        self.send_response(response.status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response.content)))
        self.end_headers()
        self.wfile.write(response.content)

    def log_message(self, format_string: str, *args: object) -> None:
        """Keep HTTP diagnostics and dummy authorization out of captured output.

        :param format_string: Standard server diagnostic template, deliberately unused.
        :param args: Standard template arguments, deliberately unused.
        :return: None without writing request metadata.
        """


@contextmanager
def provider_http_server(
    respond: Callable[[httpx.Request], httpx.Response],
) -> Iterator[str]:
    """Serve a bounded real loopback endpoint, closing on every exit path.

    :param respond: Unit response policy. Example: lambda request: httpx.Response(200).
    :return: Private base URL. Example: http://127.0.0.1:49152/v1.
    :raises TypeError: The response policy is not callable.
    :raises RuntimeError: A bounded server lifetime cannot be closed.
    """
    with _ProviderServer(respond) as server:
        worker = Thread(
            target=server.serve_forever, kwargs={"poll_interval": _POLL_SECONDS}
        )
        worker.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}/v1"
        finally:
            server.shutdown()
            worker.join(timeout=_SHUTDOWN_TIMEOUT_SECONDS)
            if worker.is_alive():
                raise RuntimeError("The owned provider endpoint failed to stop.")
