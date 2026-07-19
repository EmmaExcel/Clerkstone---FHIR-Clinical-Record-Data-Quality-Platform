# Clerkstone — Data Model (realistic admission & patient fields)

> How Clerkstone models patient and admission data realistically, informed by the **NHS England
> Synthetic Clinical Notes** dataset's `patients.csv` and `admissions.csv`. Companion documents:
> [DATA_LICENCES.md](./DATA_LICENCES.md) · [architecture.md](./architecture.md) ·
> [DATA_MINIMISATION.md](./DATA_MINIMISATION.md).

## 1. Purpose

Synthea's default output is **US-shaped**: US identifiers, US geography, US admission structures.
Clerkstone post-processes it to be **NHS-shaped**, and this document records the target field model —
what a real NHS admissions record looks like — so the `Encounter` and `Patient` projections are
realistic rather than a naive re-labelling.

The field model is informed by the NHS England Synthetic Clinical Notes dataset:

- `patients.csv` → `nhs_number`, `gender_identity`, `person_id`
- `admissions.csv` → `admission_method`, `bed_location`, `site_name`, `ward`, `admission_title`

## 2. Patient fields

| Field | Type | Source of realism | Notes |
|---|---|---|---|
| `nhs_number` | text (10 digits) | NHS Number standard | Synthetic, reserved `99…` range, valid modulus-11 check digit (`IDENT-003`). |
| `nhs_number_status` | `verified \| unverified \| absent` | NHS Number `extension` | A **quality signal**: whether the number was check-digit-verified at ingest. |
| `family_name` | text | `Patient.name.family` | — |
| `given_names` | text[] | `Patient.name.given` | — |
| `birth_date` | date | `Patient.birthDate` | Drives `TEMP-*` temporal rules and age computation. |
| `gender` | `male \| female \| other \| unknown` (FHIR `AdministrativeGender`) | — | **See the gender_identity note below.** |
| `deceased` | boolean | `Patient.deceased` | `TEMP-006` needs it. |
| `postcode` | text | outward code only | Minimised per [DATA_MINIMISATION.md](./DATA_MINIMISATION.md). |

### 2.1 The `gender_identity` mismatch (a real design decision)

The NHS England dataset's `patients.csv` carries **`gender_identity`**, which is **more granular
than FHIR's `AdministrativeGender`** (a 4-value code). This is a genuine, known interoperability
friction: UK datasets increasingly distinguish *gender identity* (self-identified) from
*administrative sex*.

Clerkstone's decision, recorded here rather than papered over:

- The FHIR `Patient.gender` slot holds **administrative sex** (`male/female/other/unknown`), per the
  UK Core bound value set.
- A richer **gender identity** value, where present in source data, is preserved in a
  **`genderIdentity` extension** on the resource, **not** projected onto `Patient.gender`.
- The projection keeps only the administrative `gender` (for bound-value-set validation), while the
  full resource retains the extension for fidelity.

This is the "FHIR for fidelity; relational for query" split applied to a sensitive field — the
projection stores what the rules need, the resource keeps what the record actually said.

## 3. Admission / encounter fields

| Field | Type | NHS `admissions.csv` analogue | FHIR `Encounter` slot |
|---|---|---|---|
| `admission_method` | text | `admission_method` | `Encounter.hospitalization.admitSource` (mapped) |
| `site_name` | text | `site_name` | `Encounter.serviceProvider` → `Organization` (with ODS code) |
| `ward` | text | `ward` | `Encounter.location` |
| `bed_location` | text | `bed_location` | `Encounter.location` (detail) |
| `admission_title` | text | `admission_title` | `Encounter.class` display (human-readable) |
| `class` | `inpatient \| outpatient \| emergency \| ambulatory` | derived | `Encounter.class` |
| `period_start` / `period_end` | timestamptz | — | `Encounter.period` (drives `TEMP-003`) |
| `admission_source` | text | `admission_method` | `Encounter.hospitalization.admitSource` |
| `discharge_disposition` | text | — | `Encounter.hospitalization.dischargeDisposition` |

### 3.1 Why these fields, not more

The projection stores exactly the fields a quality rule or the timeline needs:

- `period_start`/`period_end` → `TEMP-003` (end before start), the timeline's ordering.
- `class` → timeline display and duplication rules.
- `site_name`/`ward`/`bed_location` → realistic NHS admission structure on the timeline, and a
  **provenance anchor** (which organisation/site a record belongs to).

Everything else (full `Encounter.hospitalization` structure, participant lists, `identifier`
history) stays in the JSONB resource and is re-emitted on `$export`.

## 4. The projection vs resource split (recap)

| Stays in the FHIR resource (JSONB) | Projected to relational columns |
|---|---|
| Full `name`, `telecom`, `contact`, extensions (`genderIdentity`) | `family_name`, `given_names` |
| Full address history | `postcode` (outward code only) |
| Full `Encounter.hospitalization`, participants, `identifier[]` | `admission_method`, `site_name`, `ward`, `bed_location`, `class`, `period_start/end` |
| Provenance, `meta.security`, `meta.profile` | — |

## 5. Provenance of the field model

- Structural realism: **NHS England Synthetic Clinical Notes** (`admissions.csv`, `patients.csv`),
  MIT licence — see [DATA_LICENCES.md](./DATA_LICENCES.md).
- The fields above are **documented from that dataset's structure**; the actual values in Clerkstone
  are generated by Synthea + the UK-isation script and the corruption harness — never copied from the
  NHS dataset.
- `gender_identity` handling is Clerkstone's own design decision, stated here because it is the kind
  of nuance an integration lead would probe.
