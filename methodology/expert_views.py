"""Public Experts delivery using the existing Django shell."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from urllib.parse import urlencode
from uuid import uuid4

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_safe

from methodology.services.expert_card_presentation import (
    ExpertCardPresentation,
)
from methodology.services.expert_contact_context import build_expert_contact_context
from methodology.services.expert_text import (
    CATEGORY_LABELS,
    category_label,
    display_initials,
    format_karma,
    format_numeric_fallback,
)
from methodology.services.experts_service import (
    _CORRELATION_ID,
    ExpertProjection,
    ExpertsService,
    PublicExpertDetail,
)

logger = logging.getLogger(__name__)
_DEFAULT_CATEGORY = "development"
_LIST_LOG = "experts_list"
_DETAIL_LOG = "expert_detail"
_DETAIL_TEMPLATE = "experts/detail.html"


@require_safe
def experts_list(request: HttpRequest) -> HttpResponse:
    """Render real ranked contributors for the requested category.

    :param request: Actual request. Example: GET /experts/?category=design.
    :return: Production list HTML. Example: HTTP 200 with five Design cards.
    :raises ValueError: For invalid internal context construction.
    """
    correlation_id = _request_correlation_id(request)
    request.request_id = correlation_id
    category = _selected_category(request)
    logger.info(
        "%s | entry | category=%s actor=%s correlation_id=%s",
        _LIST_LOG,
        category,
        request.user.pk if request.user.is_authenticated else "guest",
        correlation_id,
    )
    context = _ranked_people_context(request, category, correlation_id)
    response = render(request, "experts/list.html", context)
    logger.info(
        "%s | exit | category=%s status=%s count=%s correlation_id=%s",
        _LIST_LOG,
        category,
        response.status_code,
        context["count"],
        correlation_id,
    )
    return response


def _selected_category(request: HttpRequest) -> str:
    """Resolve a recognized query slug, defaulting to Development.

    :param request: Actual HTTP request. Example: GET /experts/?category=design.
    :return: Canonical slug. Example: "design".
    :raises ValueError: For an invalid request object.
    """
    if not isinstance(request, HttpRequest):
        raise ValueError("An Experts HTTP request is required.")  # noqa: TRY004
    category = request.GET.get("category")
    if category in CATEGORY_LABELS:
        return category
    if category is not None:
        logger.info(
            "_selected_category | branch | reason=invalid_category category=%s correlation_id=%s",
            _DEFAULT_CATEGORY,
            _request_correlation_id(request),
        )
    return _DEFAULT_CATEGORY


def _category_links(selected_category: str) -> tuple[dict[str, object], ...]:
    """Build existing category labels, canonical URLs and selected-state flags.

    :param selected_category: Recognized category. Example: "design".
    :return: Five ordered links. Example: ({"slug": "product", ...}, ...).
    :raises ValueError: For an unsupported category.
    """
    category_label(selected_category)
    list_path = reverse("experts_list")
    return tuple(
        {
            "slug": slug,
            "label": label,
            "url": f"{list_path}?{urlencode({'category': slug})}",
            "current": slug == selected_category,
        }
        for slug, label in CATEGORY_LABELS.items()
    )


def _request_correlation_id(request: HttpRequest) -> str:
    """Use a safe bounded X-Request-ID or generate a request correlation ID.

    :param request: Actual request. Example: a request with X-Request-ID.
    :return: Safe nonblank identity. Example: "cedar-s03".
    :raises ValueError: For an invalid request object.
    """
    if not isinstance(request, HttpRequest):
        raise ValueError("An Experts HTTP request is required.")  # noqa: TRY004
    request_id = getattr(request, "request_id", None) or request.headers.get(
        "X-Request-ID"
    )
    if isinstance(request_id, str) and _CORRELATION_ID.fullmatch(request_id):
        return request_id
    return str(uuid4())


def _ranked_people_context(
    request: HttpRequest, category: str, correlation_id: str
) -> dict[str, object]:
    """Build ordered numeric list context and request-local contact presentation.

    :param request: Actual request/session. Example: Elena with category=design.
    :param category: Resolved canonical slug. Example: "design".
    :param correlation_id: Request identity. Example: "cedar-s03".
    :return: Numeric/public identity context. Example: {"people": ()}.
    :raises ValueError: For invalid service inputs.
    """
    projections = ExpertsService().list_leaders(category, correlation_id=correlation_id)
    label = category_label(category)
    people = tuple(
        {
            "username": person.username,
            "name": person.display_name,
            "initials": display_initials(person.display_name),
            "total_points": person.total_points,
            "category_subtotal": dict(person.category_points)[category],
            "formatted_karma": format_karma(person.total_points),
            "primary_category": label,
            "hint": format_numeric_fallback(
                person.released_public_playbook_count, person.successful_gui_copy_count
            ),
        }
        for person in projections
    )
    return {
        "nav_section": "experts",
        "selected_category": category,
        "selected_category_label": label,
        "categories": _category_links(category),
        "count": len(people),
        "people": tuple(_with_expert_contacts(request, people)),
    }


@require_safe
def expert_detail(request: HttpRequest, username: str) -> HttpResponse:
    """Render a public expert using real projections and production chrome.

    :param request: Django GET. Example: anonymous or Elena's authenticated request.
    :param username: Route account name. Example: "mrodriguez".
    :return: Public HTML or a generic 404. Example: status 200, experts/detail.html.
    """
    correlation_id = _detail_correlation_id(request)
    request.request_id = correlation_id
    logger.info(
        "%s | entry | operation=public_expert_detail authenticated=%s correlation_id=%s",
        _DETAIL_LOG,
        request.user.is_authenticated,
        correlation_id,
    )
    try:
        detail = ExpertsService.public_detail(username, correlation_id=correlation_id)
    except (LookupError, ValueError):
        logger.info(
            "%s | branch | reason=expert_unavailable correlation_id=%s",
            _DETAIL_LOG,
            correlation_id,
        )
        response = render(
            request, _DETAIL_TEMPLATE, {"nav_section": "experts"}, status=404
        )
    else:
        response = render(request, _DETAIL_TEMPLATE, _detail_context(request, detail))
    logger.info(
        "%s | exit | status=%s template=%s correlation_id=%s",
        _DETAIL_LOG,
        response.status_code,
        _DETAIL_TEMPLATE,
        correlation_id,
    )
    return response


def _detail_correlation_id(request: HttpRequest) -> str:
    """Reuse a safe bounded request ID or generate one.

    :param request: Incoming request. Example: X-Request-ID "cedar-s17".
    :return: Safe correlation string. Example: "cedar-s17".
    :raises ValueError: For an unusable request object.
    """
    return _request_correlation_id(request)


def _detail_context(
    request: HttpRequest, detail: PublicExpertDetail
) -> dict[str, object]:
    """Build allowlisted template context and category-preserving breadcrumb.

    :param request: Actual request/session. Example: Elena with category=design.
    :param detail: Public projection. Example: Maria's detail payload.
    :return: Template context. Example: {"person": detail, "nav_section": "experts", ...}.
    :raises ValueError: For malformed projection values.
    """
    category = request.GET.get("category")
    if category not in CATEGORY_LABELS:
        category = next(
            (
                slug
                for slug, label in CATEGORY_LABELS.items()
                if label == detail["primary_category"]
            ),
            None,
        )
    if category is None:
        raise ValueError("Public expert breadcrumb requires a recognized category.")
    [contact_person] = _with_expert_contacts(request, [detail])
    return {
        "person": detail,
        "contact_person": contact_person,
        "nav_section": "experts",
        "back_url": f"{reverse('experts_list')}?{urlencode({'category': category})}",
    }


def _with_expert_contacts(
    request: HttpRequest, people: Sequence[Mapping[str, object]]
) -> list[dict[str, object]]:
    """Attach contact presentation to copies of eligible public projections.

    The list passes its projected people; detail passes a one-item sequence.
    Both use the same request-scoped builder. Original payloads stay unchanged.

    :param request: Actual Django request. Example: Elena's authenticated GET.
    :param people: Eligible public projections. Example: [{"username": "mrodriguez"}].
    :return: Copied render dictionaries with contact. Example: [Maria render row].
    :raises TypeError: If a projection or username has the wrong type.
    :raises ValueError: If a projection omits its validated public username.
    """
    usernames: list[str] = []
    for person in people:
        if not isinstance(person, Mapping):
            raise TypeError("Expert presentation requires a public mapping.")
        if "username" not in person:
            raise ValueError("Expert presentation requires a username.")
        username = person["username"]
        if not isinstance(username, str):
            raise TypeError("Expert presentation usernames must be strings.")
        usernames.append(username)
    contacts = build_expert_contact_context(request, usernames)
    return [
        dict(person, contact=contacts[username])
        for person, username in zip(people, usernames, strict=True)
    ]


def _stored_expert_card_summaries(user_ids: Sequence[int]) -> Mapping[int, str | None]:
    """Read only stored public contribution paragraphs for the selected users.

    :param user_ids: Ranked subject IDs. Example: (12, 13).
    :return: User-ID-to-summary mapping. Example: {13: "Maria maintains…"}.
    :raises ValueError: If IDs are not positive integers.
    """
    raise NotImplementedError()


def _build_expert_card_presentations(
    projections: Sequence[ExpertProjection],
    summaries_by_user_id: Mapping[int, str | None],
    *,
    correlation_id: str,
) -> tuple[ExpertCardPresentation, ...]:
    """Preserve S03 ordering while presenting each public card.

    :param projections: Ranked allowlisted projections. Example: Sofia then Maria.
    :param summaries_by_user_id: Stored public prose. Example: {13: "Maria maintains…"}.
    :param correlation_id: Request identifier. Example: "cedar-s04".
    :return: Presentations in unchanged order. Example: (sofia_card, maria_card).
    :raises ValueError: If an input projection violates the public contract.
    """
    raise NotImplementedError()
