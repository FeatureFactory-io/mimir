from __future__ import annotations

from behave import given, when, then
from behave.runner import Context


@given("Maria's stored summary contains stable public facts and no aggregate scores")
def stable_summary(context: Context) -> None:
    """Read and snapshot the real seeded nine-sentence summary.
    :param context: Shared Cedar context. Example: context.cedar_dataset.
    :return: None. Example: immutable state saved on context.
    :raises AssertionError: For missing, altered or score-bearing prose.
    """
    raise NotImplementedError()


@when("an eligible consumption awards her 5 points")
def eligible_consumption(context: Context) -> None:
    """Use S36's real authorized activity-copy receipt with Maria's session.
    :param context: Real client and Cedar dataset. Example: Maria and activity 6203.
    :return: None. Example: successful receipt stored on context.
    :raises AssertionError: For failed receipt or missing atomic pair.
    """
    raise NotImplementedError()


@then("the numeric total is 8205")
def live_total(context: Context) -> None:
    """Check actual projection and rendered numeric surfaces.
    :param context: Post-receipt context. Example: EV01 completed.
    :return: None. Example: Maria 8205 and Mike 12455 verified.
    :raises AssertionError: For stale or incorrect totals/category/source.
    """
    raise NotImplementedError()


@then("the stored summary is unchanged")
def unchanged_summary(context: Context) -> None:
    """Compare exact paragraph, refresh metadata and interaction snapshots.
    :param context: Before/after evidence. Example: identical nine sentences.
    :return: None. Example: persistent summary state is unchanged.
    :raises AssertionError: For text, refresh metadata or interaction change.
    """
    raise NotImplementedError()


@then("no extra summary-generation call is required")
def no_extra_generation(context: Context) -> None:
    """Verify completed receipt/display wiring plus the required agent-proof link.
    :param context: Real receipt and display responses. Example: S28 execution.
    :return: None. Example: no refresh dispatch in these paths.
    :raises AssertionError: For generation wiring or missing certification mapping.
    """
    raise NotImplementedError()
