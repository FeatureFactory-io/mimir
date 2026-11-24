"""The request boundary publishes one safe ID and clears its log context."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from uuid import UUID

import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory

from mimir.logging_filters import RequestIDFilter
from mimir.middleware import RequestIDMiddleware
from mimir.request_local import clear_current_request, get_current_request
from tests.support.experts_logs import capture_experts_logs

_RUN = "edge.2026-11_24.request"
_CREDENTIAL = "trace" + "1" * 48
_MIDDLEWARE_LOGGER = "mimir.middleware"


@pytest.fixture
def request_logs(
    caplog: pytest.LogCaptureFixture,
) -> Iterator[pytest.LogCaptureFixture]:
    """Capture real middleware records after the actual request ID filter runs."""
    request_filter = RequestIDFilter()
    caplog.handler.addFilter(request_filter)
    try:
        with capture_experts_logs(caplog, (_MIDDLEWARE_LOGGER,)):
            yield caplog
    finally:
        caplog.handler.removeFilter(request_filter)
        clear_current_request()


@pytest.mark.parametrize(
    "identifier",
    [
        None,
        "",
        123,
        "a" * 101,
        "-no-leading-punctuation",
        "line\nbreak",
        " padded",
        "address@example.invalid",
        "eyJsynthetic.payload.signature",
        "req-xoxb-syntheticcredential",
        "client_secret:synthetic",
        "a1" * 20,
        _CREDENTIAL,
    ],
)
def test_middleware_with_rejected_or_absent_header_propagates_one_uuid(
    identifier: object, request_logs: pytest.LogCaptureFixture
) -> None:
    """Use one UUID for the view, request logs, and response."""
    options = {} if identifier is None else {"HTTP_X_REQUEST_ID": identifier}
    request = RequestFactory().get("/privacy-boundary/", **options)
    request.user = AnonymousUser()

    def view(active: HttpRequest) -> HttpResponse:
        assert get_current_request() is active
        return HttpResponse()

    response = RequestIDMiddleware(view)(request)
    published = response["X-Request-ID"]
    assert str(UUID(published, version=4)) == published
    assert request.request_id == published
    assert [record.request_id for record in request_logs.records] == [
        published,
        published,
    ]
    if identifier:
        assert str(identifier) not in " ".join(
            record.getMessage() for record in request_logs.records
        )
    assert get_current_request() is None


@pytest.mark.parametrize("identifier", [_RUN, "r", "r" * 100])
def test_middleware_with_safe_header_preserves_id_and_uses_server_actor_id(
    identifier: str, request_logs: pytest.LogCaptureFixture
) -> None:
    """Keep safe upstream IDs and report the actor PK without username."""
    request = RequestFactory().get("/privacy-boundary/", HTTP_X_REQUEST_ID=identifier)
    request.user = SimpleNamespace(pk=17, username="actor@example.invalid")

    response = RequestIDMiddleware(lambda request: HttpResponse())(request)

    assert response["X-Request-ID"] == request.request_id == identifier
    assert [record.request_id for record in request_logs.records] == [
        identifier,
        identifier,
    ]
    assert "actor_id=17" in request_logs.records[0].getMessage()
    assert "actor@example.invalid" not in request_logs.text


def test_middleware_with_view_exception_preserves_safe_id_and_clears_context(
    request_logs: pytest.LogCaptureFixture,
) -> None:
    """Correlate the error and resulting 500 without logging exception text."""
    request = RequestFactory().get("/privacy-boundary/", HTTP_X_REQUEST_ID=_CREDENTIAL)
    request.user = AnonymousUser()
    middleware = RequestIDMiddleware(lambda request: HttpResponse())
    middleware.process_request(request)
    assert middleware.process_exception(request, ValueError(_CREDENTIAL)) is None
    assert get_current_request() is None
    response = middleware.process_response(request, HttpResponse(status=500))
    assert [record.request_id for record in request_logs.records] == [
        response["X-Request-ID"]
    ] * 3
    assert "[REQUEST_ERROR]" in request_logs.text
    assert _CREDENTIAL not in request_logs.text
    assert get_current_request() is None


def test_filter_with_background_thread_or_completed_request_uses_no_request(
    request_logs: pytest.LogCaptureFixture,
) -> None:
    """Keep thread-local correlation isolated and clear it after the request."""
    logger = logging.getLogger(_MIDDLEWARE_LOGGER)

    def view(request: HttpRequest) -> HttpResponse:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(logger.info, "background worker").result(timeout=5)
        logger.info("request view")
        return HttpResponse()

    request = RequestFactory().get("/privacy-boundary/", HTTP_X_REQUEST_ID=_RUN)
    request.user = AnonymousUser()
    RequestIDMiddleware(view)(request)
    logger.info("after request")
    assert [record.request_id for record in request_logs.records] == [
        _RUN,
        "NO_REQUEST",
        _RUN,
        _RUN,
        "NO_REQUEST",
    ]
