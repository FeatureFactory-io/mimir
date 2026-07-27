"""
Guest read vs login-required routing for FOB browser views.
"""

import logging
from functools import wraps

from django.contrib.auth.views import redirect_to_login

logger = logging.getLogger(__name__)

GUEST_READ_HTTP_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def guest_read_or_login_required(view_func):
    """Allow anonymous GET when the view enforces can_view; require login for mutations.

    :param view_func: Django view callable.
    :returns: Wrapped view.
    """

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user_label = (
            request.user.username
            if request.user.is_authenticated
            else "anonymous"
        )
        if request.method in GUEST_READ_HTTP_METHODS:
            logger.info(
                "guest_read allow method=%s path=%s user=%s",
                request.method,
                request.path,
                user_label,
            )
            return view_func(request, *args, **kwargs)

        if request.user.is_authenticated:
            logger.info(
                "guest_read authenticated mutation method=%s path=%s user=%s",
                request.method,
                request.path,
                user_label,
            )
            return view_func(request, *args, **kwargs)

        logger.info(
            "guest_read redirect login method=%s path=%s user=anonymous",
            request.method,
            request.path,
        )
        return redirect_to_login(request.get_full_path())

    return _wrapped
