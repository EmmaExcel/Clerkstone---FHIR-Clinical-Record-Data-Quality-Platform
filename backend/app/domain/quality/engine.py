from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any

from app.domain.quality.rules.base import Finding, Rule, RuleContext, TerminologyClient
from app.domain.quality.rules.util import get_nhs_numbers

logger = logging.getLogger("clerkstone.quality")


def _ref_id(reference: Any | None) -> str | None:
    if not reference:
        return None
    if reference.startswith("urn:uuid:"):
        return reference[len("urn:uuid:") :]
    if "/" in reference:
        return reference.rsplit("/", 1)[1]
    return reference


def build_reference_index(resources: list[dict[str, Any]]) -> set[str]:
    return {
        f"{r.get('resourceType')}/{r.get('id')}"
        for r in resources
        if r.get("resourceType") and r.get("id")
    }


def run_rules(
    resources: list[dict[str, Any]],
    rules: list[Rule],
    terminology: TerminologyClient | None = None,
    reference_index: set[str] | None = None,
) -> tuple[list[Finding], dict[str, Any]]:
    """Run every rule over every applicable resource.

    Returns ``(findings, stats)`` where ``stats`` records per-rule timing.
    """
    if reference_index is None:
        reference_index = build_reference_index(resources)

    patient_map: dict[str, dict[str, Any]] = {
        r["id"]: r for r in resources if r.get("resourceType") == "Patient" and r.get("id")
    }
    nhs_number_owners: dict[str, list[str]] = defaultdict(list)
    for patient_id, patient_resource in patient_map.items():
        for number in get_nhs_numbers(patient_resource):
            nhs_number_owners[number].append(patient_id)
    patient_resources_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in resources:
        if r.get("resourceType") == "Patient":
            pid = r.get("id")
        else:
            pid = _ref_id((r.get("subject") or {}).get("reference"))
        if pid and pid in patient_map:
            patient_resources_map[pid].append(r)

    findings: list[Finding] = []
    stats: dict[str, float] = {}

    def reference_exists(reference: str) -> bool:
        return reference in reference_index

    for resource in resources:
        rt = resource.get("resourceType", "")
        patient: dict[str, Any] | None = None
        if rt == "Patient":
            patient = resource
        else:
            pid = _ref_id((resource.get("subject") or {}).get("reference"))
            patient = patient_map.get(pid) if pid else None

        patient_resources: list[dict[str, Any]] = []
        if patient and patient.get("id"):
            patient_resources = patient_resources_map.get(patient["id"], [])

        ctx = RuleContext(
            resource=resource,
            resource_type=rt,
            patient=patient,
            reference_exists=reference_exists,
            terminology=terminology,
            patient_resources=patient_resources,
            nhs_number_owners=nhs_number_owners,
        )

        for rule in rules:
            if rt not in rule.applies_to:
                continue
            started = time.perf_counter()
            try:
                findings.extend(rule.evaluate(ctx))
            except Exception:  # noqa: BLE001 — a single failing rule must not abort the run
                logger.warning("rule %s failed during evaluation", rule.id, exc_info=True)
                continue
            finally:
                stats[rule.id] = stats.get(rule.id, 0.0) + (time.perf_counter() - started)

    return findings, stats
