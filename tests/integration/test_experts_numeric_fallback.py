"""S26 real-DB certification of live numeric contribution fallbacks."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from http import HTTPStatus

import pytest
from django.apps import apps
from django.contrib.sessions.models import Session
from django.core import mail
from django.db import connection
from django.http import HttpResponse
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.authtoken.models import Token

from methodology.models import (
    AgentInteraction,
    EventChannel,
    ExpertProfile,
    KarmaAward,
    Playbook,
)
from methodology.services.experts_service import ExpertsService
from tests.support.experts_data import CedarDataset, load_cedar_baseline
from tests.support.experts_html import _walk_elements, element_text, find_by_test_id
from tests.support.experts_logs import capture_experts_logs
from tests.support.log_story import assert_log_story

pytestmark = pytest.mark.django_db

_MIKE = "mchen"
_LIST_URL = "/experts/?category=development"
_DETAIL_URL = "/experts/mchen/"
_OWN_URL = "/auth/user/profile/"
_REQUEST_ID = "s26-numeric-fallback"
_LOGGERS = (
    "methodology.services.experts_service",
    "methodology.services.expert_card_presentation",
    "methodology.expert_views",
)
_READ_SQL = {"SELECT", "BEGIN", "COMMIT", "SAVEPOINT", "RELEASE"}
_BASE_COPIES = 47
_BASE_BOOKS = 2
_CONSUMPTION_ROWS = 470


def test_numeric_fallback_with_cedar_mike_uses_live_counts(client: Client) -> None:
    """Prove baseline counts from persisted rows and actual response.

    :param client: Real Django client. Example: Client().
    :return: None. Example: exact 2/47 and 470 assertions pass.
    :raises AssertionError: If source/channel rows or rendered hint disagree.
    """
    dataset = load_cedar_baseline()
    mike = dataset.users_by_username[_MIKE]
    assert ExpertProfile.objects.get(user=mike).contribution_summary == ""
    assert (
        KarmaAward.objects.filter(
            recipient=mike, source_kind=KarmaAward.SourceKind.CONSUMPTION
        ).count()
        == _CONSUMPTION_ROWS
    )
    _assert_live_counts(dataset, _BASE_BOOKS, _BASE_COPIES)
    _assert_list_hint(client, _BASE_BOOKS, _BASE_COPIES)


def test_numeric_fallback_with_playbook_visibility_changes_refreshes_next_request(
    client: Client,
) -> None:
    """Prove publication transitions affect the next request without fixture edits.

    :param client: Real Django client. Example: Client().
    :return: None. Example: 2/47, 1/47 and restored 2/47 checks pass.
    :raises AssertionError: If private/nonreleased/other-author books count.
    """
    dataset = load_cedar_baseline()
    book = _public_book(dataset)
    _assert_list_hint(client, _BASE_BOOKS, _BASE_COPIES)
    for visibility, status in (
        ("private", "released"),
        ("public", "draft"),
        ("public", "active"),
        ("public", "disabled"),
    ):
        Playbook.objects.filter(pk=book.pk).update(visibility=visibility, status=status)
        _assert_live_counts(dataset, 1, _BASE_COPIES)
        _assert_list_hint(client, 1, _BASE_COPIES)
        Playbook.objects.filter(pk=book.pk).update(
            visibility="public", status="released"
        )
        _assert_list_hint(client, _BASE_BOOKS, _BASE_COPIES)
    _add_nonqualifying_books(dataset)
    _assert_list_hint(client, _BASE_BOOKS, _BASE_COPIES)
    private = Playbook.objects.get(author=book.author, name="S26 private release")
    Playbook.objects.filter(pk=private.pk).update(visibility="public")
    _assert_live_counts(dataset, 3, _BASE_COPIES)
    _assert_list_hint(client, 3, _BASE_COPIES)


def test_numeric_fallback_with_ledger_changes_counts_only_gui_author_consumption(
    client: Client,
) -> None:
    """Prove source/channel/recipient isolation using real validated awards.

    :param client: Real Django client. Example: Client().
    :return: None. Example: 47 becomes 48 only for one eligible GUI award.
    :raises AssertionError: If learning, MCP, export or other recipients inflate it.
    """
    dataset = load_cedar_baseline()
    _assert_list_hint(client, _BASE_BOOKS, _BASE_COPIES)
    _add_award(
        dataset, "eligible", KarmaAward.SourceKind.CONSUMPTION, EventChannel.GUI_COPY
    )
    _assert_list_hint(client, _BASE_BOOKS, _BASE_COPIES + 1)
    for name, source, channel, recipient in (
        ("mcp", KarmaAward.SourceKind.CONSUMPTION, EventChannel.MCP_DETAIL, _MIKE),
        ("export", KarmaAward.SourceKind.CONSUMPTION, EventChannel.EXPORT, _MIKE),
        ("history", KarmaAward.SourceKind.CONSUMPTION, EventChannel.HISTORICAL, _MIKE),
        ("learning", KarmaAward.SourceKind.LEARNING, EventChannel.GUI_COPY, _MIKE),
        (
            "other",
            KarmaAward.SourceKind.CONSUMPTION,
            EventChannel.GUI_COPY,
            "mrodriguez",
        ),
    ):
        _add_award(dataset, name, source, channel, recipient)
        _assert_live_counts(dataset, _BASE_BOOKS, _BASE_COPIES + 1)
        _assert_list_hint(client, _BASE_BOOKS, _BASE_COPIES + 1)


def test_numeric_fallback_with_missing_summary_is_consistent_across_surfaces(
    client: Client,
) -> None:
    """Prove list/detail/own-profile show the same live missing-summary facts.

    :param client: Real Django client. Example: initially anonymous Client().
    :return: None. Example: all three show exact 2/47 without fabricated prose.
    :raises AssertionError: If a numeric fallback or missing-prose control differs.
    """
    dataset = load_cedar_baseline()
    readers = _readers(client, dataset)
    _assert_surfaces(readers, _BASE_BOOKS, _BASE_COPIES)
    assert (
        ExpertProfile.objects.get(
            user=dataset.users_by_username[_MIKE]
        ).contribution_summary
        == ""
    )


def test_numeric_fallback_with_repeated_gets_preserves_summary_and_generation_history(
    client: Client,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Observe fresh counts while summary metadata and interaction history stay fixed.

    :param client: Real Django client. Example: Mike's authenticated own-profile reader.
    :param caplog: Real log capture. Example: INFO request and generation events.
    :return: None. Example: 2/47 changes to 1/48 with no read-side generation.
    :raises AssertionError: If GET stores prose, calls a model, queues work or awards.
    """
    dataset = load_cedar_baseline()
    readers = _readers(client, dataset)
    profiles = tuple(ExpertProfile.objects.order_by("pk").values())
    interactions = tuple(AgentInteraction.objects.order_by("pk").values())
    with capture_experts_logs(
        caplog, (*_LOGGERS, "methodology.services.contribution_summary_service")
    ):
        for _ in range(3):
            _assert_surfaces(readers, _BASE_BOOKS, _BASE_COPIES)
        book = _public_book(dataset)
        Playbook.objects.filter(pk=book.pk).update(visibility="private")
        _add_award(
            dataset,
            "fresh-count",
            KarmaAward.SourceKind.CONSUMPTION,
            EventChannel.GUI_COPY,
        )
        for _ in range(3):
            _assert_surfaces(readers, 1, _BASE_COPIES + 1)
    assert tuple(ExpertProfile.objects.order_by("pk").values()) == profiles
    assert tuple(AgentInteraction.objects.order_by("pk").values()) == interactions
    assert not any("llm_call" in record.getMessage() for record in caplog.records)
    assert not any(
        record.name == "methodology.services.contribution_summary_service"
        for record in caplog.records
    )


def test_numeric_fallback_log_story_happy(
    client: Client,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Assert actual inherited query/presenter/view beats and safe correlation.

    :param client: Real Django client. Example: anonymous Development request.
    :param caplog: Real log capture. Example: INFO records for s26-numeric-fallback.
    :return: None. Example: real query, live-count branch and response exit match.
    :raises AssertionError: If declared actual beats, correlation or safe content differ.
    """
    dataset = load_cedar_baseline()
    with capture_experts_logs(caplog, _LOGGERS):
        _assert_list_hint(client, _BASE_BOOKS, _BASE_COPIES)
    _assert_log_beats(caplog, dataset)
    _assert_live_counts(dataset, _BASE_BOOKS, _BASE_COPIES)
    messages = "\n".join(
        record.getMessage() for record in caplog.records if record.name in _LOGGERS
    )
    assert "@" not in messages and "DEMO_ONLY_NOT_A_REAL_TOKEN" not in messages
    for profile in ExpertProfile.objects.exclude(contribution_summary=""):
        assert profile.contribution_summary not in messages


def _assert_live_counts(dataset: CedarDataset, books: int, copies: int) -> None:
    """Reconcile independently queried rows and shared production projection.

    :param dataset: Existing Cedar rows. Example: Mike's real account mapping.
    :param books: Required public released count. Example: 2.
    :param copies: Required GUI author-consumption count. Example: 47.
    :return: None. Example: ORM and projection both equal 2/47.
    :raises AssertionError: If live filters or numeric projections disagree.
    """
    mike = dataset.users_by_username[_MIKE]
    assert (
        Playbook.objects.filter(
            author=mike, visibility="public", status="released"
        ).count()
        == books
    )
    assert (
        KarmaAward.objects.filter(
            recipient=mike,
            source_kind=KarmaAward.SourceKind.CONSUMPTION,
            event_channel=EventChannel.GUI_COPY,
        ).count()
        == copies
    )
    projection = ExpertsService().project_user(mike.pk)
    assert (
        projection.released_public_playbook_count,
        projection.successful_gui_copy_count,
    ) == (books, copies)


def _expected_hint(books: int, copies: int) -> str:
    """State the independent expected numeric sentence including singular grammar.

    :param books: Current qualifying book count. Example: 1.
    :param copies: Eligible GUI author rows. Example: 47.
    :return: Exact expected copy. Example: '1 released playbook · 47 copies'.
    :raises AssertionError: If either expected count is negative.
    """
    assert books >= 0 and copies >= 0
    book_label = "playbook" if books == 1 else "playbooks"
    copy_label = "copy" if copies == 1 else "copies"
    return f"{books} released {book_label} · {copies} {copy_label}"


def _assert_list_hint(client: Client, books: int, copies: int) -> None:
    """Read actual Development HTML and verify Mike's complete hint.

    :param client: Real request client. Example: Client().
    :param books: Expected current count. Example: 2.
    :param copies: Expected current eligible GUI rows. Example: 47.
    :return: None. Example: actual hint equals '2 released playbooks · 47 copies'.
    :raises AssertionError: If status, DOM text or actual presenter hint differs.
    """
    response = _read_unchanged(client, _LIST_URL)
    hint = _expected_hint(books, copies)
    assert (
        element_text(find_by_test_id(response.content, f"experts-card-hint-{_MIKE}"))
        == hint
    )
    person = next(
        person for person in response.context["people"] if person["username"] == _MIKE
    )
    assert person["hint"] == hint


def _public_book(dataset: CedarDataset) -> Playbook:
    """Resolve an actual currently qualifying Mike book for mutation tests.

    :param dataset: Existing Cedar rows. Example: mchen account mapping.
    :return: First real public released book. Example: Mike's production playbook.
    :raises AssertionError: If the baseline has no qualifying book.
    """
    book = (
        Playbook.objects.filter(
            author=dataset.users_by_username[_MIKE],
            status="released",
            visibility="public",
        )
        .order_by("pk")
        .first()
    )
    assert book is not None
    return book


def _add_nonqualifying_books(dataset: CedarDataset) -> None:
    """Insert actual nonqualifying book/author variants without changing the oracle.

    :param dataset: Real Cedar account map. Example: Mike and Maria.
    :return: None. Example: private/draft/active/disabled/other-author rows exist.
    :raises ValidationError: If persisted book fields violate model constraints.
    """
    for name, status, visibility, author in (
        ("private release", "released", "private", _MIKE),
        ("draft", "draft", "public", _MIKE),
        ("active", "active", "public", _MIKE),
        ("disabled", "disabled", "public", _MIKE),
        ("other author", "released", "public", "mrodriguez"),
    ):
        Playbook.objects.create(
            name=f"S26 {name}",
            description="Numeric filter boundary",
            category="development",
            author=dataset.users_by_username[author],
            status=status,
            visibility=visibility,
        )


def _add_award(
    dataset: CedarDataset, name: str, source: str, channel: str, recipient: str = _MIKE
) -> None:
    """Insert a validated positive award with explicit source/channel provenance.

    :param dataset: Real Cedar account map. Example: Mike's account.
    :param name: Unique case suffix. Example: 'eligible'.
    :param source: Canonical source choice. Example: consumption.
    :param channel: Canonical explicit channel. Example: gui_copy.
    :param recipient: Actual mapped username. Example: mchen.
    :return: None. Example: one five-point row persisted.
    :raises ValidationError: If source/channel or event data is invalid.
    """
    KarmaAward.objects.create(
        recipient=dataset.users_by_username[recipient],
        event_identity=f"s26:{name}",
        source_kind=source,
        event_channel=channel,
        points=5,
        category="development",
        occurred_at=timezone.now(),
    )


def _readers(client: Client, dataset: CedarDataset) -> tuple[Client, ...]:
    """Prepare owner token/session before the read-only observation window.

    :param client: Real client to authenticate as Mike. Example: Client().
    :param dataset: Runner-owned Cedar accounts. Example: mchen.
    :return: List, guest detail and own-profile clients. Example: three clients.
    :raises AssertionError: If fresh anonymous clients already contain cookies.
    """
    mike = dataset.users_by_username[_MIKE]
    Token.objects.get_or_create(user=mike)
    client.force_login(mike)
    public = (Client(), Client())
    assert all(not reader.cookies for reader in public)
    return (*public, client)


def _assert_surfaces(readers: Sequence[Client], books: int, copies: int) -> None:
    """Require complete identical fallback and absent prose/expansion in actual DOM.

    :param readers: Prepared list/detail/owner clients. Example: three clients.
    :param books: Expected current public count. Example: 2.
    :param copies: Expected GUI author count. Example: 47.
    :return: None. Example: all three actual responses contain identical fallback.
    :raises AssertionError: If a surface omits fallback or fabricates summary controls.
    """
    assert len(readers) == 3
    hint = _expected_hint(books, copies)
    for reader, url, hook in zip(
        readers,
        (_LIST_URL, _DETAIL_URL, _OWN_URL),
        (f"experts-card-hint-{_MIKE}", "expert-numeric-fallback", "profile-karma-card"),
        strict=True,
    ):
        response = _read_unchanged(reader, url)
        node = find_by_test_id(response.content, hook)
        if url == _OWN_URL:
            assert any(
                element.name == "p" and element_text(element) == hint
                for element in _walk_elements(node)
            ), "Own profile must render the same exact live numeric fallback."
        else:
            assert element_text(node) == hint
        for absent in (
            "expert-contribution-summary",
            "profile-contribution-summary",
            "profile-summary-toggle",
        ):
            assert f'data-testid="{absent}"'.encode() not in response.content


def _fingerprint() -> tuple[str, ...]:
    """Hash all actual domain/M2M/mail rows and decoded session identity.

    :return: Complete private-safe state hashes. Example: equal hashes across GET.
    :raises RuntimeError: If the owned test database cannot be queried.
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
    rows.append(tuple(message.__dict__ for message in getattr(mail, "outbox", [])))
    return tuple(hashlib.sha256(repr(value).encode()).hexdigest() for value in rows)


def _read_unchanged(client: Client, url: str) -> HttpResponse:
    """Require real GETs to preserve complete state and queue no post-commit work.

    :param client: Real prepared request client. Example: Mike-authenticated Client.
    :param url: Production route. Example: /experts/mchen/.
    :return: Actual successful response. Example: HTTP200 detail HTML.
    :raises AssertionError: If GET writes domain rows, changes mail or queues work.
    """
    before = _fingerprint()
    with (
        TestCase.captureOnCommitCallbacks() as callbacks,
        CaptureQueriesContext(connection) as queries,
    ):
        response = client.get(url, headers={"X-Request-ID": _REQUEST_ID})
    assert response.status_code == HTTPStatus.OK
    assert (
        _fingerprint() == before
    ), "Numeric-fallback GET changed domain/session/mail state."
    assert not callbacks, "Numeric-fallback GET queued post-commit work."
    for query in queries:
        sql = query["sql"].lstrip().upper()
        assert sql.split(maxsplit=1)[0] in _READ_SQL or sql.startswith(
            'UPDATE "DJANGO_SESSION" SET '
        ), "Numeric-fallback GET executed a domain SQL write."
    return response


def _assert_log_beats(caplog: pytest.LogCaptureFixture, dataset: CedarDataset) -> None:
    """Match actual inherited log contracts without inventing absent count events.

    :param caplog: Actual INFO capture. Example: Development GET events.
    :param dataset: Real subject map. Example: Mike's persisted user ID.
    :return: None. Example: query/presenter/view records carry one request identity.
    :raises AssertionError: If an inherited actual beat or correlation is absent.
    """
    correlation = f"correlation_id={_REQUEST_ID}"
    assert_log_story(
        caplog,
        where="ExpertsService.list_leaders",
        beats={
            "entry": (" | entry | ", "category=development", correlation),
            "exit": (" | exit | ", "returned_count=", correlation),
        },
    )
    assert_log_story(
        caplog,
        where="ExpertCardPresentationService.present",
        beats={
            "branch": (
                " | branch | ",
                f"subject_id={dataset.user_ids[_MIKE]}",
                "hint_source=live_counts",
                "reason=no_stored_public_prose",
                correlation,
            )
        },
    )
    assert_log_story(
        caplog,
        where="experts_list",
        beats={
            "exit": (" | exit | ", "status=200", "category=development", correlation)
        },
    )
