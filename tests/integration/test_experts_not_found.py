"""Real missing/zero-contribution rejection contracts on the public route."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import EmailMessage
from django.db import connection
from django.http import HttpResponse
from django.test import Client
from django.test.utils import CaptureQueriesContext
from rest_framework.authtoken.models import Token

from methodology.models import (
    AgentInteraction,
    ExpertProfile,
    KarmaAward,
    Playbook,
    ProcessImprovementProposal,
)
from methodology.services.experts_service import ExpertsService
from tests.support.experts_data import CedarDataset
from tests.support.experts_html import element_text, find_by_test_id
from tests.support.experts_logs import capture_experts_logs
from tests.support.log_story import assert_log_story

pytestmark = pytest.mark.django_db
_REJECTED_SUBJECTS = ("no-such-cedar-user", "nberg")
_READ_ONLY_MODELS = (
    User,
    Token,
    Playbook,
    ProcessImprovementProposal,
    KarmaAward,
    ExpertProfile,
    AgentInteraction,
)
_WRITE_PREFIXES = ("INSERT", "UPDATE", "DELETE", "REPLACE", "CREATE", "ALTER", "DROP")
_PRIVATE_BOOK_BODY = "S21 confidential pricing rationale for the Cedar bid."
_PRIVATE_PIP_BODY = "S21 confidential staffing rationale for the Cedar bid."
_FORBIDDEN_HOOKS = (
    "expert-name",
    "expert-karma-total",
    "expert-read-column",
    "expert-context-rail",
    "expert-contribution-summary",
    "expert-public-playbooks",
    "profile-api-token",
    "profile-token-field",
    "profile-token-toggle",
    "profile-token-copy",
    "profile-token-regenerate-form",
    "profile-edit-btn",
    "profile-email",
)


@pytest.fixture
def rejection_dataset(cedar_dataset: CedarDataset) -> CedarDataset:
    """Retain the baseline and give existing private rows distinct body probes.

    :param cedar_dataset: Real imported Cedar history, e.g. Nora's draft account.
    :return: The same dataset, with test-local private body probes populated.
    :raises AssertionError: If either expected private row is missing.
    """
    maria = cedar_dataset.users_by_username["mrodriguez"]
    books = Playbook.objects.filter(author=maria, visibility="private")
    proposals = ProcessImprovementProposal.objects.filter(
        created_by=maria, status=ProcessImprovementProposal.STATUS_DRAFT
    )
    assert books.update(description=_PRIVATE_BOOK_BODY) == 1
    assert proposals.update(summary=_PRIVATE_PIP_BODY) == 1
    _assert_rejection_preconditions(cedar_dataset)
    return cedar_dataset


@pytest.mark.parametrize("username", _REJECTED_SUBJECTS)
def test_expert_detail_with_missing_or_zero_karma_subject_returns_404(
    client: Client,
    username: str,
    rejection_dataset: CedarDataset,
    mailoutbox: list[EmailMessage],
) -> None:
    """Certify absent and zero-total subjects through the real detail route.

    :param client: Real anonymous Django client, e.g. Client().
    :param username: Exact outline subject, e.g. "nberg".
    :param rejection_dataset: Persisted baseline and private probes, e.g. Nora.
    :param mailoutbox: Actual captured Django messages, e.g. an empty list.
    :return: None after generic404, privacy and unchanged-state assertions pass.
    :raises AssertionError: If eligibility, status or privacy differs.
    """
    response = _read_rejection(client, username, mailoutbox)
    _assert_safe_rejection(response, rejection_dataset)


def test_expert_detail_with_ineligible_subject_hides_account_existence(
    client: Client,
    rejection_dataset: CedarDataset,
    mailoutbox: list[EmailMessage],
) -> None:
    """Compare generic content without exposing whether an account exists.

    :param client: Real anonymous Django client, e.g. Client().
    :param rejection_dataset: Real missing/Nora/private cases, e.g. CedarDataset.
    :param mailoutbox: Captured Django email, e.g. an unchanged empty list.
    :return: None after equivalent generic content and privacy checks.
    :raises AssertionError: If rejection text reveals existence or private data.
    """
    presentations = []
    for username in _REJECTED_SUBJECTS:
        response = _read_rejection(client, username, mailoutbox)
        _assert_safe_rejection(response, rejection_dataset)
        presentations.append(_rejection_presentation(response))
    assert presentations[0] == presentations[1]


@pytest.mark.parametrize("username", _REJECTED_SUBJECTS)
def test_expert_detail_with_rejected_subject_log_story_reject(
    client: Client,
    caplog: pytest.LogCaptureFixture,
    username: str,
    rejection_dataset: CedarDataset,
    mailoutbox: list[EmailMessage],
) -> None:
    """Prove the correlated public boundary tells the same safe rejection story.

    :param client: Real anonymous Django client, e.g. Client().
    :param caplog: Actual logger capture, e.g. INFO boundary records.
    :param username: Exact rejection subject, e.g. "nberg".
    :param rejection_dataset: Real baseline and private probes, e.g. CedarDataset.
    :param mailoutbox: Actual captured messages, e.g. an empty list.
    :return: None after safe entry, generic rejection and404exit are proven.
    :raises AssertionError: If the boundary distinguishes existence or leaks data.
    """
    with capture_experts_logs(
        caplog, ("methodology.expert_views", "methodology.services.experts_service")
    ):
        response = _read_rejection(client, username, mailoutbox)
    _assert_safe_rejection(response, rejection_dataset)
    _assert_rejection_log_story(caplog, rejection_dataset)


def _assert_rejection_preconditions(dataset: CedarDataset) -> None:
    """Verify the two subjects really differ while Sam stays a positive contributor.

    :param dataset: Imported real rows, e.g. nberg exists and the missing name does not.
    :return: None after missing, zero-total, draft and positive-no-release facts pass.
    :raises AssertionError: If a fixture cannot expose the intended policy mistake.
    """
    assert not User.objects.filter(username=_REJECTED_SUBJECTS[0]).exists()
    nora = dataset.users_by_username["nberg"]
    assert User.objects.filter(pk=nora.pk, username="nberg").exists()
    assert nora.email and nora.get_full_name()
    assert not KarmaAward.objects.filter(recipient=nora).exists()
    projection = ExpertsService().project_user(nora.pk)
    assert projection.total_points == 0 and projection.primary_category is None
    assert Playbook.objects.filter(author=nora, status="draft").exists()
    sam = dataset.users_by_username["skim"]
    assert ExpertsService().project_user(sam.pk).total_points == 4800
    assert not Playbook.objects.filter(
        author=sam, visibility="public", status="released"
    ).exists()
    assert Token.objects.filter(user=dataset.users_by_username["mrodriguez"]).exists()


def _read_rejection(
    client: Client, username: str, mailoutbox: list[EmailMessage]
) -> HttpResponse:
    """Capture the actual anonymous GET and prohibit any state mutation.

    :param client: Real Django client, e.g. an unauthenticated session.
    :param username: Fixed rejected route subject, e.g. "nberg".
    :param mailoutbox: Actual Django messages, e.g. [].
    :return: Actual404response, e.g. the generic Experts unavailable page.
    :raises AssertionError: If GET writes SQL, changes models/mail or authenticates.
    """
    before = _state_snapshot()
    prior_mail = tuple(mailoutbox)
    with CaptureQueriesContext(connection) as queries:
        response = client.get(
            f"/experts/{username}/", HTTP_X_REQUEST_ID="cedar-s21-rejection"
        )
    if any(row["sql"].lstrip().upper().startswith(_WRITE_PREFIXES) for row in queries):
        raise AssertionError("Public rejection executed a SQL write.")
    if _state_snapshot() != before or tuple(mailoutbox) != prior_mail:
        raise AssertionError("Public rejection changed persisted state or email.")
    assert not response.wsgi_request.user.is_authenticated
    assert settings.SESSION_COOKIE_NAME not in client.cookies
    return response


def _state_snapshot() -> tuple[list[dict[str, Any]], ...]:
    """Read complete ordered field values without exposing them in failure output.

    :return: Seven full model snapshots, e.g. ordered award rows plus account state.
    :raises RuntimeError: If the runner-owned database is unavailable.
    """
    return tuple(
        list(model.objects.order_by("pk").values()) for model in _READ_ONLY_MODELS
    )


def _assert_safe_rejection(response: HttpResponse, dataset: CedarDataset) -> None:
    """Check the whole document and approved public context for safe rejection.

    :param response: Actual requested Experts response, e.g. HTTP404without Location.
    :param dataset: Persisted private controls and accounts, e.g. Nora and Maria.
    :return: None after status, generic content and sensitive-value omission checks.
    :raises AssertionError: If a rejected response exposes any private value/control.
    """
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "Location" not in response
    assert "person" not in response.context and "contact_person" not in response.context
    html = response.content.decode()
    _assert_sensitive_values_absent(html, dataset)
    if "mailto:" in html or any(
        f'data-testid="{hook}"' in html for hook in _FORBIDDEN_HOOKS
    ):
        raise AssertionError("Rejected profile exposed a private or expert control.")
    assert _rejection_presentation(response) == (
        "Expert unavailable",
        "Back to Experts",
        "/experts/",
    )


def _rejection_presentation(response: HttpResponse) -> tuple[str, str, str]:
    """Normalize only stable error content, leaving CSRF/request data out.

    :param response: Actual generic404HTML, e.g. nberg's requested page.
    :return: Heading, recovery label and route, e.g. unavailable/Back/Experts.
    :raises AssertionError: If the expected accessible generic controls are absent.
    """
    heading = find_by_test_id(response.content, "expert-unavailable")
    back = find_by_test_id(response.content, "expert-unavailable-back-link")
    assert back.name == "a"
    return element_text(heading), element_text(back), dict(back.attributes)["href"]


def _sensitive_markers(dataset: CedarDataset) -> tuple[str, ...]:
    """Collect real persisted identity/private probes without echoing their values.

    :param dataset: Real fixture objects, e.g. Nora's draft and Maria's token.
    :return: Nonempty markers, e.g. private titles, bodies, addresses and token keys.
    :raises AssertionError: If a required fixture probe is absent.
    """
    nora = dataset.users_by_username["nberg"]
    maria = dataset.users_by_username["mrodriguez"]
    private_book = Playbook.objects.get(author=maria, visibility="private")
    private_pip = ProcessImprovementProposal.objects.get(
        created_by=maria, status=ProcessImprovementProposal.STATUS_DRAFT
    )
    draft = Playbook.objects.get(author=nora, status="draft")
    markers = (
        nora.get_full_name(),
        nora.email,
        draft.name,
        private_book.name,
        private_book.description,
        private_pip.title,
        private_pip.summary,
        Token.objects.get(user=maria).key,
        *(user.email for user in dataset.users_by_username.values()),
    )
    assert all(markers)
    return markers


def _assert_sensitive_values_absent(text: str, dataset: CedarDataset) -> None:
    """Reject private-value leakage using a constant safe failure message.

    :param text: Actual HTML or boundary logs, e.g. the complete404document.
    :param dataset: Real private fixture probes, e.g. Maria token and Nora draft.
    :return: None when every persisted probe is absent.
    :raises AssertionError: If a sensitive value appears, without displaying it.
    """
    if any(value in text for value in _sensitive_markers(dataset)):
        raise AssertionError("Public rejection exposed private fixture data.")


def _assert_rejection_log_story(
    caplog: pytest.LogCaptureFixture, dataset: CedarDataset
) -> None:
    """Verify the actual correlated boundary records disclose no presence distinction.

    :param caplog: Actual INFO records, e.g. expert_detail entry/branch/exit.
    :param dataset: Persisted private probes, e.g. Nora's identity and Maria's token.
    :return: None after same safe story and no private-value disclosure.
    :raises AssertionError: If a required beat or privacy property is missing.
    """
    correlation = "correlation_id=cedar-s21-rejection"
    assert_log_story(
        caplog,
        where="expert_detail",
        beats={
            "entry": ("| entry |", "authenticated=False", correlation),
            "branch": ("| branch |", "reason=expert_unavailable", correlation),
            "exit": ("| exit |", "status=404", correlation),
        },
    )
    records = [r.getMessage() for r in caplog.records if correlation in r.getMessage()]
    _assert_sensitive_values_absent(
        "\n".join(r.getMessage() for r in caplog.records), dataset
    )
    for message in records:
        if any(
            value in message
            for value in (*_REJECTED_SUBJECTS, "account_id=", "user_id=")
        ):
            raise AssertionError(
                "Correlated rejection logs distinguished account presence."
            )
    assert not any("| error |" in row or "status=200" in row for row in records)
