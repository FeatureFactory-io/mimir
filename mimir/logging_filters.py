"""Logging filters that add request context to each record."""

import logging

from mimir.request_local import get_current_request, normalize_request_id

_NO_REQUEST = "NO_REQUEST"


class RequestIDFilter(logging.Filter):
    """Attach the middleware correlation ID or the background placeholder."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add safe context without generating a second request ID.

        :param record: Record being formatted. Example: a request-start record.
        :return: True to pass the record. Example: background logs also pass.
        """
        request = get_current_request()
        identifier = normalize_request_id(getattr(request, "request_id", None))
        record.request_id = identifier or _NO_REQUEST
        return True
