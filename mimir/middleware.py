"""Normalize client-provided request IDs before publishing request context."""

import logging
import uuid

from django.http import HttpRequest, HttpResponseBase
from django.utils.deprecation import MiddlewareMixin

from mimir.request_local import (
    clear_current_request,
    normalize_request_id,
    set_current_request,
)

logger = logging.getLogger(__name__)

_REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(MiddlewareMixin):
    """Correlate a request, log records, and its response with a safe ID."""

    def process_request(self, request: HttpRequest) -> None:
        """Publish a safe upstream ID or generate a UUID before logging.

        :param request: Incoming request. Example: a POST with X-Request-ID.
        :return: None to continue processing.
        """
        upstream_id = normalize_request_id(request.headers.get(_REQUEST_ID_HEADER))
        request.request_id = upstream_id or str(uuid.uuid4())
        actor_id = getattr(getattr(request, "user", None), "pk", None)
        set_current_request(request)
        logger.info(
            "[REQUEST_START] %s %s actor_id=%s",
            request.method,
            request.path,
            actor_id if actor_id is not None else "anonymous",
        )

    def process_response(
        self, request: HttpRequest, response: HttpResponseBase
    ) -> HttpResponseBase:
        """Echo the safe ID and clear request-local context.

        :param request: Completed request. Example: a PIP submission POST.
        :param response: Response to the request. Example: a 302 redirect.
        :return: Response with X-Request-ID when request tracking started.
        """
        try:
            if hasattr(request, "request_id"):
                # Exception handling has already released its thread-local context.
                set_current_request(request)
                response[_REQUEST_ID_HEADER] = request.request_id
                logger.info(
                    "[REQUEST_END] %s %s - Status: %s",
                    request.method,
                    request.path,
                    response.status_code,
                )
            return response
        finally:
            clear_current_request()

    def process_exception(self, request: HttpRequest, exception: Exception) -> None:
        """Log the failure class and release thread-local context.

        :param request: Failed request. Example: a view that raised ValueError.
        :param exception: Raised error, whose message may contain private data.
        :return: None to leave error handling to Django.
        """
        try:
            if hasattr(request, "request_id"):
                logger.error(
                    "[REQUEST_ERROR] %s %s - Exception: %s",
                    request.method,
                    request.path,
                    type(exception).__name__,
                )
        finally:
            clear_current_request()
