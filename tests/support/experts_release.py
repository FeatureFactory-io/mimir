from __future__ import annotations

from methodology.models import Playbook, ProcessImprovementProposal

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


def prepare_reviewed_next_major_pip(
    playbook: Playbook, submitter: AbstractBaseUser
) -> ProcessImprovementProposal:
    """Prepare real reviewed ADD Activity fixture without invoking Galdr.

    Use real draft/change builders; set reviewed metadata only as explicit test
    setup. Do not finalize, publish, award, reset Cedar or set numeric versions.
    :param playbook: Released target as Playbook. Example: Nora's 6302 at v1.0.
    :param submitter: Existing actor. Example: Cedar Maria.
    :return: Undecided reviewed PIP. Example: one ADD Activity under target workflow.
    :raises ValueError: If the target lacks valid released/workflow prerequisites.
    """
    raise NotImplementedError()
