"""Shared agent control-plane trace assertions; distinct from caplog checks."""

from collections.abc import Mapping, Sequence
from typing import Any


def assert_agent_story(
    trace: Mapping[str, Any], *, workflow: str, beats: Mapping[str, Sequence[str]]
) -> None:
    """Assert workflow identity and nonempty fragments within each trace beat.

    :param trace: workflow_id plus events of beat/details dictionaries.
    :param workflow: Required workflow identifier.
    :param beats: Beat names mapped to required fragments within one event.
    :return: None if every required control-plane beat is present.
    :raises AssertionError: Naming a wrong workflow or missing beat/fragment.
    :raises ValueError: For empty workflow, beats or fragment requirements.
    """
    invalid = any(
        isinstance(fragments, str)
        or not fragments
        or any(not isinstance(f, str) or not f for f in fragments)
        for fragments in beats.values()
    )
    if not workflow or not beats or invalid:
        raise ValueError("Nonempty workflow and beat requirements are mandatory")
    assert (
        trace.get("workflow_id") == workflow
    ), f"Wrong workflow; expected {workflow!r}"
    events = trace.get("events", [])
    for beat, fragments in beats.items():
        matching = [event for event in events if event.get("beat") == beat]
        if not any(
            all(fragment in str(event.get("details", "")) for fragment in fragments)
            for event in matching
        ):
            raise AssertionError(
                f"Missing agent story beat {beat!r}; required {list(fragments)!r}"
            )
