"""S27 real-database public evidence, prompt, validator and log contracts."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict
from decimal import Decimal
from typing import Any

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext

from methodology.models import (
    Activity,
    PipChange,
    Playbook,
    PlaybookVersion,
    ProcessImprovementProposal,
    VersionSource,
    Workflow,
)
from methodology.services.pip_admin_service import PIPAdminService
from methodology.services.pip_apply_service import apply_approved_pip_aggregate
from methodology.services.public_contribution_evidence import (
    MAX_EVIDENCE_CHARACTERS,
    PublicContributionEvidenceService,
)
from tests.support.experts_data import CedarDataset, seed_s27_summary_privacy_variant
from tests.support.experts_logs import capture_experts_logs
from tests.support.log_story import assert_log_story

pytestmark = pytest.mark.django_db
_LOGGER_NAME = "methodology.services.public_contribution_evidence"
_COLLECT = "PublicContributionEvidenceService.collect"


@pytest.fixture
def s27_case(db: None) -> Mapping[str, Any]:
    """Build the real Cedar baseline and S27 privacy variant.

    :param db: Real transactional test database. Example: pytest Django DB.
    :return: ORM case data. Example: Maria, public facts and sentinel rows.
    :raises ValueError: If real fixture construction fails.
    """
    return seed_s27_summary_privacy_variant()


def test_collect_with_cedar_privacy_variant_returns_only_published_public_facts(
    s27_case: Mapping[str, Any],
) -> None:
    """Retain legitimate published facts while excluding private/unpublished bytes.

    :param s27_case: Real DB case. Example: Maria's Cedar variant.
    :return: None when the public-only contract holds.
    :raises AssertionError: If a public fact is lost or private field enters evidence.
    """
    service = PublicContributionEvidenceService()
    evidence = service.collect(s27_case["subject_id"])
    assert evidence == service.collect(s27_case["subject_id"])
    assert isinstance(evidence.facts, tuple)
    titles = {fact.title for fact in evidence.facts}
    assert {
        "Accessibility Audit Playbook",
        "Lead an Accessibility Review",
        "Trace Keyboard Focus",
        "Keyboard Navigation Audit",
        "Error Message Review",
        "Accessible component fixture",
        "Focus regression checklist",
    } <= titles
    assert any(
        fact.category == "development" and fact.operation == PipChange.CHANGE_ADD
        for fact in evidence.facts
    )
    serialized = json.dumps(asdict(evidence))
    assert "Check the focus order." in serialized
    assert "Use the real published activity guidance." in serialized
    assert all(sentinel not in serialized for sentinel in s27_case["sentinels"])
    assert all(
        field not in serialized
        for field in ("total_karma", "category_points", "source_points", "copy_count")
    )


@pytest.mark.parametrize(
    "case",
    [
        "partial",
        "legacy_receipt",
        "missing_receipt",
        "future_receipt",
        "foreign_playbook_receipt",
        "release_source_receipt",
        "mismatched_snapshot_pip",
        "mismatched_snapshot_version",
        "private",
        "draft",
        "disabled",
        "rejected_pip",
        "reviewed_pip",
        "unlisted_accepted_change",
        "ambiguous_add",
        "foreign_entity",
    ],
)
def test_collect_with_partial_or_unpublished_decisions_excludes_ineligible_changes(
    s27_case: Mapping[str, Any], case: str
) -> None:
    """Exercise partial decisions, missing/future receipts and nonpublic targets.

    :param s27_case: Real publication variants. Example: accepted/rejected siblings.
    :param case: Publication/authorship mutation. Example: future_receipt.
    :return: None when only published accepted rows contribute.
    :raises AssertionError: If an ineligible change becomes evidence.
    """
    if case in {"ambiguous_add", "foreign_entity", "unlisted_accepted_change"}:
        _assert_cedar_attribution_variant(s27_case, case)
        return
    if case == "partial":
        pip = _publish_partial_cedar_pip(s27_case["dataset"])
    else:
        pip = _record_ineligible_proposal(s27_case["dataset"], case)
    if case == "legacy_receipt":
        pip = apply_approved_pip_aggregate(
            pip=pip,
            actor=pip.playbook.author,
            aggregated_description="Legacy publication audit note.",
            apply_mutations=lambda: Activity.objects.filter(
                workflow__playbook_id=pip.playbook_id
            ).update(guidance="Current legacy-published detail."),
        )
    evidence = PublicContributionEvidenceService().collect(s27_case["subject_id"])
    projected = tuple(
        fact for fact in evidence.facts if fact.playbook_id == pip.playbook_id
    )
    titles = {fact.title for fact in projected}
    published = case in {"partial", "legacy_receipt"}
    assert ("S27 published detail" in titles) == published
    assert "S27 rejected sibling" not in titles
    # A rejected ADD would also leave an extra generic attribution if incorrectly selected.
    assert len(projected) == {"partial": 3, "legacy_receipt": 1}.get(case, 0)


def _publish_partial_cedar_pip(dataset: CedarDataset) -> ProcessImprovementProposal:
    """Publish accepted siblings using the existing administrator transaction."""
    staff = dataset.users_by_username["esvensson"]
    staff.is_staff = True
    staff.save(update_fields=["is_staff"])
    book = dataset.playbooks_by_pk[6106]
    pip = ProcessImprovementProposal.objects.create(
        playbook=book,
        title="S27 unpublished partial proposal title",
        created_by=dataset.users_by_username["mrodriguez"],
        status=ProcessImprovementProposal.STATUS_REVIEWED,
    )
    for order, (title, decision) in enumerate(
        (
            ("S27 published detail", PipChange.ADMIN_ACCEPT),
            ("S27 rejected sibling", PipChange.ADMIN_REJECT),
        ),
        start=1,
    ):
        PipChange.objects.create(
            pip=pip,
            order=order,
            change_type=PipChange.CHANGE_ADD,
            entity_type=PipChange.ENTITY_ACTIVITY,
            name=title,
            parent_workflow=book.workflows.first(),
            content="Published on acceptance.",
            admin_decision=decision,
        )
    finalized = PIPAdminService.finalize_pip(pip, staff)
    assert finalized.status == ProcessImprovementProposal.STATUS_ACCEPTED_PARTIAL
    return finalized


def _record_ineligible_proposal(
    dataset: CedarDataset, case: str
) -> ProcessImprovementProposal:
    """Seed an independent real receipt case outside normal publication."""
    maria = dataset.users_by_username["mrodriguez"]
    book = Playbook.objects.create(
        author=(
            maria
            if case in {"private", "draft", "disabled"}
            else dataset.playbooks_by_pk[6106].author
        ),
        name="S27 publication candidate",
        status=case if case in {"draft", "disabled"} else "released",
        visibility="private" if case == "private" else "public",
        version=Decimal("2.0"),
        category="design",
    )
    workflow = Workflow.objects.create(playbook=book, name="S27 ineligible workflow")
    activity = Activity.objects.create(workflow=workflow, name="S27 published detail")
    pip = ProcessImprovementProposal.objects.create(
        playbook=book,
        title="S27 unpublished proposal",
        created_by=maria,
        status={
            "rejected_pip": ProcessImprovementProposal.STATUS_REJECTED,
            "reviewed_pip": ProcessImprovementProposal.STATUS_REVIEWED,
        }.get(case, ProcessImprovementProposal.STATUS_ACCEPTED),
    )
    PipChange.objects.create(
        pip=pip,
        change_type=PipChange.CHANGE_ALTER,
        entity_type=PipChange.ENTITY_ACTIVITY,
        target_id=activity.pk,
        admin_decision=PipChange.ADMIN_ACCEPT,
    )
    _store_ineligible_receipt(dataset, pip, case)
    return pip


def _store_ineligible_receipt(
    dataset: CedarDataset, pip: ProcessImprovementProposal, case: str
) -> None:
    """Mirror the real writer's receipt fields and vary one invariant."""
    if case in {"missing_receipt", "legacy_receipt"}:
        return
    version = Decimal("3.0") if case == "future_receipt" else Decimal("2.0")
    book = pip.playbook
    if case == "foreign_playbook_receipt":
        book = Playbook.objects.create(
            author=dataset.playbooks_by_pk[6106].author,
            name="S27 unrelated publication",
            status="released",
            visibility="public",
            version=version,
            category="design",
        )
    PlaybookVersion.objects.create(
        playbook=book,
        version_number=version,
        source=(
            VersionSource.RELEASE
            if case == "release_source_receipt"
            else VersionSource.PIP_SOURCE
        ),
        pip=pip,
        snapshot_data={
            "pip_id": pip.pk + 1 if case == "mismatched_snapshot_pip" else pip.pk,
            "playbook_name": pip.playbook.name,
            "version_before": "1.0",
            "version_after": (
                "4.0" if case == "mismatched_snapshot_version" else str(version)
            ),
        },
    )


def _assert_cedar_attribution_variant(s27_case: Mapping[str, Any], case: str) -> None:
    """Check Cedar receipt membership and conservative current detail resolution."""
    dataset = s27_case["dataset"]
    pip = dataset.pips_by_key["HIST-MARIA-DESIGN-01"]
    change = PipChange.objects.get(pip=pip, change_type=PipChange.CHANGE_ADD)
    if case == "unlisted_accepted_change":
        receipt = PlaybookVersion.objects.get(pip=pip)
        receipt.snapshot_data["accepted_change_ids"].remove(change.pk)
        receipt.save(update_fields=["snapshot_data"])
    if case == "ambiguous_add":
        workflow = Workflow.objects.create(
            playbook_id=pip.playbook_id, name="S27 sibling workflow"
        )
        Activity.objects.create(workflow=workflow, name=change.name)
        PipChange.objects.filter(pk=change.pk).update(
            target_id=None, parent_workflow=None
        )
    if case == "foreign_entity":
        foreign = Activity.objects.filter(workflow__playbook_id=6201).first()
        PipChange.objects.filter(pk=change.pk).update(target_id=foreign.pk)
    evidence = PublicContributionEvidenceService().collect(s27_case["subject_id"])
    facts = tuple(
        fact for fact in evidence.facts if fact.playbook_id == pip.playbook_id
    )
    assert change.name not in {fact.title for fact in facts}
    assert any(fact.operation == PipChange.CHANGE_ADD for fact in facts) == (
        case != "unlisted_accepted_change"
    )


@pytest.mark.parametrize("invalid_id", [True, False, 0, -1, "1", None, 99999, 10**40])
def test_collect_with_invalid_subject_rejects_before_model_call(
    s27_case: Mapping[str, Any], invalid_id: Any
) -> None:
    """Reject invalid/missing subjects at the evidence boundary.

    :param s27_case: Real subject rows. Example: Maria and a missing ID.
    :param invalid_id: Unsupported or missing subject identity. Example: True.
    :return: None when rejection precedes contribution queries.
    :raises AssertionError: If invalid inputs reach contribution collection.
    """
    with (
        CaptureQueriesContext(connection) as queries,
        pytest.raises(ValueError, match="subject"),
    ):
        PublicContributionEvidenceService().collect(invalid_id)
    if invalid_id == 99999:
        assert len(queries) == 1
        assert "auth_user" in queries[0]["sql"]
    else:
        assert not queries


def test_build_summary_prompt_with_public_evidence_preserves_layers_and_bounds(
    s27_case: Mapping[str, Any],
) -> None:
    """Prove safety/identity/data layers, score exclusion and exact input bounds.

    :param s27_case: Real safe evidence. Example: Maria's public contribution facts.
    :return: None when 24,000/24,001 character cases obey the contract.
    :raises AssertionError: If prompt layers, facts or bounds are incorrect.
    """
    raise NotImplementedError()


def test_validate_summary_response_with_boundary_or_unsafe_output_enforces_contract(
    s27_case: Mapping[str, Any],
) -> None:
    """Exercise fourteen/fifteen sentences and malformed/sensitive/score output.

    :param s27_case: Exact request evidence. Example: Maria's published facts.
    :return: None when valid output passes and unsafe cases reject.
    :raises AssertionError: If output validation accepts or rejects incorrectly.
    """
    raise NotImplementedError()


def test_public_evidence_log_story_happy(
    s27_case: Mapping[str, Any], caplog: pytest.LogCaptureFixture
) -> None:
    """Prove declared happy log beats and absence of sensitive bodies.

    :param s27_case: Real DB case. Example: Maria's public facts.
    :param caplog: Captured logging. Example: INFO boundary records.
    :return: None when assert_log_story and privacy assertions pass.
    :raises AssertionError: For missing beats or leaked content.
    """
    subject_id = s27_case["subject_id"]
    with capture_experts_logs(caplog, (_LOGGER_NAME,)):
        evidence = PublicContributionEvidenceService().collect(subject_id)
    assert_log_story(
        caplog,
        where=_COLLECT,
        beats={
            "validation": (
                "validation",
                f"subject_id={subject_id}",
                "scope=public_released",
            ),
            "processing": (
                "processing",
                f"subject_id={subject_id}",
                f"fact_count={len(evidence.facts)}",
                "evidence_chars=",
            ),
        },
    )
    assert all(sentinel not in caplog.text for sentinel in s27_case["sentinels"])
    assert "Check the focus order." not in caplog.text


def test_public_evidence_log_story_reject(
    s27_case: Mapping[str, Any], caplog: pytest.LogCaptureFixture
) -> None:
    """Prove safe rejected-stage reason/correlation logging without private bytes.

    :param s27_case: Real adverse case. Example: oversized evidence.
    :param caplog: Captured logging. Example: sanitized failure records.
    :return: None when the rejected log story passes.
    :raises AssertionError: For missing error context or sensitive logging.
    """
    subject_id = s27_case["subject_id"]
    Activity.objects.filter(workflow__playbook__author_id=subject_id).update(
        guidance="Sensitive body marker. " + "x" * MAX_EVIDENCE_CHARACTERS
    )
    with (
        capture_experts_logs(caplog, (_LOGGER_NAME,)),
        pytest.raises(ValueError, match="24,000"),
    ):
        PublicContributionEvidenceService().collect(subject_id)
    assert_log_story(
        caplog,
        where=_COLLECT,
        beats={
            "error": (
                "error",
                f"subject_id={subject_id}",
                "reason_code=invalid_snapshot",
            )
        },
    )
    assert all(sentinel not in caplog.text for sentinel in s27_case["sentinels"])
    assert "Sensitive body marker." not in caplog.text


@pytest.fixture
def s19_cedar_dataset(db: None) -> CedarDataset:
    """Load real Cedar objects without replaying live event hooks.

    :param db: Isolated pytest database. Example: None.
    :return: Cedar dataset. Example: dataset.playbooks_by_pk[6101].
    :raises ValueError: If Cedar source data is invalid.
    """
    raise NotImplementedError()


@pytest.mark.django_db
@pytest.mark.parametrize("username", ["esvensson", None])
def test_public_evidence_with_cedar_release_links_existing_detail_route(
    client: Client, s19_cedar_dataset: CedarDataset, username: str | None
) -> None:
    """Verify title/version, rendered href and real 200 destination.

    :param client: Real Django client. Example: Client().
    :param s19_cedar_dataset: Real Cedar objects. Example: playbook 6101.
    :param username: Actor or guest. Example: "esvensson".
    :return: None. Example: None after checking the extracted href.
    :raises AssertionError: If href, version, badges or response differ.
    """
    raise NotImplementedError()


@pytest.mark.django_db
@pytest.mark.parametrize("username", ["esvensson", None])
def test_public_evidence_with_followed_workflow_exposes_cedar_activities(
    client: Client, s19_cedar_dataset: CedarDataset, username: str | None
) -> None:
    """Follow rendered playbook and workflow anchors into real content.

    :param client: Real Django client. Example: Client().
    :param s19_cedar_dataset: Real Cedar graph. Example: playbook 6101.
    :param username: Actor or guest. Example: None for anonymous.
    :return: None. Example: None after checking all three Cedar activities.
    :raises AssertionError: If a route redirects, fails or lacks the activity chain.
    """
    raise NotImplementedError()
