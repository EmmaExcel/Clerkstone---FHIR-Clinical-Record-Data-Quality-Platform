# Clerkstone - Architecture Decision Records (ADRs)

This file records the significant, non-obvious architecture decisions for Clerkstone. Each entry
follows the standard ADR shape: **Context**, **Decision**, **Consequences**. The five mandatory
records (ADR-001 → ADR-005) correspond to the decisions named in the project specification §9, §11,
§12, §8 and §7; ADR-006 and ADR-007 capture two further load-bearing choices.

Status vocabulary: **Accepted** (in force), **Superseded** (see the "Superseded by" link).

---

## ADR-001 - Modular monolith over microservices

- **Status:** Accepted

### Context

Clerkstone has four distinct domain concerns - FHIR ingest/search, the quality rule engine,
terminology resolution, and HL7 v2 conversion - each of which *could* be its own service. At the
target scale (500-5,000 synthetic patients, synchronous ingestion, single operator) a microservice
fleet would add network hops, deployment complexity, and distributed-transaction problems with no
scaling payoff. A portfolio project also has to be *demonstrably correct*, and a monolith is far
easier to test end-to-end.

### Decision

Build Clerkstone as a **modular monolith**: one FastAPI process, four domain modules
(`fhir`, `quality`, `terminology`, `hl7v2`) with narrow interfaces, and two stateless sidecars
(Nginx, the FHIR validator) that are separate containers for isolation, not for service-boundary
reasons. PostgreSQL is the only stateful service.

The seams are the interfaces, not the network:

- `TerminologyClient` protocol (ADR-004) - swap backends without touching business logic.
- `Rule` ABC + `registry.py` - rules are discoverable, versioned, independently testable modules.
- The bundle transaction layer - ingestion semantics live behind one function, not one process.

### Consequences

- **Positive:** single transaction boundary for ingest→persist→quality-run; trivial local dev
  (`make dev`); one image to build and scan; no distributed-tracing requirement.
- **Positive:** if load ever justified extraction, any module can be lifted behind its existing
  interface - the ADR already made the cut points explicit.
- **Negative:** a single process is a single failure domain; mitigated by running multiple uvicorn
  workers and keeping state out of the app (managed Postgres, stateless workers).

---

## ADR-002 - No machine learning in this project

- **Status:** Accepted

### Context

An earlier project proposal (Source C) suggested "a PyTorch model for a non-diagnostic task such as
predicting whether a record needs a data-quality review." Every task Clerkstone performs -
validation, quality rules, terminology resolution, timeline assembly - is **deterministic**. A
record "needs review" precisely when it *fails a rule*; a classifier predicting what the rule engine
already knows is decoration.

### Decision

**No ML model in the MVP.** The quality engine is a deterministic rule engine with stable rule IDs,
versions, severities, FHIRPath locations, and per-rule tests. This is the correct engineering
answer, not a limitation, for four reasons:

1. **Determinism** - in a clinical-safety context, the requirement is "same input ⇒ same output",
   not "probable output".
2. **Testability** - every rule has positive, negative and boundary unit tests plus golden-file
   regression fixtures. A learned model cannot be asserted the same way.
3. **Explainability** - a finding carries a human-readable message, a FHIRPath expression pointing at
   the offending element, and a `suggested_action` written from the rule's perspective.
4. **Auditability** - the ruleset is versioned and every report states which version ran.

The one defensible ML addition - a **triage prioritisation model** that ranks findings by predicted
human-review effort - is explicitly deferred to a later project (P5). It cannot exist until the
review workflow (V2) has generated labelled timing data, which is the honest reason to defer it.

### Consequences

- **Positive:** the project now *demonstrates knowing when not to use ML*, a stronger signal than a
  weak model; every behaviour is provable in CI.
- **Negative:** none for the stated scope. The optional triage model is tracked as an Advanced-tier
  item with an explicit data-dependency gate.

---

## ADR-003 - JSONB source of truth + relational projections

- **Status:** Accepted

### Context

FHIR resources are documents, and PostgreSQL JSONB is the correct store for documents. But the
queries Clerkstone needs - timeline joins, cohort completeness, duplication detection, physiological
range scans - are relational queries over identifiers, dates and codes, and JSONB alone would make
them slow and unindexable.

### Decision

Adopt a **hybrid** schema (spec §12):

- `fhir_resource` (JSONB `payload` + type + logical id + version + `security_hash`) is the
  **source of truth**, keyed on `UNIQUE (resource_type, logical_id, version_id)`.
- Derived 1:1 projection tables (`patient`, `encounter`, `observation`, `condition`,
  `medication_request`) hold exactly the fields needed for filtering/joining/sorting/aggregation,
  each with the indexes those queries need.
- Projections are **disposable and rebuildable**: `make rebuild-projections` reconstructs them from
  `fhir_resource`. This is a supported operation, not a migration emergency.

### Consequences

- **Positive:** full fidelity (re-emit the resource byte-for-byte on `$export`) *and* indexed query
  performance in one database.
- **Positive:** no dual-write correctness burden - the projection is a function of the resource, and
  the rebuild operation enforces that invariant.
- **Negative:** two representations can drift if a write path bypasses the projection builder; this is
  mitigated by routing all writes through `domain/fhir/projections.py` and by the rebuild invariant
  plus projection round-trip tests.

---

## ADR-004 - Terminology resolution behind a pluggable adapter (DI seam)

- **Status:** Accepted

### Context

The TERM-* quality rules must resolve SNOMED CT / dm+d / ICD-10 codes. Live resolution against the
NHS England Terminology Server requires an approved system-to-system account the project does not
(yet) hold, and a locally cached TRUD/dm+d subset is the only thing that can be redistributed/run
offline today. Hard-coding either backend would couple business logic to a specific access path.

### Decision

Define a `TerminologyClient` protocol (`backend/app/domain/terminology/base.py`) with three
implementations behind it:

- `local` - a SQLite cache built from a licensed TRUD/dm+d subset (runs offline, fully tested).
- `nhse` - an adapter for the NHS England Terminology Server (`$lookup`, `$expand`,
  `$validate-code`) with retry, timeout, circuit-breaker and rate-limit respect.
- `offline-stub` - for tests and demos with no data present.

The active backend is selected by one environment variable (`TERMINOLOGY_BACKEND=local|nhse|offline-stub`),
and the TERM-* rules call only the protocol. `nhse` is tested against **recorded HTTP fixtures**
(VCR-style), never a live service in CI.

### Consequences

- **Positive:** the demo and CI work offline today, and the live server can be swapped in later by
  changing configuration - not code. This is the dependency-injection pattern the target roles name
  explicitly.
- **Positive:** the quality report records *which* backend and subset version ran, so findings are
  reproducible.
- **Negative:** the local subset is deliberately smaller than the full terminology, so some codes
  that would resolve live will show as unresolved offline. This is surfaced explicitly, not silently
  papered over (see [Hazard_Log.md](./Hazard_Log.md) CLK-06).

---

## ADR-005 - Designing for agentic consumption

- **Status:** Accepted

### Context

A later project (P4) will wrap Clerkstone's API in an MCP server so an AI agent can query
patients/observations through tools. Rather than retrofit the API then, Clerkstone is designed to be
**agent-consumable from day one**. An agent can reason about stable identifiers, typed errors and
narrow verbs; it cannot reason about a 500 with a stack trace or a PATCH that silently mutates
state.

### Decision

The API obeys seven properties (also asserted by `tests/api/test_agent_consumability.py`):

1. **Stable, opaque identifiers** - every resource and every finding has an immutable `id` that an
   agent can reference reliably across turns.
2. **Predictable, typed errors** - every error is an `OperationOutcome` with a machine-readable
   `issue.code`, a human message, and an `expression` pointing at the offending element.
3. **Read-only by default; writes behind explicit verbs** - `POST /quality/findings/{id}/assign`,
   not `PATCH /findings/{id}` with an arbitrary body. Narrow, named, auditable operations map 1:1 to
   MCP tools.
4. **Idempotency keys on every write** - a retrying agent cannot double-create.
5. **Field-level scoping** - RBAC can express "this role may read demographics but not observations",
   because P4's tool proxies will enforce exactly that.
6. **Audit every read, not just writes** - an agent reading 40 patient records in a loop must be
   visible in the audit trail.
7. **Pagination and `_count` limits with hard server-side maxima** - an agent cannot accidentally
   pull the whole database into a context window.

### Consequences

- **Positive:** zero rework when P4 arrives; the intellectual spine of the agent project is already
  encoded and tested here.
- **Positive:** these properties are independently good API hygiene (typed errors, idempotency,
  pagination caps) that benefit human integrators too.
- **Negative:** a stricter, verb-oriented API surface costs a little more design up front; that cost
  is already paid and is the point.

---

## ADR-006 - FHIR validation in a sidecar container, not a library

- **Status:** Accepted

### Context

UK Core profile validation requires the HL7 FHIR **reference validator** (a Java jar) plus the
published UK Core package. Bundling a JRE and the validator into the Python API image would bloat it
and entangle two very different lifecycles.

### Decision

Run the validator as a **sidecar container** (`validator/` - JRE + HL7 validator jar + UK Core
package) that the API calls over HTTP for `$validate`. The API treats it as a black box producing
`OperationOutcome`.

### Consequences

- **Positive:** slim Python image; the heavyweight dependency is isolated and independently
  versioned; mirrors how a Trust isolates a reference validator.
- **Negative:** one more network hop per validation and a new failure mode (sidecar down), handled
  by the `/ready` probe (checks DB + validator reachability) and a timeout.

---

## ADR-007 - Append-only, hash-chained audit log

- **Status:** Accepted

### Context

An audit log that can be edited is not an audit trail. Healthcare governance (DCB0129 traceability,
DSPT) requires proof that reads *and* writes of patient data are recorded and that the record has
not been silently altered.

### Decision

Implement `audit_event` as an **append-only** table (no `UPDATE`/`DELETE` grants to the application
role) with a **SHA-256 hash chain**: `event_hash = SHA256(prev_hash ‖ canonical_json(event))`. A
`make verify-audit` target re-computes the chain and fails if any row was edited. Every read and
write of patient data is logged, including actor, role, action, resource, outcome, request ID and
hashed IP.

### Consequences

- **Positive:** tamper-evidence is provable in a demo and in CI - 40 lines of code that separate an
  audit log from an audit trail.
- **Negative:** append-only storage grows monotonically and the chain makes row deletion impossible
  by design; acceptable for a portfolio prototype, and the correct trade-off for a real system.

---

## Supplementary decisions (captured elsewhere)

| Concern | Where recorded |
|---|---|
| Synthetic-data-only scope; no real patient data, ever | [PRIVACY.md](./PRIVACY.md), [DATA_MINIMISATION.md](./DATA_MINIMISATION.md) |
| UK Core treated as "work in progress, not for implementation" | [DTAC_self_assessment.md](./DTAC_self_assessment.md), [DATA_LICENCES.md](./DATA_LICENCES.md) |
| Field-level RBAC scoping (observations vs demographics) | [THREAT_MODEL.md](./THREAT_MODEL.md), [Safety_Architecture.md](./Safety_Architecture.md) |
