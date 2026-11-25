"""Run only through Django's initialized shell inside the owned companion."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from django.contrib.auth.models import User
from django.core import serializers
from django.core.management import call_command
from django.urls import reverse
from methodology.models import (
    Activity,
    AgentInteraction,
    ExpertProfile,
    KarmaAward,
    ProcessImprovementProposal,
)
from methodology.services.copy_prompt_service import CopyPromptService
from tests.support.experts_data import (
    CedarDatabaseScope,
    _resolve_database_scope,
    load_cedar_baseline,
)

_ROOT = Path("/experts-scope")
_OUTPUT = Path("/output")


def scope() -> CedarDatabaseScope:
    """Validate actual role, database, owner, comment and private marker first.

    :return: Positively verified companion scope; never an ambient URL inference.
    :raises ValueError: If any runtime/file/SQL ownership check differs.
    """
    marker = _ROOT / "owner.json"
    record = json.loads(marker.read_text())
    claimed = CedarDatabaseScope(
        "owned_staging", record["database"], marker, record["owner_id"]
    )
    return _resolve_database_scope(claimed)


def state() -> dict[str, Any]:
    """Hash full domain rows without exporting prose, credentials or ledger bodies.

    :return: Counts and a hash of immutable/public-domain test state.
    """
    models = (KarmaAward, ExpertProfile, AgentInteraction, ProcessImprovementProposal)
    payload = [
        serializers.serialize("json", model.objects.order_by("pk")) for model in models
    ]
    return {
        "users": User.objects.count(),
        "awards": KarmaAward.objects.count(),
        "profiles": ExpertProfile.objects.count(),
        "domain_sha256": hashlib.sha256(json.dumps(payload).encode()).hexdigest(),
    }


def write_private(path: Path, payload: dict[str, Any]) -> None:
    """Create a private file without truncating an existing owner record.

    :param path: New file in the owned scope, e.g. /experts-scope/domain-state.json.
    :param payload: Safe snapshot metadata.
    :return: None once an exclusive mode0600 file exists.
    :raises OSError: The file already exists or cannot be created safely.
    """
    descriptor = os.open(
        path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w") as stream:
        json.dump(payload, stream)


def public_copy_oracle() -> None:
    """Export only a digest/length and actual route for the public guest copy.

    :return: None after the real service builds activity6203's prompt.
    :raises AssertionError: The imported public activity has no prompt.
    """
    activity = Activity.objects.select_related("workflow__playbook").get(pk=6203)
    prompt = CopyPromptService.build_activity_prompt(activity)
    assert prompt
    payload = {
        "path": reverse("activity_detail", args=(6201, 6202, 6203)),
        "sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "bytes": len(prompt.encode()),
    }
    (_OUTPUT / "public-copy.json").write_text(json.dumps(payload, indent=2) + "\n")


def initialize() -> None:
    """Check the empty dedicated DB before migration and import Cedar once.

    :return: None after exact seeded counts and a private baseline are recorded.
    :raises ValueError: Any scope proof fails before migrations/fixture access.
    :raises AssertionError: Imported real data differs from the Cedar baseline.
    """
    owned = scope()
    call_command("migrate", interactive=False, verbosity=0)
    load_cedar_baseline(scope=owned)
    snapshot = state()
    assert (snapshot["users"], snapshot["awards"], snapshot["profiles"]) == (
        12,
        2129,
        11,
    )
    write_private(_ROOT / "domain-state.json", snapshot)
    public_copy_oracle()
    call_command("collectstatic", interactive=False, verbosity=0)
    (_OUTPUT / "seed-receipt.json").write_text(json.dumps(snapshot, indent=2) + "\n")
    print(json.dumps({"stage": "owned_database_initialized", **snapshot}))


def verify_after() -> None:
    """Recheck ownership and domain state after read-only/guest-copy browser smoke.

    :return: None when real rows and decision-mail destination remain unchanged.
    :raises AssertionError: A browser read/guest copy created an unexpected effect.
    """
    scope()
    snapshot = state()
    assert snapshot == json.loads((_ROOT / "domain-state.json").read_text())
    assert not list(Path("/experts-mail").iterdir())
    result = {
        "scope_rechecked": True,
        "domain_unchanged": True,
        "decision_mail_files": 0,
        **snapshot,
    }
    (_OUTPUT / "post-browser-state.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result))
