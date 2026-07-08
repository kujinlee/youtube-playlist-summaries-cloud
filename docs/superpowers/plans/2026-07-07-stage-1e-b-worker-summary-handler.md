# Stage 1E-b — Worker + Summary Ingestion Handler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A long-lived `service_role` worker that leases jobs from the 1E-a queue and runs real, idempotent, retry-safe summary ingestion, persisting the full `Video` and the summary artifact through owner-scoped Postgres RPCs.

**Architecture:** A `worker/main.ts` loop calls an upgraded `runOnce` that supervises a `summaryHandler` with a heartbeat loop, a composed `AbortSignal` (wall-clock ⊕ lease-loss ⊕ SIGTERM), cancellation, retryability, and `progress_phase` stamping. The handler reserves an idempotent serial, skips if already promoted, calls a store-agnostic `summaryCore`, then persists via two idempotent owner-scoped RPCs (`reserve_video_slot`, `persist_summary`). The job identity gains a `playlistId` coordinate with a composite owner-safe FK.

**Tech Stack:** TypeScript, Next.js, Supabase (Postgres + `@supabase/supabase-js`), `@google/generative-ai@0.24.1`, jest (unit + integration `--runInBand` against a local Supabase stack). Node ≥ 20.3 (`AbortSignal.any`).

**Revision:** v2 — addresses the round-1 dual plan review (`docs/reviews/plan-stage-1e-b-{codex,claude-review}.md`). Changes: folded the queue adapter + fixture updates into Task 1 so every task commits green; the three `sweep`-affected tests are fixed in Task 1; the runner upgrade (Task 6) now precedes the handler (Task 7) so `JobHandler` evolves in one place; added a fenced `set_progress_phase` RPC + `JobQueue.setProgressPhase`; added a `playlist_id`-keyed `readVideo`; `generateSummary` re-throws `AbortError` unwrapped; `docVersionKey`/`slugify`/`padSerial` named correctly; concurrent + crash-safety tests added.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-07-stage-1e-b-worker-ingestion-handler-design.md` (v3). ADR: `docs/adr/0002-playlist-in-job-identity.md`.
- **Scope: summary only.** Dig, slide-asset capture → 1E-b-2. Live deploy/resource caps → 1H. Producer/route → 1E-c.
- **Job identity is `(owner_id, playlist_id, video_id, section_id, job_kind, job_version)`.** The `jobs → playlists` FK MUST be composite `(playlist_id, owner_id) references playlists(id, owner_id)`.
- **Persistence is idempotent + owner-scoped.** `reserve_video_slot` returns the *existing* serial on conflict; `persist_summary` merges (never full-replaces `videos.data`, never erases the `artifacts` sub-object) and `raise`s on 0 rows. Both `security invoker` with `(owner_id = auth.uid() or auth.role() = 'service_role')` + a `playlists` ownership check (rejects a mismatched `p_owner_id` even for the service worker).
- **`AbortSignal` bounds worker occupancy, not Gemini billing.** Never claim aborting avoids the charge.
- **Every task commits green.** Migrations are append-only; Tasks 1–2 both edit `0009_job_playlist_identity_and_worker_persistence.sql`. Every SQL/integration task runs `npx supabase db reset` → `npm run test:integration` → `npx tsc --noEmit` before commit.
- `docVersionKey({major:3,minor:3}) === '3.3'` is the `job_version` string. `CURRENT_DOC_VERSION = {major:3, minor:3}`. Compare stored `data.docVersion` (an object) via `docVersionKey(...)`, never `===` a string.
- `progress_phase ∈ {'transcribing','summarizing','writing'}` — a TS enum (`lib/job-queue/progress-phase.ts`) AND a DB check constraint, kept in sync.
- Helpers: `slugify` (`lib/slugify.ts`), `padSerial` (`lib/serial-filename.ts`) — reuse, do not re-invent.
- Test commands: `npx jest <file>`, `npm run test:integration` (`--runInBand`), `npm run check:confinement`, `npx tsc --noEmit`. Integration needs `.env.test.local` (`supabase status -o env > .env.test.local`). Client helpers: `newUser`, `signInAs`, `adminClient`, `anonSession` (`tests/integration/helpers/clients.ts`).

---

## Task ordering & review gates

| Task | Deliverable (each commits green) | Adversarial gate |
|---|---|---|
| 1 | `0009` identity re-key + `progress_phase` + `set_progress_phase` RPC + sweep backoff; `playlistId` on `JobKey`/`LeasedJob` + adapter (`enqueue`/`claim`/`setProgressPhase`); update ALL existing enqueue fixtures + the 3 sweep-affected tests | **YES (Codex + Claude)** |
| 2 | `0009` persist RPCs (`reserve_video_slot`, `persist_summary`) + sequential & concurrent idempotency tests | **YES (Codex + Claude)** |
| 3 | Worker storage seam: `getWorkerStorageBundle` + `reserveVideoSlot`/`persistSummary`/`readVideo` helpers | standard |
| 4 | Signal threading through Gemini/transcript (+ `generateSummary` abort-unwrap) | standard |
| 5 | `summaryCore` extraction + local re-wire | standard |
| 6 | `runOnce` upgrade — owns `handler-context.ts` (`JobHandler`/`HandlerCtx`), `errors.ts`; heartbeat, composed signal, `setProgressPhase`, teardown; updates `echoHandler` + existing runner tests | standard |
| 7 | `summaryHandler` (idempotent, self-healing) | standard |
| 8 | `worker/main.ts` entrypoint | standard |
| 9 | Confinement → `worker/` + `fail_job` flaky-test cleanup | standard |

Tasks 1–2 land together for a green suite because Task 1's `enqueue_job` signature change breaks every existing enqueue caller until the adapter + fixtures (folded into Task 1) are updated.

---

### Task 1: `0009` identity re-key + queue adapter + fixture updates

**Files:**
- Create: `supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql` (Task 2 appends the persist RPCs)
- Create: `lib/job-queue/progress-phase.ts`
- Modify: `lib/storage/job-queue.ts` (`JobKey`, `LeasedJob`, `JobQueue.setProgressPhase`)
- Modify: `lib/storage/supabase/supabase-job-queue.ts` (`enqueue`, `claim`, `setProgressPhase`)
- Create: `tests/integration/job-queue-playlist-identity.test.ts`
- Modify: `tests/integration/schema.test.ts`; `tests/integration/job-queue-worker.test.ts` (3 sweep tests); `job-queue-producer.test.ts`, `job-queue-store.test.ts`, `job-queue-runner.test.ts` (seed a playlist + pass `playlistId` in every `enqueue_job`/`enqueueScoped` call)

**Interfaces:**
- Produces: `JobKey { playlistId: string; videoId; sectionId; kind; version }`; `LeasedJob { …; playlistId: string }`; `ProgressPhase = 'transcribing' | 'summarizing' | 'writing'`; `JobQueue.setProgressPhase(jobId, workerId, leaseToken, phase: ProgressPhase): Promise<{ ok: boolean }>`; `enqueue_job(p_playlist_id uuid, …)`; `set_progress_phase(p_job_id, p_worker_id, p_lease_token, p_phase)`; `jobs.playlist_id`, `jobs.progress_phase`; re-keyed `jobs_idem_active`; sweep with backoff.

- [ ] **Step 1: Write the failing test** — `tests/integration/job-queue-playlist-identity.test.ts` (two playlists → two jobs; same playlist → join; another owner's playlist → rejected). Use the seeding pattern:

```ts
import { newUser, signInAs } from './helpers/clients';
import { randomUUID } from 'crypto';
async function seedPlaylist(client: any, ownerId: string, key: string): Promise<string> {
  const { data, error } = await client.from('playlists')
    .insert({ owner_id: ownerId, playlist_key: key, playlist_url: `https://x/${key}` })
    .select('id').single();
  if (error) throw error; return data.id as string;
}
test('same (video,section,kind,version) under two playlists → two distinct jobs', async () => {
  const u = await newUser(); const { client, userId } = await signInAs(u.email, u.password);
  const plA = await seedPlaylist(client, userId, `A-${randomUUID()}`);
  const plB = await seedPlaylist(client, userId, `B-${randomUUID()}`);
  const vid = randomUUID();
  const args = (pl: string) => ({ p_playlist_id: pl, p_video_id: vid, p_section_id: -1, p_job_kind: 'summary', p_job_version: '3.3', p_payload: {} });
  const a = await client.rpc('enqueue_job', args(plA)); const b = await client.rpc('enqueue_job', args(plB));
  expect(a.error).toBeNull(); expect(b.error).toBeNull();
  expect(a.data[0].job_id).not.toBe(b.data[0].job_id);
});
test('enqueue against another owner\'s playlist is rejected', async () => {
  const owner = await newUser(); const { client: oc, userId: oid } = await signInAs(owner.email, owner.password);
  const victimPl = await seedPlaylist(oc, oid, `V-${randomUUID()}`);
  const atk = await newUser(); const { client: ac } = await signInAs(atk.email, atk.password);
  const res = await ac.rpc('enqueue_job', { p_playlist_id: victimPl, p_video_id: randomUUID(), p_section_id: -1, p_job_kind: 'summary', p_job_version: '3.3', p_payload: {} });
  expect(res.error).not.toBeNull();
});
```

- [ ] **Step 2: Run** — `npm run test:integration -- job-queue-playlist-identity` → FAIL.

- [ ] **Step 3: Write the migration** — `0009_job_playlist_identity_and_worker_persistence.sql`:

```sql
-- 0009: 1E-b — job-identity playlist coordinate + worker columns/RPCs.
-- jobs is created fresh by 0008 on every `db reset` (empty at this point) → safe re-key.

alter table jobs add column playlist_id uuid not null;
alter table jobs add constraint jobs_playlist_owner_fk
  foreign key (playlist_id, owner_id) references playlists(id, owner_id) on delete cascade;
alter table jobs add column progress_phase text
  check (progress_phase in ('transcribing','summarizing','writing'));

drop index jobs_idem_active;
create unique index jobs_idem_active
  on jobs (owner_id, playlist_id, video_id, section_id, job_kind, job_version)
  where status in ('queued','active','completed');

drop function enqueue_job(text,int,text,text,jsonb);
create function enqueue_job(
  p_playlist_id uuid, p_video_id text, p_section_id int, p_job_kind text, p_job_version text, p_payload jsonb
) returns table(job_id uuid, status text, joined boolean)
  language plpgsql security invoker set search_path = public as $$
declare v_id uuid; v_status text; v_payload jsonb; v_tries int := 0;
begin
  if auth.uid() is null then raise exception 'not authenticated'; end if;
  loop
    v_tries := v_tries + 1;
    if v_tries > 8 then raise exception 'enqueue_job: retry limit exceeded'; end if;
    insert into jobs as j (owner_id, playlist_id, video_id, section_id, job_kind, job_version, payload)
    values (auth.uid(), p_playlist_id, p_video_id, p_section_id, p_job_kind, p_job_version, p_payload)
    on conflict (owner_id, playlist_id, video_id, section_id, job_kind, job_version)
      where j.status in ('queued','active','completed')
      do nothing
    returning id into v_id;
    if v_id is not null then return query select v_id, 'queued'::text, false; return; end if;
    select j.id, j.status, j.payload into v_id, v_status, v_payload from jobs j
      where j.owner_id = auth.uid() and j.playlist_id = p_playlist_id and j.video_id = p_video_id
        and j.section_id = p_section_id and j.job_kind = p_job_kind and j.job_version = p_job_version
        and j.status in ('queued','active','completed')
      limit 1;
    if v_id is not null then
      if v_payload is distinct from p_payload then
        raise log 'enqueue_job: joined % with a divergent payload (kept existing)', v_id; end if;
      return query select v_id, v_status, true; return;
    end if;
  end loop;
end $$;
revoke all on function enqueue_job(uuid,text,int,text,text,jsonb) from public;
grant execute on function enqueue_job(uuid,text,int,text,text,jsonb) to anon, authenticated, service_role;

-- set_progress_phase: lease-fenced advisory phase write (keeps lifecycle writes RPC-only).
create function set_progress_phase(p_job_id uuid, p_worker_id text, p_lease_token uuid, p_phase text)
  returns boolean language plpgsql security invoker set search_path = public as $$
declare v_ok boolean;
begin
  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
  update jobs set progress_phase = p_phase, updated_at = now()
    where id = p_job_id and locked_by = p_worker_id and lease_token = p_lease_token and status = 'active';
  get diagnostics v_ok = row_count;
  return v_ok > 0;
end $$;
revoke all on function set_progress_phase(uuid,text,uuid,text) from public;
grant execute on function set_progress_phase(uuid,text,uuid,text) to service_role;

-- crash-reclaim now backs off (resolves 1E-a deferred Minor #2), mirroring fail_job.
create or replace function sweep_expired_leases() returns int
  language plpgsql security invoker set search_path = public as $$
declare v_count int;
begin
  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
  with expired as (select id from jobs where status = 'active' and lease_expires_at < now() for update skip locked)
  update jobs j set
    status = case when j.cancel_requested then 'cancelled'
                  when j.attempts >= j.max_attempts then 'dead_letter' else 'queued' end,
    run_after = case when j.cancel_requested or j.attempts >= j.max_attempts then j.run_after
                     else now() + make_interval(secs => (10 * power(4, least(greatest(j.attempts - 1, 0), 15)))::bigint) end,
    locked_by = null, lease_token = null, lease_expires_at = null, updated_at = now()
  from expired e where j.id = e.id;
  get diagnostics v_count = row_count; return v_count;
end $$;
```

- [ ] **Step 4: Adapter + types** — `lib/job-queue/progress-phase.ts`:
```ts
export type ProgressPhase = 'transcribing' | 'summarizing' | 'writing';
export const PROGRESS_PHASES: ProgressPhase[] = ['transcribing', 'summarizing', 'writing'];
```
In `lib/storage/job-queue.ts`: add `playlistId` to `JobKey` + `LeasedJob`, and to `JobQueue`:
```ts
setProgressPhase(jobId: string, workerId: string, leaseToken: string, phase: ProgressPhase): Promise<{ ok: boolean }>;
```
In `supabase-job-queue.ts`: `enqueue` adds `p_playlist_id: key.playlistId`; `claim` return adds `playlistId: r.playlist_id`; add:
```ts
async setProgressPhase(jobId, workerId, leaseToken, phase) {
  const { data, error } = await this.client.rpc('set_progress_phase', { p_job_id: jobId, p_worker_id: workerId, p_lease_token: leaseToken, p_phase: phase });
  if (error) throw error; return { ok: data === true };
}
```

- [ ] **Step 5: Fix the 3 sweep-affected tests** — in `tests/integration/job-queue-worker.test.ts`, the fencing tests (L37, L51) and the crash-loop test (L75) re-claim immediately after `sweep_expired_leases`; the new backoff sets `run_after` in the future. After each `sweep`, reset it so the re-claim is eligible:
```ts
await adminClient().from('jobs').update({ run_after: new Date().toISOString() }).eq('id', id);
```
(insert between the `sweep` call and the next `claim` in each of the three tests). **For the L75 crash-loop test the reset MUST go *inside* the `for` loop body, immediately after `sweep_expired_leases`** — so iteration 2 can re-claim → `attempts=2` → the next sweep dead-letters. Placing it after the loop leaves the job `queued` and it never reaches `dead_letter`.

- [ ] **Step 6: Update all enqueue fixtures** — in `job-queue-producer/store/runner.test.ts` (and any `enqueueScoped` helper), seed a `playlists` row per owner and pass `p_playlist_id` in every `enqueue_job` call (incl. the anon path — `anonSession()` then seed an anon-owned playlist). Extend `schema.test.ts` to assert `jobs.playlist_id` (`not null`, uuid), the composite FK `jobs_playlist_owner_fk`, `jobs_idem_active` includes `playlist_id`, and `progress_phase`'s check constraint.

- [ ] **Step 7: Apply + full green** — `npx supabase db reset && npm run test:integration && npx tsc --noEmit` → all green.

- [ ] **Step 8: Commit** — `git add -A && git commit -m "feat(queue): playlist coordinate in job identity + set_progress_phase + sweep backoff + adapter"`

---

### Task 2: `0009` persist RPCs — `reserve_video_slot` + `persist_summary`

**Files:**
- Modify: `supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql` (append)
- Create: `tests/integration/worker-persistence-rpcs.test.ts`

**Interfaces:**
- Produces: `reserve_video_slot(p_owner_id uuid, p_playlist_id uuid, p_video_id text) returns int`; `persist_summary(p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_video jsonb, p_artifact_status text) returns void`.

- [ ] **Step 1: Write the failing test** — sequential idempotency (`reserve` twice → same serial), **concurrent idempotency** (`Promise.all` two reserves of the same video → same serial), `persist_summary` merges without erasing artifacts + raises on 0 rows + a **status-only update preserves the prior `artifacts.summaryMd.key`**, and an owner mismatch is rejected:

```ts
test('reserve_video_slot is idempotent under concurrency', async () => {
  const u = await newUser(); const { client, userId } = await signInAs(u.email, u.password);
  const pl = await seedPlaylist(client, userId); const vid = randomUUID(); const admin = adminClient();
  const [a, b] = await Promise.all([
    admin.rpc('reserve_video_slot', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid }),
    admin.rpc('reserve_video_slot', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid }),
  ]);
  expect(a.error).toBeNull(); expect(b.error).toBeNull(); expect(a.data).toBe(b.data);
});
test('status-only persist preserves the prior summaryMd key', async () => {
  const u = await newUser(); const { client, userId } = await signInAs(u.email, u.password);
  const pl = await seedPlaylist(client, userId); const vid = randomUUID(); const admin = adminClient();
  await admin.rpc('reserve_video_slot', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid });
  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md' }, p_artifact_status: 'committed' });
  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, title: 'T' }, p_artifact_status: 'promoted' });
  const row = await admin.from('videos').select('data').eq('playlist_id', pl).eq('video_id', vid).single();
  expect(row.data!.data.artifacts.summaryMd.key).toBe('1_t.md');
  expect(row.data!.data.artifacts.summaryMd.status).toBe('promoted');
  expect(row.data!.data.title).toBe('T');
});
```
(plus the 0-row raise + owner-mismatch tests from round 1.)

- [ ] **Step 2: Run** → FAIL (RPCs absent).

- [ ] **Step 3: Append the RPCs** (verified correct by round-1 review):

```sql
create function reserve_video_slot(p_owner_id uuid, p_playlist_id uuid, p_video_id text)
  returns int language plpgsql security invoker set search_path = public as $$
declare v_serial int; v_pos int;
begin
  if not (p_owner_id = auth.uid() or auth.role() = 'service_role') then raise exception 'not authorized'; end if;
  perform 1 from playlists where id = p_playlist_id and owner_id = p_owner_id for update;
  if not found then raise exception 'playlist % not owned by %', p_playlist_id, p_owner_id; end if;
  select (v.data->>'serialNumber')::int into v_serial
    from videos v where v.playlist_id = p_playlist_id and v.video_id = p_video_id;
  if v_serial is not null then return v_serial; end if;
  select coalesce(max(v.position) + 1, 0), coalesce(max((v.data->>'serialNumber')::int) + 1, 1)
    into v_pos, v_serial from videos v where v.playlist_id = p_playlist_id;
  insert into videos (playlist_id, owner_id, video_id, position, data)
    values (p_playlist_id, p_owner_id, p_video_id, v_pos, jsonb_build_object('id', p_video_id, 'serialNumber', v_serial))
    on conflict (playlist_id, video_id) do nothing;
  select (v.data->>'serialNumber')::int into v_serial
    from videos v where v.playlist_id = p_playlist_id and v.video_id = p_video_id;
  return v_serial;
end $$;
revoke all on function reserve_video_slot(uuid,uuid,text) from public;
grant execute on function reserve_video_slot(uuid,uuid,text) to authenticated, service_role;

create function persist_summary(p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_video jsonb, p_artifact_status text)
  returns void language plpgsql security invoker set search_path = public as $$
declare v_fields jsonb; v_count int;
begin
  if not (p_owner_id = auth.uid() or auth.role() = 'service_role') then raise exception 'not authorized'; end if;
  perform 1 from playlists where id = p_playlist_id and owner_id = p_owner_id;
  if not found then raise exception 'playlist % not owned by %', p_playlist_id, p_owner_id; end if;
  v_fields := p_video || jsonb_build_object('artifacts', jsonb_build_object('summaryMd', jsonb_build_object(
      'key', coalesce(p_video->>'summaryMd', (select (data->'artifacts'->'summaryMd'->>'key')
             from videos where playlist_id = p_playlist_id and video_id = p_video_id)),
      'status', p_artifact_status)));
  update videos set
    data = (data || (v_fields - 'artifacts'))
      || jsonb_build_object('artifacts', coalesce(data->'artifacts', '{}'::jsonb) || (v_fields->'artifacts')),
    updated_at = now()
   where playlist_id = p_playlist_id and video_id = p_video_id and owner_id = p_owner_id;
  get diagnostics v_count = row_count;
  if v_count = 0 then raise exception 'persist_summary: no video row for %/%', p_playlist_id, p_video_id; end if;
end $$;
revoke all on function persist_summary(uuid,uuid,text,jsonb,text) from public;
grant execute on function persist_summary(uuid,uuid,text,jsonb,text) to authenticated, service_role;
```

- [ ] **Step 4: Apply + run** — `npx supabase db reset && npm run test:integration -- worker-persistence-rpcs` → PASS.
- [ ] **Step 5: Full guard** — `npm run test:integration && npx tsc --noEmit` → green.
- [ ] **Step 6: Commit** — `git commit -am "feat(queue): reserve_video_slot + persist_summary (idempotent, owner-scoped, merge)"`

---

### Task 3: Worker storage seam + persistence/read helpers

**Files:**
- Modify: `lib/storage/resolve.ts` (`getWorkerStorageBundle`)
- Create: `lib/storage/worker-persistence.ts` (`reserveVideoSlot`, `persistSummary`, `readVideo`)
- Create: `tests/integration/worker-storage-bundle.test.ts`

**Interfaces:**
- Produces:
  - `getWorkerStorageBundle(serviceClient, ownerId, playlistId): Promise<{ blobStore: BlobStore; principal: Principal; ownerId: string; playlistId: string }>` — resolves `playlists.id → { playlist_key, owner_id }`, asserts `owner_id === ownerId` (throws otherwise), builds `Principal { id: ownerId, indexKey: playlist_key }`.
  - `reserveVideoSlot(client, ownerId, playlistId, videoId): Promise<number>`
  - `persistSummary(client, ownerId, playlistId, videoId, video: Partial<Video>, status: 'committed'|'promoted'): Promise<void>`
  - `readVideo(client, playlistId, videoId): Promise<Video | null>` — **`playlist_id`-keyed** (`from('videos').select('data').eq('playlist_id', playlistId).eq('video_id', videoId).maybeSingle()`), owner-safe (never resolves by the non-unique `playlist_key`). This is the idempotency-skip read.

- [ ] **Step 1: Write the failing test** — `getWorkerStorageBundle` resolves the principal (`indexKey === playlist_key`) and **rejects a playlist owned by another owner**; **two owners sharing one `playlist_key`** each resolve their own row by `playlistId` (the B1 regression); `readVideo` returns the persisted row by `(playlistId, videoId)` and does not throw when two owners share a `playlist_key`.

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement** — `worker-persistence.ts` (`reserveVideoSlot`/`persistSummary` call the Task 2 RPCs; `readVideo` is the direct `playlist_id`-keyed select, returning `data as Video`). `getWorkerStorageBundle` resolves `playlists` by `id`, asserts owner, builds `SupabaseBlobStore(serviceClient, ARTIFACTS_BUCKET)` + principal; reuse `validateStorageEnv()`.

- [ ] **Step 4: Run** — `npm run test:integration -- worker-storage-bundle` → PASS.
- [ ] **Step 5: Full guard** — `npm run test:integration && npx tsc --noEmit` → green.
- [ ] **Step 6: Commit** — `git commit -am "feat(storage): worker seam (UUID-bound) + reserve/persist/readVideo helpers"`

---

### Task 4: Signal threading through Gemini/transcript

**Files:**
- Modify: `lib/gemini.ts` (`generateSummary`, `generateJson`, `transcribeViaGemini`), incl. re-throwing `AbortError` unwrapped from `generateSummary`
- Modify: `lib/transcript-source.ts` (`resolveTranscriptSegments` + typed error)
- Create: `lib/transcript-source-errors.ts` (`PermanentTranscriptError`)
- Create/Modify: `tests/lib/gemini-signal.test.ts`, `tests/lib/transcript-source.test.ts`

**Interfaces:**
- Produces: optional trailing `opts?: { signal?: AbortSignal }` on `generateSummary`, `transcribeViaGemini`, `generateJson`, `resolveTranscriptSegments`; abort-aware backoff; `PermanentTranscriptError extends Error`. **`generateSummary` re-throws an `AbortError` (by `name`) unwrapped**, not wrapped in `Error('Gemini summary failed…')`.

- [ ] **Step 1: Write the failing test** — `gemini-signal.test.ts`: mock `model.generateContent` to **reject when `signal` fires** (not merely hang); call `generateSummary(segs,'en','v',{ signal })`; abort; assert the rejection's `name === 'AbortError'` (identity preserved) and that it rejects before the retry backoff would have elapsed.

- [ ] **Step 2: Run** → FAIL (no opts; abort wrapped as generic `Error`; backoff not abort-aware).

- [ ] **Step 3: Implement** — widen leaf calls to `{ timeout: REQUEST_TIMEOUT_MS, signal: opts?.signal }`; thread `opts` through `generateSummary → attempt() → generateJson`; in `generateJson`, `if (opts?.signal?.aborted) throw new DOMException('aborted','AbortError');` before each attempt and make the backoff sleep abort-aware (reject with `AbortError` on abort). In `generateSummary`'s outer catch, **re-throw unwrapped when `err?.name === 'AbortError'`** (else keep the existing `Error('Gemini summary failed: …', { cause })`). In `resolveTranscriptSegments`, add `signal?`, forward it, and throw `PermanentTranscriptError` only when captions returned empty AND Gemini returned zero segments (deterministic no-source); wrap any other fallback failure in the existing retryable `Error`.

- [ ] **Step 4: Run** — `npx jest gemini-signal transcript-source` → PASS.
- [ ] **Step 5: Local regression** — `npx jest gemini transcript-source pipeline && npx tsc --noEmit` → green (optional params; existing callers unchanged).
- [ ] **Step 6: Commit** — `git commit -am "feat(gemini): thread AbortSignal + abort-aware backoff; unwrap AbortError; typed transcript error"`

---

### Task 5: `summaryCore` extraction + local re-wire

**Files:**
- Create: `lib/ingestion/summary-core.ts`
- Modify: `lib/pipeline.ts` (`writeSummaryDoc` delegates to `summaryCore`)
- Create: `tests/lib/summary-core.test.ts`; keep `tests/lib/pipeline-write-summary.test.ts` green (golden)

**Interfaces:**
- Produces: `summaryCore(input: { videoId; title; youtubeUrl; channel?; durationSeconds; baseName }, deps: { resolveTranscriptSegments; generateSummary; extractQuickView }, opts?: { signal?: AbortSignal }): Promise<{ frontmatter: string; markdown: string; mdContent: string; quickView: { tldr: string; takeaways: string[] } | null; geminiFields: { language: 'en'|'ko'; ratings; overallScore; videoType?; audience?; tags?; tldr?; takeaways? } }>` — pure of storage.

- [ ] **Step 1–2:** failing test with mocked deps asserting `mdContent`/`geminiFields` match today's `writeSummaryDoc` output → FAIL.
- [ ] **Step 3: Implement** — move everything in `writeSummaryDoc` **except** the `blobStore.put(localPrincipal(outputFolder), …)` (L105) into `summaryCore`; re-point `writeSummaryDoc` to call `summaryCore` then do its existing local `put` — behavior preserved.
- [ ] **Step 4:** `npx jest summary-core pipeline-write-summary` → PASS (golden proves byte-identical local output).
- [ ] **Step 5:** `npx jest pipeline && npx tsc --noEmit` → green.
- [ ] **Step 6: Commit** — `git commit -am "refactor(ingestion): extract store-agnostic summaryCore; local re-wired"`

---

### Task 6: `runOnce` upgrade — heartbeat, composed signal, teardown

**Files:**
- Modify: `lib/job-queue/worker-runner.ts`
- Create: `lib/job-queue/handler-context.ts` (`HandlerCtx`, the upgraded `JobHandler`)
- Create: `lib/job-queue/errors.ts` (`NonRetryableError`)
- Modify: existing runner tests + `echoHandler` (align to the new `JobHandler`)
- Create: `tests/integration/worker-runner-runtime.test.ts`

**Interfaces:**
- Consumes: `ProgressPhase` (Task 1), `LeasedJob`/`JobQueue.setProgressPhase` (Task 1).
- Produces: `HandlerCtx = { isCancelled(): Promise<boolean>; signal: AbortSignal; setPhase(p: ProgressPhase): Promise<void> }`; `JobHandler = (job: LeasedJob, ctx: HandlerCtx) => Promise<unknown>` (replaces the 1E-a `JobHandler` in `worker-runner.ts`; `echoHandler` and existing runner tests are updated to the new ctx in THIS task — no cross-task type collision); `NonRetryableError extends Error`; `runOnce(queue, handler, opts)` with `opts.shutdownSignal?: AbortSignal`.

- [ ] **Step 1: Write the failing test** — with a trivial inline handler, claiming with a **short lease** (`leaseSeconds: 2`) so the heartbeat interval (`leaseSeconds*1000/3 ≈ 667ms`) fires several times before the lease would expire: (a) a handler that runs ~3s (> the 2s lease) still `complete`s successfully — proving the heartbeat **extended** the lease (without it, the lease expires and `complete` returns `ok:false`/`'lost'`); (b) the `setInterval` is cleared on throw (spy shows no heartbeat after settle); (c) a handler that throws `NonRetryableError` → `fail(retryable:false)` → status `failed`; (d) `setPhase('summarizing')` writes `progress_phase` on the row (via `set_progress_phase`); (e) **heartbeat RPC rejects → treated as lease-loss** (mock `queue.heartbeat` to throw; assert the handler is aborted and the process does not crash — no unhandled rejection); (f) **lease-lost mid-handler → no double terminal write** (force `heartbeat` `ok:false`; assert exactly one of `complete`/`fail` is attempted and it's the no-op `'lost'` path); (g) **wall-clock exceeded → prompt `fail(retryable:true)`** (tiny `wallClockMs` in opts; a slow handler is aborted and failed retryably).

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement** — in `worker-runner.ts`: import `JobHandler`/`HandlerCtx` from `handler-context.ts` (delete the local `JobHandler`; **re-export it for back-compat: `export type { JobHandler } from './handler-context';`** so `tests/integration/job-queue-runner.test.ts`'s `import type { JobHandler } from '@/lib/job-queue/worker-runner'` keeps compiling; update `echoHandler` to the new ctx signature). Build the composed `signal = AbortSignal.any([wallClock, leaseLost, opts.shutdownSignal].filter(Boolean) as AbortSignal[])`. **Heartbeat: derive the interval from the lease** and guard the rejection path:
```ts
const leaseSeconds = opts.leaseSeconds ?? 120;
const hb = setInterval(() => {
  queue.heartbeat(job.id, opts.workerId, job.leaseToken, leaseSeconds)
    .then(r => { if (!r.ok) leaseLost.abort(); })
    .catch(() => leaseLost.abort());   // a throwing heartbeat ⇒ treat as lease-loss, never an unhandled rejection (M1)
}, Math.floor((leaseSeconds * 1000) / 3));
```
`setPhase = (p) => queue.setProgressPhase(job.id, opts.workerId, job.leaseToken, p).then(() => {})`. **Wall-clock timer — store the handle and unref it, then clear it alongside the heartbeat in `finally`** so a fast job never leaves a ref'd 600s timer holding the event loop open (Jest would otherwise hang without `--forceExit`):
```ts
const wallClock = new AbortController();
const wct = setTimeout(() => wallClock.abort(), opts.wallClockMs ?? 600_000);
wct.unref?.();                      // don't keep the process/Jest alive on its own
try {
  // … heartbeat setInterval(hb), run handler under `signal`, complete/fail …
} finally {
  clearInterval(hb);
  clearTimeout(wct);                // release the wall-clock timer on every exit path
}
```
A `let settled = false;` guards the single `complete`/`fail`; map `err instanceof NonRetryableError` → `fail(…, { retryable: false })`.

- [ ] **Step 4: Run** — `npm run test:integration -- worker-runner-runtime` → PASS.
- [ ] **Step 5: Full guard** — `npm run test:integration && npx jest worker && npx tsc --noEmit` → green (existing runner tests updated).
- [ ] **Step 6: Commit** — `git commit -am "feat(worker): runOnce heartbeat + composed signal + setPhase + teardown + retryability"`

---

### Task 7: `summaryHandler` — idempotent, self-healing

**Files:**
- Create: `lib/job-queue/summary-handler.ts`
- Create: `lib/job-queue/ingestion-payload.ts` (`IngestionPayload` + zod validator)
- Create: `tests/integration/summary-handler.test.ts`

**Interfaces:**
- Consumes: Task 3 (`getWorkerStorageBundle`, `reserveVideoSlot`, `persistSummary`, `readVideo`), Task 4 (signal), Task 5 (`summaryCore`), Task 6 (`HandlerCtx`, `JobHandler`, `NonRetryableError`), `CURRENT_DOC_VERSION` (`lib/doc-version.ts`), `docVersionKey` (**exported from `lib/storage/job-queue.ts`**, not `doc-version.ts`), `slugify` (`lib/slugify.ts`), `padSerial` (`lib/serial-filename.ts`).
- Produces: `makeSummaryHandler(serviceClient: SupabaseClient): JobHandler`; `IngestionPayload` (spec §6, incl. `playlistIndex`, `videoPublishedAt`, `addedToPlaylistAt`).
- **Testing note:** call the handler directly with a mock `HandlerCtx` (`{ isCancelled: async()=>false, signal: new AbortController().signal, setPhase: async()=>{} }`) — no `runOnce` needed.

- [ ] **Step 1: Write the failing test** — (a) happy path → `Video` row persisted (`serialNumber`, `playlistIndex`, `summaryMd`, `ratings`, `artifacts.summaryMd.status==='promoted'`) + blob present; (b) **idempotent re-run of the same job** (a fresh `makeSummaryHandler` on the same DB state) → the Gemini mock is **not** called again (assert via a module-level call counter reset before the first run and checked after the second) and the serial is unchanged; (c) malformed payload → `NonRetryableError`; (d) over-long video → `NonRetryableError`; (e) **pre-promote-crash retry (self-healing, spec §10):** run the handler once with the blob `promote` stubbed to throw *after* `persistSummary(committed)` (simulating a crash between commit and promote); re-run a fresh handler → it re-reserves the **same serial**, re-stages the same deterministic key, promotes cleanly, and ends `artifacts.summaryMd.status==='promoted'` — no orphan, no serial drift, Gemini called again (because nothing was promoted, so the skip does not fire — that is correct); (f) **transient transcript failure → retryable:** mock `resolveTranscriptSegments` to throw a non-`PermanentTranscriptError` → the handler propagates it (the runner will mark it retryable) and does **not** throw `NonRetryableError`.

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement** — the handler:
  1. `IngestionPayload` zod-validate → `NonRetryableError` on failure; reject `durationSeconds > MAX_DURATION_SECONDS` (`export const MAX_DURATION_SECONDS = 4 * 3600`) as `NonRetryableError`.
  2. `bundle = await getWorkerStorageBundle(serviceClient, job.ownerId, job.playlistId)`.
  3. **idempotency skip:** `const existing = await readVideo(serviceClient, job.playlistId, job.videoId);` if `existing?.artifacts?.summaryMd?.status === 'promoted'` **and** `existing.docVersion && docVersionKey(existing.docVersion) === job.version` → return early (no Gemini). *(Note: `artifacts` is on the DB `data` jsonb, not the `Video` zod type — read it via `(existing as any).artifacts`.)*
  4. `const serial = await reserveVideoSlot(serviceClient, job.ownerId, job.playlistId, job.videoId); const baseName = \`${padSerial(serial)}_${slugify(payload.title)}\`;`
  5. `await ctx.setPhase('transcribing')`; `const core = await summaryCore({ …payload, baseName }, deps, { signal: ctx.signal });` with `setPhase('summarizing')` before Gemini and `setPhase('writing')` before the write.
  6. build the full `Video` = `core.geminiFields` + `{ id: job.videoId, title, youtubeUrl, durationSeconds, channel, serialNumber: serial, summaryMd: \`${baseName}.md\`, playlistIndex: payload.playlistIndex, videoPublishedAt, addedToPlaylistAt, docVersion: CURRENT_DOC_VERSION, archived: false, processedAt: new Date().toISOString() }`.
  7. `putStaged(principal, \`${baseName}.md\`, bytes) → verify exists → persistSummary(…, video, 'committed') → promote → persistSummary(…, video, 'promoted')`.

- [ ] **Step 4: Run** — `npm run test:integration -- summary-handler` → PASS.
- [ ] **Step 5: Full guard** — `npm run test:integration && npx tsc --noEmit` → green.
- [ ] **Step 6: Commit** — `git commit -am "feat(worker): idempotent, self-healing summary handler"`

---

### Task 8: `worker/main.ts` entrypoint

**Files:**
- Create: `worker/main.ts`
- Modify: `package.json` (`"worker": "ts-node worker/main.ts"`)
- Create: `tests/integration/worker-main.test.ts`

**Interfaces:**
- Produces: `runWorkerLoop(deps: { queue; handler; shutdownSignal: AbortSignal; workerId: string }): Promise<void>` (exported for tests); `main()` (env fail-fast, build service client + handler, SIGTERM → `AbortController`, call `runWorkerLoop`).

- [ ] **Step 1–2:** failing test — seed one job (+ playlist/video fixtures), run `runWorkerLoop` with a shutdown signal aborted after the first `runOnce`, assert the job reaches `completed`.
- [ ] **Step 3: Implement** — loop `while (!shutdownSignal.aborted) { const r = await runOnce(queue, handler, { workerId, shutdownSignal }); if (r === 'idle') await sleep(POLL_MS, shutdownSignal); }`. `main()`: `validateStorageEnv()` + assert `GEMINI_API_KEY`/`YOUTUBE_API_KEY`/`SUPABASE_SERVICE_ROLE_KEY`; build a service-role client; `handler = makeSummaryHandler(client)`; `process.on('SIGTERM', () => ac.abort())`.
- [ ] **Step 4–5:** `npm run test:integration -- worker-main` → PASS; then `npm run test:integration && npx tsc --noEmit` → green.
- [ ] **Step 6: Commit** — `git commit -am "feat(worker): worker/main.ts entrypoint + loop + SIGTERM shutdown"`

---

### Task 9: Confinement → `worker/` + flaky-test cleanup

**Files:**
- Modify: `scripts/check-service-confinement.ts` (`collectEntrypoints`)
- Modify: `tests/integration/job-queue-worker.test.ts` (harden the `fail_job` `run_after`-reset backoff test — the DB-clock-skew flake, distinct from the 3 sweep tests fixed in Task 1)

- [ ] **Step 1:** confirm `npm run check:confinement` does not yet scan `worker/`; then extend `collectEntrypoints()` to include `worker/**`, verifying `worker/main.ts` is the sole allowed `service_role` consumer.
- [ ] **Step 2:** harden the `fail_job` backoff test (set `run_after = now()` in-DB rather than via the client clock; or assert on job id).
- [ ] **Step 3:** `npm run check:confinement` → PASS; `npm run test:integration -- job-queue-worker` 3× → stable.
- [ ] **Step 4: Full guard** — `npx jest && npm run test:integration && npm run check:confinement && npx tsc --noEmit` → all green.
- [ ] **Step 5: Commit** — `git commit -am "chore(worker): extend confinement scan to worker/; harden flaky fail_job test"`

---

## Notes for the executor

- **Tasks 1 & 2 get the per-task adversarial review** (Codex + Claude) on the SQL.
- After every SQL/integration task: `npx supabase db reset` → `npm run test:integration` → `npx tsc --noEmit` (the tsc step is mandatory).
- **`playlistIndex` is 0-indexed from YouTube but `VideoSchema.playlistIndex` is `.int().positive()`** — the 1E-c producer must send a 1-based index; 1E-b fixtures use `1..N`. (Documented producer-contract note; not a 1E-b defect.)
- `persist_summary`/`reserve_video_slot` trust the service worker's `p_owner_id` (it comes from the leased job's `ownerId`, not an external caller) — service_role is the trust boundary; deployment hardening is 1H.
- `writeSummaryDoc` stays the local path; the cloud handler never calls it (it calls `summaryCore` + `persistSummary`).
- **`security invoker` vs spec §8's `security definer` (reconciled):** the plan deliberately uses `security invoker` for `reserve_video_slot`/`persist_summary`/`set_progress_phase`. It is functionally equivalent-and-safer here: `service_role` bypasses RLS regardless, and the explicit `owner_id = p_owner_id` + playlist-ownership checks reject a mismatched owner even for the worker; for an authenticated caller, RLS `owner_id = auth.uid()` aligns with the guard. This supersedes spec §8's `definer` wording — no behavioural difference for the worker path.
