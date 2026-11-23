from __future__ import annotations

"""Reusable assertions consuming S03's existing Django Element helpers."""


def assert_public_design_ranking(html: str) -> None:
    """Check all five public Design cards in their fixed Cedar order.

    :param html: Rendered HTML str. Example: response.content.decode().
    :return: None. Example: assertions succeed.
    :raises AssertionError: Wrong count, order, totals or excluded card.
    """
    raise NotImplementedError()


def assert_guest_auth_banner(html: str) -> None:
    """Check the guest banner's named authentication anchors.

    :param html: Rendered HTML str. Example: response.content.decode().
    :return: None. Example: Sign In and Register both match routes.
    :raises AssertionError: Missing, duplicated or incorrect banner action.
    """
    raise NotImplementedError()


def assert_no_private_account_controls(html: str) -> None:
    """Reject own-profile controls and the fictional private-token sentinel.

    :param html: Rendered HTML str. Example: anonymous Experts response.
    :return: None. Example: no private account control exists.
    :raises AssertionError: Private control or fixture token sentinel appears.
    """
    raise NotImplementedError()
