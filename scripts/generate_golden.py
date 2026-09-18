#!/usr/bin/env python
"""Generate committed golden expected reports for the corrupted fixtures.

Runs the rule engine (``run_rules``) over each corrupted fixture and writes the
exact finding set (rule_id, severity, FHIRPath expression, with multiplicity
preserved) to ``data/fixtures/expected/<Defect>.json``.

These are regression snapshots, not an oracle — review the diff before
committing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.domain.quality.engine import run_rules  # noqa: E402
from app.domain.quality.rules.registry import discover_rules  # noqa: E402
from app.domain.terminology.base import get_terminology_client  # noqa: E402
from freezegun import freeze_time  # noqa: E402

# Frozen "now" so time-dependent rules (future dates, 24-month cohort windows)
# produce deterministic snapshots forever. Kept in sync with test_golden.py.
FROZEN_NOW = "2026-09-01T00:00:00Z"


def resources_of(bundle: dict) -> list[dict]:
    return [e["resource"] for e in bundle.get("entry", []) if "resource" in e]


def main() -> None:
    rules = discover_rules()
    terminology = get_terminology_client()
    manifest = json.loads((ROOT / "data/fixtures/manifest.json").read_text())
    out_dir = ROOT / "data/fixtures/expected"
    out_dir.mkdir(parents=True, exist_ok=True)

    with freeze_time(FROZEN_NOW):
        for defect in manifest["defects"]:
            bundle = json.loads((ROOT / "data/fixtures/corrupted" / defect["file"]).read_text())
            findings, _ = run_rules(resources_of(bundle), rules, terminology=terminology)
            rows = sorted(
                (
                    {"rule_id": f.rule_id, "severity": f.severity, "expression": f.expression}
                    for f in findings
                ),
                key=lambda x: (x["rule_id"], x["expression"]),
            )
            doc = {"defect": defect["defect"], "rule": defect["rule"], "findings": rows}
            (out_dir / f"{defect['defect']}.json").write_text(json.dumps(doc, indent=2) + "\n")

    print(f"wrote {len(manifest['defects'])} expected reports to {out_dir}")


if __name__ == "__main__":
    main()
