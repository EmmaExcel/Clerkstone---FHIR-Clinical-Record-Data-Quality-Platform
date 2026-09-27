# Clerkstone - System Architecture

> Part of the Clerkstone governance/architecture documentation suite. Companion documents:
> [DECISIONS.md](./DECISIONS.md) · [THREAT_MODEL.md](./THREAT_MODEL.md) · [Safety_Architecture.md](./Safety_Architecture.md)

## 1. Overview

Clerkstone is a **modular monolith** that ingests synthetic FHIR R4 resources, validates them
against HL7 FHIR UK Core profiles, persists them in a **relational + JSONB hybrid** PostgreSQL
schema, runs a **deterministic data-quality rule engine**, and exposes a governed REST API plus a
React clinical timeline.

There are exactly six runtime components, deployed as five containers (the terminology source is a
library seam, not a service in the default build):

| # | Component | Responsibility | Container |
|---|-----------|----------------|-----------|
| 1 | **Next.js web** | Patient search, clinical timeline, quality dashboard, resource viewer | `web` |
| 2 | **Nginx reverse proxy** | TLS termination, rate limiting, CORS allow-list, request-ID injection, security headers | `nginx` |
| 3 | **FastAPI application** | FHIR ingest/search, quality rule engine, terminology resolver, HL7 v2 ADT→FHIR converter, auth/RBAC, audit, metrics | `api` |
| 4 | **PostgreSQL 16** | Source-of-truth JSONB store + relational projections + audit/quality/review tables | `db` |
| 5 | **FHIR validator sidecar** | Reference HL7 validator (jar) + UK Core package; `$validate` proxy | `validator` |
| 6 | **Terminology source** | Local cached TRUD/dm+d subset behind a pluggable adapter (`local` / `nhse` / `offline-stub`) | inside `api` |

## 2. Component diagram

```mermaid
flowchart TB
    subgraph Client["Browser"]
        WEB["Next.js 15 (App Router)<br/>TypeScript · nhsuk-react-components<br/>Patient search · Timeline · Quality dashboard"]
    end

    subgraph Edge["Edge"]
        NGINX["Nginx reverse proxy<br/>TLS termination · rate limiting<br/>CORS allow-list · request-ID injection"]
    end

    subgraph App["FastAPI (Python 3.12 · Pydantic v2)"]
        direction TB
        FHIR["fhir<br/>ingest / search"]
        QUALITY["quality<br/>rule engine (60+ rules)"]
        TERM["terminology<br/>resolver (pluggable)"]
        HL7V2["hl7v2<br/>ADT → FHIR converter"]
        CROSS["Cross-cutting: auth (JWT+RBAC) · audit · structured logging<br/>correlation IDs · exception taxonomy · metrics"]
    end

    subgraph Data["Data & integration"]
        DB[("PostgreSQL 16<br/>resource JSONB · projections<br/>audit_event · dq_run/finding · review_task")]
        VALIDATOR["FHIR Validator sidecar<br/>HL7 validator jar + UK Core package<br/>$validate · OperationOutcome"]
        TERMSRC[("Terminology source<br/>local cached subset (TRUD/dm+d)<br/>adapter → NHSE Terminology Server")]
    end

    WEB -->|"HTTPS · JWT (RS256) · CORS allow-list"| NGINX
    NGINX --> App
    FHIR --> DB
    QUALITY --> DB
    TERM --> TERMSRC
    HL7V2 --> FHIR
    FHIR -->|"validate on ingest"| VALIDATOR
    QUALITY --> VALIDATOR
```

## 3. The modular-monolith decision

Clerkstone is deployed as **one FastAPI process** (plus stateless sidecars), not as a fleet of
microservices. This is a deliberate engineering choice, not a lack of ambition:

- **The seams are inside the process.** `fhir`, `quality`, `terminology`, and `hl7v2` are separate
  domain modules with narrow interfaces (`TerminologyClient` protocol, `Rule` ABC, the bundle
  transaction layer). If the load ever justified a split, any module could be extracted behind its
  existing interface without a rewrite.
- **The workload is synchronous and small.** Ingestion of a bundle is a single request/response.
  There is no long-running queue work, so a message broker would be theatre.
- **Operational simplicity is a feature for a portfolio project.** One image, one healthcheck set,
  one database transaction boundary. Fake microservices would add deployment complexity with no
  scaling payoff at the 500-5,000-patient scale.
- **PostgreSQL is the only stateful service.** Everything else is stateless and horizontally
  scalable. The validator sidecar is isolated in its own container purely because it drags a JRE and
  the reference validator jar - a heavyweight dependency a Trust would isolate the same way.

The full reasoning is recorded in [DECISIONS.md - ADR-001](./DECISIONS.md).

## 4. "FHIR for fidelity; relational projections for query performance"

The single most important storage principle in Clerkstone:

> **FHIR for fidelity and exchange; relational projections for query performance. Projections are
> disposable and rebuildable; resources are not.**

The FHIR resource (JSONB) is the **source of truth** and the thing re-emitted on `$export`.
Relational tables are **derived projections** that exist only to make filtering, joining, sorting,
and aggregation fast. A projection must never be allowed to disagree with the resource: rebuilding
projections from resources is a supported, first-class operation (`make rebuild-projections`).

```mermaid
flowchart LR
    subgraph SourceOfTruth["Source of truth"]
        R["fhir_resource<br/>JSONB payload · type · logical_id<br/>version · last_updated · security_hash"]
    end

    subgraph Projections["Disposable relational projections"]
        P["patient"]
        E["encounter"]
        O["observation"]
        C["condition"]
        M["medication_request"]
    end

    R -->|"1-0..1 (derived, rebuildable)"| P
    P -->|"1-N"| E
    P -->|"1-N"| O
    P -->|"1-N"| C
    P -->|"1-N"| M
```

| What stays as a FHIR resource (JSONB) | What becomes a relational projection |
|---|---|
| The full resource - always | Anything filtered, joined, sorted or aggregated: identifiers, dates, codes, patient FK, status |
| Complex nested structures with no query value (`Patient.contact`, `Observation.component`, `Condition.stage`, extension trees) | Anything a quality rule needs fast access to |
| Provenance, `meta.security`, `meta.profile` | Anything the UI lists on a page (timeline entries) |
| Resource history / versions | Anything the audit log references |

The projection columns are chosen to serve three concrete consumers: the timeline query
(`idx_obs_patient_time`, `idx_enc_patient_start`), the quality engine's cohort/duplication rules
(`idx_obs_code`, `idx_patient_birth`), and the audit join (`patient.logical_id`).

## 5. Data flows

### 5.1 Ingest → validate → store → quality run

```mermaid
sequenceDiagram
    autonumber
    participant C as Client (analyst)
    participant A as FastAPI
    participant V as FHIR Validator
    participant D as PostgreSQL
    participant T as Terminology

    C->>A: POST /api/v1/fhir (Bundle transaction)
    A->>A: parse (fhir-resources Pydantic) · de-duplicate by logical_id
    A->>V: structural + UK Core profile validation
    V-->>A: OperationOutcome
    A->>D: persist fhir_resource rows (+ projections, provenance, audit)
    A->>A: run quality rules (60+ deterministic rules)
    A->>T: TERM-* rules resolve codes (local subset)
    A->>D: persist dq_run + dq_finding rows
    A-->>C: 201 · bundle_id · status · OperationOutcome · quality_run_id
```

### 5.2 Clinical read path

```mermaid
sequenceDiagram
    autonumber
    participant C as Client (reader)
    participant N as Nginx
    participant A as FastAPI
    participant D as PostgreSQL

    C->>N: GET /api/v1/patients/{id}/timeline (JWT)
    N->>N: rate limit · inject X-Request-Id
    N->>A: forward
    A->>A: verify JWT (RS256) · RBAC dependency · field-level scope
    A->>D: join patient → encounter/observation/condition/medication_request
    D-->>A: projection rows (+ inline quality_flags)
    A->>D: append audit_event (read.patient)
    A-->>C: JSON timeline · synthetic_data_notice
```

## 6. Deployment topology

```mermaid
flowchart TB
    subgraph CI["GitHub Actions"]
        LINT["lint / type / test / coverage gate"]
        FE["frontend lint / type / vitest / Playwright / axe"]
        BUILD["docker build (api, web, validator)"]
        SCAN["trivy + pip-audit + npm audit (fail HIGH/CRITICAL)"]
        PUSH["on tag v*: push images to GHCR"]
        LINT --> BUILD --> SCAN
        FE --> SCAN
        SCAN --> PUSH
    end

    subgraph Host["Deploy (Fly.io / Render / Hetzner VPS)"]
        PROXY["Caddy or Nginx<br/>TLS (Let's Encrypt) · rate limiting · security headers"]
        subgraph Apps["Stateless containers"]
            WEB["web (Next.js standalone)"]
            API["api (uvicorn, 2 workers)"]
            VAL["validator (HAPI validator jar)"]
        end
        DBEXT["managed Postgres (NOT containerised)"]
        PROXY --> WEB
        PROXY --> API
        API --> VAL
        API --> DBEXT
    end

    PUSH --> Host
    Host --> MON["Healthchecks + uptime monitor"]
    Host --> LOGS["Structured logs → provider drain"]
    Host --> METRICS["/metrics scraped (optional Grafana Cloud)"]
```

The **stateless / stateful split** is deliberate: containers for stateless apps, a **managed**
Postgres for state. Containerising the database in production is explicitly avoided - that
distinction is the kind of judgement an NHS engineering lead looks for (see
[RUNBOOK.md](./RUNBOOK.md)).

## 7. What is deliberately left out

- **No Kubernetes** - not evidenced by the target roles; docker compose is right-sized.
- **No message queue** - ingestion is synchronous and small.
- **No ML service** - every task is deterministic (see [DECISIONS.md - ADR-002](./DECISIONS.md)).
- **No separate microservice split** - a modular monolith is the correct architecture at this scale.
- **No Redis** - PostgreSQL handles the caching Clerkstone needs.
