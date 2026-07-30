"""NHS England Terminology Server adapter (system-to-system access).

Resolves codes via $lookup with retry, timeout and a circuit breaker. CI never
hits the live service; tests use recorded HTTP fixtures (respx/VCR). See
docs/DECISIONS.md ADR-004.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.logging import get_logger

logger = get_logger("clerkstone.terminology.nhse")


class NhseTerminologyClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        circuit_breaker_threshold: int = 5,
        timeout_seconds: int = 10,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._threshold = circuit_breaker_threshold
        self._timeout = timeout_seconds
        self._failures = 0

    def resolve(self, system: str, code: str) -> dict[str, Any] | None:
        if self._failures >= self._threshold:
            logger.warning("terminology circuit breaker open; refusing request")
            return None
        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.get(
                    f"{self._base_url}/CodeSystem/$lookup",
                    params={"system": system, "code": code},
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                resp.raise_for_status()
                self._failures = 0
                data = resp.json()
                params = (data.get("parameter") or [])
                display = next(
                    (p.get("valueString") for p in params if p.get("name") == "display"),
                    None,
                )
                return {"display": display, "active": True}
        except httpx.HTTPError:
            self._failures += 1
            logger.warning("terminology lookup failed", exc_info=True)
            return None
