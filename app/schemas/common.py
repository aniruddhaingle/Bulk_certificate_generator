from pydantic import BaseModel


class ErrorDetail(BaseModel):
    field: str | None = None
    issue: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] | None = None
    context: dict[str, str] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
