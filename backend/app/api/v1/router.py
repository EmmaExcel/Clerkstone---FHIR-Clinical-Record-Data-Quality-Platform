from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import audit, fhir, hl7v2, patients, quality, system, terminology

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(system.router)
api_router.include_router(fhir.router)
api_router.include_router(patients.router)
api_router.include_router(quality.router)
api_router.include_router(terminology.router)
api_router.include_router(hl7v2.router)
api_router.include_router(audit.router)
