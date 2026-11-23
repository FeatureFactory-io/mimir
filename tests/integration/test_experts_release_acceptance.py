from __future__ import annotations

"""S30 real Django-client acceptance contract."""
import pytest


@pytest.mark.django_db
def test_karma_release_01_with_baseline_displays_award_and_product_ranking() -> None:
    """Execute Nora's normal release POST and query the live Product list.

    Assert baseline Nora=0, target version=1.0, Nora=5000 Product points, exact
    earned message, and rendered Product order apatel=5400 then nberg=5000.
    Read the real ledger/projection and HTTP responses; do not hard-code scores
    into rendered fixtures or replace domain services with mocks.

    :return: None when every KARMA-RELEASE-01 observable matches the contract.
    :raises AssertionError: If any amount, version, message or rank differs.
    """
    raise NotImplementedError()


@pytest.mark.django_db
def test_release_with_nonfirst_outcome_omits_earned_message() -> None:
    """Keep normal release success without claiming another first award.

    :return: None when later publication succeeds without an earned-5000 message.
    :raises AssertionError: If the message announces unearned points.
    """
    raise NotImplementedError()
