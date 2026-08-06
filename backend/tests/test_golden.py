from __future__ import annotations

import json
from pathlib import Path

from app.domain.quality.engine import run_rules
from app.domain.quality.rules.registry import discover_rules
from app.domain.terminology.base import get_terminology_client
from freezegun import freeze_time

ROOT = Path(__file__).resolve().parents[2]

# Keep in sync with scripts/generate_golden.py.
FROZEN_NOW = "2026-09-01T00:00:00Z"


def _manifest() -> dict:
    return json.loads((ROOT / "data/fixtures/manifest.json").read_text())


def _resources(bundle: dict) -> list[dict]:
    return [e["resource"] for e in bundle.get("entry", []) if "resource" in e]


def _load_corrupted(name: str) -> dict:
    return json.loads((ROOT / "data/fixtures/corrupted" / name).read_text())


def _actual(bundle: dict, terminology) -> list[tuple[str, str, str]]:
    findings, _ = run_rules(_resources(bundle), discover_rules(), terminology=terminology)
    return sorted((f.rule_id, f.severity, f.expression) for f in findings)


@freeze_time(FROZEN_NOW)
def test_valid_fixture_is_clean():
    valid = json.loads((ROOT / "data/fixtures/valid/patients.json").read_text())
    findings, _ = run_rules(
        _resources(valid), discover_rules(), terminology=get_terminology_client()
    )
    assert findings == [], f"valid fixture must be clean; got {sorted(f.rule_id for f in findings)}"


@freeze_time(FROZEN_NOW)
def test_each_defect_triggers_its_rule():
    terminology = get_terminology_client()
    for defect in _manifest()["defects"]:
        findings, _ = run_rules(
            _resources(_load_corrupted(defect["file"])), discover_rules(), terminology=terminology
        )
        rule_ids = {f.rule_id for f in findings}
        assert defect["rule"] in rule_ids, (
            f"{defect['defect']} should trigger {defect['rule']}; got {sorted(rule_ids)}"
        )


@freeze_time(FROZEN_NOW)
def test_golden_exact_findings():
    terminology = get_terminology_client()
    for defect in _manifest()["defects"]:
        expected_doc = json.loads(
            (ROOT / "data/fixtures/expected" / f"{defect['defect']}.json").read_text()
        )
        expected = sorted(
            (f["rule_id"], f["severity"], f["expression"]) for f in expected_doc["findings"]
        )
        actual = _actual(_load_corrupted(defect["file"]), terminology)
        assert actual == expected, (
            f"{defect['defect']}: findings diverged from the golden report.\n"
            f"  expected={expected}\n  actual  ={actual}"
        )
