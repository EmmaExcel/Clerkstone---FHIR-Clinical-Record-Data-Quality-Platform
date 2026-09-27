# Clerkstone — Governance & Architecture Documentation

> Index of the documentation suite. Clerkstone is a FHIR R4 clinical record & data-quality platform
> (personal NHS portfolio project). All patient data is **synthetic**; the project is a prototype and
> must not be used for patient care.

## Architecture & decisions

| Document | What it covers |
|---|---|
| [architecture.md](./architecture.md) | System architecture (Mermaid), modular-monolith rationale, "FHIR for fidelity; relational projections for query performance", data flows, deployment topology. |
| [DECISIONS.md](./DECISIONS.md) | Architecture Decision Records (ADR-001…ADR-007): modular monolith, no ML, JSONB+relational, terminology DI seam, agentic-consumption design, validator sidecar, hash-chained audit. |

## Clinical safety & governance

| Document | What it covers |
|---|---|
| [Hazard_Log.md](./Hazard_Log.md) | DCB0129-*informed* hazard log (CLK-01…CLK-08): severity/likelihood matrix, controls, residual risk, status, CSO caveat. |
| [Safety_Architecture.md](./Safety_Architecture.md) | How the architecture contributes to safety: human-in-the-loop, deterministic rules, versioned rulesets, synthetic-data framing. |
| [THREAT_MODEL.md](./THREAT_MODEL.md) | STRIDE over each component (web, nginx, api, db, validator, terminology) with mitigations mapped to the §19 controls. |
| [DTAC_self_assessment.md](./DTAC_self_assessment.md) | Honest walk of the five DTAC pillars (satisfied / partially / out of scope). |

## Data quality (the core of the project)

| Document | What it covers |
|---|---|
| [DEFECT_TAXONOMY.md](./DEFECT_TAXONOMY.md) | **The key interview artefact.** Taxonomy of clinical-data defects with real-world causes: timezone/migration artefacts, decimal-point errors, sentinel values, retired terminology, local-code drift, mojibake, duplicate identifiers, dangling references. |

## Operations & API

| Document | What it covers |
|---|---|
| [RUNBOOK.md](./RUNBOOK.md) | Deploy, investigate a failed quality run, restore, rotate keys. |
| [API_GUIDE.md](./API_GUIDE.md) | Reference for every endpoint (method, path, purpose, minimum role, example request/response). |

## Standards & interoperability

| Document | What it covers |
|---|---|
| [HL7V2_MAPPING.md](./HL7V2_MAPPING.md) | HL7 v2 ADT (A01/A03/A08) → FHIR segment mapping, worked examples, contract tests. |
| [DATA_MODEL.md](./DATA_MODEL.md) | Realistic patient/admission fields (NHS England admissions.csv), the `gender_identity` decision. |
| [accessibility.md](./accessibility.md) | WCAG 2.2 AA conformance notes. |

## Data governance

| Document | What it covers |
|---|---|
| [DATA_LICENCES.md](./DATA_LICENCES.md) | Provenance, licence and citation for every dataset (Synthea, NHS England notes, NHSRdatasets, MIMIC-IV, Simulacrum). |
| [PRIVACY.md](./PRIVACY.md) | UK GDPR / DPA 2018 statement: no personal data processed, plus the lawful basis that *would* apply to real data. |
| [DATA_MINIMISATION.md](./DATA_MINIMISATION.md) | Caldicott-aligned data minimisation (outward postcode, hashed IP, per-field justification). |

---

## Reading order for an interviewer

1. [architecture.md](./architecture.md) — what it is and why.
2. [DEFECT_TAXONOMY.md](./DEFECT_TAXONOMY.md) — the intellectual core.
3. [DECISIONS.md](./DECISIONS.md) — the judgement calls (especially ADR-002: why there is no ML).
4. [Hazard_Log.md](./Hazard_Log.md) + [DTAC_self_assessment.md](./DTAC_self_assessment.md) — the
   governance awareness, with honest caveats.

**Root document:** `../README.md` (the recruiter-facing entry point). **Source of truth for this
project:** `../build.txt`.
