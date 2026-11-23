"""AT lifecycle hooks; behave-django --simple supplies transactional isolation."""

import logging

logger = logging.getLogger(__name__)


def django_ready(context) -> None:
    """Expose a real Django client after behave-django prepares the test case.

    :param context: Behave context with context.test from the simple runner.
    :return: None.
    :raises RuntimeError: If the Django test case was not initialized.
    """
    if not hasattr(context, "test"):
        raise RuntimeError("Run AT with manage.py behave --simple")
    context.client = context.test.client
    logger.info("AT django_ready | entry | scenario=%s", context.scenario.name)
