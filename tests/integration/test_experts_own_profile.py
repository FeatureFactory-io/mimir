"""S10 real-DB profile integration and log-story contracts."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.test import Client, RequestFactory
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils.html import escape
from rest_framework.authtoken.models import Token

from accounts.views import _profile_contribution_context
from methodology.models import AgentInteraction, ExpertProfile, KarmaAward
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset
from tests.support.experts_html import element_text, find_by_test_id
from tests.support.experts_logs import capture_experts_logs
from tests.support.log_story import assert_log_story

pytestmark = pytest.mark.django_db
_VIEW_LOGGER = "accounts.views"
_SERVICE_LOGGER = "methodology.services.experts_service"
_CONTEXT_STORY = "accounts.views._profile_contribution_context"


def test_profile_view_with_maria_adds_contribution_context(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Verify live 8200/Design and seeded stored prose on the existing route.

    :param client: Real Django client; example: authenticated Cedar Maria.
    :param cedar_dataset: Real imported accounts and oracle; example: Cedar Maria.
    :return: None; example: all context assertions pass.
    :raises AssertionError: If signals or stored prose diverge from the oracle.
    """
    maria = cedar_dataset.users_by_username["mrodriguez"]
    oracle = next(
        item
        for item in cedar_dataset.oracle["people"]
        if item["username"] == maria.username
    )
    client.force_login(maria)
    response = client.get(reverse("profile"))

    assert response.status_code == 200
    assert "accounts/profile.html" in [template.name for template in response.templates]
    assert response.context["contributions"] == {
        "total_karma": 8200,
        "formatted_karma": "8,200",
        "primary_category": "Design",
        "summary": oracle["summary"],
        "source_rows": tuple(
            {"label": label, "points": points, "formatted_points": f"{points:,}"}
            for label, points in oracle["karma_by_source"].items()
        ),
        "category_rows": (
            {"label": "Design", "points": 7200, "formatted_points": "7,200"},
            {"label": "Development", "points": 1000, "formatted_points": "1,000"},
        ),
    }
    _assert_maria_contribution_markup(response.content, oracle["summary"])


def _assert_maria_contribution_markup(html: bytes, summary_text: str) -> None:
    """Verify the authenticated HTML contains the live signals and full stored prose.

    :param html: Profile response bytes. Example: client.get(...).content.
    :param summary_text: Stored paragraph. Example: Maria's Cedar summary.
    :return: None when contribution and disclosure elements match the contract.
    :raises AssertionError: If the data, elements or disclosure attributes differ.
    """
    find_by_test_id(html, "profile-karma-card")
    assert element_text(find_by_test_id(html, "profile-karma-total")) == "8,200"
    assert element_text(find_by_test_id(html, "profile-primary-category")) == "Design"
    summary = find_by_test_id(html, "profile-contribution-summary")
    toggle = find_by_test_id(html, "profile-summary-toggle")
    assert element_text(summary) == " ".join(summary_text.split())
    assert ("id", "own-contribution-summary") in summary.attributes
    assert toggle.name == "button"
    assert {
        ("type", "button"),
        ("aria-expanded", "false"),
        ("aria-controls", "own-contribution-summary"),
    }.issubset(toggle.attributes)
    assert element_text(toggle) == "Show more"
    assert find_by_test_id(html, "profile-karma-source-breakdown").name == "table"
    assert find_by_test_id(html, "profile-karma-category-breakdown").name == "dl"


def test_profile_view_with_maria_preserves_account_controls(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Verify account controls, existing sections and token identity survive.

    :param client: Real Django client; example: Maria with an existing token.
    :param cedar_dataset: Real accounts and content; example: Cedar Maria.
    :return: None; example: all pre-existing profile controls remain.
    :raises AssertionError: If GET rotates token or removes account functions.
    """
    maria = cedar_dataset.users_by_username["mrodriguez"]
    token, _ = Token.objects.get_or_create(user=maria)
    client.force_login(maria)
    response = client.get(reverse("profile"))

    assert response.status_code == 200
    html = response.content
    assert element_text(find_by_test_id(html, "profile-first-name")) == maria.first_name
    assert element_text(find_by_test_id(html, "profile-last-name")) == maria.last_name
    assert element_text(find_by_test_id(html, "profile-email")) == maria.email
    edit = find_by_test_id(html, "profile-edit-btn")
    assert ("href", reverse("profile_edit")) in edit.attributes
    field = dict(find_by_test_id(html, "profile-token-field").attributes)
    assert field["type"] == "password"
    assert field["value"] == token.key
    assert "readonly" in field
    _assert_token_controls(html)
    for test_id in (
        "profile-pips-table",
        "profile-playbooks-table",
        "profile-teams-section",
    ):
        find_by_test_id(html, test_id)
    assert Token.objects.get(user=maria).key == token.key


def _assert_token_controls(html: bytes) -> None:
    """Verify account token controls in the rendered profile.

    :param html: Profile response bytes. Example: client.get(...).content.
    :return: None when existing token actions and field contracts are present.
    :raises AssertionError: If account token actions or confirmations are lost.
    """
    assert find_by_test_id(html, "profile-token-toggle").name == "button"
    assert find_by_test_id(html, "profile-token-copy").name == "button"
    form = find_by_test_id(html, "profile-token-regenerate-form")
    assert form.name == "form"
    assert ("action", reverse("profile_regenerate_token")) in form.attributes
    assert ("method", "post") in form.attributes
    password = dict(
        find_by_test_id(html, "profile-token-regenerate-password").attributes
    )
    assert password["type"] == "password"
    assert password["name"] == "current_password"
    assert "required" in password
    submit = find_by_test_id(html, "profile-token-regenerate-submit")
    assert ("type", "submit") in submit.attributes


def test_profile_view_with_other_subject_query_uses_request_owner(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Verify caller-selected query subjects cannot change the profile owner.

    :param client: Real client; example: Maria requests ?username=mchen.
    :param cedar_dataset: Real imported accounts; example: Maria and Mike.
    :return: None; example: only Maria account/contribution context is used.
    :raises AssertionError: If another subject's context or token appears.
    """
    maria = cedar_dataset.users_by_username["mrodriguez"]
    mike = cedar_dataset.users_by_username["mchen"]
    other_token = Token.objects.create(user=mike)
    other_summary = "This is Mike's stored contribution paragraph."
    ExpertProfile.objects.filter(user=mike).update(contribution_summary=other_summary)
    client.force_login(maria)

    response = client.get(
        reverse("profile"), {"username": mike.username, "user_id": mike.pk}
    )

    assert response.status_code == 200
    assert response.context["username"] == maria.username
    assert response.context["email"] == maria.email
    assert response.context["api_token"] == Token.objects.get(user=maria).key
    assert other_token.key.encode() not in response.content
    contributions = response.context["contributions"]
    assert contributions["total_karma"] == 8200
    assert contributions["primary_category"] == "Design"
    assert (
        contributions["summary"]
        == ExpertProfile.objects.get(user=maria).contribution_summary
    )


def test_profile_view_with_missing_expert_profile_preserves_account_page(
    client: Client,
) -> None:
    """Verify an absent stored-summary row does not break the account profile.

    :param client: Real client; example: authenticated user without ExpertProfile.
    :return: None; example: 200 with numeric projection and empty summary.
    :raises AssertionError: If GET creates profile/award/interaction rows.
    """
    user = User.objects.create_user(username="profile-without-expert-record")
    client.force_login(user)
    models = (ExpertProfile, KarmaAward, AgentInteraction)
    counts = [model.objects.count() for model in models]

    response = client.get(reverse("profile"))

    assert response.status_code == 200
    assert response.context["username"] == user.username
    contributions = response.context["contributions"]
    assert contributions["total_karma"] == 0
    assert contributions["formatted_karma"] == "0"
    assert contributions["primary_category"] is None
    assert contributions["summary"] == ""
    assert [row["points"] for row in contributions["source_rows"]] == [0, 0, 0, 0]
    assert contributions["category_rows"] == ()
    assert not ExpertProfile.objects.filter(user=user).exists()
    assert [model.objects.count() for model in models] == counts


def test_profile_view_with_summary_markup_escapes_content(client: Client) -> None:
    """Verify stored summary text retains Django autoescaping.

    :param client: Real client; example: profile stores a literal script tag.
    :return: None; example: escaped text renders without executable markup.
    :raises AssertionError: If generated/stored text bypasses autoescaping.
    """
    user = User.objects.create_user(username="profile-with-summary-markup")
    summary_text = '<script data-example="summary-prose">alert(1)</script>'
    ExpertProfile.objects.create(user=user, contribution_summary=summary_text)
    client.force_login(user)

    response = client.get(reverse("profile"))

    assert response.status_code == 200
    summary = find_by_test_id(response.content, "profile-contribution-summary")
    assert element_text(summary) == summary_text
    assert escape(summary_text).encode() in response.content
    assert summary_text.encode() not in response.content


def test_profile_contribution_context_with_maria_log_story_happy(
    client: Client, caplog: pytest.LogCaptureFixture, cedar_dataset: CedarDataset
) -> None:
    """Prove stored/missing branches and entry/exit using assert_log_story.

    :param client: Real client; example: request ID "s10-profile-happy".
    :param caplog: Captured application logs; example: INFO records.
    :param cedar_dataset: Imported Cedar; example: Maria has prose, Mike has none.
    :return: None; example: all required beats and privacy assertions pass.
    :raises AssertionError: If beats, identity or body-free logging are absent.
    """
    maria = cedar_dataset.users_by_username["mrodriguez"]
    mike = cedar_dataset.users_by_username["mchen"]
    with capture_experts_logs(caplog, (_VIEW_LOGGER, _SERVICE_LOGGER)):
        client.force_login(maria)
        stored = client.get(
            reverse("profile"), headers={"X-Request-ID": "s10-profile-happy"}
        )
        client.force_login(mike)
        missing = client.get(
            reverse("profile"), headers={"X-Request-ID": "s10-profile-missing"}
        )

    assert stored.status_code == missing.status_code == 200
    assert missing.context["contributions"]["summary"] == ""
    assert_log_story(
        caplog,
        where=_CONTEXT_STORY,
        beats={
            "entry": (
                "beat=entry",
                f"actor_user_id={maria.pk}",
                "request_id=s10-profile-happy",
            ),
            "stored": (
                "beat=branch",
                "summary_state=stored",
                f"subject_user_id={maria.pk}",
                "request_id=s10-profile-happy",
            ),
            "missing": (
                "beat=branch",
                "summary_state=missing",
                f"subject_user_id={mike.pk}",
                "request_id=s10-profile-missing",
            ),
            "exit": (
                "beat=exit",
                "total_points=8200",
                "primary_category=Design",
                "source_count=4",
                "request_id=s10-profile-happy",
            ),
        },
    )
    messages = "\n".join(
        record.getMessage()
        for record in caplog.records
        if record.name in (_VIEW_LOGGER, _SERVICE_LOGGER)
    )
    private_values = (
        maria.email,
        mike.email,
        CEDAR_PASSWORD,
        stored.context["api_token"],
        missing.context["api_token"],
        stored.context["contributions"]["summary"],
        "Cedar Bid Pricing",
        "Internal staffing notes for Cedar",
    )
    assert not any(
        value in messages for value in private_values
    ), "Profile logs exposed private content."


def test_profile_contribution_context_with_anonymous_request_log_story_reject(
    caplog: pytest.LogCaptureFixture, rf: RequestFactory
) -> None:
    """Prove direct anonymous helper rejection before any domain/token write.

    :param caplog: Captured logs; example: authentication_required rejection.
    :param rf: Direct request builder; example: GET without a session.
    :return: None; example: PermissionDenied and unchanged persisted counts.
    :raises AssertionError: If validation is bypassed or secrets are logged.
    """
    request = rf.get(reverse("profile"), headers={"X-Request-ID": "s10-profile-reject"})
    request.user = AnonymousUser()
    models = (Token, ExpertProfile, KarmaAward, AgentInteraction)
    counts = [model.objects.count() for model in models]

    with (
        capture_experts_logs(caplog, (_VIEW_LOGGER, _SERVICE_LOGGER)),
        CaptureQueriesContext(connection) as queries,
        pytest.raises(PermissionDenied),
    ):
        _profile_contribution_context(request)

    assert not queries.captured_queries
    assert [model.objects.count() for model in models] == counts
    assert_log_story(
        caplog,
        where="accounts.views._validate_profile_contribution_request",
        beats={
            "validation": (
                "beat=validation",
                "outcome=rejected",
                "reason=authentication_required",
                "request_id=s10-profile-reject",
            )
        },
    )
    assert not any(
        _CONTEXT_STORY in record.getMessage() or record.name == _SERVICE_LOGGER
        for record in caplog.records
    )


def test_own_profile_with_zero_karma_renders_neutral_category(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Render Nora's authenticated existing profile with zero Karma and neutral category.

    :param client: Real Django client. Example: authenticated Nora.
    :param cedar_dataset: Imported accounts and Karma ledger. Example: Cedar Nora.
    :return: None. Example: no category_label(None) failure or invented primary category.
    :raises AssertionError: Account controls disappear, a category is invented or rendering fails.
    """
    client.force_login(cedar_dataset.users_by_username["nberg"])

    response = client.get(reverse("profile"))

    assert response.status_code == 200
    html = response.content
    assert element_text(find_by_test_id(html, "profile-karma-total")) == "0"
    category = find_by_test_id(html, "profile-primary-category")
    assert element_text(category) == "No primary category"
    assert b'data-testid="profile-summary-toggle"' not in html
    find_by_test_id(html, "profile-edit-btn")
    find_by_test_id(html, "profile-token-field")
