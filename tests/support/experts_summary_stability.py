from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any
from uuid import uuid4

from django.core import mail
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection
from django.http import HttpResponse
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from methodology.models import Activity, AgentInteraction, ExpertProfile, KarmaAward
from methodology.services.experts_service import ExpertsService
from tests.support.agent_story import assert_agent_story
from tests.support.experts_data import CedarDataset
from tests.support.experts_html import (
    assert_karma_source_rows,
    element_text,
    find_by_test_id,
)
from tests.support.experts_privacy import _assert_private_markers_absent

_MARIA = "mrodriguez"
_ACTIVITY_ID = 6203
_SOURCE_VALUES = {
    "Released playbooks": 5000,
    "PIP contributions": 1600,
    "Consumption": 1200,
    "Learning": 405,
}
_READ_COMMANDS = {"SELECT", "BEGIN", "COMMIT", "SAVEPOINT", "RELEASE"}
_OWN_SOURCE_VALUES = {
    "Released": 5000,
    "PIP": 1600,
    "Consumption": 1200,
    "Learning": 405,
}


@dataclass(frozen=True)
class SummaryState:
    """Immutable persisted prose/refresh/interaction evidence."""

    profile_values: Mapping[str, Any]
    interaction_values: tuple[Mapping[str, Any], ...]


def capture_summary_state(subject_id: int) -> SummaryState:
    """Read complete summary metadata and actual interaction rows.

    :param subject_id: Positive profile owner ID. Example: Maria's user PK.
    :return: Immutable state. Example: nine sentences and successful metadata.
    :raises ValueError: For invalid/missing subject.
    """
    if type(subject_id) is not int or subject_id <= 0:
        raise ValueError("A positive real subject ID is required.")
    try:
        profile = ExpertProfile.objects.values().get(user_id=subject_id)
    except ExpertProfile.DoesNotExist as error:
        raise ValueError("The subject has no stored profile.") from error
    interactions = tuple(
        MappingProxyType(
            {
                key: json.dumps(value, cls=DjangoJSONEncoder, sort_keys=True)
                for key, value in row.items()
            }
        )
        for row in AgentInteraction.objects.order_by("pk").values()
    )
    return SummaryState(MappingProxyType(profile), interactions)


def post_authorized_copy(client: Client, cedar: CedarDataset) -> str:
    """GET activity 6203 and POST S36's real CSRF-valid receipt.

    :param client: Real authenticated strict client. Example: Maria's session.
    :param cedar: Real ORM baseline. Example: CEDAR-RFP-01.
    :return: Applied action UUID string. Example: a new UUID4 string.
    :raises AssertionError: For missing prompt/CSRF or unsuccessful receipt.
    """
    assert client.handler.enforce_csrf_checks
    control = _copy_control(client)
    assert client.session["_auth_user_id"] == str(cedar.users_by_username[_MARIA].pk)
    action = str(uuid4())
    receipt = client.post(
        control["data-copy-receipt-url"],
        data={
            "entity_type": "activity",
            "entity_id": _ACTIVITY_ID,
            "event_identity": action,
        },
        content_type="application/json",
        HTTP_X_CSRFTOKEN=control["data-copy-receipt-csrf"],
        HTTP_X_REQUEST_ID="s28-copy-receipt",
    )
    assert receipt.status_code == 200
    assert receipt.json() == {"status": "applied"}
    return action


def assert_live_displays(client: Client, cedar: CedarDataset) -> None:
    """Assert post-copy actual HTML totals, sources, category and stored text.

    :param client: Real Maria client. Example: authenticated Django client.
    :param cedar: Real baseline with oracle paragraph. Example: CEDAR-RFP-01.
    :return: None. Example: all rendered values reconcile to 8205/12455.
    :raises AssertionError: For stale score, changed prose or side effects.
    """
    subject_id = cedar.users_by_username[_MARIA].pk
    before = capture_summary_state(subject_id)
    awards = tuple(KarmaAward.objects.order_by("pk").values_list())
    outbox = tuple(getattr(mail, "outbox", ()))
    with CaptureQueriesContext(connection) as queries:
        own = client.get("/auth/user/profile/", HTTP_X_REQUEST_ID="s28-live-displays")
        public = Client().get(f"/experts/{_MARIA}/")
        _assert_maria_surface(own, cedar, own=True)
        _assert_maria_surface(public, cedar, own=False)
        _assert_leaderboards(client, cedar)
    _assert_read_queries(queries)
    assert capture_summary_state(subject_id) == before
    assert tuple(KarmaAward.objects.order_by("pk").values_list()) == awards
    assert tuple(getattr(mail, "outbox", ())) == outbox


def _assert_maria_surface(
    response: HttpResponse, cedar: CedarDataset, *, own: bool
) -> None:
    """Check exact complete prose and both numeric dimensions on one real page.

    :param response: Actual HTTP response. Example: Maria own-profile200.
    :param cedar: Independent oracle and real accounts. Example: CEDAR-RFP-01.
    :param own: Whether this is authenticated own profile. Example: True.
    :return: None. Example: source sum8205 and complete nine sentences.
    :raises AssertionError: For stale/missing text, wrong score or category.
    """
    assert response.status_code == 200
    prefix = "profile" if own else "expert"
    summary = find_by_test_id(response.content, f"{prefix}-contribution-summary")
    assert element_text(summary) == _oracle_paragraph(cedar)
    category = find_by_test_id(response.content, f"{prefix}-primary-category")
    assert element_text(category) == "Design"
    html = response.content.decode(response.charset)
    sources = _OWN_SOURCE_VALUES if own else _SOURCE_VALUES
    assert_karma_source_rows(html, sources, f"{prefix}-karma-total", 8205)
    data = response.context["contributions" if own else "person"]
    expected = (("Design", 7200), ("Development", 1005))
    assert data["category_rows"] == tuple(
        (
            {"label": label, "points": points, "formatted_points": f"{points:,}"}
            if own
            else {"label": label, "points": f"{points:,}"}
        )
        for label, points in expected
    )
    section_id = (
        "profile-karma-category-breakdown" if own else "karma-category-breakdown"
    )
    expected_text = (
        "Design 7200 Development 1005" if own else "Design 7,200 Development 1,005"
    )
    assert element_text(find_by_test_id(html, section_id)) == expected_text
    if not own:
        _assert_private_markers_absent(html, cedar, False)


def _oracle_paragraph(cedar: CedarDataset) -> str:
    """Read the full independent Maria oracle instead of copying produced prose.

    :param cedar: Real baseline with independent data contract. Example: CEDAR-RFP-01.
    :return: Nine exact sentences. Example: ending with availability caveat.
    :raises AssertionError: If the fixture is incomplete or wrong.
    """
    paragraph = next(
        row["summary"] for row in cedar.oracle["people"] if row["username"] == _MARIA
    )
    assert isinstance(paragraph, str) and len(paragraph.split(". ")) == 9
    assert paragraph.endswith(
        "availability and project fit still require a conversation."
    )
    return paragraph


def _assert_leaderboards(client: Client, cedar: CedarDataset) -> None:
    """Require live Design/Mike cards and intact full stored DOM hint after copy.

    :param client: Real authenticated Maria session. Example: Client().
    :param cedar: Exact case oracle. Example: Maria and Mike baseline handles.
    :return: None. Example: Maria8205 inDesign and Mike12455 inDevelopment.
    :raises AssertionError: For stale membership, totals, text or projections.
    """
    design = client.get("/experts/?category=design")
    development = client.get("/experts/?category=development")
    assert design.status_code == development.status_code == 200
    maria = find_by_test_id(design.content, "experts-card-mrodriguez")
    mike = find_by_test_id(development.content, "experts-card-mchen")
    assert element_text(find_by_test_id(str(maria), "expert-card-karma")) == "8,205"
    assert element_text(find_by_test_id(str(mike), "expert-card-karma")) == "12,455"
    assert element_text(
        find_by_test_id(design.content, "experts-card-hint-mrodriguez")
    ) == _oracle_paragraph(cedar)
    assert b'data-testid="experts-card-mrodriguez"' not in development.content
    projection = ExpertsService().project_user(cedar.users_by_username[_MARIA].pk)
    assert dict(projection.category_points) == {"design": 7200, "development": 1005}
    assert projection.total_points == 8205


def _assert_read_queries(queries: CaptureQueriesContext) -> None:
    """Forbid domain SQL writes during actual display GETs; allow session refresh.

    :param queries: Real query capture. Example: own/list/public reads.
    :return: None. Example: reads and ordinary authenticated expiry refresh only.
    :raises AssertionError: If a read schedules a domain mutation.
    """
    statements = [row["sql"].lstrip().upper() for row in queries]
    assert any(statement.startswith("SELECT ") for statement in statements)
    assert all(
        statement.split(maxsplit=1)[0] in _READ_COMMANDS
        or statement.startswith('UPDATE "DJANGO_SESSION" SET ')
        for statement in statements
    )


def _assert_s28_generation_story(
    interaction: AgentInteraction, subject_id: int, pip_id: int
) -> None:
    """Inspect the actual persisted successful trace before the no-call window.

    :param interaction: Real S23 persisted attempt. Example: successful summary call.
    :param subject_id: Maria's actual primary key. Example: 42.
    :param pip_id: Actual submitted draft key. Example: 7302.
    :return: None. Example: eight authentic beats and actual persisted prose.
    :raises AssertionError: For a fabricated/missing trace or bypassed lifecycle.
    """
    assert interaction.outcome == "success" and not interaction.error_code
    assert (interaction.subject_id, interaction.pip_id, interaction.correlation_id) == (
        subject_id,
        pip_id,
        "s28-real-generation",
    )
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
    assert_agent_story(
        {"workflow_id": interaction.workflow_id, "events": interaction.events},
        workflow="contribution_summary",
        beats=_generation_beats(subject_id, pip_id),
    )


def _copy_control(client: Client) -> dict[str, str]:
    """Read the actual authorized Copy control and its CSRF/target metadata.

    :param client: Real authenticated strict client. Example: Maria session.
    :return: Real rendered attributes. Example: activity6203 receipt URL/token.
    :raises AssertionError: If the route, metadata or CSRF token is missing.
    """
    activity = Activity.objects.select_related("workflow__playbook").get(
        pk=_ACTIVITY_ID
    )
    response = client.get(
        reverse(
            "activity_detail",
            kwargs={
                "playbook_pk": activity.workflow.playbook_id,
                "workflow_pk": activity.workflow_id,
                "activity_pk": activity.pk,
            },
        )
    )
    assert response.status_code == 200
    control = dict(find_by_test_id(response.content, "copy-prompt-btn").attributes)
    assert control["data-copy-receipt-entity-type"] == "activity"
    assert control["data-copy-receipt-entity-id"] == str(_ACTIVITY_ID)
    assert control["data-copy-receipt-url"] == reverse("karma_copy_receipt")
    assert control["data-copy-receipt-csrf"] not in ("", "NOTPROVIDED")
    return control


def _generation_beats(subject_id: int, pip_id: int) -> dict[str, tuple[str, ...]]:
    """Return required fragments for actual stored nine-sentence orchestration.

    :param subject_id: Real Maria key. Example: 3.
    :param pip_id: Real submitted draft key. Example: 7302.
    :return: Required control beats. Example: validation sentence_count=9.
    :raises AssertionError: The caller checks each beat against persisted events.
    """
    return {
        "entry": (
            f"subject_id={subject_id}",
            f"pip_id={pip_id}",
            "correlation_id=s28-real-generation",
        ),
        "public_evidence": ("scope=public_released", "evidence_chars="),
        "llm_call": ("model=scripted", "tools=none", "max_tokens=1024"),
        "validation": ("status=accepted", "sentence_count=9", "limit=14"),
        "domain_write": ("profile_id=", "summary_updated=true"),
        "exit": ("outcome=success", "karma_awarded=0"),
    }
