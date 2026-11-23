from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/experts/", True),
        ("/experts/mrodriguez/", True),
        ("/experts-other/", False),
        ("/dashboard/", False),
        ("/playbooks/12/", False),
    ],
)
def test_is_experts_path_with_local_paths_returns_expected_match(
    path: str, expected: bool
) -> None:
    """Prove route-family matching.

    :param path: Candidate local path. Example: "/experts/".
    :param expected: Required match result. Example: True.
    :return: None. Example: None.
    :raises AssertionError: If the matcher selects the wrong section.
    """
    raise NotImplementedError()


@pytest.mark.parametrize("path", [None, 42, "", "//external/", "https://external/"])
def test_is_experts_path_with_invalid_input_raises_value_error(path: object) -> None:
    """Prove invalid inputs fail clearly.

    :param path: Invalid boundary value. Example: None.
    :return: None. Example: None.
    :raises AssertionError: If ValueError is not raised.
    """
    raise NotImplementedError()


def test_collaborate_items_with_experts_preserves_existing_links() -> None:
    """Prove one Experts entry and unchanged existing destinations.

    :return: None. Example: None.
    :raises AssertionError: If Experts is duplicated or Teams/PIPs change.
    """
    raise NotImplementedError()


@pytest.mark.parametrize("path", ["/experts/", "/experts/mrodriguez/"])
def test_primary_nav_section_with_experts_path_marks_experts_current(path: str) -> None:
    """Prove active-section integration uses the existing shell.

    :param path: Experts family path. Example: "/experts/".
    :return: None. Example: None.
    :raises AssertionError: If section, realm or chrome changes incorrectly.
    """
    raise NotImplementedError()
