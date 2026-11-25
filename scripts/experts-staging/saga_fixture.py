"""Guarded real-ORM companions for explicit fresh-database Saga cases.

There is deliberately no flush, reset, generic mutation or ambient DB fallback.
The caller creates a distinct owned companion lifecycle for each case.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.core import serializers
from django.core.serializers.json import DjangoJSONEncoder
from django.urls import reverse
from methodology.models import Activity, ExpertProfile, KarmaAward, Workflow
from methodology.services.copy_prompt_service import CopyPromptService
from methodology.services.experts_service import ExpertsService

from bootstrap import scope, state, write_private
from saga_contract import (
    ACTORS,
    NORMAL_LOGIN_EXPIRY_SECONDS,
    LoginInterval,
    assert_row_delta,
    validate_case,
    validate_copy_attempts,
    validate_login_observation,
)

logger = logging.getLogger(__name__)
_ROOT = Path("/experts-scope")
_OUTPUT = Path("/output")
_FIXTURE = Path("/app/test-data/experts/cedar-rfp-01.json")
_MAIL = Path("/experts-mail")
_SESSION_FIELDS = frozenset(
    {"_auth_user_id", "_auth_user_backend", "_auth_user_hash", "_session_expiry"}
)


class SnapshotJSONEncoder(DjangoJSONEncoder):
    """Preserve actual datetime microseconds in private evidence, never product JSON."""

    def default(self: SnapshotJSONEncoder, value: Any) -> Any:
        """Encode exact datetime values without Django's millisecond truncation.

        :param value: Actual field value from the real model serializer.
        :return: Full ISO microseconds or the unchanged standard Django encoding.
        :raises TypeError: A field type cannot be serialized normally.
        """
        if isinstance(value, datetime):
            return value.isoformat(timespec="microseconds")
        return super().default(value)


def domain_rows() -> dict[str, dict[str, Any]]:
    """Read every installed concrete model and M2M row at full private precision.

    :return: Model/PK/value map, never printed or exported as public evidence.
    :raises DatabaseError: The actual owned connection cannot read a model.
    """
    models = sorted(
        (
            model
            for model in apps.get_models(include_auto_created=True)
            if not model._meta.proxy
        ),
        key=lambda model: model._meta.label,
    )
    result = {}
    for model in models:
        fields = [
            field.name for field in (*model._meta.fields, *model._meta.many_to_many)
        ]
        encoded = serializers.serialize(
            "json", model.objects.order_by("pk"), fields=fields, cls=SnapshotJSONEncoder
        )
        rows = json.loads(encoded)
        result[model._meta.label_lower] = {str(row["pk"]): row for row in rows}
    return result


def projections() -> dict[str, Any]:
    """Read actual whole-user numeric projections without account details.

    :return: JSON-normalized projections keyed by existing user IDs.
    :raises DatabaseError: An actual projection read fails.
    """
    service = ExpertsService()
    rows = {
        str(pk): asdict(service.project_user(pk))
        for pk in User.objects.values_list("pk", flat=True)
    }
    return json.loads(json.dumps(rows))


def assert_pristine() -> None:
    """Recheck positive ownership and the exact original imported core baseline.

    :return: None before any per-case files or preparation are created.
    :raises ValueError: Actual DB, marker, role, owner or catalog identity differs.
    :raises AssertionError: The baseline was already changed or mail exists.
    """
    scope()
    original = json.loads((_ROOT / "domain-state.json").read_text())
    assert state() == original, "Saga requires a fresh independent baseline."
    assert (original["users"], original["awards"], original["profiles"]) == (
        12,
        2129,
        11,
    )
    assert not list(_MAIL.iterdir()), "A fresh Saga case must have no decision mail."


def prepare_case(case: str) -> None:
    """Prepare only safe oracles from one newly created owned baseline.

    :param case: Implemented lane, e.g. nomination or copy-maria.
    :return: None after exclusive private snapshot and public oracle creation.
    :raises ValueError: Case or actual database ownership differs.
    :raises AssertionError: Baseline rows or required public evidence differ.
    :raises FileExistsError: This owned case was already prepared.
    """
    validate_case(case)
    assert_pristine()
    baseline = {
        "case": case,
        "rows": domain_rows(),
        "projections": projections(),
        "prepared_at": datetime.now(timezone.utc).isoformat(timespec="microseconds"),
    }
    write_private(_ROOT / "saga-baseline.json", baseline)
    oracle = public_oracle(case)
    write_private(_OUTPUT / "saga-oracle.json", oracle)
    logger.info("Saga fixture prepared | case=%s | independent_baseline=true", case)


def public_oracle(case: str) -> dict[str, Any]:
    """Read actual routes/content digests alongside the independent fixture oracle.

    :param case: Validated implemented lane, e.g. nomination.
    :return: Public-only metadata; no token, password or private PIP body.
    :raises AssertionError: Actual initial public prose differs from the fixture.
    """
    validate_case(case)
    document = json.loads(_FIXTURE.read_text())
    people = {person["username"]: person for person in document["people"]}
    public = {name: people[name]["summary"] for name in ("sreed", "mrodriguez")}
    assert all(
        ExpertProfile.objects.get(user__username=name).contribution_summary == prose
        for name, prose in public.items()
    )
    workflow = Workflow.objects.get(
        playbook_id=6101, name="Lead an Accessibility Review"
    )
    return {
        "case": case,
        "operator": "automated_staged_Saga",
        "fixture_sha256": hashlib.sha256(_FIXTURE.read_bytes()).hexdigest(),
        "actor": ACTORS[case],
        "public_summaries": public,
        "workflow_path": reverse("workflow_detail", args=(6101, workflow.pk)),
        **copy_oracle(),
    }


def copy_oracle() -> dict[str, Any]:
    """Build the exact real public prompt oracle without exposing its text.

    :return: Actual activity/workflow names, route, prompt hash and byte length.
    :raises DoesNotExist: The required actual activity is absent.
    """
    activity = Activity.objects.select_related("workflow__playbook").get(pk=6203)
    prompt = CopyPromptService.build_activity_prompt(activity)
    assert prompt
    return {
        "copy_path": reverse("activity_detail", args=(6201, 6202, 6203)),
        "copy_activity_name": activity.name,
        "copy_workflow_name": activity.workflow.name,
        "copy_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "copy_bytes": len(prompt.encode()),
    }


def verify_case(case: str) -> None:
    """Verify all actual effects after the completed native browser lane.

    :param case: Same explicit case prepared before starting the web process.
    :return: None after a bounded public result states only this case's verdict.
    :raises ValueError: Actual database/role/owner identity differs.
    :raises AssertionError: Browser, domain rows, awards, projections or mail differs.
    """
    validate_case(case)
    scope()
    baseline = json.loads((_ROOT / "saga-baseline.json").read_text())
    observed = json.loads((_OUTPUT / "saga-browser.json").read_text())
    additions = verify_case_state(case, baseline, observed)
    result = {
        "case": case,
        "status": "CASE_VERIFIED",
        "scope_rechecked": True,
        "new_awards": len(additions),
        "full_saga_accepted": False,
    }
    write_private(_OUTPUT / "saga-effects.json", result)
    logger.info(
        "Saga fixture verified | case=%s | added_awards=%s", case, len(additions)
    )


def verify_case_state(
    case: str, baseline: dict[str, Any], observed: dict[str, Any]
) -> list[str]:
    """Reconcile full private state with the exact already observed native event.

    :param case: Explicit actual case.
    :param baseline: Private complete original state and preparation time.
    :param observed: Safe actual browser observations, including its precise login.
    :return: Actual allowed award IDs; raises AssertionError for any other effect.
    """
    assert baseline["case"] == observed["case"] == case
    assert observed["status"] == "BROWSER_OBSERVED"
    login = validate_login_observation(
        case,
        observed.get("login_observation"),
        baseline["prepared_at"],
        datetime.now(timezone.utc).isoformat(timespec="microseconds"),
    )
    additions = assert_row_delta(case, baseline["rows"], domain_rows(), login)
    verify_actual_session(login)
    expected = expected_projections(case, baseline["projections"])
    assert projections() == expected, "Whole-user projections differ."
    verify_awards(case, observed, additions)
    assert not list(_MAIL.iterdir()), "A read or copy emitted decision mail."
    return additions


def verify_actual_session(login: LoginInterval | None) -> None:
    """Check private decoded state of the exact new observed browser session.

    :param login: Actual native login metadata; None for anonymous reading.
    :return: None after actor/backend/auth-hash/normal expiry agree privately.
    :raises AssertionError: The exact observed session or decoded state differs.
    """
    if login is None:
        return
    matches = [
        row
        for row in Session.objects.all()
        if hashlib.sha256(row.session_key.encode()).hexdigest()
        == login.session_key_sha256
    ]
    assert len(matches) == 1
    user = User.objects.get(username=login.actor)
    actual = matches[0].get_decoded()
    assert actual.keys() == _SESSION_FIELDS
    assert actual["_auth_user_id"] == str(user.pk)
    assert len(settings.AUTHENTICATION_BACKENDS) == 1
    assert actual["_auth_user_backend"] == settings.AUTHENTICATION_BACKENDS[0]
    assert actual["_auth_user_hash"] == user.get_session_auth_hash()
    assert (
        type(actual["_session_expiry"]) is int
        and actual["_session_expiry"] == NORMAL_LOGIN_EXPIRY_SECONDS
    )


def expected_projections(case: str, baseline: dict[str, Any]) -> dict[str, Any]:
    """Derive the exact only permitted numeric deltas from full baseline values.

    :param case: Implemented lane, e.g. copy-maria.
    :param baseline: Complete JSON-normalized pre-browser projections.
    :return: Deep independent expected projections for every original user.
    :raises ValueError: The case is invalid.
    """
    validate_case(case)
    result = json.loads(json.dumps(baseline))
    if case == "copy-maria":
        for row in result.values():
            if row["username"] in {"mrodriguez", "mchen"}:
                increment_projection(row)
    return result


def increment_projection(row: dict[str, Any]) -> None:
    """Apply only the established +5 author/consumer numeric projection delta.

    :param row: Private copied projection for Maria or Mike.
    :return: None after the deterministic expected delta.
    :raises KeyError: Projection schema is incompatible.
    """
    source = "Learning" if row["username"] == "mrodriguez" else "Consumption"
    row["total_points"] += 5
    row["category_points"] = [
        [key, value + 5 if key == "development" else value]
        for key, value in row["category_points"]
    ]
    row["source_points"] = [
        [key, value + 5 if key == source else value]
        for key, value in row["source_points"]
    ]
    row["successful_gui_copy_count"] += int(row["username"] == "mchen")


def verify_awards(case: str, observed: dict[str, Any], additions: list[str]) -> None:
    """Require exact real paired GUI provenance, or absolutely no new awards.

    :param case: Explicit copy or nomination lane.
    :param observed: Actual passive browser receipt records.
    :param additions: Actual newly inserted award primary keys.
    :return: None once complete provenance and paired event time agree.
    :raises AssertionError: A request, recipient or immutable snapshot differs.
    """
    if case == "nomination":
        assert observed["receipt_attempts"] == [] and additions == []
        return
    identity = validate_copy_attempts(case, observed["receipt_attempts"])
    if case != "copy-maria":
        assert additions == []
        return
    maria, mike = (User.objects.get(username=name) for name in ("mrodriguez", "mchen"))
    awards = list(KarmaAward.objects.filter(pk__in=additions).order_by("pk"))
    assert len(awards) == 2 and {
        (row.recipient_id, row.source_kind) for row in awards
    } == {(maria.pk, "learning"), (mike.pk, "consumption")}
    for row in awards:
        assert_award_payload(row, f"consumption:gui_copy:{maria.pk}:{identity}")
    assert awards[0].occurred_at == awards[1].occurred_at


def assert_award_payload(award: KarmaAward, identity: str) -> None:
    """Require every provenance attribute of an actual newly inserted GUI award.

    :param award: Real ledger object after browser copy.
    :param identity: Exact observed actor/channel/UUID identity.
    :return: None when snapshots, points, category and event channel match.
    :raises AssertionError: Any real award field differs.
    """
    assert award.event_identity == identity and award.points == 5
    assert award.category == "development" and award.event_channel == "gui_copy"
    assert award.playbook_id_snapshot == 6201 and award.change_id_snapshot is None
    assert award.entity_type_snapshot == "activity" and award.entity_id_snapshot == 6203
