"""Bounded real ORM preparation and complete C03/C04 effect oracles.

Only the owned companion invokes preparation. No reset, seed mutation, provider
call, publication, award or artificial Reviewed transition is performed here.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sessions.backends.db import SessionStore
from django.urls import reverse
from methodology.models import (
    Activity,
    ExpertProfile,
    KarmaAward,
    PipChange,
    Playbook,
    ProcessImprovementProposal,
    Workflow,
)
from tests.support.experts_data import CedarDataset
from tests.support.experts_summary_data import (
    SUMMARY_SCRIPTS,
    load_summary_script,
    prepare_summary_submission,
)

from bootstrap import scope, write_private
from saga_contract import (
    assert_login_user,
    assert_new_auth_token,
    assert_session_rows,
    checked_login_interval,
    utc_timestamp,
)
from saga_fixture import (
    assert_pristine,
    domain_rows,
    projections,
)
from saga_summary_contract import CASE, assert_closed_rows

logger = logging.getLogger(__name__)
_ROOT = Path("/experts-scope")
_OUTPUT = Path("/output")
_MAIL = Path("/experts-mail")
_FIXTURE = Path("/app/test-data/experts/cedar-rfp-01.json")
_AUTH = frozenset({"auth.user", "authtoken.token", "sessions.session"})
_PIP = "methodology.processimprovementproposal"
_CHANGE = "methodology.pipchange"
_PROFILE = "methodology.expertprofile"
_INTERACTION = "methodology.agentinteraction"


def now() -> str:
    """Return an actual precise aware UTC observation instant.

    :return: Full microsecond ISO UTC, for example 2026-11-25T01:00:00.000001+00:00.
    """
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def read_baseline() -> dict[str, Any]:
    """Read the exclusive private preparation record after checking ownership.

    :return: This owned scope's baseline; never exported.
    :raises ValueError: Database ownership differs.
    """
    scope()
    baseline = json.loads((_ROOT / "saga-summary-baseline.json").read_text())
    assert baseline["case"] == CASE
    return baseline


def prepared_change(baseline: dict[str, Any]) -> PipChange:
    """Resolve exactly the prepared Draft/Reviewed/Accepted proposal and change.

    :param baseline: Actual owned preparation record.
    :return: Single real change with parent/actor identity validated.
    :raises AssertionError: Target identity, cardinality or staff separation differs.
    """
    change = PipChange.objects.select_related("pip__created_by", "pip__playbook").get(
        pk=baseline["change_id"]
    )
    pip = change.pip
    assert pip.pk == baseline["pip_id"] and pip.changes.count() == 1
    assert pip.created_by.username == "mrodriguez" and not pip.created_by.is_staff
    assert (pip.playbook_id, pip.playbook.author.username) == (6106, "hkim")
    assert change.parent_workflow.playbook_id == 6106
    assert (
        change.change_type == PipChange.CHANGE_ADD
        and change.entity_type == PipChange.ENTITY_ACTIVITY
    )
    assert User.objects.get(username="mchen").is_staff
    return change


def prepare_summary_case() -> None:
    """Create only one service-backed Draft/ADD after pristine ownership checks.

    :return: None after exclusive full private baseline and safe route oracle.
    :raises AssertionError: Imported Cedar is stale or preparation caused other effects.
    :raises FileExistsError: This owned case has already been prepared.
    """
    assert_pristine()
    assert not (_ROOT / "saga-summary-baseline.json").exists()
    before = domain_rows()
    cedar = CedarDataset(
        {u.username: u for u in User.objects.all()},
        {p.pk: p for p in Playbook.objects.all()},
        {},
        {w.pk: w for w in Workflow.objects.all()},
    )
    pip = prepare_summary_submission(cedar)
    change = pip.changes.get()
    baseline = {
        "case": CASE,
        "pip_id": pip.pk,
        "change_id": change.pk,
        "rows": domain_rows(),
        "projections": projections(),
        "prepared_at": now(),
    }
    assert_closed_rows(before, baseline["rows"], {}, {_PIP: 1, _CHANGE: 1})
    assert pip.status == pip.STATUS_DRAFT and not pip.decided_at
    assert baseline["projections"][str(pip.created_by_id)]["total_points"] == 8200
    assert not list(_MAIL.iterdir()) and not pip.summary_interactions.exists()
    write_private(_ROOT / "saga-summary-baseline.json", baseline)
    write_private(_OUTPUT / "saga-summary-oracle.json", summary_oracle(baseline))
    logger.info("Summary companion prepared | pip_id=%s | case=%s", pip.pk, CASE)


def summary_oracle(baseline: dict[str, Any]) -> dict[str, Any]:
    """Expose safe source identity, native routes and explicit finite public prose.

    :param baseline: Private preparation record.
    :return: Public-only browser expectations without draft bodies or credentials.
    """
    change = prepared_change(baseline)
    responses = load_summary_script(
        SUMMARY_SCRIPTS / "PRF-EXPERTS-01/happy.json", change.pk
    )
    return {
        "case": CASE,
        "pip_id": change.pip_id,
        "change_id": change.pk,
        "fixture_sha256": hashlib.sha256(_FIXTURE.read_bytes()).hexdigest(),
        "detail_path": reverse("pip_detail", args=[change.pip_id]),
        "submit_path": reverse("pip_submit_review", args=[change.pip_id]),
        "review_path": reverse("pip_admin_review", args=[change.pip_id]),
        "public_summary": responses[0].content,
        "initial_summary": ExpertProfile.objects.get(
            user=change.pip.created_by
        ).contribution_summary,
    }


_SUBMISSION_PIP_FIELDS = frozenset(
    {
        "status",
        "submitted_at",
        "reviewed_at",
        "updated_at",
        "galdr_holistic_assessment",
        "status_changed_at",
    }
)
_ASSESSMENT_FIELDS = frozenset(
    {"galdr_recommendation", "galdr_reasoning", "updated_at"}
)
_REFRESH_FIELDS = frozenset(
    {
        "contribution_summary",
        "summary_updated_at",
        "summary_status",
        "summary_error_code",
        "last_summary_correlation_id",
    }
)


def transition_fields(baseline: dict[str, Any], accepted: bool) -> dict[str, Any]:
    """List only source-supported fields of the exact prepared rows.

    :param baseline: Owned private preparation identity.
    :param accepted: Whether comparing the decision to the Reviewed snapshot.
    :return: Exact field exception map; values require independent validators.
    """
    pip, change = str(baseline["pip_id"]), str(baseline["change_id"])
    if accepted:
        return {
            _PIP: {
                pip: frozenset(
                    {"status", "decided_at", "updated_at", "status_changed_at"}
                )
            },
            _CHANGE: {change: frozenset({"admin_decision", "admin_note"})},
            "methodology.playbook": {"6106": frozenset({"version", "updated_at"})},
        }
    profile = next(
        pk
        for pk, row in baseline["rows"][_PROFILE].items()
        if row["fields"]["user"] == baseline["rows"][_PIP][pip]["fields"]["created_by"]
    )
    return {
        _PIP: {pip: _SUBMISSION_PIP_FIELDS},
        _CHANGE: {change: _ASSESSMENT_FIELDS},
        _PROFILE: {profile: _REFRESH_FIELDS},
    }


def domain_delta(
    baseline: dict[str, Any],
    before: dict[str, Any],
    after: dict[str, Any],
    accepted: bool,
) -> None:
    """Protect every concrete/M2M row except precise independently validated effects.

    :param baseline: Actual prepared identity.
    :param before: Complete starting snapshot.
    :param after: Complete current snapshot.
    :param accepted: Select exact decision additions versus summary interaction.
    :return: None after closed structural comparison.
    :raises AssertionError: Any unrelated change or account model omission occurs.
    """
    assert before.keys() == after.keys() and _AUTH <= before.keys()
    additions = (
        {
            "methodology.karmaaward": 1,
            "methodology.activity": 1,
            "methodology.playbookversion": 1,
        }
        if accepted
        else {_INTERACTION: 1}
    )
    assert_closed_rows(
        {k: v for k, v in before.items() if k not in _AUTH},
        {k: v for k, v in after.items() if k not in _AUTH},
        transition_fields(baseline, accepted),
        additions,
    )


def capture_reviewed(baseline: dict[str, Any], calls: int) -> dict[str, Any]:
    """Observe persisted Reviewed before any staff decision, with no domain writes.

    :param baseline: Owned private preparation record.
    :param calls: Actual same-serving-worker ScriptedLLM call count.
    :return: Exclusive private full-precision predecision evidence.
    :raises AssertionError: Summary, lifecycle, unchanged Karma or no-mail differs.
    """
    scope()
    assert calls == 2 and settings.GALDR_EAGER is False
    change = prepared_change(baseline)
    assert change.pip.status == ProcessImprovementProposal.STATUS_REVIEWED
    record = {
        "case": CASE,
        "rows": domain_rows(),
        "projections": projections(),
        "observed_at": now(),
        "provider_calls": calls,
    }
    domain_delta(baseline, baseline["rows"], record["rows"], False)
    assert record["projections"] == baseline["projections"]
    validate_reviewed_values(baseline, record)
    validate_no_mail(_MAIL)
    write_private(_ROOT / "saga-summary-reviewed.json", record)
    return record


def validate_no_mail(mail_path: Path) -> None:
    """Reject any actual decision-mail artifact before staff acceptance.

    :param mail_path: Exact owned private file-mail directory.
    :return: None only for an empty real directory.
    :raises AssertionError: Any message or other entry exists.
    """
    assert mail_path.is_dir() and not list(mail_path.iterdir())


def bounded(value: str, start: str, end: str) -> None:
    """Require one actual microsecond timestamp inside its real observation envelope.

    :param value: Persisted actual timestamp.
    :param start: Actual earlier observation.
    :param end: Actual later observation.
    :return: None after exact comparison.
    """
    assert utc_timestamp(start) <= utc_timestamp(value) <= utc_timestamp(end)


def validate_reviewed_values(baseline: dict[str, Any], record: dict[str, Any]) -> None:
    """Require the exact refreshed public paragraph and authentic successful interaction.

    :param baseline: Actual prepared identity and original rows.
    :param record: Full precise Reviewed observation.
    :return: None after exact source-backed values and times agree.
    :raises AssertionError: A refresh, assessment, provenance or measurement differs.
    """
    change = prepared_change(baseline)
    pip = change.pip
    assert pip.status == pip.STATUS_REVIEWED and pip.decided_at is None
    assert change.admin_decision == change.admin_note == ""
    assert change.galdr_recommendation == PipChange.GALDR_ACCEPT
    assert change.galdr_reasoning == "The proposed activity fits the review workflow."
    assert (
        pip.galdr_holistic_assessment
        == "COHERENT: The proposed activity has a clear place in the workflow."
    )
    validate_refresh_profile(baseline, record, pip, change)


def validate_refresh_profile(
    baseline: dict[str, Any],
    record: dict[str, Any],
    pip: ProcessImprovementProposal,
    change: PipChange,
) -> None:
    """Validate the actual successful public profile and measurement row.

    :param baseline: Exact prepared identity and initial time.
    :param record: Actual precise Reviewed observation.
    :param pip: Real Reviewed proposal.
    :param change: Real assessed ADD.
    :return: None after profile, usage, time and correlation agree.
    """
    profile = ExpertProfile.objects.get(user=pip.created_by)
    interaction = pip.summary_interactions.get()
    profile.full_clean()
    interaction.full_clean()
    assert (
        profile.contribution_summary
        == load_summary_script(
            SUMMARY_SCRIPTS / "PRF-EXPERTS-01/happy.json", change.pk
        )[0].content
    )
    assert profile.summary_status == "success" and profile.summary_error_code == ""
    assert (
        interaction.subject_id == pip.created_by_id and interaction.outcome == "success"
    )
    assert interaction.correlation_id == profile.last_summary_correlation_id
    assert (interaction.model, interaction.input_tokens, interaction.output_tokens) == (
        "scripted",
        210,
        15,
    )
    assert interaction.estimated_cost_usd is None and interaction.latency_ms >= 0
    assert (
        not interaction.error_code and interaction.workflow_id == "contribution_summary"
    )
    validate_refresh_times(baseline, record, pip, change, profile, interaction)


def validate_refresh_times(
    baseline: dict[str, Any],
    record: dict[str, Any],
    pip: ProcessImprovementProposal,
    change: PipChange,
    profile: ExpertProfile,
    interaction: Any,
) -> None:
    """Bind every actual submission/refresh/review timestamp to its real envelope.

    :param baseline: Initial precise observation.
    :param record: Real Reviewed observation.
    :param pip: Actual Reviewed proposal.
    :param change: Actual assessed ADD.
    :param profile: Actual successful refreshed profile.
    :param interaction: Actual successful interaction.
    :return: None after exact temporal order and current version agree.
    """
    for stamp in (
        pip.submitted_at,
        pip.status_changed_at,
        pip.reviewed_at,
        pip.updated_at,
        change.updated_at,
        profile.summary_updated_at,
        interaction.created_at,
    ):
        bounded(
            stamp.isoformat(timespec="microseconds"),
            baseline["prepared_at"],
            record["observed_at"],
        )
    assert pip.submitted_at <= profile.summary_updated_at <= pip.reviewed_at
    assert pip.playbook.version == Decimal("2.0")


def validated_logins(
    baseline: dict[str, Any], observed: dict[str, Any], end: str
) -> list[Any]:
    """Bind precisely three real native sign-ins and exact distinct session identities.

    :param baseline: Actual baseline time.
    :param observed: Browser-only safe response metadata.
    :param end: Actual effect verification time.
    :return: Exact native Maria/Mike/Maria login bounds.
    :raises AssertionError: An actor, envelope, expiry or request differs.
    """
    assert settings.SESSION_SAVE_EVERY_REQUEST is True
    assert settings.SESSION_COOKIE_AGE == 14 * 24 * 60 * 60
    window = (utc_timestamp(baseline["prepared_at"]), utc_timestamp(end))
    assert 0 <= (window[1] - window[0]).total_seconds() <= 720
    records = observed["login_observations"]
    assert len(records) == 3
    logins = [
        checked_login_interval(actor, row, window, settings.SESSION_COOKIE_AGE)
        for actor, row in zip(("mrodriguez", "mchen", "mrodriguez"), records)
    ]
    assert (
        logins[0].completed_at
        <= logins[1].started_at
        <= logins[1].completed_at
        <= logins[2].started_at
    )
    assert len({row.session_key_sha256 for row in logins}) == 3
    return logins


def account_delta(
    before: dict[str, Any], after: dict[str, Any], logins: list[Any]
) -> None:
    """Protect all users/tokens and the one surviving native session exactly.

    :param before: Complete original private rows.
    :param after: Actual complete current private rows.
    :param logins: Actual chronological native login observations.
    :return: None; exceptions apply only to exact actor fields and generated rows.
    :raises AssertionError: Existing token/session or unrelated account changed.
    """
    assert all(
        rows == after[label]
        for label, rows in before.items()
        if label.startswith("accounts.")
    )
    users, current = before["auth.user"], after["auth.user"]
    assert users.keys() == current.keys()
    for pk, row in users.items():
        matching = [
            login for login in logins if login.actor == row["fields"]["username"]
        ]
        if matching:
            assert_login_user(row, current[pk], matching[-1])
        else:
            assert row == current[pk], "Unrelated account changed."
    verify_tokens(before, after, logins)
    assert_session_rows(
        before["sessions.session"], after["sessions.session"], logins[-1]
    )
    verify_snapshot_session(after["sessions.session"], logins[-1])


def verify_tokens(
    before: dict[str, Any], after: dict[str, Any], logins: list[Any]
) -> None:
    """Bind only missing actor tokens to their first exact actual native login.

    :param before: Private original complete rows.
    :param after: Actual complete precise rows.
    :param logins: Actual chronological login metadata.
    :return: None after every old token and exact new token is checked.
    """
    users = before["auth.user"]
    tokens, actual = before["authtoken.token"], after["authtoken.token"]
    assert all(actual.get(pk) == row for pk, row in tokens.items())
    required = {
        int(pk): next(
            login for login in logins if login.actor == row["fields"]["username"]
        )
        for pk, row in users.items()
        if any(login.actor == row["fields"]["username"] for login in logins)
        and not any(token["fields"]["user"] == int(pk) for token in tokens.values())
    }
    added = actual.keys() - tokens.keys()
    assert len(added) == len(required)
    assert {actual[pk]["fields"]["user"] for pk in added} == required.keys()
    for pk in added:
        user = actual[pk]["fields"]["user"]
        assert_new_auth_token(pk, actual[pk], user, required[user])


def verify_snapshot_session(rows: dict[str, Any], login: Any) -> None:
    """Validate exact cookie-linked decoded session even after its native logout.

    :param rows: Actual private full-precision session snapshot.
    :param login: Exact native login observation.
    :return: None after normal auth/backend/hash/age fields match.
    :raises AssertionError: The snapshot identity or private payload differs.
    """
    keys = [
        pk
        for pk in rows
        if hashlib.sha256(pk.encode()).hexdigest() == login.session_key_sha256
    ]
    assert len(keys) == 1
    user = User.objects.get(username=login.actor)
    decoded = SessionStore().decode(rows[keys[0]]["fields"]["session_data"])
    assert len(settings.AUTHENTICATION_BACKENDS) == 1
    assert decoded == {
        "_auth_user_id": str(user.pk),
        "_auth_user_backend": settings.AUTHENTICATION_BACKENDS[0],
        "_auth_user_hash": user.get_session_auth_hash(),
        "_session_expiry": login.session_age_seconds,
    }


def verify_session_lifecycle(
    baseline: dict[str, Any], worker: list[dict[str, Any]], logins: list[Any]
) -> None:
    """Reconcile three exact cookie-linked insertions and their two native deletions.

    :param baseline: Complete original private rows.
    :param worker: Actual same-worker body-free metadata and private auth snapshots.
    :param logins: Exact actual browser POST response bounds.
    :return: None after only case-created sessions are inserted/deleted.
    :raises AssertionError: A logout deletes another session or any payload differs.
    """
    original = baseline["rows"]["sessions.session"]
    auth = [
        row
        for row in worker
        if row["path"] == "/auth/user/logout/"
        or (row["path"] == "/auth/user/login/" and row["method"] == "POST")
    ]
    assert [row["path"] for row in auth] == [
        "/auth/user/login/",
        "/auth/user/logout/",
        "/auth/user/login/",
        "/auth/user/logout/",
        "/auth/user/login/",
    ]
    for index, login in enumerate(logins):
        inserted = auth[index * 2]
        assert inserted["sessions_before"] == original
        assert_session_rows(original, inserted["sessions_after"], login)
        verify_snapshot_session(inserted["sessions_after"], login)
        if index < 2:
            deleted = auth[index * 2 + 1]
            assert_session_rows(original, deleted["sessions_before"], login)
            verify_snapshot_session(deleted["sessions_before"], login)
            assert deleted["sessions_after"] == original


def verify_summary_case() -> None:
    """Reconcile real browser C01–C05, complete rows, one decision mail and calls.

    :return: None after exclusive safe effects receipt.
    :raises AssertionError: Any requirement or precise unrelated-row protection fails.
    """
    baseline = read_baseline()
    reviewed = json.loads((_ROOT / "saga-summary-reviewed.json").read_text())
    observed = json.loads((_OUTPUT / "saga-summary-browser.json").read_text())
    assert observed["case"] == CASE and observed["status"] == "BROWSER_OBSERVED"
    assert observed["completed_steps"] == ["C01", "C02", "C03", "C04", "C05"]
    current = domain_rows()
    logins = validated_logins(baseline, observed, now())
    account_delta(baseline["rows"], reviewed["rows"], logins[:1])
    account_delta(baseline["rows"], current, logins)
    domain_delta(baseline, reviewed["rows"], current, True)
    validate_submission_envelope(baseline, reviewed, observed)
    validate_decision_values(baseline, reviewed, current, observed)
    validate_mail(baseline)
    worker = [
        json.loads(line)
        for line in (_ROOT / "saga-summary-worker.jsonl").read_text().splitlines()
    ]
    assert worker and len({row["pid"] for row in worker}) == 1
    verify_session_lifecycle(baseline, worker, logins)
    assert (
        worker[-1]["provider_calls"] == 2
        and max(row["provider_calls"] for row in worker) == 2
    )
    write_effect_receipt()


def write_effect_receipt() -> None:
    """Publish only the verified safe counts after every strict oracle succeeded.

    :return: None after exclusive creation; no private rows leave the scope.
    :raises FileExistsError: An earlier acquisition has this name.
    """
    write_private(
        _OUTPUT / "saga-summary-effects.json",
        {
            "case": CASE,
            "status": "CASE_VERIFIED",
            "scope_rechecked": True,
            "new_awards": 1,
            "new_activities": 1,
            "new_versions": 1,
            "decision_mail_files": 1,
            "provider_calls": 2,
            "galdr_eager": False,
            "all_installed_rows_protected": True,
            "full_saga_accepted": False,
        },
    )
    logger.info("Summary companion verified | case=%s | new_awards=1", CASE)


def validate_submission_envelope(
    baseline: dict[str, Any], reviewed: dict[str, Any], observed: dict[str, Any]
) -> None:
    """Bind the real async refresh to the actual native submission request start.

    :param baseline: Precise prepared identity and time.
    :param reviewed: Actual persisted Reviewed snapshot.
    :param observed: Actual native POST response envelopes.
    :return: None after exact request, times and async temporal order agree.
    """
    submission = observed["submission"]
    start, end = validate_native_post(
        submission, reverse("pip_submit_review", args=[baseline["pip_id"]])
    )
    validate_native_post(
        observed["finalization"], reverse("pip_admin_review", args=[baseline["pip_id"]])
    )
    assert utc_timestamp(baseline["prepared_at"]) <= start <= end
    assert (end - start).total_seconds() <= 30
    pip = reviewed["rows"][_PIP][str(baseline["pip_id"])]["fields"]
    assert start <= utc_timestamp(pip["submitted_at"]) <= end
    assert (
        start
        <= utc_timestamp(pip["reviewed_at"])
        <= utc_timestamp(reviewed["observed_at"])
    )
    assert end <= utc_timestamp(observed["finalization"]["started_at"])


def validate_native_post(
    observed: dict[str, Any], path: str
) -> tuple[datetime, datetime]:
    """Validate one exact bounded native action-start→POST-response observation.

    :param observed: Actual safe browser response metadata.
    :param path: Source-resolved prepared native route.
    :return: Exact full-precision actual start/end timestamps.
    :raises AssertionError: Metadata shape, method, response or timing differs.
    """
    assert observed.keys() == {"method", "path", "status", "started_at", "completed_at"}
    assert (observed["method"], observed["path"], observed["status"]) == (
        "POST",
        path,
        302,
    )
    start, end = utc_timestamp(observed["started_at"]), utc_timestamp(
        observed["completed_at"]
    )
    assert 0 <= (end - start).total_seconds() <= 30
    return start, end


def validate_decision_values(
    baseline: dict[str, Any],
    reviewed: dict[str, Any],
    current: dict[str, Any],
    observed: dict[str, Any],
) -> None:
    """Check exact sole publication, award, new activity and cached summary identity.

    :param baseline: Actual prepared identity.
    :param reviewed: Exact before-decision snapshot.
    :param current: Actual final complete rows.
    :param observed: Native response decision envelope.
    :return: None after source-backed application values agree.
    """
    change = prepared_change(baseline)
    pip = change.pip
    assert (
        pip.status == pip.STATUS_ACCEPTED
        and change.admin_decision == PipChange.ADMIN_ACCEPT
    )
    assert change.admin_note == "" and pip.playbook.version == Decimal("3.0")
    assert reviewed["rows"][_PROFILE] == current[_PROFILE]
    assert reviewed["rows"][_INTERACTION] == current[_INTERACTION]
    validate_publication(change, reviewed, observed)
    expected = json.loads(json.dumps(baseline["projections"]))
    maria = expected[str(pip.created_by_id)]
    maria["total_points"] += 500
    maria["category_points"] = [
        [key, value + 500 if key == "design" else value]
        for key, value in maria["category_points"]
    ]
    maria["source_points"] = [
        [key, value + 500 if key == "PIP" else value]
        for key, value in maria["source_points"]
    ]
    assert projections() == expected, "Whole-user numeric state differs."


def validate_publication(
    change: PipChange, reviewed: dict[str, Any], observed: dict[str, Any]
) -> None:
    """Validate provenance/time/content for exactly the one allowed decision.

    :param change: Real prepared Activity ADD.
    :param reviewed: Actual predecision evidence timestamp.
    :param observed: Actual finalization POST/302 observation.
    :return: None after all exact publication fields match source behavior.
    """
    pip = change.pip
    validate_award(change)
    decision = observed["finalization"]
    for stamp in (
        pip.decided_at,
        pip.status_changed_at,
        pip.updated_at,
        pip.playbook.updated_at,
    ):
        bounded(
            stamp.isoformat(timespec="microseconds"),
            decision["started_at"],
            decision["completed_at"],
        )
    validate_activity(change, decision)
    validate_receipt(change, decision)
    assert utc_timestamp(reviewed["observed_at"]) <= utc_timestamp(
        decision["started_at"]
    )


def validate_award(change: PipChange) -> None:
    """Check exact recipient, amount, channel, snapshots and event timestamp.

    :param change: The actual accepted Activity ADD.
    :return: None after its sole immutable 500-point event agrees.
    """
    pip = change.pip
    award = KarmaAward.objects.get(event_identity=f"accepted_change:{change.pk}")
    assert (
        award.recipient_id,
        award.playbook_id_snapshot,
        award.change_id_snapshot,
    ) == (pip.created_by_id, 6106, change.pk)
    assert (award.points, award.category, award.event_channel, award.source_kind) == (
        500,
        "design",
        "accepted_change",
        "major",
    )
    assert award.occurred_at == pip.decided_at
    assert award.entity_type_snapshot is None and award.entity_id_snapshot is None


def validate_activity(change: PipChange, decision: dict[str, Any]) -> None:
    """Check sole appended public Activity fields and exact native decision times.

    :param change: Accepted actual ADD.
    :param decision: Actual staff POST response envelope.
    :return: None after all new activity values agree.
    """
    activity = Activity.objects.get(
        workflow_id=change.parent_workflow_id, name=change.name, guidance=change.content
    )
    assert activity.phase_id is None and activity.agent_id is None
    assert (
        activity.predecessor_id is None
        and activity.successor_id is None
        and activity.last_accessed_at is None
    )
    assert not activity.skills.exists() and not activity.rules.exists()
    for stamp in (activity.created_at, activity.updated_at):
        bounded(
            stamp.isoformat(timespec="microseconds"),
            decision["started_at"],
            decision["completed_at"],
        )


def validate_receipt(change: PipChange, decision: dict[str, Any]) -> None:
    """Check exact provenance and snapshot of the sole new major publication.

    :param change: Accepted real ADD.
    :param decision: Actual staff POST response envelope.
    :return: None after publication fields and time agree.
    """
    pip = change.pip
    receipt = pip.playbook_versions.get()
    assert (
        receipt.playbook_id,
        receipt.version_number,
        receipt.source,
        receipt.is_major,
        receipt.created_by.username,
    ) == (6106, Decimal("3.0"), "pip", True, "mchen")
    assert receipt.snapshot_data == {
        "pip_id": pip.pk,
        "playbook_name": pip.playbook.name,
        "version_before": "2.0",
        "version_after": "3.0",
        "accepted_change_ids": [change.pk],
        "category": "design",
    }
    assert (
        receipt.change_summary == f"ADD {change.name}"
        and receipt.description == receipt.change_summary
    )
    bounded(
        receipt.created_at.isoformat(timespec="microseconds"),
        decision["started_at"],
        decision["completed_at"],
    )


def validate_mail(baseline: dict[str, Any]) -> None:
    """Inspect only one genuine file-mail message without exporting its recipient.

    :param baseline: Actual prepared identity.
    :return: None after exact local decision message recipient and content agree.
    :raises AssertionError: Backend, count, verdict or notification content differs.
    """
    assert settings.EMAIL_BACKEND == "django.core.mail.backends.filebased.EmailBackend"
    assert Path(settings.EMAIL_FILE_PATH).resolve() == _MAIL.resolve()
    files = list(_MAIL.iterdir())
    assert len(files) == 1 and files[0].is_file()
    message = BytesParser(policy=policy.default).parsebytes(files[0].read_bytes())
    change = prepared_change(baseline)
    assert (
        message["To"] == change.pip.created_by.email
        and "Accepted" in message["Subject"]
    )
    body = message.get_content()
    assert f'ADD Activity "{change.name}"' in body and "Decision: ACCEPT" in body
    assert "is now v3.0" in body
