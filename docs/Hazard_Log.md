# Clerkstone — Hazard Log (DCB0129-informed)

> ⚠️ **Portfolio artefact.** This log is *informed by* DCB0129 (Clinical Risk Management: its
> Application in the Manufacture of Health IT Systems) and DCB0160 (Clinical Risk Management: its
> Application in the Deployment and Use of Health IT Systems). It is **not** a compliant Clinical
> Safety Case Report (CSCR).

## Scope and status note

A compliant CSCR must be produced and signed by a **registered Clinical Safety Officer (CSO)**.
Clerkstone has no CSO and is not a medical device; it is a portfolio prototype operating exclusively
on **synthetic data**. The hazards below are therefore recorded to *demonstrate the method* — hazard
identification, likelihood/severity scoring, control identification, and residual-risk assessment —
not to assert clinical-safety compliance.

**Severity** is scored 1–4 (minor → catastrophic). **Likelihood** is scored 1–4 (remote → frequent).
Initial risk = pre-controls; residual risk = post-controls. **Target residual ≤ Moderate** for any
hazard that is still open.

### Severity scale

| Score | Meaning |
|---|---|
| 1 | Minor — no patient harm, minor inconvenience |
| 2 | Moderate — short-term or reversible harm |
| 3 | Major — serious harm, delayed or wrong clinical decision |
| 4 | Catastrophic — permanent harm or death (hypothetical here — no live data) |

### Likelihood scale

| Score | Meaning |
|---|---|
| 1 | Remote — would require multiple independent failures |
| 2 | Unlikely — plausible but not expected |
| 3 | Possible — could occur under normal use |
| 4 | Frequent — expected under normal use |

### Risk matrix

|  | **L1 (remote)** | **L2 (unlikely)** | **L3 (possible)** | **L4 (frequent)** |
|---|---|---|---|---|
| **S4 (catastrophic)** | Moderate | High | Extreme | Extreme |
| **S3 (major)** | Low | Moderate | High | High |
| **S2 (moderate)** | Low | Low | Moderate | Moderate |
| **S1 (minor)** | Low | Low | Low | Low |

---

## Hazard register

### CLK-01 — Quality rule produces a false negative (a defective record passes as clean)

| Field | Detail |
|---|---|
| **Hazard** | A defective record fails no rule, is validated successfully, and is presented to a downstream consumer as clean. |
| **Potential clinical consequence** | A clinician or analyst trusts incomplete/incorrect data; delayed or wrong decision. |
| **Initial risk (S×L)** | 3 × 3 = **High** |
| **Controls (design + process)** | (a) Golden-file regression suite over 40 curated defect fixtures; (b) every rule requires positive and negative tests before merge; (c) the ruleset is versioned and the report always states the ruleset version; (d) the UI displays "⟨N⟩ rules applied, ruleset v⟨X⟩" so completeness is never implied. |
| **Residual risk (S×L)** | 3 × 2 = **Moderate** |
| **Status** | Closed |

### CLK-02 — Quality rule produces a false positive (a valid record is flagged)

| Field | Detail |
|---|---|
| **Hazard** | A valid record is flagged as erroneous. |
| **Potential clinical consequence** | Analyst fatigue; genuine defects deprioritised; if acted on, valid data could be wrongly "corrected". |
| **Initial risk (S×L)** | 2 × 3 = **Moderate** |
| **Controls (design + process)** | (a) Severity tiers so only `error` blocks; (b) `accepted_risk` resolution state records a deliberate human override with attribution; (c) per-rule false-positive rate published in the run summary. |
| **Residual risk (S×L)** | 2 × 2 = **Low** |
| **Status** | Closed |

### CLK-03 — Patient mis-identification (projections link observations to the wrong patient)

| Field | Detail |
|---|---|
| **Hazard** | Projection rows attach observations/encounters to the wrong patient identity. |
| **Potential clinical consequence** | Data presented under the wrong identity; in a real system this is catastrophic. |
| **Initial risk (S×L)** | 4 × 2 = **High** |
| **Controls (design + process)** | (a) Unique constraint on `(resource_type, logical_id, version_id)`; (b) `IDENT-005` detects duplicate NHS numbers and blocks ingestion; (c) NHS number check-digit validation; (d) the UI always shows the identifier used for the match, not just the name; (e) the audit log records every identifier-based lookup. |
| **Residual risk (S×L)** | 4 × 1 = **Moderate** |
| **Status** | Active |

### CLK-04 — Authorisation bypass (reader reaches a write route, or reads another's scoped data)

| Field | Detail |
|---|---|
| **Hazard** | A reader reaches an analyst write route, or one user reads another's scoped data. |
| **Potential clinical consequence** | Unauthorised disclosure/modification of patient-identifiable data. |
| **Initial risk (S×L)** | 4 × 2 = **High** |
| **Controls (design + process)** | (a) Single RBAC dependency, no per-route ad-hoc checks; (b) exhaustive route×role matrix test in CI; (c) IDOR tests (patient A's token cannot read patient B); (d) deny-by-default. |
| **Residual risk (S×L)** | 4 × 1 = **Moderate** |
| **Status** | Active |

### CLK-05 — Audit log tampering or loss (the audit trail is edited or silently truncated)

| Field | Detail |
|---|---|
| **Hazard** | The audit trail is edited or silently truncated. |
| **Potential clinical consequence** | Loss of accountability; inability to investigate an incident; DSPT/DCB0129 non-conformance. |
| **Initial risk (S×L)** | 4 × 2 = **High** |
| **Controls (design + process)** | (a) Append-only table, no `UPDATE`/`DELETE` grants to the application role; (b) SHA-256 hash chain; (c) `make verify-audit` in CI and on a schedule; (d) DB role separation. |
| **Residual risk (S×L)** | 4 × 1 = **Moderate** |
| **Status** | Active |

### CLK-06 — Terminology resolution silently fails and codes are treated as valid

| Field | Detail |
|---|---|
| **Hazard** | The resolver is unavailable and the system treats codes as valid rather than failing loudly. |
| **Potential clinical consequence** | Unmapped or retired codes propagate; coded data becomes unusable or misleading. |
| **Initial risk (S×L)** | 3 × 3 = **High** |
| **Controls (design + process)** | (a) Circuit-breaker with explicit `unresolved` state, never a silent pass; (b) TERM rules escalate severity when the resolver is unavailable; (c) reports state resolver mode (`local-subset` vs `nhse-live`) and subset version. |
| **Residual risk (S×L)** | 3 × 2 = **Moderate** |
| **Status** | Closed |

### CLK-07 — Synthetic data mistaken for real by a viewer or downstream consumer

| Field | Detail |
|---|---|
| **Hazard** | A viewer or downstream consumer mistakes synthetic data for real patient data. |
| **Potential clinical consequence** | Erosion of trust; if ever connected to a real system, mis-scaled expectations of safety. |
| **Initial risk (S×L)** | 3 × 2 = **Moderate** |
| **Controls (design + process)** | (a) Permanent banner in every UI view; (b) `synthetic_data_notice` in every API response body; (c) README scope statement; (d) HTTP header `X-Clerkstone-Data-Class: synthetic`; (e) repo name and product name avoid clinical-trust language. |
| **Residual risk (S×L)** | 3 × 1 = **Low** |
| **Status** | Closed |

### CLK-08 — Encoding corruption of non-ASCII names/addresses during ingestion

| Field | Detail |
|---|---|
| **Hazard** | Non-ASCII names/addresses are mis-decoded (mojibake / combining-character corruption) during ingestion. |
| **Potential clinical consequence** | Mis-rendered patient identity; search failures; potential mis-identification. |
| **Initial risk (S×L)** | 2 × 3 = **Moderate** |
| **Controls (design + process)** | (a) Explicit UTF-8 enforcement at every boundary; (b) `STRUCT-004` rule detects mojibake patterns and combining-character anomalies; (c) round-trip test asserting byte-identical re-export. Note: this hazard is **not hypothetical** — NHS England documents incorrectly decoded special characters as a known issue in their own synthetic notes dataset. |
| **Residual risk (S×L)** | 2 × 2 = **Low** |
| **Status** | Closed |

---

## Summary

| ID | Hazard | Initial | Residual | Status |
|---|---|---|---|---|
| CLK-01 | False negative (defective record passes) | High | Moderate | Closed |
| CLK-02 | False positive (valid record flagged) | Moderate | Low | Closed |
| CLK-03 | Patient mis-identification | High | Moderate | Active |
| CLK-04 | Authorisation bypass | High | Moderate | Active |
| CLK-05 | Audit log tampering/loss | High | Moderate | Active |
| CLK-06 | Terminology resolution silent failure | High | Moderate | Closed |
| CLK-07 | Synthetic data mistaken for real | Moderate | Low | Closed |
| CLK-08 | Encoding corruption of non-ASCII data | Moderate | Low | Closed |

**Closed** hazards have residual risk reduced to an acceptable level and their controls verified in
CI. **Active** hazards remain open because their controls rely on operational process (scheduled
`verify-audit`, RBAC maintenance) as well as code, and are re-reviewed on each release. For a real
deployment, all Active hazards would require a CSO's sign-off before go-live.

## Hazard register review

| Reviewed | By | Outcome |
|---|---|---|
| ⟨date⟩ | ⟨name — portfolio author⟩ | Initial draft; hazards CLK-01…CLK-08 recorded from the defect-injection and control design in the specification §19. |

> **Reminder:** this document satisfies the *method* requirement of DCB0129/DCB0160 awareness. It is
> not, and cannot be, a compliant CSCR without a registered CSO.
