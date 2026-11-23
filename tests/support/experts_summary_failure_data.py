from __future__ import annotations

"""S29 real Cedar failure-case setup; no alternate production collaborator."""
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from tests.support.scripted_llm import ScriptedLLM

if TYPE_CHECKING:
    from methodology.models import ExpertProfile, ProcessImprovementProposal
    from tests.support.experts_data import CedarDataset


@dataclass(frozen=True)
class S29FailureCase:
    """Real ORM handles and immutable pre-attempt comparison values."""

    cedar: CedarDataset
    pip: ProcessImprovementProposal
    profile: ExpertProfile
    paragraph: str
    successful_at: datetime | None
    award_ids: tuple[int, ...]


def prepare_s29_failure_case(*, has_last_good: bool = True) -> S29FailureCase:
    """Load Cedar and create the exact draft through S23's shared preparation.

    :param has_last_good: Seed Maria's exact nine-sentence successful fixture.
    :return: Real case with original paragraph/timestamp/award identities.
    :raises ValueError: For invalid baseline or missing shared bindings.
    """
    raise NotImplementedError()


def load_s29_submission_model(case: S29FailureCase, script_name: str) -> ScriptedLLM:
    """Use S23's loader with this real change ID and finite ordered script.

    :param case: Real Maria draft/ADD case.
    :param script_name: Allowlisted fixture name, for example s29_provider.
    :return: ScriptedLLM containing summary and real assessment responses.
    :raises ValueError: For unknown script or invalid fixture data.
    :raises OSError: If the fixture cannot be read.
    """
    raise NotImplementedError()
