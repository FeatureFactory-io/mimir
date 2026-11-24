"""S23 normal submission steps; real Django domain and captured provider seam."""

from __future__ import annotations

from decimal import Decimal

from behave import given, then, when
from behave.runner import Context

from methodology.models import PipChange, Playbook, VersionSource


@given("Hana owns Accessible Forms Review at version 2.0")
def hana_target_has_original_publication(context: Context) -> None:
    """Verify real Hana authorship, current v2.0 and historical accepted-change receipts.

    :param context: Actual isolated Django-client acceptance state. Example: context.cedar_dataset.
    :return: None when the described real observation holds. Example: None.
    :raises AssertionError: Actual domain, response or recorded boundary differs.
    """
    cedar = context.cedar_dataset
    hana = cedar.users_by_username["hkim"]
    target = Playbook.objects.get(pk=cedar.playbook_ids[6106])
    assert (target.author_id, target.name, target.version) == (
        hana.pk,
        "Accessible Forms Review",
        Decimal("2.0"),
    )
    assert (target.visibility, target.status) == ("public", "released")
    historical_pip = cedar.pips_by_key["HIST-MARIA-DESIGN-01"]
    receipt = target.versions.get(
        pip=historical_pip,
        source=VersionSource.PIP_SOURCE,
        version_number=target.version,
    )
    accepted = historical_pip.changes.filter(admin_decision=PipChange.ADMIN_ACCEPT)
    assert set(receipt.snapshot_data["accepted_change_ids"]) == {
        change.pk for change in accepted
    }
    assert receipt.snapshot_data["accepted_change_ids"]


@given('Maria drafts Screen Reader Error Recovery with one ADD Activity change')
def maria_drafts_error_recovery_activity(context: Context) -> None:
    """Create the actual permitted draft/change through existing PIPService against Hana workflow; retain private title.

    :param context: Actual isolated Django-client acceptance state. Example: context.cedar_dataset.
    :return: None when the described real observation holds. Example: None.
    :raises AssertionError: Actual domain, response or recorded boundary differs.
    """
    raise NotImplementedError()

@when('Maria submits the PIP through its normal lifecycle')
def maria_submits_normal_summary_lifecycle(context: Context) -> None:
    """Submit through the actual authenticated Django POST with one captured finite ScriptedLLM port for summary then assessment; retain requests and DB snapshots.

    :param context: Actual isolated Django-client acceptance state. Example: context.cedar_dataset.
    :return: None when the described real observation holds. Example: None.
    :raises AssertionError: Actual domain, response or recorded boundary differs.
    """
    raise NotImplementedError()

@then('a contribution-summary refresh is requested during processing')
def summary_refresh_occurs_during_processing(context: Context) -> None:
    """Inspect the real captured request and persisted interaction from normal processing, without patching services.

    :param context: Actual isolated Django-client acceptance state. Example: context.cedar_dataset.
    :return: None when the described real observation holds. Example: None.
    :raises AssertionError: Actual domain, response or recorded boundary differs.
    """
    raise NotImplementedError()

@then("Maria's total remains {total:d}")
def maria_summary_total_remains(context: Context, total: int) -> None:
    """Reconcile actual ledger total and unchanged original award snapshots across submission or resubmission.

:param context: Actual isolated Django-client acceptance state. Example: context.cedar_dataset.
:param total: Expected actual ledger total. Example: 8200.
:return: None when the described real observation holds. Example: None.
:raises AssertionError: Actual domain, response or recorded boundary differs."""
    raise NotImplementedError()

@then('the new proposal is not described as accepted')
def summary_excludes_unpublished_proposal(context: Context) -> None:
    """Inspect actual captured public input and stored prose: draft title/change content excluded; no accepted publication receipt.

    :param context: Actual isolated Django-client acceptance state. Example: context.cedar_dataset.
    :return: None when the described real observation holds. Example: None.
    :raises AssertionError: Actual domain, response or recorded boundary differs.
    """
    raise NotImplementedError()

@then('the successful public summary is stored on her profile')
def summary_success_persists_validated_prose(context: Context) -> None:
    """Compare actual validated provider text, stored last-good text, timestamp and interaction outcome.

    :param context: Actual isolated Django-client acceptance state. Example: context.cedar_dataset.
    :return: None when the described real observation holds. Example: None.
    :raises AssertionError: Actual domain, response or recorded boundary differs.
    """
    raise NotImplementedError()

@then('it contains at most {limit:d} sentences')
def summary_obeys_sentence_bound(context: Context, limit: int) -> None:
    """Count the actual stored plain-prose sentences using the real shared validator, including the full final sentence.

:param context: Actual isolated Django-client acceptance state. Example: context.cedar_dataset.
:param limit: Maximum allowed stored sentence count. Example: 14.
:return: None when the described real observation holds. Example: None.
:raises AssertionError: Actual domain, response or recorded boundary differs."""
    raise NotImplementedError()
