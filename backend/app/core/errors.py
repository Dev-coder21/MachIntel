from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from backend.app.core.logging import logger


class MachIntelException(Exception):
    """Base exception for MachIntel application errors."""
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundException(MachIntelException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class AuthenticationException(MachIntelException):
    def __init__(self, message: str = "Invalid credentials", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="AUTHENTICATION_FAILED",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class PermissionDeniedException(MachIntelException):
    def __init__(self, message: str = "Permission denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="PERMISSION_DENIED",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class ConflictException(MachIntelException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="RESOURCE_CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class BadRequestException(MachIntelException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="BAD_REQUEST",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class ValidationException(MachIntelException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class CrossDomainEvidenceException(MachIntelException):
    def __init__(self, message: str = "Cross-domain evidence linkage is strictly prohibited.", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="CROSS_DOMAIN_EVIDENCE_PROHIBITED",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


async def machintel_exception_handler(request: Request, exc: MachIntelException) -> JSONResponse:
    from backend.app.core.middleware import get_request_id
    req_id = getattr(request.state, "request_id", None) or get_request_id()

    logger.warning(
        f"Handled application error: {exc.code} - {exc.message}",
        extra={"status_code": exc.status_code, "details": exc.details, "request_id": req_id},
    )
    return JSONResponse(
        status_code=exc.status_code,
        headers={"X-Request-ID": req_id} if req_id else {},
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "request_id": req_id,
            }
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    from backend.app.core.middleware import get_request_id
    req_id = getattr(request.state, "request_id", None) or get_request_id()

    logger.warning(f"Request validation error on {request.url.path}: {exc.errors()}", extra={"request_id": req_id})
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        headers={"X-Request-ID": req_id} if req_id else {},
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request payload failed schema validation",
                "details": {"validation_errors": jsonable_encoder(exc.errors())},
                "request_id": req_id,
            }
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    from backend.app.core.middleware import get_request_id
    req_id = getattr(request.state, "request_id", None) or get_request_id()

    return JSONResponse(
        status_code=exc.status_code,
        headers={"X-Request-ID": req_id} if req_id else {},
        content={
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail if isinstance(exc.detail, str) else "HTTP Exception",
                "details": exc.detail if isinstance(exc.detail, dict) else {},
                "request_id": req_id,
            }
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    from backend.app.core.middleware import get_request_id
    req_id = getattr(request.state, "request_id", None) or get_request_id()

    logger.error(f"Unhandled exception on {request.url.path}: {str(exc)}", exc_info=True, extra={"request_id": req_id})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        headers={"X-Request-ID": req_id} if req_id else {},
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected server error occurred",
                "details": {},
                "request_id": req_id,
            }
        },
    )
