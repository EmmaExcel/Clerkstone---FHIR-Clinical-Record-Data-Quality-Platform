from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db.session import async_session_factory  # noqa: E402
from app.domain.fhir.ingest import ingest_bundle  # noqa: E402


async def _load(path: Path) -> None:
    bundle = json.loads(path.read_text())
    async with async_session_factory() as session:
        result = await ingest_bundle(session, bundle, uploaded_by="load-script")
        await session.commit()
        print(
            f"ingested {result.accepted} resources "
            f"(status={result.status}, rejected={result.rejected})"
        )


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/fixtures/valid/patients.json")
    asyncio.run(_load(path))


if __name__ == "__main__":
    main()
