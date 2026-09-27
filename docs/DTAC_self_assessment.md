# Clerkstone - DTAC Self-Assessment

> The NHS **Digital Technology Assessment Criteria (DTAC)** is the national baseline for assessing
> digital health technologies. It has five pillars. This is an honest self-assessment of Clerkstone
> against those pillars, using the standard three-way rating:
>
> - Yes **Satisfied** - the artefact exists and is appropriate to the prototype's scope.
> - 🟡 **Partially satisfied** - the right thing is demonstrated, but not to production depth.
> - ⬜ **Out of scope** - not meaningful for a synthetic-data portfolio prototype.
>
> This document is itself portfolio evidence: an interviewer checking "DTAC awareness" (a desirable
> in the target roles) is looking for someone who can *honestly place* a system against the criteria,
> not someone who ticks every box.

## Pillar 1 - Clinical Safety

| Criterion | Rating | Evidence |
|---|---|---|
| Clinical risk management process | 🟡 | [Hazard_Log.md](./Hazard_Log.md) is DCB0129-*informed* (8 hazards, S×L matrix, controls, residual risk). **Not** a compliant CSCR - that requires a registered CSO's signature. |
| Clinical safety case | 🟡 | [Safety_Architecture.md](./Safety_Architecture.md) records the safety argument (human-in-the-loop, deterministic rules, versioned rulesets). Prototype only. |
| Human-in-the-loop model | Yes | Review workflow with `accepted_risk` as a first-class, attributed state; findings never auto-modify data. |
| SaMD / medical-device boundary | Yes | Explicitly **not** a medical device; no clinical decision-making; optional NEWS2 (if built) is a verbatim published-algorithm implementation, never a learned model. |

**Pillar 1 verdict:** 🟡 **Partially satisfied.** The *method* is demonstrated end-to-end; the
*mandate* (CSO sign-off, live-data clinical risk management) is honestly out of scope for a
synthetic-data prototype.

## Pillar 2 - Information Governance

| Criterion | Rating | Evidence |
|---|---|---|
| Lawful basis / GDPR | Yes | [PRIVACY.md](./PRIVACY.md) states no personal data is processed (all synthetic), and explains the lawful basis that *would* apply to real data (Art. 6(1)(e) public task + Art. 9(2)(h) health and social care, with a DPIA). |
| Data minimisation | Yes | [DATA_MINIMISATION.md](./DATA_MINIMISATION.md): outward postcode only, salted-hashed IP, per-field Caldicott justification. |
| Audit & traceability | Yes | Append-only, hash-chained audit log covering reads and writes; `make verify-audit`. |
| Records management | 🟡 | Data retention for a prototype is "delete the dataset"; no formal retention schedule (not needed for synthetic data). |
| DSPT alignment | 🟡 | Controls are *mapped to* DSPT expectations; no formal DSPT submission (out of scope for a personal project). |

**Pillar 2 verdict:** Yes **Satisfied** *for the data actually held* (synthetic). The governance
documents would carry straight over to a real-data deployment with the addition of a DPIA and CSO
sign-off.

## Pillar 3 - Usability & Accessibility

| Criterion | Rating | Evidence |
|---|---|---|
| NHS Design System | Yes | `nhsuk-react-components` + `nhsuk-frontend` styling; NHS header/footer; skip link. |
| WCAG 2.2 AA | Yes | [accessibility.md](./accessibility.md): semantic HTML, contrast ≥4.5:1, no colour-only severity encoding, keyboard-complete, `aria-live` on async results; axe-core in CI + manual screen-reader pass. |
| Responsive / inclusive | Yes | Tested at 320 px; keyboard-only journeys in Playwright. |
| Clinical-safety usability | Yes | Permanent synthetic-data banner; timeline renders FHIR resources clinician-readably with quality-flag badges. |
| User research | ⬜ | No formal user research - not meaningful for a portfolio prototype. |

**Pillar 3 verdict:** Yes **Satisfied** for an NHS-facing front end, within the limits of a prototype
(no user research).

## Pillar 4 - Technical Assurance & Security

| Criterion | Rating | Evidence |
|---|---|---|
| Threat modelling | Yes | [THREAT_MODEL.md](./THREAT_MODEL.md): STRIDE over all six components, mitigations mapped to §19 controls. |
| Secure development | Yes | JWT RS256 + RBAC, parameterised SQL only, input validation, secrets management, deny-by-default. |
| Penetration / code review | 🟡 | Automated security tests (SQLi, IDOR, JWT tamper/expiry) in CI; no third-party pen test (out of scope). |
| Supply chain | Yes | Pinned lockfiles, pip-audit, npm audit, Trivy image scan, pinned base digests, Dependabot. |
| Monitoring / ops | Yes | [RUNBOOK.md](./RUNBOOK.md), `/health` + `/ready`, structured logs with correlation IDs, Prometheus `/metrics`. |

**Pillar 4 verdict:** Yes **Satisfied** *for a prototype*. A real deployment would add a WAF, SIEM
and managed keys - named as such in the threat model, not silently claimed.

## Pillar 5 - Interoperability & Standards

| Criterion | Rating | Evidence |
|---|---|---|
| Standards compliance | 🟡 | FHIR R4 + UK Core profile validation via the reference validator; **honest caveat**: UK Core is published "a work in progress… not for implementation". |
| Terminology standards | 🟡 | SNOMED CT / dm+d / ICD-10 resolution behind a pluggable adapter; **honest caveat**: the mapping table is illustrative and non-clinical; resolution runs against a local subset, not the live NHS England Terminology Server. |
| Messaging standards | Yes | FHIR R4 bundles + an HL7 v2 ADT→FHIR converter ([HL7V2_MAPPING.md](./HL7V2_MAPPING.md)), closing the HL7/FHIR pairing. |
| API standards | Yes | REST + OpenAPI (`/docs`), FHIR-native `OperationOutcome` error semantics, FHIR search parameters. |
| Identifier standards | Yes | Synthetic NHS numbers in the reserved test range with valid modulus-11 check digits. |

**Pillar 5 verdict:** 🟡 **Partially satisfied.** The *engineering* is standards-correct; the
*caveats* are exactly the nuance an integration lead would probe (UK Core "not for implementation",
illustrative mappings, local subset).

---

## Overall summary

| Pillar | Verdict |
|---|---|
| 1 - Clinical Safety | 🟡 Partially satisfied (method demonstrated; CSO mandate out of scope) |
| 2 - Information Governance | Yes Satisfied for synthetic data |
| 3 - Usability & Accessibility | Yes Satisfied (no user research) |
| 4 - Technical Assurance & Security | Yes Satisfied for a prototype |
| 5 - Interoperability & Standards | 🟡 Partially satisfied (honest caveats) |

The pattern - **fully satisfied where the prototype genuinely is, partially satisfied where
production depth would require a CSO / DPIA / live data, out of scope where the criterion is
meaningless for synthetic data** - is the point. It is more credible than a wall of green ticks.
