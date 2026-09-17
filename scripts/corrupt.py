"""Deterministic corruption harness.

Applies named, seeded mutations to a valid FHIR Bundle. Each mutation is a class
whose docstring names the rule ID(s) it should trigger, so the golden-file tests
can assert exactly which findings each defect produces. See docs/DEFECT_TAXONOMY.md.
"""

from __future__ import annotations

import argparse
import copy
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.domain.fhir.nhs import make_valid_nhs_number  # noqa: E402

NHS_SYSTEM = "https://fhir.nhs.uk/Id/nhs-number"


def _resources(bundle: dict) -> list[dict]:
    return [e["resource"] for e in bundle.get("entry", []) if "resource" in e]


def _find(bundle: dict, resource_type: str, idx: int = 0) -> dict | None:
    matches = [r for r in _resources(bundle) if r.get("resourceType") == resource_type]
    return matches[idx] if idx < len(matches) else None


def _find_obs(bundle: dict, code: str) -> dict | None:
    for r in _resources(bundle):
        if r.get("resourceType") != "Observation":
            continue
        for c in (r.get("code") or {}).get("coding") or []:
            if c.get("code") == code:
                return r
    return None


def _set_obs_value(bundle: dict, code: str, value: float) -> dict:
    obs = _find_obs(bundle, code)
    if obs is not None:
        obs.setdefault("valueQuantity", {})["value"] = value
    return bundle


# Core defects


class MissingNhsNumber:
    """IDENT-001 — remove the NHS number identifier."""

    rule = "IDENT-001"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        patient = _find(bundle, "Patient")
        patient["identifier"] = []
        return bundle


class InvalidNhsNumberCheckDigit:
    """IDENT-003 — corrupt the NHS number check digit."""

    rule = "IDENT-003"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        patient = _find(bundle, "Patient")
        for ident in patient.get("identifier", []):
            value = ident.get("value", "")
            if len(value) == 10 and value.isdigit():
                bad = str((int(value[-1]) + 1) % 10)
                ident["value"] = value[:-1] + bad
                break
        return bundle


class TemporalInversion:
    """TEMP-003 — set Encounter.period.end before start."""

    rule = "TEMP-003"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        from datetime import datetime

        enc = _find(bundle, "Encounter")
        period = enc.setdefault("period", {})
        start = period.get("start", "2026-06-01T10:00:00Z")
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        period["end"] = (start_dt - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        period["start"] = start
        return bundle


class FutureBirthDate:
    """TEMP-001 — set Patient.birthDate in the future."""

    rule = "TEMP-001"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        patient = _find(bundle, "Patient")
        patient["birthDate"] = "2031-04-02"
        return bundle


class DecimalShift:
    """PHYS-001 — multiply a systolic BP value by 10."""

    rule = "PHYS-001"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        obs = _find_obs(bundle, "271649006")
        if obs is None:
            return bundle
        vq = obs.get("valueQuantity") or {}
        vq["value"] = round((vq.get("value", 120) or 120) * 10, 1)
        obs["valueQuantity"] = vq
        return bundle


class SpO2Sentinel:
    """PHYS-004 — set SpO2 to the sentinel value 0."""

    rule = "PHYS-004"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        return _set_obs_value(bundle, "431314004", 0.0)


class UnresolvableSnomedCode:
    """TERM-002 — replace a SNOMED code with a plausible but wrong one."""

    rule = "TERM-002"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        obs = _find(bundle, "Observation")
        (obs["code"]["coding"][0])["code"] = "999999999"
        return bundle


class DanglingReference:
    """REF-001 — point Observation.subject at a missing Patient."""

    rule = "REF-001"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        obs = _find(bundle, "Observation")
        obs["subject"] = {"reference": "Patient/missing-patient"}
        return bundle


class DuplicateObservation:
    """DUP-001 — duplicate an Observation exactly."""

    rule = "DUP-001"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        obs = _find(bundle, "Observation")
        dup = copy.deepcopy(obs)
        dup["id"] = obs["id"] + "-dup"
        bundle["entry"].append({"fullUrl": f"urn:uuid:{dup['id']}", "resource": dup,
                                "request": {"method": "POST", "url": "Observation"}})
        return bundle


class MissingProfile:
    """PROF-002 — remove meta.profile from a Patient."""

    rule = "PROF-002"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        patient = _find(bundle, "Patient")
        patient.setdefault("meta", {})["profile"] = []
        return bundle


class MojibakeName:
    """STRUCT-004 — inject mojibake into the patient family name."""

    rule = "STRUCT-004"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        patient = _find(bundle, "Patient")
        patient["name"][0]["family"] = "Sm\u00efth\u00c3\u00a9"
        return bundle


class MissingObservationCode:
    """REQ-006 — remove Observation.code."""

    rule = "REQ-006"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        obs = _find(bundle, "Observation")
        obs["code"] = {"coding": []}
        return bundle


# Identifier


class UnverifiedNhsNumber:
    """IDENT-002 — strip the NHS number verification-status extension."""

    rule = "IDENT-002"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        patient = _find(bundle, "Patient")
        for ident in patient.get("identifier", []):
            if ident.get("system") == NHS_SYSTEM:
                ident.pop("extension", None)
                break
        return bundle


class TwoNhsNumbers:
    """IDENT-004 — add a second, distinct NHS number to the same Patient."""

    rule = "IDENT-004"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        patient = _find(bundle, "Patient")
        existing = (patient.get("identifier") or [{}])[0] or {}
        second = {
            "system": NHS_SYSTEM,
            "value": make_valid_nhs_number("991000001"),
            "extension": existing.get("extension") or [],
        }
        patient.setdefault("identifier", []).append(second)
        return bundle


class SharedNhsNumber:
    """IDENT-005 — give two Patients the same NHS number (cross-patient)."""

    rule = "IDENT-005"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        patients = [r for r in _resources(bundle) if r.get("resourceType") == "Patient"]
        number = None
        for ident in patients[0].get("identifier", []):
            if ident.get("system") == NHS_SYSTEM:
                number = ident["value"]
                break
        for ident in patients[1].get("identifier", []):
            if ident.get("system") == NHS_SYSTEM:
                ident["value"] = number
                break
        return bundle


class UnrecognisedIdentifierSystem:
    """IDENT-006 — add an identifier with an unrecognised system URI."""

    rule = "IDENT-006"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        patient = _find(bundle, "Patient")
        patient.setdefault("identifier", []).append(
            {"system": "http://example.org/mrn", "value": "MRN12345"}
        )
        return bundle


class InvalidNhsNumberFormat:
    """IDENT-009 — set the NHS number to a non-10-digit value (also fails IDENT-003)."""

    rule = "IDENT-009"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        patient = _find(bundle, "Patient")
        for ident in patient.get("identifier", []):
            if ident.get("system") == NHS_SYSTEM:
                ident["value"] = "ABC"
                break
        return bundle


# Required fields


class BirthDateAbsent:
    """REQ-001 — remove Patient.birthDate."""

    rule = "REQ-001"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        _find(bundle, "Patient").pop("birthDate", None)
        return bundle


class GenderAbsent:
    """REQ-002 — remove Patient.gender."""

    rule = "REQ-002"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        _find(bundle, "Patient").pop("gender", None)
        return bundle


class GenderOutOfValueSet:
    """REQ-003 — set Patient.gender to a value outside the FHIR value set."""

    rule = "REQ-003"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        _find(bundle, "Patient")["gender"] = "invalid-code"
        return bundle


class EncounterClassAbsent:
    """REQ-004 — remove Encounter.class."""

    rule = "REQ-004"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        _find(bundle, "Encounter").pop("class", None)
        return bundle


class ObservationStatusAbsent:
    """REQ-005 — remove Observation.status."""

    rule = "REQ-005"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        _find(bundle, "Observation").pop("status", None)
        return bundle


class PatientNameAbsent:
    """REQ-007 — remove Patient.name."""

    rule = "REQ-007"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        _find(bundle, "Patient").pop("name", None)
        return bundle


class EncounterStatusAbsent:
    """REQ-008 — remove Encounter.status."""

    rule = "REQ-008"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        _find(bundle, "Encounter").pop("status", None)
        return bundle


class MedicationWithoutCode:
    """REQ-009 — remove MedicationRequest.medicationCodeableConcept."""

    rule = "REQ-009"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        _find(bundle, "MedicationRequest").pop("medicationCodeableConcept", None)
        return bundle


# Referential integrity


class EncounterSubjectDangling:
    """REF-002 — point Encounter.subject at a missing Patient."""

    rule = "REF-002"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        _find(bundle, "Encounter")["subject"] = {"reference": "Patient/missing-patient"}
        return bundle


class ObservationSubjectMissing:
    """REF-005 — remove Observation.subject."""

    rule = "REF-005"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        _find(bundle, "Observation").pop("subject", None)
        return bundle


class MedicationSubjectDangling:
    """REF-006 — point MedicationRequest.subject at a missing Patient."""

    rule = "REF-006"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        _find(bundle, "MedicationRequest")["subject"] = {"reference": "Patient/missing-patient"}
        return bundle


class ObservationEncounterDangling:
    """REF-004 — point Observation.encounter at a missing Encounter."""

    rule = "REF-004"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        _find(bundle, "Observation")["encounter"] = {"reference": "Encounter/missing-encounter"}
        return bundle


# Temporal coherence


class BirthDateTooOld:
    """TEMP-002 — set Patient.birthDate more than 130 years in the past."""

    rule = "TEMP-002"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        _find(bundle, "Patient")["birthDate"] = "1800-01-01"
        return bundle


class DeathBeforeBirth:
    """TEMP-004 — set Patient.deceasedDateTime before birthDate."""

    rule = "TEMP-004"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        patient = _find(bundle, "Patient")
        birth = date.fromisoformat((patient.get("birthDate") or "1980-01-01")[:10])
        patient["deceasedDateTime"] = (birth - timedelta(days=365 * 20)).isoformat() + "T00:00:00Z"
        return bundle


class ObservationBeforeBirth:
    """TEMP-005 — set an Observation effective time before the patient's birth."""

    rule = "TEMP-005"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        patient = _find(bundle, "Patient")
        birth = date.fromisoformat((patient.get("birthDate") or "1980-01-01")[:10])
        obs = _find(bundle, "Observation")
        obs["effectiveDateTime"] = (birth - timedelta(days=365)).isoformat() + "T00:00:00Z"
        return bundle


class ConditionOnsetAfterAbatement:
    """TEMP-007 — set Condition.abatement before onset."""

    rule = "TEMP-007"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        cond = _find(bundle, "Condition")
        cond["onsetDateTime"] = "2026-06-01T00:00:00Z"
        cond["abatementDateTime"] = "2020-01-01T00:00:00Z"
        return bundle


class ObservationInFuture:
    """TEMP-008 — set an Observation effective time in the future."""

    rule = "TEMP-008"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        _find(bundle, "Observation")["effectiveDateTime"] = "2031-01-01T00:00:00Z"
        return bundle


class ConditionOnsetInFuture:
    """TEMP-009 — set Condition.onset in the future."""

    rule = "TEMP-009"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        _find(bundle, "Condition")["onsetDateTime"] = "2031-01-01T00:00:00Z"
        return bundle


# Physiological plausibility


class DiastolicBp:
    """PHYS-002 — set diastolic BP to an impossible value."""

    rule = "PHYS-002"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        return _set_obs_value(bundle, "271650006", 999.0)


class HeartRate:
    """PHYS-003 — set heart rate to an impossible value."""

    rule = "PHYS-003"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        return _set_obs_value(bundle, "364075005", 999.0)


class Temperature:
    """PHYS-005 — set body temperature to an impossible value."""

    rule = "PHYS-005"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        return _set_obs_value(bundle, "386725007", 99.0)


class Weight:
    """PHYS-006 — set body weight to an impossible value."""

    rule = "PHYS-006"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        return _set_obs_value(bundle, "27113001", 9999.0)


class Height:
    """PHYS-007 — set body height to an impossible value."""

    rule = "PHYS-007"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        return _set_obs_value(bundle, "50373000", 9999.0)


class RespiratoryRate:
    """PHYS-008 — set respiratory rate to an impossible value."""

    rule = "PHYS-008"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        return _set_obs_value(bundle, "86290005", 999.0)


# Terminology


class CodeSystemUnrecognised:
    """TERM-001 — change an Observation code system to an unrecognised URI."""

    rule = "TERM-001"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        obs = _find(bundle, "Observation")
        obs["code"]["coding"][0]["system"] = "http://example.org/codes"
        return bundle


class DmdCodeUnresolvable:
    """TERM-003 — set a MedicationRequest dm+d code to an unresolvable one."""

    rule = "TERM-003"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        med = _find(bundle, "MedicationRequest")
        med["medicationCodeableConcept"]["coding"][0]["code"] = "999999999"
        return bundle


class DmdCodeFormatInvalid:
    """TERM-008 — set a MedicationRequest dm+d code to a non-9-digit value."""

    rule = "TERM-008"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        med = _find(bundle, "MedicationRequest")
        med["medicationCodeableConcept"]["coding"][0]["code"] = "ABC"
        return bundle


# Duplication / structural / cohort


class DuplicateEncounter:
    """DUP-002 — duplicate an Encounter exactly."""

    rule = "DUP-002"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        enc = _find(bundle, "Encounter")
        dup = copy.deepcopy(enc)
        dup["id"] = enc["id"] + "-dup"
        bundle["entry"].append({"fullUrl": f"urn:uuid:{dup['id']}", "resource": dup,
                                "request": {"method": "POST", "url": "Encounter"}})
        return bundle


class UnknownExtension:
    """STRUCT-002 — add an unrecognised extension URL to a Patient."""

    rule = "STRUCT-002"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        _find(bundle, "Patient")["extension"] = [{"url": "http://example.org/unknown-extension"}]
        return bundle


class EncounterWithoutObservations:
    """COH-001 — remove all Observations so the patient has encounters but no observations."""

    rule = "COH-001"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        bundle["entry"] = [
            e for e in bundle.get("entry", [])
            if e.get("resource", {}).get("resourceType") != "Observation"
        ]
        return bundle


class ObservationsWithoutEncounters:
    """COH-004 — remove all Encounters so the patient has observations but no encounters."""

    rule = "COH-004"

    @staticmethod
    def apply(bundle: dict, rng: random.Random) -> dict:
        bundle["entry"] = [
            e for e in bundle.get("entry", [])
            if e.get("resource", {}).get("resourceType") != "Encounter"
        ]
        for e in bundle.get("entry", []):
            if e.get("resource", {}).get("resourceType") == "Observation":
                e["resource"].pop("encounter", None)
        return bundle


# Registration

_EXISTING = (
    MissingNhsNumber, InvalidNhsNumberCheckDigit, TemporalInversion, FutureBirthDate,
    DecimalShift, SpO2Sentinel, UnresolvableSnomedCode, DanglingReference,
    DuplicateObservation, MissingProfile, MojibakeName, MissingObservationCode,
)

_NEW = (
    # identifier
    UnverifiedNhsNumber, TwoNhsNumbers, SharedNhsNumber, UnrecognisedIdentifierSystem,
    InvalidNhsNumberFormat,
    # required
    BirthDateAbsent, GenderAbsent, GenderOutOfValueSet, EncounterClassAbsent,
    ObservationStatusAbsent, PatientNameAbsent, EncounterStatusAbsent, MedicationWithoutCode,
    # referential
    EncounterSubjectDangling, ObservationSubjectMissing, MedicationSubjectDangling,
    ObservationEncounterDangling,
    # temporal
    BirthDateTooOld, DeathBeforeBirth, ObservationBeforeBirth, ConditionOnsetAfterAbatement,
    ObservationInFuture, ConditionOnsetInFuture,
    # physiological
    DiastolicBp, HeartRate, Temperature, Weight, Height, RespiratoryRate,
    # terminology
    CodeSystemUnrecognised, DmdCodeUnresolvable, DmdCodeFormatInvalid,
    # duplication / structural / cohort
    DuplicateEncounter, UnknownExtension, EncounterWithoutObservations,
    ObservationsWithoutEncounters,
)

_ALL = _EXISTING + _NEW

DEFECTS = [cls.__name__ for cls in _ALL]
_REGISTRY = {cls.__name__: cls for cls in _ALL}

# Defects that target a specific coded observation; the subset is chosen from a
# patient who actually has that code so the defect reliably fires.
_CODE_DEFECTS = {
    "DecimalShift": "271649006", "SpO2Sentinel": "431314004",
    "DiastolicBp": "271650006", "HeartRate": "364075005",
    "Temperature": "386725007", "Weight": "27113001",
    "Height": "50373000", "RespiratoryRate": "86290005",
}

# Defects that need a two-patient bundle rather than a single-patient subset.
_CROSS_PATIENT_DEFECTS = {"SharedNhsNumber"}


def corrupt_bundle(bundle: dict, defect_name: str, seed: int) -> dict:
    cls = _REGISTRY[defect_name]
    rng = random.Random(seed)
    return cls.apply(copy.deepcopy(bundle), rng)


def _patient_subset(base: dict, needs_code: str | None) -> dict:
    """Return a minimal bundle: one patient's resources (chosen to include the
    coded observation when ``needs_code`` is given)."""
    entries_by_patient: dict[str, list[dict]] = {}
    for e in base.get("entry", []):
        r = e.get("resource", {})
        if r.get("resourceType") == "Patient":
            entries_by_patient.setdefault(r["id"], []).append(e)
    for e in base.get("entry", []):
        r = e.get("resource", {})
        if r.get("resourceType") == "Patient":
            continue
        subject = (r.get("subject") or {}).get("reference") or ""
        pid = subject.rsplit("/", 1)[-1]
        if pid in entries_by_patient:
            entries_by_patient[pid].append(e)

    if needs_code:
        for entries in entries_by_patient.values():
            for e in entries:
                codings = (e.get("resource", {}).get("code") or {}).get("coding") or []
                if any(c.get("code") == needs_code for c in codings):
                    return {"resourceType": "Bundle", "type": "transaction", "entry": entries}

    first = next(iter(entries_by_patient.values()))
    return {"resourceType": "Bundle", "type": "transaction", "entry": first}


def _two_patient_subset(base: dict) -> dict:
    """Return the resources of the first two patients combined."""
    patient_entries = [
        e for e in base.get("entry", [])
        if e.get("resource", {}).get("resourceType") == "Patient"
    ][:2]
    ids = {e["resource"]["id"] for e in patient_entries}
    entries = list(patient_entries)
    for e in base.get("entry", []):
        r = e.get("resource", {})
        if r.get("resourceType") == "Patient":
            continue
        subject = (r.get("subject") or {}).get("reference") or ""
        pid = subject.rsplit("/", 1)[-1]
        if pid in ids:
            entries.append(e)
    return {"resourceType": "Bundle", "type": "transaction", "entry": entries}


def _make_subset(base: dict, name: str) -> dict:
    if name in _CROSS_PATIENT_DEFECTS:
        return _two_patient_subset(base)
    return _patient_subset(base, _CODE_DEFECTS.get(name))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/fixtures/valid/patients.json"))
    parser.add_argument("--out", type=Path, default=Path("data/fixtures/corrupted"))
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    base = json.loads(args.input.read_text())
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = {"seed": args.seed, "defects": []}
    for name in DEFECTS:
        subset = _make_subset(base, name)
        corrupted = corrupt_bundle(subset, name, args.seed)
        path = args.out / f"{name}.json"
        path.write_text(json.dumps(corrupted, indent=2))
        manifest["defects"].append({"defect": name, "rule": _REGISTRY[name].rule, "file": path.name})
    (args.out.parent / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"wrote {len(DEFECTS)} corrupted bundles to {args.out}")


if __name__ == "__main__":
    main()
