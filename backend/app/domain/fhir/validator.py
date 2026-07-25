"""FHIR validator sidecar client (the profile-validation DI seam).

``$validate`` delegates UK Core profile validation to a sidecar running the HL7
FHIR validator jar. When the sidecar is unreachable, the API falls back to
structural validation and notes that profile validation was skipped — it never
silently claims a profile was validated.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger("clerkstone.fhir.validator")


class ValidatorClient:
    def __init__(self, base_url: str, timeout_seconds: int = 20) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    async def validate(self, resource: dict[str, Any]) -> dict[str, Any] | None:
        """Return the OperationOutcome from the sidecar, or None if unreachable."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/validate", json={"resource": resource}
                )
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as exc:
            logger.warning("validator sidecar unreachable: %s", exc)
            return None


def get_validator_client() -> ValidatorClient | None:
    settings = get_settings()
    if not settings.validator_base_url:
        return None
    return ValidatorClient(settings.validator_base_url, settings.validator_timeout_seconds)
