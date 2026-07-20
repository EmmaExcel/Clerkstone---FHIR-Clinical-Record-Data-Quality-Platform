# Clerkstone — HL7 v2 → FHIR Mapping (ADT)

> How the `hl7v2` module converts HL7 v2 **ADT** messages to FHIR R4 `Patient`/`Encounter` (and, on
> ADT^A08, a patient update). This closes the HL7/FHIR pairing named by NHS integration roles.
> Companion documents: [API_GUIDE.md](./API_GUIDE.md) · [architecture.md](./architecture.md).

## 1. Supported message types

| Message | Event | Effect on FHIR |
|---|---|---|
| **ADT^A01** | Admit/visit notification | Create `Patient` (if absent) + create `Encounter` (status `arrived`/`in-progress`) |
| **ADT^A03** | Discharge/end visit | Set `Encounter.period.end` and `Encounter.status = finished` |
| **ADT^A08** | Update patient information | Update `Patient` demographics; no encounter change |

A small, deliberately-bounded set (spec §7): enough to demonstrate a real integration, not a
full HL7 v2 stack. After conversion, every resource flows through the **same** validation and
quality rules as directly-ingested FHIR — that is the point: one governance path for two wire formats.

## 2. Segment → element mapping

### 2.1 MSH — message header → provenance / meta

| HL7 field | Content | FHIR target |
|---|---|---|
| MSH-7 | Date/time of message | `Provenance.recorded` / `meta.lastUpdated` |
| MSH-3 / MSH-4 | Sending application / facility | `Provenance.agent` (role: author) |
| MSH-5 / MSH-6 | Receiving application / facility | `Provenance.agent` (role: custodian) |
| MSH-9 | Message type (`ADT^A01`) | determines the operation applied |
| MSH-10 | Message control ID | `Bundle.id` / idempotency key |

### 2.2 PID — patient identification → `Patient`

| HL7 field | Content | FHIR target |
|---|---|---|
| PID-3 | Patient identifier list | `Patient.identifier` (system mapped by the ID's assigning authority, e.g. `https://fhir.nhs.uk/Id/nhs-number`) |
| PID-5 | Patient name (family, given) | `Patient.name` (family / given) |
| PID-7 | Date/time of birth | `Patient.birthDate` |
| PID-8 | Administrative sex | `Patient.gender` (see mapping below) |
| PID-11 | Address | `Patient.address` (projections store **outward postcode only** — see [DATA_MINIMISATION.md](./DATA_MINIMISATION.md)) |
| PID-13 | Phone/telecom | `Patient.telecom` |
| PID-29 | Date/time of death | `Patient.deceasedDateTime` |
| PID-30 | Patient death indicator | `Patient.deceasedBoolean` |
| PID-3 (NHS number) | modulus-11 check | validated by `IDENT-003` after mapping |

**PID-8 → `Patient.gender` (FHIR `AdministrativeGender`):**

| PID-8 | FHIR |
|---|---|
| `F` | `female` |
| `M` | `male` |
| `O` | `other` |
| `U` / empty | `unknown` |

### 2.3 PV1 — patient visit → `Encounter`

| HL7 field | Content | FHIR target |
|---|---|---|
| PV1-2 | Patient class | `Encounter.class` (see mapping below) |
| PV1-3 | Assigned patient location | `Encounter.location` |
| PV1-7 | Attending doctor | `Encounter.participant` (role: `attender`) |
| PV1-19 | Visit number | `Encounter.identifier` |
| PV1-44 | Admit date/time | `Encounter.period.start` |
| PV1-45 | Discharge date/time | `Encounter.period.end` |
| PV1-14 | Admit source | `Encounter.hospitalization.admitSource` |
| PV1-36 | Discharge disposition | `Encounter.hospitalization.dischargeDisposition` |

**PV1-2 → `Encounter.class`:**

| PV1-2 | FHIR |
|---|---|
| `I` | `inpatient` |
| `O` | `outpatient` |
| `E` | `emergency` |
| `B` | `obstetrics` |
| `P` | `preadmit` |
| `R` / `C` / `N` | `ambulatory` (with a note) |

### 2.4 Optional segments

| Segment | FHIR target |
|---|---|
| AL1 (allergy) | `AllergyIntolerance` |
| DG1 (diagnosis) | `Condition` |
| NK1 (next of kin) | `Patient.contact` |
| PR1 (procedure) | `Procedure` |

Only AL1/DG1/NK1/PR1 are mapped in the MVP; other segments are ignored explicitly (not silently
dropped) so the converter can report what it did **not** map.

## 3. Worked example — ADT^A01

### Input message

```hl7
MSH|^~\&|SENDAPP|SENDFAC|RECAPP|RECFAC|20260901090200||ADT^A01|MSG000123|P|2.5
EVN|A01|20260901090200
PID|1||9900000001^^^NHS^NH||Okonkwo^Amara||19580311|F|||14 Cherry Tree Lane^Leeds^LS1 1AB||||||
PV1|1|E|A&E^Cubicle 4^||||||||||||||||||||A01
```

### Output FHIR (summarised)

```json
{
  "resourceType": "Patient",
  "id": "9900000001-19580311",   // derived, stable; replaced by logical id on ingest
  "identifier": [{ "system": "https://fhir.nhs.uk/Id/nhs-number", "value": "9900000001" }],
  "name": [{ "family": "Okonkwo", "given": ["Amara"] }],
  "birthDate": "1958-03-11",
  "gender": "female",
  "address": [{ "postalCode": "LS1", "country": "GB" }]
}
```

```json
{
  "resourceType": "Encounter",
  "status": "arrived",
  "class": { "code": "emergency" },
  "identifier": [{ "value": "MSG000123" }],
  "subject": { "reference": "Patient/9900000001-19580311" },
  "period": { "start": "2026-09-01T09:02:00Z" },
  "location": [{ "location": { "display": "A&E Cubicle 4" } }]
}
```

> Note: `PID-11` stores the full address on the FHIR resource, but the relational `patient`
> projection retains **only the outward postcode** (`LS1`), per the data-minimisation rule.

## 4. Event-type specifics

### ADT^A03 (discharge)

- Requires `PV1-45` (discharge date/time). If absent, the converter emits a **warning** finding
  (the discharge has no end time) rather than silently fabricating one.
- Sets `Encounter.status = finished`, `Encounter.period.end = PV1-45`.
- Matches the existing encounter by `PV1-19` (visit number) / `PID-3` (patient id).

### ADT^A08 (update)

- Updates `Patient` demographics only; no `Encounter` is created or changed.
- If the message changes the NHS number, `IDENT-005` (duplicate) and `IDENT-003` (check digit) are
  re-evaluated on the updated identifier before the update is accepted.

## 5. Contract tests

Eight sample ADT messages (spec §18), including three malformed ones, assert field-by-field output:

| Fixture | Purpose |
|---|---|
| `adt_a01_admit.hl7` | Full admit → Patient + Encounter |
| `adt_a03_discharge.hl7` | Discharge → period.end + status |
| `adt_a08_update.hl7` | Patient update, no encounter change |
| `adt_a01_no_pv1.hl7` | A01 with missing PV1 → Patient only + warning |
| `adt_a03_missing_pv145.hl7` | Discharge without end time → warning finding |
| `adt_malformed_msh.hl7` | Malformed MSH → `OperationOutcome` error |
| `adt_malformed_pid.hl7` | Malformed PID → error, no partial write |
| `adt_malformed_encoding.hl7` | Non-UTF-8 encoding → `STRUCT-004` mojibake detection |

## 6. Honest limits

- This maps a **representative subset** of ADT, not the full HL7 v2 specification (no PV2, IN1,
  GT1, ROL, etc. in the MVP). Unmapped segments are recorded, not silently dropped.
- `python-hl7` is a parser, not a validation engine: message-level conformance checking is
  deliberately left to the **post-conversion FHIR validation**, so a bad ADT message fails in the
  same governed way as a bad FHIR bundle.
