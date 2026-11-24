"""Test-only extraction of Maria's rendered View profile destination."""

from __future__ import annotations

from tests.support.experts_html import find_by_test_id

_MARIA_PROFILE_LINK = "experts-view-profile-mrodriguez"
_MARIA_PROFILE_PATH = "/experts/mrodriguez/"


def extract_maria_profile_href(html: str | bytes) -> str:
    """Require exactly one Maria anchor with the production local destination.

    :param html: Real rendered response HTML. Example: Design leaderboard HTML.
    :return: Destination str. Example: "/experts/mrodriguez/".
    :raises AssertionError: For an absent or ambiguous anchor or an incorrect href.
    :raises ValueError: For an unsupported input type or unparseable HTML.
    """
    anchor = find_by_test_id(html, _MARIA_PROFILE_LINK)
    assert anchor.name == "a", "Maria's View profile control must be an anchor."
    hrefs = [value for name, value in anchor.attributes if name == "href"]
    assert len(hrefs) == 1, "Maria's View profile anchor must have exactly one href."
    href = hrefs[0]
    assert (
        href == _MARIA_PROFILE_PATH
    ), "Maria's View profile href must be her local path."
    return href
