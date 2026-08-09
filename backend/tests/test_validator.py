from __future__ import annotations

import httpx
import pytest
import respx
from app.domain.fhir.validator import ValidatorClient


@pytest.mark.asyncio
async def test_validator_client_returns_outcome():
    with respx.mock() as mock:
        mock.post("http://validator:8080/validate").mock(
            return_value=httpx.Response(
                200,
                json={
                    "resourceType": "OperationOutcome",
                    "issue": [{"severity": "error", "code": "invalid"}],
                },
            )
        )
        client = ValidatorClient("http://validator:8080")
        outcome = await client.validate({"resourceType": "Patient"})
        assert outcome is not None
        assert outcome["issue"][0]["code"] == "invalid"


@pytest.mark.asyncio
async def test_validator_client_unreachable_returns_none():
    with respx.mock() as mock:
        mock.post("http://validator:8080/validate").mock(
            side_effect=httpx.ConnectError("connection refused")
        )
        client = ValidatorClient("http://validator:8080")
        outcome = await client.validate({"resourceType": "Patient"})
        assert outcome is None
