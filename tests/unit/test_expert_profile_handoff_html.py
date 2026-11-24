"""Boundary checks for the shared test-only rendered-link extractor."""

from __future__ import annotations

import pytest

from tests.support.expert_profile_handoff import extract_maria_profile_href

_MARIA_PATH = "/experts/mrodriguez/"
_MARIA_TEST_ID = "experts-view-profile-mrodriguez"
_MARIA_ANCHOR = (
    f'<a data-testid="{_MARIA_TEST_ID}" href="{_MARIA_PATH}">View profile</a>'
)


@pytest.mark.parametrize(
    "html",
    [
        pytest.param("", id="missing-anchor"),
        pytest.param(f"{_MARIA_ANCHOR}{_MARIA_ANCHOR}", id="duplicate-anchor"),
        pytest.param(
            f'<a data-testid="{_MARIA_TEST_ID}">View profile</a>', id="missing-href"
        ),
        pytest.param(
            f'<a data-testid="{_MARIA_TEST_ID}" href="https://example.com{_MARIA_PATH}">View profile</a>',
            id="external-href",
        ),
        pytest.param(
            f'<a data-testid="{_MARIA_TEST_ID}" href="//example.com{_MARIA_PATH}">View profile</a>',
            id="network-path-href",
        ),
        pytest.param(
            f'<a data-testid="{_MARIA_TEST_ID}" href="/experts/sreed/">View profile</a>',
            id="wrong-local-href",
        ),
        pytest.param(
            f'<button data-testid="{_MARIA_TEST_ID}" href="{_MARIA_PATH}">View profile</button>',
            id="non-anchor",
        ),
        pytest.param(
            f'<a data-testid="{_MARIA_TEST_ID}" href="/experts/sreed/" href="{_MARIA_PATH}">View profile</a>',
            id="ambiguous-href",
        ),
    ],
)
def test_extract_maria_profile_href_with_invalid_anchor_rejects(html: str) -> None:
    """Reject absent, ambiguous or invalid navigation evidence.

    :param html: Invalid HTML sample. Example: an anchor without href.
    :return: None. Example: extraction raises AssertionError as required.
    :raises AssertionError: Extraction accepts an invalid sample.
    """
    with pytest.raises(AssertionError):
        extract_maria_profile_href(html)


def test_extract_maria_profile_href_with_other_links_returns_maria_path() -> None:
    """Resolve the exact Maria hook among unrelated profile links.

    :return: None. Example: the local Maria path is returned as rendered.
    :raises AssertionError: Extraction chooses the wrong link or changes its href.
    """
    sofia_anchor = '<a data-testid="experts-view-profile-sreed" href="/experts/sreed/">View profile</a>'
    html = f"<section>{sofia_anchor}{_MARIA_ANCHOR}</section>"

    assert extract_maria_profile_href(html) == _MARIA_PATH
