from __future__ import annotations

from uuid import UUID

import pytest
from django.http import HttpResponse
from django.test import Client
from django.urls import reverse
from django.utils.html import escape

from methodology.models import AgentInteraction, ExpertProfile, KarmaAward, Playbook
from tests.support.experts_data import CedarDataset
from tests.support.experts_html import element_text, find_by_test_id
from tests.support.experts_logs import capture_experts_logs
from tests.support.log_story import assert_log_story

pytestmark = pytest.mark.django_db
_MARIA_PATH = "/experts/mrodriguez/"
_VIEW_LOGGER = "methodology.expert_views"
_SERVICE_LOGGER = "methodology.services.experts_service"


def test_public_detail_with_cedar_maria_returns_identity_and_complete_summary(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Prove exact identity and complete real stored prose.

    :param client: Real Django client. Example: authenticated Elena.
    :param cedar_dataset: Imported Cedar fixture. Example: Maria's stored prose.
    :return: None. Example: all public values match Cedar ORM baseline.
    :raises AssertionError: For missing, altered or shortened content.
    """
    client.force_login(cedar_dataset.users_by_username["esvensson"])
    response = client.get(_MARIA_PATH, {"category": "research"})

    _assert_maria_identity_and_summary(response, cedar_dataset)
    back_link = find_by_test_id(response.content, "expert-back-link")
    assert ("href", "/experts/?category=research") in back_link.attributes
    book = cedar_dataset.playbooks_by_pk[6101]
    book_link = find_by_test_id(response.content, f"expert-playbook-{book.pk}")
    assert ("href", reverse("playbook_detail", args=[book.pk])) in book_link.attributes
    find_by_test_id(response.content, "karma-source-breakdown")
    find_by_test_id(response.content, "karma-category-breakdown")


def test_public_detail_with_guest_returns_same_public_identity_and_summary(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Prove anonymous readability without contact disclosure.

    :param client: Real anonymous client. Example: Bob.
    :param cedar_dataset: Imported Cedar fixture. Example: Maria's account and prose.
    :return: None. Example: 200 and complete Maria paragraph without email.
    :raises AssertionError: For a redirect, altered prose or exposed email.
    """
    response = client.get(_MARIA_PATH)

    _assert_maria_identity_and_summary(response, cedar_dataset)
    maria = cedar_dataset.users_by_username["mrodriguez"]
    assert "email" not in response.context["person"]
    assert maria.email.encode() not in response.content
    assert b"mailto:" not in response.content


def test_public_detail_with_html_summary_escapes_untrusted_markup(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Prove stored prose is escaped rather than interpreted as markup.

    :param client: Real anonymous client. Example: Bob.
    :param cedar_dataset: Imported Cedar fixture. Example: Maria's persisted profile.
    :return: None. Example: escaped text with no executable script node.
    :raises AssertionError: When unsafe markup reaches the rendered document.
    """
    markup = '<script>alert("expert")</script> & <strong>example</strong>'
    maria = cedar_dataset.users_by_username["mrodriguez"]
    ExpertProfile.objects.filter(user=maria).update(contribution_summary=markup)
    response = client.get(_MARIA_PATH)

    assert response.status_code == 200
    paragraph = find_by_test_id(response.content, "expert-contribution-summary")
    assert paragraph.children == [markup]
    assert escape(markup).encode() in response.content
    assert markup.encode() not in response.content


def _assert_maria_identity_and_summary(
    response: HttpResponse, cedar_dataset: CedarDataset
) -> None:
    """Check the complete persisted paragraph and exact public identity.

    :param response: Real public detail response. Example: GET /experts/mrodriguez/.
    :param cedar_dataset: Imported Cedar fixture. Example: Maria's persisted profile.
    :return: None after confirming the server-rendered identity and summary.
    :raises AssertionError: For missing public fields or shortened text.
    """
    assert response.status_code == 200
    assert any(
        template.name == "experts/detail.html" for template in response.templates
    )
    assert b"<title>Maria Rodriguez</title>" in response.content
    heading = find_by_test_id(response.content, "expert-name")
    assert heading.name == "h1"
    assert element_text(heading) == "Maria Rodriguez"
    assert (
        element_text(find_by_test_id(response.content, "expert-karma-total")) == "8,200"
    )
    assert (
        element_text(find_by_test_id(response.content, "expert-primary-category"))
        == "Design"
    )
    maria = cedar_dataset.users_by_username["mrodriguez"]
    stored = ExpertProfile.objects.get(user=maria).contribution_summary
    paragraph = find_by_test_id(response.content, "expert-contribution-summary")
    assert paragraph.name == "p"
    assert paragraph.children == [stored]


@pytest.mark.parametrize("username", ["no-such-cedar-user", "nberg"])
def test_public_detail_with_unavailable_subject_renders_navigable_404(
    client: Client, cedar_dataset: CedarDataset, username: str
) -> None:
    """Check a generic accessible rejection with a route back to Experts.

    :param client: Real anonymous client. Example: Bob.
    :param cedar_dataset: Imported Cedar fixture. Example: Nora's zero-Karma account.
    :param username: Requested account. Example: "nberg".
    :return: None after checking the rejection inside the production shell.
    :raises AssertionError: If the rejection exposes an identity or lacks navigation.
    """
    nora = cedar_dataset.users_by_username["nberg"]
    response = client.get(reverse("expert_detail", args=[username]))

    assert response.status_code == 404
    heading = find_by_test_id(response.content, "expert-unavailable")
    assert heading.name == "h1"
    assert element_text(heading) == "Expert unavailable"
    back_link = find_by_test_id(response.content, "expert-unavailable-back-link")
    assert ("href", reverse("experts_list")) in back_link.attributes
    find_by_test_id(response.content, "app-sidebar")
    assert nora.get_full_name().encode() not in response.content
    assert nora.email.encode() not in response.content
    assert b'data-testid="expert-name"' not in response.content


def test_public_detail_with_request_preserves_persisted_state(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Prove a detail read neither awards nor refreshes summaries.

    :param client: Real Django client. Example: Elena GETs Maria.
    :param cedar_dataset: Real Cedar dataset. Example: contains Elena and Maria.
    :return: None. Example: identical ledger, summary metadata and trace counts.
    :raises AssertionError: When a read causes persistence effects.
    """
    client.force_login(cedar_dataset.users_by_username["esvensson"])
    awards = list(KarmaAward.objects.order_by("pk").values())
    profiles = list(ExpertProfile.objects.order_by("pk").values())
    interactions = list(AgentInteraction.objects.order_by("pk").values())

    response = client.get(_MARIA_PATH)

    assert response.status_code == 200
    assert list(KarmaAward.objects.order_by("pk").values()) == awards
    assert list(ExpertProfile.objects.order_by("pk").values()) == profiles
    assert list(AgentInteraction.objects.order_by("pk").values()) == interactions


def test_public_detail_with_cedar_baseline_exposes_only_public_projection(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Prove the detail payload contains only approved display fields.

    :param client: Real Django client. Example: Bob GETs Maria.
    :param cedar_dataset: Real Cedar dataset. Example: Maria's own released evidence.
    :return: None. Example: no raw account and only public released book payloads.
    :raises AssertionError: For a private object, email or unexpected payload key.
    """
    maria = cedar_dataset.users_by_username["mrodriguez"]
    for status in ("draft", "active", "disabled"):
        Playbook.objects.create(
            author=maria,
            name=status,
            category="design",
            visibility="public",
            status=status,
        )
    summary = ExpertProfile.objects.get(user=maria).contribution_summary
    book = cedar_dataset.playbooks_by_pk[6101]
    assert reverse("expert_detail", kwargs={"username": maria.username}) == _MARIA_PATH
    response = client.get(_MARIA_PATH, {"category": "research"})

    assert response.status_code == 200
    assert response.context["back_url"] == "/experts/?category=research"
    assert response.context["person"] == {
        "subject_id": maria.pk,
        "username": "mrodriguez",
        "name": "Maria Rodriguez",
        "initials": "MR",
        "total_karma": 8200,
        "formatted_karma": "8,200",
        "primary_category": "Design",
        "summary": summary,
        "numeric_fallback": "1 released playbook · 0 copies",
        "source_rows": (
            {"label": "Released playbooks", "points": "5,000"},
            {"label": "PIP contributions", "points": "1,600"},
            {"label": "Consumption", "points": "1,200"},
            {"label": "Learning", "points": "400"},
        ),
        "category_rows": (
            {"label": "Design", "points": "7,200"},
            {"label": "Development", "points": "1,000"},
        ),
        "public_playbooks": (
            {"pk": book.pk, "title": book.name, "category": "Design", "version": "1.0"},
        ),
    }
    assert any(
        template.name == "experts/detail.html" for template in response.templates
    )


def test_public_detail_with_legacy_release_preserves_public_projection(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Keep a blank-category released book visible and the expert eligible.

    :param client: Real Django client. Example: Bob GETs Maria.
    :param cedar_dataset: Imported real dataset. Example: Maria's public playbook 6101.
    :return: None. Example: the public book retains its blank display category.
    :raises AssertionError: If a legacy category suppresses eligible evidence or identity.
    """
    book = cedar_dataset.playbooks_by_pk[6101]
    Playbook.objects.filter(pk=book.pk).update(category="")
    response = client.get(_MARIA_PATH, {"category": "unknown"})

    assert response.status_code == 200
    assert response.context["back_url"] == "/experts/?category=design"
    detail = response.context["person"]
    assert detail["primary_category"] == "Design"
    assert detail["numeric_fallback"] == "1 released playbook · 0 copies"
    assert detail["public_playbooks"] == (
        {"pk": book.pk, "title": book.name, "version": "1.0", "category": ""},
    )


def test_public_detail_with_no_public_books_preserves_positive_projection(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Use persisted points to establish eligibility independently of evidence.

    :param client: Real Django client. Example: Bob GETs Sam.
    :param cedar_dataset: Imported real dataset. Example: Sam has historical awards.
    :return: None. Example: Sam has 4,800 points and no public book rows.
    :raises AssertionError: If an empty evidence list suppresses the expert.
    """
    sam = cedar_dataset.users_by_username["skim"]
    response = client.get(reverse("expert_detail", kwargs={"username": sam.username}))

    assert response.status_code == 200
    assert response.context["person"]["total_karma"] == 4800
    assert response.context["person"]["public_playbooks"] == ()


@pytest.mark.parametrize("request_id", ["cedar-s17", "invalid@example.invalid"])
def test_public_detail_log_story_happy(
    client: Client,
    cedar_dataset: CedarDataset,
    caplog: pytest.LogCaptureFixture,
    request_id: str,
) -> None:
    """Prove correlated detail logs without sensitive content.

    :param client: Real client. Example: GET with request ID cedar-s17.
    :param cedar_dataset: Real Cedar dataset. Example: Maria's persisted contribution.
    :param caplog: Captured INFO records. Example: entry, processing and exit.
    :param request_id: Incoming header. Example: "cedar-s17".
    :return: None. Example: assert_log_story verifies each declared beat.
    :raises AssertionError: For missing beats or leaked prose/email/sentinels.
    """
    maria = cedar_dataset.users_by_username["mrodriguez"]
    with capture_experts_logs(caplog, (_VIEW_LOGGER, _SERVICE_LOGGER)):
        response = client.get(_MARIA_PATH, headers={"X-Request-ID": request_id})
    assert response.status_code == 200
    feature_messages = [
        record.getMessage()
        for record in caplog.records
        if record.name in (_VIEW_LOGGER, _SERVICE_LOGGER)
    ]
    detail_logs = "\n".join(feature_messages)
    correlation_id = response.headers["X-Request-ID"]
    if request_id == "cedar-s17":
        assert correlation_id == request_id
    else:
        assert str(UUID(correlation_id)) == correlation_id
        assert request_id not in detail_logs

    correlation = f"correlation_id={correlation_id}"
    assert_log_story(
        caplog,
        where="expert_detail",
        beats={
            "entry": (
                "| entry |",
                "authenticated=False",
                "operation=public_expert_detail",
                correlation,
            ),
            "exit": (
                "| exit |",
                "status=200",
                "template=experts/detail.html",
                correlation,
            ),
        },
    )
    assert_log_story(
        caplog,
        where="ExpertsService.public_detail",
        beats={
            "processing": (
                "| processing |",
                f"subject_id={maria.pk}",
                "summary_present=True",
                "public_playbook_count=1",
                correlation,
            )
        },
    )
    assert [
        message.split(" | ")[1]
        for message in feature_messages
        if message.startswith(("expert_detail |", "ExpertsService.public_detail |"))
    ] == ["entry", "processing", "exit"]
    assert maria.username not in detail_logs
    assert maria.email not in detail_logs
    assert "Cedar Bid Pricing" not in detail_logs
    assert "Internal staffing notes for Cedar" not in detail_logs
    assert ExpertProfile.objects.get(user=maria).contribution_summary not in detail_logs


@pytest.mark.parametrize("username", ["no-such-cedar-user", "nberg"])
def test_public_detail_log_story_reject(
    client: Client,
    cedar_dataset: CedarDataset,
    caplog: pytest.LogCaptureFixture,
    username: str,
) -> None:
    """Prove both rejection paths use one generic response and safe log story.

    :param client: Real client. Example: anonymous Bob.
    :param cedar_dataset: Imported real data. Example: Nora's zero-point account.
    :param caplog: Captured INFO records. Example: entry, branch and exit.
    :param username: Requested account. Example: "nberg".
    :return: None. Example: both branches report the same reason and status.
    :raises AssertionError: If a branch reveals the subject or its eligibility.
    """
    nora = cedar_dataset.users_by_username["nberg"]
    correlation = "correlation_id=cedar-s17-missing"
    with capture_experts_logs(caplog, (_VIEW_LOGGER, _SERVICE_LOGGER)):
        response = client.get(
            f"/experts/{username}/", headers={"X-Request-ID": "cedar-s17-missing"}
        )
    assert response.status_code == 404
    assert nora.email.encode() not in response.content
    assert all(
        username not in record.getMessage()
        for record in caplog.records
        if record.name in (_VIEW_LOGGER, _SERVICE_LOGGER)
    )
    assert_log_story(
        caplog,
        where="ExpertsService.public_detail",
        beats={"branch": ("| branch |", "reason=missing_or_ineligible", correlation)},
    )
    assert_log_story(
        caplog,
        where="expert_detail",
        beats={
            "branch": ("| branch |", "reason=expert_unavailable", correlation),
            "exit": ("| exit |", "status=404", correlation),
        },
    )
