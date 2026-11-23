from __future__ import annotations

"""S22-only Django-client assertions; no browser activation or domain mocks."""
from behave import then
from behave.runner import Context


@then("Sam Kim's positive Karma identity is shown")
def sam_positive_identity(context: Context) -> None:
    """Check Sam's identity using the actual response and Cedar oracle.

    :param context: Transactional AT context. Example: response for /experts/skim/.
    :return: None. Example: status 200, Sam Kim, 4,800 and Research verified.
    :raises AssertionError: If positive identity is absent or incorrect.
    """
    raise NotImplementedError()


@then('the evidence section says "{message}"')
def evidence_section_says(context: Context, message: str) -> None:
    """Check exact empty evidence text inside the real evidence section.

    :param context: Real response context. Example: Sam's production profile.
    :param message: Required text. Example: "No public released playbooks to show".
    :return: None. Example: exact message and absence of evidence links verified.
    :raises AssertionError: If text is misplaced, absent or evidence links exist.
    """
    raise NotImplementedError()
