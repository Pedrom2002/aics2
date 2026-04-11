from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ProblemDetail(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str | None = None


# Custom exception classes
class NotFoundError(HTTPException):
    def __init__(self, resource: str, identifier: str | None = None):
        detail = (
            f"{resource} not found" if not identifier else f"{resource} '{identifier}' not found"
        )
        super().__init__(status_code=404, detail=detail)


class ConflictError(HTTPException):
    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(status_code=409, detail=detail)


class ForbiddenError(HTTPException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=403, detail=detail)


class BadRequestError(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status_code=400, detail=detail)


class ServiceUnavailableError(HTTPException):
    def __init__(self, service: str):
        super().__init__(status_code=503, detail=f"{service} is unavailable")


class QuotaExceededError(HTTPException):
    def __init__(self, detail: str = "Monthly quota exceeded"):
        super().__init__(status_code=429, detail=detail)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = request.headers.get("X-Request-ID", "")
    return JSONResponse(
        status_code=exc.status_code,
        content=ProblemDetail(
            type=f"errors/{exc.status_code}",
            title=exc.detail if isinstance(exc.detail, str) else "Error",
            status=exc.status_code,
            detail=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
            instance=str(request.url),
        ).model_dump(),
        headers={"X-Request-ID": request_id} if request_id else {},
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=ProblemDetail(
            type="errors/validation_error",
            title="Validation Error",
            status=422,
            detail=str(exc.errors()),
            instance=str(request.url),
        ).model_dump(),
    )
