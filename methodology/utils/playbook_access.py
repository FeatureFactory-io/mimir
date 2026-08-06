"""
Shared playbook access helpers for views and API layers.
"""

import logging

from django.http import Http404
from django.shortcuts import get_object_or_404

from methodology.models import Playbook

logger = logging.getLogger(__name__)


def playbook_readable_or_404(request, pk):
    """Return playbook if the logged-in user may view it; else Http404.

    Does not distinguish between "not found" and "not accessible" — both return 404
    to avoid revealing whether a private playbook exists.

    :param request: Django HTTP request.
    :param pk: int Playbook primary key.
    :returns: Playbook instance.
    :raises Http404: If playbook does not exist or is not accessible to request.user.

    Example return: Playbook(id=3, name="FeatureFactory", visibility="public", ...)
    """
    playbook = get_object_or_404(Playbook, pk=pk)
    user_label = (
        request.user.username
        if request.user.is_authenticated
        else "anonymous"
    )
    if not playbook.can_view(request.user):
        logger.info(
            "User %s denied view on playbook id=%s (visibility=%s status=%s)",
            user_label,
            pk,
            playbook.visibility,
            playbook.status,
        )
        raise Http404()
    return playbook


def playbook_can_submit_pip(playbook, user) -> bool:
    """True when an owned released playbook owner may start a PIP from the UI."""
    return (
        user.is_authenticated
        and playbook.source == "owned"
        and playbook.author_id == user.id
        and playbook.is_released
    )
