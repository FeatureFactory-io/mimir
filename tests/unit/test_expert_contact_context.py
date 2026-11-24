"""Exercise the S14 request boundary against real Django accounts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from types import SimpleNamespace

import pytest
from django.db import connection
from django.http import HttpRequest
from django.test import Client
from django.test.utils import CaptureQueriesContext

from methodology.expert_views import _with_expert_contacts
from methodology.services.expert_contact_context import build_expert_contact_context
from methodology.services.experts_service import ExpertsService
from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset

pytestmark = pytest.mark.django_db

_MARIA = "mrodriguez"
_MARIA_PATH = f"/experts/{_MARIA}/"
_MARIA_MAILTO = "mailto:maria.rodriguez@example.com"


def test_build_expert_contact_context_with_authenticated_request_returns_exact_mailto(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Prove the exact immutable contact, one lookup and clean public payloads.

    :param client: Real Django client. Example: logged-in Cedar Elena.
    :param cedar_dataset: Fixture with real account rows. Example: Maria.
    :return: None. Example: Maria's exact destination is attached to a copy.
    :raises AssertionError: For wrong href, mutation or public-payload pollution.
    """
    assert client.login(username="esvensson", password=CEDAR_PASSWORD)
    request = client.get("/experts/").wsgi_request
    public = ExpertsService.public_detail(_MARIA, correlation_id="cedar-s14")
    projection = ExpertsService().project_user(
        cedar_dataset.users_by_username[_MARIA].pk
    )
    with CaptureQueriesContext(connection) as queries:
        contacts = build_expert_contact_context(
            request, [_MARIA, _MARIA, "missing-expert"]
        )

    assert len(queries) == 1
    assert tuple(contacts) == (_MARIA, "missing-expert")
    contact = contacts[_MARIA]
    assert (contact.username, contact.state, contact.href) == (
        _MARIA,
        "available",
        _MARIA_MAILTO,
    )
    assert contacts["missing-expert"].state == "unavailable"
    assert contacts["missing-expert"].href is None
    with pytest.raises(TypeError):
        contacts[_MARIA] = contacts["missing-expert"]
    with pytest.raises(FrozenInstanceError):
        contact.href = None

    [presentation] = _with_expert_contacts(request, [public])
    assert presentation == {**public, "contact": contact}
    assert "contact" not in public and "email" not in public
    assert not hasattr(projection, "contact") and not hasattr(projection, "email")


def test_build_expert_contact_context_with_guest_request_does_not_query_email(
    client: Client, cedar_dataset: CedarDataset
) -> None:
    """Prove guest short-circuit before any target-email query.

    :param client: Real anonymous client. Example: Bob with guest=0.
    :param cedar_dataset: Fixture with real account rows. Example: Maria.
    :return: None. Example: zero lookup queries and disabled contact verified.
    :raises AssertionError: For a lookup, leaked href or bypassed restriction.
    """
    request = client.get(_MARIA_PATH, {"guest": "0", "authenticated": "1"}).wsgi_request
    assert request.user.is_anonymous
    with CaptureQueriesContext(connection) as queries:
        contacts = build_expert_contact_context(request, [_MARIA])

    assert len(queries) == 0
    contact = contacts[_MARIA]
    assert contact.state == "authentication_required"
    assert contact.href is None
    assert contact.explanation == "You need to be logged in to reach out to the expert"
    with pytest.raises(TypeError):
        contacts[_MARIA] = contact
    with pytest.raises(FrozenInstanceError):
        contact.explanation = ""


@pytest.mark.parametrize(
    ("email", "href"),
    [
        ("", None),
        ("   ", None),
        ("no-domain", None),
        ("maria@example.com,other@example.com", None),
        ("maria@example.com\r\nBcc: other@example.com", None),
        ("maria@example.com\n", None),
        ("maria%0D%0A@example.com", None),
        ("maria@example.com?bcc=other@example.com", None),
        ("maria+cedar&design@example.com", "mailto:maria%2Bcedar%26design@example.com"),
    ],
)
def test_build_expert_contact_context_with_unusable_email_disables_handoff(
    client: Client, cedar_dataset: CedarDataset, email: str, href: str | None
) -> None:
    """Verify real stored unsafe addresses and reserved characters.

    :param client: Real Django client. Example: logged-in Cedar Elena.
    :param cedar_dataset: Fixture with real account rows. Example: Maria.
    :param email: Stored account input. Example: CR/LF header injection.
    :param href: Expected handoff. Example: None for unsafe input.
    :return: None. Example: an unusable address produces no href.
    :raises AssertionError: For unsafe destinations or fabricated contact success.
    """
    maria = cedar_dataset.users_by_username[_MARIA]
    maria.email = email
    maria.save(update_fields=["email"])
    assert client.login(username="esvensson", password=CEDAR_PASSWORD)
    request = client.get(_MARIA_PATH).wsgi_request

    contact = build_expert_contact_context(request, [_MARIA])[_MARIA]

    assert contact.href == href
    if href is None:
        assert contact.state == "unavailable"
        assert contact.explanation == "Contact information is unavailable"
    else:
        assert contact.state == "available"


def test_build_expert_contact_context_with_invalid_boundary_input_raises(
    client: Client,
) -> None:
    """Prove typed boundary validation and the valid empty-collection case.

    :param client: Real anonymous client. Example: middleware-backed list GET.
    :return: None. Example: invalid inputs reject and empty input returns empty.
    :raises AssertionError: For accepted invalid input or wrong exception type.
    """
    request = client.get("/experts/").wsgi_request
    with pytest.raises(TypeError, match="HttpRequest"):
        build_expert_contact_context({}, [_MARIA])
    with pytest.raises(ValueError, match="authentication context"):
        build_expert_contact_context(HttpRequest(), [_MARIA])
    fabricated = HttpRequest()
    fabricated.session = request.session
    fabricated.user = SimpleNamespace(is_authenticated=True, pk=123)
    with pytest.raises(ValueError, match="authentication context"):
        build_expert_contact_context(fabricated, [_MARIA])
    for invalid_type in (_MARIA, b"mrodriguez", {_MARIA}, [123]):
        with pytest.raises(TypeError, match="username"):
            build_expert_contact_context(request, invalid_type)
    for invalid_username in ("", " ", "with space", "null\x00byte", "a" * 151):
        with pytest.raises(ValueError, match="username"):
            build_expert_contact_context(request, [invalid_username])
    assert build_expert_contact_context(request, []) == {}
