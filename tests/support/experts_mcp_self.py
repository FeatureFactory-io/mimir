from __future__ import annotations

"""Undecorated, real-ORM self-fetch certification support."""
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from django.contrib.auth.models import User
from django.db.models import Sum

from methodology.models import KarmaAward
from tests.support.experts_data import CedarDataset
from tests.support.karma_mcp import _prepare_mcp_entities

_CONTENT_BODIES = {
    "playbook": {
        "name": "React Frontend Development",
        "description": "",
        "category": "development",
        "status": "released",
        "version": "2.0",
        "visibility": "public",
        "author_id": None,
    },
    "workflow": {
        "name": "React Frontend Development",
        "description": "",
        "abbreviation": "RDT",
        "order": 1,
    },
    "phase": {
        "name": "Cedar Review Phase",
        "description": "Review evidence",
        "order": 1,
    },
    "activity": {
        "name": "Setup component structure",
        "guidance": "",
        "order": 1,
        "workflow_id": None,
    },
    "skill": {
        "title": "Cedar Review Skill",
        "content": "Verify review evidence",
        "capability_domain": "",
        "technology_stack": "",
    },
    "rule": {
        "title": "Cedar Review Rule",
        "slug": "cedar-review-rule",
        "content": "Check review evidence",
        "always_apply": True,
    },
    "agent": {"name": "Cedar Review Agent", "description": "Review evidence"},
    "artifact": {
        "name": "Cedar Evidence Checklist",
        "description": "Checklist evidence",
        "type": "Document",
        "is_required": False,
        "produced_by_id": None,
    },
}


@dataclass(frozen=True)
class SelfFetchCase:
    actor: User
    tool_name: str
    entity_type: str
    entity_id: int
    target_author_id: int
    creator_id: int | None
    expected_total: int
    expected_content: Mapping[str, object]
    exclusion_reason: str


@dataclass(frozen=True)
class KarmaSnapshot:
    ledger_rows: tuple[tuple[object, ...], ...]
    totals_by_user_id: Mapping[int, int]


def resolve_self_fetch_case(
    dataset: CedarDataset, consumer: str, content: str
) -> SelfFetchCase:
    """Resolve one literal outline row using actual Cedar ORM relationships.

    :param dataset: Restored baseline. Example: load_cedar_baseline().
    :param consumer: Literal name. Example: "Maria".
    :param content: Literal content label. Example: "Mike's Activity".
    :return: Immutable real entity/actor case. Example: activity 6203.
    :raises ValueError: Unknown/ambiguous row or missing real fixture relation.
    :raises TypeError: Consumer or content is not a literal string.
    """
    rows = _self_rows()
    if not isinstance(consumer, str) or not isinstance(content, str):
        raise TypeError("Literal consumer/content strings are required.")
    if (consumer, content) not in rows:
        raise ValueError("Unknown exact self-fetch row.")
    username, entity_type, key = rows[consumer, content]
    prepared = _prepare_mcp_entities(dataset)
    actor = dataset.users_by_username[username]
    entity_id = prepared.entity_ids[key]
    author_id, creator_id = _self_relationships(dataset, actor, entity_type, key)
    expected = _expected_self_content(dataset, entity_type, entity_id, key)
    reason = "self_creator" if creator_id == actor.pk else "self_author"
    return SelfFetchCase(
        actor,
        f"get_{entity_type}",
        entity_type,
        entity_id,
        author_id,
        creator_id,
        8200 if username == "mrodriguez" else 12450,
        MappingProxyType(expected),
        reason,
    )


def snapshot_karma_state() -> KarmaSnapshot:
    """Capture complete ledger payloads and projected totals for all users.

    :return: Deterministic snapshot. Example: Mike total 12450.
    :raises AssertionError: Baseline ledger/projection is inconsistent.
    """
    totals = {
        row["pk"]: row["total"]
        for row in User.objects.order_by("pk")
        .annotate(total=Sum("karma_awards__points", default=0))
        .values("pk", "total")
    }
    ledger = tuple(KarmaAward.objects.order_by("pk").values_list())
    assert ledger, "Expected the real nonempty historical ledger."
    return KarmaSnapshot(ledger, MappingProxyType(totals))


def assert_self_fetch_content(
    payload: Mapping[str, object], case: SelfFetchCase
) -> None:
    """Assert successful actual content, not an error or empty placeholder.

    :param payload: Decoded actual tool response. Example: activity dict.
    :param case: Real fixture case. Example: get_activity for 6203.
    :return: None. Example: IDs and stored content match.
    :raises AssertionError: Response identity/content or success differs.
    """
    assert isinstance(payload, Mapping) and "error" not in payload
    assert payload.get("id") == case.entity_id
    _assert_content_matches(payload, case.expected_content)


def assert_self_fetch_unchanged(before: KarmaSnapshot, case: SelfFetchCase) -> None:
    """Compare full current ledger and every total with the captured state.

    :param before: Pre-operation snapshot. Example: baseline Cedar ledger.
    :param case: Expected actor/author case. Example: Maria remains 8200.
    :return: None. Example: no learner or author row was inserted.
    :raises AssertionError: Any award, payload, timestamp or total changed.
    """
    after = snapshot_karma_state()
    assert after == before, "Complete ledger or all-user totals changed."
    assert before.totals_by_user_id[case.actor.pk] == case.expected_total
    assert after.totals_by_user_id[case.actor.pk] == case.expected_total


def _self_rows() -> Mapping[tuple[str, str], tuple[str, str, str]]:
    """Declare exactly ten independent acceptance rows.

    :return: Literal row mapping. Example: Mike's Phase uses mike_phase.
    :raises AssertionError: The declared row count is not ten.
    """
    kinds = (
        "playbook",
        "workflow",
        "phase",
        "activity",
        "skill",
        "rule",
        "agent",
        "artifact",
    )
    rows = {
        ("Mike", f"Mike's {kind.title()}"): ("mchen", kind, f"mike_{kind}")
        for kind in kinds
    }
    rows["Mike", "Maria's historical PIP targeting Mike's playbook"] = (
        "mchen",
        "pip",
        "maria_dev_pip",
    )
    rows["Maria", "Maria's historical PIP targeting Hana's playbook"] = (
        "mrodriguez",
        "pip",
        "maria_design_pip",
    )
    assert len(rows) == 10
    return rows


def _self_relationships(
    dataset: CedarDataset, actor: User, entity_type: str, key: str
) -> tuple[int, int | None]:
    """Verify actual creator/target relationships before any tested read.

    :param dataset: Independent Cedar baseline. Example: historical PIP maps.
    :param actor: Actual persisted consumer. Example: Mike.
    :param entity_type: Literal kind. Example: pip.
    :param key: S39 fixture key. Example: maria_dev_pip.
    :return: Actual author and creator IDs. Example: Mike and Maria.
    :raises AssertionError: Relationships or original staff policy differ.
    """
    mike, maria, hana = (
        dataset.users_by_username[u] for u in ("mchen", "mrodriguez", "hkim")
    )
    assert mike.is_staff and not maria.is_staff and not hana.is_staff
    if entity_type != "pip":
        assert actor.pk == mike.pk == dataset.playbooks_by_pk[6201].author_id
        return mike.pk, None
    pip_key = "HIST-MARIA-DEV-01" if key == "maria_dev_pip" else "HIST-MARIA-DESIGN-01"
    pip = dataset.pips_by_key[pip_key]
    book_pk = 6201 if key == "maria_dev_pip" else 6106
    assert (
        pip.title == pip_key and pip.playbook_id == dataset.playbooks_by_pk[book_pk].pk
    )
    assert pip.created_by_id == maria.pk
    author_id = mike.pk if book_pk == 6201 else hana.pk
    assert pip.playbook.author_id == author_id
    assert actor.pk == (mike.pk if book_pk == 6201 else maria.pk)
    assert (actor.pk == author_id) != (actor.pk == pip.created_by_id)
    return author_id, pip.created_by_id


def _expected_self_content(
    dataset: CedarDataset, entity_type: str, entity_id: int, key: str
) -> dict[str, object]:
    """Construct independent expected public body fields from declared fixtures.

    :param dataset: Restored contract. Example: declared historical PIP facts.
    :param entity_type: Exact detail kind. Example: activity.
    :param entity_id: Actual resolved ID. Example: actual phase PK.
    :param key: Semantic S39 fixture identity. Example: mike_skill.
    :return: Full authored content expectations plus actual identity.
    :raises KeyError: Unsupported fixture or missing declared relationship.
    """
    if entity_type == "pip":
        return {"id": entity_id, **_expected_pip_content(dataset, key)}
    body = {"id": entity_id, **_CONTENT_BODIES[entity_type]}
    if entity_type == "playbook":
        body["author_id"] = dataset.users_by_username["mchen"].pk
    elif entity_type == "activity":
        body["workflow_id"] = dataset.workflows_by_pk[6202].pk
    elif entity_type == "artifact":
        body["produced_by_id"] = dataset.activities_by_pk[6203].pk
    elif entity_type == "workflow":
        body["activities"] = _expected_workflow_activities(dataset)
    if entity_type not in ("playbook", "activity"):
        body["playbook_id"] = dataset.playbooks_by_pk[6201].pk
    return body


def _expected_pip_content(dataset: CedarDataset, key: str) -> dict[str, object]:
    """Read immutable declared historical content rather than serializers.

    :param dataset: Cedar JSON oracle and actual relationship maps.
    :param key: Literal PIP fixture. Example: maria_dev_pip.
    :return: All authored PIP/change body fields. Example: two named additions.
    :raises AssertionError: Declared or persisted historical identity differs.
    """
    title = "HIST-MARIA-DEV-01" if key == "maria_dev_pip" else "HIST-MARIA-DESIGN-01"
    record = next(
        row for row in dataset.oracle["historical_pips"] if row["id"] == title
    )
    changes = [
        {
            "name": row["name"],
            "target_name_snapshot": row["name"],
            "order": index,
            "change_type": row["operation"],
            "entity_type": row["entity"],
            "content": "",
            "admin_decision": "ACCEPT",
        }
        for index, row in enumerate(record["accepted_changes"], start=1)
    ]
    return {
        "title": title,
        "summary": "",
        "status": "accepted",
        "playbook_id": dataset.playbooks_by_pk[record["playbook_pk"]].pk,
        "submitted_by_username": "mrodriguez",
        "changes_count": len(changes),
        "changes": changes,
    }


def _assert_content_matches(actual: object, expected: object) -> None:
    """Compare every authored body field, including every nested change.

    :param actual: Real decoded detail payload. Example: PIP changes.
    :param expected: Independent contract subset. Example: exact change bodies.
    :return: None when every expected field matches.
    :raises AssertionError: Missing, truncated, mutated or replaced content.
    """
    if isinstance(expected, Mapping):
        assert isinstance(actual, Mapping)
        for field, value in expected.items():
            assert field in actual, f"Missing content field {field}."
            _assert_content_matches(actual[field], value)
    elif isinstance(expected, list):
        assert isinstance(actual, list) and len(actual) == len(expected)
        for actual_item, expected_item in zip(actual, expected, strict=True):
            _assert_content_matches(actual_item, expected_item)
    else:
        assert actual == expected, "Returned content differs from independent contract."


def _expected_workflow_activities(dataset: CedarDataset) -> list[dict[str, object]]:
    """Resolve real IDs for all independently declared workflow child stubs.

    :param dataset: Imported actual current activities. Example: Mike's workflow.
    :return: Exact ordered child content. Example: three named activities.
    :raises KeyError: An independently named child is missing from its parent.
    """
    names = (
        "Setup component structure",
        "Accessible component fixture",
        "Focus regression checklist",
    )
    actual_ids = {
        activity.name: activity.pk
        for activity in dataset.activities_by_pk.values()
        if activity.workflow_id == dataset.workflows_by_pk[6202].pk
    }
    return [
        {"id": actual_ids[name], "name": name, "order": order}
        for order, name in enumerate(names, start=1)
    ]
