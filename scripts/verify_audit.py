from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.audit import verify_chain  # noqa: E402
from app.db.session import async_session_factory  # noqa: E402


async def _verify() -> int:
    async with async_session_factory() as session:
        ok, bad_id = await verify_chain(session)
    if ok:
        print("audit chain VALID")
        return 0
    print(f"audit chain TAMPERED — first divergent event id: {bad_id}")
    return 1


def main() -> None:
    sys.exit(asyncio.run(_verify()))


if __name__ == "__main__":
    main()
