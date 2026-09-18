"""Generate synthetic, UK-flavoured FHIR R4 patients.

Deterministic (seeded) by default so the committed fixture is reproducible.
Produces a single transaction Bundle. Two modes:

- ``python`` (default): pure-Python generator, no Java required — used for the
  committed fixture and CI.
- ``synthea``: run the Synthea simulator (needs Java 17 + the Synthea JAR) and
  then UK-ise its output. This is the "real" path; see docs/DATA_LICENCES.md.

All data is synthetic. NHS numbers use the reserved 99-prefix test range with a
valid modulus-11 check digit. SNOMED CT / dm+d codes come from the committed
illustrative subset (data/terminology/subset.json).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.domain.fhir.nhs import make_valid_nhs_number  # noqa: E402

SNOMED = "http://snomed.info/sct"
DMD = "https://dmd.nhs.uk/"
NHS_NUMBER_SYSTEM = "https://fhir.nhs.uk/Id/nhs-number"
UKCORE_PATIENT = "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Patient"

_FAMILIES = ["Smith", "Patel", "Jones", "Okonkwo", "Khan", "Williams", "Murphy", "O'Brien", "Chukwu", "Hussain"]
_GIVEN = ["Amara", "Oliver", "Grace", "Noah", "Priya", "Ade", "Isobel", "Dylan", "Nadia", "Thomas"]
_CITIES = [("Manchester", "M13"), ("Leeds", "LS1"), ("Birmingham", "B15"), ("Cardiff", "CF10"), ("Glasgow", "G12")]

_VITALS = [
    ("271649006", "Systolic blood pressure", 120, 8, "mm[Hg]"),
    ("271650006", "Diastolic blood pressure", 78, 6, "mm[Hg]"),
    ("364075005", "Heart rate", 72, 8, "beats/min"),
    ("431314004", "Peripheral oxygen saturation", 98, 1, "%"),
    ("386725007", "Body temperature", 36.7, 0.2, "degC"),
    ("27113001", "Body weight", 78, 5, "kg"),
    ("50373000", "Body height", 170, 6, "cm"),
    ("86290005", "Respiratory rate", 16, 2, "/min"),
]
_CONDITIONS = [
    ("44054006", "Diabetes mellitus"),
    ("38341003", "Hypertensive disorder"),
    ("195967001", "Asthma"),
    ("73211009", "Diabetes mellitus type 2"),
    ("56265001", "Heart disease"),
    ("13645005", "Chronic obstructive lung disease"),
]
_MEDS = [
    ("317935006", "Aspirin 75mg tablet"),
    ("324328004", "Atorvastatin 20mg tablet"),
    ("317942005", "Ramipril 2.5mg capsule"),
    ("321278003", "Metformin 500mg tablet"),
    ("319713008", "Salbutamol 100micrograms inhaler"),
    ("318330008", "Lisinopril 10mg tablet"),
]


def _nhs_number(rng) -> str:
    while True:
        prefix = "99" + "".join(str(rng.randint(0, 9)) for _ in range(7))
        try:
            return make_valid_nhs_number(prefix)
        except ValueError:
            continue


def _identifier(nhs_number: str) -> dict:
    return {
        "system": NHS_NUMBER_SYSTEM,
        "value": nhs_number,
        "extension": [
            {
                "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-NHSNumberVerificationStatus",
                "valueCodeableConcept": {"coding": [{"system": "https://fhir.hl7.org.uk/CodeSystem/UKCore-NHSNumberVerificationStatus", "code": "01"}]},
            }
        ],
    }


def _make_patient(rng, idx: int, nhs_number: str) -> dict:
    family = rng.choice(_FAMILIES)
    given = rng.choice(_GIVEN)
    city, outward = rng.choice(_CITIES)
    year = rng.randint(1935, 2005)
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    return {
        "resourceType": "Patient",
        "id": f"p-{idx:05d}",
        "meta": {"profile": [UKCORE_PATIENT]},
        "identifier": [_identifier(nhs_number)],
        "name": [{"family": family, "given": [given]}],
        "gender": rng.choice(["female", "male"]),
        "birthDate": f"{year:04d}-{month:02d}-{day:02d}",
        "address": [{"postalCode": f"{outward} {rng.randint(1,9)}AB", "city": city, "country": "GB"}],
    }


def _make_encounter(rng, patient_id: str, idx: int) -> dict:
    hour = rng.randint(0, 23)
    start = f"2026-{rng.randint(1, 8):02d}-{rng.randint(1, 28):02d}T{hour:02d}:{rng.randint(0, 59):02d}:00Z"
    cls = rng.choice(["inpatient", "outpatient", "emergency", "ambulatory"])
    return {
        "resourceType": "Encounter",
        "id": f"enc-{patient_id}-{idx}",
        "meta": {"profile": ["https://fhir.hl7.org.uk/StructureDefinition/UKCore-Encounter"]},
        "status": "finished",
        "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": cls},
        "subject": {"reference": f"Patient/{patient_id}"},
        "period": {"start": start},
    }


def _make_observation(rng, patient_id: str, encounter_id: str, idx: int) -> dict:
    code, display, mean, sd, unit = rng.choice(_VITALS)
    value = round(rng.gauss(mean, sd), 1)
    if code == "431314004":  # SpO2: avoid the 100 sentinel value
        value = min(value, 99.0)
    return {
        "resourceType": "Observation",
        "id": f"obs-{patient_id}-{idx}",
        "meta": {"profile": ["https://fhir.hl7.org.uk/StructureDefinition/UKCore-Observation"]},
        "status": "final",
        "code": {"coding": [{"system": SNOMED, "code": code, "display": display}]},
        "subject": {"reference": f"Patient/{patient_id}"},
        "encounter": {"reference": f"Encounter/{encounter_id}"},
        "effectiveDateTime": f"2026-{rng.randint(1,8):02d}-{rng.randint(1,28):02d}T{rng.randint(0,23):02d}:{rng.randint(0,59):02d}:00Z",
        "valueQuantity": {"value": value, "unit": unit, "system": "http://unitsofmeasure.org", "code": unit},
    }


def _make_condition(rng, patient_id: str, idx: int) -> dict:
    code, display = rng.choice(_CONDITIONS)
    return {
        "resourceType": "Condition",
        "id": f"cond-{patient_id}-{idx}",
        "meta": {"profile": ["https://fhir.hl7.org.uk/StructureDefinition/UKCore-Condition"]},
        "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
        "code": {"coding": [{"system": SNOMED, "code": code, "display": display}]},
        "subject": {"reference": f"Patient/{patient_id}"},
        "onsetDateTime": f"2020-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}T00:00:00Z",
    }


def _make_medication(rng, patient_id: str, idx: int) -> dict:
    code, display = rng.choice(_MEDS)
    return {
        "resourceType": "MedicationRequest",
        "id": f"med-{patient_id}-{idx}",
        "meta": {"profile": ["https://fhir.hl7.org.uk/StructureDefinition/UKCore-MedicationRequest"]},
        "status": "active",
        "intent": "order",
        "medicationCodeableConcept": {"coding": [{"system": DMD, "code": code, "display": display}]},
        "subject": {"reference": f"Patient/{patient_id}"},
        "authoredOn": f"2026-{rng.randint(1,8):02d}-{rng.randint(1,28):02d}",
        "dosageInstruction": [{"text": "Take as directed (illustrative)"}],
    }


def generate_bundle(count: int, seed: int) -> dict:
    rng = __import__("random").Random(seed)
    entries = []
    for i in range(count):
        patient_id = f"p-{i:05d}"
        nhs = _nhs_number(rng)
        patient = _make_patient(rng, i, nhs)
        entries.append({"fullUrl": f"urn:uuid:{patient_id}", "resource": patient,
                        "request": {"method": "POST", "url": "Patient"}})
        n_enc = rng.randint(2, 5)
        for e in range(n_enc):
            enc_id = f"enc-{patient_id}-{e}"
            entries.append({"fullUrl": f"urn:uuid:{enc_id}",
                            "resource": _make_encounter(rng, patient_id, e),
                            "request": {"method": "POST", "url": "Encounter"}})
            for o in range(rng.randint(2, 5)):
                entries.append({"fullUrl": f"urn:uuid:obs-{patient_id}-{e}-{o}",
                                "resource": _make_observation(rng, patient_id, enc_id, f"{e}-{o}"),
                                "request": {"method": "POST", "url": "Observation"}})
        conditions = []
        for c in range(rng.randint(1, 3)):
            cond = _make_condition(rng, patient_id, c)
            conditions.append(cond)
            entries.append({"fullUrl": f"urn:uuid:cond-{patient_id}-{c}",
                            "resource": cond,
                            "request": {"method": "POST", "url": "Condition"}})
        # Diabetic patients get an HbA1c observation (cohort completeness).
        if any((cc["code"]["coding"][0]["code"]) in ("44054006", "73211009") for cc in conditions):
            hba1c = {
                "resourceType": "Observation",
                "id": f"hba1c-{patient_id}",
                "meta": {"profile": ["https://fhir.hl7.org.uk/StructureDefinition/UKCore-Observation"]},
                "status": "final",
                "code": {"coding": [{"system": SNOMED, "code": "43396009", "display": "Hemoglobin A1c"}]},
                "subject": {"reference": f"Patient/{patient_id}"},
                "effectiveDateTime": f"2026-{rng.randint(1,8):02d}-{rng.randint(1,28):02d}T00:00:00Z",
                "valueQuantity": {"value": round(rng.uniform(42, 75), 1), "unit": "mmol/mol",
                                  "system": "http://unitsofmeasure.org", "code": "mmol/mol"},
            }
            entries.append({"fullUrl": f"urn:uuid:hba1c-{patient_id}", "resource": hba1c,
                            "request": {"method": "POST", "url": "Observation"}})
        for m in range(rng.randint(1, 4)):
            entries.append({"fullUrl": f"urn:uuid:med-{patient_id}-{m}",
                            "resource": _make_medication(rng, patient_id, m),
                            "request": {"method": "POST", "url": "MedicationRequest"}})
    return {"resourceType": "Bundle", "type": "transaction", "entry": entries}


_UKCORE_PROFILES = {
    "Patient": "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Patient",
    "Encounter": "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Encounter",
    "Observation": "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Observation",
    "Condition": "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Condition",
    "MedicationRequest": "https://fhir.hl7.org.uk/StructureDefinition/UKCore-MedicationRequest",
}

# Illustrative RxNorm -> dm+d mapping for a few common Synthea medications.
# NOT an official NHS mapping; see docs/DATA_LICENCES.md.
_RXNORM_TO_DMD = {
    "1191": ("317935006", "Aspirin 75mg tablet"),      # aspirin
    "153165": ("324328004", "Atorvastatin 20mg tablet"),  # atorvastatin
    "860975": ("321278003", "Metformin 500mg tablet"),  # metformin
    "68442": ("319713008", "Salbutamol 100micrograms inhaler"),  # albuterol/salbutamol
}


def uk_ise_bundle(bundle: dict, seed: int = 42) -> dict:
    """UK-ise a Synthea (US-flavoured) FHIR bundle: NHS numbers, UK postcodes,
    UK Core profiles, and an illustrative medication-code remap."""
    import random

    rng = random.Random(seed)
    for entry in bundle.get("entry") or []:
        resource = entry.get("resource") or {}
        rt = resource.get("resourceType")
        if rt == "Patient":
            resource["identifier"] = [_identifier(_nhs_number(rng))]
            for addr in resource.get("address") or []:
                outward, city = rng.choice(_CITIES)
                addr["postalCode"] = f"{outward} {rng.randint(1, 9)}AB"
                addr["country"] = "GB"
        elif rt == "MedicationRequest":
            _remap_medication(resource)
        profile = _UKCORE_PROFILES.get(rt)
        if profile:
            resource.setdefault("meta", {})["profile"] = [profile]
    return bundle


def _remap_medication(resource: dict) -> None:
    coding = (resource.get("medicationCodeableConcept") or {}).get("coding") or []
    for c in coding:
        if c.get("system") == "http://www.nlm.nih.gov/research/umls/rxnorm":
            mapped = _RXNORM_TO_DMD.get(c.get("code"))
            if mapped:
                c["system"] = DMD
                c["code"] = mapped[0]
                c["display"] = mapped[1]


def _run_synthea(count: int, seed: int, out: Path) -> None:
    import subprocess

    jar = Path("scripts/synthea/synthea-with-dependencies.jar")
    if not jar.exists():
        print("Synthea JAR not found. Run: bash scripts/fetch_synthea.sh", file=sys.stderr)
        sys.exit(1)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.parent / "synthea_raw"
    subprocess.run(
        ["java", "-jar", str(jar), "-p", str(count), "-s", str(seed),
         "--exporter.fhir.export", "true", "--exporter.baseDirectory", str(tmp)],
        check=True,
    )
    # Synthea writes one FHIR bundle per patient under tmp/fhir/.
    fhir_dir = tmp / "fhir"
    entries: list[dict] = []
    for f in sorted(fhir_dir.glob("*.json")):
        raw = json.loads(f.read_text())
        uk_ise_bundle(raw, seed)
        entries.extend(raw.get("entry") or [])
    combined = {"resourceType": "Bundle", "type": "transaction", "entry": entries}
    out.write_text(json.dumps(combined, indent=2))
    print(f"wrote {count} Synthea patients ({len(entries)} resources) to {out}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("data/generated/patients.json"))
    parser.add_argument("--source", choices=["python", "synthea"], default="python")
    args = parser.parse_args()

    if args.source == "synthea":
        _run_synthea(args.count, args.seed, args.out)
        return

    bundle = generate_bundle(args.count, args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(bundle, indent=2))
    n = len(bundle["entry"])
    print(f"wrote {args.count} patients ({n} resources) to {args.out}")


if __name__ == "__main__":
    main()
