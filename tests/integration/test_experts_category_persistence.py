from __future__ import annotations

"""Real Django-client proofs for EXPERTS-LIST-02."""
import pytest
from django.test import Client
from pytest import LogCaptureFixture

pytestmark = pytest.mark.django_db


def test_category_links_with_design_query_show_five_links_and_one_current(
    client: Client,
) -> None:
    """Prove labels, hrefs, hooks and unique Design current state.

    :param client: Real Django client. Example: authenticated Cedar Elena.
    :return: None. Example: five expected anchors asserted.
    :raises AssertionError: If response, category order, hrefs or ARIA differ.
    :raises NotImplementedError: Until BPE adds the acceptance assertions.
    """
    raise NotImplementedError


def test_category_selection_with_repeated_design_get_remains_current(
    client: Client,
) -> None:
    """Prove the Design query reconstructs the same state on another request.

    :param client: Real Django client. Example: authenticated Cedar Elena.
    :return: None. Example: two equal category snapshots asserted.
    :raises AssertionError: If repeat GET changes URL or current category.
    :raises NotImplementedError: Until BPE adds the acceptance assertions.
    """
    raise NotImplementedError


def test_category_selection_log_story_happy(
    client: Client, caplog: LogCaptureFixture
) -> None:
    """Prove the shared list story independently for two Design requests.

    :param client: Real Django client. Example: authenticated Cedar Elena.
    :param caplog: Captured pytest records. Example: INFO experts_list beats.
    :return: None. Example: entry and exit asserted for both requests.
    :raises AssertionError: If any declared log beat or fragment is absent.
    :raises NotImplementedError: Until BPE adds the log-story assertions.
    """
    raise NotImplementedError
