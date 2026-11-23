from __future__ import annotations

from behave.runner import Context


def prepare_stable_award_events(context: Context) -> None:
    """Prepare actual accepted receipt and successful consumption independently.

    :param context: Behave state. Example: context.cedar_dataset from S03.
    :return: None. Example: persisted change receipt plus stable action UUID.
    :raises AssertionError: Fixture/domain prerequisites differ from contract.
    """
    raise NotImplementedError()


def retry_recorded_award_events(context: Context) -> None:
    """Replay award recording only, preserving fixed identities and payloads.

    :param context: Prepared real event cases. Example: accepted and copy pair.
    :return: None. Example: actual retry outcomes retained for assertions.
    :raises AssertionError: Recording fails or repeats domain mutations.
    """
    raise NotImplementedError()


def assert_one_award_per_recipient(context: Context) -> None:
    """Assert complete row payloads and no duplicate applicable recipient.

    :param context: Actual retry results. Example: original PKs and timestamps.
    :return: None. Example: unchanged whole-event field projections.
    :raises AssertionError: Duplicate, missing, extra or changed row.
    """
    raise NotImplementedError()


def assert_event_recipient_cardinality(context: Context) -> None:
    """Assert one submitter award versus exact learner/author pair.

    :param context: Independent accepted/consumption cases. Example: 1 versus 2.
    :return: None. Example: correct recipients, amounts and categories.
    :raises AssertionError: Cardinality or attribution differs.
    """
    raise NotImplementedError()


def record_later_intentional_consumption(context: Context) -> None:
    """Use a new UUID and prove one additional complete consumption event.

    :param context: Original successful-consumption case. Example: UUID A.
    :return: None. Example: UUID B creates exactly two additional rows.
    :raises AssertionError: New action is suppressed or creates extra awards.
    """
    raise NotImplementedError()
