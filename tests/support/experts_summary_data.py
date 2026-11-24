"""Real lifecycle setup and the sole scoped provider composition for proofs."""

from __future__ import annotations

import json
import re
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from typing import Any

from django.contrib.auth.base_user import AbstractBaseUser
from django.test import override_settings

from methodology.llm.base import LLMError, LLMResponse
from methodology.models import PipChange, Playbook, ProcessImprovementProposal, Workflow
from methodology.services.pip_service import PIPService
from tests.support.experts_data import CedarDataset
from tests.support.scripted_llm import ScriptedLLM

SUMMARY_SCRIPTS = Path(__file__).parents[1] / "fixtures/llm_scripts"
SUMMARY_PIP_TITLE = "Screen Reader Error Recovery"
SUMMARY_PIP_BODY = "Unpublished rationale for the proposed screen reader activity."
SUMMARY_CHANGE_BODY = "Unpublished guidance for recovering from a form error."
_CEDAR_TARGET_PLAYBOOK_ID = 6106
_CHANGE_MARKER = "$CHANGE_ID"
_SCRIPT_MARKER = re.compile(r"\$[A-Z][A-Z0-9_]*")


def prepare_summary_submission(cedar: CedarDataset) -> ProcessImprovementProposal:
    """Create Maria's exact draft and one ADD through real PIPService methods.

    Use Hana's real Accessible Forms Review v2.0 and an existing workflow.
    Do not set reviewed/accepted state or call award hooks during setup.

    :param cedar: Imported real baseline. Example: load_cedar_baseline().
    :return: Draft with one Screen Reader Error Recovery ADD. Example: PIP 7301.
    :raises ValueError: For missing or inconsistent Cedar objects.
    """
    maria, playbook, workflow = _submission_target(cedar)
    pip = PIPService.create_draft_for_playbook(
        actor=maria,
        playbook_id=playbook.pk,
        title=SUMMARY_PIP_TITLE,
        summary=SUMMARY_PIP_BODY,
    )
    PIPService.add_change(
        actor=maria,
        pip=pip,
        change_type=PipChange.CHANGE_ADD,
        entity_type=PipChange.ENTITY_ACTIVITY,
        parent_workflow_id=workflow.pk,
        name=SUMMARY_PIP_TITLE,
        content=SUMMARY_CHANGE_BODY,
    )
    return pip


def _submission_target(
    cedar: CedarDataset,
) -> tuple[AbstractBaseUser, Playbook, Workflow]:
    """Resolve Maria, Hana's public released v2.0 and its real target workflow.

    :param cedar: Real baseline handles. Example: CedarDataset(...).
    :return: Submitter, target and workflow. Example: (maria, playbook6106, workflow).
    :raises ValueError: For missing objects, wrong owner/status/version or workflow.
    """
    maria = cedar.users_by_username.get("mrodriguez")
    hana = cedar.users_by_username.get("hkim")
    playbook = cedar.playbooks_by_pk.get(_CEDAR_TARGET_PLAYBOOK_ID)
    if (
        maria is None
        or hana is None
        or playbook is None
        or playbook.author_id != hana.pk
        or playbook.name != "Accessible Forms Review"
        or playbook.version != Decimal("2.0")
        or (playbook.status, playbook.visibility) != ("released", "public")
    ):
        raise ValueError(
            "Expected Maria and Hana's public Accessible Forms Review v2.0."
        )
    workflow = playbook.workflows.order_by("order", "pk").first()
    if workflow is None:
        raise ValueError("Cedar's target playbook has no workflow.")
    return maria, playbook, workflow


@contextmanager
def summary_processing_scope(
    responses: Sequence[LLMResponse | LLMError | str],
    *,
    rates: Mapping[str, tuple[str, str]] | None = None,
) -> Iterator[ScriptedLLM]:
    """Install one provider-only setting for real HTTP/service/live-server work.

    Enable eager processing and install the finite CAP-004 transport for this scope.

    No service, factory, ORM method, clock or scheduler is mocked. This scope
    makes no implicit queue-consumption assertion because reject-before-provider
    tests intentionally leave turns untouched.

    :param responses: Explicit finite queue. Example: (summary, assessment).
    :param rates: Optional deterministic model rates. Example: {"scripted": ("3", "15")}.
    :return: Context yielding actual captured port. Example: ScriptedLLM instance.
    :raises ValueError: For invalid responses or rate data.
    """
    llm = ScriptedLLM(responses)
    configured_rates = {} if rates is None else dict(rates)
    with override_settings(
        GALDR_EAGER=True,
        CONTRIBUTION_SUMMARY_LLM=llm,
        CONTRIBUTION_SUMMARY_MODEL_RATES=configured_rates,
    ):
        yield llm


def load_summary_script(
    path: Path, change_id: int
) -> tuple[LLMResponse | LLMError, ...]:
    """Load an explicit queue and resolve the single permitted change-ID marker.

    The script is data, not executable templating. A content object can carry
    assessment JSON; only change_id fields containing "$CHANGE_ID" are replaced.

    :param path: Repository script. Example: Path("tests/fixtures/llm_scripts/PRF-EXPERTS-01/happy.json").
    :param change_id: Actual created change ID. Example: 7302.
    :return: Finite port queue. Example: (LLMResponse("Public facts."), verdict).
    :raises ValueError: For malformed scripts or invalid marker placement.
    :raises OSError: When the script cannot be read.
    """
    if type(change_id) is not int or change_id <= 0:
        raise ValueError("A real positive change ID is required.")
    return tuple(
        _decode_script_item(item, change_id) for item in _read_script_items(path)
    )


def _read_script_items(path: Path) -> tuple[Mapping[str, Any], ...]:
    """Parse a nonempty sequence of explicit response/error objects.

    :param path: Script path. Example: PRF-EXPERTS-02/reject_provider.json.
    :return: Ordered objects. Example: ({"kind": "error", "code": "provider_failed"},).
    :raises ValueError: For invalid JSON shape or empty queues.
    :raises OSError: When the file cannot be read.
    """
    document = json.loads(path.read_text(encoding="utf-8"))
    responses = document.get("responses") if isinstance(document, dict) else None
    if (
        not isinstance(responses, list)
        or not responses
        or any(not isinstance(item, dict) for item in responses)
    ):
        raise ValueError("Expected a nonempty sequence of summary script objects.")
    return tuple(responses)


def _decode_script_item(
    item: Mapping[str, Any], change_id: int
) -> LLMResponse | LLMError:
    """Decode one allowed response or explicit safe error without fallback.

    :param item: Typed script object. Example: {"kind": "error", "code": "provider_failed"}.
    :param change_id: Actual assessment target. Example: 7302.
    :return: One explicit queue item. Example: LLMError("provider_failed").
    :raises ValueError: For unsupported kinds or malformed fields.
    """
    if item.get("kind") == "response":
        return _response_from_item(item, change_id)
    if item.get("kind") == "error":
        code = item.get("code")
        if isinstance(code, str) and code:
            return LLMError(code)
    raise ValueError("Expected a normalized response or an explicit scripted error.")


def _response_from_item(item: Mapping[str, Any], change_id: int) -> LLMResponse:
    """Build a normalized response from explicit content/model/usage metadata.

    :param item: Response object. Example: {"kind": "response", "content": "Public facts."}.
    :param change_id: Actual assessment target. Example: 7302.
    :return: Normalized response. Example: LLMResponse("Public facts.", model="scripted").
    :raises ValueError: For malformed content, usage or stop reason.
    """
    content = item.get("content")
    if isinstance(content, dict):
        content = json.dumps(_resolve_assessment_payload(content, change_id))
    model = item.get("model", "")
    stop_reason = item.get("stop_reason", "end_turn")
    if not all(isinstance(field, str) for field in (content, model, stop_reason)):
        raise ValueError(
            "Scripted response content, model and stop reason must be strings."
        )
    return LLMResponse(content, model, _script_usage(item.get("usage")), stop_reason)


def _resolve_assessment_payload(
    payload: Mapping[str, Any], change_id: int
) -> Mapping[str, Any]:
    """Copy assessment JSON and resolve only declared change_id markers.

    :param payload: Assessment object. Example: {"change_assessments": [{"change_id": "$CHANGE_ID"}]}.
    :param change_id: Actual created change. Example: 7302.
    :return: Copied resolved object. Example: change_id=7302.
    :raises ValueError: For unknown markers or marker placement.
    """
    result = {}
    for key, value in payload.items():
        if _SCRIPT_MARKER.search(key):
            raise ValueError("Change markers must be values of a change_id field.")
        if key == "change_id" and value == _CHANGE_MARKER:
            result[key] = change_id
        elif isinstance(value, dict):
            result[key] = _resolve_assessment_payload(value, change_id)
        elif isinstance(value, list):
            result[key] = [
                (
                    _resolve_assessment_payload(row, change_id)
                    if isinstance(row, dict)
                    else row
                )
                for row in value
            ]
        else:
            result[key] = value
    if _SCRIPT_MARKER.search(json.dumps(result)):
        raise ValueError("Unexpected marker in scripted assessment.")
    return result


def _script_usage(value: Any) -> Mapping[str, int]:
    """Validate explicitly supplied usage without inventing missing counts.

    :param value: Usage object or absent value. Example: {"input_tokens": 120}.
    :return: Valid counts. Example: {"input_tokens": 120}.
    :raises ValueError: For booleans, negative or malformed usage.
    """
    if value is None:
        return {}
    if not isinstance(value, dict) or any(
        key not in {"input_tokens", "output_tokens"}
        or type(tokens) is not int
        or tokens < 0
        for key, tokens in value.items()
    ):
        raise ValueError(
            "Scripted usage requires known keys and nonnegative integer counts."
        )
    return value
