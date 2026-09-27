# Clerkstone - Taxonomy of Clinical-Data Defects

> **This is the core document of the project.** It catalogues the ways clinical data actually goes
> wrong during EPR migration and integration, and maps each defect to (a) its real-world cause,
> (b) a concrete worked example, and (c) the deterministic rule(s) that detect it. Every defect
> family is seeded into the corruption harness (`scripts/corrupt.py`) at the frequencies in §15, and
> every rule has positive/negative/boundary tests plus a golden-file regression fixture.

The organising idea: **a data-quality gateway is only as good as its taxonomy.** A rule engine that
checks "date is present" is noise. A rule engine that knows *"an encounter whose period ends before
it starts is usually a local-time-vs-UTC migration artefact"* is actionable - and that is the
difference this document exists to demonstrate.

---

## 1. The defect families at a glance

| # | Family | Signature defect | Primary rules | Typical severity |
|---|---|---|---|---|
| 1 | Timezone / migration artefacts | `period.end` before `period.start` | `TEMP-003` | error |
| 2 | Impossible date sequences | birth in future; death before birth; observation after death | `TEMP-004`, `TEMP-005`, `TEMP-006` | error |
| 3 | Decimal-point transcription errors | systolic BP recorded as `1420` | `PHYS-001` | error |
| 4 | Sentinel values | `SpO₂ = 0` as "not recorded" | `PHYS-004` | error/warning |
| 5 | Retired terminology | concept used after its retirement date | `TERM-005` | error/warning |
| 6 | Local-code drift | trust-local code with no national mapping | `TERM-001`, `TERM-002` | error |
| 7 | Mojibake / encoding corruption | `Jáuregui` → `JÃ¡uregui` | `STRUCT-004` | warning |
| 8 | Duplicate identifiers | same NHS number on two patients | `IDENT-003`, `IDENT-005` | error |
| 9 | Dangling references | `Observation.subject` → absent patient | `REF-001`, `REF-003` | error |
| 10 | Identifier check-digit failures | NHS number fails modulus-11 | `IDENT-003` | error |
| 11 | Display/term disagreement | display text ≠ resolved term | `TERM-004` | warning |
| 12 | Duplicate records | same patient/code/time/value | `DUP-002` | warning |
| 13 | Cohort completeness gaps | diabetes diagnosis, no HbA1c in 24 months | `COH-001`, `COH-002` | info/warning |
| 14 | Structural corruption | truncated JSON; missing `meta.profile` | `STRUCT-001`, `PROF-002` | error |

---

## 2. The families, in detail

### 2.1 Timezone / migration artefacts (`TEMP-003`)

**What it is.** Timestamps recorded in two different time conventions within the same record -
typically local wall-clock time on the source system and UTC (or vice-versa) after migration. A
record migrated from a system using local time often gains or loses an hour, or a midnight-boundary
date flips.

**Real-world causes.**

- A source EPR stored `local_time` with no timezone; the migration tool interpreted it as UTC.
- BST/GMT (British Summer Time) transitions not re-applied to historical data.
- A "midnight sentinel" (`00:00:00`) used to mean "date only, time unknown" being parsed as a real
  instant and then shifted by the local offset.

**Worked example** (the golden fixture for `TEMP-003`):

```json
{ "resourceType": "Encounter",
  "period": {
    "start": "2026-09-01T09:02:00Z",
    "end":   "2026-08-30T10:00:00Z" }
}
```

The rule computes `delta_hours = -47.2` and reports:

> `Encounter.period.end (2026-08-30T10:00:00Z) precedes Encounter.period.start
> (2026-09-01T09:02:00Z).`

**Detecting rule:** `TEMP-003` (category: *temporal coherence*). **Severity:** error.
**Suggested action in the finding:** *"Confirm source-system timezone handling; records migrated
from a system using local time commonly exhibit this defect."*

### 2.2 Impossible date sequences (`TEMP-004` / `TEMP-005` / `TEMP-006`)

**What it is.** Dates that cannot be true for any patient: birth date in the future, birth date more
than 130 years ago, death before birth, an observation *after* the recorded `deceasedDateTime`, a
condition onset after its abatement.

**Real-world causes.**

- Blank dates coerced to `0001-01-01` or `9999-12-31` by an ETL "default".
- Patient records merged without a conflict check, so one person's death date landed on another.
- Observations back-dated or forward-dated by a device with a drifted clock.

**Worked example:**

```json
{ "resourceType": "Patient", "birthDate": "2031-04-02" }
```

The validator independently reports `birthDate: date is in the future`; the quality rule adds the
domain context and a location. `TEMP-006` catches the clinically serious case of an observation
*after death*, which matters because it implies either mis-attribution or a wrong death date.

**Detecting rules:** `TEMP-004`, `TEMP-005`, `TEMP-006`. **Severity:** error.

### 2.3 Decimal-point transcription errors (`PHYS-001`)

**What it is.** A value an order of magnitude wrong because a decimal point was dropped, added, or
moved during manual transcription or a column-format conversion.

**Real-world causes.**

- CSV import interpreting `142.0` as the integer `1420` (a locale/format mismatch).
- A manual entry of `142` meant as `14.2`, or a units change (mmol/L ↔ mg/dL) applied but not
  converted.
- OCR or voice-dictation transcription of vitals.

**Worked example:**

```json
{ "resourceType": "Observation",
  "code": { "coding": [{ "system": "http://snomed.info/sct", "code": "271649006",
                          "display": "Systolic blood pressure" }] },
  "valueQuantity": { "value": 1420, "unit": "mm[Hg]" } }
```

**Detecting rule:** `PHYS-001` (category: *physiological plausibility*). Systolic BP is bounded to
30-300 mmHg, with the reference range **cited in the rule definition**. **Severity:** error
(impossible) vs warning (implausible) - `1420` is impossible, so it is an error.

### 2.4 Sentinel values (`PHYS-004`)

**What it is.** A clinically meaningful field holding a magic "not recorded" value instead of an
actual measurement. `SpO₂ = 0` and `SpO₂ = 100` are the classic sentinels - `0` meaning "not
measured" and `100` meaning "we didn't take it but needed a number". A real patient cannot have
SpO₂ of 0 while the record is being written.

**Real-world causes.**

- A source system required a numeric field, so staff entered `0` or `999` for "unknown".
- A device emitted `0` on a failed reading, and the EPR stored it as a valid observation.
- A "blank = 100%" assumption in a legacy form.

**Worked example:** `valueQuantity.value = 0` on an SpO₂ observation with `interpretation: normal`.

**Detecting rule:** `PHYS-004` (SpO₂ outside 40-100 %). **Severity:** error at the hard bound,
warning at the implausible edge. The rule's `suggested_action` names the sentinel convention so a
reviewer can fix the *encoding*, not the patient.

### 2.5 Retired terminology (`TERM-005`)

**What it is.** A code that was once valid but has since been retired/inactivated in SNOMED CT or
dm+d, used with an effective date *after* its retirement.

**Real-world causes.**

- A Trust's local pick-list was frozen years ago and never reconciled with the national release.
- A mapper produced codes from an outdated terminology version (the "terminology lag" problem).
- A drug was withdrawn (dm+d VMP inactivated) but old order sets still emit its code.

**Worked example:** a SNOMED concept with an `effectiveTime` retirement of `2018-01-31`, referenced
by an Observation with `effectiveDateTime: 2023-05-01`.

**Detecting rule:** `TERM-005` (category: *terminology*). **Severity:** error (post-retirement use)
/ warning (used on the retirement date). This requires the resolver to carry historical
`effectiveTime` - which is exactly why the resolver mode and subset version are recorded in every
report.

### 2.6 Local-code drift (`TERM-001` / `TERM-002`)

**What it is.** A code that only has meaning inside one organisation ("local code") - either an
unrecognised system URI, or a plausible-looking code that is not resolvable in any bound value set.

**Real-world causes.**

- A Trust system emits its internal observation codes (e.g. `WEIGHT` or a numeric trust code)
  instead of SNOMED CT / LOINC.
- Two organisations merge and their local codes collide with different meanings.
- A mapping table exists but was never applied to historical records.

**Worked example:** an Observation coded with `system: "http://trust.local/fhir/codes"` and
`code: "BP-SYS"`. `TERM-001` flags the unrecognised system; `TERM-002` flags a code that *looks*
SNOMED-shaped but resolves to nothing.

**Detecting rules:** `TERM-001`, `TERM-002`. **Severity:** error. The finding distinguishes "not
recognised" (system URI unknown) from "recognised system, unknown code" - two very different
remediation paths.

### 2.7 Mojibake / encoding corruption (`STRUCT-004`)

**What it is.** Non-ASCII characters corrupted by a wrong encoding round-trip - UTF-8 bytes decoded
as Latin-1 (Windows-1252), combining characters split from their base letter, or replacement
characters (`�`) where an encoding boundary dropped bytes.

**Real-world causes.**

- A legacy HL7 v2 feed in 8-bit encoding piped through a UTF-8-only parser without conversion.
- Excel editing a CSV and re-saving it in Windows-1252.
- **This is a real, documented issue:** NHS England flags incorrectly decoded special characters as a
  known problem in its own synthetic notes dataset.

**Worked example:** `"family": "JÃ¡uregui"` (the UTF-8 `á` = `0xC3 0xA1` reinterpreted as
Latin-1 → `Ã¡`); or `"given": ["Noe\u0308l"]` where the diaeresis is a combining character that
should be `ë` (U+00EB).

**Detecting rule:** `STRUCT-004`. **Severity:** warning. A round-trip test additionally asserts
byte-identical re-export, so the corruption cannot silently round-trip through ingestion.

### 2.8 Duplicate identifiers (`IDENT-005`)

**What it is.** Two *different* Patient resources carrying the *same* NHS number - or one patient
carrying two different NHS numbers. Both are mis-identification hazards.

**Real-world causes.**

- Two source systems (GP and acute) each created a patient record for the same person, then a
  demographic merge assigned one number to both without de-duplication.
- A manual "find or create" step that generated a new record instead of matching.
- Identifier reuse after a number was reassigned (or a wrong number keyed in).

**Worked example:** two `Patient` resources, both with
`identifier.system = https://fhir.nhs.uk/Id/nhs-number` and `value = 9900000001`, but different
`logical_id`s.

**Detecting rules:** `IDENT-003` (check-digit), `IDENT-005` (duplicate across patients).
**Severity:** error. Ingestion **blocks** on a duplicate NHS number - the system refuses to persist a
second record for an already-seen number until a human resolves it.

### 2.9 Dangling references (`REF-001` / `REF-003`)

**What it is.** A resource whose `subject`/`encounter` reference points at a resource that does not
exist in the store.

**Real-world causes.**

- A migration exported observations but dropped the corresponding patient/encounter records (partial
  extract).
- A referential-integrity constraint was absent in the source, so orphan rows accumulated for years.
- A bundle was assembled from two systems with mismatched IDs.

**Worked example:** an Observation with `subject.reference = "Patient/missing-xyz"` where
`missing-xyz` was never ingested. `REF-003` is the cohort variant: a patient with 0 Encounters but
40 Observations - the observations are effectively orphaned at the *patient* level.

**Detecting rules:** `REF-001` (dangling reference), `REF-003` (orphaned cohort).
**Severity:** error.

### 2.10 Identifier check-digit failures (`IDENT-003`)

**What it is.** An NHS number that is structurally plausible (10 digits) but fails the modulus-11
check digit.

**Real-world causes.** Manual transcription errors (transposed digits are the classic case), OCR
errors on a scanned record, or a source system that stored a number without validating it.

**Worked example:** `943 476 5919` vs the correctly-checked `943 476 5870` - a single digit is
wrong. The rule recomputes the modulus-11 check and flags the mismatch.

**Detecting rule:** `IDENT-003`. **Severity:** error. Clerkstone generates its *own* synthetic
numbers with valid check digits (in the reserved `99…` test range), so a check-digit failure in
ingested data is always a deliberate or genuine defect, never an artefact of the generator.

### 2.11 Display/term disagreement (`TERM-004`)

**What it is.** A code's `display` text does not match the text of the concept the code actually
resolves to.

**Real-world causes.**

- A mapper copied the right code with a display string from a *different* (old or local) source.
- Manual edits changed the display without changing the code.
- A language/dialect variant of the preferred term.

**Worked example:** `code: 271649006` (Systolic blood pressure) but `display: "Heart rate"`.

**Detecting rule:** `TERM-004`. **Severity:** warning - the *code* is authoritative, but the mismatch
signals a broken mapping upstream that will mislead a human reader.

### 2.12 Duplicate records (`DUP-002`)

**What it is.** Two Observations for the same patient with the same code, effective time and value -
a true duplicate - or two Encounters with identical class and start ±5 minutes.

**Real-world causes.**

- A retried interface message that was not idempotent, so the same observation was written twice.
- Two feeds (device + EPR) each submitting the same reading.
- A re-run of an import without de-duplication.

**Worked example:** two identical `heart rate = 72 bpm` Observations at `2026-09-01T09:14:00Z`.

**Detecting rule:** `DUP-002` (category: *duplication*). **Severity:** warning - duplicates inflate
counts and break cohort analytics even though no single record is "wrong".

### 2.13 Cohort completeness gaps (`COH-001` / `COH-002`)

**What it is.** A *cross-resource* signal, not a single-record defect: a patient with a diagnosis but
no corroborating observations. The classic case is a diabetes diagnosis (`SNOMED 44054006`) with no
HbA1c observation in the last 24 months.

**Real-world causes.**

- The lab feed was never connected, so results exist in the lab system but not the EPR.
- A patient was diagnosed elsewhere and only the diagnosis (not the history) migrated.
- A data-loss incident dropped a date range of observations.

**Worked example:** a `Condition` with `code = 44054006` (Diabetes mellitus), `clinical_status =
active`, and zero HbA1c Observations within 24 months of the query date.

**Detecting rules:** `COH-001` (encounter with zero observations), `COH-002` (diabetes without
recent HbA1c). **Severity:** info/warning - this is a *population-level* signal that a Trust uses to
find feed gaps, and it is exactly the kind of query J1's "handling data quality issues" means.

### 2.14 Structural corruption (`STRUCT-001` / `PROF-002`)

**What it is.** Malformed/truncated JSON, unknown elements, or a missing mandated `meta.profile`.

**Real-world causes.** A crashed export truncating a file; an HL7 v2 pipe that dropped a segment; a
schema-less consumer that silently stripped fields; an older system that never emitted
`meta.profile`.

**Worked example:** a Bundle whose final entry is cut off mid-object, or a Patient lacking
`meta.profile` where UK Core mandates it.

**Detecting rules:** `STRUCT-001` (malformed/truncated), `PROF-002` (missing `meta.profile`).
**Severity:** error. The FHIR validator sidecar independently reports structural failures as
`OperationOutcome`; the quality rules add the *domain* consequence.

---

## 3. How the taxonomy is exercised

Each family is injected **deterministically** by a named corruption class (`TemporalInversion`,
`InvalidNhsNumberCheckDigit`, `DecimalShift`, …) with a docstring naming the rule it must trigger.
The frequency of injection is parameterised (spec §15), so the seeded corpus is a *realistic*
mixture rather than one of everything:

| Edge case (from §15) | Injected frequency | Rule exercised |
|---|---|---|
| Missing NHS number | 3% | `IDENT-001` |
| NHS number with invalid check digit | 1% | `IDENT-003` |
| Same NHS number on two Patients | 0.5% | `IDENT-005` |
| Local-time vs UTC mix | 5% of encounters | `TEMP-003` |
| Encounter end before start | 0.5% | `TEMP-003` |
| Deceased patient with later Observations | 0.2% | `TEMP-006` |
| Systolic BP recorded as 1420 | 0.3% | `PHYS-001` |
| SpO₂ = 0 or 100 sentinel | 2% | `PHYS-004` |
| Unresolvable SNOMED code | 1% | `TERM-002` |
| Retired concept, post-retirement date | 0.5% | `TERM-005` |
| Display text ≠ code | 2% | `TERM-004` |
| Dangling reference | 1% | `REF-001` |
| Duplicate Observation | 3% | `DUP-002` |
| Diabetes with no HbA1c in 24 months | 4% | `COH-002` |
| Truncated / malformed JSON | 0.5% | `STRUCT-001` |
| Missing `meta.profile` | 10% | `PROF-002` |
| Non-ASCII / mojibake names | 2% | `STRUCT-004` |
| 0 Encounters but 40 Observations | 0.5% | `REF-003` / `COH-001` |

Golden-file regression (`tests/test_rules_golden.py`) asserts that applying each defect class to the
fixture produces **exactly** the expected findings (rule IDs + severities + expressions) against a
committed golden JSON file.

## 4. The honest limit of a taxonomy

> The quality engine detects the defects this taxonomy names. It has **no coverage guarantee** against
> defects not anticipated here - which is why the ruleset is versioned and every report states which
> version ran. A taxonomy is a living artefact: each new observed defect is a new rule with a new
> fixture, and a new ruleset version.
