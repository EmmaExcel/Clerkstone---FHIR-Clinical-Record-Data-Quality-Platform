# Clerkstone - Operational Runbook

> Day-2 operations for Clerkstone. Companion documents: [architecture.md](./architecture.md) ·
> [THREAT_MODEL.md](./THREAT_MODEL.md) · [API_GUIDE.md](./API_GUIDE.md).

## 1. Topology reminder

Six logical components, five containers, one managed service:

| Component | Container / service | Stateful? |
|---|---|---|
| Next.js web | `web` (Next.js standalone) | no |
| Nginx / Caddy | reverse proxy | no |
| FastAPI | `api` (uvicorn, 2 workers) | no |
| FHIR validator | `validator` (HAPI validator jar) | no |
| Terminology | inside `api` (adapter) | local SQLite cache only |
| PostgreSQL | **managed** (Fly Postgres / Neon), never a container in prod | **yes** |

**The one rule that governs everything else:** containers are for stateless apps; managed services
are for state. Never containerise the database in production.

## 2. Deploy

### 2.1 What goes public vs what stays local

| Public (deploy it) | Local only (never deploy) |
|---|---|
| Frontend + API on the **20-patient committed fixture** | The 500- and 5,000-patient generated datasets |
| OpenAPI docs (`/docs`) - read-only | The Simulacrum extract (5.22 GB, form-gated) |
| Read-only demo credentials (`demo-reader` / `demo-analyst`) | Any TRUD-derived SNOMED CT subset |
| Static docs site (GitHub Pages) | MIMIC-IV Demo data (link, don't host) |
| Container images on GHCR | **Your JWT private keys** |

### 2.2 CI/CD path

```
GitHub push ─▶ GitHub Actions
   ├─ lint / type / test / coverage gate
   ├─ frontend lint / type / vitest / Playwright / axe
   ├─ docker build (api, web, validator)
   ├─ trivy + pip-audit + npm audit  ── fail on HIGH/CRITICAL
   └─ on tag v*:  push images to GHCR
                        │
                        ▼
      Deploy (Fly.io / Render / £5 Hetzner VPS)
      ┌─────────────────────────────────────────┐
      │ Caddy/Nginx - TLS (Let's Encrypt),      │
      │ rate limiting, security headers         │
      │   ├─ web      (Next.js standalone)      │
      │   ├─ api      (uvicorn, 2 workers)      │
      │   ├─ validator (HAPI validator jar)     │
      │   └─ db       (managed Postgres)        │
      └─────────────────────────────────────────┘
```

### 2.3 Release checklist

1. `make test` green locally (unit + golden + integration + authz matrix).
2. `make verify-audit` passes against a scratch DB (proves the audit chain computes).
3. Tag `v⟨X.Y.Z⟩` → CI builds and pushes to GHCR.
4. `make smoke-test` against the deployed URL: `GET /health` and one **authenticated** read.
5. Confirm `/ready` reports DB + validator reachable.

### 2.4 Configuration secrets

Secrets are **injected at runtime**, never baked into images:

- `JWT_PRIVATE_KEY_PATH` / `JWT_PUBLIC_KEY_PATH` - from `/run/secrets/…`
- `DATABASE_URL` - managed Postgres connection string
- `AUDIT_HASH_SALT` - secret store only
- `TERMINOLOGY_NHSE_API_KEY` - only if using `TERMINOLOGY_BACKEND=nhse`
- `.env.example` is committed; `.env` is gitignored; `make check-secrets` runs gitleaks.

## 3. Investigate a failed quality run

### 3.1 Recognise the failure

A quality run has status `running | complete | failed`. A **failed** run means the run itself did not
complete (exception, validator unavailable, DB timeout) - *not* that findings were produced. Findings
are the normal, expected output of a **complete** run.

### 3.2 Steps, in order

1. **Get the run record.**
   `GET /api/v1/quality/runs/{id}` → note `ruleset_version`, `scope`, `status`, and any partial
   `counts`.

2. **Find the request.** The response's correlation ID (`X-Request-Id`, injected by Nginx and
   carried into the audit log) is the join key. Pull the structured log lines for that ID:
   `jq 'select(.request_id == "<id>")' <log-drain>`.

3. **Check the two dependencies the run touches.**
   - `GET /ready` → does it report the validator reachable? If not, that is usually the cause
     (validator container down, or `VALIDATOR_TIMEOUT_SECONDS` too low for a large bundle).
   - `DB_STATEMENT_TIMEOUT_MS` exceeded → a slow analytical query (duplication / cohort rules) on a
     cold index.

4. **Look at the failure mode, not just the error.**
   - Timeout → increase `VALIDATOR_TIMEOUT_SECONDS` or `DB_STATEMENT_TIMEOUT_MS`; re-run.
   - `unresolved` terminology (not a failure, but a *signal*) → check the resolver mode recorded in
     the run summary (`local-subset` vs `nhse-live`). If the local subset is missing codes, that is a
     data-completeness issue, not a bug.

5. **Re-run idempotently.** A quality run is read-only against the resource store (it only writes
   `dq_run`/`dq_finding`). Re-running with the same `scope` and `ruleset_version` must produce the
   same findings - if it does not, that is a determinism regression and a release blocker.

### 3.3 Determinism check (the key diagnostic)

The engine is deterministic (see [DECISIONS.md - ADR-002](./DECISIONS.md)). If two runs with the
same scope and ruleset version differ, suspect: (a) a rule reading a wall-clock value instead of the
resource's own dates, (b) an unordered iteration leaking into the output, or (c) a changed ruleset
version between runs. The golden-file suite is the regression net for all three.

## 4. Restore

### 4.1 Restore from a failed/partial ingestion

Ingestion is **transactional per bundle** with partial-success semantics: a bundle either fully
applies, or is recorded with `status: partial|rejected` and its `operation_outcome`. There is no
half-written resource state to recover. To recover a *bad* bundle:

1. Identify the bundle by `bundle_id` (returned on `POST /fhir`).
2. If resources were wrongly persisted, they carry `source_bundle` → `ingestion_bundle.id`, so they
   can be traced and removed by a targeted, audited operation.
3. Re-run `make load` against the fixture to re-establish a known-good state.

### 4.2 Restore the database

- **Local/dev:** `make migrate` applies Alembic migrations forward; `make rebuild-projections`
  reconstructs projections from `fhir_resource` (the source of truth) - use this after any
  projection drift.
- **Prod:** restore the managed Postgres from its point-in-time backup (managed service), then
  `make rebuild-projections` and `make verify-audit` to confirm integrity post-restore.

### 4.3 Restore the terminology cache

The local cache is rebuildable from the licensed TRUD/dm+d subset:
`make build-terminology` → writes `TERMINOLOGY_LOCAL_DB_PATH`. After any rebuild, record the new
subset version so reports stay reproducible.

## 5. Rotate keys

### 5.1 JWT signing key rotation

JWT is RS256 with a short-lived access token (15 min) and a separate refresh path. Rotation:

1. Generate a new keypair (`openssl genrsa …` → private PEM; derive public PEM).
2. Put the **new public key** into the API's trust location and **add the old public key** to the
   allowed set for a grace window (so in-flight 15-min tokens still verify).
3. Update the private key at `JWT_PRIVATE_KEY_PATH` for the *issuer* only after the grace window
   begins; keep the old private key accessible until the last issued token expires (≤ 15 min).
4. Remove the old public key from the trust set once the max token TTL has elapsed.
5. Restart the API; `GET /health` then one authed read as a smoke check.

Because access tokens are 15 minutes, key rotation is fully drained within 15 minutes - the point of
the short TTL.

### 5.2 Other secrets

| Secret | Rotation note |
|---|---|
| `DATABASE_URL` password | Rotate in the managed Postgres; update the runtime secret; restart `api` |
| `AUDIT_HASH_SALT` | **Do not rotate casually.** Changing the salt invalidates the hash-chain continuity (`prev_hash` links). If it must change, re-anchor the chain and document the break in a release note. |
| `TERMINOLOGY_NHSE_API_KEY` | Rotate in the system-to-system account; update the secret store only |

## 6. Health and observability

| Check | What it proves |
|---|---|
| `GET /health` | Process liveness |
| `GET /ready` | DB **and** validator reachable |
| `GET /metrics` | Prometheus: request-duration histograms, rule-execution timers |
| Structured logs | JSON, correlation IDs propagated from Nginx |
| `make verify-audit` | Audit hash chain intact (run in CI **and** on a schedule) |

## 7. Incident template

```
Severity:   (error | warning | info)
Correlation: <X-Request-Id>
Component:  (api | web | db | validator | nginx)
Run/Bundle: <id> or n/a
Symptom:    …
Diagnosis:  …
Fix:        …
Prevent:    (new rule? new fixture? new monitor?)
```

If the incident revealed a data defect the taxonomy did not anticipate, the remediation is a **new
rule + fixture + ruleset version** - see [DEFECT_TAXONOMY.md](./DEFECT_TAXONOMY.md) §4.
