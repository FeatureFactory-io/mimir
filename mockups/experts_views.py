"""DEBUG-only Experts prototypes using the Cedar fixture, without datastore reads."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from types import SimpleNamespace

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse

from methodology.context_processors import build_shell_context
from mockups.views import MOCK_INDEX_GROUPS, _index_group_with_hrefs

logger = logging.getLogger(__name__)
DATA_FILE = Path(settings.BASE_DIR) / "test-data/experts/cedar-rfp-01.json"
CATEGORIES = ("Product", "Development", "Research", "Design", "Other")
SOURCE_LABELS = {
    "Released": "Released playbooks",
    "PIP": "PIP contributions",
    "Consumption": "Consumption",
    "Learning": "Learning",
}


def _data() -> dict:
    """Read public fictional design data.

    :return: Cedar domain fixture dictionary.
    :raises FileNotFoundError: When the required design fixture is absent.
    """
    return json.loads(DATA_FILE.read_text())


def _person(person: dict) -> dict:
    """Project fixture fields into template display values without DB access.

    :param person: One fixture person.
    :return: Independent template dictionary with formatted points and initials.
    """
    result = dict(person)
    result["formatted_karma"] = f"{person['total_karma']:,}"
    result["initials"] = "".join(part[0] for part in person["name"].split()[:2])
    result["source_rows"] = [
        {"label": SOURCE_LABELS[key], "points": f"{value:,}"}
        for key, value in person.get("karma_by_source", {}).items()
    ]
    result["hint"] = person.get("summary") or (
        f"{len(person.get('public_playbooks', []))} public released playbooks"
    )
    return result


def _context(request: HttpRequest, screen_id: str) -> dict:
    """Build a fictional shell without replacing request.user or reading accounts.

    :param request: Anonymous prototype request; guest=1 selects guest chrome.
    :param screen_id: Traceability ID from the journey.
    :return: Shell context and shared mockup inventory.
    """
    authenticated = request.GET.get("guest") != "1"
    actor = SimpleNamespace(
        is_authenticated=authenticated,
        is_staff=False,
        username="esvensson",
        first_name="Elena",
        last_name="Svensson",
    )
    shell_request = SimpleNamespace(user=actor, path="/experts/")
    context = build_shell_context(shell_request)
    context.update(
        {
            "user": actor,
            "screen_id": screen_id,
            "mock_authenticated": authenticated,
            "guest_query": "" if authenticated else "?guest=1",
            "nav_section": "experts",
            "unread_notification_count": 0,
            "pip_nav_unread_count": 0,
            "mockup_inventory": [
                _index_group_with_hrefs(group) for group in MOCK_INDEX_GROUPS
            ],
        }
    )
    for section in context["sidebar_sections"]:
        if section["id"] == "collaborate":
            section["items"].append(
                {
                    "slug": "experts",
                    "label": "Experts",
                    "url": reverse("mockup_experts_list"),
                    "testid": "nav-experts",
                    "icon": "fa-solid fa-user-graduate",
                    "active": True,
                }
            )
    return context


def experts_list(request: HttpRequest) -> HttpResponse:
    """Render ranked fixture cards for a selected playbook category.

    :param request: Prototype request with optional category/guest/state.
    :return: HTML design reference with persistent mockup chrome.
    """
    selected = next(
        (c for c in CATEGORIES if c.lower() == request.GET.get("category")),
        "Development",
    )
    people = [
        _person(p)
        for p in _data()["people"]
        if p["primary_category"] == selected and p["total_karma"] > 0
    ]
    people.sort(key=lambda p: (-p["total_karma"], p["username"]))
    context = _context(request, "FOB-EXPERTS-LIST+FIND-1")
    context.update(
        {
            "people": people[:5],
            "selected_category": selected,
            "categories": CATEGORIES,
            "state": request.GET.get("state", "loaded"),
        }
    )
    logger.info("Experts mockup list category=%s count=%s", selected, len(people[:5]))
    return render(request, "mockups/experts/list.html", context)


def expert_detail(request: HttpRequest, username: str) -> HttpResponse:
    """Render one eligible fixture profile and its public evidence.

    :param request: Prototype request; guest=1 disables contact.
    :param username: Fixture username.
    :return: Public profile design reference.
    :raises Http404: When the fixture person is missing or has no points.
    """
    person = next(
        (
            p
            for p in _data()["people"]
            if p["username"] == username and p["total_karma"] > 0
        ),
        None,
    )
    if person is None:
        raise Http404("Expert not found")
    context = _context(request, "FOB-EXPERT-VIEW-1")
    context["person"] = _person(person)
    return render(request, "mockups/experts/detail.html", context)


def expert_own_profile(request: HttpRequest) -> HttpResponse:
    """Render Maria's contribution section using existing account layout patterns.

    :param request: Prototype request, without live account authentication.
    :return: Own-profile design reference.
    """
    person = next(p for p in _data()["people"] if p["username"] == "mrodriguez")
    context = _context(request, "FOB-PROFILE-VIEW-1")
    context["person"] = _person(person)
    context["user"] = SimpleNamespace(
        is_authenticated=True,
        is_staff=False,
        username="mrodriguez",
        first_name="Maria",
        last_name="Rodriguez",
    )
    return render(request, "mockups/experts/own_profile.html", context)


def expert_playbook(request: HttpRequest, pk: int) -> HttpResponse:
    """Render public fixture evidence without querying a live playbook.

    :param request: Prototype request.
    :param pk: Numeric fixture playbook identifier.
    :return: Playbook evidence design reference.
    :raises Http404: When no public released fixture book matches.
    """
    book = next(
        (
            b
            for p in _data()["people"]
            for b in p.get("public_playbooks", [])
            if b["pk"] == pk
        ),
        None,
    )
    if book is None:
        raise Http404("Public playbook not found")
    context = _context(request, "FOB-PLAYBOOKS-VIEW_PLAYBOOK-1")
    context["book"] = book
    return render(request, "mockups/experts/playbook.html", context)
