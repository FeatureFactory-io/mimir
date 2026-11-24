"""Real anonymous Chromium certification of generic expert rejection pages."""

from __future__ import annotations

from http import HTTPStatus

import pytest
from django.conf import settings
from django.core.mail import EmailMessage
from playwright.sync_api import Page, expect

from tests.integration.test_experts_not_found import (
    _FORBIDDEN_HOOKS,
    _assert_sensitive_values_absent,
    _state_snapshot,
)
from tests.integration.test_experts_not_found import (
    rejection_dataset as _rejection_dataset,
)
from tests.support.experts_data import CedarDataset

_REJECTED_SUBJECTS = ("no-such-cedar-user", "nberg")
rejection_dataset = _rejection_dataset


@pytest.mark.e2e
@pytest.mark.django_db(transaction=True)
def test_expert_detail_with_missing_or_zero_karma_subject_browser_returns_404(
    page: Page,
    live_server_url: str,
    rejection_dataset: CedarDataset,
    mailoutbox: list[EmailMessage],
) -> None:
    """Certify both anonymous rejection pages with the existing browser lifecycle.

    :param page: Isolated Playwright page, e.g. a fresh anonymous context.
    :param live_server_url: Function-scoped server origin, e.g. localhost URL.
    :param rejection_dataset: Real missing/Nora/private cases, e.g. persisted Cedar.
    :param mailoutbox: Actual local Django mail capture, e.g. an empty list.
    :return: None after two real404s, usable recovery and unchanged state.
    :raises AssertionError: If HTTP, presentation, privacy or persistence differs.
    """
    before, prior_mail = _state_snapshot(), tuple(mailoutbox)
    assert not page.context.cookies()
    presentations = [
        _read_generic_rejection(page, live_server_url, username, rejection_dataset)
        for username in _REJECTED_SUBJECTS
    ]
    assert presentations[0] == presentations[1]
    page.get_by_test_id("expert-unavailable-back-link").click()
    expect(page).to_have_url(f"{live_server_url}/experts/")
    expect(page.get_by_role("heading", name="Experts", exact=True)).to_be_visible()
    if _state_snapshot() != before or tuple(mailoutbox) != prior_mail:
        raise AssertionError("Anonymous browser recovery changed domain state or mail.")
    assert not any(
        cookie["name"] == settings.SESSION_COOKIE_NAME
        for cookie in page.context.cookies()
    )


def _read_generic_rejection(
    page: Page, origin: str, username: str, dataset: CedarDataset
) -> tuple[str, str, str]:
    """Read the actual requested404and inspect its safe, usable recovery controls.

    :param page: Existing anonymous browser page, e.g. no authentication cookie.
    :param origin: Actual Django live-server origin, e.g. localhost URL.
    :param username: One exact rejected subject, e.g. nberg.
    :param dataset: Persisted private fixture probes, e.g. Nora and Maria.
    :return: Generic heading, link name and href, e.g. unavailable/Back/Experts.
    :raises AssertionError: If a response redirects, leaks or disguises its status.
    """
    url = f"{origin}/experts/{username}/"
    response = page.goto(url)
    assert response is not None and response.status == HTTPStatus.NOT_FOUND
    assert response.request.redirected_from is None
    expect(page).to_have_url(url)
    _assert_sensitive_values_absent(page.content(), dataset)
    for hook in _FORBIDDEN_HOOKS:
        expect(page.get_by_test_id(hook)).to_have_count(0)
    expect(page.locator('a[href^="mailto:"]')).to_have_count(0)
    heading = page.get_by_test_id("expert-unavailable")
    back = page.get_by_test_id("expert-unavailable-back-link")
    expect(heading).to_be_visible()
    expect(heading).to_have_text("Expert unavailable")
    expect(back).to_be_visible()
    expect(back).to_have_accessible_name("Back to Experts")
    expect(back).to_have_attribute("href", "/experts/")
    back.click(trial=True)
    return heading.inner_text(), back.inner_text(), str(back.get_attribute("href"))
