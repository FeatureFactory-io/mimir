"""Deployment and model-boundary regressions for holistic PIP review (#185)."""

import json
import runpy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import yaml
from django.contrib.auth import get_user_model

from methodology.models import PipChange, Playbook, ProcessImprovementProposal
from methodology.services.galdr_client import GaldrClient, GaldrLLMError
from methodology.services.galdr_engine import GaldrEngine
from methodology.services.galdr_prompts import (
    HOLISTIC_SYSTEM_PROMPT,
    build_change_prompt,
    build_target_state_prompt,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "manifest", ["deploy/docker-compose.tmpl.yml", "docker-compose.prod.yml"]
)
def test_production_manifest_with_default_settings_enables_holistic_review(manifest):
    environment = yaml.safe_load((ROOT / manifest).read_text())["services"]["web"][
        "environment"
    ]
    assert (
        environment.get("GALDR_USE_TARGET_STATE") == "${GALDR_USE_TARGET_STATE:-true}"
    )


@pytest.mark.parametrize("holistic", [True, False])
def test_review_prompt_with_pending_parent_includes_full_batch_and_refs(holistic):
    parent = PipChange(
        id=1,
        order=1,
        change_type="ADD",
        entity_type="Workflow",
        name="Run Iteration",
        internal_ref="#wf-rit",
        content="Parent purpose",
    )
    child = PipChange(
        id=2,
        order=2,
        change_type="ADD",
        entity_type="Activity",
        name="Run PIN",
        parent_workflow_ref="#wf-rit",
        phase_ref="42",
        content="Scope. " * 100 + "Unique orchestration purpose.",
    )
    later = PipChange(
        id=3,
        order=3,
        change_type="LINK",
        relationship_type="activity_workflow",
        source_entity_ref="22",
        target_entity_ref="#wf-rit",
        content="Secondary membership",
    )
    changes = [parent, child, later]
    if holistic:
        prompt = build_target_state_prompt(
            ProcessImprovementProposal(id=1, title="Batch"),
            "Current",
            "Target",
            changes,
        )
    else:
        prompt = build_change_prompt(child, "Current", all_changes=changes)
    assert "parent_workflow_ref: #wf-rit (pending ADD" in prompt
    assert "phase_ref: 42" in prompt
    assert "Unique orchestration purpose." in prompt
    assert "Secondary membership" in prompt
    assert "activity_workflow" in prompt


def _processing_pip(db):
    user = get_user_model().objects.create_user(username="batch_contract")
    playbook = Playbook.objects.create(
        name="Batch", author=user, status="released", version="1.0"
    )
    pip = ProcessImprovementProposal.objects.create(
        playbook=playbook,
        created_by=user,
        title="Batch",
        status=ProcessImprovementProposal.STATUS_PROCESSING_GALDR,
    )
    change = PipChange.objects.create(
        pip=pip, change_type="ADD", entity_type="Workflow", name="New"
    )
    return pip, change


@pytest.mark.parametrize("case", ["missing", "duplicate", "foreign"])
def test_persist_with_incomplete_assessments_keeps_pip_unreviewed(db, case):
    pip, change = _processing_pip(db)
    row = (change.pk, "ACCEPT", "Valid")
    payloads = {
        "missing": [],
        "duplicate": [row, row],
        "foreign": [(change.pk + 999, "ACCEPT", "Wrong PIP")],
    }[case]
    GaldrEngine._persist_recommendations(pip.pk, payloads, holistic_note="COHERENT")
    pip.refresh_from_db()
    change.refresh_from_db()
    assert pip.status == ProcessImprovementProposal.STATUS_SUBMITTED
    assert change.galdr_recommendation == ""


def test_call_llm_with_large_batch_allocates_holistic_output_budget(monkeypatch):
    client = MagicMock()
    client.messages.create.return_value = SimpleNamespace(
        content=[SimpleNamespace(text=json.dumps({"ok": True}))], stop_reason="end_turn"
    )
    monkeypatch.setattr("anthropic.Anthropic", lambda: client)
    GaldrClient()._call_llm_raw("58 changes", system=HOLISTIC_SYSTEM_PROMPT)
    assert client.messages.create.call_args.kwargs["max_tokens"] >= 16384


def test_call_llm_with_truncated_output_raises_before_parsing(monkeypatch):
    client = MagicMock()
    client.messages.create.return_value = SimpleNamespace(
        content=[SimpleNamespace(text="{}")], stop_reason="max_tokens"
    )
    monkeypatch.setattr("anthropic.Anthropic", lambda: client)
    with pytest.raises(GaldrLLMError, match="truncated"):
        GaldrClient()._call_llm_raw("58 changes", system=HOLISTIC_SYSTEM_PROMPT)


@pytest.mark.parametrize(
    "configured,expected", [(None, True), ("true", True), ("false", False)]
)
def test_base_settings_with_review_flag_defaults_to_holistic(
    monkeypatch, configured, expected
):
    if configured is None:
        monkeypatch.delenv("GALDR_USE_TARGET_STATE", raising=False)
    else:
        monkeypatch.setenv("GALDR_USE_TARGET_STATE", configured)
    assert (
        runpy.run_path(str(ROOT / "mimir/settings/base.py"))["GALDR_USE_TARGET_STATE"]
        is expected
    )
