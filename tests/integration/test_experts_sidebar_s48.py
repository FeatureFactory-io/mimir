"""Real shell, exact living-spec and observability certification for S48."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from django.contrib.auth.models import User
from django.core import mail
from django.test import Client, TestCase
from django.test.html import Element
from pytest import LogCaptureFixture

from methodology.models import AgentInteraction, ExpertProfile, KarmaAward
from tests.support.experts_acceptance import run_exact_acceptance
from tests.support.experts_data import load_cedar_baseline
from tests.support.experts_html import _walk_elements, element_text, find_by_test_id
from tests.support.experts_logs import capture_experts_logs
from tests.support.log_story import assert_log_story

_SECTION_LABELS = (
    ("sidebar-sec-workspace", "Workspace"),
    ("sidebar-sec-methodology", "Methodology"),
    ("sidebar-sec-collaborate", "Collaborate"),
)
_EXPECTED_LINKS = (
    (("Home", "/dashboard/", "nav-dashboard"),),
    (
        ("Playbooks", "/playbooks/", "nav-playbooks"),
        ("Workflows", "/workflows/", "nav-workflows"),
        ("Phases", "/phases/", "nav-phases"),
        ("Activities", "/activities/", "nav-activities"),
        ("Artifacts", "/artifacts/", "nav-artifacts"),
        ("Agents", "/agents/", "nav-agents"),
        ("Skills", "/skills/", "nav-skills"),
        ("Rules", "/rules/", "nav-rules"),
    ),
    (
        ("Teams", "/teams/", "nav-teams"),
        ("Experts", "/experts/", "nav-experts"),
        ("PIPs", "/pips/", "nav-pips"),
    ),
)
_PROTECTED_MODELS = (User, KarmaAward, ExpertProfile, AgentInteraction)


@pytest.mark.django_db
def test_sidebar_with_authenticated_elena_preserves_existing_navigation(
    client: Client,
) -> None:
    """Prove the existing shell exposes exactly one correctly grouped Experts link.

    :param client: Real Django client. Example: authenticated Cedar Elena.
    :return: None. Example: None.
    :raises AssertionError: If grouping, order, destination or accessible name differs.
    """
    elena = _login_elena(client)
    before = _protected_state()
    with TestCase.captureOnCommitCallbacks(execute=False) as callbacks:
        response = client.get("/dashboard/")
    assert response.status_code == 200 and response.wsgi_request.user == elena
    assert response.context["chrome"] == "authenticated"
    sidebar = _assert_sidebar_structure(response.content)
    link = find_by_test_id(str(sidebar), "nav-experts")
    assert dict(link.attributes)["title"] == "Top contributors by playbook category"
    icons = [node for node in _walk_elements(link) if node.name == "i"]
    assert len(icons) == 1
    assert set(dict(icons[0].attributes)["class"].split()) == {
        "fa-solid",
        "fa-user-graduate",
    }
    _assert_only_current(sidebar, "nav-dashboard")
    assert _protected_state() == before and callbacks == []


@pytest.mark.django_db
def test_sidebar_with_experts_destination_marks_only_experts_current(
    client: Client,
) -> None:
    """Follow the rendered destination and inspect actual current-page semantics.

    :param client: Real Django client. Example: authenticated Cedar Elena.
    :return: None. Example: None.
    :raises AssertionError: If response, leaderboard or scoped current state differs.
    """
    elena = _login_elena(client)
    before = _protected_state()
    with TestCase.captureOnCommitCallbacks(execute=False) as callbacks:
        landing = client.get("/dashboard/")
        assert landing.status_code == 200
        sidebar = _assert_sidebar_structure(landing.content)
        link = find_by_test_id(str(sidebar), "nav-experts")
        href = dict(link.attributes)["href"]
        response = client.get(href)
    assert href == "/experts/" and response.status_code == 200
    assert response.wsgi_request.get_full_path() == href
    assert response.wsgi_request.user == elena and not response.has_header("Location")
    assert "experts/list.html" in [template.name for template in response.templates]
    find_by_test_id(response.content, "experts-leaderboard")
    _assert_only_current(_assert_sidebar_structure(response.content), "nav-experts")
    realm = find_by_test_id(response.content, "realm-nav-list")
    _assert_only_current(realm, "realm-nav-mimir")
    categories = find_by_test_id(response.content, "experts-category-tabs")
    _assert_only_current(categories, "experts-category-development")
    assert _protected_state() == before and callbacks == []


@pytest.mark.django_db
def test_sidebar_log_story_happy(client: Client, caplog: LogCaptureFixture) -> None:
    """Prove the existing authenticated Experts shell decision narrative.

    :param client: Real Django client. Example: authenticated Cedar Elena.
    :param caplog: INFO capture. Example: context-processor log records.
    :return: None. Example: None.
    :raises AssertionError: If any declared entry, branch or exit beat is absent.
    """
    elena = _login_elena(client)
    before = _protected_state()
    with capture_experts_logs(caplog, ("methodology.context_processors",)):
        response = client.get("/experts/")
    assert response.status_code == 200 and response.wsgi_request.user == elena
    assert_log_story(
        caplog,
        where="primary_nav_section",
        beats={
            "entry": ("entry", "path=/experts/"),
            "branch": ("branch", "chrome=authenticated"),
            "exit": ("exit", "nav_section=experts"),
        },
    )
    assert _protected_state() == before


def test_sidebar_acceptance_with_exact_contract_runs_one_passing_scenario(
    tmp_path: Path,
) -> None:
    """Run exact Behave selection in a separate acceptance-settings process.

    :param tmp_path: Report directory. Example: pytest-owned temporary directory.
    :return: None. Example: None.
    :raises AssertionError: For nonzero exit, wrong count, skips or failed steps.
    """
    assert tmp_path.is_dir()
    result = run_exact_acceptance(
        Path("docs/features/act-0-auth/experts-navigation.feature"),
        "FOB-NAV-EXPERTS-01",
        1,
    )
    assert (
        result.scenario_count,
        result.step_count,
        result.skipped_count,
        result.undefined_count,
    ) == (1, 6, 0, 0)


def _login_elena(client: Client) -> User:
    """Use the actual Cedar identity without changing its permissions.

    :param client: Runner-owned Django client. Example: client fixture.
    :return: Authenticated original user. Example: esvensson, nonstaff.
    :raises AssertionError: The fixture grants unexpected elevated permissions.
    """
    elena = load_cedar_baseline().users_by_username["esvensson"]
    assert not elena.is_staff and not elena.is_superuser
    client.force_login(elena)
    return elena


def _protected_state() -> str:
    """Fingerprint complete account, ledger, profile and interaction records.

    :return: Private digest and mail count. Example: a SHA256 hex string.
    :raises TypeError: A stored field cannot be serialized by the actual adapter.
    """
    rows = [
        (model._meta.label, list(model.objects.order_by("pk").values_list()))
        for model in _PROTECTED_MODELS
    ]
    rows.append(("mail_count", len(getattr(mail, "outbox", ()))))
    encoded = json.dumps(rows, default=str, sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def _assert_sidebar_structure(html: str | bytes) -> Element:
    """Check the actual unique sidebar's three labelled lists and exact links.

    :param html: Actual Django response bytes. Example: response.content.
    :return: Original parsed sidebar. Example: aside#mmAppSidebar.
    :raises AssertionError: A section, label, order or existing link differs.
    """
    sidebar = find_by_test_id(html, "app-sidebar")
    assert sidebar.name == "aside"
    assert dict(sidebar.attributes)["aria-label"] == "Mimir in-app navigation"
    nodes = tuple(_walk_elements(sidebar))
    labels = [
        node
        for node in nodes
        if "mm-sidebar-section-label" in dict(node.attributes).get("class", "").split()
    ]
    assert (
        tuple((dict(node.attributes)["id"], element_text(node)) for node in labels)
        == _SECTION_LABELS
    )
    groups = [node for node in nodes if node.name == "ul"]
    assert len(groups) == len(_SECTION_LABELS)
    for group, (label_id, _), expected in zip(
        groups, _SECTION_LABELS, _EXPECTED_LINKS, strict=True
    ):
        assert dict(group.attributes)["aria-labelledby"] == label_id
        _assert_group_links(group, expected)
    return sidebar


def _assert_group_links(
    group: Element, expected: tuple[tuple[str, str, str], ...]
) -> None:
    """Require original ordered anchors and decorative shell icons.

    :param group: Actual labelled list. Example: Collaborate ul.
    :param expected: Independent link oracle. Example: Teams, Experts, PIPs.
    :return: None. Example: all destinations and icons preserved.
    :raises AssertionError: A link, accessible name, icon or destination differs.
    """
    links = [node for node in _walk_elements(group) if node.name == "a"]
    actual = tuple(
        (
            element_text(node),
            dict(node.attributes).get("href"),
            dict(node.attributes).get("data-testid"),
        )
        for node in links
    )
    assert actual == expected
    for link in links:
        assert dict(link.attributes).get("title", "").strip()
        icons = [node for node in _walk_elements(link) if node.name == "i"]
        assert len(icons) == 1 and ("aria-hidden", "true") in icons[0].attributes
        assert element_text(icons[0]) == ""


def _assert_only_current(container: Element, test_id: str) -> None:
    """Require both current signals to identify exactly the same sole link.

    :param container: Actual parsed navigation region. Example: sidebar.
    :param test_id: Sole expected current selector. Example: nav-experts.
    :return: None. Example: every other region link lacks either current signal.
    :raises AssertionError: Active styling or accessible current state differs.
    """
    links = [
        dict(node.attributes) for node in _walk_elements(container) if node.name == "a"
    ]
    assert [
        link.get("data-testid") for link in links if link.get("aria-current") == "page"
    ] == [test_id]
    assert [
        link.get("data-testid")
        for link in links
        if "active" in link.get("class", "").split()
    ] == [test_id]
