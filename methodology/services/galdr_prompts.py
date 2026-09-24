"""Galdr prompts and compact playbook summaries for Claude assessments."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from methodology.models import PipChange

SYSTEM_PROMPT = """You are Galdr, an AI reviewer for playbook improvement proposals.
Assess whether each proposed change is consistent with the playbook's goals,
free of conflicts with existing entities, and structurally sound.

Respond ONLY with a JSON object — no prose, no markdown fences:
{"recommendation": "ACCEPT"|"REJECT"|"NEEDS_CLARIFICATION", "reasoning": "<one paragraph>"}
"""

HOLISTIC_SYSTEM_PROMPT = """You are Galdr, an AI reviewer for playbook improvement proposals.
Evaluate the FULL proposed PIP holistically: assess whether the TARGET STATE (after all
changes are applied in order) is architecturally coherent, then provide per-change diagnostics
in that full context — not against the current state in isolation.

Structural validation has already dry-run applied the complete batch atomically.
Activities have a primary parent workflow and may be LINKed into secondary workflows.
Do not invent a one-workflow-only restriction. Judge semantic coherence using all changes.
Return exactly one assessment for every change ID; give concise reasons (1-2 sentences).

When a parent, phase, producer, ordering, LINK or UNLINK field uses #internal_ref (e.g. #artifact-dsp-target), that slug labels
a pending ADD in the same PIP — not a missing live catalog entity. Use the pending identity
map and target state; do not REJECT solely because #slug is absent from the released snapshot.

Respond ONLY with a JSON object — no prose, no markdown fences:
{
  "holistic_assessment": {
    "overall_coherence": "COHERENT"|"INCOHERENT",
    "reasoning": "<one paragraph>"
  },
  "change_assessments": [
    {"change_id": <int>, "recommendation": "ACCEPT"|"REJECT"|"NEEDS_CLARIFICATION", "reasoning": "<one paragraph>"}
  ]
}
"""

INTERNAL_REF_IDENTITY_NOTE = (
    "NOTE: #slug in parent, phase, producer, ordering or LINK/UNLINK fields refers to a pending ADD in this PIP, "
    "not a missing live catalog entry. Use the identity map and target state below."
)


def _ordered_activities(playbook):
    from methodology.models import Activity

    return (
        Activity.objects.filter(workflow__playbook=playbook)
        .select_related("agent", "workflow")
        .order_by("workflow__order", "order", "pk")
    )


def _append_catalog_section(
    lines: list[str],
    header: str,
    rows: Iterable,
    formatter: Callable,
) -> None:
    lines.append("")
    lines.append(header)
    for row in rows:
        lines.append(formatter(row))


def _append_skill_activity_links(lines: list[str], playbook) -> None:
    from methodology.models import Activity

    lines.append("")
    lines.append("--- Skill → Activity links ---")
    for act in (
        Activity.objects.filter(workflow__playbook=playbook)
        .prefetch_related("skills")
        .order_by("workflow__order", "order", "pk")
    ):
        for sk in act.skills.all():
            lines.append(f"  Skill [{sk.pk}] → Activity [{act.pk}] {act.name}")


def _append_rule_activity_links(lines: list[str], playbook) -> None:
    from methodology.models import Activity

    lines.append("")
    lines.append("--- Rule → Activity links ---")
    for act in (
        Activity.objects.filter(workflow__playbook=playbook)
        .prefetch_related("rules")
        .order_by("workflow__order", "order", "pk")
    ):
        for ru in act.rules.all():
            lines.append(f"  Rule [{ru.pk}] → Activity [{act.pk}] {act.name}")


def _append_agent_activity_links(lines: list[str], playbook) -> None:
    lines.append("")
    lines.append("--- Agent → Activity links ---")
    for act in _ordered_activities(playbook):
        if act.agent_id:
            lines.append(
                f"  Agent [{act.agent.pk}] → Activity [{act.pk}] {act.name}"
            )


def _append_artifact_activity_links(lines: list[str], playbook) -> None:
    from methodology.models import Activity

    lines.append("")
    lines.append("--- Artifact → Activity links ---")
    for act in (
        Activity.objects.filter(workflow__playbook=playbook)
        .prefetch_related("input_artifacts__artifact")
        .order_by("workflow__order", "order", "pk")
    ):
        for ai in act.input_artifacts.all():
            lines.append(
                f"  Artifact [{ai.artifact.pk}] → Activity [{act.pk}] {act.name}"
            )


def _append_entity_catalogs_and_links(lines: list[str], playbook) -> None:
    from methodology.models import Agent, Artifact, Phase, Rule, Skill

    _append_catalog_section(
        lines,
        "--- Phases ---",
        Phase.objects.filter(playbook=playbook).order_by("pk"),
        lambda ph: f"  Phase [{ph.pk}] {ph.name} (#{ph.order})",
    )
    _append_catalog_section(
        lines,
        "--- Artifacts ---",
        Artifact.objects.filter(playbook=playbook).order_by("pk"),
        lambda art: f"  Artifact [{art.pk}] {art.name} ({art.type})",
    )
    _append_catalog_section(
        lines,
        "--- Skills ---",
        Skill.objects.filter(playbook=playbook).order_by("pk"),
        lambda sk: f"  Skill [{sk.pk}] {sk.title}",
    )
    _append_catalog_section(
        lines,
        "--- Agents ---",
        Agent.objects.filter(playbook=playbook).order_by("pk"),
        lambda ag: f"  Agent [{ag.pk}] {ag.name}",
    )
    _append_catalog_section(
        lines,
        "--- Rules ---",
        Rule.objects.filter(playbook=playbook).order_by("pk"),
        lambda ru: f"  Rule [{ru.pk}] {ru.title}",
    )
    _append_skill_activity_links(lines, playbook)
    _append_rule_activity_links(lines, playbook)
    _append_agent_activity_links(lines, playbook)
    _append_artifact_activity_links(lines, playbook)


def build_playbook_context_summary(playbook) -> str:
    """
    Build compact text summarising playbook structure for Galdr prompts.

    :param playbook: :class:`~methodology.models.Playbook` instance.
    :return: Multi-line textual outline of workflows, entities, and links.
    """
    from methodology.models import Workflow

    lines = [
        f"Playbook: {playbook.name} v{playbook.version} (status={playbook.status})",
    ]
    for wf in Workflow.objects.filter(playbook=playbook).order_by("order", "pk"):
        lines.append(f"  Workflow [{wf.pk}] {wf.name} (#{wf.order})")
        for act in wf.activities.order_by("order", "pk"):
            lines.append(f"    Activity [{act.pk}] {act.name} (#{act.order})")

    _append_entity_catalogs_and_links(lines, playbook)
    return "\n".join(lines)


def build_extended_playbook_summary(playbook) -> str:
    """
    Build a richer playbook outline including workflow detail.

    Entity catalogs and links come from :func:`build_playbook_context_summary`.

    :param playbook: :class:`~methodology.models.Playbook` instance.
    :return: Multi-line textual outline for Galdr target-state context.
    """
    from methodology.models import Workflow

    lines = [build_playbook_context_summary(playbook), "", "--- Workflows (detail) ---"]
    for wf in Workflow.objects.filter(playbook=playbook).order_by("order", "pk"):
        lines.append(f"  Workflow [{wf.pk}] {wf.name}: {wf.description[:120]}")
    return "\n".join(lines)


def _pending_ref_display_name(change) -> str:
    return (change.name or change.target_name_snapshot or "(unnamed)").strip()


def _format_pending_ref_line(
    ref_key: str,
    change,
    ref_map: dict[str, tuple[str, int]],
) -> str:
    line = (
        f"  {ref_key} → ADD {change.entity_type} order={change.order} "
        f"\"{_pending_ref_display_name(change)}\""
    )
    hit = ref_map.get(ref_key)
    if hit:
        entity_type, pk = hit
        line += f" → target-state {entity_type} [{pk}]"
    return line


def build_internal_ref_identity_lines(
    changes,
    ref_map: dict[str, tuple[str, int]] | None = None,
    *,
    before_order: int | None = None,
) -> list[str]:
    """
    Build pending ``#internal_ref`` → ADD identity lines for Galdr prompts.

    :param changes: Ordered PipChange rows for one PIP.
    :param ref_map: Optional dry-run map of ref → (entity_type, pk).
    :param before_order: When set, only ADD rows with ``order`` strictly less apply.
    :return: Lines like ``#art-handoff → ADD Artifact order=1 "Handoff" → target-state …``.
    """
    from methodology.models import PipChange
    from methodology.services.pip_link_service import normalize_internal_ref

    ref_map = ref_map or {}
    lines: list[str] = []
    for change in changes:
        if change.change_type != PipChange.CHANGE_ADD or not change.internal_ref:
            continue
        if before_order is not None and change.order >= before_order:
            continue
        key = normalize_internal_ref(change.internal_ref)
        lines.append(_format_pending_ref_line(key, change, ref_map))
    return lines


def _annotate_internal_ref_endpoint(
    ref: str,
    changes,
    ref_map: dict[str, tuple[str, int]] | None = None,
) -> str:
    from methodology.models import PipChange
    from methodology.services.pip_link_service import (
        is_internal_ref,
        normalize_internal_ref,
    )

    if not is_internal_ref(ref):
        return ref
    ref_map = ref_map or {}
    key = normalize_internal_ref(ref)
    for change in changes:
        if change.change_type != PipChange.CHANGE_ADD or not change.internal_ref:
            continue
        if normalize_internal_ref(change.internal_ref) != key:
            continue
        annotated = (
            f"{ref} (pending ADD order={change.order} "
            f"\"{_pending_ref_display_name(change)}\")"
        )
        hit = ref_map.get(key)
        if hit:
            entity_type, pk = hit
            annotated += f" → target-state {entity_type} [{pk}]"
        return annotated
    return ref


def _change_reference_lines(
    change: PipChange, changes: list[PipChange], ref_map: dict[str, tuple[str, int]],
) -> list[str]:
    """Describe explicit parent, phase, producer and insertion references.

    :param change: PIP change whose structural fields are serialized.
    :param changes: Full ordered PIP batch for pending identity resolution.
    :param ref_map: Dry-run identity map, or an empty mapping.
    :return: Annotated field lines, e.g. parent_workflow_ref: #wf (pending ADD ...).
    """
    lines: list[str] = []
    for field in (
        "parent_workflow_id",
        "parent_workflow_ref",
        "insert_after_activity_id",
        "insert_after_activity_ref",
        "phase_ref",
        "produced_by_activity_ref",
    ):
        value = getattr(change, field)
        if value:
            annotated = _annotate_internal_ref_endpoint(str(value), changes, ref_map)
            lines.append(f"  {field}: {annotated}")
    return lines


def _format_change_list(
    changes,
    ref_map: dict[str, tuple[str, int]] | None = None,
) -> str:
    blocks: list[str] = []
    ref_map = ref_map or {}
    for change in changes:
        header = (
            f"Change [{change.pk}] order={change.order} "
            f"{change.change_type} {change.entity_type or change.relationship_type}"
        )
        body_lines = [header, f"  name: {change.name or '(empty)'}"]
        body_lines.extend(_change_reference_lines(change, changes, ref_map))
        if change.display_order is not None:
            body_lines.append(f"  display_order: {change.display_order}")
        if change.target_id:
            body_lines.append(f"  target_id: {change.target_id}")
        if change.target_name_snapshot:
            body_lines.append(f"  target_name_snapshot: {change.target_name_snapshot}")
        if change.content:
            body_lines.append(f"  content: {change.content}")
        if change.internal_ref:
            body_lines.append(f"  internal_ref: {change.internal_ref}")
        if change.change_type in {"LINK", "UNLINK"}:
            src = _annotate_internal_ref_endpoint(
                change.source_entity_ref or "",
                changes,
                ref_map,
            )
            tgt = _annotate_internal_ref_endpoint(
                change.target_entity_ref or "",
                changes,
                ref_map,
            )
            body_lines.append(f"  relationship_type: {change.relationship_type}")
            body_lines.append(f"  link: {src} → {tgt}")
        blocks.append("\n".join(body_lines))
    return "\n\n".join(blocks)


def build_target_state_prompt(
    pip,
    current_summary: str,
    target_summary: str,
    changes,
    ref_map: dict[str, tuple[str, int]] | None = None,
) -> str:
    """
    Compose holistic Galdr user message with current + target state context.

    :param pip: Parent :class:`~methodology.models.ProcessImprovementProposal`.
    :param current_summary: Pre-change playbook outline.
    :param target_summary: Post-apply playbook outline from dry-run.
    :param changes: Ordered PipChange queryset or list.
    :param ref_map: Dry-run ``internal_ref`` → ``(entity_type, pk)`` map.
    :return: Full user prompt for holistic assessment.
    """
    ref_map = ref_map or {}
    identity_lines = build_internal_ref_identity_lines(changes, ref_map)
    sections = [
        f"Assess PIP [{pip.pk}] \"{pip.title}\" holistically.",
        f"Summary: {pip.summary or '(none)'}",
        "",
        "--- Current Playbook State ---",
        current_summary,
        "",
        "--- Target State After All Changes ---",
        target_summary,
    ]
    if identity_lines:
        sections.extend([
            "",
            "--- Pending internal_ref identities (same PIP) ---",
            *identity_lines,
            INTERNAL_REF_IDENTITY_NOTE,
        ])
    sections.extend(
        [
            "",
            "--- Proposed Changes (in order) ---",
            _format_change_list(changes, ref_map),
            "",
            (
                "Evaluate target-state coherence first, then per-change recommendations "
                "in the context of the full PIP."
            ),
        ]
    )
    return "\n".join(sections)


def build_change_prompt(
    change,
    context_summary: str,
    *,
    all_changes=None,
    ref_map: dict[str, tuple[str, int]] | None = None,
) -> str:
    """
    Compose the user message assessing a single :class:`~methodology.models.PipChange`.

    :param change: PipChange row.
    :param context_summary: Output of :func:`build_playbook_context_summary`.
    :param all_changes: All PipChange rows in the PIP (for pending ref context).
    :param ref_map: Optional dry-run ``internal_ref`` map.
    :return: Full user prompt content.
    """
    from methodology.models import PipChange

    lines = [
        (
            "Assess the focused change in the context of the complete PIP below. "
            "All changes form one atomic proposal; pending parents need not exist live."
        ),
        "",
        "--- Playbook snapshot ---",
        context_summary,
    ]
    if all_changes:
        lines.extend(
            [
                "",
                "--- Complete PIP change set ---",
                _format_change_list(all_changes, ref_map),
            ]
        )
        identity_lines = build_internal_ref_identity_lines(
            all_changes,
            ref_map,
            before_order=change.order,
        )
        if identity_lines:
            lines.extend([
                "",
                "--- Pending internal_ref identities (prior in this PIP) ---",
                *identity_lines,
                INTERNAL_REF_IDENTITY_NOTE,
            ])
    lines.extend([
        "",
        "--- Proposed change ---",
        f"change_type: {change.change_type}",
        f"entity_type: {change.entity_type}",
        f"name: {change.name or '(empty)'}",
        f"target_id: {change.target_id or '(none)'}",
        f"append_to_playbook_end: {change.append_to_playbook_end}",
        f"content / rationale:\n{change.content or '(empty)'}",
    ])
    lines.extend(_change_reference_lines(change, all_changes or [change], ref_map or {}))
    if change.display_order is not None:
        lines.append(f"display_order: {change.display_order}")
    if change.target_name_snapshot:
        lines.append(f"target_name_snapshot: {change.target_name_snapshot}")
    if change.parent_workflow_id:
        lines.append(f"parent_workflow_id: {change.parent_workflow_id}")
    if change.change_type in {PipChange.CHANGE_LINK, PipChange.CHANGE_UNLINK}:
        src = _annotate_internal_ref_endpoint(
            change.source_entity_ref or "",
            all_changes or [change],
            ref_map,
        )
        tgt = _annotate_internal_ref_endpoint(
            change.target_entity_ref or "",
            all_changes or [change],
            ref_map,
        )
        lines.extend([
            f"relationship_type: {change.relationship_type}",
            f"source: {change.source_entity_type} {src}",
            f"target: {change.target_entity_type} {tgt}",
        ])
    if change.internal_ref:
        lines.append(f"internal_ref: {change.internal_ref}")
    if change.insert_after_activity_id:
        lines.append(f"insert_after_activity_id: {change.insert_after_activity_id}")
    return "\n".join(lines)
