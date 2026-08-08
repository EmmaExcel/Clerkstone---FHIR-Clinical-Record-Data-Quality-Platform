from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from synthesise import uk_ise_bundle  # noqa: E402


def _us_patient() -> dict:
    return {
        "resourceType": "Patient",
        "id": "p1",
        "identifier": [{"system": "http://hl7.org/fhir/sid/us-ssn", "value": "123-45-6789"}],
        "name": [{"family": "Smith", "given": ["Alice"]}],
        "address": [{"postalCode": "02139", "city": "Boston", "country": "US"}],
    }


def test_uk_ise_replaces_identifier_and_address():
    bundle = {"resourceType": "Bundle", "type": "transaction",
              "entry": [{"resource": _us_patient()}]}
    uk_ise_bundle(bundle, seed=42)
    patient = bundle["entry"][0]["resource"]
    assert patient["identifier"][0]["system"] == "https://fhir.nhs.uk/Id/nhs-number"
    assert patient["identifier"][0]["value"].startswith("99")  # reserved test range
    assert patient["address"][0]["country"] == "GB"
    assert patient["meta"]["profile"] == [
        "https://fhir.hl7.org.uk/StructureDefinition/UKCore-Patient"
    ]


def test_uk_ise_remaps_rxnorm_medication():
    bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {"resource": {
                "resourceType": "MedicationRequest",
                "id": "m1",
                "status": "active",
                "medicationCodeableConcept": {
                    "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                                "code": "1191", "display": "aspirin"}]
                },
            }}
        ],
    }
    uk_ise_bundle(bundle, seed=42)
    coding = bundle["entry"][0]["resource"]["medicationCodeableConcept"]["coding"][0]
    assert coding["system"] == "https://dmd.nhs.uk/"
    assert coding["code"] == "317935006"
