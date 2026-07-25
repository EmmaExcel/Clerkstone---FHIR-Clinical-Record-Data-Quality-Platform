"""HL7 v2 ADT -> FHIR converter.

Supports ADT^A01/A03/A08 (admit, discharge, update). Maps PID -> Patient and
PV1 -> Encounter. See docs/HL7V2_MAPPING.md for the committed mapping table.
"""

from __future__ import annotations

import uuid
from typing import Any

import hl7

_NHS_NUMBER_SYSTEM = "https://fhir.nhs.uk/Id/nhs-number"

_GENDER_MAP = {"M": "male", "F": "female", "O": "other", "U": "unknown"}
_CLASS_MAP = {"I": "inpatient", "O": "outpatient", "E": "emergency", "B": "ambulatory"}


def _field(segment: Any, index: int) -> Any:
    """Return a field by 1-indexed HL7 position, or None if absent."""
    if segment is None:
        return None
    try:
        return segment[index]
    except (IndexError, KeyError):
        return None


def _text(value: Any) -> str | None:
    """Recursively flatten a component (str or nested sub-component list) to text."""
    while isinstance(value, (list, tuple)) and value:
        value = value[0]
    if value is None or isinstance(value, (list, tuple)) or str(value).strip() == "":
        return None
    return str(value).strip()


def _component(field: Any, index: int) -> str | None:
    """Return the component at ``index`` of an HL7 field, tolerating repeats."""
    if field is None:
        return None
    # A repeating field is a list of Field (list) values; take the first.
    if isinstance(field, list) and field and isinstance(field[0], (list, tuple)):
        field = field[0]
    if isinstance(field, (list, tuple)):
        return _text(field[index]) if index < len(field) else None
    return _text(field)


def _hl7_ts(value: str | None) -> str | None:
    """Convert an HL7 TS (YYYYMMDD[HHMMSS[.S]]) to an ISO date/datetime."""
    if not value:
        return None
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) >= 14:
        return f"{digits[0:4]}-{digits[4:6]}-{digits[6:8]}T{digits[8:10]}:{digits[10:12]}:{digits[12:14]}Z"
    if len(digits) >= 8:
        return f"{digits[0:4]}-{digits[4:6]}-{digits[6:8]}"
    return None


def _event_type(msg: hl7.Message) -> str:
    # MSH-9 = "ADT^A01": component 1 is the trigger event (A01/A03/A08).
    msh = msg.segment("MSH")
    return str(_component(_field(msh, 9), 1) or "")


def adt_to_fhir_bundle(message_text: str) -> dict[str, Any]:
    try:
        msg = hl7.parse(message_text)
    except Exception as exc:  # noqa: BLE001 — normalise parser errors to ValueError
        raise ValueError(f"Invalid HL7 v2 message: {exc}") from exc
    pid = msg.segment("PID")
    pv1 = msg.segment("PV1")

    patient_id = f"p-{uuid.uuid4().hex[:8]}"
    encounter_id = f"e-{uuid.uuid4().hex[:8]}"

    identifiers: list[dict[str, Any]] = []
    nhs_number = _component(_field(pid, 3), 0)
    if nhs_number:
        identifiers.append({"system": _NHS_NUMBER_SYSTEM, "value": nhs_number})

    family = _component(_field(pid, 5), 0)
    given = _component(_field(pid, 5), 1)
    name = []
    if family or given:
        name.append({"family": family, "given": [given] if given else []})

    birth_date = _hl7_ts(_component(_field(pid, 7), 0))
    gender = _GENDER_MAP.get((_component(_field(pid, 8), 0) or "").upper())

    address_parts = _field(pid, 11)
    address = None
    if address_parts:
        street = _component(address_parts, 0)
        city = _component(address_parts, 2)
        postal = _component(address_parts, 4)
        if street or city or postal:
            address = {"city": city, "postalCode": postal, "country": "GB"}

    patient: dict[str, Any] = {
        "resourceType": "Patient",
        "id": patient_id,
        "identifier": identifiers,
        "name": name,
        "gender": gender,
        "birthDate": birth_date,
        "address": [address] if address else [],
    }

    class_code = _component(_field(pv1, 2), 0)
    msg_type = _event_type(msg)
    encounter: dict[str, Any] = {
        "resourceType": "Encounter",
        "id": encounter_id,
        "status": "finished" if msg_type == "A03" else "in-progress",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": _CLASS_MAP.get((class_code or "").upper(), class_code),
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "period": {
            "start": _hl7_ts(_component(_field(pv1, 44), 0)),
            "end": _hl7_ts(_component(_field(pv1, 45), 0)),
        },
    }

    return {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {"fullUrl": f"urn:uuid:{patient_id}", "resource": patient,
             "request": {"method": "POST", "url": "Patient"}},
            {"fullUrl": f"urn:uuid:{encounter_id}", "resource": encounter,
             "request": {"method": "POST", "url": "Encounter"}},
        ],
    }
