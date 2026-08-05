from __future__ import annotations

from app.main import create_app


def test_create_app_registers_routes():
    app = create_app()
    assert app.title == "Clerkstone — FHIR Clinical Record & Data Quality Platform"
    assert app.docs_url == "/docs"

    paths = set(app.openapi()["paths"].keys())
    assert "/metrics" in paths
    assert "/api/v1/health" in paths
    assert "/api/v1/fhir" in paths
    assert "/api/v1/patients" in paths
    assert "/api/v1/quality/runs" in paths
    assert "/api/v1/terminology/resolve" in paths
