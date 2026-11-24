"""Certification helpers for the Cedar public-profile privacy boundary."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from decimal import Decimal
from html import unescape
from http import HTTPStatus
from typing import cast
from urllib.parse import unquote

from django.http import HttpResponse
from django.urls import reverse
from rest_framework.authtoken.models import Token

from methodology.models import Playbook, ProcessImprovementProposal
from tests.support.experts_data import CedarDataset, load_cedar_baseline
from tests.support.experts_html import element_text, find_by_test_id

EXCLUDED_EVIDENCE_CASES = (
    ("public", "draft"),
    ("public", "active"),
    ("public", "disabled"),
    ("private", "released"),
)

_MARIA = "mrodriguez"
_PUBLIC_BOOK_ID = 6101
_PRIVATE_BOOK_TITLE = "Cedar Bid Pricing"
_PRIVATE_BOOK_BODY = "Cedar confidential pricing rationale for internal review."
_PRIVATE_PIP_TITLE = "Internal staffing notes for Cedar"
_PRIVATE_PIP_BODY = "Cedar confidential staffing rationale for internal review."
_ACCOUNT_HOOKS = (
    "profile-api-token",
    "profile-token-field",
    "profile-token-toggle",
    "profile-token-copy",
    "profile-token-regenerate-form",
    "profile-token-regenerate-password",
    "profile-token-regenerate-submit",
    "profile-edit-btn",
    "profile-email",
    "profile-pips-table",
    "profile-teams-section",
    "profile-playbooks-table",
)
_PERSON_FIELDS = {
    "subject_id": int,
    "username": str,
    "name": str,
    "initials": str,
    "total_karma": int,
    "formatted_karma": str,
    "primary_category": str,
    "summary": str,
    "numeric_fallback": str,
    "source_rows": tuple,
    "category_rows": tuple,
    "public_playbooks": tuple,
}
_BREAKDOWN_FIELDS = {"label": str, "points": str}
_BOOK_FIELDS = {"pk": int, "title": str, "version": str, "category": str}


def load_privacy_case() -> CedarDataset:
    """Load real Cedar records and distinct ineligible publication variants.

    :return: Cedar dataset with supplemental privacy data, e.g. Maria and book 6101.
    :raises AssertionError: If an expected private row cannot be enriched uniquely.
    """
    dataset = load_cedar_baseline()
    book_count = Playbook.objects.filter(**_private_book_filter(dataset)).update(
        description=_PRIVATE_BOOK_BODY
    )
    pip_count = ProcessImprovementProposal.objects.filter(
        **_private_pip_filter(dataset)
    ).update(summary=_PRIVATE_PIP_BODY)
    if book_count != 1 or pip_count != 1:
        raise AssertionError("Cedar private playbook or PIP fixture is missing.")
    Playbook.objects.bulk_create(
        [
            Playbook(
                **_variant_fields(dataset, visibility, status),
                category="design",
                version=Decimal("0.1" if status == "draft" else "1.0"),
                source="owned",
            )
            for visibility, status in EXCLUDED_EVIDENCE_CASES
        ]
    )
    return dataset


def assert_private_rows_exist(dataset: CedarDataset) -> None:
    """Verify the ORM holds each private field before checking for omission.

    :param dataset: Imported Cedar ORM dataset, e.g. Maria and playbook 6101.
    :return: None after all persisted fields reconcile with the fixture.
    :raises AssertionError: If the private book, PIP or token is missing or wrong.
    """
    if not Playbook.objects.filter(
        **_private_book_filter(dataset), description=_PRIVATE_BOOK_BODY
    ).exists():
        raise AssertionError("Cedar private playbook title or description is missing.")
    if not ProcessImprovementProposal.objects.filter(
        **_private_pip_filter(dataset), summary=_PRIVATE_PIP_BODY
    ).exists():
        raise AssertionError("Cedar private PIP title or summary is missing.")
    token = _maria_oracle(dataset)["private_token"]
    if (
        not token
        or not Token.objects.filter(
            user_id=dataset.user_ids[_MARIA], key=token
        ).exists()
    ):
        raise AssertionError("Cedar private token fixture is missing.")


def assert_public_projection(dto: Mapping[str, object], dataset: CedarDataset) -> None:
    """Validate the designated DTO's exact primitive schema and real evidence.

    :param dto: S17 public projection, e.g. response.context["person"].
    :param dataset: Real Cedar dataset, e.g. public playbook 6101.
    :return: None after schema, identity, prose and evidence validation.
    :raises AssertionError: If a field or value breaks the public boundary.
    """
    _assert_fields(dto, _PERSON_FIELDS, "person")
    oracle = _maria_oracle(dataset)
    for field, expected in (
        ("subject_id", dataset.user_ids[_MARIA]),
        ("username", _MARIA),
        ("name", oracle["name"]),
        ("summary", oracle["summary"]),
    ):
        if dto[field] != expected:
            raise AssertionError(f"Public projection changed the expected {field}.")
    for section in ("source_rows", "category_rows"):
        rows = cast(tuple[object, ...], dto[section])
        if not rows:
            raise AssertionError(f"Public projection omitted the {section} breakdown.")
        for row in rows:
            _assert_fields(row, _BREAKDOWN_FIELDS, section)
    books = cast(tuple[dict[str, object], ...], dto["public_playbooks"])
    _assert_public_books(books, dataset)
    _assert_private_markers_absent(json.dumps(dto, ensure_ascii=False), dataset, False)


def assert_public_response(
    response: HttpResponse,
    dataset: CedarDataset,
    authenticated: bool,
    *,
    excluded_evidence: tuple[str, str] | None = None,
) -> None:
    """Check the full raw document, authorized contact and public DTO.

    :param response: Real Django-client response, e.g. a successful Maria detail GET.
    :param dataset: Real Cedar dataset, e.g. Maria's public and private fixtures.
    :param authenticated: Contact eligibility, e.g. False for Bob.
    :param excluded_evidence: Optional visibility and status, e.g. ("public", "active").
    :return: None after signed-in or guest privacy assertions pass.
    :raises AssertionError: For a leak, wrong status or lost authorized content.
    """
    assert response.status_code == HTTPStatus.OK
    html = response.content.decode(response.charset)
    _assert_private_markers_absent(html, dataset, authenticated)
    person = response.context["person"]
    assert_public_projection(person, dataset)
    if excluded_evidence is not None:
        _assert_excluded_evidence(html, person, dataset, *excluded_evidence)
    _assert_public_html(html, dataset)
    if authenticated:
        action = find_by_test_id(html, f"experts-reach-out-{_MARIA}")
        expected_href = f"mailto:{dataset.users_by_username[_MARIA].email}"
        if action.name != "a" or dict(action.attributes).get("href") != expected_href:
            raise AssertionError("Elena's authorized Reach out link is missing.")


def _assert_excluded_evidence(
    html: str,
    person: Mapping[str, object],
    dataset: CedarDataset,
    visibility: str,
    status: str,
) -> None:
    """Check that a persisted ineligible book's name, body and link stay private.

    :param html: Full raw markup from the public response.
    :param person: Public projection with its schema already validated.
    :param dataset: Real Cedar dataset, e.g. Maria's persisted fixtures.
    :param visibility: Variant visibility, e.g. "private".
    :param status: Variant status, e.g. "released".
    :return: None; the book exists but is absent from Maria's public response.
    :raises AssertionError: If the variant is missing or its evidence leaks.
    """
    fields = _variant_fields(dataset, visibility, status)
    pk = Playbook.objects.filter(**fields).values_list("pk", flat=True).first()
    if pk is None:
        raise AssertionError(
            f"Cedar {visibility} {status} evidence fixture is missing."
        )
    document = _decoded_text(html)
    dto = _decoded_text(json.dumps(person, ensure_ascii=False))
    for marker, field in (
        (cast(str, fields["name"]), "title"),
        (cast(str, fields["description"]), "description"),
        (reverse("playbook_detail", args=[pk]), "link"),
    ):
        category = f"{visibility} {status} evidence {field}"
        _assert_omitted(document, marker, category)
        _assert_omitted(dto, marker, category)


def _maria_oracle(dataset: CedarDataset) -> Mapping[str, object]:
    """Read Maria's independent source row.

    :param dataset: Loaded Cedar baseline, e.g. CEDAR-RFP-01.
    :return: Oracle entry containing the stored public summary and private markers.
    :raises StopIteration: If the validated oracle lacks Maria's row.
    """
    people = cast(Sequence[Mapping[str, object]], dataset.oracle["people"])
    return next(person for person in people if person["username"] == _MARIA)


def _private_book_filter(dataset: CedarDataset) -> dict[str, str | int]:
    """Identify Maria's baseline private book, independent of its body.

    :param dataset: Cedar baseline with Maria's real user ID.
    :return: ORM filter for the expected author, title and private draft state.
    """
    return {
        "author_id": dataset.user_ids[_MARIA],
        "name": _PRIVATE_BOOK_TITLE,
        "visibility": "private",
        "status": "draft",
    }


def _private_pip_filter(dataset: CedarDataset) -> dict[str, str | int]:
    """Identify Maria's unpublished PIP on her public playbook.

    :param dataset: Cedar baseline with the author and playbook 6101.
    :return: ORM filter for the expected draft PIP, independent of its body.
    """
    return {
        "created_by_id": dataset.user_ids[_MARIA],
        "playbook_id": _PUBLIC_BOOK_ID,
        "title": _PRIVATE_PIP_TITLE,
        "status": ProcessImprovementProposal.STATUS_DRAFT,
    }


def _variant_fields(
    dataset: CedarDataset, visibility: str, status: str
) -> dict[str, str | int]:
    """Declare unique title and body markers for a real publication variant.

    :param dataset: Cedar baseline with Maria's user ID.
    :param visibility: Publication visibility, e.g. "public".
    :param status: Publication status, e.g. "disabled".
    :return: Fields used to persist and then verify the variant in the database.
    """
    return {
        "author_id": dataset.user_ids[_MARIA],
        "name": f"Cedar S20 {visibility} {status} evidence",
        "description": f"S20 {visibility} {status} rationale for internal review.",
        "visibility": visibility,
        "status": status,
    }


def _assert_fields(value: object, fields: Mapping[str, type], category: str) -> None:
    """Reject extra or missing fields and non-primitive types without echoing values.

    :param value: Candidate DTO or nested row, e.g. a source breakdown row.
    :param fields: Exact approved names and types, e.g. {"label": str, "points": str}.
    :param category: Safe schema label, e.g. "source_rows".
    :return: None after validating the mapping.
    :raises AssertionError: For different keys, a model object or another wrong type.
    """
    if type(value) is not dict or value.keys() != fields.keys():
        raise AssertionError(f"Public {category} schema differs from its allowlist.")
    for field, field_type in fields.items():
        if type(value[field]) is not field_type:
            raise AssertionError(f"Public {category}.{field} has an invalid type.")


def _assert_public_books(
    books: tuple[dict[str, object], ...], dataset: CedarDataset
) -> None:
    """Resolve every evidence PK and reconcile metadata with eligible Cedar rows.

    :param books: Projected evidence tuple, e.g. a single book 6101 row.
    :param dataset: Cedar baseline with Maria as evidence author.
    :return: None after verifying the exact public evidence.
    :raises AssertionError: If eligibility, public metadata or evidence IDs differ.
    """
    for book in books:
        _assert_fields(book, _BOOK_FIELDS, "playbook evidence")
        row = Playbook.objects.filter(
            pk=book["pk"],
            author_id=dataset.user_ids[_MARIA],
            visibility="public",
            status="released",
        ).first()
        if row is None:
            raise AssertionError(
                "Projected evidence does not resolve to a public release."
            )
        if (book["title"], book["version"], book["category"]) != (
            row.name,
            str(row.version),
            row.get_category_display(),
        ):
            raise AssertionError("Projected evidence changed public metadata.")
    if tuple(book["pk"] for book in books) != (_PUBLIC_BOOK_ID,):
        raise AssertionError("Public evidence does not retain exactly Cedar book 6101.")


def _assert_public_html(html: str, dataset: CedarDataset) -> None:
    """Assert Maria's visible identity, complete summary and actual evidence link.

    :param html: Actual response document from Django.
    :param dataset: Cedar baseline with independent summary oracle and public book.
    :return: None when all required public content is present.
    :raises AssertionError: If the public content disappears or is truncated.
    """
    oracle = _maria_oracle(dataset)
    if element_text(find_by_test_id(html, "expert-name")) != oracle["name"]:
        raise AssertionError("Rendered public identity does not match Maria.")
    summary = find_by_test_id(html, "expert-contribution-summary")
    if element_text(summary) != oracle["summary"]:
        raise AssertionError("Rendered public summary is missing or incomplete.")
    evidence = find_by_test_id(html, "expert-public-playbooks")
    if dataset.playbooks_by_pk[_PUBLIC_BOOK_ID].name not in element_text(evidence):
        raise AssertionError("Rendered public evidence title is missing.")
    link = find_by_test_id(str(evidence), f"expert-playbook-{_PUBLIC_BOOK_ID}")
    if link.name != "a" or dict(link.attributes).get("href") != reverse(
        "playbook_detail", args=[_PUBLIC_BOOK_ID]
    ):
        raise AssertionError("Public evidence link does not lead to Cedar book 6101.")


def _assert_private_markers_absent(
    text: str, dataset: CedarDataset, allow_contact: bool
) -> None:
    """Scan the entire document or allowlisted DTO representation safely.

    :param text: Raw HTML or JSON of the designated public DTO.
    :param dataset: Cedar baseline with persisted privacy markers.
    :param allow_contact: Whether this surface permits contact, e.g. Elena's HTML.
    :return: None when prohibited values and account controls are absent.
    :raises AssertionError: If a private value or control is present.
    """
    document = _decoded_text(text)
    markers = {
        "private playbook title": _PRIVATE_BOOK_TITLE,
        "private playbook description": _PRIVATE_BOOK_BODY,
        "private PIP title": _PRIVATE_PIP_TITLE,
        "private PIP summary": _PRIVATE_PIP_BODY,
        "private token": cast(str, _maria_oracle(dataset)["private_token"]),
    }
    for category, marker in markers.items():
        _assert_omitted(document, marker, category)
    for hook in _ACCOUNT_HOOKS:
        _assert_omitted(document, hook, "account control")
    if not allow_contact:
        _assert_omitted(document, "mailto:", "contact link")
        for user in dataset.users_by_username.values():
            if user.email:
                _assert_omitted(document, user.email, "account email")


def _decoded_text(text: str) -> str:
    """Decode HTML entities and URL escapes while retaining hidden content.

    :param text: Raw document with possible encoded attributes or links.
    :return: Case-insensitive comparable text retaining the full document.
    """
    return unescape(unquote(text)).casefold()


def _assert_omitted(document: str, marker: str, category: str) -> None:
    """Detect private text without exposing the marker or containing document.

    :param document: Decoded document, including hidden attributes and scripts.
    :param marker: Expected-to-be-absent text, e.g. the fixture token.
    :param category: Safe description, e.g. "private token".
    :return: None when the marker is absent.
    :raises AssertionError: If the marker appears in the document.
    """
    if marker.casefold() in document:
        raise AssertionError(f"Public profile exposed {category}.")
