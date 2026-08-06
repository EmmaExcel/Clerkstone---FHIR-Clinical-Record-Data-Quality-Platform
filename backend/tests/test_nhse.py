from __future__ import annotations

import httpx
import respx
from app.domain.terminology.nhse import NhseTerminologyClient

BASE = "https://ontology.nhs.uk/production1/fhir"


def test_resolve_success():
    with respx.mock() as mock:
        mock.get(f"{BASE}/CodeSystem/$lookup").mock(
            return_value=httpx.Response(
                200,
                json={"parameter": [{"name": "display", "valueString": "Hypertension"}]},
            )
        )
        client = NhseTerminologyClient(BASE, "test-key")
        result = client.resolve("http://snomed.info/sct", "38341003")
        assert result == {"display": "Hypertension", "active": True}


def test_resolve_http_error_returns_none():
    with respx.mock() as mock:
        mock.get(f"{BASE}/CodeSystem/$lookup").mock(return_value=httpx.Response(500))
        client = NhseTerminologyClient(BASE, "test-key")
        assert client.resolve("http://snomed.info/sct", "38341003") is None


def test_circuit_breaker_opens_after_threshold():
    with respx.mock() as mock:
        mock.get(f"{BASE}/CodeSystem/$lookup").mock(
            side_effect=httpx.ConnectError("unreachable")
        )
        client = NhseTerminologyClient(BASE, "test-key", circuit_breaker_threshold=2)
        assert client.resolve("http://snomed.info/sct", "x") is None  # failure 1
        assert client.resolve("http://snomed.info/sct", "x") is None  # failure 2 -> open
        # Circuit is now open: returns None without issuing a request.
        assert client.resolve("http://snomed.info/sct", "x") is None
