from __future__ import annotations

import pytest
from app.domain.hl7v2.to_fhir import adt_to_fhir_bundle

_ADT_A01 = (
    "MSH|^~\\&|EPIC|HOSP|CLERKSTONE|HOSP|20260925090000||ADT^A01|MSG00001|P|2.5|\r"
    "PID|1||9900000019^^^NHS^NH||Smith^Alice^Mary||19800301|F|||123 Fake Street^^Manchester^^M13 9PL^GB^H||\r"
    "PV1|1|I|Ward1^Room1^Bed1^HOSP||||1234^Jones^Bob^|||MED|||||||||||||||||||||||||20260925090000\r"
)


def _pv1(
    patient_class: str = "I",
    location: str = "Ward1^Room1^Bed1^HOSP",
    admit: str | None = None,
    discharge: str | None = None,
) -> str:
    """Build a PV1 segment with fields at the correct HL7 positions."""
    fields = [""] * 46  # indices 0..45
    fields[0] = "PV1"
    fields[1] = "1"
    fields[2] = patient_class
    fields[3] = location
    fields[44] = admit or ""
    fields[45] = discharge or ""
    return "|".join(fields)


_ADT_A03 = (
    "MSH|^~\\&|EPIC|HOSP|CLERKSTONE|HOSP|20260928090000||ADT^A03|MSG00002|P|2.5|\r"
    "PID|1||9900000027^^^NHS^NH||Patel^Raj||19750515|M\r"
    + _pv1(patient_class="I", location="Ward2^Room2^Bed2^HOSP",
           admit="20260925090000", discharge="20260928090000")
    + "\r"
)

_ADT_A08 = (
    "MSH|^~\\&|EPIC|HOSP|CLERKSTONE|HOSP|20260927090000||ADT^A08|MSG00003|P|2.5|\r"
    "PID|1||9900000035^^^NHS^NH||O'Brien^Niamh||19901010|F\r"
    "PV1|1|O|ClinicA^^^HOSP||||9999^Doc^Jane^|||GEN|||||||||||||||||||||||||20260927090000\r"
)

_ADT_MALE = (
    "MSH|^~\\&|EPIC|HOSP|CLERKSTONE|HOSP|20260925090000||ADT^A01|MSG00004|P|2.5|\r"
    "PID|1||9900000043^^^NHS^NH||Hussain^Omar^Ali||19650101|M\r"
    "PV1|1|E|ED^Room3^Bed3^HOSP||||5555^Doc^Sam^|||EMER|||||||||||||||||||||||||20260925090000\r"
)

_ADT_NO_NHS = (
    "MSH|^~\\&|EPIC|HOSP|CLERKSTONE|HOSP|20260925090000||ADT^A01|MSG00005|P|2.5|\r"
    "PID|1||||Jones^Grace||19850707|F\r"
    "PV1|1|I|Ward1^Room1^Bed1^HOSP||||1234^Jones^Bob^|||MED|||||||||||||||||||||||||20260925090000\r"
)

_MALFORMED_MISSING_MSH = "PID|1||9900000019^^^NHS^NH||Smith^Alice||19800301|F\r"

_MALFORMED_EMPTY = ""

_MALFORMED_TRUNCATED = "MSH|^~\\&|EPIC|HOSP|CLERKSTONE|HOSP|20260925090000||ADT^A01|\rPID|1\r"


def _entry(bundle: dict, resource_type: str) -> dict:
    return next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == resource_type)


class TestAdtToFhir:
    def test_a01_admit_maps_patient(self):
        bundle = adt_to_fhir_bundle(_ADT_A01)
        patient = _entry(bundle, "Patient")
        assert patient["identifier"][0]["system"] == "https://fhir.nhs.uk/Id/nhs-number"
        assert patient["identifier"][0]["value"] == "9900000019"
        assert patient["name"][0]["family"] == "Smith"
        assert patient["name"][0]["given"] == ["Alice"]
        assert patient["gender"] == "female"
        assert patient["birthDate"] == "1980-03-01"
        assert patient["address"][0]["postalCode"] == "M13 9PL"

    def test_a01_encounter_status_and_class(self):
        encounter = _entry(adt_to_fhir_bundle(_ADT_A01), "Encounter")
        assert encounter["status"] == "in-progress"
        assert encounter["class"]["code"] == "inpatient"

    def test_a03_discharge_finished(self):
        encounter = _entry(adt_to_fhir_bundle(_ADT_A03), "Encounter")
        assert encounter["status"] == "finished"
        assert encounter["period"]["start"] is not None
        assert encounter["period"]["end"] is not None

    def test_a08_update_stays_in_progress(self):
        encounter = _entry(adt_to_fhir_bundle(_ADT_A08), "Encounter")
        assert encounter["status"] == "in-progress"
        assert encounter["class"]["code"] == "outpatient"

    def test_male_gender(self):
        patient = _entry(adt_to_fhir_bundle(_ADT_MALE), "Patient")
        assert patient["gender"] == "male"
        assert patient["name"][0]["given"] == ["Omar"]

    def test_no_nhs_number(self):
        patient = _entry(adt_to_fhir_bundle(_ADT_NO_NHS), "Patient")
        assert patient["identifier"] == []
        assert patient["name"][0]["family"] == "Jones"


class TestMalformedMessages:
    @pytest.mark.parametrize("message", [_MALFORMED_MISSING_MSH, _MALFORMED_EMPTY])
    def test_malformed_raises_value_error(self, message):
        with pytest.raises(ValueError):
            adt_to_fhir_bundle(message)
