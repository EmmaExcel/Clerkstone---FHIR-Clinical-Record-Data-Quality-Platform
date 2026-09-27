# Clerkstone - API Guide

> Reference for every endpoint in the specification §13. Base path `/api/v1`. All responses are
> JSON. All errors are FHIR `OperationOutcome`. All requests require `Authorization: Bearer <jwt>`
> except `/health`, `/ready` and `/docs`. Roles: `reader | analyst | admin`. The interactive OpenAPI
> schema is served at `/docs`.

**Conventions**

- **Errors are `OperationOutcome`.** Every failure - auth, authz, validation, not-found - returns a
  FHIR `OperationOutcome` with a machine-readable `issue.code`, a human message, and an `expression`
  pointing at the offending element (see [DECISIONS.md - ADR-005](./DECISIONS.md)).
- **Field-level scoping** applies on read endpoints: a role that may read demographics but not
  observations will receive demographics only, and the omission is audited.
- **Pagination** uses `_count` with a hard server-side maximum (`MAX_PAGE_SIZE`, default 200).
- **Idempotency** on writes is via an `Idempotency-Key` header.
- Every response carries `X-Clerkstone-Data-Class: synthetic`.

## 0. Roles at a glance

| Role | Can do |
|---|---|
| `reader` | Read FHIR resources, patients, quality runs/findings, terminology |
| `analyst` | Everything `reader` can do, **plus** ingest bundles, validate, run quality, assign/resolve findings, export, HL7 v2 ingest |
| `admin` | Everything `analyst` can do, **plus** query the audit log and manage users/roles |

---

## 1. System

### GET `/health`

| | |
|---|---|
| **Purpose** | Liveness probe - process is up. |
| **Min role** | none |

```http
GET /api/v1/health
```

```json
{ "status": "ok" }
```

### GET `/ready`

| | |
|---|---|
| **Purpose** | Readiness - database **and** validator reachable. |
| **Min role** | none |

```http
GET /api/v1/ready
```

```json
{ "status": "ready", "checks": { "db": "ok", "validator": "ok" } }
```

### GET `/metrics`

| | |
|---|---|
| **Purpose** | Prometheus metrics (request-duration histograms, rule-execution timers). |
| **Min role** | internal (scrape endpoint) |

---

## 2. FHIR

### POST `/fhir`

| | |
|---|---|
| **Purpose** | Ingest a FHIR `Bundle` (transaction). Parse, de-duplicate by logical ID, validate, persist, run quality rules. |
| **Min role** | analyst |

```http
POST /api/v1/fhir
Authorization: Bearer <jwt>
Content-Type: application/fhir+json
```

```json
{
  "resourceType": "Bundle",
  "type": "transaction",
  "entry": [
    { "fullUrl": "urn:uuid:6f1c…", "resource": { "resourceType": "Patient", "id": "6f1c…",
        "identifier": [{ "system": "https://fhir.nhs.uk/Id/nhs-number", "value": "9900000001" }],
        "name": [{ "family": "Okonkwo", "given": ["Amara"] }],
        "gender": "female", "birthDate": "1958-03-11" },
      "request": { "method": "POST", "url": "Patient" } },
    { "resource": { "resourceType": "Observation", "status": "final",
        "code": { "coding": [{ "system": "http://snomed.info/sct", "code": "271649006",
                               "display": "Systolic blood pressure" }] },
        "valueQuantity": { "value": 142, "unit": "mm[Hg]", "system": "http://unitsofmeasure.org" },
        "effectiveDateTime": "2026-09-01T09:14:00Z" },
      "request": { "method": "POST", "url": "Observation" } }
  ]
}
```

**201 Created**

```json
{
  "bundle_id": "9c1a4f2e-…",
  "status": "partial",
  "resources": { "accepted": 2, "rejected": 0 },
  "validation": {
    "resourceType": "OperationOutcome",
    "issue": [
      { "severity": "warning", "code": "business-rule",
        "expression": ["Patient.identifier[0].value"],
        "details": { "coding": [{ "system": "https://clerkstone.local/rules", "code": "IDENT-002" }] },
        "diagnostics": "NHS number present but check-digit not verified against the NHS Number standard." }
    ]
  },
  "quality_run_id": "4d0b…",
  "links": { "self": "/api/v1/fhir/bundles/9c1a4f2e-…", "quality_run": "/api/v1/quality/runs/4d0b…" }
}
```

### POST `/fhir/$validate`

| | |
|---|---|
| **Purpose** | Validate a resource/bundle **without storing** (structure + UK Core profile). Returns `OperationOutcome`. |
| **Min role** | reader |

```http
POST /api/v1/fhir/$validate
Authorization: Bearer <jwt>
```

**Request** - a Patient missing `identifier`:

```json
{ "resourceType": "Patient", "name": [{ "family": "Okonkwo" }], "birthDate": "2031-04-02" }
```

**Response:**

```json
{ "resourceType": "OperationOutcome",
  "issue": [
    { "severity": "error", "code": "required",
      "details": { "text": "UKCore-Patient: identifier required where available" },
      "expression": ["Patient.identifier"] },
    { "severity": "error", "code": "invalid",
      "details": { "text": "Patient.birthDate: date is in the future" },
      "expression": ["Patient.birthDate"],
      "diagnostics": "2031-04-02 is after the current date (2026-09-25)." }
  ] }
```

### GET `/fhir/{resourceType}/{id}`

| | |
|---|---|
| **Purpose** | Read a single resource by logical ID. |
| **Min role** | reader |

```http
GET /api/v1/fhir/Observation/b2…
Authorization: Bearer <jwt>
```

→ the full FHIR resource JSON.

## 3. Patients

### GET `/patients`

| | |
|---|---|
| **Purpose** | Search patients (`family`, `birthdate`, `gender`, `_count`, `_page`). |
| **Min role** | reader |

```http
GET /api/v1/patients?family=Okonkwo&_count=20
```

```json
{ "total": 1, "page": { "count": 20, "next": null },
  "patients": [ { "id": "6f1c…", "family_name": "Okonkwo", "given_names": ["Amara"],
                  "birth_date": "1958-03-11", "gender": "female",
                  "nhs_number_status": "verified" } ] }
```

### GET `/patients/{id}`

| | |
|---|---|
| **Purpose** | Patient summary - demographics plus per-type counts. |
| **Min role** | reader |

### GET `/patients/{id}/timeline`

| | |
|---|---|
| **Purpose** | Ordered clinical timeline (`from`, `_count`). Entries carry inline `quality_flags`. |
| **Min role** | reader |

```http
GET /api/v1/patients/6f1c…/timeline?from=2026-01-01&_count=50
```

```json
{
  "patient": { "id": "6f1c…", "nhs_number_status": "verified", "birth_date": "1958-03-11",
               "age_years": 68, "gender": "female" },
  "synthetic_data_notice": "All records in this system are synthetically generated. This is a portfolio prototype and must not be used for patient care.",
  "range": { "from": "2026-01-01T00:00:00Z", "to": "2026-09-25T00:00:00Z" },
  "entries": [
    { "type": "Encounter", "id": "a1…", "date": "2026-09-01T09:02:00Z", "class": "emergency",
      "display": "Emergency admission", "status": "finished",
      "quality_flags": ["TEMP-001"] },
    { "type": "Observation", "id": "b2…", "date": "2026-09-01T09:14:00Z",
      "display": "Systolic blood pressure", "value": "142 mm[Hg]", "interpretation": "high",
      "code": { "system": "SNOMED CT", "value": "271649006", "resolved": true } }
  ],
  "counts": { "encounters": 4, "observations": 61, "conditions": 7, "medications": 9 },
  "page": { "count": 50, "next": null }
}
```

### GET `/patients/{id}/observations`

| | |
|---|---|
| **Purpose** | Observations for a patient, filterable by `code` and `date`, `_count`. |
| **Min role** | reader |

### GET `/patients/{id}/conditions`

| | |
|---|---|
| **Purpose** | Conditions for a patient. |
| **Min role** | reader |

### GET `/patients/{id}/medications`

| | |
|---|---|
| **Purpose** | Medication requests (dm+d). |
| **Min role** | reader |

### GET `/patients/{id}/$export`

| | |
|---|---|
| **Purpose** | Emit a valid FHIR `Bundle` for the patient (round-trip re-ingestible). |
| **Min role** | analyst |

## 4. Terminology

### GET `/terminology/resolve`

| | |
|---|---|
| **Purpose** | Resolve a code (`system`, `code`) → `display`, `active`, value-set membership. |
| **Min role** | reader |

```http
GET /api/v1/terminology/resolve?system=http://snomed.info/sct&code=271649006
```

```json
{ "system": "http://snomed.info/sct", "code": "271649006",
  "display": "Systolic blood pressure", "active": true,
  "resolver": "local-subset", "subset_version": "⟨version⟩",
  "value_set_membership": ["UKCore-Observation-VitalSigns"] }
```

## 5. HL7 v2

### POST `/hl7v2`

| | |
|---|---|
| **Purpose** | Accept an ADT message, convert to FHIR, validate, run quality rules, ingest. |
| **Min role** | analyst |

```http
POST /api/v1/hl7v2
Authorization: Bearer <jwt>
Content-Type: text/plain
```

```hl7
MSH|^~\&|SENDAPP|SENDFAC|RECAPP|RECFAC|20260901090200||ADT^A01|MSGID|P|2.5
PID|1||9900000001^^^NHS^NH||Okonkwo^Amara||19580311|F||||
PV1|1|I|WARD1^Bed1^Room1|||||||||||||||A01
```

→ a `201` with `bundle_id`, `quality_run_id`, and the `OperationOutcome`, identical in shape to
`POST /fhir`. See [HL7V2_MAPPING.md](./HL7V2_MAPPING.md) for the segment→element mapping.

## 6. Quality

### GET `/quality/rules`

| | |
|---|---|
| **Purpose** | List rules in the active ruleset (id, category, severity, title, FHIRPath). |
| **Min role** | reader |

### POST `/quality/runs`

| | |
|---|---|
| **Purpose** | Start a quality run over a scope (patients/bundles) with the active ruleset. |
| **Min role** | analyst |

```http
POST /api/v1/quality/runs
{ "scope": { "patients": ["6f1c…"], "bundles": [] }, "ruleset_version": "2.1.0" }
```

```json
{ "run_id": "4d0b…", "status": "running", "ruleset_version": "2.1.0" }
```

### GET `/quality/runs`

| | |
|---|---|
| **Purpose** | List runs (reverse chronological). |
| **Min role** | reader |

### GET `/quality/runs/{id}`

| | |
|---|---|
| **Purpose** | Run summary + severity counts. |
| **Min role** | reader |

```json
{ "run_id": "4d0b…", "ruleset_version": "2.1.0", "status": "complete",
  "summary": { "error": 3, "warning": 17, "info": 5 },
  "rules_applied": ⟨N⟩, "resolver": "local-subset" }
```

### GET `/quality/runs/{id}/findings`

| | |
|---|---|
| **Purpose** | Findings, filterable by `severity`, `rule`, `patient`, `_page`. |
| **Min role** | reader |

```http
GET /api/v1/quality/runs/4d0b…/findings?severity=error
```

```json
{
  "run_id": "4d0b…", "ruleset_version": "2.1.0",
  "summary": { "error": 3, "warning": 17, "info": 5 },
  "findings": [
    { "id": "f001", "rule_id": "TEMP-003", "severity": "error",
      "title": "Encounter period ends before it starts",
      "resource": { "type": "Encounter", "logical_id": "enc-8821",
                    "url": "/api/v1/fhir/Encounter/enc-8821" },
      "patient_id": "6f1c…",
      "expression": ["Encounter.period.end"],
      "message": "Encounter.period.end (2026-08-30T10:00:00Z) precedes Encounter.period.start (2026-09-01T09:02:00Z).",
      "context": { "start": "2026-09-01T09:02:00Z", "end": "2026-08-30T10:00:00Z", "delta_hours": -47.2 },
      "review_status": "open",
      "suggested_action": "Confirm source-system timezone handling; records migrated from a system using local time commonly exhibit this defect." }
  ],
  "page": { "count": 20, "total": 3, "next": null }
}
```

### POST `/quality/findings/{id}/assign`

| | |
|---|---|
| **Purpose** | Assign a finding for review (deterministic state machine: `open → assigned`). |
| **Min role** | analyst |

### POST `/quality/findings/{id}/resolve`

| | |
|---|---|
| **Purpose** | Record a resolution (`resolved` or `accepted_risk`), with attribution. |
| **Min role** | analyst |

> The review workflow is an explicit, named, auditable verb - not a generic PATCH - by design
> ([DECISIONS.md - ADR-005](./DECISIONS.md)).

## 7. Governance

### GET `/audit/events`

| | |
|---|---|
| **Purpose** | Query the append-only, hash-chained audit log (actor, action, resource, outcome, request ID). |
| **Min role** | admin |

```http
GET /api/v1/audit/events?actor=alice&action=read.patient&_count=50
```

```json
{ "events": [
    { "occurred_at": "2026-09-25T10:00:00Z", "actor": "alice", "actor_role": "reader",
      "action": "read.patient", "resource_type": "Patient", "resource_id": "6f1c…",
      "outcome": "success", "request_id": "req-9f2…", "ip_hash": "⟨salted hash⟩" } ],
  "chain_verified": true }
```

---

## 8. Error reference (all are `OperationOutcome`)

| HTTP | `issue.code` | Meaning |
|---|---|---|
| 401 | `login` / `security` | Missing/invalid/expired JWT |
| 403 | `forbidden` | Valid token, insufficient role or field scope |
| 404 | `not-found` | Resource/run/finding not found (or not visible to the caller) |
| 409 | `duplicate` / `conflict` | Idempotency replay or duplicate identifier blocked (e.g. `IDENT-005`) |
| 422 | `invalid` / `required` / `business-rule` | FHIR validation or quality-rule failure |
| 429 | `throttled` | Rate limit exceeded (`RATE_LIMIT_PER_MINUTE`) |
| 500 | `exception` | Unhandled server error (logged with correlation ID; never exposes a stack trace) |

Every `500` carries the `X-Request-Id` so the operator can find it in the structured logs - see
[RUNBOOK.md](./RUNBOOK.md).
