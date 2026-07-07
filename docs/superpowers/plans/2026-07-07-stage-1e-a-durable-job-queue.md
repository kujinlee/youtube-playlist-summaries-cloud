# Stage 1E-a Durable Job Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Version:** v2 (2026-07-07) — hardened after two independent adversarial reviews of v1 (`docs/reviews/plan-stage-1e-a-codex.md`, `plan-stage-1e-a-claude-review.md`).

**Goal:** Build a durable, cloud-only Postgres job queue with a full fenced lifecycle (enqueue/claim/heartbeat/complete/fail/sweep), a `JobQueue` seam, and a worker-runner with a stub handler — all integration-tested, shipping dormant.

**Architecture:** A single owner-scoped `jobs` table with `SELECT … FOR UPDATE SKIP LOCKED` leasing. All mutations go through `SECURITY INVOKER`/`SECURITY DEFINER` plpgsql RPCs; producers get **read+insert only** on the table (no direct lifecycle writes), workers require `service_role` and fence every write on a `lease_token`. A `SupabaseJobQueue` class calls the RPCs; a `runOnce` worker loop drives a stub handler. Local tool untouched. Cloud bundle gains an optional `jobQueue`.

**Tech Stack:** Postgres (Supabase local stack), plpgsql migrations, TypeScript, `@supabase/supabase-js`, Jest integration tests (`--runInBand`).

## Global Constraints

- **Migrations** are plain SQL, lowercase keywords, no `begin/commit` wrapper, no `if not exists` on `create table`. Applied in filename order; the new file is `supabase/migrations/0008_jobs_queue.sql`. **Apply with `npx supabase db reset` only** (the single 0008 file grows across Tasks 1–3; `supabase migration up` would not re-run an already-recorded file, so RPCs added in later tasks would be missing — always `db reset`).
- **Every new table needs BOTH** `enable row level security` and `force row level security`, a `<table>_owner` `for all` policy (`using` = `with check` = `owner_id = auth.uid()`), and explicit grants (see below).
- **Producer privilege lockdown (plan review Codex-B1):** grant only `select, insert` on `public.jobs` to `anon, authenticated`; grant `select, insert, update, delete` to `service_role` only. Producers must NEVER be able to `update`/`delete` a job directly (that would let a user fake `status='completed'`). All lifecycle mutation is via RPCs; cancellation is a `SECURITY DEFINER` RPC.
- **RPC idiom:** `language plpgsql security invoker set search_path = public as $$ … $$`, then `revoke all on function <name>(<argtypes>) from public;` and `grant execute on function <name>(<argtypes>) to <roles>;` (repeat the full typed signature verbatim). `request_cancel_job` is `security definer` (owner can't update the table directly) with an explicit `owner_id = auth.uid()` guard.
- **Worker RPCs require `service_role`:** first body line is `if auth.role() <> 'service_role' then raise exception 'workers only'; end if;`. Producer RPCs require a principal: `if auth.uid() is null then raise exception 'not authenticated'; end if;`. (`service_role` has `BYPASSRLS`, confirmed in `0006`, so worker RPCs update any owner's row under `force row level security` with no service policy — verified by the plan review.)
- **`attempts` = executions started, incremented once at `claim`** (spec §5). `fail`/`sweep` do not re-increment; they route to `dead_letter` when `attempts ≥ max_attempts`.
- **`job_version`** is the target `DocVersion` rendered as `"major.minor"` (e.g. `"3.3"`). Helper `docVersionKey(v)`.
- **`section_id`** sentinel for a whole-video (summary) target is **`-1`** (a dig section can start at second 0).
- **TEST ISOLATION (plan review Codex-B3 / Claude-B1):** `claim_next_job` is `service_role` and claims the globally-oldest queued job, ignoring RLS; tests never reset the DB between suites. So **every claim-based test MUST scope its claim** by a run-unique `video_id` (`crypto.randomUUID()`) passed to both `enqueue_job` and `claim_next_job`'s `p_video_id` filter. Never assert that a bare `claim()` returns "my" job.
- **Stores never build their own client** — injected via constructor. `SupabaseJobQueue` imports no `service.ts` (confinement-safe). The worker entrypoint lives under `lib/job-queue/`, never imported by a route (`npm run check:confinement`).
- **Integration tests** run serially (`npm run test:integration`); isolation is per fresh `newUser()` + per-test `randomUUID()` video id. Worker (service_role) ops use `adminClient()`.

---

## File Structure

- Create `supabase/migrations/0008_jobs_queue.sql` — table, indexes, RLS, grants, all RPCs (built across Tasks 1–3).
- Create `lib/storage/job-queue.ts` — `JobQueue` interface + types + `docVersionKey`.
- Create `lib/storage/supabase/supabase-job-queue.ts` — `SupabaseJobQueue implements JobQueue`.
- Create `lib/job-queue/worker-runner.ts` — `runOnce()` loop + `JobHandler` + echo stub.
- Modify `lib/storage/resolve.ts` — named `StorageBundle` interface; optional `jobQueue`; wire `SupabaseJobQueue`.
- Create tests: `tests/integration/job-queue-schema.test.ts`, `job-queue-producer.test.ts`, `job-queue-worker.test.ts`, `job-queue-store.test.ts`, `job-queue-runner.test.ts`; `tests/lib/storage/resolve-bundle.test.ts`.

---

### Task 1: `jobs` table, indexes, RLS, grants

**Files:** Create `supabase/migrations/0008_jobs_queue.sql`; Test `tests/integration/job-queue-schema.test.ts`

**Interfaces:**
- Produces: `public.jobs` with columns `(id, owner_id, video_id, section_id, job_kind, job_version, status, payload, result, error, attempts, max_attempts, locked_by, lease_token, lease_expires_at, run_after, cancel_requested, created_at, updated_at)`; partial unique index `jobs_idem_active`; policy `jobs_owner`; producer grants `select,insert`.

- [ ] **Step 1: Write the failing test**

```ts
// tests/integration/job-queue-schema.test.ts
import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs } from './helpers/clients';

test('a user can insert and read only their own jobs (RLS isolation)', async () => {
  const a = await newUser(); const b = await newUser();
  const ca = await signInAs(a.email, a.password);
  const cb = await signInAs(b.email, b.password);
  const vid = randomUUID();
  const ins = await ca.client.from('jobs').insert({
    owner_id: ca.userId, video_id: vid, section_id: -1,
    job_kind: 'summary', job_version: '3.3', payload: { hi: 1 },
  }).select().single();
  expect(ins.error).toBeNull();
  expect(ins.data.status).toBe('queued');

  const seenByA = await ca.client.from('jobs').select('id').eq('video_id', vid);
  expect(seenByA.data).toHaveLength(1);
  const seenByB = await cb.client.from('jobs').select('id').eq('video_id', vid);
  expect(seenByB.data).toHaveLength(0);
});

test('inserting a job for another owner is rejected by the with-check policy', async () => {
  const a = await newUser(); const b = await newUser();
  const ca = await signInAs(a.email, a.password);
  const ins = await ca.client.from('jobs').insert({
    owner_id: b.user.id, video_id: randomUUID(), section_id: -1,
    job_kind: 'summary', job_version: '3.3', payload: {},
  });
  expect(ins.error).not.toBeNull();
});

test('a producer cannot directly update a job (no update grant)', async () => {
  const a = await newUser();
  const ca = await signInAs(a.email, a.password);
  const vid = randomUUID();
  const ins = await ca.client.from('jobs').insert({
    owner_id: ca.userId, video_id: vid, section_id: -1,
    job_kind: 'summary', job_version: '3.3', payload: {},
  }).select().single();
  const upd = await ca.client.from('jobs').update({ status: 'completed' }).eq('id', ins.data.id).select();
  // no update grant → PostgREST returns 0 rows (permission), status stays queued
  expect(upd.data ?? []).toHaveLength(0);
  const check = await adminClient().from('jobs').select('status').eq('id', ins.data.id).single();
  expect(check.data.status).toBe('queued');
});

test('idempotency index blocks a second live job for the same work target', async () => {
  const a = await newUser();
  const ca = await signInAs(a.email, a.password);
  const vid = randomUUID();
  const row = { owner_id: ca.userId, video_id: vid, section_id: -1, job_kind: 'summary', job_version: '3.3', payload: {} };
  expect((await ca.client.from('jobs').insert(row)).error).toBeNull();
  expect((await ca.client.from('jobs').insert(row)).error).not.toBeNull();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test:integration -- job-queue-schema`
Expected: FAIL — relation "jobs" does not exist.

- [ ] **Step 3: Write the migration (table + indexes + RLS + grants)**

```sql
-- supabase/migrations/0008_jobs_queue.sql
create table jobs (
  id            uuid primary key default gen_random_uuid(),
  owner_id      uuid not null references profiles(id) on delete cascade,
  video_id      text not null,
  section_id    int  not null default -1,   -- dig: section start-second; -1 = whole-video (summary)
  job_kind      text not null,              -- 'summary' | 'dig'
  job_version   text not null,              -- target DocVersion 'major.minor'
  status        text not null default 'queued',
  payload       jsonb not null,
  result        jsonb,
  error         text,
  attempts      int  not null default 0,    -- executions started (bumped once at claim)
  max_attempts  int  not null default 5,
  locked_by         text,
  lease_token       uuid,
  lease_expires_at  timestamptz,
  run_after         timestamptz not null default now(),
  cancel_requested  boolean not null default false,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  constraint jobs_status_chk check (status in ('queued','active','completed','failed','dead_letter','cancelled')),
  constraint jobs_kind_chk   check (job_kind in ('summary','dig'))
);

alter table jobs enable row level security;
alter table jobs force  row level security;

create unique index jobs_idem_active on jobs (owner_id, video_id, section_id, job_kind, job_version)
  where status in ('queued','active','completed');
create index jobs_claim on jobs (run_after, created_at, id) where status = 'queued';
create index jobs_sweep on jobs (lease_expires_at)          where status = 'active';
create index jobs_owner on jobs (owner_id, created_at);

create policy jobs_owner on jobs for all
  using (owner_id = auth.uid()) with check (owner_id = auth.uid());

-- producers: read + insert only (NEVER direct update/delete — lifecycle is RPC-only)
grant select, insert on public.jobs to anon, authenticated;
grant select, insert, update, delete on public.jobs to service_role;
```

- [ ] **Step 4: Apply and run test to verify it passes**

Run: `npx supabase db reset && npm run test:integration -- job-queue-schema`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/0008_jobs_queue.sql tests/integration/job-queue-schema.test.ts
git commit -m "feat(queue): 0008 jobs table + RLS + producer-locked grants"
```

---

### Task 2: Producer RPCs — `enqueue_job`, `request_cancel_job`

**Files:** Modify `supabase/migrations/0008_jobs_queue.sql`; Test `tests/integration/job-queue-producer.test.ts`

**Interfaces:**
- Produces: `enqueue_job(p_video_id text, p_section_id int, p_job_kind text, p_job_version text, p_payload jsonb) returns table(job_id uuid, status text, joined boolean)` (atomic insert-or-join; logs on payload mismatch); `request_cancel_job(p_job_id uuid) returns void` (`security definer`, owner-guarded).

- [ ] **Step 1: Write the failing test**

```ts
// tests/integration/job-queue-producer.test.ts
import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs, anonSession } from './helpers/clients';

function enqueue(client: any, videoId: string, over: Record<string, unknown> = {}) {
  return client.rpc('enqueue_job', {
    p_video_id: videoId, p_section_id: -1, p_job_kind: 'summary',
    p_job_version: '3.3', p_payload: { n: 1 }, ...over,
  });
}

test('enqueue creates a queued job; same live key joins it', async () => {
  const u = await newUser(); const c = (await signInAs(u.email, u.password)).client;
  const vid = randomUUID();
  const first = await enqueue(c, vid);
  expect(first.error).toBeNull();
  expect(first.data[0].status).toBe('queued');
  expect(first.data[0].joined).toBe(false);
  const second = await enqueue(c, vid);
  expect(second.data[0].joined).toBe(true);
  expect(second.data[0].job_id).toBe(first.data[0].job_id);
});

test('a completed job is joined (not re-run) on re-enqueue of the same version', async () => {
  const u = await newUser(); const c = (await signInAs(u.email, u.password)).client;
  const vid = randomUUID();
  const j = (await enqueue(c, vid)).data[0];
  await adminClient().from('jobs').update({ status: 'completed' }).eq('id', j.job_id); // service_role sets terminal
  const again = await enqueue(c, vid);
  expect(again.data[0].joined).toBe(true);
  expect(again.data[0].job_id).toBe(j.job_id);
  expect(again.data[0].status).toBe('completed');
});

test('a fresh job is allowed after the prior one is cancelled', async () => {
  const u = await newUser(); const c = (await signInAs(u.email, u.password)).client;
  const vid = randomUUID();
  const j = (await enqueue(c, vid)).data[0];
  await c.rpc('request_cancel_job', { p_job_id: j.job_id }); // queued → cancelled
  const fresh = await enqueue(c, vid);
  expect(fresh.data[0].joined).toBe(false);
  expect(fresh.data[0].job_id).not.toBe(j.job_id);
});

test('a different owner enqueuing the same key gets a separate job', async () => {
  const a = await newUser(); const b = await newUser();
  const ca = (await signInAs(a.email, a.password)).client;
  const cb = (await signInAs(b.email, b.password)).client;
  const vid = randomUUID();
  const ja = (await enqueue(ca, vid)).data[0];
  const jb = (await enqueue(cb, vid)).data[0];
  expect(jb.joined).toBe(false);              // idem index is owner-scoped
  expect(jb.job_id).not.toBe(ja.job_id);
});

test('concurrent enqueue of the same key yields exactly one live job', async () => {
  const u = await newUser(); const c = (await signInAs(u.email, u.password)).client;
  const vid = randomUUID();
  const [r1, r2] = await Promise.all([enqueue(c, vid), enqueue(c, vid)]);
  const ids = [r1.data[0].job_id, r2.data[0].job_id];
  expect(ids[0]).toBe(ids[1]);                                    // both resolve to one job
  const live = await adminClient().from('jobs')
    .select('id').eq('video_id', vid).in('status', ['queued', 'active', 'completed']);
  expect(live.data).toHaveLength(1);
});

test('anon can enqueue its own job', async () => {
  const s = await anonSession();
  const r = await enqueue(s.client, randomUUID());
  expect(r.error).toBeNull();
  expect(r.data[0].status).toBe('queued');
});

test('request_cancel_job cancels a queued job; another user cannot cancel it', async () => {
  const a = await newUser(); const b = await newUser();
  const ca = (await signInAs(a.email, a.password)).client;
  const cb = (await signInAs(b.email, b.password)).client;
  const j = (await enqueue(ca, randomUUID())).data[0];
  const foreign = await cb.rpc('request_cancel_job', { p_job_id: j.job_id });
  expect(foreign.error).not.toBeNull();                            // 'job not found or not owned'
  const own = await ca.rpc('request_cancel_job', { p_job_id: j.job_id });
  expect(own.error).toBeNull();
  const row = await adminClient().from('jobs').select('status,cancel_requested').eq('id', j.job_id).single();
  expect(row.data.status).toBe('cancelled');
  expect(row.data.cancel_requested).toBe(true);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test:integration -- job-queue-producer`
Expected: FAIL — function `enqueue_job` does not exist.

- [ ] **Step 3: Append the producer RPCs to the migration**

```sql
-- enqueue: atomic insert-or-join over live+completed states (table aliased to avoid the
-- output-param `status` colliding with the column — plan review Codex-B2)
create function enqueue_job(
  p_video_id text, p_section_id int, p_job_kind text, p_job_version text, p_payload jsonb
) returns table(job_id uuid, status text, joined boolean)
  language plpgsql security invoker set search_path = public as $$
declare v_id uuid; v_status text; v_payload jsonb;
begin
  if auth.uid() is null then raise exception 'not authenticated'; end if;
  loop
    insert into jobs (owner_id, video_id, section_id, job_kind, job_version, payload)
    values (auth.uid(), p_video_id, p_section_id, p_job_kind, p_job_version, p_payload)
    on conflict (owner_id, video_id, section_id, job_kind, job_version)
      where status in ('queued','active','completed')
      do nothing
    returning id into v_id;
    if v_id is not null then
      return query select v_id, 'queued'::text, false; return;
    end if;
    select j.id, j.status, j.payload into v_id, v_status, v_payload from jobs j
      where j.owner_id = auth.uid() and j.video_id = p_video_id and j.section_id = p_section_id
        and j.job_kind = p_job_kind and j.job_version = p_job_version
        and j.status in ('queued','active','completed')
      limit 1;
    if v_id is not null then
      if v_payload is distinct from p_payload then
        raise log 'enqueue_job: joined % with a divergent payload (kept existing)', v_id;  -- spec §9.2
      end if;
      return query select v_id, v_status, true; return;
    end if;
    -- conflicting row went terminal (failed/cancelled) in the gap: retry the insert
  end loop;
end $$;
revoke all on function enqueue_job(text,int,text,text,jsonb) from public;
grant execute on function enqueue_job(text,int,text,text,jsonb) to anon, authenticated, service_role;

-- cancel: SECURITY DEFINER because producers have no direct update grant. Explicit owner guard.
create function request_cancel_job(p_job_id uuid) returns void
  language plpgsql security definer set search_path = public as $$
begin
  update jobs
    set cancel_requested = true,
        status = case when status = 'queued' then 'cancelled' else status end,
        updated_at = now()
  where id = p_job_id and owner_id = auth.uid();
  if not found then raise exception 'job not found or not owned'; end if;
end $$;
revoke all on function request_cancel_job(uuid) from public;
grant execute on function request_cancel_job(uuid) to anon, authenticated, service_role;
```

- [ ] **Step 4: Apply and run test to verify it passes**

Run: `npx supabase db reset && npm run test:integration -- job-queue-producer`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/0008_jobs_queue.sql tests/integration/job-queue-producer.test.ts
git commit -m "feat(queue): enqueue_job (atomic join, qualified cols) + owner-guarded cancel"
```

---

### Task 3: Worker RPCs — claim / heartbeat / complete / fail / sweep

**Files:** Modify `supabase/migrations/0008_jobs_queue.sql`; Test `tests/integration/job-queue-worker.test.ts`

**Interfaces:**
- Produces: `claim_next_job(p_worker_id text, p_lease_seconds int, p_video_id text default null) returns setof jobs` (mints `lease_token`, `attempts += 1`, optional `p_video_id` filter for test isolation); `heartbeat_job(p_job_id uuid, p_worker_id text, p_lease_token uuid, p_lease_seconds int) returns boolean`; `complete_job(p_job_id uuid, p_worker_id text, p_lease_token uuid, p_result jsonb) returns boolean`; `fail_job(p_job_id uuid, p_worker_id text, p_lease_token uuid, p_error text, p_retryable boolean) returns text`; `sweep_expired_leases() returns int`. All require `service_role`; every write fences on `locked_by + lease_token + status='active'`.

- [ ] **Step 1: Write the failing test**

```ts
// tests/integration/job-queue-worker.test.ts
import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs } from './helpers/clients';
jest.setTimeout(20_000);

const admin = () => adminClient();
async function enqueueScoped(videoId: string, over: Record<string, unknown> = {}) {
  const u = await newUser();
  const c = (await signInAs(u.email, u.password)).client;
  const r = await c.rpc('enqueue_job', {
    p_video_id: videoId, p_section_id: -1, p_job_kind: 'summary', p_job_version: '3.3', p_payload: {}, ...over });
  return r.data[0].job_id as string;
}
const claim = (worker: string, videoId: string, lease = 120) =>
  admin().rpc('claim_next_job', { p_worker_id: worker, p_lease_seconds: lease, p_video_id: videoId });

test('claim leases exactly one job with a token and bumps attempts', async () => {
  const vid = randomUUID(); await enqueueScoped(vid);
  const c = await claim('w1', vid);
  expect(c.error).toBeNull();
  expect(c.data).toHaveLength(1);
  expect(c.data[0].status).toBe('active');
  expect(c.data[0].lease_token).toBeTruthy();
  expect(c.data[0].attempts).toBe(1);
});

test('heartbeat extends the lease for the current owner and rejects a stale token', async () => {
  const vid = randomUUID(); const id = await enqueueScoped(vid);
  const c = (await claim('w1', vid)).data[0];
  const ok = await admin().rpc('heartbeat_job', {
    p_job_id: id, p_worker_id: 'w1', p_lease_token: c.lease_token, p_lease_seconds: 300 });
  expect(ok.data).toBe(true);
  const stale = await admin().rpc('heartbeat_job', {
    p_job_id: id, p_worker_id: 'w1', p_lease_token: randomUUID(), p_lease_seconds: 300 });
  expect(stale.data).toBe(false);
});

test('a stale lease token cannot complete a reclaimed job (fencing)', async () => {
  const vid = randomUUID(); const id = await enqueueScoped(vid);
  const first = (await claim('w1', vid, 1)).data[0];
  await admin().from('jobs').update({ lease_expires_at: new Date(Date.now() - 1000).toISOString() }).eq('id', id);
  await admin().rpc('sweep_expired_leases');
  const second = (await claim('w2', vid)).data[0];
  const staleDone = await admin().rpc('complete_job', {
    p_job_id: id, p_worker_id: 'w1', p_lease_token: first.lease_token, p_result: {} });
  expect(staleDone.data).toBe(false);
  const ok = await admin().rpc('complete_job', {
    p_job_id: id, p_worker_id: 'w2', p_lease_token: second.lease_token, p_result: { done: true } });
  expect(ok.data).toBe(true);
});

test('two concurrent claims get distinct jobs', async () => {
  const vid = randomUUID();
  await enqueueScoped(vid); await enqueueScoped(vid, { p_job_kind: 'dig', p_section_id: 5 }); // 2 live jobs, same video
  const [a, b] = await Promise.all([claim('wa', vid), claim('wb', vid)]);
  const ids = [a.data[0]?.id, b.data[0]?.id];
  expect(ids[0]).toBeTruthy(); expect(ids[1]).toBeTruthy();
  expect(ids[0]).not.toBe(ids[1]);
});

test('a crash-looping job dead-letters at max attempts (sweep)', async () => {
  const vid = randomUUID(); const id = await enqueueScoped(vid);
  await admin().from('jobs').update({ max_attempts: 2 }).eq('id', id);
  for (let i = 0; i < 2; i++) {
    await claim('w', vid, 1);
    await admin().from('jobs').update({ lease_expires_at: new Date(Date.now() - 1000).toISOString() }).eq('id', id);
    await admin().rpc('sweep_expired_leases');
  }
  const row = await admin().from('jobs').select('status,attempts').eq('id', id).single();
  expect(row.data.status).toBe('dead_letter');
  expect(row.data.attempts).toBe(2);
});

test('fail retryable requeues with backoff; non-retryable → failed', async () => {
  const vid = randomUUID(); const id = await enqueueScoped(vid);
  const c = (await claim('w', vid)).data[0];
  const s = await admin().rpc('fail_job', {
    p_job_id: id, p_worker_id: 'w', p_lease_token: c.lease_token, p_error: 'boom', p_retryable: true });
  expect(s.data).toBe('queued');
  // retryable fail set run_after = now()+10s; reset it so the next claim is eligible (plan review Claude-B2)
  await admin().from('jobs').update({ run_after: new Date().toISOString() }).eq('id', id);
  const c2 = (await claim('w', vid)).data[0];
  const s2 = await admin().rpc('fail_job', {
    p_job_id: id, p_worker_id: 'w', p_lease_token: c2.lease_token, p_error: 'bad input', p_retryable: false });
  expect(s2.data).toBe('failed');
});

test('completing a cancel-requested job yields cancelled, not completed', async () => {
  const vid = randomUUID(); const id = await enqueueScoped(vid);
  const c = (await claim('w', vid)).data[0];
  await admin().from('jobs').update({ cancel_requested: true }).eq('id', id);
  await admin().rpc('complete_job', { p_job_id: id, p_worker_id: 'w', p_lease_token: c.lease_token, p_result: {} });
  const row = await admin().from('jobs').select('status').eq('id', id).single();
  expect(row.data.status).toBe('cancelled');
});

test('claim requires service_role', async () => {
  const u = await newUser(); const c = (await signInAs(u.email, u.password)).client;
  const r = await c.rpc('claim_next_job', { p_worker_id: 'w', p_lease_seconds: 120 });
  expect(r.error).not.toBeNull();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test:integration -- job-queue-worker`
Expected: FAIL — function `claim_next_job` does not exist.

- [ ] **Step 3: Append the worker RPCs to the migration**

```sql
create function claim_next_job(p_worker_id text, p_lease_seconds int, p_video_id text default null)
  returns setof jobs language plpgsql security invoker set search_path = public as $$
declare v_token uuid := gen_random_uuid();
begin
  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
  return query
  update jobs set status='active', locked_by=p_worker_id, lease_token=v_token,
         lease_expires_at = now() + make_interval(secs => p_lease_seconds),
         attempts = attempts + 1, updated_at = now()   -- one increment per execution (spec §5)
  where id = (select id from jobs
              where status='queued' and run_after <= now()
                and (p_video_id is null or video_id = p_video_id)   -- test-isolation filter
              order by created_at, id
              for update skip locked limit 1)
  returning *;
end $$;
revoke all on function claim_next_job(text,int,text) from public;
grant execute on function claim_next_job(text,int,text) to service_role;

create function heartbeat_job(p_job_id uuid, p_worker_id text, p_lease_token uuid, p_lease_seconds int)
  returns boolean language plpgsql security invoker set search_path = public as $$
declare v_rows int;
begin
  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
  update jobs set lease_expires_at = now() + make_interval(secs => p_lease_seconds), updated_at = now()
  where id = p_job_id and locked_by = p_worker_id and lease_token = p_lease_token and status = 'active';
  get diagnostics v_rows = row_count;
  return v_rows > 0;
end $$;
revoke all on function heartbeat_job(uuid,text,uuid,int) from public;
grant execute on function heartbeat_job(uuid,text,uuid,int) to service_role;

create function complete_job(p_job_id uuid, p_worker_id text, p_lease_token uuid, p_result jsonb)
  returns boolean language plpgsql security invoker set search_path = public as $$
declare v_rows int;
begin
  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
  update jobs
    set status = case when cancel_requested then 'cancelled' else 'completed' end,
        result = p_result, locked_by = null, lease_token = null, lease_expires_at = null, updated_at = now()
  where id = p_job_id and locked_by = p_worker_id and lease_token = p_lease_token and status = 'active';
  get diagnostics v_rows = row_count;
  return v_rows > 0;
end $$;
revoke all on function complete_job(uuid,text,uuid,jsonb) from public;
grant execute on function complete_job(uuid,text,uuid,jsonb) to service_role;

create function fail_job(p_job_id uuid, p_worker_id text, p_lease_token uuid, p_error text, p_retryable boolean)
  returns text language plpgsql security invoker set search_path = public as $$
declare v_attempts int; v_max int; v_cancel boolean; v_new text; v_backoff int;
begin
  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
  select attempts, max_attempts, cancel_requested into v_attempts, v_max, v_cancel from jobs
    where id = p_job_id and locked_by = p_worker_id and lease_token = p_lease_token and status = 'active'
    for update;
  if not found then return null; end if;            -- lost lease
  if v_cancel then v_new := 'cancelled';
  elsif not p_retryable then v_new := 'failed';
  elsif v_attempts >= v_max then v_new := 'dead_letter';
  else v_new := 'queued';
  end if;
  v_backoff := (10 * power(4, greatest(v_attempts - 1, 0)))::int;   -- 10, 40, 160, ...
  update jobs set status = v_new, error = p_error,
       run_after = case when v_new = 'queued' then now() + make_interval(secs => v_backoff) else run_after end,
       locked_by = null, lease_token = null, lease_expires_at = null, updated_at = now()
  where id = p_job_id;
  return v_new;
end $$;
revoke all on function fail_job(uuid,text,uuid,text,boolean) from public;
grant execute on function fail_job(uuid,text,uuid,text,boolean) to service_role;

create function sweep_expired_leases() returns int
  language plpgsql security invoker set search_path = public as $$
declare v_count int;
begin
  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
  with expired as (
    select id from jobs where status = 'active' and lease_expires_at < now()
    for update skip locked
  )
  update jobs j set
    status = case when j.cancel_requested then 'cancelled'
                  when j.attempts >= j.max_attempts then 'dead_letter'
                  else 'queued' end,
    locked_by = null, lease_token = null, lease_expires_at = null, updated_at = now()
  from expired e where j.id = e.id;
  get diagnostics v_count = row_count;
  return v_count;
end $$;
revoke all on function sweep_expired_leases() from public;
grant execute on function sweep_expired_leases() to service_role;
```

- [ ] **Step 4: Apply and run test to verify it passes**

Run: `npx supabase db reset && npm run test:integration -- job-queue-worker`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/0008_jobs_queue.sql tests/integration/job-queue-worker.test.ts
git commit -m "feat(queue): worker RPCs with lease fencing + p_video_id claim filter"
```

---

### Task 4: `JobQueue` interface + `SupabaseJobQueue`

**Files:** Create `lib/storage/job-queue.ts`, `lib/storage/supabase/supabase-job-queue.ts`; Test `tests/integration/job-queue-store.test.ts`

**Interfaces:**
- Consumes: RPCs from Tasks 2–3; `DocVersion` from `lib/doc-version.ts`.
- Produces:
  - `type JobKind = 'summary' | 'dig'`; `type JobStatus = 'queued'|'active'|'completed'|'failed'|'dead_letter'|'cancelled'`.
  - `interface JobKey { videoId: string; sectionId: number; kind: JobKind; version: string }`.
  - `interface EnqueueResult { jobId: string; status: JobStatus; joined: boolean }`.
  - `interface LeasedJob { id: string; ownerId: string; videoId: string; sectionId: number; kind: JobKind; version: string; payload: unknown; attempts: number; leaseToken: string }`.
  - `interface JobRecord { id: string; status: JobStatus; cancelRequested: boolean; result: unknown; error: string | null }`.
  - `interface JobQueue { enqueue(key,payload): Promise<EnqueueResult>; getStatus(jobId): Promise<JobRecord|null>; requestCancel(jobId): Promise<void>; claim(workerId, leaseSeconds, videoId?: string|null): Promise<LeasedJob|null>; heartbeat(jobId, workerId, leaseToken, leaseSeconds): Promise<{ok:boolean}>; complete(jobId, workerId, leaseToken, result): Promise<{ok:boolean}>; fail(jobId, workerId, leaseToken, error, opts:{retryable:boolean}): Promise<{ok:boolean; status:JobStatus|null}>; sweepExpired(): Promise<number> }`.
  - `function docVersionKey(v: DocVersion): string`.
  - `class SupabaseJobQueue implements JobQueue { constructor(client: SupabaseClient) }`.

- [ ] **Step 1: Write the failing test**

```ts
// tests/integration/job-queue-store.test.ts
import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs } from './helpers/clients';
import { SupabaseJobQueue } from '@/lib/storage/supabase/supabase-job-queue';
jest.setTimeout(20_000);

const key = (videoId: string) => ({ videoId, sectionId: -1, kind: 'summary' as const, version: '3.3' });

test('enqueue → claim(video) → complete round-trip through the store', async () => {
  const u = await newUser();
  const userQ = new SupabaseJobQueue((await signInAs(u.email, u.password)).client);
  const workerQ = new SupabaseJobQueue(adminClient());
  const vid = randomUUID();
  const enq = await userQ.enqueue(key(vid), { n: 1 });
  expect(enq.joined).toBe(false);

  const leased = await workerQ.claim('w1', 120, vid);   // scoped claim
  expect(leased?.id).toBe(enq.jobId);
  expect(leased?.leaseToken).toBeTruthy();

  const done = await workerQ.complete(leased!.id, 'w1', leased!.leaseToken, { ok: true });
  expect(done.ok).toBe(true);
  expect((await userQ.getStatus(enq.jobId))?.status).toBe('completed');
});

test('claim returns null when the scoped queue is empty', async () => {
  const workerQ = new SupabaseJobQueue(adminClient());
  const leased = await workerQ.claim('w', 120, randomUUID()); // no job for this fresh video id
  expect(leased).toBeNull();
});

test('fail through the store reports the resulting status', async () => {
  const u = await newUser();
  const userQ = new SupabaseJobQueue((await signInAs(u.email, u.password)).client);
  const workerQ = new SupabaseJobQueue(adminClient());
  const vid = randomUUID();
  const enq = await userQ.enqueue(key(vid), {});
  const leased = await workerQ.claim('w', 120, vid);
  const r = await workerQ.fail(leased!.id, 'w', leased!.leaseToken, 'boom', { retryable: false });
  expect(r.ok).toBe(true);
  expect(r.status).toBe('failed');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test:integration -- job-queue-store`
Expected: FAIL — cannot find module `@/lib/storage/supabase/supabase-job-queue`.

- [ ] **Step 3: Write the interface + types**

```ts
// lib/storage/job-queue.ts
import type { DocVersion } from '@/lib/doc-version';

export type JobKind = 'summary' | 'dig';
export type JobStatus = 'queued' | 'active' | 'completed' | 'failed' | 'dead_letter' | 'cancelled';

export interface JobKey { videoId: string; sectionId: number; kind: JobKind; version: string; }
export interface EnqueueResult { jobId: string; status: JobStatus; joined: boolean; }
export interface LeasedJob {
  id: string; ownerId: string; videoId: string; sectionId: number;
  kind: JobKind; version: string; payload: unknown; attempts: number; leaseToken: string;
}
export interface JobRecord {
  id: string; status: JobStatus; cancelRequested: boolean; result: unknown; error: string | null;
}

export interface JobQueue {
  enqueue(key: JobKey, payload: unknown): Promise<EnqueueResult>;
  getStatus(jobId: string): Promise<JobRecord | null>;
  requestCancel(jobId: string): Promise<void>;
  claim(workerId: string, leaseSeconds: number, videoId?: string | null): Promise<LeasedJob | null>;
  heartbeat(jobId: string, workerId: string, leaseToken: string, leaseSeconds: number): Promise<{ ok: boolean }>;
  complete(jobId: string, workerId: string, leaseToken: string, result: unknown): Promise<{ ok: boolean }>;
  fail(jobId: string, workerId: string, leaseToken: string, error: string, opts: { retryable: boolean }):
    Promise<{ ok: boolean; status: JobStatus | null }>;
  sweepExpired(): Promise<number>;
}

export function docVersionKey(v: DocVersion): string { return `${v.major}.${v.minor}`; }
```

- [ ] **Step 4: Write `SupabaseJobQueue`**

```ts
// lib/storage/supabase/supabase-job-queue.ts
import type { SupabaseClient } from '@supabase/supabase-js';
import type { JobQueue, JobKey, EnqueueResult, LeasedJob, JobRecord } from '@/lib/storage/job-queue';

export class SupabaseJobQueue implements JobQueue {
  constructor(private client: SupabaseClient) {}

  async enqueue(key: JobKey, payload: unknown): Promise<EnqueueResult> {
    const { data, error } = await this.client.rpc('enqueue_job', {
      p_video_id: key.videoId, p_section_id: key.sectionId, p_job_kind: key.kind,
      p_job_version: key.version, p_payload: payload });
    if (error) throw error;
    const row = data[0];
    return { jobId: row.job_id, status: row.status, joined: row.joined };
  }

  async getStatus(jobId: string): Promise<JobRecord | null> {
    const { data, error } = await this.client
      .from('jobs').select('id,status,cancel_requested,result,error').eq('id', jobId).maybeSingle();
    if (error) throw error;
    if (!data) return null;
    return { id: data.id, status: data.status, cancelRequested: data.cancel_requested, result: data.result, error: data.error };
  }

  async requestCancel(jobId: string): Promise<void> {
    const { error } = await this.client.rpc('request_cancel_job', { p_job_id: jobId });
    if (error) throw error;
  }

  async claim(workerId: string, leaseSeconds: number, videoId: string | null = null): Promise<LeasedJob | null> {
    const { data, error } = await this.client.rpc('claim_next_job', {
      p_worker_id: workerId, p_lease_seconds: leaseSeconds, p_video_id: videoId });
    if (error) throw error;
    if (!data || data.length === 0) return null;
    const r = data[0];
    return {
      id: r.id, ownerId: r.owner_id, videoId: r.video_id, sectionId: r.section_id,
      kind: r.job_kind, version: r.job_version, payload: r.payload, attempts: r.attempts, leaseToken: r.lease_token };
  }

  async heartbeat(jobId: string, workerId: string, leaseToken: string, leaseSeconds: number) {
    const { data, error } = await this.client.rpc('heartbeat_job', {
      p_job_id: jobId, p_worker_id: workerId, p_lease_token: leaseToken, p_lease_seconds: leaseSeconds });
    if (error) throw error;
    return { ok: data === true };
  }

  async complete(jobId: string, workerId: string, leaseToken: string, result: unknown) {
    const { data, error } = await this.client.rpc('complete_job', {
      p_job_id: jobId, p_worker_id: workerId, p_lease_token: leaseToken, p_result: result });
    if (error) throw error;
    return { ok: data === true };
  }

  async fail(jobId: string, workerId: string, leaseToken: string, err: string, opts: { retryable: boolean }) {
    const { data, error } = await this.client.rpc('fail_job', {
      p_job_id: jobId, p_worker_id: workerId, p_lease_token: leaseToken, p_error: err, p_retryable: opts.retryable });
    if (error) throw error;
    return { ok: data !== null, status: data };
  }

  async sweepExpired(): Promise<number> {
    const { data, error } = await this.client.rpc('sweep_expired_leases');
    if (error) throw error;
    return data as number;
  }
}
```

- [ ] **Step 5: Run tests + full type-check**

Run: `npm run test:integration -- job-queue-store && npx tsc --noEmit`
Expected: PASS (3 tests), `tsc` clean.

- [ ] **Step 6: Commit**

```bash
git add lib/storage/job-queue.ts lib/storage/supabase/supabase-job-queue.ts tests/integration/job-queue-store.test.ts
git commit -m "feat(queue): JobQueue seam + SupabaseJobQueue over the RPCs"
```

---

### Task 5: Worker-runner loop + stub handler

**Files:** Create `lib/job-queue/worker-runner.ts`; Test `tests/integration/job-queue-runner.test.ts`

**Interfaces:**
- Consumes: `JobQueue`, `LeasedJob` from `lib/storage/job-queue.ts`.
- Produces:
  - `type JobHandler = (job: LeasedJob, ctx: { isCancelled(): Promise<boolean> }) => Promise<unknown>`.
  - `interface RunnerOpts { workerId: string; leaseSeconds?: number; videoFilter?: string | null }`.
  - `function runOnce(queue: JobQueue, handler: JobHandler, opts: RunnerOpts): Promise<'idle'|'done'|'failed'|'cancelled'|'lost'>` — sweeps, claims one job (scoped by `videoFilter`), runs the handler, finalizes.
  - `const echoHandler: JobHandler`.
  - **Note:** `runOnce` does NOT run a heartbeat loop; the 1E-a stub completes instantly, well within the lease. A periodic heartbeat around the handler is REQUIRED before 1E-b swaps in the real (long-running) ingestion handler — tracked as a 1E-b task.

- [ ] **Step 1: Write the failing test**

```ts
// tests/integration/job-queue-runner.test.ts
import { randomUUID } from 'crypto';
import { adminClient, newUser, signInAs } from './helpers/clients';
import { SupabaseJobQueue } from '@/lib/storage/supabase/supabase-job-queue';
import { runOnce, echoHandler } from '@/lib/job-queue/worker-runner';
import type { JobHandler } from '@/lib/job-queue/worker-runner';
jest.setTimeout(20_000);

const key = (videoId: string) => ({ videoId, sectionId: -1, kind: 'summary' as const, version: '3.3' });

test('runOnce processes a queued job to completed with the echo stub', async () => {
  const u = await newUser();
  const userQ = new SupabaseJobQueue((await signInAs(u.email, u.password)).client);
  const workerQ = new SupabaseJobQueue(adminClient());
  const vid = randomUUID();
  const enq = await userQ.enqueue(key(vid), { hi: 1 });

  const outcome = await runOnce(workerQ, echoHandler, { workerId: 'w1', videoFilter: vid });
  expect(outcome).toBe('done');
  const st = await userQ.getStatus(enq.jobId);
  expect(st?.status).toBe('completed');
  expect(st?.result).toEqual({ echoed: { hi: 1 } });
});

test('runOnce returns idle when the scoped queue is empty', async () => {
  const workerQ = new SupabaseJobQueue(adminClient());
  const outcome = await runOnce(workerQ, echoHandler, { workerId: 'w-empty', videoFilter: randomUUID() });
  expect(outcome).toBe('idle');
});

test('a handler that observes cancellation ends the job cancelled', async () => {
  const u = await newUser();
  const userQ = new SupabaseJobQueue((await signInAs(u.email, u.password)).client);
  const workerQ = new SupabaseJobQueue(adminClient());
  const vid = randomUUID();
  const enq = await userQ.enqueue(key(vid), {});

  const cancelDuringHandler: JobHandler = async (job, ctx) => {
    expect(job.id).toBe(enq.jobId);          // scoped claim guarantees we got our job
    await userQ.requestCancel(job.id);       // request cancel mid-run (job is 'active' now)
    if (await ctx.isCancelled()) throw new Error('cancelled by request');
    return {};
  };
  const outcome = await runOnce(workerQ, cancelDuringHandler, { workerId: 'w2', videoFilter: vid });
  expect(outcome).toBe('cancelled');
  expect((await userQ.getStatus(enq.jobId))?.status).toBe('cancelled');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test:integration -- job-queue-runner`
Expected: FAIL — cannot find module `@/lib/job-queue/worker-runner`.

- [ ] **Step 3: Write the runner**

```ts
// lib/job-queue/worker-runner.ts
import type { JobQueue, LeasedJob } from '@/lib/storage/job-queue';

export type JobHandler = (job: LeasedJob, ctx: { isCancelled(): Promise<boolean> }) => Promise<unknown>;
export interface RunnerOpts { workerId: string; leaseSeconds?: number; videoFilter?: string | null }

export const echoHandler: JobHandler = async (job) => ({ echoed: job.payload });

// NOTE: no heartbeat loop — the 1E-a stub completes instantly. 1E-b must add a periodic
// heartbeat around the handler before swapping in the real (long-running) ingestion handler.
export async function runOnce(
  queue: JobQueue, handler: JobHandler, opts: RunnerOpts,
): Promise<'idle' | 'done' | 'failed' | 'cancelled' | 'lost'> {
  await queue.sweepExpired();
  const job = await queue.claim(opts.workerId, opts.leaseSeconds ?? 120, opts.videoFilter ?? null);
  if (!job) return 'idle';

  const ctx = { isCancelled: async () => (await queue.getStatus(job.id))?.cancelRequested ?? false };
  try {
    const result = await handler(job, ctx);
    const { ok } = await queue.complete(job.id, opts.workerId, job.leaseToken, result);
    return ok ? 'done' : 'lost';
  } catch (e) {
    const { ok, status } = await queue.fail(
      job.id, opts.workerId, job.leaseToken, e instanceof Error ? e.message : String(e), { retryable: true });
    if (!ok) return 'lost';
    return status === 'cancelled' ? 'cancelled' : 'failed';
  }
}
```

- [ ] **Step 4: Run tests + type-check**

Run: `npm run test:integration -- job-queue-runner && npx tsc --noEmit`
Expected: PASS (3 tests), `tsc` clean.

- [ ] **Step 5: Commit**

```bash
git add lib/job-queue/worker-runner.ts tests/integration/job-queue-runner.test.ts
git commit -m "feat(queue): worker-runner runOnce loop + echo stub handler"
```

---

### Task 6: Bundle wiring + confinement

**Files:** Modify `lib/storage/resolve.ts`; Test `tests/lib/storage/resolve-bundle.test.ts`

**Interfaces:**
- Consumes: `JobQueue`, `SupabaseJobQueue`.
- Produces: `interface StorageBundle { metadataStore: MetadataStore; blobStore: BlobStore; jobQueue?: JobQueue }`; `getStorageBundle` returns it and wires `jobQueue: new SupabaseJobQueue(ctx.supabaseClient)` in the `supabase` branch; local leaves `jobQueue` undefined.

- [ ] **Step 1: Write the failing test**

```ts
// tests/lib/storage/resolve-bundle.test.ts
import { getStorageBundle } from '@/lib/storage/resolve';

describe('storage bundle jobQueue wiring', () => {
  const OLD = process.env.STORAGE_BACKEND;
  afterEach(() => { process.env.STORAGE_BACKEND = OLD; });

  test('local bundle has no jobQueue', () => {
    process.env.STORAGE_BACKEND = 'local';
    expect(getStorageBundle().jobQueue).toBeUndefined();
  });

  test('supabase bundle exposes a jobQueue', () => {
    process.env.STORAGE_BACKEND = 'supabase';
    const fakeClient = { rpc: () => {}, from: () => {} } as any;
    expect(getStorageBundle({ supabaseClient: fakeClient }).jobQueue).toBeDefined();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest resolve-bundle`
Expected: FAIL — `bundle.jobQueue` is undefined / type error.

- [ ] **Step 3: Extract `StorageBundle` and wire `jobQueue`**

In `lib/storage/resolve.ts`:

```ts
import { SupabaseJobQueue } from '@/lib/storage/supabase/supabase-job-queue';
import type { JobQueue } from '@/lib/storage/job-queue';

export interface StorageBundle {
  metadataStore: MetadataStore;
  blobStore: BlobStore;
  jobQueue?: JobQueue;   // cloud-only; undefined for the local bundle
}

export function getStorageBundle(ctx?: { supabaseClient?: SupabaseClient }): StorageBundle {
  const backend = process.env.STORAGE_BACKEND ?? 'local';
  if (backend === 'local') return LOCAL_BUNDLE;              // jobQueue stays undefined
  if (backend === 'supabase') {
    validateStorageEnv();
    if (!ctx?.supabaseClient) throw new Error('supabase backend requires an authenticated client (routes not wired in 1C)');
    return {
      metadataStore: new SupabaseMetadataStore(ctx.supabaseClient),
      blobStore: new SupabaseBlobStore(ctx.supabaseClient, ARTIFACTS_BUCKET),
      jobQueue: new SupabaseJobQueue(ctx.supabaseClient),
    };
  }
  throw new Error(`unknown STORAGE_BACKEND: ${backend}`);
}
```

Ensure `LOCAL_BUNDLE` is typed `StorageBundle` (so `jobQueue` is legitimately absent).

- [ ] **Step 4: Run the unit test, confinement scan, and full suites**

Run: `npx jest resolve-bundle && npm run check:confinement && npm test && npx tsc --noEmit`
Expected: unit PASS; confinement PASS (`SupabaseJobQueue` imports no `service.ts`); full unit suite green; `tsc` clean.

- [ ] **Step 5: Run the full integration suite (regression)**

Run: `npx supabase db reset && npm run test:integration`
Expected: all suites green (5 new job-queue suites + existing 1A–1C suites).

- [ ] **Step 6: Commit**

```bash
git add lib/storage/resolve.ts tests/lib/storage/resolve-bundle.test.ts
git commit -m "feat(queue): expose optional jobQueue on the cloud storage bundle"
```

---

## Self-Review

**Spec coverage** (each §1E-a spec section → task):
- §3 seam (producer/worker interfaces, fencing, cloud-only) → Tasks 4 (interface), 6 (wiring); local absence enforced by Task 6.
- §4 table + FK to `profiles` + idempotency-over-{queued,active,completed} + hot-path indexes + RLS `for all` with-check + **producer-locked grants** + atomic enqueue RPC → Tasks 1–2.
- §5 state machine, **attempts bumped once at claim** (spec reconciled to "executions started"), lease fencing, crash-loop dead-letter, backoff, cooperative cancel honored on complete/fail/sweep → Task 3.
- §6 deliverables + worker confinement → Tasks 4–6 (`check:confinement` in Task 6).
- §7 tests: join, completed-reuse, **concurrent enqueue**, **concurrent claim**, fencing, **heartbeat happy + stale**, dead-letter bound, backoff, cancel, RLS/anon, **cross-owner idempotency + cancel** → distributed across Tasks 1–5.
- §9 resolved decisions: per-playlist concurrency (no queue lock; rely on 1C transactional methods); payload-on-join (key determines payload — enqueue joins, `raise log` on mismatch); dead-letter visibility (owner reads via RLS).

**Plan-review findings addressed:**
- Codex-B1 (producer bypass) → producer grants limited to `select,insert`; `update,delete` service_role-only; `request_cancel_job` is `security definer`; Task 1 test proves a producer cannot direct-update.
- Codex-B2 (`status` ambiguity) → `enqueue_job` aliases `jobs j`, qualifies columns.
- Codex-B3 / Claude-B1 (global-claim test isolation) → `claim_next_job` gains `p_video_id`; every claim-based test uses a `randomUUID()` video id and asserts by job id.
- Claude-B2 (backoff crash) → the fail test resets `run_after` before re-claim.
- Codex-H1/H2 / Claude-M3 (attempts semantics) → spec §5 reconciled to "executions started, bumped at claim"; plan matches; no lingering "deviation."
- Claude-H1 (heartbeat coverage) → Task 3 heartbeat happy + stale tests.
- Claude-H2 (concurrency tests) → Task 2 concurrent-enqueue, Task 3 concurrent-claim.
- Codex-H3 / Claude-L3 (null-claim test) → Task 4 asserts `claim(...,randomUUID()) === null`.
- Codex-M1 / Claude-M4 (FK) → restored `references profiles(id) on delete cascade` (anon has a profiles row via the 0003 trigger — verified).
- Codex-M3 / Claude-L1 (payload log) → `raise log` in `enqueue_job`; concurrent-enqueue test checks single live row.
- Claude-M1 (dead code) → runner cancel test rewritten, asserts `job.id === enq.jobId`, no dead block.
- Codex-L1 (db-reset-only) → Global Constraints note.
- Codex-L2 / Claude H1 (no heartbeat loop) → Task 5 interface note; heartbeat tested at RPC level.

**Explicitly deferred (noted, not silent):**
- The `enqueue_job` vanished-row retry loop (conflicting row goes terminal mid-call) is not deterministically unit-testable here; behavior is specified and the loop is bounded by re-conflict. Deferred to a targeted concurrency test in 1E-b if it proves reachable.
- Periodic heartbeat loop in the worker runner → 1E-b (the stub completes instantly).

**Placeholder scan:** none — every step has concrete SQL/TS/test code and exact commands.

**Type consistency:** `JobKey`, `LeasedJob`, `EnqueueResult`, `JobRecord`, `JobQueue` (incl. `claim`'s optional `videoId`), `docVersionKey` defined in Task 4, consumed unchanged in Tasks 5–6. RPC names/arg names identical between Tasks 2–3 (SQL) and Task 4 (`.rpc(...)`), including `p_video_id`.
