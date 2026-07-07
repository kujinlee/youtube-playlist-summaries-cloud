# Stage 1E-a — Durable Job Queue + Lifecycle — Design Spec

**Date:** 2026-07-06
**Status:** Draft v1 — brainstormed, pending grill-with-docs + Codex adversarial review + user approval.
**Parent:** `docs/superpowers/specs/2026-07-01-cloud-publishing-architecture-design.md` §9, and the 2026-07-06 roadmap revision in §10.
**Stage:** 1E-a (first of three worker sub-slices: 1E-a queue → 1E-b worker+ingestion → 1E-c polling).

---

## 1. Goal & scope

Build a **durable, cloud-only job queue** with a full lifecycle, so that expensive work (summaries, dig) can later be run by a separate worker instead of inline in the request. This slice builds and tests the queue **machinery only** — it runs a trivial stub handler, not the real Gemini pipeline.

**In scope:**
- A Postgres `jobs` table with owner-scoped RLS and an idempotency key.
- The cloud `JobQueue` implementation: enqueue / status / cancel (producer) and claim / heartbeat / complete / fail (worker).
- A worker-runner loop that claims jobs, runs a stub handler, finalizes them, and sweeps expired leases.
- Integration + unit tests covering the whole lifecycle against local Supabase Postgres.

**Out of scope (later slices):**
- The real ingestion handler (Gemini YouTube-URL → cloud storage) — **1E-b**.
- Progress polling API + client — **1E-c**.
- Quota debit / spend reservation on enqueue — **1D** (hooks into the same idempotency key).
- Deploy, scheduled sweeps (pg_cron), health checks — **1H**.

**Non-goal:** touching the local tool. The local app keeps running ingestion **inline with SSE** and its in-memory `job-registry`. No local `JobQueue` impl exists.

---

## 2. Why this shape

Three decisions from the 2026-07-06 brainstorming (recorded in the parent §10):

1. **Reorder — 1E before 1D.** 1D's guardrails are preflight gates on the enqueue transaction; that transaction does not exist until the queue does. Build the queue first so 1D gates a real path.
2. **The durable queue is cloud-only.** A single-user, single-process local tool gains nothing from Postgres-backed durability, and forcing it there risks the working SSE path. Storage is a genuine two-sided seam (same verbs, different backend); job *execution topology* (inline vs. worker) is not — so we do not invent a fake local queue impl.
3. **Hand-rolled Postgres queue (`SELECT … FOR UPDATE SKIP LOCKED`), not pg-boss.** Our requirements — an RLS-owned `jobs` table, a domain idempotency tuple, a future 1D quota FK, and only two job types — make a single owned table simpler to reason about than reconciling pg-boss's parallel lifecycle. `SKIP LOCKED` is the same primitive pg-boss uses internally. This overrides §9's stated pg-boss pick, which predated the seam + RLS-jobs framing.

---

## 3. Execution model & the `JobQueue` seam

The local tool runs ingestion **inline**: the pipeline executes inside the request handler and streams progress over SSE (`app/api/ingest/stream/route.ts` + `lib/job-registry.ts`). The cloud model is the opposite: enqueue a row, a separate worker runs it, the client polls.

We resolve this asymmetry cleanly:

- **`JobQueue` is cloud-only.** The cloud storage bundle exposes an optional `jobQueue`; the local bundle has none.
- **The producer interface is uniform** (used by cloud routes in later slices):
  - `enqueue(key, payload) → { jobId, joined }`
  - `getStatus(jobId) → JobStatus`
  - `requestCancel(jobId) → void`
- **The worker interface exists only on the cloud impl** (used by the worker runner):
  - `claim(workerId) → LeasedJob | null`
  - `heartbeat(jobId, workerId) → { ok: boolean }`  (`ok:false` means the lease was lost)
  - `complete(jobId, result) → void`
  - `fail(jobId, error, { retryable }) → void`
- **Routes branch once.** When a `jobQueue` is present (cloud), a route enqueues and returns a job id to poll; otherwise it runs inline exactly as today. Execution topology stays an impl detail behind the bundle. *(No route changes land in 1E-a; this is the contract later slices consume.)*

`key` is the domain idempotency tuple `(owner_id, document_id, artifact_type, version)`. In 1E-a `owner_id` comes from the authenticated principal; `document_id` / `artifact_type` / `version` are supplied by the caller (tests use placeholder values since there is no real handler yet).

---

## 4. Data model — the `jobs` table (migration `0008`)

```sql
create table jobs (
  id            uuid primary key default gen_random_uuid(),
  owner_id      uuid not null references profiles(id),
  -- idempotency tuple (the domain key)
  document_id   text not null,
  artifact_type text not null,      -- 'summary' | 'dig' (extensible)
  version       int  not null,
  status        text not null default 'queued',  -- queued|active|completed|failed|dead_letter|cancelled
  payload       jsonb not null,     -- handler input (opaque to the queue)
  result        jsonb,              -- handler output on success
  error         text,
  attempts      int  not null default 0,
  max_attempts  int  not null default 5,
  -- leasing
  locked_by         text,
  lease_expires_at  timestamptz,    -- null when not leased
  run_after         timestamptz not null default now(),  -- backoff / scheduled start
  -- cancellation (cooperative)
  cancel_requested  boolean not null default false,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

-- IDEMPOTENCY: at most one *live* job per logical artifact
create unique index jobs_idem_live on jobs (owner_id, document_id, artifact_type, version)
  where status in ('queued','active');
```

**Idempotency = a partial unique index over live states only.** Enqueuing a key while a job is `queued`/`active` conflicts → return the existing job (`joined:true`). A terminal job (`completed`/`failed`/`dead_letter`/`cancelled`) with the same key does **not** block a fresh enqueue, so re-runs after failure and new versions work. This is where 1D will later anchor its "charge quota once per live job."

**RLS mirrors 1B §5.4 / 1C exactly** (no new ownership convention):
- Force RLS; owner policy `owner_id = auth.uid()` for `select` (so 1E-c's polling reads directly under RLS).
- `enqueue` is a `SECURITY INVOKER` RPC stamping `owner_id = auth.uid()`.
- The worker claims/updates via `service_role` (bypasses RLS, same confinement as 1C — nothing imports the service client outside the worker path).
- Table grants to `authenticated` per the `0006_grants` convention.

---

## 5. Lifecycle & the worker-runner loop

The worker runner is a long-lived loop: **claim → run stub handler → finalize**, with a lease-reclaim sweep each pass.

**Claim** — one atomic statement leases the oldest eligible row:

```sql
UPDATE jobs SET status='active', locked_by=$w, lease_expires_at=now()+interval '2 min', updated_at=now()
WHERE id = (SELECT id FROM jobs
            WHERE status='queued' AND run_after <= now()
            ORDER BY created_at
            FOR UPDATE SKIP LOCKED LIMIT 1)
RETURNING *;
```

`FOR UPDATE SKIP LOCKED` guarantees no two workers claim the same job — losers skip the locked row and take the next.

**Heartbeat** — mid-run, the worker extends `lease_expires_at` roughly every `ttl/4`. A heartbeat that finds the lease already lost (row reclaimed) tells the worker to abort.

**Finalize** — success → `status='completed'` + `result`. Failure paths:

| What happens | How we detect it | Result |
|---|---|---|
| Worker dies mid-job | sweep finds `active` + `lease_expires_at < now()` | → `queued`, `attempts += 1` |
| Handler throws (retryable) | exception in run, `fail(...,{retryable:true})` | `attempts < max` → `queued`, `run_after = now()+backoff` |
| Attempts exhausted | retryable failure with `attempts ≥ max_attempts` | → `dead_letter` |
| Handler throws (non-retryable) | `fail(...,{retryable:false})` | → `failed` (terminal, no retry) |
| Cancel requested | `cancel_requested = true` | cooperative → `cancelled` (immediate if still `queued`) |

**`failed` vs `dead_letter`:** `failed` is a *deliberate* terminal state for errors the handler knows are not worth retrying (bad input, permanent rejection). `dead_letter` is for retryable errors that *exhausted* their attempts. Both are terminal and both free the idempotency key for a fresh enqueue.

**Two approved decisions:**
1. **A crash-reclaim counts as a failed attempt** — so a job that serially kills its worker eventually reaches `dead_letter` instead of re-leasing forever.
2. **The worker runs the reclaim sweep itself, each loop** — no separate scheduler in 1E-a. A scheduled sweep (pg_cron) is deferred to 1H.

**Cancellation is cooperative** — no preemptive kill. `requestCancel` flips the flag; the worker checks it at safe checkpoints and unwinds cleanly.

**Stub handler:** in 1E-a the run step is an identity/echo over `payload`. This exercises the full state machine without the ingestion pipeline. The real handler is injected in 1E-b.

**Default settings** (config-driven, tunable): `lease_ttl = 120s`, `heartbeat_interval = 30s`, `max_attempts = 5`, `backoff = 10 · 4^(n−1) s` (10s → 40s → ~2.5min → …).

---

## 6. Deliverables & dormancy

Four pieces:
1. Migration `0008` — `jobs` table, idempotency index, RLS policies, `enqueue` RPC.
2. `PostgresJobQueue` — producer + worker methods above.
3. The worker-runner loop with the stub handler and inline reclaim sweep.
4. Cloud bundle wiring — expose optional `jobQueue`; local bundle has none.

**Ships dormant, like 1A–1C:** the queue is fully built and tested, but no live route uses it and it is not deployed. The local tool is untouched. Merging 1E-a carries no runtime risk.

---

## 7. Testing strategy

TDD (strong fit: core logic, branching, concurrency, data integrity), via subagent-driven development.

**Integration tests** (local Supabase Postgres, same harness as 1C):
- Enqueue creates a `queued` job. Same live key → joins (same id, no duplicate). Same key after terminal → new job allowed.
- Claim leases exactly one job; two concurrent claims get distinct jobs (or one gets `null`) — never the same job.
- Heartbeat extends the lease; heartbeat after reclaim → `ok:false`.
- Sweep re-queues an expired-lease `active` job and increments `attempts`.
- Fail under max → `queued` with backoff `run_after`; fail at max → `dead_letter`.
- Cancel: `queued` → `cancelled` immediately; `active` → flag set, worker stops, `cancelled`.
- RLS: owner sees only own jobs; another user cannot see or enqueue into them; worker (service_role) can update.

**Unit tests:** backoff formula; status-transition guards; eligibility predicate helpers (pure functions).

---

## 8. Deferred / dependencies

- **1E-b** injects the real ingestion handler; adds worker runtime budgets (wall-clock/disk/memory/concurrency) and graceful shutdown.
- **1E-c** builds the polling status API + client over the `getStatus`/RLS reads this slice provides.
- **1D** adds atomic quota debit + spend reservation to `enqueue`, keyed to the idempotency tuple so retries never re-charge.
- **1H** adds scheduled sweeps (pg_cron), health/readiness, deploy, secrets.

---

## 9. Open questions

- **Dead-letter visibility:** do owners see their `dead_letter` jobs (RLS `select` already allows it), or are those admin-only? Default: visible to owner (a failed job the user can see and retry). Revisit in 1E-c when the polling UI is designed.
- **`enqueue` return on join:** confirm it returns the *existing* job's current status too (so the caller can immediately poll), not just the id. Leaning yes.
