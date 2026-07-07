# Stage 1E-a — Durable Job Queue + Lifecycle — Design Spec

**Date:** 2026-07-06 (v2: 2026-07-07)
**Status:** Draft v2 — hardened after two independent adversarial reviews (Codex `gpt-5.5` + Claude). See `docs/reviews/stage-1e-a-durable-job-queue-spec-codex.md` and `...-spec-claude-review.md`. Pending grill-with-docs + user approval.
**Parent:** `docs/superpowers/specs/2026-07-01-cloud-publishing-architecture-design.md` §9, and the 2026-07-06 roadmap revision in §10.
**Stage:** 1E-a (first of three worker sub-slices: 1E-a queue → 1E-b worker+ingestion → 1E-c polling).

---

## 1. Goal & scope

Build a **durable, cloud-only job queue** with a full lifecycle, so expensive work (summaries, dig) can later run in a separate worker instead of inline. This slice builds and tests the queue **machinery only** — it runs a trivial stub handler, not the real Gemini pipeline.

**In scope:** Postgres `jobs` table (owner-scoped RLS, idempotency key, lease fencing); the cloud `JobQueue` impl (enqueue/status/cancel + claim/heartbeat/complete/fail); a worker-runner loop with a stub handler and lease-reclaim sweep; full integration + unit tests against local Supabase Postgres.

**Out of scope (later slices):** real ingestion handler → **1E-b**; polling API + client → **1E-c**; quota debit / spend reservation → **1D**; deploy, scheduled sweeps (pg_cron), health checks, dead-letter retention/archival → **1H**.

**Non-goal:** touching the local tool. It keeps running ingestion **inline with SSE** and its in-memory `job-registry`. No local `JobQueue` impl exists.

---

## 2. Why this shape

Three decisions from the 2026-07-06 brainstorming (recorded in parent §10):

1. **Reorder — 1E before 1D.** 1D's guardrails are preflight gates on the enqueue transaction; that transaction doesn't exist until the queue does.
2. **The durable queue is cloud-only.** A single-user, single-process local tool gains nothing from Postgres durability, and forcing it there risks the working SSE path. Storage is a genuine two-sided seam; job *execution topology* (inline vs. worker) is not.
3. **Hand-rolled Postgres queue (`SELECT … FOR UPDATE SKIP LOCKED`), not pg-boss.** An RLS-owned `jobs` table, a domain idempotency tuple, a future 1D quota FK, and only two job types make one owned table simpler than reconciling pg-boss's parallel lifecycle. This overrides §9's pg-boss pick — see §10 for the obligations we take on by doing so.

---

## 3. Execution model & the `JobQueue` seam

The local tool runs ingestion **inline** (pipeline inside the request, SSE progress, `lib/job-registry.ts`). The cloud model enqueues a row, a separate worker runs it, the client polls. We resolve the asymmetry:

- **`JobQueue` is cloud-only.** The cloud storage bundle exposes an optional `jobQueue`; the local bundle has none.
- **Producer interface (used by cloud routes in later slices):**
  - `enqueue(key, payload) → { jobId, status, joined }` — atomic; on join, also returns the existing job's current `status` (resolves v1 open-question Q2).
  - `getStatus(jobId) → JobStatus`
  - `requestCancel(jobId) → void`
- **Worker interface (cloud impl only, consumed by the worker runner) — all fenced on lease ownership:**
  - `claim(workerId) → LeasedJob | null` — returns a fresh **`lease_token`** (uuid) with the job.
  - `heartbeat(jobId, workerId, leaseToken) → { ok }` — `ok:false` ⇒ lease lost, worker must abort.
  - `complete(jobId, workerId, leaseToken, result) → { ok }`
  - `fail(jobId, workerId, leaseToken, error, { retryable }) → { ok }`

  Every worker mutation runs `… WHERE id=$1 AND locked_by=$w AND lease_token=$t AND status='active'`. **0 rows updated ⇒ the worker lost the lease (reclaimed/cancelled); it discards its result and stops.** This is the core fix for double-execution (Codex B1 / Claude B1).

- **Routes branch once.** When a `jobQueue` is present (cloud), a route enqueues and returns a job id to poll; otherwise it runs inline as today. No route changes land in 1E-a; this is the contract later slices consume.

`key` is the domain idempotency tuple `(owner_id, document_id, artifact_type, version)`. `owner_id` comes from the authenticated **or anonymous** principal (parent §7 requires anon guest jobs). In 1E-a the other three are caller-supplied (tests use placeholders).

---

## 4. Data model — the `jobs` table (migration `0008`)

```sql
create table jobs (
  id            uuid primary key default gen_random_uuid(),
  owner_id      uuid not null references profiles(id),
  document_id   text not null,
  artifact_type text not null,      -- 'summary' | 'dig' (extensible)
  version       int  not null,
  status        text not null default 'queued',  -- queued|active|completed|failed|dead_letter|cancelled
  payload       jsonb not null,
  result        jsonb,
  error         text,
  attempts      int  not null default 0,
  max_attempts  int  not null default 5,
  -- leasing (fenced)
  locked_by         text,
  lease_token       uuid,           -- rotated on every claim; null when not leased
  lease_expires_at  timestamptz,
  run_after         timestamptz not null default now(),
  -- cancellation (cooperative)
  cancel_requested  boolean not null default false,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

-- IDEMPOTENCY: at most one live-OR-succeeded job per logical artifact
create unique index jobs_idem_active on jobs (owner_id, document_id, artifact_type, version)
  where status in ('queued','active','completed');

-- HOT PATHS
create index jobs_claim  on jobs (run_after, created_at, id) where status = 'queued';
create index jobs_sweep  on jobs (lease_expires_at)          where status = 'active';
create index jobs_owner  on jobs (owner_id, created_at);     -- polling/listing (1E-c)
```

**Idempotency = a partial unique index over `{queued, active, completed}`** (revised from v1's live-only set — Codex B4 / Claude H2). This enforces "at most one live *or already-succeeded* job per `(owner, document, artifact, version)`." Consequences:
- Enqueuing a key with a `queued`/`active` job → **join** the running job.
- Enqueuing a key with a `completed` job → **join/return the completed job**; it does **not** re-run paid work or regenerate the source-of-truth blob, and 1D does not re-charge. A legitimate re-run requires a **new `version`**.
- Only `failed` / `cancelled` / `dead_letter` are excluded from the index → a fresh enqueue after one of those is allowed (retry).

**Enqueue is one atomic RPC** (resolves Codex B3 / Claude B3):
```sql
-- inside a single SECURITY INVOKER function, owner_id := auth.uid()
insert into jobs (owner_id, document_id, artifact_type, version, payload)
values (auth.uid(), $doc, $type, $ver, $payload)
on conflict (owner_id, document_id, artifact_type, version)
  where status in ('queued','active','completed')
  do nothing
returning id, status, false as joined;
-- if no row returned: select the conflicting live/completed row and return it as joined=true;
-- if THAT select finds nothing (row went terminal-failed/cancelled in the gap): retry the insert (bounded loop).
```

**RLS (revised — Codex B2 / Claude H1)** mirrors 0002's `with check` convention, not v1's select-only:
- Force RLS. Policies: `for select using (owner_id = auth.uid())`; `for insert with check (owner_id = auth.uid())`; `for update using (owner_id = auth.uid()) with check (owner_id = auth.uid())` (owner-scoped `requestCancel`).
- `enqueue` / `requestCancel` are `SECURITY INVOKER` (writes pass the `with check`).
- The **worker** claims/heartbeats/completes/fails via `service_role` (bypasses RLS; same confinement story as 1C — see §6).
- **Grants** follow the 0006 convention: `select, insert, update` to `anon, authenticated, service_role` (anon required for guest enqueue, parent §7).

---

## 5. Lifecycle, state machine & the worker loop

The worker runner loops: **claim → run stub handler → finalize**, with a lease-reclaim sweep each pass.

**Claim** — one atomic statement leases the oldest eligible row and mints a lease token:
```sql
update jobs set status='active', locked_by=$w, lease_token=gen_random_uuid(),
       lease_expires_at=now()+interval '2 min', updated_at=now()
where id = (select id from jobs
            where status='queued' and run_after <= now()
            order by created_at, id
            for update skip locked limit 1)
returning *;   -- includes lease_token
```
`FOR UPDATE SKIP LOCKED` guarantees no two workers claim the same job. `order by created_at, id` gives stable FIFO (Claude L4).

**Attempts counted once per execution.** `attempts` = number of failed executions. It is incremented **exactly once** in whichever fenced terminal update wins — either the worker's `fail()` *or* the sweep's reclaim, never both, because both fence on `(locked_by, lease_token, status='active')` and the first to run rotates/clears the lease so the other no-ops (Codex H1 / Claude H4).

**State machine (guarded transitions — Codex H2).** Every transition is a guarded SQL update; terminal states (`completed`, `failed`, `dead_letter`, `cancelled`) are immutable except an explicit admin/retry op.

| From | Event | To | Guard |
|---|---|---|---|
| — | enqueue | `queued` | idempotency RPC (§4) |
| `queued` | claim | `active` | `FOR UPDATE SKIP LOCKED` |
| `active` | heartbeat | `active` | fence; extends lease |
| `active` | handler ok **and** not cancel_requested | `completed` | fence **and** `cancel_requested=false` |
| `active` | handler throws, retryable, `attempts+1 < max` | `queued` (backoff) | fence; `attempts+=1`, `run_after=now()+backoff` |
| `active` | handler throws, retryable, `attempts+1 ≥ max` | `dead_letter` | fence; `attempts+=1` |
| `active` | handler throws, non-retryable | `failed` | fence |
| `active` | lease expired (sweep), `attempts+1 < max` | `queued` | `attempts+=1`, lease cleared |
| `active` | lease expired (sweep), `attempts+1 ≥ max` | `dead_letter` | `attempts+=1` (fixes crash-loop, Claude B2) |
| `active`/`queued` | cancel requested | `cancelled` | see below |

**`failed` vs `dead_letter`:** `failed` = handler declared the error not worth retrying (bad input); `dead_letter` = retryable errors that exhausted attempts, *including crash-loops* (the sweep now dead-letters at max, so a job that always kills its worker cannot re-lease forever). Both are terminal.

**Cancellation (cooperative, and honored on every exit — Codex M1 / Claude M2/L1).**
- `requestCancel` runs one statement: set `cancel_requested=true` always, **and** flip `queued → cancelled` in the same update (`where status='queued'`), so a job claimed in the gap isn't missed.
- An `active` job's worker checks `cancel_requested` **before and after** each expensive/side-effecting step and unwinds to `cancelled`.
- If an active, cancel-requested job instead *throws*, `fail()` short-circuits to `cancelled` (not queued/failed) so a cancel is never silently converted to a retry or failure.

**Sweep** runs each worker loop (Codex M3): it reclaims expired-lease `active` rows using its own `FOR UPDATE SKIP LOCKED` so concurrent workers' sweeps don't collide. (A scheduled/pg_cron sweep is deferred to 1H; the inline sweep keeps 1E-a self-contained.)

**Concurrency invariant vs. the local tool (Codex M2 — needs your confirmation, see §9).** The local tool serializes ingestion per output folder (`activeByFolder`). The cloud model deliberately does **not** take a coarse per-playlist lock: idempotency prevents duplicate work on the *same* `(owner, document, artifact, version)`, and cross-artifact safety within a playlist rests on **1C's transactional `MetadataStore` methods** (`claimVideoSlot` row-lock, `reconcile*`), not on a queue-level lock. This is a deliberate divergence, stated so 1E-b's handler can rely on it.

**Stub handler with a checkpoint (Claude M1).** The 1E-a handler is an echo, but exposes an **injectable await/checkpoint** so tests can pause it mid-run — which is what makes the lost-lease abort path and cancel-mid-run path actually exercisable in integration tests.

**Default settings** (config-driven, tunable): `lease_ttl=120s`, `heartbeat_interval=30s`, `max_attempts=5`, `backoff=10·4^(n−1) s` (10s → 40s → ~2.5min → …).

---

## 6. Deliverables & dormancy

1. Migration `0008` — `jobs` table, idempotency + hot-path indexes, RLS policies + grants, `enqueue` and `request_cancel` RPCs.
2. `PostgresJobQueue` — producer + fenced worker methods.
3. Worker-runner loop with the checkpoint-able stub handler and inline reclaim sweep.
4. Cloud bundle wiring — expose optional `jobQueue`; local bundle has none.

**Worker confinement (Claude M5).** The worker runner is a **separate long-lived entrypoint**, not reachable from the Next.js app bundle. It is the only `service_role` consumer here; the existing import-graph confinement scan (from 1B/1C) is **extended to cover the worker entrypoint** so the service client can't leak into a route.

**Ships dormant, like 1A–1C:** fully built and tested, but no live route uses it and it isn't deployed. The local tool is untouched. Merging carries no runtime risk.

---

## 7. Testing strategy

TDD (core logic, branching, concurrency, data integrity), via subagent-driven development.

**Integration tests** (local Supabase Postgres, 1C harness):
- Enqueue creates `queued`. Same live key → joins (same id + status, no dup). Same key when `completed` → joins the completed job, **no new work**. Same key after `failed`/`cancelled` → fresh job allowed.
- Concurrent enqueue of the same key (parallel) → exactly one insert, the other joins; never two live rows.
- Claim leases one job with a lease token; two concurrent claims get distinct jobs (or one `null`).
- **Fencing:** a stale `(workerId, leaseToken)` calling `complete`/`fail`/`heartbeat` after reclaim → `ok:false`, no state change; the current lease owner's call succeeds. (Uses the stub checkpoint to force the stall.)
- Sweep re-queues an expired-lease job and increments `attempts` once; a job at `attempts=max-1` whose lease expires → `dead_letter` (crash-loop bound).
- Fail retryable under max → `queued` + backoff `run_after`; non-retryable → `failed`; retryable at max → `dead_letter`.
- Cancel: `queued` → `cancelled` immediately; `active` → checkpoint observes flag → `cancelled`; active+cancel that throws → `cancelled`, not failed/queued.
- RLS: owner sees only own jobs; another user cannot `select`/`insert`/`cancel` into them; anon can enqueue its own; worker (service_role) can update any.

**Unit tests:** backoff formula; the guarded transition predicates; the enqueue conflict/vanished-row retry logic.

---

## 8. Deferred / dependencies (explicit — Codex H3, not silent)

- **1E-b:** real ingestion handler; worker runtime budgets (wall-clock/disk/memory/concurrency); graceful shutdown (SIGTERM).
- **1E-c:** polling status API + client over the `getStatus`/RLS reads this slice provides.
- **1D:** atomic quota debit + spend reservation on `enqueue`, keyed to the idempotency tuple (so retries/joins never re-charge); **per-owner + global queue-depth / concurrency cap** (parent §8) — 1E-a reserves the hook (the claim query and `owner_id` index) but does not enforce a cap.
- **1H:** scheduled sweeps (pg_cron), health/readiness, deploy, secrets, and **dead-letter retention/archival + admin-retry + payload/error redaction** (Codex M3 / Claude L2).

---

## 9. Open decisions for review

1. **Per-playlist concurrency (Codex M2).** Proposed: cloud does **not** take a coarse per-playlist lock; it relies on idempotency + 1C's transactional `MetadataStore` methods for cross-artifact safety. Confirm, or require queue-level per-playlist serialization.
2. **Payload on join (Claude M4).** The idempotency key excludes `payload`. Proposed: the key is treated as fully determining the payload; on a join with a mismatched payload we keep the existing job and log a warning (no error). Confirm, or require rejecting mismatched-payload joins.
3. **Dead-letter visibility.** Proposed: owners see their own `dead_letter` jobs via the RLS `select` policy; retention/admin-retry deferred to 1H. Confirm.
