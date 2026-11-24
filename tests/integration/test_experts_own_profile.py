"""S10 real-DB profile integration and log-story contracts."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.test import Client, RequestFactory
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.authtoken.models import Token

from accounts.views import _profile_contribution_context
from methodology.models import AgentInteraction, ExpertProfile, KarmaAward
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset
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


def test_profile_view_with_maria_preserves_account_controls(client: Client) -> None:
    """Verify account controls, existing sections and token identity survive.

    :param client: Real Django client; example: Maria with an existing token.
    :return: None; example: all pre-existing profile controls remain.
    :raises AssertionError: If GET rotates token or removes account functions.
    """
    raise NotImplementedError()


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
    raise NotImplementedError()


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


def test_own_profile_with_zero_karma_renders_neutral_category() -> None:
    """Render Nora's authenticated existing profile with zero Karma and neutral category.

    :return: None. Example: no category_label(None) failure or invented primary category.
    :raises AssertionError: Account controls disappear, a category is invented or rendering fails.
    """
    raise NotImplementedError()
