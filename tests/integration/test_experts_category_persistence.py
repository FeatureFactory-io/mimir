"""Real Django-client proofs for EXPERTS-LIST-02."""

from __future__ import annotations

import logging
from http import HTTPStatus
from urllib.parse import urljoin

import pytest
from django.http import HttpResponse
from django.test import Client
from pytest import LogCaptureFixture

from tests.support.experts_category_html import category_anchors
from tests.support.experts_data import CedarDataset
from tests.support.experts_html import _walk_elements, find_by_test_id
from tests.support.experts_logs import capture_experts_logs
from tests.support.log_story import assert_log_story

pytestmark = pytest.mark.django_db

_LIST_PATH = "/experts/"
_DESIGN_URL = "/experts/?category=design"
_VIEW_LOGGER = "methodology.expert_views"
_CATEGORIES = (
    ("product", "Product"),
    ("development", "Development"),
    ("research", "Research"),
    ("design", "Design"),
    ("other", "Other"),
)


def test_category_links_with_design_query_show_five_links_and_one_current(
    client: Client,
    cedar_dataset: CedarDataset,
) -> None:
    """Prove labels, hrefs, hooks and unique Design current state.

    :param client: Real Django client. Example: authenticated Cedar Elena.
    :param cedar_dataset: Imported history and accounts. Example: Cedar Elena.
    :return: None. Example: five expected anchors asserted.
    :raises AssertionError: If response, category order, hrefs or ARIA differ.
    """
    client.force_login(cedar_dataset.users_by_username["esvensson"])
    response = client.get(_DESIGN_URL)
    assert response.status_code == HTTPStatus.OK
    assert response.wsgi_request.get_full_path() == _DESIGN_URL

    anchors = category_anchors(response.content.decode())
    assert [
        (
            anchor.label,
            urljoin(_DESIGN_URL, anchor.href),
            anchor.test_id,
            anchor.aria_current,
        )
        for anchor in anchors
    ] == [
        (
            label,
            f"{_LIST_PATH}?category={slug}",
            f"experts-category-{slug}",
            "page" if slug == "design" else None,
        )
        for slug, label in _CATEGORIES
    ]


def test_category_selection_with_repeated_design_get_remains_current(
    client: Client,
    cedar_dataset: CedarDataset,
) -> None:
    """Prove the Design query reconstructs the same state on another request.

    :param client: Real Django client. Example: authenticated Cedar Elena.
    :param cedar_dataset: Imported accounts and expected order. Example: Cedar Elena.
    :return: None. Example: two equal category and ranking snapshots asserted.
    :raises AssertionError: If repeat GET changes URL, current category or ranking.
    """
    client.force_login(cedar_dataset.users_by_username["esvensson"])
    index = client.get(_LIST_PATH)
    assert index.status_code == HTTPStatus.OK
    design_links = [
        anchor
        for anchor in category_anchors(index.content.decode())
        if anchor.label == "Design"
    ]
    assert len(design_links) == 1
    design = design_links[0]
    design_url = urljoin(index.wsgi_request.get_full_path(), design.href)
    assert design_url == _DESIGN_URL

    selected = client.get(design_url)
    assert selected.status_code == HTTPStatus.OK
    selected_url = selected.wsgi_request.get_full_path()
    assert selected_url == _DESIGN_URL
    refreshed = client.get(selected_url)
    assert refreshed.status_code == HTTPStatus.OK
    assert refreshed.wsgi_request.get_full_path() == selected_url

    anchors = category_anchors(selected.content.decode())
    assert [
        (anchor.test_id, anchor.aria_current)
        for anchor in anchors
        if anchor.aria_current is not None
    ] == [("experts-category-design", "page")]
    assert category_anchors(refreshed.content.decode()) == anchors
    expected_ranking = cedar_dataset.oracle["expected_design_order"]
    assert (
        _ranked_usernames(selected) == _ranked_usernames(refreshed) == expected_ranking
    )


def test_category_selection_log_story_happy(
    client: Client, cedar_dataset: CedarDataset, caplog: LogCaptureFixture
) -> None:
    """Prove the shared list story independently for two Design requests.

    :param client: Real Django client. Example: authenticated Cedar Elena.
    :param cedar_dataset: Imported history and accounts. Example: Cedar Elena.
    :param caplog: Captured pytest records. Example: INFO experts_list beats.
    :return: None. Example: entry and exit asserted for both requests.
    :raises AssertionError: If a request lacks the two correlated INFO beats.
    """
    client.force_login(cedar_dataset.users_by_username["esvensson"])
    for request_id in ("cedar-s02-design-select", "cedar-s02-design-refresh"):
        caplog.clear()
        with capture_experts_logs(caplog, (_VIEW_LOGGER,)):
            response = client.get(_DESIGN_URL, headers={"X-Request-ID": request_id})
        assert response.status_code == HTTPStatus.OK
        assert response.headers["X-Request-ID"] == request_id
        _assert_design_log_story(caplog, request_id)


def _ranked_usernames(response: HttpResponse) -> list[str]:
    """Read the ordered contributor identities from the rendered leaderboard.

    :param response: Real Design response. Example: GET /experts/?category=design.
    :return: Usernames in DOM order. Example: ["sreed", "mrodriguez"].
    :raises AssertionError: If the ranked section is missing or duplicated.
    """
    leaderboard = find_by_test_id(response.content, "experts-leaderboard")
    card_prefix = "experts-card-"
    return [
        value.removeprefix(card_prefix)
        for node in _walk_elements(leaderboard)
        for name, value in node.attributes
        if name == "data-testid" and value.startswith(card_prefix)
    ]


def _assert_design_log_story(caplog: LogCaptureFixture, request_id: str) -> None:
    """Check a single request's actual view log levels, order and correlation.

    :param caplog: View records for this request. Example: the captured INFO logs.
    :param request_id: Safe header value. Example: "cedar-s02-design-refresh".
    :return: None. Example: both required beats matched.
    :raises AssertionError: For missing, unordered or incorrectly correlated beats.
    """
    correlation = f"correlation_id={request_id}"
    assert_log_story(
        caplog,
        where="experts_list |",
        beats={
            "entry": ("| entry |", "category=design", correlation),
            "exit": ("| exit |", "category=design", "status=200", correlation),
        },
    )
    records = [
        record
        for record in caplog.records
        if record.name == _VIEW_LOGGER
        and record.getMessage().startswith("experts_list | ")
    ]
    assert len(records) == 2
    for record, beat in zip(records, ("entry", "exit"), strict=True):
        _where, actual_beat, fields = record.getMessage().split(" | ", 2)
        assert (record.levelno, actual_beat) == (logging.INFO, beat)
        assert correlation in fields.split()
