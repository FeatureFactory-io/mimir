"""Real-data presentation and log-story contracts for ranked expert cards."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, asdict, replace

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from methodology.models import EventChannel, ExpertProfile, KarmaAward, Playbook
from methodology.services.expert_card_presentation import ExpertCardPresentationService
from methodology.services.experts_service import ExpertsService
from tests.support.experts_data import CedarDataset
from tests.support.experts_logs import capture_experts_logs
from tests.support.log_story import assert_log_story

_LOGGER = "methodology.services.expert_card_presentation"
_STORY = "ExpertCardPresentationService.present"
_CORRELATION = "cedar-s04"


@pytest.mark.django_db
def test_present_with_stored_summary_preserves_public_prose(
    cedar_dataset: CedarDataset,
) -> None:
    """Prove original prose and Maria's formatted public fields.

    :param cedar_dataset: Readable baseline rows and independent oracle.
    :return: None. Example: approved prose remains byte-for-byte unchanged.
    :raises AssertionError: If prose, display values, order or allowlist differ.
    """
    projections = ExpertsService().list_leaders("design", correlation_id=_CORRELATION)
    presenter = ExpertCardPresentationService()
    with CaptureQueriesContext(connection) as queries:
        summaries = dict(
            ExpertProfile.objects.filter(
                user_id__in=[projection.user_id for projection in projections]
            ).values_list("user_id", "contribution_summary")
        )
        cards = tuple(
            presenter.present(
                projection,
                summaries.get(projection.user_id),
                correlation_id=_CORRELATION,
            )
            for projection in projections
        )
    assert len(queries) == 1
    assert [card.username for card in cards] == cedar_dataset.oracle[
        "expected_design_order"
    ]
    maria = next(
        person
        for person in cedar_dataset.oracle["people"]
        if person["username"] == "mrodriguez"
    )
    assert asdict(cards[1]) == {
        "username": "mrodriguez",
        "display_name": "Maria Rodriguez",
        "initials": "MR",
        "formatted_karma": "8,200",
        "primary_category": "Design",
        "hint": maria["summary"],
        "hint_source": "stored_summary",
    }
    assert cards[1].hint.endswith(
        "availability and project fit still require a conversation."
    )
    with pytest.raises(FrozenInstanceError):
        cards[1].hint = "changed"


@pytest.mark.django_db
def test_present_with_missing_summary_uses_live_numeric_fallback(
    cedar_dataset: CedarDataset,
) -> None:
    """Prove None/empty/blank fallback and updated independent live counts.

    :param cedar_dataset: Mike's public books, profile and persisted awards.
    :return: None. Example: Mike displays "2 released playbooks · 47 copies".
    :raises AssertionError: If stale, aggregate-consumption or fixture counts leak in.
    """
    mike = cedar_dataset.users_by_username["mchen"]
    service = ExpertsService()
    presenter = ExpertCardPresentationService()
    profile = ExpertProfile.objects.get(user_id=mike.pk)
    assert profile.contribution_summary == ""
    assert (
        KarmaAward.objects.filter(
            recipient=mike, source_kind=KarmaAward.SourceKind.CONSUMPTION
        ).count()
        == 470
    )
    projection = service.project_user(mike.pk)
    for summary in (None, profile.contribution_summary, " \t\n"):
        card = presenter.present(projection, summary, correlation_id=_CORRELATION)
        assert card.hint == "2 released playbooks · 47 copies"
        assert card.hint_source == "live_counts"
    book = cedar_dataset.playbooks_by_pk[6204]
    assert (
        Playbook.objects.filter(pk=book.pk, visibility="public").update(
            visibility="private"
        )
        == 1
    )
    KarmaAward.objects.create(
        recipient=mike,
        category="development",
        source_kind=KarmaAward.SourceKind.CONSUMPTION,
        event_channel=EventChannel.GUI_COPY,
        event_identity="cedar-test:presenter-gui-copy",
        points=5,
        occurred_at=timezone.now(),
    )
    fresh_card = presenter.present(
        service.project_user(mike.pk), None, correlation_id=_CORRELATION
    )
    assert fresh_card.hint == "1 released playbook · 48 copies"
    assert fresh_card.formatted_karma == "12,455"
    assert fresh_card.primary_category == "Development"


@pytest.mark.django_db
def test_present_with_invalid_projection_rejects_input(
    cedar_dataset: CedarDataset,
) -> None:
    """Cover invalid identity, category, totals, counts and call arguments.

    :param cedar_dataset: Real baseline from which to derive malformed copies.
    :return: None. Example: each invalid projection raises ValueError.
    :raises AssertionError: If an invalid projection is accepted.
    """
    projection = ExpertsService().project_user(cedar_dataset.user_ids["mrodriguez"])
    presenter = ExpertCardPresentationService()
    with pytest.raises(ValueError, match="projection"):
        presenter.present(None, None, correlation_id=_CORRELATION)
    for field_name, invalid_values, message in (
        ("user_id", (0, True), "ID"),
        ("username", (" ", None), "username"),
        ("display_name", ("\n", 7), "name"),
        ("total_points", (0, -1, 2.5, True), "total"),
        ("primary_category", (None, "unknown"), "category"),
        ("released_public_playbook_count", (-1, 2.5, True), "counts"),
        ("successful_gui_copy_count", (-1, "47", False), "counts"),
    ):
        for invalid_value in invalid_values:
            invalid_projection = replace(projection, **{field_name: invalid_value})
            with pytest.raises(ValueError, match=message):
                presenter.present(invalid_projection, None, correlation_id=_CORRELATION)
    with pytest.raises(ValueError, match="summary"):
        presenter.present(projection, 7, correlation_id=_CORRELATION)
    for invalid_correlation in ("", "bad\nline", "a" * 101, None):
        with pytest.raises(ValueError, match="correlation"):
            presenter.present(projection, None, correlation_id=invalid_correlation)


@pytest.mark.django_db
def test_expert_card_log_story_happy(
    cedar_dataset: CedarDataset, caplog: pytest.LogCaptureFixture
) -> None:
    """Capture both hint-source branches with the shared log-story helper.

    :param cedar_dataset: Maria and Mike's persisted public and private data.
    :param caplog: Real captured logs. Example: stored-summary branch records.
    :return: None. Example: entry, branch and exit proven for both sources.
    :raises AssertionError: If a required beat is missing or sensitive data appears.
    """
    presenter = ExpertCardPresentationService()
    for username, source, reason in (
        ("mrodriguez", "stored_summary", "stored_public_prose"),
        ("mchen", "live_counts", "no_stored_public_prose"),
    ):
        caplog.clear()
        subject = cedar_dataset.users_by_username[username]
        projection = ExpertsService().project_user(subject.pk)
        summary = ExpertProfile.objects.get(user_id=subject.pk).contribution_summary
        correlation_id = f"{_CORRELATION}-{source}"
        with capture_experts_logs(caplog, (_LOGGER,)):
            presenter.present(projection, summary, correlation_id=correlation_id)
        context = (f"subject_id={subject.pk}", f"correlation_id={correlation_id}")
        assert_log_story(
            caplog,
            where=_STORY,
            beats={
                "entry": ("| entry |", *context),
                "branch": (
                    "| branch |",
                    f"hint_source={source}",
                    f"reason={reason}",
                    *context,
                ),
                "exit": ("| exit |", "status=ok", *context),
            },
        )
        assert username not in caplog.text
        assert projection.display_name not in caplog.text
        assert subject.email not in caplog.text
        if summary:
            assert summary not in caplog.text


@pytest.mark.django_db
def test_expert_card_log_story_reject(
    cedar_dataset: CedarDataset, caplog: pytest.LogCaptureFixture
) -> None:
    """Prove sanitized validation rejection without successful exit.

    :param cedar_dataset: Maria's real baseline account and projection.
    :param caplog: Real captured logs. Example: invalid-projection validation record.
    :return: None. Example: entry/reject beats present and no sensitive payload.
    :raises AssertionError: If rejection evidence is absent or misleading.
    """
    subject = cedar_dataset.users_by_username["mrodriguez"]
    projection = ExpertsService().project_user(subject.pk)
    presenter = ExpertCardPresentationService()
    private_sentinel = "s04-private-profile-sentinel"
    with capture_experts_logs(caplog, (_LOGGER,)):
        with pytest.raises(ValueError, match="counts"):
            presenter.present(
                replace(projection, successful_gui_copy_count=-1),
                private_sentinel,
                correlation_id=_CORRELATION,
            )
        with pytest.raises(ValueError, match="correlation"):
            presenter.present(projection, None, correlation_id=subject.email)
    assert_log_story(
        caplog,
        where=_STORY,
        beats={
            "entry": (
                "| entry |",
                f"subject_id={subject.pk}",
                f"correlation_id={_CORRELATION}",
            ),
            "validation": (
                "| validation |",
                "status=rejected",
                "reason=invalid_projection",
                f"correlation_id={_CORRELATION}",
            ),
            "masked": (
                "| validation |",
                "status=rejected",
                "reason=invalid_projection",
                "correlation_id=-",
            ),
        },
    )
    presenter_log = "\n".join(
        record.getMessage() for record in caplog.records if record.name == _LOGGER
    )
    for omitted in (
        "| exit |",
        private_sentinel,
        subject.email,
        projection.display_name,
    ):
        assert omitted not in presenter_log
