

from __future__ import annotations

from typing import cast

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from starlette.types import ExceptionHandler

from app.api.errors import (
    FhirError,
    fhir_error_handler,
    pydantic_validation_handler,
    request_validation_handler,
)
from app.api.v1.router import api_router
from app.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import AuditMiddleware
from app.core.security import SecurityHeadersMiddleware


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title="Clerkstone — FHIR Clinical Record & Data Quality Platform",
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(AuditMiddleware)

    app.add_exception_handler(FhirError, cast(ExceptionHandler, fhir_error_handler))
    app.add_exception_handler(
        RequestValidationError, cast(ExceptionHandler, request_validation_handler)
    )
    app.add_exception_handler(
        ValidationError, cast(ExceptionHandler, pydantic_validation_handler)
    )

    try:
        from prometheus_fastapi_instrumentator import Instrumentator

        Instrumentator().instrument(app).expose(app, endpoint="/metrics")
    except Exception as exc:  # noqa: BLE001 — metrics are best-effort
        import logging

        logging.getLogger("clerkstone").warning("metrics instrumentation unavailable: %s", exc)

    app.include_router(api_router)
    return app


app = create_app()
