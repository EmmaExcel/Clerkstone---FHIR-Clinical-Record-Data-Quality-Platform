from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"


class TerminologyClient(Protocol):
    """Minimal terminology interface used by TERM-* rules (the DI seam)."""

    def resolve(self, system: str, code: str) -> dict[str, Any] | None: ...


@dataclass(frozen=True)
class Finding:
    rule_id: str
    category: str
    severity: str
    title: str
    expression: str
    message: str
    resource_type: str
    resource_logical_id: str | None
    patient_logical_id: str | None = None
    suggested_action: str = ""
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleContext:
    """What a rule may consult while evaluating a single resource."""

    resource: dict[str, Any]
    resource_type: str
    # Resolved Patient resource for subject-bearing resources (Observation etc.).
    patient: dict[str, Any] | None = None
    # True iff a FHIR reference (e.g. "Patient/abc") resolves to a stored resource.
    reference_exists: Callable[[str], bool] = field(default_factory=lambda: lambda _: True)
    terminology: TerminologyClient | None = None
    # Cohort rules get the patient's full resource bundle.
    patient_resources: list[dict[str, Any]] = field(default_factory=list)
    # NHS number -> list of Patient logical ids, for cross-patient identity rules.
    nhs_number_owners: dict[str, list[str]] = field(default_factory=dict)


class Rule:
    """Base class for a deterministic data-quality rule.

    Subclasses set class attributes and implement ``evaluate``. Rules are
    auto-discovered by ``registry.py``.
    """

    id: str = ""
    category: str = ""
    severity: str = SEVERITY_ERROR
    title: str = ""
    description: str = ""
    fhirpath: str = ""
    suggested_action: str = ""
    applies_to: frozenset[str] = frozenset()

    def evaluate(self, ctx: RuleContext) -> list[Finding]:
        raise NotImplementedError

    def _finding(
        self,
        ctx: RuleContext,
        message: str,
        expression: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> Finding:
        return Finding(
            rule_id=self.id,
            category=self.category,
            severity=self.severity,
            title=self.title,
            expression=expression or self.fhirpath,
            message=message,
            resource_type=ctx.resource_type,
            resource_logical_id=ctx.resource.get("id"),
            patient_logical_id=(ctx.patient or {}).get("id"),
            suggested_action=self.suggested_action,
            context=context or {},
        )
