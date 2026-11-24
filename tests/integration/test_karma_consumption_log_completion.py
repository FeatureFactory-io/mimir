"""Certify complete, safe exclusion stories using real Cedar ORM state."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest
from django.contrib.auth.models import AnonymousUser, User
from django.db.models import Sum
from pytest import LogCaptureFixture

from methodology.models import KarmaAward
from methodology.services.karma_service import KarmaService
from tests.support.experts_data import CedarDataset
from tests.support.experts_logs import capture_experts_logs
from tests.support.log_story import assert_log_story

_LOGGER = "methodology.services.karma_service"
_OPERATION = "KarmaService.award_successful_consumption"
_ACTION = UUID("c3600000-0000-4000-8000-000000000040")
_CASES = ("guest", "activity-owner", "pip-author", "pip-creator", "pip-both")
_LEDGER_FIELDS = tuple(field.attname for field in KarmaAward._meta.concrete_fields)


def _state() -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    """Snapshot every immutable field and every recipient total.

    :return: Ordered full ledger and all user totals. Example: (rows, totals).
    :raises AssertionError: If the ORM cannot read the owned test database.
    """
    return (
        tuple(KarmaAward.objects.order_by("pk").values_list(*_LEDGER_FIELDS)),
        tuple(
            User.objects.order_by("pk")
            .annotate(total=Sum("karma_awards__points", default=0))
            .values_list("pk", "total")
        ),
    )


def _case(
    dataset: CedarDataset, case: str
) -> tuple[User | AnonymousUser, str, int, int | None, int | None, str]:
    """Resolve authorized imported identities without inventing entity IDs.

    :param dataset: Owned real fixture. Example: CedarDataset.
    :param case: Explicit exclusion lane. Example: "pip-creator".
    :return: Actor, kind, ID, author, creator and role. Example: Mike/activity/6203.
    :raises ValueError: If a case is outside the finite declared matrix.
    """
    mike = dataset.users_by_username["mchen"]
    maria = dataset.users_by_username["mrodriguez"]
    if case == "guest":
        return AnonymousUser(), "activity", 6203, None, None, "guest"
    if case == "activity-owner":
        return mike, "activity", 6203, mike.pk, None, "self_author"
    if case not in _CASES:
        raise ValueError("Unknown consumption exclusion case.")
    key = "HIST-MARIA-DESIGN-01" if case == "pip-creator" else "HIST-MARIA-DEV-01"
    pip = dataset.pips_by_key[key]
    if case == "pip-both":
        pip.created_by = mike
        pip.save(update_fields=["created_by"])
    actor = maria if case == "pip-creator" else mike
    role = "self_creator" if case == "pip-creator" else "self_author"
    return actor, "pip", pip.pk, pip.playbook.author_id, pip.created_by_id, role


def _assert_story(
    caplog: LogCaptureFixture,
    actor: User | AnonymousUser,
    entity_type: str,
    entity_id: int,
    author_id: int | None,
    creator_id: int | None,
    role: str,
) -> None:
    """Require complete correlated beats and actual role attribution.

    :param caplog: Actual service log capture. Example: caplog.
    :param actor: Real actor or guest. Example: Mike.
    :param entity_type: Authorized kind. Example: "pip".
    :param entity_id: Actual imported ID. Example: the historical proposal PK.
    :param author_id: Real target author. Example: Mike's PK.
    :param creator_id: Real PIP creator, or None. Example: Maria's PK.
    :param role: Expected role, author taking precedence. Example: "self_author".
    :return: None after exact ordered beat and privacy checks.
    :raises AssertionError: Missing beats, wrong identity or private data disclosure.
    """
    messages = [r.getMessage() for r in caplog.records if _OPERATION in r.getMessage()]
    guest = isinstance(actor, AnonymousUser)
    beats = (
        ["entry", "branch", "exit"]
        if guest
        else ["entry", "validation", "branch", "exit"]
    )
    assert [message.split(" | ")[1] for message in messages] == beats
    expected = _base_beats(actor, entity_type, entity_id)
    if not guest:
        details = (
            f"actor_id={actor.pk}",
            f"author_id={author_id}",
            f"pip_creator_id={creator_id}",
            f"exclusion_role={role}",
        )
        expected["branch"] += details
        expected["exit"] += details
        identity = KarmaService._canonical_consumption_identity(
            actor.pk, _ACTION, "mcp_detail"
        )
        expected["exit"] += (f"event_identity={identity}",)
    assert_log_story(caplog, where=_OPERATION, beats=expected)
    assert all("transaction=pending" not in message for message in messages)
    assert all("@" not in message and "password" not in message for message in messages)


def _base_beats(
    actor: User | AnonymousUser, entity_type: str, entity_id: int
) -> dict[str, tuple[str, ...]]:
    """Build independently expected safe entry and exclusion fields.

    :param actor: Actual persisted actor or guest. Example: Mike.
    :param entity_type: Validated target kind. Example: "activity".
    :param entity_id: Actual target ID. Example: 6203.
    :return: Required beat fragments. Example: {"exit": ("created_count=0",)}.
    :raises AssertionError: If an expected log field cannot be represented.
    """
    common = (f"action_uuid={_ACTION}", "channel=mcp_detail")
    entry = (
        f"actor_id={actor.pk}",
        f"entity_type={entity_type}",
        f"entity_id={entity_id}",
    )
    reason = "guest" if isinstance(actor, AnonymousUser) else "self_consumption"
    expected = {
        "entry": ("| entry |", *common, *entry),
        "branch": ("| branch |", *common, f"reason={reason}", "awards=0"),
        "exit": ("| exit |", *common, f"reason={reason}", "created_count=0"),
    }
    if not isinstance(actor, AnonymousUser):
        expected["validation"] = ("| validation |", *common, "authorized")
    return expected


@pytest.mark.django_db
@pytest.mark.parametrize("case", _CASES)
def test_consumption_log_story_with_excluded_actor_completes_without_mutation(
    cedar_dataset: CedarDataset, caplog: LogCaptureFixture, case: str
) -> None:
    """Prove guest, ordinary owner and both independent PIP roles stay unchanged.

    :param cedar_dataset: Real imported history. Example: CedarDataset.
    :param caplog: Real service capture. Example: caplog.
    :param case: Independent restored lane. Example: "pip-author".
    :return: None after an empty outcome, complete story and unchanged full ledger.
    :raises AssertionError: Wrong policy, attribution, missing beat or mutation.
    """
    actor, kind, entity_id, author, creator, role = _case(cedar_dataset, case)
    before = _state()
    with capture_experts_logs(caplog, (_LOGGER,)):
        result = KarmaService.award_successful_consumption(
            actor, kind, entity_id, _ACTION, channel="mcp_detail"
        )
    assert result == ()
    assert _state() == before
    _assert_story(caplog, actor, kind, entity_id, author, creator, role)


@pytest.mark.django_db
@pytest.mark.parametrize("actor", (None, 1), ids=("none", "integer"))
def test_consumption_log_story_with_invalid_actor_preserves_permission_error(
    cedar_dataset: CedarDataset, caplog: LogCaptureFixture, actor: Any
) -> None:
    """Keep unsupported actor rejection owned by the existing authorization path.

    :param cedar_dataset: Real isolated baseline. Example: CedarDataset.
    :param caplog: Actual entry capture. Example: actor_id=None.
    :param actor: Unsupported boundary value. Example: None.
    :return: None after the unchanged PermissionError and full ledger snapshot.
    :raises AssertionError: Logging changes authorization failure or mutates evidence.
    """
    assert cedar_dataset.users_by_username["mchen"].is_staff
    before = _state()
    with capture_experts_logs(caplog, (_LOGGER,)), pytest.raises(PermissionError):
        KarmaService.award_successful_consumption(
            actor, "activity", 6203, _ACTION, channel="mcp_detail"
        )
    assert _state() == before
    messages = [r.getMessage() for r in caplog.records if _OPERATION in r.getMessage()]
    assert len(messages) == 1 and "| entry |" in messages[0]
    assert "actor_id=None" in messages[0]
