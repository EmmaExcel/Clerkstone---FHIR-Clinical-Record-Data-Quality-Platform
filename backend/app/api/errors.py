"""FHIR-native error handling.

Every API error is a FHIR ``OperationOutcome`` with a machine-readable
``issue.code``, a human message, and an ``expression`` pointing at the offending
element — so a client (or an agent) can reason about the failure.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError


class FhirError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        diagnostics: str,
        expression: str | None = None,
        severity: str = "error",
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.diagnostics = diagnostics
        self.expression = expression
        self.severity = severity
        super().__init__(diagnostics)


def issue(
    severity: str,
    code: str,
    diagnostics: str,
    expression: str | None = None,
    details_text: str | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {"severity": severity, "code": code, "diagnostics": diagnostics}
    if expression:
        out["expression"] = [expression]
    if details_text:
        out["details"] = {"text": details_text}
    return out


def operation_outcome(issues: list[dict[str, Any]]) -> dict[str, Any]:
    return {"resourceType": "OperationOutcome", "issue": issues}


async def fhir_error_handler(request: Request, exc: FhirError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=operation_outcome(
            [issue(exc.severity, exc.code, exc.diagnostics, exc.expression)]
        ),
    )


def _validation_issues(exc: RequestValidationError) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", ()) if p != "body")
        out.append(
            issue(
                "error",
                "invalid",
                err.get("msg", "validation error"),
                expression=loc or None,
            )
        )
    return out


async def request_validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422, content=operation_outcome(_validation_issues(exc))
    )


async def pydantic_validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
    issues = [
        issue("error", "invalid", ".".join(str(p) for p in e["loc"]), None)
        for e in exc.errors()
    ]
    return JSONResponse(status_code=422, content=operation_outcome(issues))
