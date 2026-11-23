from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
import pytest
from methodology.llm.base import LLMError, LLMResponse


def _load_s27_script(path: Path) -> tuple[LLMResponse | LLMError, ...]:
    """Read an explicit nonempty CAP-004 script, rejecting invalid/exhausted data.

    :param path: PRF fixture path. Example: PRF-EXPERTS-03/happy.json.
    :return: Ordered normalized responses/errors. Example: (public_response,).
    :raises ValueError: For empty scripts, invalid entries or malformed JSON.
    """
    raise NotImplementedError()


@pytest.fixture
def s27_proof_case(db: None) -> Mapping[str, Any]:
    """Construct the actual Cedar baseline through the shared adapter.

    :param db: Real test DB. Example: pytest Django DB.
    :return: Real ORM/privacy variant. Example: Maria and publication receipts.
    :raises ValueError: If fixture invariants fail.
    """
    raise NotImplementedError()


@pytest.mark.django_db
@pytest.mark.agent_proof
def test_s27_summary_agent_story_happy(s27_proof_case: Mapping[str, Any]) -> None:
    """Prove PRF-EXPERTS-03 through the real read-only completion boundary.

    :param s27_proof_case: Real Cedar variant. Example: Maria's privacy cases.
    :return: None when request capture, public facts and production trace pass.
    :raises AssertionError: For leaked input, bypassed collaborators or domain writes.
    """
    raise NotImplementedError()


@pytest.mark.django_db
@pytest.mark.agent_proof
def test_s27_summary_agent_story_reject(s27_proof_case: Mapping[str, Any]) -> None:
    """Prove unsafe scripted output returns a sanitized typed failure trace.

    :param s27_proof_case: Real DB case. Example: Maria with last good profile data.
    :return: None when failure trace passes and database remains unchanged.
    :raises AssertionError: If unsafe output succeeds or changes domain state.
    """
    raise NotImplementedError()


@pytest.mark.django_db
@pytest.mark.agent_proof
def test_s27_summary_with_exhausted_script_fails_loudly(
    s27_proof_case: Mapping[str, Any],
) -> None:
    """Prove finite script exhaustion cannot produce fallback success.

    :param s27_proof_case: Real DB case. Example: Maria's public facts.
    :return: None when exhausted completion fails explicitly.
    :raises AssertionError: For fallback prose or a success outcome.
    """
    raise NotImplementedError()


@pytest.mark.agent_proof
@pytest.mark.django_db(transaction=True)
def test_s23_submission_agent_story_happy() -> None:
    """Prove PRF-EXPERTS-01 through real submit/query/prompt/store orchestration.

    :return: None. Example: None after trace, requests and unchanged-ledger assertions.
    :raises AssertionError: If a real collaborator is bypassed or prose is not stored.
    """
    raise NotImplementedError()


@pytest.mark.agent_proof
@pytest.mark.django_db(transaction=True)
def test_s23_submission_agent_story_reject() -> None:
    """Prove essential PRF-EXPERTS-02 failure retention and assessment continuity.

    :return: None. Example: None after failure trace and last-good assertions.
    :raises AssertionError: For domain_write on failure or changed PIP recovery.
    """
    raise NotImplementedError()


@pytest.mark.agent_proof
@pytest.mark.django_db(transaction=True)
def test_s23_submission_with_private_sentinels_agent_story_happy() -> None:
    """Prove PRF-EXPERTS-03 using the actual recorded summary request.

    :return: None. Example: None after public-fact retention and sentinel exclusions.
    :raises AssertionError: For private/unpublished evidence or mutable scores.
    """
    raise NotImplementedError()


@pytest.mark.agent_proof
@pytest.mark.django_db(transaction=True)
def test_s23_summary_interaction_agent_story_happy() -> None:
    """Prove PRF-OBS-01 persisted correlation, usage, latency and unknown cost.

    :return: None. Example: None after configured-rate and missing-rate assertions.
    :raises AssertionError: For missing trace metadata or fabricated zero cost.
    """
    raise NotImplementedError()
