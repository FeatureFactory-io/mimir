from __future__ import annotations

"""Real Cedar release-case construction for pytest and AT."""
from dataclasses import dataclass
from typing import TYPE_CHECKING
from django.test import Client

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser
    from methodology.models import Playbook


@dataclass(frozen=True)
class NoraReleaseCase:
    """Hold the independently restored real Cedar publication case.

    :param author: Persisted nberg user. Example: Nora.
    :param playbook: Persisted draft 6302. Example: Accessible Workshop Starter.
    :param client: Authenticated real Django client. Example: Nora's session.
    """

    author: AbstractBaseUser
    playbook: Playbook
    client: Client


def build_nora_release_case() -> NoraReleaseCase:
    """Load the shared Cedar baseline and prepare its normal release prerequisites.

    Use S03's real loader and fixed Cedar identities. Keep Nora at zero points.
    If adding a required workflow increments the draft minor version, retain that
    real behavior; the first major must still be exactly 1.0. Never call a live
    release/acceptance service while constructing historical baseline objects.

    :return: Isolated real case. Example: Nora, draft 6302 and authenticated client.
    :raises ValueError: If baseline records or totals do not match the contract.
    """
    raise NotImplementedError()
