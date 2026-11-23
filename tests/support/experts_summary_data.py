from __future__ import annotations

"""Real lifecycle setup and the sole scoped provider composition for proofs."""
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from django.contrib.auth.base_user import AbstractBaseUser
from methodology.llm.base import LLMError, LLMResponse
from methodology.models import Playbook, ProcessImprovementProposal, Workflow
from tests.support.experts_data import CedarDataset
from tests.support.scripted_llm import ScriptedLLM


def prepare_summary_submission(cedar: CedarDataset) -> ProcessImprovementProposal:
    """Create Maria's exact draft and one ADD through real PIPService methods.

    Use Hana's real Accessible Forms Review v2.0 and an existing workflow.
    Do not set reviewed/accepted state or call award hooks during setup.

    :param cedar: Imported real baseline. Example: load_cedar_baseline().
    :return: Draft with one Screen Reader Error Recovery ADD. Example: PIP 7301.
    :raises ValueError: For missing or inconsistent Cedar objects.
    """
    raise NotImplementedError()


def _submission_target(
    cedar: CedarDataset,
) -> tuple[AbstractBaseUser, Playbook, Workflow]:
    """Resolve Maria, Hana's public released v2.0 and its real target workflow.

    :param cedar: Real baseline handles. Example: CedarDataset(...).
    :return: Submitter, target and workflow. Example: (maria, playbook6106, workflow).
    :raises ValueError: For missing objects, wrong owner/status/version or workflow.
    """
    raise NotImplementedError()


@contextmanager
def summary_processing_scope(
    responses: Sequence[LLMResponse | LLMError | str],
    *,
    rates: Mapping[str, tuple[str, str]] | None = None,
) -> Iterator[ScriptedLLM]:
    """Install one provider-only setting for real HTTP/service/live-server work.

    Future body creates ScriptedLLM, enters override_settings with
    GALDR_EAGER=True, CONTRIBUTION_SUMMARY_LLM=that instance and optional
    CONTRIBUTION_SUMMARY_MODEL_RATES, yields it, and restores settings in finally.

    No service, factory, ORM method, clock or scheduler is mocked. This scope
    makes no implicit queue-consumption assertion because reject-before-provider
    tests intentionally leave turns untouched.

    :param responses: Explicit finite queue. Example: (summary, assessment).
    :param rates: Optional deterministic model rates. Example: {"scripted": ("3", "15")}.
    :return: Context yielding actual captured port. Example: ScriptedLLM instance.
    :raises ValueError: For invalid responses or rate data.
    """
    raise NotImplementedError()


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
    raise NotImplementedError()


def _read_script_items(path: Path) -> tuple[Mapping[str, Any], ...]:
    """Parse a nonempty sequence of explicit response/error objects.

    :param path: Script path. Example: PRF-EXPERTS-02/reject_provider.json.
    :return: Ordered objects. Example: ({"kind": "error", "code": "provider_failed"},).
    :raises ValueError: For invalid JSON shape or empty queues.
    :raises OSError: When the file cannot be read.
    """
    raise NotImplementedError()


def _decode_script_item(
    item: Mapping[str, Any], change_id: int
) -> LLMResponse | LLMError:
    """Decode one allowed response or explicit safe error without fallback.

    :param item: Typed script object. Example: {"kind": "error", "code": "provider_failed"}.
    :param change_id: Actual assessment target. Example: 7302.
    :return: One explicit queue item. Example: LLMError("provider_failed").
    :raises ValueError: For unsupported kinds or malformed fields.
    """
    raise NotImplementedError()


def _response_from_item(item: Mapping[str, Any], change_id: int) -> LLMResponse:
    """Build a normalized response from explicit content/model/usage metadata.

    :param item: Response object. Example: {"kind": "response", "content": "Public facts."}.
    :param change_id: Actual assessment target. Example: 7302.
    :return: Normalized response. Example: LLMResponse("Public facts.", model="scripted").
    :raises ValueError: For malformed content, usage or stop reason.
    """
    raise NotImplementedError()


def _resolve_assessment_payload(
    payload: Mapping[str, Any], change_id: int
) -> Mapping[str, Any]:
    """Copy assessment JSON and resolve only declared change_id markers.

    :param payload: Assessment object. Example: {"change_assessments": [{"change_id": "$CHANGE_ID"}]}.
    :param change_id: Actual created change. Example: 7302.
    :return: Copied resolved object. Example: change_id=7302.
    :raises ValueError: For unknown markers or marker placement.
    """
    raise NotImplementedError()


def _script_usage(value: Any) -> Mapping[str, int]:
    """Validate explicitly supplied usage without inventing missing counts.

    :param value: Usage object or absent value. Example: {"input_tokens": 120}.
    :return: Valid counts. Example: {"input_tokens": 120}.
    :raises ValueError: For booleans, negative or malformed usage.
    """
    raise NotImplementedError()
