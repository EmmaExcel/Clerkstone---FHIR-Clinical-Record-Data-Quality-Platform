from __future__ import annotations

import inspect
from typing import Any

from app.domain.quality.rules import (
    cohort,
    duplication,
    identifier,
    physiological,
    referential,
    required,
    structural,
    temporal,
    terminology,
)
from app.domain.quality.rules.base import Rule

_MODULES = (
    required,
    identifier,
    referential,
    temporal,
    physiological,
    terminology,
    duplication,
    cohort,
    structural,
)

RULESET_VERSION = "1.0.0"


def discover_rules() -> list[Rule]:
    """Return one instantiated Rule per concrete rule class, in declaration order."""
    rules: list[Rule] = []
    seen: set[str] = set()
    for module in _MODULES:
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if not (issubclass(obj, Rule) and obj is not Rule):
                continue
            if not getattr(obj, "id", ""):
                continue  # abstract bases like _VitalRule have no id
            if obj.id in seen:
                raise ValueError(f"Duplicate rule id: {obj.id}")
            seen.add(obj.id)
            rules.append(obj())
    return rules


def get_rule_map() -> dict[str, Rule]:
    return {r.id: r for r in discover_rules()}


def rule_catalog() -> list[dict[str, Any]]:
    """Serialisable rule metadata, used to seed the ``dq_rule`` table."""
    out: list[dict[str, Any]] = []
    for rule in discover_rules():
        out.append(
            {
                "id": rule.id,
                "category": rule.category,
                "severity": rule.severity,
                "title": rule.title,
                "description": rule.description,
                "fhirpath": rule.fhirpath,
                "suggested_action": rule.suggested_action,
            }
        )
    return out
