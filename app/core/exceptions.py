from typing import Optional
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class MarketForgeException(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        detail: Optional[str] = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.detail = detail or message
        super().__init__(self.message)


class NotFoundError(MarketForgeException):
    def __init__(self, resource: str, identifier: str) -> None:
        super().__init__(
            message=f"{resource} not found",
            status_code=404,
            detail=f"{resource} with identifier '{identifier}' was not found",
        )


class UnauthorizedError(MarketForgeException):
    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(
            message=message,
            status_code=401,
            detail=message,
        )


class ForbiddenError(MarketForgeException):
    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(
            message=message,
            status_code=403,
            detail=message,
        )


class ValidationError(MarketForgeException):
    def __init__(self, message: str) -> None:
        super().__init__(
            message="Validation error",
            status_code=422,
            detail=message,
        )


class ConflictError(MarketForgeException):
    def __init__(self, message: str) -> None:
        super().__init__(
            message="Conflict error",
            status_code=409,
            detail=message,
        )


async def marketforge_exception_handler(
    request: Request,
    exc: MarketForgeException,
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "detail": exc.detail,
        },
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if hasattr(exc, "__str__") else "Unknown error",
        },
    )