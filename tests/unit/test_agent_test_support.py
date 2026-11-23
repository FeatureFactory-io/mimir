"""Failure-sensitive contracts for the agent test infrastructure."""

import pytest

from methodology.llm.base import BaseLLM, LLMError, LLMMessage, LLMResponse
from tests.support.agent_story import assert_agent_story
from tests.support.scripted_llm import ScriptedLLM

MESSAGES = (LLMMessage(role="user", content="Public contribution facts"),)


def test_scripted_llm_with_finite_queue_replays_order_and_rejects_exhaustion():
    scripted = ScriptedLLM(["first", LLMResponse("second", model="fixture")])
    assert isinstance(scripted, BaseLLM)
    assert scripted.complete(MESSAGES).content == "first"
    assert scripted.complete(MESSAGES).model == "fixture"
    with pytest.raises(LLMError, match="exhausted"):
        scripted.complete(MESSAGES)


def test_scripted_llm_with_caller_list_mutation_preserves_original_queue():
    responses = ["original"]
    scripted = ScriptedLLM(responses)
    responses[0] = "mutated"
    assert scripted.complete(MESSAGES).content == "original"


@pytest.mark.parametrize("responses", [[], ["ok", None], [object()], "not a queue"])
def test_scripted_llm_with_invalid_queue_rejects_input(responses):
    with pytest.raises(ValueError):
        ScriptedLLM(responses)


def test_scripted_llm_with_scripted_error_surfaces_failure_and_consumes_turn():
    scripted = ScriptedLLM([LLMError("provider timeout"), "recovery"])
    with pytest.raises(LLMError, match="provider timeout"):
        scripted.complete(MESSAGES)
    assert scripted.complete(MESSAGES).content == "recovery"


def test_scripted_llm_with_invalid_request_does_not_consume_response():
    scripted = ScriptedLLM(["still queued"])
    with pytest.raises(ValueError):
        scripted.complete([], max_tokens=0)
    assert scripted.complete(MESSAGES).content == "still queued"


def test_agent_story_with_real_trace_shape_accepts_required_control_beats():
    trace = {
        "workflow_id": "contribution_summary",
        "events": [
            {"beat": "entry", "details": "submitter_id=3 public_only=true"},
            {"beat": "domain_write", "details": "summary_saved=true"},
        ],
    }
    assert_agent_story(
        trace,
        workflow="contribution_summary",
        beats={
            "entry": ["submitter_id=3", "public_only=true"],
            "domain_write": ["summary_saved=true"],
        },
    )


@pytest.mark.parametrize(
    "trace,beats,fragment",
    [
        ({"workflow_id": "other", "events": []}, {"entry": ["start"]}, "workflow"),
        (
            {"workflow_id": "x", "events": []},
            {"domain_write": ["saved"]},
            "domain_write",
        ),
        (
            {
                "workflow_id": "x",
                "events": [
                    {"beat": "entry", "details": "a"},
                    {"beat": "entry", "details": "b"},
                ],
            },
            {"entry": ["a", "b"]},
            "entry",
        ),
    ],
)
def test_agent_story_with_missing_control_beat_fails_precisely(trace, beats, fragment):
    with pytest.raises(AssertionError, match=fragment):
        assert_agent_story(trace, workflow="x", beats=beats)


@pytest.mark.parametrize(
    "workflow,beats",
    [
        ("", {"entry": ["x"]}),
        ("x", {}),
        ("x", {"entry": []}),
        ("x", {"entry": [""]}),
        ("x", {"entry": "not a fragment list"}),
    ],
)
def test_agent_story_with_empty_requirements_rejects_vacuous_proof(workflow, beats):
    with pytest.raises(ValueError):
        assert_agent_story(
            {"workflow_id": "x", "events": []}, workflow=workflow, beats=beats
        )
