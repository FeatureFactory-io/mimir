"""Explicit companion entrypoint; image check precedes Django and scope precedes SQL writes."""

from __future__ import annotations

import os
import subprocess
import sys

_GUNICORN = [
    "gunicorn",
    "mimir.wsgi:application",
    "--workers",
    "1",
    "--threads",
    "4",
    "--bind",
    "0.0.0.0:8443",
    "--certfile",
    "/tls/server.crt",
    "--keyfile",
    "/tls/server.key",
    "--timeout",
    "90",
]


def main() -> None:
    """Verify code, initialize only the positively owned DB, then serve TLS.

    :return: Does not return after successful Gunicorn exec.
    :raises CalledProcessError: Image/scope/import/static preparation fails closed.
    """
    subprocess.run([sys.executable, "/runtime/verify_image.py"], check=True)
    subprocess.run(
        [
            sys.executable,
            "manage.py",
            "shell",
            "--no-imports",
            "-c",
            "from bootstrap import initialize; initialize()",
        ],
        check=True,
    )

    os.execvp(_GUNICORN[0], _GUNICORN)


if __name__ == "__main__":
    main()
