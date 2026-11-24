"""Real stored-source serving contracts; visual previews are certified separately."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import replace
from http import HTTPStatus
from typing import Any, cast

from django.apps import apps
from django.contrib.sessions.models import Session
from django.core.mail import EmailMessage
from django.db import connection
from django.http import HttpResponse
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from methodology.llm.base import LLMResponse
from methodology.models import AgentInteraction, ExpertProfile
from tests.support.experts_data import CedarDataset
from tests.support.experts_html import element_text, find_by_test_id
from tests.support.experts_privacy import assert_public_response
from tests.support.experts_summary_data import (
    SUMMARY_SCRIPTS,
    load_summary_script,
    prepare_summary_submission,
    summary_processing_scope,
)
from tests.support.scripted_llm import ScriptedLLM

_MARIA = "mrodriguez"
_SENTENCE_COUNT = 9
_READ_REPETITIONS = 3
_SETUP_CALL_COUNT = 2
_CORRELATION_ID = "s24-stored-read-setup"
_READ_SQL = {"SELECT", "BEGIN", "COMMIT", "SAVEPOINT", "RELEASE"}


def test_stored_summary_with_three_surface_reads_preserves_identical_full_text(
    client: Client, cedar_dataset: CedarDataset, mailoutbox: list[EmailMessage]
) -> None:
    """Certify one stored paragraph through three production HTTP surfaces.

    :param client: Real Django client. Example: authenticated Maria's client.
    :param cedar_dataset: Isolated real Cedar ORM dataset. Example: CEDAR-RFP-01.
    :param mailoutbox: Real captured Django mail. Example: [].
    :return: None when each designated DTO and full paragraph equals the oracle.
    :raises AssertionError: If a GET changes or omits stored text or creates work.
    """
    paragraph = _oracle_paragraph(cedar_dataset)
    readers = _authenticated_readers(client, cedar_dataset)
    with _refreshed_summary(client, cedar_dataset, paragraph) as llm:
        before = _state_fingerprint(mailoutbox)
        with (
            TestCase.captureOnCommitCallbacks() as callbacks,
            CaptureQueriesContext(connection) as queries,
        ):
            _assert_three_surfaces(readers, cedar_dataset, paragraph)
        _assert_read_only(before, mailoutbox, queries, callbacks, llm)


def test_stored_summary_with_repeated_reads_preserves_refresh_state(
    client: Client, cedar_dataset: CedarDataset, mailoutbox: list[EmailMessage]
) -> None:
    """Certify repeated GETs preserve complete successful refresh and domain state.

    :param client: Real Django client. Example: Maria's authenticated session.
    :param cedar_dataset: Runner-owned Cedar database. Example: nine-sentence Maria.
    :param mailoutbox: Real captured Django mail. Example: [].
    :return: None when three rounds preserve rows, prose, usage, trace and mail.
    :raises AssertionError: If reads mutate state, queue work or request completion.
    """
    paragraph = _oracle_paragraph(cedar_dataset)
    readers = _authenticated_readers(client, cedar_dataset)
    with _refreshed_summary(client, cedar_dataset, paragraph) as llm:
        before = _state_fingerprint(mailoutbox)
        with (
            TestCase.captureOnCommitCallbacks() as callbacks,
            CaptureQueriesContext(connection) as queries,
        ):
            for _ in range(_READ_REPETITIONS):
                _assert_three_surfaces(readers, cedar_dataset, paragraph)
                if _state_fingerprint(mailoutbox) != before:
                    raise AssertionError("A read changed stored domain state or mail.")
        _assert_read_only(before, mailoutbox, queries, callbacks, llm)


def _oracle_paragraph(dataset: CedarDataset) -> str:
    """Reconcile Maria's stored text with the independent nine-sentence oracle.

    :param dataset: Loaded real Cedar baseline. Example: CEDAR-RFP-01.
    :return: Exact complete public paragraph. Example: Maria's nine sentences.
    :raises AssertionError: If the stored paragraph differs or lacks its ending.
    """
    people = cast(Sequence[dict[str, Any]], dataset.oracle["people"])
    paragraph = next(
        person["summary"] for person in people if person["username"] == _MARIA
    )
    assert isinstance(paragraph, str) and paragraph.strip()
    assert len(paragraph.split(". ")) == _SENTENCE_COUNT
    profile = ExpertProfile.objects.get(user=dataset.users_by_username[_MARIA])
    assert profile.contribution_summary == paragraph
    assert paragraph.endswith(
        "availability and project fit still require a conversation."
    )
    return paragraph


def _authenticated_readers(client: Client, dataset: CedarDataset) -> tuple[Client, ...]:
    """Create real Maria/Elena sessions before observing read-side effects.

    :param client: Existing real client. Example: initially anonymous Client().
    :param dataset: Real Cedar accounts. Example: Maria and Elena.
    :return: Own-profile, Design-list and guest-detail clients. Example: three clients.
    :raises AssertionError: If the guest unexpectedly has an authenticated session.
    """
    client.force_login(dataset.users_by_username[_MARIA])
    elena = Client()
    elena.force_login(dataset.users_by_username["esvensson"])
    guest = Client()
    assert not guest.cookies
    return client, elena, guest


@contextmanager
def _refreshed_summary(
    client: Client, dataset: CedarDataset, paragraph: str
) -> Iterator[ScriptedLLM]:
    """Establish S24's successful-refresh precondition through S23's actual lifecycle.

    :param client: Real authenticated Maria client. Example: own-profile reader.
    :param dataset: Existing Cedar dataset. Example: Hana's public playbook 6106.
    :param paragraph: Independent public oracle. Example: Maria's nine sentences.
    :return: Existing captured CAP-004 provider. Example: two setup calls then no more.
    :raises AssertionError: If normal submission cannot persist the full paragraph.
    """
    pip = prepare_summary_submission(dataset)
    script = load_summary_script(
        SUMMARY_SCRIPTS / "PRF-EXPERTS-03/submission_happy.json", pip.changes.get().pk
    )
    summary = script[0]
    assert isinstance(summary, LLMResponse)
    script = (replace(summary, content=paragraph), *script[1:])
    with summary_processing_scope(script, rates={"scripted": ("3", "15")}) as llm:
        with TestCase.captureOnCommitCallbacks(execute=True):
            response = client.post(
                reverse("pip_submit_review", kwargs={"pk": pip.pk}),
                headers={"X-Request-ID": _CORRELATION_ID},
            )
        assert response.status_code == HTTPStatus.FOUND
        assert len(llm.calls) == _SETUP_CALL_COUNT
        _assert_refresh_precondition(dataset, paragraph)
        yield llm


def _assert_refresh_precondition(dataset: CedarDataset, paragraph: str) -> None:
    """Require nonempty real successful metadata before testing read preservation.

    :param dataset: Cedar ORM accounts. Example: Maria's stored profile.
    :param paragraph: Independent expected prose. Example: complete nine sentences.
    :return: None when real usage, cost and control trace exist. Example: success.
    :raises AssertionError: If setup leaves an empty or unsuccessful interaction.
    """
    profile = ExpertProfile.objects.get(user=dataset.users_by_username[_MARIA])
    interaction = AgentInteraction.objects.get(
        subject=profile.user, correlation_id=_CORRELATION_ID
    )
    assert profile.contribution_summary == paragraph
    assert profile.summary_status == ExpertProfile.SummaryStatus.SUCCESS
    assert profile.summary_updated_at is not None and not profile.summary_error_code
    assert profile.last_summary_correlation_id == interaction.correlation_id
    assert interaction.outcome == AgentInteraction.Outcome.SUCCESS
    assert interaction.model == "scripted"
    assert interaction.input_tokens and interaction.output_tokens
    assert interaction.estimated_cost_usd is not None and interaction.latency_ms >= 0
    assert tuple(event["beat"] for event in interaction.events) == (
        "entry",
        "entry",
        "public_evidence",
        "llm_call",
        "validation",
        "exit",
        "domain_write",
        "exit",
    )


def _assert_three_surfaces(
    readers: tuple[Client, ...], dataset: CedarDataset, paragraph: str
) -> None:
    """Read Maria's real own-profile, Elena's Design list and Bob's public detail.

    :param readers: Three established clients. Example: (maria, elena, guest).
    :param dataset: Real Cedar objects and privacy oracle. Example: CEDAR-RFP-01.
    :param paragraph: Entire stored source. Example: all nine Maria sentences.
    :return: None after designated DTOs and full DOM source reconcile. Example: success.
    :raises AssertionError: For a wrong response, source or public privacy boundary.
    """
    own = readers[0].get(reverse("profile"))
    leaderboard = readers[1].get(reverse("experts_list"), {"category": "design"})
    detail = readers[2].get(reverse("expert_detail", args=[_MARIA]))
    assert (
        own.status_code
        == leaderboard.status_code
        == detail.status_code
        == HTTPStatus.OK
    )
    assert own.context["username"] == _MARIA
    assert own.context["contributions"]["summary"] == paragraph
    card = next(
        person
        for person in leaderboard.context["people"]
        if person["username"] == _MARIA
    )
    assert card["hint"] == paragraph
    assert detail.context["person"]["summary"] == paragraph
    for response, test_id in (
        (own, "profile-contribution-summary"),
        (leaderboard, f"experts-card-hint-{_MARIA}"),
        (detail, "expert-contribution-summary"),
    ):
        _assert_full_source(response, test_id, paragraph)
    assert_public_response(detail, dataset, authenticated=False)
    assert not readers[2].cookies


def _assert_full_source(response: HttpResponse, test_id: str, paragraph: str) -> None:
    """Check full initial DOM source without claiming CSS preview visibility.

    :param response: Actual production response. Example: Maria's public detail.
    :param test_id: Existing paragraph hook. Example: profile-contribution-summary.
    :param paragraph: Entire stored public source. Example: nine Maria sentences.
    :return: None when normalized text matches through its final sentence.
    :raises AssertionError: If rendering slices or changes the stored paragraph.
    """
    node = find_by_test_id(response.content, test_id)
    assert element_text(node) == paragraph


def _state_fingerprint(mailoutbox: list[EmailMessage]) -> tuple[str, ...]:
    """Hash complete domain/account/M2M rows and mail without exposing private values.

    :param mailoutbox: Actual captured mail. Example: existing submission notices.
    :return: Ordered SHA-256 comparisons, including session identities. Example: hashes.
    :raises RuntimeError: If the isolated database cannot be queried.
    """
    models = sorted(
        apps.get_models(include_auto_created=True), key=lambda model: model._meta.label
    )
    rows = [
        tuple(model.objects.order_by("pk").values_list())
        for model in models
        if model is not Session
    ]
    rows.append(
        tuple(
            (session.pk, session.get_decoded())
            for session in Session.objects.order_by("pk")
        )
    )
    mail = tuple((type(message).__name__, message.__dict__) for message in mailoutbox)
    return tuple(
        hashlib.sha256(repr(value).encode()).hexdigest() for value in (*rows, mail)
    )


def _assert_read_only(
    before: tuple[str, ...],
    mailoutbox: list[EmailMessage],
    queries: CaptureQueriesContext,
    callbacks: list[Any],
    llm: ScriptedLLM,
) -> None:
    """Reject domain writes and model work while permitting existing session refresh.

    :param before: Safe complete-domain hashes. Example: pre-GET state fingerprint.
    :param mailoutbox: Real locmem mail. Example: unchanged submission messages.
    :param queries: Actual SQL during GETs. Example: SELECT plus session UPDATE.
    :param callbacks: Actual post-commit registrations. Example: [].
    :param llm: Existing setup model seam. Example: exactly two captured calls.
    :return: None when reads preserve state and create no generation. Example: success.
    :raises AssertionError: For any side effect beyond existing session refresh.
    """
    if _state_fingerprint(mailoutbox) != before:
        raise AssertionError(
            "Stored-summary GETs changed complete domain/account/mail state."
        )
    assert not callbacks, "A stored-summary GET registered post-commit work."
    assert len(llm.calls) == _SETUP_CALL_COUNT, "A GET requested model completion."
    for query in queries:
        sql = query["sql"].lstrip().upper()
        command = sql.split(maxsplit=1)[0]
        if command not in _READ_SQL and not sql.startswith(
            'UPDATE "DJANGO_SESSION" SET '
        ):
            raise AssertionError("A stored-summary GET executed a domain SQL write.")
