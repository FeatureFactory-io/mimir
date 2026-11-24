"""Real DB and Django-client proofs for successful-copy receipts."""

from __future__ import annotations

import json
from uuid import UUID

import pytest
from _pytest.logging import LogCaptureFixture
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.http import HttpResponse
from django.test import Client
from django.urls import reverse

from methodology.models import EventChannel, KarmaAward
from methodology.services.karma_service import KarmaService
from tests.support.experts_data import CedarDataset
from tests.support.log_story import assert_log_story

ACTIVITY_ID = 6203
PLAYBOOK_ID = 6201
WORKFLOW_ID = 6202
EVENT_ID = UUID("55f41062-b673-4698-bf16-91f871b6408f")
REQUEST_ID = "cedar-copy-receipt-01"
RECEIPT_VIEW = "copy_success_receipt"
CONSUMPTION_SERVICE = "KarmaService.award_successful_consumption"


def _payload() -> dict[str, object]:
    """Return the valid browser report. Example: the Cedar activity 6203 copy."""
    return {
        "entity_type": "activity",
        "entity_id": ACTIVITY_ID,
        "event_identity": str(EVENT_ID),
    }


def _activity_url() -> str:
    """Return Cedar activity's real detail URL."""
    return reverse(
        "activity_detail",
        kwargs={
            "playbook_pk": PLAYBOOK_ID,
            "workflow_pk": WORKFLOW_ID,
            "activity_pk": ACTIVITY_ID,
        },
    )


def _post_receipt(
    client: Client, payload: dict[str, object] | str, **headers: str
) -> HttpResponse:
    """Post JSON to the production receipt route with a correlatable request ID.

    :param client: Real Django client. Example: authenticated Maria.
    :param payload: Browser report or raw JSON. Example: _payload().
    :param headers: Optional Django test headers. Example: HTTP_X_CSRFTOKEN.
    :return: Real receipt response. Example: HTTP 200 with an applied status.
    """
    return client.post(
        reverse("karma_copy_receipt"),
        data=payload,
        content_type="application/json",
        HTTP_X_REQUEST_ID=REQUEST_ID,
        **headers,
    )


def _total_points(user: User) -> int:
    """Read one recipient's real awarded total. Example: 8205 for Maria."""
    return user.karma_awards.aggregate(points=Sum("points", default=0))["points"]


@pytest.mark.django_db
def test_award_successful_consumption_with_other_author_creates_atomic_pair(
    cedar_dataset: CedarDataset,
) -> None:
    """Prove both real awards and immutable attribution for one action."""
    maria = cedar_dataset.users_by_username["mrodriguez"]
    mike = cedar_dataset.users_by_username["mchen"]
    learning, consumption = KarmaService.award_successful_consumption(
        maria, "activity", ACTIVITY_ID, EVENT_ID, channel="gui_copy"
    )

    assert learning.created and consumption.created
    assert learning.award is not None and consumption.award is not None
    identity = f"consumption:gui_copy:{maria.pk}:{EVENT_ID}"
    awards = KarmaAward.objects.filter(event_identity=identity)
    assert set(awards.values_list("recipient_id", "source_kind", "points")) == {
        (maria.pk, KarmaAward.SourceKind.LEARNING, 5),
        (mike.pk, KarmaAward.SourceKind.CONSUMPTION, 5),
    }
    assert list(
        awards.values_list(
            "category",
            "playbook_id_snapshot",
            "change_id_snapshot",
            "event_channel",
            "entity_type_snapshot",
            "entity_id_snapshot",
        )
        .distinct()
        .order_by()
    ) == [
        (
            "development",
            PLAYBOOK_ID,
            None,
            EventChannel.GUI_COPY,
            "activity",
            ACTIVITY_ID,
        )
    ]
    assert learning.award.occurred_at == consumption.award.occurred_at
    assert (_total_points(maria), _total_points(mike)) == (8205, 12455)

    with pytest.raises(ValidationError, match="conflict"):
        KarmaService.award_successful_consumption(
            maria, "playbook", PLAYBOOK_ID, EVENT_ID, channel="gui_copy"
        )
    assert awards.count() == 2


@pytest.mark.django_db
def test_copy_receipt_with_authenticated_authorized_activity_credits_both(
    cedar_dataset: CedarDataset,
) -> None:
    """Prove an authenticated, CSRF-valid session credits both parties."""
    maria = cedar_dataset.users_by_username["mrodriguez"]
    mike = cedar_dataset.users_by_username["mchen"]
    client = Client(enforce_csrf_checks=True)
    client.force_login(maria)
    assert client.get(_activity_url()).status_code == 200
    csrf_token = client.cookies[settings.CSRF_COOKIE_NAME].value

    response = _post_receipt(client, _payload(), HTTP_X_CSRFTOKEN=csrf_token)

    assert response.status_code == 200
    assert response.json()["status"] == "applied"
    retry = _post_receipt(client, _payload(), HTTP_X_CSRFTOKEN=csrf_token)
    assert retry.status_code == 200
    assert retry.json()["status"] == "replayed"
    assert (_total_points(maria), _total_points(mike)) == (8205, 12455)


@pytest.mark.django_db
def test_copy_receipt_with_render_only_creates_no_awards(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Prove detail/list/embed rendering leaves the live ledger unchanged."""
    client.force_login(cedar_dataset.users_by_username["mrodriguez"])
    before = KarmaAward.objects.count()
    url = _activity_url()
    list_url = reverse(
        "activity_list",
        kwargs={"playbook_pk": PLAYBOOK_ID, "workflow_pk": WORKFLOW_ID},
    )

    assert client.get(url).status_code == 200
    assert client.get(url, {"embed": "1"}).status_code == 200
    assert client.get(list_url).status_code == 200
    assert KarmaAward.objects.count() == before


@pytest.mark.django_db
def test_copy_receipt_with_forbidden_fields_rejects_request(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Prove request inputs cannot alter attribution or set trusted metadata."""
    client.force_login(cedar_dataset.users_by_username["mrodriguez"])
    before = KarmaAward.objects.count()
    payload = _payload()
    candidates = (
        *(
            {**payload, field: "override"}
            for field in (
                "actor",
                "author",
                "category",
                "points",
                "source_kind",
                "event_channel",
                "occurred_at",
            )
        ),
        {**payload, "event_identity": "malformed"},
        {**payload, "entity_type": "user"},
        {**payload, "entity_id": True},
        {**payload, "entity_id": 2**63},
        {**payload, "entity_id": "6203"},
        json.dumps(list(payload.items())),
        json.dumps(payload)[:-1] + ', "entity_id": 6203}',
        "{brokenJSON",
    )

    for candidate in candidates:
        response = _post_receipt(client, candidate)
        assert response.status_code == 400
        assert response.json() == {"status": "rejected", "reason": "invalid_payload"}
    assert KarmaAward.objects.count() == before


@pytest.mark.django_db
def test_copy_receipt_with_unauthorized_entity_creates_no_awards(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Prove private playbooks and creator-or-staff PIPs recheck access."""
    maria = cedar_dataset.users_by_username["mrodriguez"]
    mike = cedar_dataset.users_by_username["mchen"]
    client.force_login(maria)
    book = cedar_dataset.playbooks_by_pk[PLAYBOOK_ID]
    book.visibility = "private"
    book.save(update_fields=["visibility"])
    before = KarmaAward.objects.count()

    assert _post_receipt(client, _payload()).status_code == 404

    pip = cedar_dataset.pips_by_key["HIST-MARIA-DESIGN-01"]
    learner = cedar_dataset.users_by_username["jlee"]
    client.force_login(learner)
    pip_payload = {**_payload(), "entity_type": "pip", "entity_id": pip.pk}
    assert _post_receipt(client, pip_payload).status_code == 404
    assert KarmaAward.objects.count() == before

    client.force_login(maria)
    assert _post_receipt(client, pip_payload).json() == {
        "status": "skipped",
        "reason": "self_consumption",
    }
    assert KarmaAward.objects.count() == before

    client.force_login(mike)
    assert _post_receipt(client, pip_payload).json()["status"] == "applied"
    hana = cedar_dataset.users_by_username["hkim"]
    assert (_total_points(maria), _total_points(mike), _total_points(hana)) == (
        8200,
        12455,
        5805,
    )


@pytest.mark.django_db
def test_copy_receipt_with_missing_csrf_rejects_request(
    cedar_dataset: CedarDataset,
) -> None:
    """Prove session receipts remain CSRF protected."""
    client = Client(enforce_csrf_checks=True)
    client.force_login(cedar_dataset.users_by_username["mrodriguez"])
    before = KarmaAward.objects.count()

    assert _post_receipt(client, _payload()).status_code == 403
    assert KarmaAward.objects.count() == before


@pytest.mark.django_db
def test_copy_receipt_log_story_happy(
    client: Client, caplog: LogCaptureFixture, cedar_dataset: CedarDataset
) -> None:
    """Prove both receipt outcomes report the original persisted event time."""
    maria = cedar_dataset.users_by_username["mrodriguez"]
    mike = cedar_dataset.users_by_username["mchen"]
    client.force_login(maria)
    identity = f"consumption:gui_copy:{maria.pk}:{EVENT_ID}"
    trace = f"request_id={REQUEST_ID}"

    with caplog.at_level("INFO"):
        assert _post_receipt(client, _payload()).status_code == 200

    awards = KarmaAward.objects.filter(event_identity=identity)
    original_awards = dict(awards.values_list("pk", "occurred_at"))
    assert len(original_awards) == 2
    (occurred_at,) = set(original_awards.values())
    recorded_time = f"occurred_at={occurred_at.isoformat()}"
    eligibility = (
        "| branch |",
        f"event_identity={identity}",
        f"actor_id={maria.pk}",
        f"playbook_id={PLAYBOOK_ID}",
        f"author_id={mike.pk}",
        "category=development",
        "reason=eligible",
    )

    assert_log_story(
        caplog,
        where=RECEIPT_VIEW,
        beats={
            "entry": ("| entry |", trace, f"actor_id={maria.pk}", "operation=gui_copy"),
            "validation": (
                "| validation |",
                trace,
                "validated",
                "entity_type=activity",
                f"entity_id={ACTIVITY_ID}",
                str(EVENT_ID),
            ),
            "exit": ("| exit |", trace, str(EVENT_ID), "status=applied"),
        },
    )
    assert_log_story(
        caplog,
        where=CONSUMPTION_SERVICE,
        beats={
            "validation": (
                "| validation |",
                f"actor_id={maria.pk}",
                f"playbook_id={PLAYBOOK_ID}",
                "channel=gui_copy",
            ),
            "eligibility": eligibility,
            "processing": (
                "| processing |",
                identity,
                f"learner_id={maria.pk}",
                f"author_id={mike.pk}",
                "points=5",
                "status=applied",
            ),
            "created": (
                "| exit |",
                f"event_identity={identity}",
                "created_count=2",
                recorded_time,
            ),
        },
    )
    assert maria.email not in caplog.text and mike.email not in caplog.text

    caplog.clear()
    with caplog.at_level("INFO"):
        replay = _post_receipt(client, _payload())
    assert replay.status_code == 200 and replay.json() == {"status": "replayed"}
    assert dict(awards.values_list("pk", "occurred_at")) == original_awards
    assert_log_story(
        caplog,
        where=RECEIPT_VIEW,
        beats={"exit": ("| exit |", trace, str(EVENT_ID), "status=replayed")},
    )
    assert_log_story(
        caplog,
        where=CONSUMPTION_SERVICE,
        beats={
            "eligibility": eligibility,
            "processing": ("| processing |", identity, "points=5", "status=replayed"),
            "duplicate": (
                "| exit |",
                f"event_identity={identity}",
                "duplicate",
                recorded_time,
            ),
        },
    )
    assert maria.email not in caplog.text and mike.email not in caplog.text


@pytest.mark.django_db
def test_copy_receipt_log_story_reject(
    client: Client, caplog: LogCaptureFixture, cedar_dataset: CedarDataset
) -> None:
    """Prove safe malformed, denied and excluded branches write no awards."""
    client.force_login(cedar_dataset.users_by_username["mrodriguez"])
    before = KarmaAward.objects.count()
    private_content = "private-clipboard-prompt-content"
    with caplog.at_level("INFO"):
        assert (
            _post_receipt(client, {**_payload(), "prompt": private_content}).status_code
            == 400
        )
        assert (
            _post_receipt(client, {**_payload(), "entity_id": 2**62}).status_code == 404
        )
        assert (
            KarmaService.award_successful_consumption(
                AnonymousUser(), "activity", ACTIVITY_ID, EVENT_ID, channel="gui_copy"
            )
            == ()
        )

    assert_log_story(
        caplog,
        where=RECEIPT_VIEW,
        beats={
            reason: (
                "| branch |",
                f"request_id={REQUEST_ID}",
                f"reason={reason}",
                "awards=0",
            )
            for reason in ("invalid_payload", "access_denied")
        },
    )
    assert_log_story(
        caplog,
        where=CONSUMPTION_SERVICE,
        beats={"guest": ("| branch |", "reason=guest", "channel=gui_copy", "awards=0")},
    )
    assert KarmaAward.objects.count() == before
    assert private_content not in caplog.text
    assert not any(
        CONSUMPTION_SERVICE in record.getMessage()
        and any(
            fragment in record.getMessage()
            for fragment in ("reason=eligible", "| processing |", "| exit |")
        )
        for record in caplog.records
    )


@pytest.mark.django_db
def test_award_successful_consumption_with_self_activity_returns_no_awards() -> None:
    """Prove authorized self-consumption has no domain effect.

    :return: None after empty result, ledger and 12450/8200/47 assertions.
    :raises AssertionError: If self-copy changes any award or projection.
    """
    raise NotImplementedError()


@pytest.mark.django_db
def test_copy_receipt_with_self_activity_returns_successful_exclusion() -> None:
    """Exercise a genuine strict-CSRF self-copy receipt.

    :return: None after HTTP 200, self-exclusion and unchanged-domain assertions.
    :raises AssertionError: If real token, route, result or effects differ.
    """
    raise NotImplementedError()


@pytest.mark.django_db
def test_copy_receipt_with_self_activity_without_csrf_returns_forbidden() -> None:
    """Prove authenticated self-copy does not bypass CSRF middleware.

    :return: None after HTTP 403 and unchanged ledger assertions.
    :raises AssertionError: If a tokenless session receipt succeeds.
    """
    raise NotImplementedError()


@pytest.mark.django_db
def test_copy_receipt_with_self_activity_log_story_happy(
    caplog: LogCaptureFixture,
) -> None:
    """Prove the real successful exclusion story without sensitive bodies.

    :param caplog: INFO records from the strict-CSRF real request.
    :return: None after correlated ordered beats and no-persistence assertions.
    :raises AssertionError: If logging omits exclusion or leaks request content.
    """
    raise NotImplementedError()
