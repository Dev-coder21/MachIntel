import contextvars
import re
import uuid
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Context variable for storing request correlation ID across async task execution
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")

REQUEST_ID_REGEX = re.compile(r"^[A-Za-z0-9_\-]{8,64}$")


def get_request_id() -> str:
    """Retrieve the current request correlation ID from context."""
    return request_id_ctx.get()


class SecurityAndCorrelationMiddleware(BaseHTTPMiddleware):
    """
    Middleware providing:
    1. Request correlation ID extraction/generation (X-Request-ID)
    2. HTTP defense-in-depth security headers (OWASP recommended)
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Extract or generate correlation ID
        incoming_id = request.headers.get("X-Request-ID")
        if incoming_id and REQUEST_ID_REGEX.match(incoming_id):
            req_id = incoming_id
        else:
            req_id = str(uuid.uuid4())

        token = request_id_ctx.set(req_id)
        # Also attach to request.state for convenient handler access
        request.state.request_id = req_id

        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)

        # Attach correlation header
        response.headers["X-Request-ID"] = req_id

        # Defense-in-depth security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"

        # Safe default CSP allowing API Docs and local Next.js client
        if "Content-Security-Policy" not in response.headers:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: blob: https://fastapi.tiangolo.com; "
                "font-src 'self' data:; "
                "connect-src 'self' http://localhost:* http://127.0.0.1:* ws://localhost:* ws://127.0.0.1:*;"
            )

        return response
