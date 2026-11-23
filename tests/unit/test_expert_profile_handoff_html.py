from __future__ import annotations

"""Boundary checks for the shared test-only rendered-link extractor."""
import pytest


@pytest.mark.parametrize(
    "html",
    [
        "",
        '<a data-testid="experts-view-profile-mrodriguez">View profile</a>',
        '<a data-testid="experts-view-profile-mrodriguez" href="https://example.com/">View profile</a>',
        '<a data-testid="experts-view-profile-mrodriguez" href="/experts/mrodriguez/"></a><a data-testid="experts-view-profile-mrodriguez" href="/experts/mrodriguez/"></a>',
    ],
)
def test_extract_maria_profile_href_with_invalid_anchor_rejects(html: str) -> None:
    """Reject absent, ambiguous or invalid navigation evidence.

    :param html: Invalid HTML sample. Example: an anchor without href.
    :return: None. Example: extraction raises AssertionError as required.
    :raises AssertionError: Extraction accepts an invalid sample.
    :raises NotImplementedError: Until the approved test slice is implemented.
    """
    raise NotImplementedError()
