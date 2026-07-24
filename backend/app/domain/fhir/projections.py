"""Resource -> relational projection mapping.

Projections are disposable views of the JSONB source of truth. They must never
disagree with the resource; ``scripts/rebuild_projections.py`` rebuilds them.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.domain.fhir.resources import NHS_NUMBER_SYSTEM

_NHS_VERIFICATION_EXT = (
    "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-NHSNumberVerificationStatus"
)
_VERIFICATION_STATUS = {"01": "verified", "02": "unverified"}


def _first_coding(codeable: dict[str, Any] | None) -> tuple[str | None, str | None, str | None]:
    codings = (codeable or {}).get("coding") or []
    if not codings:
        return None, None, None
    first = codings[0] or {}
    return first.get("system"), first.get("code"), first.get("display")


def _identifier_value(
    identifiers: list[dict[str, Any]] | None, system: str
) -> tuple[str | None, str | None]:
    for ident in identifiers or []:
        if (ident or {}).get("system") == system:
            status = "absent"
            for ext in ident.get("extension") or []:
                if ext.get("url") == _NHS_VERIFICATION_EXT:
                    code = (
                        (((ext.get("valueCodeableConcept") or {}).get("coding") or [{}])[0] or {})
                        .get("code")
                    )
                    status = _VERIFICATION_STATUS.get(str(code), "unverified")
                    break
            return str(ident["value"]), status
    return None, None


def _outward_postcode(postal_code: str | None) -> str | None:
    if not postal_code:
        return None
    return postal_code.strip().split(" ")[0].upper()


def project_patient(resource: dict[str, Any]) -> dict[str, Any]:
    name = (resource.get("name") or [{}])[0] or {}
    nhs_number, nhs_status = _identifier_value(resource.get("identifier"), NHS_NUMBER_SYSTEM)
    address = (resource.get("address") or [{}])[0] or {}
    deceased = resource.get("deceasedBoolean", False)
    if "deceasedDateTime" in resource:
        deceased = True

    birth = resource.get("birthDate")
    return {
        "logical_id": resource.get("id"),
        "nhs_number": nhs_number,
        "nhs_number_status": nhs_status,
        "family_name": name.get("family"),
        "given_names": name.get("given") or None,
        "birth_date": date.fromisoformat(birth[:10]) if birth else None,
        "gender": resource.get("gender"),
        "deceased": bool(deceased),
        "postcode": _outward_postcode(address.get("postalCode")),
    }


def project_encounter(resource: dict[str, Any]) -> dict[str, Any]:
    period = resource.get("period") or {}
    hospitalization = resource.get("hospitalization") or {}
    class_ = (resource.get("class") or {})
    class_code = (class_.get("coding") or [{}])[0].get("code") if class_.get("coding") else None

    def _ts(v: str | None) -> datetime | None:
        return datetime.fromisoformat(v.replace("Z", "+00:00")) if v else None

    return {
        "logical_id": resource.get("id"),
        "status": resource.get("status") or "unknown",
        "class_": class_code,
        "period_start": _ts(period.get("start")),
        "period_end": _ts(period.get("end")),
        "admission_source": (hospitalization.get("admitSource") or {}).get("code"),
        "discharge_disposition": (hospitalization.get("dischargeDisposition") or {}).get("code"),
    }


def project_observation(resource: dict[str, Any]) -> dict[str, Any]:
    code_system, code_value, code_display = _first_coding(resource.get("code"))
    value = resource.get("valueQuantity") or {}
    interpretation = (resource.get("interpretation") or [{}])[0] or {}
    interp_code = (interpretation.get("coding") or [{}])[0].get("code")

    effective = resource.get("effectiveDateTime")
    if effective is None:
        effective = (resource.get("effectivePeriod") or {}).get("start")
    effective_at = (
        datetime.fromisoformat(effective.replace("Z", "+00:00")) if effective else None
    )

    return {
        "logical_id": resource.get("id"),
        "effective_at": effective_at,
        "code_system": code_system or "",
        "code_value": code_value or "",
        "code_display": code_display,
        "value_quantity": value.get("value"),
        "value_unit": value.get("unit"),
        "interpretation": interp_code,
        "status": resource.get("status") or "unknown",
    }


def project_condition(resource: dict[str, Any]) -> dict[str, Any]:
    code_system, code_value, code_display = _first_coding(resource.get("code"))
    clinical = (resource.get("clinicalStatus") or {}).get("coding") or []
    clinical_code = clinical[0].get("code") if clinical else None

    def _date(v: str | None) -> date | None:
        return date.fromisoformat(v[:10]) if v else None

    onset = resource.get("onsetDateTime")
    abatement = resource.get("abatementDateTime")

    return {
        "logical_id": resource.get("id"),
        "code_system": code_system or "",
        "code_value": code_value or "",
        "code_display": code_display,
        "clinical_status": clinical_code,
        "onset_date": _date(onset),
        "abatement_date": _date(abatement),
    }


def project_medication_request(resource: dict[str, Any]) -> dict[str, Any]:
    dm_d_system, dm_d_code, dm_d_display = _first_coding(resource.get("medicationCodeableConcept"))
    dosage = (resource.get("dosageInstruction") or [{}])[0] or {}

    authored = resource.get("authoredOn")
    return {
        "logical_id": resource.get("id"),
        "dm_d_code": dm_d_code,
        "dm_d_display": dm_d_display,
        "status": resource.get("status") or "unknown",
        "authored_on": date.fromisoformat(authored[:10]) if authored else None,
        "dosage_text": dosage.get("text"),
    }


PROJECTORS = {
    "Patient": project_patient,
    "Encounter": project_encounter,
    "Observation": project_observation,
    "Condition": project_condition,
    "MedicationRequest": project_medication_request,
}


def build_projection(resource_type: str, resource: dict[str, Any]) -> dict[str, Any] | None:
    project = PROJECTORS.get(resource_type)
    if project is None:
        return None
    return project(resource)
