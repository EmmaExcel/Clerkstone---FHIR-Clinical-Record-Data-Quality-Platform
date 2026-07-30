"""Local terminology client backed by a committed illustrative subset.

The subset (``data/terminology/subset.json``) is illustrative and hand-verified on
a small set of concepts; it is NOT an official NHS mapping and must not be used
clinically (see docs/DATA_LICENCES.md).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class LocalTerminologyClient:
    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._index: dict[tuple[str, str], dict[str, Any]] = {}
        if not self._path.exists():
            return
        data = json.loads(self._path.read_text(encoding="utf-8"))
        for entry in data.get("concepts", []):
            self._index[(entry["system"], entry["code"])] = entry

    def resolve(self, system: str, code: str) -> dict[str, Any] | None:
        entry = self._index.get((system, code))
        if entry is None:
            return None
        return {"display": entry.get("display"), "active": entry.get("active", True)}
