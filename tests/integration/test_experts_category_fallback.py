"""Certify S03 category recovery and its log story through real Cedar requests."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from urllib.parse import urlencode

import pytest
from django.core.mail import EmailMessage
from django.test import Client, TestCase

from methodology.models import AgentInteraction, ExpertProfile, KarmaAward
from tests.support.experts_data import CedarDataset
from tests.support.experts_fallback_assertions import assert_development_fallback
from tests.support.experts_logs import capture_experts_logs
from tests.support.log_story import assert_log_story

pytestmark = pytest.mark.django_db

_UNKNOWN_PATH = "/experts/?category=unrecognized"
_DEVELOPMENT_PATH = "/experts/?category=development"
_VIEW_LOGGER = "methodology.expert_views"
_QUERY_LOGGER = "methodology.services.experts_service"
_SUMMARY_LOGGERS = (
    "methodology.services.contribution_summary_service",
    "methodology.services.contribution_summary_boundary",
)
_VIEW_ENTRY = ("| entry |", "category=development")
_VIEW_EXIT = ("| exit |", "category=development", "status=200", "count=2")
_FALLBACK_BRANCH = ("| branch |", "reason=invalid_category", "category=development")
_QUERY_SELECTION = ("| branch |", "primary_category=development", "eligible_count=2")


@pytest.fixture
def experts_fallback_log_capture(
    caplog: pytest.LogCaptureFixture,
) -> Iterator[pytest.LogCaptureFixture]:
    """Capture S03 loggers while preserving global test logging configuration.

    :param caplog: Pytest capture fixture. Example: caplog.
    :return: Capture iterator with restored logger flags on teardown. Example: iter((caplog,)).
    :raises ValueError: If a production logger name is invalid.
    """
    with capture_experts_logs(caplog, (_VIEW_LOGGER, _QUERY_LOGGER, *_SUMMARY_LOGGERS)):
        yield caplog


def test_experts_list_with_unknown_category_returns_development_only(
    client: Client, cedar_dataset: CedarDataset, mailoutbox: list[EmailMessage]
) -> None:
    """Prove the exact acceptance URL and unchanged Experts state.

    :param client: Real Django client. Example: Client().
    :param cedar_dataset: Fresh Cedar ORM baseline. Example: esvensson and mchen records.
    :param mailoutbox: Local Django mail capture. Example: [].
    :return: None. Example: passing assertions return None.
    :raises AssertionError: If fallback is erroneous, mixed-category or mutating.
    """
    client.force_login(cedar_dataset.users_by_username["esvensson"])
    observed_models = (KarmaAward, ExpertProfile, AgentInteraction)
    before = [list(model.objects.order_by("pk").values()) for model in observed_models]
    before_mail = tuple(mailoutbox)

    with TestCase.captureOnCommitCallbacks() as callbacks:
        response = client.get(_UNKNOWN_PATH)

    assert_development_fallback(response)
    assert response.wsgi_request.get_full_path() == _UNKNOWN_PATH
    assert not callbacks
    assert [
        list(model.objects.order_by("pk").values()) for model in observed_models
    ] == before
    assert tuple(mailoutbox) == before_mail


@pytest.mark.parametrize(
    "request_path",
    [
        pytest.param("/experts/", id="missing"),
        pytest.param("/experts/?category=", id="blank"),
        pytest.param("/experts/?category=%20%09", id="whitespace"),
        pytest.param(_UNKNOWN_PATH, id="unknown"),
        pytest.param("/experts/?category=DESIGN", id="uppercase"),
        pytest.param("/experts/?category[]=design", id="bracket-name"),
        pytest.param("/experts/?category=%00design", id="encoded-control"),
    ],
)
def test_experts_list_with_invalid_category_variant_returns_development_only(
    client: Client, cedar_dataset: CedarDataset, request_path: str
) -> None:
    """Certify every Section D invalid/default query row.

    :param client: Real Django client. Example: Client().
    :param cedar_dataset: Fresh Cedar ORM baseline. Example: mchen and jlee records.
    :param request_path: Parameterized local URL. Example: "/experts/?category=%20%09".
    :return: None. Example: passing assertions return None.
    :raises AssertionError: If any variant leaks unrelated cards or fails recovery.
    """
    client.force_login(cedar_dataset.users_by_username["esvensson"])
    ledger_before = list(KarmaAward.objects.order_by("pk").values())

    response = client.get(request_path)

    assert_development_fallback(response)
    path, _, query = request_path.partition("?")
    assert response.wsgi_request.path == path
    assert response.wsgi_request.META["QUERY_STRING"] == query
    assert list(KarmaAward.objects.order_by("pk").values()) == ledger_before


def test_experts_category_fallback_log_story_happy(
    client: Client,
    cedar_dataset: CedarDataset,
    experts_fallback_log_capture: pytest.LogCaptureFixture,
) -> None:
    """Prove S03's recognized Development story through real HTTP.

    :param client: Real Django client. Example: Client().
    :param cedar_dataset: Fresh Cedar baseline. Example: two Development contributors.
    :param experts_fallback_log_capture: Enabled capture. Example: caplog.
    :return: None. Example: passing assertions return None.
    :raises AssertionError: If declared beats are missing or fallback is falsely reported.
    """
    caplog = experts_fallback_log_capture
    request_id = "cedar-s09-development"
    response = client.get(_DEVELOPMENT_PATH, headers={"X-Request-ID": request_id})
    assert_development_fallback(response)
    assert response.headers["X-Request-ID"] == request_id
    correlation = f"correlation_id={request_id}"
    assert_log_story(
        caplog,
        where="experts_list",
        beats={
            "entry": (*_VIEW_ENTRY, "actor=guest", correlation),
            "exit": (*_VIEW_EXIT, correlation),
        },
    )
    assert_log_story(
        caplog,
        where="ExpertsService.list_leaders",
        beats={
            "entry": ("| entry |", "category=development", "limit=5", correlation),
            "selection": (*_QUERY_SELECTION, correlation),
            "exit": ("| exit |", "returned_count=2", correlation),
        },
    )
    assert not any(
        "_selected_category | branch |" in message for message in caplog.messages
    )


def test_experts_category_fallback_log_story_reject(
    client: Client,
    cedar_dataset: CedarDataset,
    experts_fallback_log_capture: pytest.LogCaptureFixture,
) -> None:
    """Prove S03's recoverable unknown-input story through real HTTP.

    :param client: Real Django client. Example: Client().
    :param cedar_dataset: Fresh Cedar baseline. Example: mchen and jlee.
    :param experts_fallback_log_capture: Enabled capture. Example: caplog.
    :return: None. Example: passing assertions return None.
    :raises AssertionError: If fallback/exit beats are absent or unsafe logging occurs.
    """
    elena = cedar_dataset.users_by_username["esvensson"]
    client.force_login(elena)
    caplog = experts_fallback_log_capture
    caplog.clear()
    hostile = "<s09-raw-category-probe>\n\x00"
    query = urlencode({"category": hostile})
    request_id = "cedar-s09-recovery"
    response = client.get(f"/experts/?{query}", headers={"X-Request-ID": request_id})
    assert_development_fallback(response)
    assert response.wsgi_request.GET["category"] == hostile
    assert response.headers["X-Request-ID"] == request_id
    correlation = f"correlation_id={request_id}"
    assert_log_story(
        caplog,
        where="_selected_category",
        beats={"branch": (*_FALLBACK_BRANCH, correlation)},
    )
    assert_log_story(
        caplog,
        where="experts_list",
        beats={
            "entry": (*_VIEW_ENTRY, f"actor={elena.pk}", correlation),
            "exit": (*_VIEW_EXIT, correlation),
        },
    )
    assert all(record.levelno < logging.ERROR for record in caplog.records)
    assert all(record.name not in _SUMMARY_LOGGERS for record in caplog.records)
    assert "s09-raw-category-probe" not in caplog.text
