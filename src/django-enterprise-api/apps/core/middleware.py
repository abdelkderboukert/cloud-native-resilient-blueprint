"""
Cloud-Native Request Correlation and Tracing Middleware
"""

import uuid
import threading

_thread_locals = threading.local()


def get_current_request_id():
    """Retrieve current request correlation ID from thread-local storage."""
    return getattr(_thread_locals, "request_id", None)


class CorrelationIdMiddleware:
    """
    Middleware that captures or generates an X-Request-ID / correlation ID
    and propagates it into HTTP response headers and thread context.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Extract request ID from incoming header or generate new UUID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.request_id = request_id
        _thread_locals.request_id = request_id

        response = self.get_response(request)

        # Echo request ID in downstream response headers
        response["X-Request-ID"] = request_id
        return response
