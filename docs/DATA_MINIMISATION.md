# Clerkstone — Data Minimisation (Caldicott-aligned)

> Per-field justification for every piece of patient-shaped data Clerkstone retains, against the
> Caldicott Principles. Companion documents: [PRIVACY.md](./PRIVACY.md) · [DATA_LICENCES.md](./DATA_LICENCES.md).

## 1. The governing principle

**Caldicott Principle 5:** *"Use the minimum necessary personal data."*

Applied to a synthetic-data prototype, the discipline is: even though the data is synthetic, retain
**only the fields a real system would strictly need**, and be able to justify each one. That is what
this document does. Where a field would be minimised for real data (full postcode → outward postcode;
raw IP → salted hash), Clerkstone applies the same minimisation **now**, so the behaviour is
demonstrably correct rather than bolted on later.

## 2. The two non-negotiable minimisations

| Field | Stored form | Why |
|---|---|---|
| **Address postcode** | **Outward code only** (e.g. `LS1`, never `LS1 1AB` and never a street/house number) | An outward postcode supports cohort geography (a legitimate analytical need) without identifying a household. The full address is never projected. |
| **Client IP address** | **Salted hash only** (`ip_hash`), never the raw IP | The raw IP is not needed for the audit's purpose (accountability), and a salted hash preserves "same source" linkage for abuse detection without retaining the identifier. |

Both are stored only in the audit/projection layer — the FHIR resource itself retains whatever the
synthetic generator produced (which is itself synthetic), but **nothing real** is ever projected.

## 3. Per-field justification

| Field | Retained? | Justification (Caldicott-aligned) |
|---|---|---|
| NHS number (synthetic) | Yes | Identity key for de-duplication (`IDENT-005`) and cross-resource joins. Synthetic `99…` range only. |
| Family / given names | Yes | Timeline and search display; synthetic. |
| Birth date | Yes (full date) | Required for temporal rules (`TEMP-*`) and age computation. Not truncatable without breaking the rules. |
| Gender | Yes | Bound-value-set validation and cohort rules. |
| Deceased flag / date | Yes | `TEMP-006` (observation-after-death) needs it. |
| Full address (street, town) | **No** — not projected | No analytical use; outward postcode suffices. |
| Postcode | **Outward code only** | Cohort geography. |
| Raw IP | **No** | Salted hash only. |
| Phone / email (`telecom`) | Not projected | No quality rule or UI needs it; retained in the synthetic resource only. |
| `Observation.value` | Yes | Physiological-plausibility rules (`PHYS-*`) are the core of the gateway. |
| SNOMED / dm+d / ICD-10 codes | Yes | Terminology-resolvability rules (`TERM-*`). |
| `meta.security` / provenance | Yes | Audit and provenance integrity. |

## 4. Caldicott Principles — how Clerkstone maps

| Principle | Clerkstone behaviour |
|---|---|
| 1 — Justify the purpose | Synthetic-data quality demonstration; stated in README and [PRIVACY.md](./PRIVACY.md). |
| 2 — Don't use personal data unless necessary | No personal data at all (synthetic). |
| 3 — Use the minimum necessary | This document; outward postcode, hashed IP. |
| 4 — Access on a strict need-to-know | RBAC with field-level scoping (observations vs demographics). |
| 5 — Everyone with access must understand their responsibility | Roles are audited; the synthetic-data notice is present in every view. |
| 6 — Comply with the law | [PRIVACY.md](./PRIVACY.md) states the UK GDPR / DPA 2018 position. |
| 7 — Duty to share information as well as protect | N/A for synthetic data; noted for completeness. |

## 5. What would change for real data

- Full postcode and address would be **restricted to out-of-hours/cohort analysis behind a further
  access control**, not available to the default `reader` role.
- IP hashing would use a **rotated per-deployment salt** with a documented retention window.
- A formal **retention schedule** would replace "delete the dataset".
- Each projection column would be re-justified in a DPIA (see [PRIVACY.md](./PRIVACY.md) §3).
