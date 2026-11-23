from __future__ import annotations

"""Server-only assertions for guest public-detail evidence."""
from django.http import HttpResponse
from django.test import Client
from tests.support.experts_data import CedarDataset


def assert_guest_detail_evidence_readable(
    client: Client, response: HttpResponse, dataset: CedarDataset
) -> None:
    """Assert full public prose and anonymously readable released evidence.

    :param client: Anonymous real Django client. Example: Client().
    :param response: Detail HTTP response. Example: GET /experts/mrodriguez/.
    :param dataset: Real Cedar objects and oracle. Example: load_cedar_baseline().
    :return: None. Example: None after valid summary and playbook response.
    :raises AssertionError: If response, prose, evidence or guest access differs.
    """
    raise NotImplementedError()
