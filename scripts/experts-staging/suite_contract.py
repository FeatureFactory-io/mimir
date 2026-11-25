"""Closed full-suite phases; application and control identities stay separate."""

from __future__ import annotations

from typing import Any, NamedTuple


class SuiteCase(NamedTuple):
    """One immutable phase with a true case and exact native actor."""

    phase: str
    case: str
    actor: str | None


FULL_CASES = (
    SuiteCase("core", "core", None),
    SuiteCase("nomination", "nomination", "esvensson"),
    SuiteCase("guest-public", "guest-public", None),
    SuiteCase("copy-maria", "copy-maria", "mrodriguez"),
    SuiteCase("copy-guest", "copy-guest", None),
    SuiteCase("copy-self", "copy-self", "mchen"),
    SuiteCase("authenticated-matrix", "authenticated-matrix", "esvensson"),
    SuiteCase("long-identity-and-prose", "long_identity_and_prose", "esvensson"),
    SuiteCase("missing-summary", "missing_summary", "esvensson"),
    SuiteCase("summary-acceptance", "summary-acceptance", "mrodriguez"),
    SuiteCase("final-confirmation", "nomination", "esvensson"),
)


def suite_cases(suite: str) -> tuple[SuiteCase, ...]:
    """Select the closed explicit suite.

    :param suite: core or full.
    :return: Immutable phases, e.g. eleven for full.
    :raises ValueError: Unknown suite.
    """
    if type(suite) is not str or suite not in {"core", "full"}:
        raise ValueError("Explicit core or full suite required.")
    return FULL_CASES if suite == "full" else FULL_CASES[:1]


def selected_case(manifest: dict[str, Any]) -> SuiteCase:
    """Resolve one exact phase/case pair without relabeling a guest.

    :param manifest: Public runtime declaration.
    :return: Exact closed phase.
    :raises ValueError: Unknown or mismatched declaration.
    """
    phase = manifest.get("suite_phase", "core")
    case = manifest.get("saga_case", "core")
    matches = [row for row in FULL_CASES if row.phase == phase and row.case == case]
    if len(matches) != 1:
        raise ValueError("Exact closed suite phase and true case required.")
    return matches[0]
