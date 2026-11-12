"""Request ID middleware for correlating API requests."""

import uuid
import threading

_thread_locals = threading.local()


def get_current_request_id():
    """Retrieve current request correlation ID from thread-local storage."""
    return getattr(_thread_locals, "request_id", None)


class CorrelationIdMiddleware:
    """Keep the request ID available to the request and response."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.request_id = request_id
        _thread_locals.request_id = request_id

        response = self.get_response(request)

        response["X-Request-ID"] = request_id
        return response
