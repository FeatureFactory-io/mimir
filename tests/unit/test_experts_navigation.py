from __future__ import annotations

import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory
from django.urls import reverse

from methodology.context_processors import (
    _collaborate_items,
    _is_experts_path,
    primary_nav_section,
)


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/experts/", True),
        ("/experts/mrodriguez/", True),
        ("/experts", False),
        ("/experts-other/", False),
        ("/dashboard/", False),
        ("/playbooks/12/", False),
        ("/playbooks/experts/", False),
    ],
)
def test_is_experts_path_with_local_paths_returns_expected_match(
    path: str, expected: bool
) -> None:
    """Prove route-family matching.

    :param path: Candidate local path. Example: "/experts/".
    :param expected: Required match result. Example: True.
    :return: None. Example: None.
    :raises AssertionError: If the matcher selects the wrong section.
    """
    assert _is_experts_path(path) is expected


@pytest.mark.parametrize(
    "path",
    [
        None,
        42,
        "",
        "experts/",
        "//external/",
        "https://external/",
        "/\\external/",
        "/experts/?category=design",
        "/experts/#section",
        "/experts/\nextra/",
    ],
)
def test_is_experts_path_with_invalid_input_raises_value_error(path: object) -> None:
    """Prove invalid inputs fail clearly.

    :param path: Invalid boundary value. Example: None.
    :return: None. Example: None.
    :raises AssertionError: If ValueError is not raised.
    """
    with pytest.raises(ValueError, match="local absolute path"):
        _is_experts_path(path)


def test_collaborate_items_with_experts_preserves_existing_links() -> None:
    """Prove one Experts entry and unchanged existing destinations.

    :return: None. Example: None.
    :raises AssertionError: If Experts is duplicated or Teams/PIPs change.
    """
    teams, experts, pips = _collaborate_items()
    assert (teams["slug"], teams["url"], teams["testid"]) == (
        "teams",
        "/teams/",
        "nav-teams",
    )
    assert experts == {
        "slug": "experts",
        "label": "Experts",
        "url": "/experts/",
        "testid": "nav-experts",
        "icon": "fa-solid fa-user-graduate",
        "tooltip": "Top contributors by playbook category",
    }
    assert experts["url"] == reverse("experts_list")
    assert (pips["slug"], pips["url"], pips["testid"]) == (
        "pips",
        reverse("pip_list"),
        "nav-pips",
    )


@pytest.mark.parametrize("chrome", ["guest", "authenticated"])
@pytest.mark.parametrize(
    ("path", "section"),
    [
        ("/experts/", "experts"),
        ("/experts/mrodriguez/", "experts"),
        ("/experts/activities/", "experts"),
        ("/experts-other/", None),
        ("/experts/%5Cinvalid/", None),
        ("/playbooks/experts/", "playbooks"),
    ],
)
def test_primary_nav_section_with_experts_path_marks_experts_current(
    path: str, section: str | None, chrome: str
) -> None:
    """Prove exact active-section matching uses the existing shell.

    :param path: Incoming request path. Example: "/experts/".
    :param section: Required active section. Example: "experts".
    :param chrome: Expected shell identity. Example: "authenticated".
    :return: None. Example: None.
    :raises AssertionError: If section, realm or chrome changes incorrectly.
    """
    request = RequestFactory().get(path)
    request.user = (
        User(username="esvensson") if chrome == "authenticated" else AnonymousUser()
    )
    context = primary_nav_section(request)
    assert context["nav_section"] == section
    assert context["active_realm"] == "mimir"
    assert context["chrome"] == chrome
