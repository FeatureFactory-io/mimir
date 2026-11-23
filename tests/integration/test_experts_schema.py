"""Prove model validation and database integrity with real persisted awards."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from methodology.models import EventChannel, ExpertProfile, KarmaAward, Playbook
from methodology.models.karma_award import first_release_identity

pytestmark = pytest.mark.django_db

ORIGINAL_EVENT_TIME = datetime(2024, 2, 29, 9, 30, tzinfo=timezone(timedelta(hours=-5)))
NAIVE_EVENT_TIME = ORIGINAL_EVENT_TIME.replace(tzinfo=None)
SOURCE = KarmaAward.SourceKind


@pytest.fixture
def award() -> KarmaAward:
    """Build a valid award for an existing user, with no ledger writes.

    :return: An unsaved consumption award. Example: a five-point GUI copy.
    """
    return KarmaAward(
        recipient=User.objects.create_user(username="award-recipient"),
        event_identity="consumption:gui_copy:1:test-event",
        source_kind=SOURCE.CONSUMPTION,
        event_channel=EventChannel.GUI_COPY,
        points=5,
        category="design",
        occurred_at=ORIGINAL_EVENT_TIME,
    )


def test_karma_award_with_same_event_and_recipient_rejects_duplicate(
    award: KarmaAward,
) -> None:
    """Prove event/recipient uniqueness at the database boundary.

    :param award: Award to persist. Example: a five-point GUI copy.
    :return: None.
    :raises AssertionError: If duplicate recipient credit persists.
    """
    award.save()
    award.pk = None
    award._state.adding = True
    with pytest.raises(IntegrityError), transaction.atomic():
        award.save()
    assert KarmaAward.objects.count() == 1


def test_karma_award_with_same_event_and_different_recipient_allows_pair(
    award: KarmaAward,
) -> None:
    """Prove paired consumption awards retain the original event timestamp.

    :param award: First recipient's award. Example: a five-point GUI copy.
    :return: None.
    :raises AssertionError: If distinct recipient rows cannot coexist.
    """
    first_recipient = award.recipient
    second_recipient = User.objects.create_user(username="other-recipient")
    award.save()
    award.pk = None
    award._state.adding = True
    award.recipient = second_recipient
    award.save()
    rows = KarmaAward.objects.filter(event_identity=award.event_identity)
    assert set(rows.values_list("recipient_id", "occurred_at")) == {
        (first_recipient.pk, ORIGINAL_EVENT_TIME.astimezone(UTC)),
        (second_recipient.pk, ORIGINAL_EVENT_TIME.astimezone(UTC)),
    }
    first_recipient.delete()
    assert rows.get().recipient_id == second_recipient.pk


def test_karma_award_with_second_release_recipient_rejects_duplicate_playbook(
    award: KarmaAward,
) -> None:
    """Prove author changes cannot create another first-release award.

    :param award: Award for the released playbook. Example: a Design release.
    :return: None.
    :raises AssertionError: If two awards persist for the same playbook.
    """
    book = Playbook.objects.create(
        name="Design handbook", category="design", author=award.recipient
    )
    award.source_kind = SOURCE.RELEASE
    award.event_channel = EventChannel.RELEASE
    award.playbook_id_snapshot = book.pk
    award.event_identity = first_release_identity(book.pk)
    assert award.event_identity == f"first_release:{book.pk}"
    award.save()

    other_recipient = User.objects.create_user(username="new-author")
    duplicate = KarmaAward(
        recipient=other_recipient,
        event_identity="a-different-release-identity",
        source_kind=SOURCE.RELEASE,
        event_channel=EventChannel.HISTORICAL,
        points=award.points,
        category=award.category,
        playbook_id_snapshot=book.pk,
        occurred_at=award.occurred_at,
    )
    # Use a distinct historical key to isolate this constraint from the live anchor.
    with pytest.raises(IntegrityError), transaction.atomic():
        KarmaAward.objects.bulk_create([duplicate])
    playbook_id = book.pk
    book.delete()
    assert KarmaAward.objects.get().playbook_id_snapshot == playbook_id


@pytest.mark.parametrize("points", [0, -1])
def test_karma_award_with_nonpositive_points_rejects(
    award: KarmaAward, points: int
) -> None:
    """Prove zero and negative points fail both model and database checks.

    :param award: Award to invalidate. Example: a five-point GUI copy.
    :param points: Invalid amount. Example: 0.
    :return: None.
    :raises AssertionError: If nonpositive awards persist.
    """
    award.points = points
    with pytest.raises(ValidationError) as exc:
        award.save()
    assert "points" in exc.value.message_dict
    with pytest.raises(IntegrityError), transaction.atomic():
        KarmaAward.objects.bulk_create([award])
    assert not KarmaAward.objects.exists()


def test_expert_profile_with_same_user_rejects_duplicate(award: KarmaAward) -> None:
    """Prove one stored profile exists per account.

    :param award: Award providing an existing account. Example: a GUI copy.
    :return: None.
    :raises AssertionError: If duplicate profiles persist.
    """
    profile = ExpertProfile(
        user=award.recipient, contribution_summary="Published evidence."
    )
    profile.full_clean()
    profile.save()

    with pytest.raises(IntegrityError), transaction.atomic():
        ExpertProfile.objects.create(user=award.recipient)
    assert (
        ExpertProfile.objects.get(user=award.recipient).contribution_summary
        == "Published evidence."
    )


@pytest.mark.parametrize(
    "entity_type, entity_id", [(None, 8), ("skill", None), ("", 8), ("skill", 0)]
)
def test_karma_award_with_unpaired_entity_snapshots_rejects(
    award: KarmaAward, entity_type: str | None, entity_id: int | None
) -> None:
    """Prove entity snapshot pairing, including SQL NULL behavior.

    :param award: Award to invalidate. Example: a five-point GUI copy.
    :param entity_type: Optional entity kind. Example: "skill".
    :param entity_id: Optional entity ID. Example: None.
    :return: None.
    :raises AssertionError: If an incomplete snapshot persists.
    """
    award.entity_type_snapshot = entity_type
    award.entity_id_snapshot = entity_id
    with pytest.raises(ValidationError):
        award.clean()
    with pytest.raises(IntegrityError), transaction.atomic():
        KarmaAward.objects.bulk_create([award])


@pytest.mark.parametrize(
    "source, channel",
    [
        (SOURCE.RELEASE, EventChannel.GUI_COPY),
        (SOURCE.CONSUMPTION, EventChannel.ACCEPTED_CHANGE),
        (SOURCE.MINOR, EventChannel.MCP_DETAIL),
        (SOURCE.LEARNING, "unsupported-channel"),
    ],
)
def test_karma_award_with_invalid_source_channel_pair_rejects(
    award: KarmaAward, source: str, channel: str
) -> None:
    """Reject invalid explicit pairs at both validation boundaries.

    :param award: Award to invalidate. Example: a five-point GUI copy.
    :param source: Award source. Example: "minor".
    :param channel: Incompatible channel. Example: "mcp_detail".
    :return: None.
    :raises AssertionError: If an invalid pair is allowed.
    """
    award.source_kind = source
    award.event_channel = channel
    with pytest.raises(ValidationError) as exc:
        award.clean()
    assert "event_channel" in exc.value.message_dict
    with pytest.raises(IntegrityError), transaction.atomic():
        KarmaAward.objects.bulk_create([award])


def test_karma_award_with_unknown_historical_release_allows_null_content(
    award: KarmaAward,
) -> None:
    """Preserve unknown content and require canonical keys for known releases.

    :param award: Award to convert. Example: a historical Design release.
    :return: None.
    :raises AssertionError: If unknown history or known release keys are mishandled.
    """
    award.source_kind = SOURCE.RELEASE
    award.event_channel = EventChannel.HISTORICAL
    award.event_identity = "historical:unknown-release"
    award.save()
    assert KarmaAward.objects.get().playbook_id_snapshot is None

    award.pk = None
    award._state.adding = True
    award.event_channel = EventChannel.RELEASE
    with pytest.raises(ValidationError) as exc:
        award.save()
    assert "playbook_id_snapshot" in exc.value.message_dict

    award.event_channel = EventChannel.HISTORICAL
    award.playbook_id_snapshot = 17
    with pytest.raises(ValidationError) as exc:
        award.save()
    assert "event_identity" in exc.value.message_dict


def test_karma_award_with_live_anchor_conflict_rejects(award: KarmaAward) -> None:
    """Protect a non-consumption live event independently of recipient.

    :param award: Award to convert. Example: an accepted change award.
    :return: None.
    :raises AssertionError: If the same live anchor credits two recipients.
    """
    award.source_kind = SOURCE.MAJOR
    award.event_channel = EventChannel.ACCEPTED_CHANGE
    award.event_identity = "accepted_change:7"
    award.change_id_snapshot = 7
    award.save()
    award.pk = None
    award._state.adding = True
    award.recipient = User.objects.create_user(username="duplicate-anchor")
    with pytest.raises(IntegrityError), transaction.atomic():
        award.save()


@pytest.mark.parametrize(
    "field, value",
    [
        ("event_identity", " "),
        ("source_kind", "unknown"),
        ("category", "unknown"),
        ("playbook_id_snapshot", True),
        ("playbook_id_snapshot", 0),
        ("change_id_snapshot", -1),
        ("entity_id_snapshot", True),
        ("points", True),
        ("occurred_at", None),
        ("occurred_at", NAIVE_EVENT_TIME),
    ],
)
def test_karma_award_with_invalid_fields_rejects_save(
    award: KarmaAward, field: str, value: object
) -> None:
    """Reject invalid Python values before persistence can coerce them.

    :param award: Award to invalidate. Example: a five-point GUI copy.
    :param field: Field being validated. Example: "points".
    :param value: Invalid input. Example: True.
    :return: None.
    :raises AssertionError: If the field is silently coerced or persisted.
    """
    if field == "entity_id_snapshot":
        award.entity_type_snapshot = "skill"
    setattr(award, field, value)
    with pytest.raises(ValidationError) as exc:
        award.save()
    assert field in exc.value.message_dict
    assert not KarmaAward.objects.exists()


@pytest.mark.parametrize(
    "field, value",
    [
        ("event_identity", "distinct-event"),
        ("category", "research"),
        ("points", 10),
        ("occurred_at", ORIGINAL_EVENT_TIME + timedelta(seconds=1)),
        ("playbook_id_snapshot", 17),
        ("change_id_snapshot", 12),
        ("entity_type_snapshot", "activity"),
        ("entity_id_snapshot", 9),
        ("event_channel", EventChannel.MCP_DETAIL),
        ("source_kind", SOURCE.LEARNING),
        ("recipient_id", None),
    ],
)
def test_karma_award_with_changed_snapshot_rejects_clean_and_save(
    award: KarmaAward, field: str, value: object
) -> None:
    """Guard every logical field even when the replacement is otherwise valid.

    :param award: Award to persist. Example: a five-point GUI copy.
    :param field: Immutable field. Example: "category".
    :param value: Replacement data. Example: "research".
    :return: None.
    :raises AssertionError: If the original snapshot changes.
    """
    award.entity_type_snapshot = "skill"
    award.entity_id_snapshot = 8
    award.save()
    award.save()
    original = getattr(award, field)
    if field == "recipient_id":
        value = User.objects.create_user(username="replacement-recipient").pk
    setattr(award, field, value)
    with pytest.raises(ValidationError):
        award.clean()
    with pytest.raises(ValidationError):
        award.save(update_fields=[field])
    award.refresh_from_db()
    assert getattr(award, field) == original


@pytest.mark.parametrize("playbook_id", [False, True, 0, -1, "17", 17.5])
def test_first_release_identity_with_invalid_id_rejects(playbook_id: object) -> None:
    """Require an actual positive integer PK for the shared key format.

    :param playbook_id: Invalid candidate. Example: True.
    :return: None.
    :raises AssertionError: If an invalid ID produces a key.
    """
    with pytest.raises(ValueError):
        first_release_identity(playbook_id)


def test_expert_profile_with_failure_preserves_last_success(award: KarmaAward) -> None:
    """Accept failed-attempt metadata alongside intact last-good content.

    :param award: Award providing the profile owner. Example: a GUI copy.
    :return: None.
    :raises AssertionError: If validation alters last-good metadata.
    """
    profile = ExpertProfile(
        user=award.recipient,
        summary_status=ExpertProfile.SummaryStatus.FAILURE,
        summary_error_code="provider_failed",
        last_summary_correlation_id="attempt-0",
    )
    profile.full_clean()
    profile.save()
    profile.contribution_summary = "Published evidence."
    profile.summary_updated_at = ORIGINAL_EVENT_TIME
    profile.summary_status = ExpertProfile.SummaryStatus.SUCCESS
    profile.summary_error_code = ""
    profile.last_summary_correlation_id = "success-1"
    profile.full_clean()
    profile.save()
    profile.summary_status = ExpertProfile.SummaryStatus.FAILURE
    profile.summary_error_code = "provider_failed"
    profile.last_summary_correlation_id = "attempt-2"
    profile.full_clean()
    profile.save()
    profile.refresh_from_db()
    assert profile.contribution_summary == "Published evidence."
    assert profile.summary_updated_at == ORIGINAL_EVENT_TIME
    assert profile.summary_error_code == "provider_failed"
    assert profile.last_summary_correlation_id == "attempt-2"


@pytest.mark.parametrize(
    "status, overrides, invalid_field",
    [
        ("unknown", {}, "summary_status"),
        ("never", {"summary_updated_at": ORIGINAL_EVENT_TIME}, "summary_updated_at"),
        (
            "success",
            {
                "contribution_summary": "Published evidence.",
                "last_summary_correlation_id": "success-1",
            },
            "summary_updated_at",
        ),
        (
            "success",
            {
                "summary_updated_at": ORIGINAL_EVENT_TIME,
                "last_summary_correlation_id": "success-1",
            },
            "contribution_summary",
        ),
        ("failure", {"last_summary_correlation_id": "attempt-1"}, "summary_error_code"),
        (
            "failure",
            {"summary_error_code": "provider_failed"},
            "last_summary_correlation_id",
        ),
        (
            "failure",
            {
                "summary_error_code": "provider_failed",
                "last_summary_correlation_id": "attempt-1",
                "summary_updated_at": NAIVE_EVENT_TIME,
            },
            "summary_updated_at",
        ),
    ],
)
def test_expert_profile_with_inconsistent_metadata_rejects(
    award: KarmaAward, status: str, overrides: dict[str, object], invalid_field: str
) -> None:
    """Reject inconsistent status, attempt details and last-good timestamps.

    :param award: Award providing the profile owner. Example: a GUI copy.
    :param status: Refresh status under test. Example: "failure".
    :param overrides: Metadata being validated. Example: {"summary_error_code": "provider_failed"}.
    :param invalid_field: Field with an expected error. Example: "last_summary_correlation_id".
    :return: None.
    :raises AssertionError: If inconsistent metadata passes validation.
    """
    profile = ExpertProfile(user=award.recipient, summary_status=status, **overrides)
    with pytest.raises(ValidationError) as exc:
        profile.clean()
    assert invalid_field in exc.value.message_dict
