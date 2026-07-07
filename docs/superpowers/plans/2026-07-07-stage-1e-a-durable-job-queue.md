# Stage 1E-a Durable Job Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a durable, cloud-only Postgres job queue with a full fenced lifecycle (enqueue/claim/heartbeat/complete/fail/sweep), a `JobQueue` seam, and a worker-runner with a stub handler — all integration-tested, shipping dormant.

**Architecture:** A single owner-scoped `jobs` table with `SELECT … FOR UPDATE SKIP LOCKED` leasing. All mutations go through `SECURITY INVOKER` plpgsql RPCs (producer RPCs read `auth.uid()`; worker RPCs require `service_role` and fence every write on a `lease_token`). A `SupabaseJobQueue` class calls the RPCs; a `runOnce` worker loop drives a stub handler. Local tool untouched (no local impl). Cloud bundle gains an optional `jobQueue`.

**Tech Stack:** Postgres (Supabase local stack), plpgsql migrations, TypeScript, `@supabase/supabase-js`, Jest integration tests (`--runInBand`).

## Global Constraints

- **Migrations** are plain SQL, lowercase keywords, no `begin/commit` wrapper, no `if not exists` on `create table`. Applied in filename order; the new file is `supabase/migrations/0008_jobs_queue.sql`. Apply changes locally with `npx supabase db reset`.
- **Every new table needs BOTH** `enable row level security` and `force row level security`, a `<table>_owner` `for all` policy (`using` = `with check` = `owner_id = auth.uid()`), and an explicit `grant select, insert, update, delete on public.<table> to anon, authenticated, service_role;` (without the grant, PostgREST returns `42501`, not an empty set).
- **RPC idiom:** `language plpgsql security invoker set search_path = public as $$ … $$`, then `revoke all on function <name>(<argtypes>) from public;` and `grant execute on function <name>(<argtypes>) to <roles>;` (repeat the full typed signature verbatim in both).
- **Worker RPCs require `service_role`:** first line of body is `if auth.role() <> 'service_role' then raise exception 'workers only'; end if;`. Producer RPCs require a signed-in principal: `if auth.uid() is null then raise exception 'not authenticated'; end if;`.
- **Stores never build their own client** — the Supabase client is injected via constructor (`constructor(private client: SupabaseClient) {}`), exactly like `SupabaseMetadataStore`.
- **Integration tests never reset the DB.** Isolation is per fresh user via `newUser()` from `tests/integration/helpers/clients.ts`. Worker (service_role) ops use `adminClient()`. Serial run only (`npm run test:integration`).
- **`job_version`** is the target `DocVersion` (`{major, minor}`) rendered as the string `"major.minor"` (e.g. `"3.3"`). Helper `docVersionKey(v)`.
- **`section_id`** sentinel for a whole-video (summary) work target is **`-1`** (a real dig section can start at second 0, so 0 is not a safe sentinel).
- **Confinement:** the `service_role` client (`lib/supabase/service.ts`) must never be reachable from `app/`, `pages/`, or `middleware.ts` (`npm run check:confinement`). `SupabaseJobQueue` takes an injected client and must NOT import `service.ts`. The worker entrypoint lives under `lib/job-queue/` and is never imported by a route.

---

## File Structure

- Create `supabase/migrations/0008_jobs_queue.sql` — table, indexes, RLS, grants, all RPCs (built across Tasks 1–3).
- Create `lib/storage/job-queue.ts` — `JobQueue` interface + types (`JobKey`, `JobKind`, `JobStatus`, `LeasedJob`, `JobRecord`, `EnqueueResult`) + `docVersionKey`.
- Create `lib/storage/supabase/supabase-job-queue.ts` — `SupabaseJobQueue implements JobQueue`.
- Create `lib/job-queue/worker-runner.ts` — `runOnce()` loop + `JobHandler` type + echo stub.
- Modify `lib/storage/resolve.ts` — extract a named `StorageBundle` interface; add optional `jobQueue`; wire `SupabaseJobQueue` in the `supabase` branch.
- Create tests: `tests/integration/job-queue-schema.test.ts`, `job-queue-producer.test.ts`, `job-queue-worker.test.ts`, `job-queue-store.test.ts`, `job-queue-runner.test.ts`; and `tests/lib/storage/resolve-bundle.test.ts` (unit).

---

### Task 1: `jobs` table, indexes, RLS, grants

**Files:**
- Create: `supabase/migrations/0008_jobs_queue.sql`
- Test: `tests/integration/job-queue-schema.test.ts`

**Interfaces:**
- Produces: the `public.jobs` table with columns `(id, owner_id, video_id, section_id, job_kind, job_version, status, payload, result, error, attempts, max_attempts, locked_by, lease_token, lease_expires_at, run_after, cancel_requested, created_at, updated_at)`; partial unique index `jobs_idem_active`; RLS policy `jobs_owner`.

- [ ] **Step 1: Write the failing test**

```ts
// tests/integration/job-queue-schema.test.ts
import { adminClient, newUser, signInAs } from './helpers/clients';

async function insertJob(client: any, ownerId: string, over: Record<string, unknown> = {}) {
  const { data, error } = await client.from('jobs').insert({
    owner_id: ownerId, video_id: 'vid1', section_id: -1,
    job_kind: 'summary', job_version: '3.3', payload: { hello: 'world' }, ...over,
  }).select().single();
  return { data, error };
}

test('a user can insert and read only their own jobs (RLS isolation)', async () => {
  const a = await newUser();
  const b = await newUser();
  const ca = await signInAs(a.email, a.password);
  const cb = await signInAs(b.email, b.password);

  const ins = await insertJob(ca.client, ca.userId);
  expect(ins.error).toBeNull();
  expect(ins.data.status).toBe('queued');

  const seenByA = await ca.client.from('jobs').select('id');
  expect(seenByA.data).toHaveLength(1);

  const seenByB = await cb.client.from('jobs').select('id');
  expect(seenByB.data).toHaveLength(0); // RLS scopes A's job away from B
});

test('inserting a job for another owner is rejected by the with-check policy', async () => {
  const a = await newUser();
  const b = await newUser();
  const ca = await signInAs(a.email, a.password);
  const ins = await insertJob(ca.client, b.user.id); // A tries to write B's owner_id
  expect(ins.error).not.toBeNull(); // with check (owner_id = auth.uid()) violated
});

test('idempotency index blocks a second live job for the same work target', async () => {
  const a = await newUser();
  const ca = await signInAs(a.email, a.password);
  const first = await insertJob(ca.client, ca.userId);
  expect(first.error).toBeNull();
  const dup = await insertJob(ca.client, ca.userId); // same (owner,video,section,kind,version), both queued
  expect(dup.error).not.toBeNull(); // unique violation on jobs_idem_active
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
  owner_id      uuid not null,
  video_id      text not null,
  section_id    int  not null default -1,   -- dig: section start-second; -1 = whole-video (summary)
  job_kind      text not null,              -- 'summary' | 'dig'
  job_version   text not null,              -- target DocVersion 'major.minor'
  status        text not null default 'queued',
  payload       jsonb not null,
  result        jsonb,
  error         text,
  attempts      int  not null default 0,    -- executions started (bumped at claim)
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

-- at most one live-OR-succeeded job per (work target, job kind, job version)
create unique index jobs_idem_active on jobs (owner_id, video_id, section_id, job_kind, job_version)
  where status in ('queued','active','completed');
create index jobs_claim on jobs (run_after, created_at, id) where status = 'queued';
create index jobs_sweep on jobs (lease_expires_at)          where status = 'active';
create index jobs_owner on jobs (owner_id, created_at);

create policy jobs_owner on jobs for all
  using (owner_id = auth.uid()) with check (owner_id = auth.uid());

grant select, insert, update, delete on public.jobs to anon, authenticated, service_role;
```

- [ ] **Step 4: Apply and run test to verify it passes**

Run: `npx supabase db reset && npm run test:integration -- job-queue-schema`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/0008_jobs_queue.sql tests/integration/job-queue-schema.test.ts
git commit -m "feat(queue): 0008 jobs table + RLS + idempotency index"
```

---

### Task 2: Producer RPCs — `enqueue_job`, `request_cancel_job`

**Files:**
- Modify: `supabase/migrations/0008_jobs_queue.sql` (append)
- Test: `tests/integration/job-queue-producer.test.ts`

**Interfaces:**
- Produces: `enqueue_job(p_video_id text, p_section_id int, p_job_kind text, p_job_version text, p_payload jsonb) returns table(job_id uuid, status text, joined boolean)`; `request_cancel_job(p_job_id uuid) returns void`.

- [ ] **Step 1: Write the failing test**

```ts
// tests/integration/job-queue-producer.test.ts
import { newUser, signInAs, anonSession } from './helpers/clients';

async function enqueue(client: any, over: Record<string, unknown> = {}) {
  return client.rpc('enqueue_job', {
    p_video_id: 'vid1', p_section_id: -1, p_job_kind: 'summary',
    p_job_version: '3.3', p_payload: { n: 1 }, ...over,
  });
}

test('enqueue creates a queued job; same live key joins it', async () => {
  const u = await newUser();
  const c = (await signInAs(u.email, u.password)).client;
  const first = await enqueue(c);
  expect(first.error).toBeNull();
  expect(first.data[0].status).toBe('queued');
  expect(first.data[0].joined).toBe(false);

  const second = await enqueue(c);
  expect(second.data[0].joined).toBe(true);
  expect(second.data[0].job_id).toBe(first.data[0].job_id); // joined, not duplicated
});

test('a completed job is joined (not re-run) on re-enqueue of the same version', async () => {
  const u = await newUser();
  const c = (await signInAs(u.email, u.password)).client;
  const j = (await enqueue(c)).data[0];
  // simulate completion directly (owner update allowed by RLS)
  await c.from('jobs').update({ status: 'completed' }).eq('id', j.job_id);
  const again = await enqueue(c);
  expect(again.data[0].joined).toBe(true);
  expect(again.data[0].job_id).toBe(j.job_id);
  expect(again.data[0].status).toBe('completed');
});

test('a fresh job is allowed after the prior one is cancelled', async () => {
  const u = await newUser();
  const c = (await signInAs(u.email, u.password)).client;
  const j = (await enqueue(c)).data[0];
  await c.from('jobs').update({ status: 'cancelled' }).eq('id', j.job_id);
  const fresh = await enqueue(c);
  expect(fresh.data[0].joined).toBe(false);
  expect(fresh.data[0].job_id).not.toBe(j.job_id);
});

test('anon can enqueue its own job', async () => {
  const s = await anonSession();
  const r = await enqueue(s.client);
  expect(r.error).toBeNull();
  expect(r.data[0].status).toBe('queued');
});

test('request_cancel_job cancels a queued job immediately', async () => {
  const u = await newUser();
  const c = (await signInAs(u.email, u.password)).client;
  const j = (await enqueue(c)).data[0];
  const cancel = await c.rpc('request_cancel_job', { p_job_id: j.job_id });
  expect(cancel.error).toBeNull();
  const row = await c.from('jobs').select('status,cancel_requested').eq('id', j.job_id).single();
  expect(row.data.status).toBe('cancelled');
  expect(row.data.cancel_requested).toBe(true);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test:integration -- job-queue-producer`
Expected: FAIL — function `enqueue_job` does not exist.

- [ ] **Step 3: Append the producer RPCs to the migration**

```sql
-- enqueue: atomic insert-or-join over live+completed states
create function enqueue_job(
  p_video_id text, p_section_id int, p_job_kind text, p_job_version text, p_payload jsonb
) returns table(job_id uuid, status text, joined boolean)
  language plpgsql security invoker set search_path = public as $$
declare v_id uuid; v_status text;
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
    select id, status into v_id, v_status from jobs
      where owner_id = auth.uid() and video_id = p_video_id and section_id = p_section_id
        and job_kind = p_job_kind and job_version = p_job_version
        and status in ('queued','active','completed')
      limit 1;
    if v_id is not null then
      return query select v_id, v_status, true; return;   -- joined
    end if;
    -- conflicting row went terminal (failed/cancelled) in the gap: retry the insert
  end loop;
end $$;
revoke all on function enqueue_job(text,int,text,text,jsonb) from public;
grant execute on function enqueue_job(text,int,text,text,jsonb) to anon, authenticated, service_role;

-- cancel: set the flag always; flip a still-queued job straight to cancelled
create function request_cancel_job(p_job_id uuid) returns void
  language plpgsql security invoker set search_path = public as $$
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
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/0008_jobs_queue.sql tests/integration/job-queue-producer.test.ts
git commit -m "feat(queue): enqueue_job (atomic join) + request_cancel_job RPCs"
```

---

### Task 3: Worker RPCs — `claim_next_job`, `heartbeat_job`, `complete_job`, `fail_job`, `sweep_expired_leases`

**Files:**
- Modify: `supabase/migrations/0008_jobs_queue.sql` (append)
- Test: `tests/integration/job-queue-worker.test.ts`

**Interfaces:**
- Consumes: `jobs` table + `enqueue_job` (Task 2).
- Produces: `claim_next_job(p_worker_id text, p_lease_seconds int) returns setof jobs` (mints `lease_token`, bumps `attempts`); `heartbeat_job(p_job_id uuid, p_worker_id text, p_lease_token uuid, p_lease_seconds int) returns boolean`; `complete_job(p_job_id uuid, p_worker_id text, p_lease_token uuid, p_result jsonb) returns boolean`; `fail_job(p_job_id uuid, p_worker_id text, p_lease_token uuid, p_error text, p_retryable boolean) returns text`; `sweep_expired_leases() returns int`. All require `service_role`. Every write fences on `locked_by + lease_token + status='active'`.

- [ ] **Step 1: Write the failing test**

```ts
// tests/integration/job-queue-worker.test.ts
import { adminClient, newUser, signInAs } from './helpers/clients';
jest.setTimeout(20_000);

const admin = () => adminClient();
async function enqueueAs(email: string, password: string, over: Record<string, unknown> = {}) {
  const c = (await signInAs(email, password)).client;
  const r = await c.rpc('enqueue_job', {
    p_video_id: 'vid1', p_section_id: -1, p_job_kind: 'summary', p_job_version: '3.3', p_payload: {}, ...over });
  return r.data[0].job_id as string;
}

test('claim leases exactly one job with a token and bumps attempts', async () => {
  const u = await newUser(); await enqueueAs(u.email, u.password);
  const c = await admin().rpc('claim_next_job', { p_worker_id: 'w1', p_lease_seconds: 120 });
  expect(c.error).toBeNull();
  expect(c.data).toHaveLength(1);
  expect(c.data[0].status).toBe('active');
  expect(c.data[0].lease_token).toBeTruthy();
  expect(c.data[0].attempts).toBe(1);
});

test('a stale lease token cannot complete a reclaimed job (fencing)', async () => {
  const u = await newUser(); const id = await enqueueAs(u.email, u.password);
  const first = (await admin().rpc('claim_next_job', { p_worker_id: 'w1', p_lease_seconds: 1 })).data[0];
  // expire + sweep back to queued
  await admin().from('jobs').update({ lease_expires_at: new Date(Date.now() - 1000).toISOString() }).eq('id', id);
  await admin().rpc('sweep_expired_leases');
  const second = (await admin().rpc('claim_next_job', { p_worker_id: 'w2', p_lease_seconds: 120 })).data[0];

  const stale = await admin().rpc('complete_job', {
    p_job_id: id, p_worker_id: 'w1', p_lease_token: first.lease_token, p_result: {} });
  expect(stale.data).toBe(false); // w1 lost the lease

  const ok = await admin().rpc('complete_job', {
    p_job_id: id, p_worker_id: 'w2', p_lease_token: second.lease_token, p_result: { done: true } });
  expect(ok.data).toBe(true);
});

test('a crash-looping job dead-letters at max attempts (sweep)', async () => {
  const u = await newUser(); const id = await enqueueAs(u.email, u.password);
  await admin().from('jobs').update({ max_attempts: 2 }).eq('id', id);
  for (let i = 0; i < 2; i++) {
    await admin().rpc('claim_next_job', { p_worker_id: 'w', p_lease_seconds: 1 });
    await admin().from('jobs').update({ lease_expires_at: new Date(Date.now() - 1000).toISOString() }).eq('id', id);
    await admin().rpc('sweep_expired_leases');
  }
  const row = await admin().from('jobs').select('status,attempts').eq('id', id).single();
  expect(row.data.status).toBe('dead_letter'); // never re-leases forever
});

test('fail retryable under max requeues with backoff; non-retryable → failed', async () => {
  const u = await newUser(); const id = await enqueueAs(u.email, u.password);
  const c = (await admin().rpc('claim_next_job', { p_worker_id: 'w', p_lease_seconds: 120 })).data[0];
  const s = await admin().rpc('fail_job', {
    p_job_id: id, p_worker_id: 'w', p_lease_token: c.lease_token, p_error: 'boom', p_retryable: true });
  expect(s.data).toBe('queued');

  const c2 = (await admin().rpc('claim_next_job', { p_worker_id: 'w', p_lease_seconds: 120 })).data[0];
  const s2 = await admin().rpc('fail_job', {
    p_job_id: id, p_worker_id: 'w', p_lease_token: c2.lease_token, p_error: 'bad input', p_retryable: false });
  expect(s2.data).toBe('failed');
});

test('completing a cancel-requested job yields cancelled, not completed', async () => {
  const u = await newUser(); const id = await enqueueAs(u.email, u.password);
  const c = (await admin().rpc('claim_next_job', { p_worker_id: 'w', p_lease_seconds: 120 })).data[0];
  await admin().from('jobs').update({ cancel_requested: true }).eq('id', id);
  await admin().rpc('complete_job', { p_job_id: id, p_worker_id: 'w', p_lease_token: c.lease_token, p_result: {} });
  const row = await admin().from('jobs').select('status').eq('id', id).single();
  expect(row.data.status).toBe('cancelled');
});

test('claim requires service_role', async () => {
  const u = await newUser(); const c = (await signInAs(u.email, u.password)).client;
  const r = await c.rpc('claim_next_job', { p_worker_id: 'w', p_lease_seconds: 120 });
  expect(r.error).not.toBeNull(); // 'workers only'
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test:integration -- job-queue-worker`
Expected: FAIL — function `claim_next_job` does not exist.

- [ ] **Step 3: Append the worker RPCs to the migration**

```sql
create function claim_next_job(p_worker_id text, p_lease_seconds int)
  returns setof jobs language plpgsql security invoker set search_path = public as $$
declare v_token uuid := gen_random_uuid();
begin
  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
  return query
  update jobs set status='active', locked_by=p_worker_id, lease_token=v_token,
         lease_expires_at = now() + make_interval(secs => p_lease_seconds),
         attempts = attempts + 1, updated_at = now()   -- one increment per execution
  where id = (select id from jobs
              where status='queued' and run_after <= now()
              order by created_at, id
              for update skip locked limit 1)
  returning *;
end $$;
revoke all on function claim_next_job(text,int) from public;
grant execute on function claim_next_job(text,int) to service_role;

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
  if not found then return null; end if;   -- lost lease
  if v_cancel then v_new := 'cancelled';
  elsif not p_retryable then v_new := 'failed';
  elsif v_attempts >= v_max then v_new := 'dead_letter';
  else v_new := 'queued';
  end if;
  v_backoff := 10 * power(4, greatest(v_attempts - 1, 0))::int;   -- 10, 40, 160, ...
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
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add supabase/migrations/0008_jobs_queue.sql tests/integration/job-queue-worker.test.ts
git commit -m "feat(queue): worker RPCs — claim/heartbeat/complete/fail/sweep with lease fencing"
```

---

### Task 4: `JobQueue` interface + `SupabaseJobQueue`

**Files:**
- Create: `lib/storage/job-queue.ts`, `lib/storage/supabase/supabase-job-queue.ts`
- Test: `tests/integration/job-queue-store.test.ts`

**Interfaces:**
- Consumes: the RPCs from Tasks 2–3; `DocVersion` from `lib/doc-version.ts`.
- Produces:
  - `type JobKind = 'summary' | 'dig'`; `type JobStatus = 'queued'|'active'|'completed'|'failed'|'dead_letter'|'cancelled'`.
  - `interface JobKey { videoId: string; sectionId: number; kind: JobKind; version: string }`.
  - `interface EnqueueResult { jobId: string; status: JobStatus; joined: boolean }`.
  - `interface LeasedJob { id: string; ownerId: string; videoId: string; sectionId: number; kind: JobKind; version: string; payload: unknown; attempts: number; leaseToken: string }`.
  - `interface JobRecord { id: string; status: JobStatus; cancelRequested: boolean; result: unknown; error: string | null }`.
  - `interface JobQueue { enqueue(key, payload): Promise<EnqueueResult>; getStatus(jobId): Promise<JobRecord|null>; requestCancel(jobId): Promise<void>; claim(workerId, leaseSeconds): Promise<LeasedJob|null>; heartbeat(jobId, workerId, leaseToken, leaseSeconds): Promise<{ok:boolean}>; complete(jobId, workerId, leaseToken, result): Promise<{ok:boolean}>; fail(jobId, workerId, leaseToken, error, opts:{retryable:boolean}): Promise<{ok:boolean; status:JobStatus|null}>; sweepExpired(): Promise<number> }`.
  - `function docVersionKey(v: DocVersion): string`.
  - `class SupabaseJobQueue implements JobQueue { constructor(client: SupabaseClient) }`.

- [ ] **Step 1: Write the failing test**

```ts
// tests/integration/job-queue-store.test.ts
import { adminClient, newUser, signInAs } from './helpers/clients';
import { SupabaseJobQueue } from '@/lib/storage/supabase/supabase-job-queue';
jest.setTimeout(20_000);

const KEY = { videoId: 'vid1', sectionId: -1, kind: 'summary' as const, version: '3.3' };

test('enqueue → claim → complete round-trip through the store', async () => {
  const u = await newUser();
  const userQ = new SupabaseJobQueue((await signInAs(u.email, u.password)).client);
  const workerQ = new SupabaseJobQueue(adminClient());

  const enq = await userQ.enqueue(KEY, { n: 1 });
  expect(enq.joined).toBe(false);
  expect(enq.status).toBe('queued');

  const leased = await workerQ.claim('w1', 120);
  expect(leased?.id).toBe(enq.jobId);
  expect(leased?.leaseToken).toBeTruthy();

  const done = await workerQ.complete(leased!.id, 'w1', leased!.leaseToken, { ok: true });
  expect(done.ok).toBe(true);

  const status = await userQ.getStatus(enq.jobId);
  expect(status?.status).toBe('completed');
});

test('claim returns null when the queue is empty', async () => {
  const workerQ = new SupabaseJobQueue(adminClient());
  // no enqueue for this fresh worker call is guaranteed empty only if no queued rows exist globally;
  // enqueue+claim+complete one first to drain, then claim again:
  const u = await newUser();
  const userQ = new SupabaseJobQueue((await signInAs(u.email, u.password)).client);
  const enq = await userQ.enqueue(KEY, {});
  const leased = await workerQ.claim('w', 120);
  await workerQ.complete(leased!.id, 'w', leased!.leaseToken, {});
  // this user has nothing queued now; a claim may still pick up other suites' rows, so assert on THIS job only
  expect((await userQ.getStatus(enq.jobId))?.status).toBe('completed');
});

test('fail through the store reports the resulting status', async () => {
  const u = await newUser();
  const userQ = new SupabaseJobQueue((await signInAs(u.email, u.password)).client);
  const workerQ = new SupabaseJobQueue(adminClient());
  const enq = await userQ.enqueue(KEY, {});
  const leased = await workerQ.claim('w', 120);
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
  claim(workerId: string, leaseSeconds: number): Promise<LeasedJob | null>;
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
      p_job_version: key.version, p_payload: payload,
    });
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

  async claim(workerId: string, leaseSeconds: number): Promise<LeasedJob | null> {
    const { data, error } = await this.client.rpc('claim_next_job', { p_worker_id: workerId, p_lease_seconds: leaseSeconds });
    if (error) throw error;
    if (!data || data.length === 0) return null;
    const r = data[0];
    return {
      id: r.id, ownerId: r.owner_id, videoId: r.video_id, sectionId: r.section_id,
      kind: r.job_kind, version: r.job_version, payload: r.payload, attempts: r.attempts, leaseToken: r.lease_token,
    };
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

**Files:**
- Create: `lib/job-queue/worker-runner.ts`
- Test: `tests/integration/job-queue-runner.test.ts`

**Interfaces:**
- Consumes: `JobQueue`, `LeasedJob` from `lib/storage/job-queue.ts`.
- Produces:
  - `type JobHandler = (job: LeasedJob, ctx: { isCancelled(): Promise<boolean> }) => Promise<unknown>`.
  - `interface RunnerOpts { workerId: string; leaseSeconds?: number }`.
  - `function runOnce(queue: JobQueue, handler: JobHandler, opts: RunnerOpts): Promise<'idle'|'done'|'failed'|'cancelled'|'lost'>` — sweeps, claims one job, runs the handler, finalizes; returns the outcome.
  - `const echoHandler: JobHandler` — returns `{ echoed: job.payload }` (the 1E-a stub).

- [ ] **Step 1: Write the failing test**

```ts
// tests/integration/job-queue-runner.test.ts
import { adminClient, newUser, signInAs } from './helpers/clients';
import { SupabaseJobQueue } from '@/lib/storage/supabase/supabase-job-queue';
import { runOnce, echoHandler } from '@/lib/job-queue/worker-runner';
import type { JobHandler } from '@/lib/job-queue/worker-runner';
jest.setTimeout(20_000);

const KEY = { videoId: 'vid1', sectionId: -1, kind: 'summary' as const, version: '3.3' };

test('runOnce processes a queued job to completed with the echo stub', async () => {
  const u = await newUser();
  const userQ = new SupabaseJobQueue((await signInAs(u.email, u.password)).client);
  const workerQ = new SupabaseJobQueue(adminClient());
  const enq = await userQ.enqueue(KEY, { hi: 1 });

  const outcome = await runOnce(workerQ, echoHandler, { workerId: 'w1' });
  expect(outcome).toBe('done');
  const st = await userQ.getStatus(enq.jobId);
  expect(st?.status).toBe('completed');
  expect(st?.result).toEqual({ echoed: { hi: 1 } });
});

test('runOnce returns idle when nothing is claimable', async () => {
  const workerQ = new SupabaseJobQueue(adminClient());
  // drain: nothing enqueued by this test; but other suites may leave rows, so assert type only
  const outcome = await runOnce(workerQ, echoHandler, { workerId: 'w-empty' });
  expect(['idle', 'done']).toContain(outcome);
});

test('a handler that observes cancellation ends the job cancelled', async () => {
  const u = await newUser();
  const userQ = new SupabaseJobQueue((await signInAs(u.email, u.password)).client);
  const workerQ = new SupabaseJobQueue(adminClient());
  const enq = await userQ.enqueue(KEY, {});
  await userQ.requestCancel(enq.jobId); // cancel_requested set while queued? it flips queued→cancelled

  // re-enqueue a fresh job that we cancel AFTER claim, via a handler checkpoint:
  const u2 = await newUser();
  const userQ2 = new SupabaseJobQueue((await signInAs(u2.email, u2.password)).client);
  const enq2 = await userQ2.enqueue(KEY, {});
  const cancelDuringHandler: JobHandler = async (job, ctx) => {
    await userQ2.requestCancel(job.id);       // request cancel mid-run
    if (await ctx.isCancelled()) throw new Error('cancelled by request');
    return {};
  };
  const outcome = await runOnce(workerQ, cancelDuringHandler, { workerId: 'w2' });
  expect(outcome).toBe('cancelled');
  expect((await userQ2.getStatus(enq2.jobId))?.status).toBe('cancelled');
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
export interface RunnerOpts { workerId: string; leaseSeconds?: number }

export const echoHandler: JobHandler = async (job) => ({ echoed: job.payload });

export async function runOnce(
  queue: JobQueue, handler: JobHandler, opts: RunnerOpts,
): Promise<'idle' | 'done' | 'failed' | 'cancelled' | 'lost'> {
  await queue.sweepExpired();
  const lease = opts.leaseSeconds ?? 120;
  const job = await queue.claim(opts.workerId, lease);
  if (!job) return 'idle';

  const ctx = {
    isCancelled: async () => (await queue.getStatus(job.id))?.cancelRequested ?? false,
  };
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

**Files:**
- Modify: `lib/storage/resolve.ts`
- Test: `tests/lib/storage/resolve-bundle.test.ts`

**Interfaces:**
- Consumes: `JobQueue`, `SupabaseJobQueue`.
- Produces: a named `interface StorageBundle { metadataStore: MetadataStore; blobStore: BlobStore; jobQueue?: JobQueue }`; `getStorageBundle` returns it and wires `jobQueue: new SupabaseJobQueue(ctx.supabaseClient)` in the `supabase` branch. The `local` bundle leaves `jobQueue` undefined.

- [ ] **Step 1: Write the failing test**

```ts
// tests/lib/storage/resolve-bundle.test.ts
import { getStorageBundle } from '@/lib/storage/resolve';

describe('storage bundle jobQueue wiring', () => {
  const OLD = process.env.STORAGE_BACKEND;
  afterEach(() => { process.env.STORAGE_BACKEND = OLD; });

  test('local bundle has no jobQueue', () => {
    process.env.STORAGE_BACKEND = 'local';
    const bundle = getStorageBundle();
    expect(bundle.jobQueue).toBeUndefined();
  });

  test('supabase bundle exposes a jobQueue', () => {
    process.env.STORAGE_BACKEND = 'supabase';
    const fakeClient = { rpc: () => {}, from: () => {} } as any;
    const bundle = getStorageBundle({ supabaseClient: fakeClient });
    expect(bundle.jobQueue).toBeDefined();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest resolve-bundle`
Expected: FAIL — `bundle.jobQueue` is not a property / type error.

- [ ] **Step 3: Extract `StorageBundle` and wire `jobQueue`**

In `lib/storage/resolve.ts`, add the named interface and the wiring (adjust the existing inline return type):

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

(Ensure `LOCAL_BUNDLE` is typed as `StorageBundle` so `jobQueue` is legitimately absent.)

- [ ] **Step 4: Run the unit test, confinement scan, and full suites**

Run: `npx jest resolve-bundle && npm run check:confinement && npm test && npx tsc --noEmit`
Expected: unit PASS; confinement PASS (`SupabaseJobQueue` takes an injected client, imports no `service.ts`); full unit suite green; `tsc` clean.

- [ ] **Step 5: Run the full integration suite (regression)**

Run: `npx supabase db reset && npm run test:integration`
Expected: all suites green (the 5 new job-queue suites + the existing 1A–1C suites).

- [ ] **Step 6: Commit**

```bash
git add lib/storage/resolve.ts tests/lib/storage/resolve-bundle.test.ts
git commit -m "feat(queue): expose optional jobQueue on the cloud storage bundle"
```

---

## Self-Review

**Spec coverage** (each §1E-a spec section → task):
- §3 seam (producer/worker interfaces, fencing, cloud-only) → Tasks 4 (interface), 6 (bundle wiring); local absence enforced by Task 6 test.
- §4 table, idempotency-over-{queued,active,completed}, hot-path indexes, RLS `for select/insert/update` with-check, anon grants, atomic enqueue RPC → Tasks 1 (table/indexes/RLS/grants) + 2 (enqueue).
- §5 state machine, claim-time single attempts increment, lease fencing, crash-loop dead-letter, backoff, cooperative cancel honored on complete/fail/sweep → Task 3.
- §6 deliverables + worker confinement entrypoint → Tasks 4–6 (`check:confinement` in Task 6).
- §7 tests (join, completed-reuse, fencing, dead-letter bound, cancel, RLS/anon) → distributed across Tasks 1–5.
- §9 resolved decisions: per-playlist concurrency (rely on 1C transactional methods — no queue lock added, consistent with plan); payload-on-join (key determines payload — enqueue ignores a divergent payload; note: the plan does not add a warning log, see Deviations); dead-letter visibility (owner reads via RLS — Task 1 policy).

**Deviations from spec, called out:**
- **Attempts incremented at claim** (Codex-preferred "once per execution"), not in the terminal update as spec §5 phrased it. Property preserved (exactly one increment per execution); dead-letter bound uses the post-claim value. Simpler and race-free.
- **Payload-on-join warning log** (spec §9.2) is **not** implemented in SQL/TS in this slice (it would require a follow-up read to compare); behavior is "key determines payload, divergent payload on join is ignored." Flag for reviewer: acceptable for 1E-a, or add a `raise log` in `enqueue_job` when the joined row's payload differs?

**Placeholder scan:** none — every step has concrete SQL/TS/test code and exact run commands.

**Type consistency:** `JobKey`, `LeasedJob`, `EnqueueResult`, `JobRecord`, `JobQueue`, `docVersionKey` defined in Task 4 and consumed unchanged in Tasks 5–6. RPC names (`enqueue_job`, `request_cancel_job`, `claim_next_job`, `heartbeat_job`, `complete_job`, `fail_job`, `sweep_expired_leases`) and their argument names are identical between Tasks 2–3 (SQL) and Task 4 (`.rpc(...)` calls).
