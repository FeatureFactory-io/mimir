from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

from behave import then, when
from behave.runner import Context
from django.contrib.auth import SESSION_KEY
from django.contrib.auth.models import User
from django.core import mail
from django.urls import reverse
from rest_framework.authtoken.models import Token

from methodology.models import (
    AgentInteraction,
    ExpertProfile,
    KarmaAward,
    Playbook,
    ProcessImprovementProposal,
)
from tests.support.experts_data import CedarDataset
from tests.support.experts_html import _parse_root, _walk_elements
from tests.support.experts_privacy import assert_public_response

_MARIA = "mrodriguez"
_PUBLIC_BOOK_ID = 6101
_READ_ONLY_MODELS = (
    User,
    Token,
    Playbook,
    ProcessImprovementProposal,
    KarmaAward,
    ExpertProfile,
    AgentInteraction,
)


@when('anonymous Bob opens "{path}"')
def anonymous_bob_opens(context: Context, path: str) -> None:
    """Log out and request the exact production path.

    :param context: Real AT context, e.g. context.client and cedar_dataset.
    :param path: Local absolute path, e.g. "/experts/mrodriguez/".
    :return: None; context.response contains actual HTTP result.
    :raises ValueError: If the path differs from Maria's exact local public route.
    :raises AssertionError: If probes are absent or the request changes private state.
    """
    if path != reverse("expert_detail", args=[_MARIA]):
        raise ValueError("Privacy acceptance requires Maria's local public route.")
    _persisted_private_sentinels(context.cedar_dataset)
    context.execute_steps("Given an anonymous AT visitor")
    before = _snapshot_private_request_models()
    mail_before = tuple(getattr(mail, "outbox", ()))
    context.execute_steps(f'When the AT visitor requests "{path}"')
    request = context.response.wsgi_request
    if request.user.is_authenticated or SESSION_KEY in request.session:
        raise AssertionError("Public privacy request must remain anonymous.")
    if _snapshot_private_request_models() != before:
        raise AssertionError("Public privacy request changed persisted records.")
    if tuple(getattr(mail, "outbox", ())) != mail_before:
        raise AssertionError("Public privacy request changed the mail outbox.")


@then('the response omits "{value}"')
@then('it omits "{value}"')
def response_omits(context: Context, value: str) -> None:
    """Assert exact sentinel exclusion from full response markup.

    :param context: Real AT context, e.g. response status 200.
    :param value: Forbidden sentinel, e.g. "Cedar Bid Pricing".
    :return: None; stored fixture exists and sentinel is absent.
    :raises ValueError: If the value is not an original private Cedar probe.
    :raises AssertionError: If fixture evidence is missing or value appears.
    """
    if value not in _persisted_private_sentinels(context.cedar_dataset):
        raise ValueError("Privacy acceptance requires an original private Cedar probe.")
    assert_public_response(context.response, context.cedar_dataset, authenticated=False)


@then('no "{test_id}" exists')
def response_has_no_test_id(context: Context, test_id: str) -> None:
    """Use S03 shared HTML parser to check an absent control.

    :param context: Real AT context, e.g. guest detail response.
    :param test_id: Forbidden hook, e.g. "profile-token-field".
    :return: None; matching element count is zero.
    :raises ValueError: If the test ID is blank or not text.
    :raises AssertionError: If the forbidden control exists.
    """
    if not isinstance(test_id, str) or not test_id.strip():
        raise ValueError("A nonblank private-control test ID is required.")
    nodes = _walk_elements(_parse_root(context.response.content))
    if any(("data-testid", test_id) in node.attributes for node in nodes):
        raise AssertionError("Public profile contains the prohibited private control.")


def _persisted_private_sentinels(dataset: CedarDataset) -> tuple[str, str, str]:
    """Verify the three original private probes without reloading the baseline.

    :param dataset: Existing transactional Cedar background, e.g. Maria and book 6101.
    :return: Privately held probes, e.g. the book title, PIP title and API token.
    :raises AssertionError: If any probe lacks its actual private ORM record.
    """
    people = cast(Sequence[Mapping[str, object]], dataset.oracle["people"])
    person = next(row for row in people if row["username"] == _MARIA)
    book_title = cast(Sequence[str], person["private_playbooks"])[0]
    pip_title, token = cast(str, person["private_pip"]), cast(
        str, person["private_token"]
    )
    author_id = dataset.user_ids[_MARIA]
    exists = (
        Playbook.objects.filter(
            author_id=author_id, name=book_title, visibility="private", status="draft"
        ).exists(),
        ProcessImprovementProposal.objects.filter(
            created_by_id=author_id,
            playbook_id=_PUBLIC_BOOK_ID,
            title=pip_title,
            status=ProcessImprovementProposal.STATUS_DRAFT,
        ).exists(),
        Token.objects.filter(user_id=author_id, key=token).exists(),
    )
    if not all(exists):
        raise AssertionError("Original private Cedar probes are not persisted.")
    return book_title, pip_title, token


def _snapshot_private_request_models() -> tuple[tuple[tuple[object, ...], ...], ...]:
    """Capture complete rows without serializing or logging their private values.

    :return: Ordered immutable ORM snapshots, e.g. awards and token records.
    """
    return tuple(
        tuple(model.objects.order_by("pk").values_list()) for model in _READ_ONLY_MODELS
    )
