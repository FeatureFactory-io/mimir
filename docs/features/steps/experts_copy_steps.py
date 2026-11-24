"""Supplementary Django-client checks for the browser copy contract."""

from __future__ import annotations

import logging
import re
from html import unescape
from http import HTTPStatus
from uuid import uuid4

from behave import then, when
from behave.runner import Context
from django.test import Client
from django.urls import reverse

from methodology.models import EventChannel, KarmaAward
from methodology.services.copy_prompt_service import CopyPromptService
from methodology.services.experts_service import ExpertsService
from tests.support.experts_html import find_by_test_id

logger = logging.getLogger(__name__)
_ACTIVITY_ID = 6203
_MARIA = "mrodriguez"
_MIKE = "mchen"


@when("she successfully copies Mike's public released activity 6203")
def reports_successful_activity_copy(context: Context) -> None:
    """Exercise rendered prompt and real successful-action receipt boundary.

    :param context: Real Django-client AT context. Example: Maria session.
    :return: None with the rendered page and applied receipt's action UUID.
    :raises AssertionError: If authorized prompt or receipt is unavailable.
    """
    dataset = context.cedar_dataset
    activity = dataset.activities_by_pk[_ACTIVITY_ID]
    path = reverse(
        "activity_detail",
        args=[activity.workflow.playbook_id, activity.workflow_id, activity.pk],
    )
    client = Client(enforce_csrf_checks=True)
    client.cookies.update(context.client.cookies)
    page = client.get(path)
    assert page.status_code == HTTPStatus.OK, "The released activity did not load."
    assert page.wsgi_request.user == dataset.users_by_username[_MARIA]
    control = find_by_test_id(page.content, "copy-prompt-btn")
    attributes = dict(control.attributes)
    assert control.name == "button" and "data-copy-prompt-trigger" in attributes
    endpoint = attributes["data-copy-receipt-url"]
    assert endpoint == reverse("karma_copy_receipt")
    target = {
        "entity_type": attributes["data-copy-receipt-entity-type"],
        "entity_id": int(attributes["data-copy-receipt-entity-id"]),
    }
    assert target == {"entity_type": "activity", "entity_id": _ACTIVITY_ID}
    action_id = str(uuid4())
    receipt = client.post(
        endpoint,
        {**target, "event_identity": action_id},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=attributes["data-copy-receipt-csrf"],
    )
    assert receipt.status_code == HTTPStatus.OK, "The real copy receipt was rejected."
    assert receipt.json() == {"status": "applied"}
    context.copy_activity_page, context.copy_action_id = page, action_id


@then("the clipboard receives the actual activity prompt")
def actual_activity_prompt_is_the_copy_payload(context: Context) -> None:
    """Check actual server-built copy payload; browser gate proves the clipboard.

    :param context: AT context containing the real rendered prompt. Example: activity 6203.
    :return: None after exact rendered prompt equality. Playwright checks the clipboard.
    :raises AssertionError: If rendered payload differs from CopyPromptService output.
    """
    response = context.copy_activity_page
    source_id = f"copy-prompt-text-activity-{_ACTIVITY_ID}"
    # Django's semantic HTML parser normalizes the Markdown whitespace.
    matches = re.findall(
        rf'<textarea\b(?=[^>]*\sdata-testid="{source_id}")'
        r"(?=[^>]*\sdata-copy-prompt-source\b)[^>]*>(.*?)</textarea>",
        response.content.decode(response.charset),
        flags=re.DOTALL,
    )
    assert len(matches) == 1, (
        "Expected one rendered clipboard source for activity 6203."
    )
    activity = context.cedar_dataset.activities_by_pk[_ACTIVITY_ID]
    expected = CopyPromptService.build_activity_prompt(activity)
    assert expected and unescape(matches[0]) == expected, "The rendered prompt differs."
    logger.info(
        "Copy server acceptance | rendered prompt matched | activity_id=%s", activity.pk
    )


@then("Maria's total becomes {maria_total:d} and Mike's becomes {mike_total:d}")
def copy_pair_totals_match_cedar(
    context: Context, maria_total: int, mike_total: int
) -> None:
    """Check real ledger projections against EV01.

    :param context: AT context with real Cedar actors. Example: Maria and Mike.
    :param maria_total: Expected live projection for Maria. Example: 8205.
    :param mike_total: Expected live projection for Mike. Example: 12455.
    :return: None after both numeric total assertions.
    :raises AssertionError: If either projected total differs.
    """
    users = context.cedar_dataset.users_by_username
    service = ExpertsService()
    maria = service.project_user(users[_MARIA].pk)
    mike = service.project_user(users[_MIKE].pk)
    assert (maria.total_points, mike.total_points) == (maria_total, mike_total), (
        f"Unexpected copy totals: Maria {maria.total_points}, Mike {mike.total_points}."
    )


@then("both awards belong to Development")
def copy_pair_category_is_development(context: Context) -> None:
    """Check the two new immutable category snapshots.

    :param context: AT context carrying the receipt identity. Example: EV01 action UUID.
    :return: None after exact two-recipient Development assertions.
    :raises AssertionError: If award attribution differs.
    """
    users = context.cedar_dataset.users_by_username
    maria_id, mike_id = users[_MARIA].pk, users[_MIKE].pk
    identity = (
        f"consumption:{EventChannel.GUI_COPY}:{maria_id}:{context.copy_action_id}"
    )
    awards = list(
        KarmaAward.objects.filter(event_identity=identity).values_list(
            "recipient_id", "category", "event_channel"
        )
    )
    assert len(awards) == 2 and set(awards) == {
        (maria_id, "development", EventChannel.GUI_COPY),
        (mike_id, "development", EventChannel.GUI_COPY),
    }, "Expected exactly two Development GUI copy awards for Maria and Mike."
