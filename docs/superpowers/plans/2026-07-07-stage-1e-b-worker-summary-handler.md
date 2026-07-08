# Stage 1E-b — Worker + Summary Ingestion Handler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A long-lived `service_role` worker that leases jobs from the 1E-a queue and runs real, idempotent, retry-safe summary ingestion, persisting the full `Video` and the summary artifact through owner-scoped Postgres RPCs.

**Architecture:** A `worker/main.ts` loop calls an upgraded `runOnce` that supervises a `summaryHandler` with a heartbeat loop, a composed `AbortSignal` (wall-clock ⊕ lease-loss ⊕ SIGTERM), cancellation, retryability, and `progress_phase` stamping. The handler reserves an idempotent serial, skips if already promoted, calls a store-agnostic `summaryCore`, then persists via two idempotent owner-scoped RPCs (`reserve_video_slot`, `persist_summary`). The job identity gains a `playlistId` coordinate with a composite owner-safe FK.

**Tech Stack:** TypeScript, Next.js, Supabase (Postgres + `@supabase/supabase-js`), `@google/generative-ai`, jest (unit + integration `--runInBand` against a local Supabase stack).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-07-stage-1e-b-worker-ingestion-handler-design.md` (v3). ADR: `docs/adr/0002-playlist-in-job-identity.md`.
- **Scope: summary only.** Dig, slide-asset capture → 1E-b-2. Live deploy/resource caps → 1H. Producer/route → 1E-c.
- **Job identity is `(owner_id, playlist_id, video_id, section_id, job_kind, job_version)`.** The `jobs → playlists` FK MUST be composite `(playlist_id, owner_id) references playlists(id, owner_id)` (never single-column).
- **Persistence is idempotent + owner-scoped.** `reserve_video_slot` returns the *existing* serial on conflict; `persist_summary` merges (never full-replaces `videos.data`, never erases the `artifacts` sub-object) and `raise`s on 0 rows. Both `security invoker` with the guard `(owner_id = auth.uid() or auth.role() = 'service_role')`.
- **`AbortSignal` bounds worker occupancy, not Gemini billing.** Never claim aborting avoids the charge. Sequential double-charge is closed by the idempotency skip; the concurrent one is deferred to 1D.
- **Migrations are append-only and run via `db reset`.** Tasks 1–2 both edit `supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql`; every SQL/integration task runs `npx supabase db reset` then the integration suite, and ends with `npx tsc --noEmit`.
- **`docVersionKey({major:3,minor:3}) === '3.3'`** is the `job_version` string. `CURRENT_DOC_VERSION = {major:3, minor:3}`.
- `progress_phase ∈ {'transcribing','summarizing','writing'}` — bounded by a TS enum AND a DB check constraint.
- Test commands: `npx jest <file>` (unit), `npm run test:integration` (integration, `--runInBand`), `npm run check:confinement`, `npx tsc --noEmit`. Integration tests need the local stack env in `.env.test.local` (`supabase status -o env > .env.test.local`).
- Every enqueue fixture MUST seed a real `playlists` row owned by the principal (composite FK), including the anon path.

---

## Task ordering & review gates

| Task | Deliverable | Adversarial-review gate |
|---|---|---|
| 1 | `0009` job-identity re-key (FK, index, `enqueue_job`, sweep backoff, `progress_phase`) | **YES (Codex + Claude)** |
| 2 | `0009` persist RPCs (`reserve_video_slot`, `persist_summary`) | **YES (Codex + Claude)** |
| 3 | Queue types + adapter (`playlistId`) | standard |
| 4 | Worker storage seam + persistence helpers | standard |
| 5 | Signal threading through Gemini/transcript | standard |
| 6 | `summaryCore` extraction + local re-wire | standard |
| 7 | `summaryHandler` (idempotent, self-healing) | standard |
| 8 | `runOnce` upgrade (heartbeat, composed signal, teardown) | standard |
| 9 | `worker/main.ts` entrypoint | standard |
| 10 | Confinement → `worker/` + flaky-test cleanup | standard |

---

### Task 1: `0009` migration — job identity re-key

**Files:**
- Create: `supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql` (this task adds the identity re-key; Task 2 appends the persist RPCs to the same file)
- Create: `tests/integration/job-queue-playlist-identity.test.ts`
- Modify: `tests/integration/schema.test.ts` (extend the jobs-schema guardrail with `playlist_id` + `progress_phase`)

**Interfaces:**
- Consumes: 1E-a `jobs` table, `jobs_idem_active`, `enqueue_job`, `sweep_expired_leases` (0008); `playlists(id, owner_id)` with `unique(id, owner_id)` (0001).
- Produces: `enqueue_job(p_playlist_id uuid, p_video_id text, p_section_id int, p_job_kind text, p_job_version text, p_payload jsonb)`; `jobs.playlist_id uuid not null`; `jobs.progress_phase text` (checked); re-keyed `jobs_idem_active`; `sweep_expired_leases` with backoff.

- [ ] **Step 1: Write the failing test** — `tests/integration/job-queue-playlist-identity.test.ts`

```ts
import { newUser, signInAs, adminClient } from './helpers/clients';
import { randomUUID } from 'crypto';

async function seedPlaylist(client: any, ownerId: string, key: string): Promise<string> {
  const { data, error } = await client.from('playlists')
    .insert({ owner_id: ownerId, playlist_key: key, playlist_url: `https://x/${key}` })
    .select('id').single();
  if (error) throw error;
  return data.id as string;
}

test('same (video,section,kind,version) under two playlists → two distinct jobs', async () => {
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  const plA = await seedPlaylist(client, userId, `A-${randomUUID()}`);
  const plB = await seedPlaylist(client, userId, `B-${randomUUID()}`);
  const vid = randomUUID();
  const argsFor = (pl: string) => ({ p_playlist_id: pl, p_video_id: vid, p_section_id: -1, p_job_kind: 'summary', p_job_version: '3.3', p_payload: {} });
  const a = await client.rpc('enqueue_job', argsFor(plA));
  const b = await client.rpc('enqueue_job', argsFor(plB));
  expect(a.error).toBeNull(); expect(b.error).toBeNull();
  expect(a.data[0].job_id).not.toBe(b.data[0].job_id);
  expect(a.data[0].joined).toBe(false); expect(b.data[0].joined).toBe(false);
});

test('re-enqueue at the same playlist joins', async () => {
  const u = await newUser();
  const { client, userId } = await signInAs(u.email, u.password);
  const pl = await seedPlaylist(client, userId, `C-${randomUUID()}`);
  const vid = randomUUID();
  const args = { p_playlist_id: pl, p_video_id: vid, p_section_id: -1, p_job_kind: 'summary', p_job_version: '3.3', p_payload: {} };
  const first = await client.rpc('enqueue_job', args);
  const second = await client.rpc('enqueue_job', args);
  expect(second.data[0].job_id).toBe(first.data[0].job_id);
  expect(second.data[0].joined).toBe(true);
});

test('enqueue against another owner\'s playlist is rejected', async () => {
  const owner = await newUser();
  const { client: ownerClient, userId: ownerId } = await signInAs(owner.email, owner.password);
  const victimPl = await seedPlaylist(ownerClient, ownerId, `V-${randomUUID()}`);
  const attacker = await newUser();
  const { client: atkClient } = await signInAs(attacker.email, attacker.password);
  const res = await atkClient.rpc('enqueue_job', {
    p_playlist_id: victimPl, p_video_id: randomUUID(), p_section_id: -1,
    p_job_kind: 'summary', p_job_version: '3.3', p_payload: {} });
  expect(res.error).not.toBeNull(); // composite FK / owner guard rejects
});
```

- [ ] **Step 2: Run test to verify it fails** — `npm run test:integration -- job-queue-playlist-identity` → FAIL (`enqueue_job` has no `p_playlist_id`).

- [ ] **Step 3: Write the migration** — `supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql`

```sql
-- 0009: 1E-b — job-identity playlist coordinate + worker persistence RPCs.
-- jobs is empty in every environment (1E-a undeployed) → safe re-key, no data migration.

-- 1. playlist coordinate on the job identity, composite owner-safe FK (ADR-0002).
alter table jobs add column playlist_id uuid not null;
alter table jobs add constraint jobs_playlist_owner_fk
  foreign key (playlist_id, owner_id) references playlists(id, owner_id) on delete cascade;

-- 2. bounded progress phase (advisory display state).
alter table jobs add column progress_phase text
  check (progress_phase in ('transcribing','summarizing','writing'));

-- 3. re-key the active idempotency index to include playlist.
drop index jobs_idem_active;
create unique index jobs_idem_active
  on jobs (owner_id, playlist_id, video_id, section_id, job_kind, job_version)
  where status in ('queued','active','completed');

-- 4. replace enqueue_job with the playlist-aware signature (drop old, create new).
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
    if v_id is not null then
      return query select v_id, 'queued'::text, false; return;
    end if;
    select j.id, j.status, j.payload into v_id, v_status, v_payload from jobs j
      where j.owner_id = auth.uid() and j.playlist_id = p_playlist_id and j.video_id = p_video_id
        and j.section_id = p_section_id and j.job_kind = p_job_kind and j.job_version = p_job_version
        and j.status in ('queued','active','completed')
      limit 1;
    if v_id is not null then
      if v_payload is distinct from p_payload then
        raise log 'enqueue_job: joined % with a divergent payload (kept existing)', v_id;
      end if;
      return query select v_id, v_status, true; return;
    end if;
  end loop;
end $$;
revoke all on function enqueue_job(uuid,text,int,text,text,jsonb) from public;
grant execute on function enqueue_job(uuid,text,int,text,text,jsonb) to anon, authenticated, service_role;

-- 5. crash-reclaim now backs off (resolves 1E-a deferred Minor #2), mirroring fail_job.
create or replace function sweep_expired_leases() returns int
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
    run_after = case when j.cancel_requested or j.attempts >= j.max_attempts then j.run_after
                     else now() + make_interval(secs => (10 * power(4, least(greatest(j.attempts - 1, 0), 15)))::bigint) end,
    locked_by = null, lease_token = null, lease_expires_at = null, updated_at = now()
  from expired e where j.id = e.id;
  get diagnostics v_count = row_count;
  return v_count;
end $$;
```

- [ ] **Step 4: Apply + run test** — `npx supabase db reset && npm run test:integration -- job-queue-playlist-identity` → PASS.

- [ ] **Step 5: Extend the schema guardrail** — in `tests/integration/schema.test.ts`, add assertions that `jobs.playlist_id` exists (`not null`, type `uuid`), the FK `jobs_playlist_owner_fk` is composite, `jobs_idem_active` includes `playlist_id`, and `jobs.progress_phase` has the check constraint. Run: `npm run test:integration -- schema` → PASS.

- [ ] **Step 6: Full guard** — `npm run test:integration && npx tsc --noEmit` → all green.

- [ ] **Step 7: Commit** — `git add -A && git commit -m "feat(queue): 0009 job identity playlist coordinate + composite FK + sweep backoff"`

---

### Task 2: `0009` persist RPCs — `reserve_video_slot` + `persist_summary`

**Files:**
- Modify: `supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql` (append the two RPCs)
- Create: `tests/integration/worker-persistence-rpcs.test.ts`

**Interfaces:**
- Consumes: `videos` table (PK `(playlist_id, video_id)`, composite FK, CHECK `data->>'id' = video_id`), `playlists`, the `merge_video_data` merge model (0007), the owner-guard pattern.
- Produces: `reserve_video_slot(p_owner_id uuid, p_playlist_id uuid, p_video_id text) returns int` (idempotent serial); `persist_summary(p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_video jsonb, p_artifact_status text) returns void` (owner-scoped merge, raises on 0 rows).

- [ ] **Step 1: Write the failing test** — `tests/integration/worker-persistence-rpcs.test.ts`

```ts
import { newUser, signInAs, adminClient } from './helpers/clients';
import { randomUUID } from 'crypto';

async function seedPlaylist(client: any, ownerId: string): Promise<string> {
  const { data } = await client.from('playlists')
    .insert({ owner_id: ownerId, playlist_key: `k-${randomUUID()}`, playlist_url: 'https://x' })
    .select('id').single();
  return data.id as string;
}

test('reserve_video_slot returns the SAME serial on re-call (idempotent)', async () => {
  const u = await newUser(); const { client, userId } = await signInAs(u.email, u.password);
  const pl = await seedPlaylist(client, userId); const vid = randomUUID();
  const admin = adminClient();
  const first = await admin.rpc('reserve_video_slot', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid });
  const second = await admin.rpc('reserve_video_slot', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid });
  expect(first.error).toBeNull();
  expect(second.data).toBe(first.data); // same serial, not first+1
});

test('persist_summary merges without erasing artifacts, raises on 0 rows', async () => {
  const u = await newUser(); const { client, userId } = await signInAs(u.email, u.password);
  const pl = await seedPlaylist(client, userId); const vid = randomUUID();
  const admin = adminClient();
  await admin.rpc('reserve_video_slot', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid });
  // write an artifact status first
  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid,
    p_video: { id: vid }, p_artifact_status: 'committed' });
  // then persist the full video — must NOT erase artifacts.summaryMd.status
  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid,
    p_video: { id: vid, title: 'T', summaryMd: `1_t.md` }, p_artifact_status: 'promoted' });
  const row = await admin.from('videos').select('data').eq('playlist_id', pl).eq('video_id', vid).single();
  expect(row.data!.data.title).toBe('T');
  expect(row.data!.data.artifacts.summaryMd.status).toBe('promoted');
  // 0-row raise: unknown video
  const bad = await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: randomUUID(),
    p_video: { id: 'z' }, p_artifact_status: 'committed' });
  expect(bad.error).not.toBeNull();
});

test('persist_summary rejects a mismatched owner', async () => {
  const u = await newUser(); const { client, userId } = await signInAs(u.email, u.password);
  const pl = await seedPlaylist(client, userId); const vid = randomUUID();
  const admin = adminClient();
  await admin.rpc('reserve_video_slot', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid });
  const res = await admin.rpc('persist_summary', { p_owner_id: randomUUID(), p_playlist_id: pl, p_video_id: vid,
    p_video: { id: vid }, p_artifact_status: 'committed' });
  expect(res.error).not.toBeNull();
});
```

- [ ] **Step 2: Run test to verify it fails** — `npm run test:integration -- worker-persistence-rpcs` → FAIL (RPCs don't exist).

- [ ] **Step 3: Append the RPCs to `0009`**

```sql
-- 6. reserve_video_slot: idempotent serial reservation. Unlike claim_video_slot, on conflict
--    it RETURNS THE EXISTING row's serial (not a freshly-computed one) so a retry is truly idempotent.
create function reserve_video_slot(p_owner_id uuid, p_playlist_id uuid, p_video_id text)
  returns int language plpgsql security invoker set search_path = public as $$
declare v_serial int; v_pos int;
begin
  if not (p_owner_id = auth.uid() or auth.role() = 'service_role') then
    raise exception 'not authorized'; end if;
  perform 1 from playlists where id = p_playlist_id and owner_id = p_owner_id for update;
  if not found then raise exception 'playlist % not owned by %', p_playlist_id, p_owner_id; end if;

  select (v.data->>'serialNumber')::int into v_serial
    from videos v where v.playlist_id = p_playlist_id and v.video_id = p_video_id;
  if v_serial is not null then return v_serial; end if;   -- idempotent: existing row's serial

  select coalesce(max(v.position) + 1, 0), coalesce(max((v.data->>'serialNumber')::int) + 1, 1)
    into v_pos, v_serial from videos v where v.playlist_id = p_playlist_id;
  insert into videos (playlist_id, owner_id, video_id, position, data)
    values (p_playlist_id, p_owner_id, p_video_id, v_pos,
            jsonb_build_object('id', p_video_id, 'serialNumber', v_serial))
    on conflict (playlist_id, video_id) do nothing;
  -- re-read in case of a concurrent insert winning the race
  select (v.data->>'serialNumber')::int into v_serial
    from videos v where v.playlist_id = p_playlist_id and v.video_id = p_video_id;
  return v_serial;
end $$;
revoke all on function reserve_video_slot(uuid,uuid,text) from public;
grant execute on function reserve_video_slot(uuid,uuid,text) to authenticated, service_role;

-- 7. persist_summary: owner-scoped merge of the full Video + artifact status. Shallow-merges every
--    top-level key (artifacts deep-merged one level, mirroring merge_video_data) so prior artifact
--    status is never erased. Raises on 0 rows (no silent no-op). data->>'id' must stay = video_id.
create function persist_summary(
  p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_video jsonb, p_artifact_status text
) returns void language plpgsql security invoker set search_path = public as $$
declare v_fields jsonb; v_count int;
begin
  if not (p_owner_id = auth.uid() or auth.role() = 'service_role') then
    raise exception 'not authorized'; end if;
  perform 1 from playlists where id = p_playlist_id and owner_id = p_owner_id;
  if not found then raise exception 'playlist % not owned by %', p_playlist_id, p_owner_id; end if;

  v_fields := p_video || jsonb_build_object(
    'artifacts', jsonb_build_object('summaryMd', jsonb_build_object(
      'key', coalesce(p_video->>'summaryMd', (select (data->'artifacts'->'summaryMd'->>'key')
             from videos where playlist_id = p_playlist_id and video_id = p_video_id)),
      'status', p_artifact_status)));

  update videos set
    data = (data || (v_fields - 'artifacts'))
      || jsonb_build_object('artifacts',
           coalesce(data->'artifacts', '{}'::jsonb) || (v_fields->'artifacts')),
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

- [ ] **Step 6: Commit** — `git add -A && git commit -m "feat(queue): reserve_video_slot + persist_summary (idempotent, owner-scoped, merge)"`

---

### Task 3: Queue types + adapter — `playlistId`

**Files:**
- Modify: `lib/storage/job-queue.ts` (`JobKey`, `LeasedJob`)
- Modify: `lib/storage/supabase/supabase-job-queue.ts` (`enqueue`, `claim`)
- Create: `tests/integration/job-queue-playlist-adapter.test.ts`

**Interfaces:**
- Consumes: Task 1 `enqueue_job(p_playlist_id, …)` + `claim_next_job` returning `playlist_id`.
- Produces: `JobKey { playlistId: string; videoId; sectionId; kind; version }`; `LeasedJob { …; playlistId: string }`.

- [ ] **Step 1: Write the failing test** — `tests/integration/job-queue-playlist-adapter.test.ts` (enqueue via `SupabaseJobQueue` with a `playlistId` key, claim via a service client, assert `leased.playlistId === pl`). Mirror the seeding + `newUser/signInAs/adminClient` pattern.

- [ ] **Step 2: Run** → FAIL (`JobKey` has no `playlistId`; `enqueue` doesn't pass it).

- [ ] **Step 3: Implement** — in `lib/storage/job-queue.ts`:

```ts
export interface JobKey { playlistId: string; videoId: string; sectionId: number; kind: JobKind; version: string; }
export interface LeasedJob {
  id: string; ownerId: string; playlistId: string; videoId: string; sectionId: number;
  kind: JobKind; version: string; payload: unknown; attempts: number; leaseToken: string;
}
```
In `lib/storage/supabase/supabase-job-queue.ts` `enqueue`, add `p_playlist_id: key.playlistId` to the rpc object; in `claim`'s return mapping add `playlistId: r.playlist_id,`.

- [ ] **Step 4: Run** — `npm run test:integration -- job-queue-playlist-adapter` → PASS.

- [ ] **Step 5: Fix fallout** — update every existing `JobKey` literal in `tests/integration/*` to include `playlistId` (seed a playlist per test/owner, incl. the anon path). Run `npm run test:integration && npx tsc --noEmit` → green.

- [ ] **Step 6: Commit** — `git commit -am "feat(queue): thread playlistId through JobKey/LeasedJob + adapter"`

---

### Task 4: Worker storage seam + persistence helpers

**Files:**
- Modify: `lib/storage/resolve.ts` (`getWorkerStorageBundle`)
- Create: `lib/storage/worker-persistence.ts` (`reserveVideoSlot`, `persistSummary`)
- Create: `tests/integration/worker-storage-bundle.test.ts`

**Interfaces:**
- Consumes: Task 2 RPCs, `SupabaseBlobStore`, `Principal`, `playlists`.
- Produces:
  - `getWorkerStorageBundle(serviceClient: SupabaseClient, ownerId: string, playlistId: string): Promise<{ blobStore: BlobStore; principal: Principal; ownerId: string; playlistId: string }>` — resolves `playlists.id → { playlist_key, owner_id }`, asserts `owner_id === ownerId` (throws otherwise), builds `Principal { id: ownerId, indexKey: playlist_key }`.
  - `reserveVideoSlot(client, ownerId, playlistId, videoId): Promise<number>`
  - `persistSummary(client, ownerId, playlistId, videoId, video, status: 'committed'|'promoted'): Promise<void>`

- [ ] **Step 1: Write the failing test** — assert `getWorkerStorageBundle` resolves the principal (`indexKey === playlist_key`), and **rejects a playlist owned by another owner**; assert two owners sharing a `playlist_key` each resolve their own row (the B1 regression: seed two owners with the same `playlist_key`, resolve each by `playlistId`, confirm distinct principals).

- [ ] **Step 2: Run** → FAIL (function absent).

- [ ] **Step 3: Implement** — `lib/storage/worker-persistence.ts`:

```ts
import type { SupabaseClient } from '@supabase/supabase-js';
import type { Video } from '@/types';

export async function reserveVideoSlot(client: SupabaseClient, ownerId: string, playlistId: string, videoId: string): Promise<number> {
  const { data, error } = await client.rpc('reserve_video_slot', { p_owner_id: ownerId, p_playlist_id: playlistId, p_video_id: videoId });
  if (error) throw error;
  return data as number;
}
export async function persistSummary(client: SupabaseClient, ownerId: string, playlistId: string, videoId: string, video: Partial<Video>, status: 'committed' | 'promoted'): Promise<void> {
  const { error } = await client.rpc('persist_summary', { p_owner_id: ownerId, p_playlist_id: playlistId, p_video_id: videoId, p_video: video, p_artifact_status: status });
  if (error) throw error;
}
```
In `lib/storage/resolve.ts` add `getWorkerStorageBundle` (resolve `playlists` by `id`, assert `owner_id === ownerId`, build the `SupabaseBlobStore` + principal). Reuse `ARTIFACTS_BUCKET` and `validateStorageEnv()`.

- [ ] **Step 4: Run** — `npm run test:integration -- worker-storage-bundle` → PASS.
- [ ] **Step 5: Full guard** — `npm run test:integration && npx tsc --noEmit` → green.
- [ ] **Step 6: Commit** — `git commit -am "feat(storage): worker storage seam (UUID-bound) + persist helpers"`

---

### Task 5: Signal threading through Gemini/transcript

**Files:**
- Modify: `lib/gemini.ts` (`generateSummary`, `generateJson`, `transcribeViaGemini`)
- Modify: `lib/transcript-source.ts` (`resolveTranscriptSegments` + typed error)
- Create: `lib/transcript-source-errors.ts` (`PermanentTranscriptError`)
- Create/Modify tests: `tests/lib/gemini-signal.test.ts`, `tests/lib/transcript-source.test.ts`

**Interfaces:**
- Produces: optional trailing `opts?: { signal?: AbortSignal }` on `generateSummary`, `transcribeViaGemini`, `resolveTranscriptSegments`; `generateJson(..., opts?: { signal?: AbortSignal })` with abort-aware backoff; `PermanentTranscriptError extends Error` (thrown only when the fallback is deterministically no-source).

- [ ] **Step 1: Write the failing test** — `tests/lib/gemini-signal.test.ts`: mock `model.generateContent` to hang; call `generateSummary(segs,'en','v',{ signal })`; abort the controller; assert the promise rejects **promptly** (`AbortError`) rather than running the full retry loop.

- [ ] **Step 2: Run** → FAIL (`generateSummary` takes no opts; backoff not abort-aware).

- [ ] **Step 3: Implement** — widen the leaf calls `model.generateContent(prompt, { timeout: REQUEST_TIMEOUT_MS, signal: opts?.signal })`; thread `opts` through `generateSummary → attempt() → generateJson`; in `generateJson`'s loop, `if (opts?.signal?.aborted) throw new DOMException('aborted','AbortError');` before each attempt and make the backoff sleep abort-aware:

```ts
await new Promise<void>((res, rej) => {
  if (opts?.signal?.aborted) return rej(new DOMException('aborted', 'AbortError'));
  const t = setTimeout(res, baseDelayMs * 2 ** attempt);
  opts?.signal?.addEventListener('abort', () => { clearTimeout(t); rej(new DOMException('aborted', 'AbortError')); }, { once: true });
});
```
In `resolveTranscriptSegments`, add `signal?`, forward to `transcribeViaGemini`, and throw `PermanentTranscriptError` **only** when both the caption fetch returned empty AND the Gemini fallback returned zero segments (deterministic no-source); wrap any other fallback failure in the existing retryable `Error`.

- [ ] **Step 4: Run** — `npx jest gemini-signal transcript-source` → PASS.

- [ ] **Step 5: Local regression** — `npx jest gemini transcript-source pipeline` → PASS (optional param, no behavior change for existing callers). Then `npx tsc --noEmit`.

- [ ] **Step 6: Commit** — `git commit -am "feat(gemini): thread AbortSignal + abort-aware backoff; typed transcript error"`

---

### Task 6: `summaryCore` extraction + local re-wire

**Files:**
- Create: `lib/ingestion/summary-core.ts`
- Modify: `lib/pipeline.ts` (`writeSummaryDoc` delegates to `summaryCore`)
- Create: `tests/lib/summary-core.test.ts`; keep `tests/lib/pipeline-write-summary.test.ts` green (golden).

**Interfaces:**
- Produces: `summaryCore(input: { videoId; title; youtubeUrl; channel?; durationSeconds; baseName; language? }, deps: { resolveTranscriptSegments; generateSummary; extractQuickView }, opts?: { signal?: AbortSignal }): Promise<{ frontmatter: string; markdown: string; mdContent: string; quickView: { tldr: string; takeaways: string[] } | null; geminiFields: { language: 'en'|'ko'; ratings; overallScore; videoType?; audience?; tags?; tldr?; takeaways? } }>` — pure of storage (no `put`, `fs`, principal).

- [ ] **Step 1: Write the failing test** — `tests/lib/summary-core.test.ts` with mocked deps; assert the returned `mdContent`/`geminiFields` match the fields `writeSummaryDoc` produces today for the same input.

- [ ] **Step 2: Run** → FAIL (module absent).

- [ ] **Step 3: Implement** — move the transcript→Gemini→build-markdown→quick-view logic (everything in `writeSummaryDoc` **except** the `blobStore.put(localPrincipal(...))` at L105) into `summaryCore`, returning `mdContent` + `geminiFields`. Re-point `writeSummaryDoc` to call `summaryCore` then do its existing `blobStore.put(localPrincipal(outputFolder), \`${baseName}.md\`, …)` — behavior preserved.

- [ ] **Step 4: Run** — `npx jest summary-core pipeline-write-summary` → PASS (the existing golden proves byte-identical local output).

- [ ] **Step 5: Local regression** — `npx jest pipeline && npx tsc --noEmit` → green.

- [ ] **Step 6: Commit** — `git commit -am "refactor(ingestion): extract store-agnostic summaryCore; local re-wired"`

---

### Task 7: `summaryHandler` — idempotent, self-healing

**Files:**
- Create: `lib/job-queue/handler-context.ts` (shared types — defined here because both this task and Task 8 import them)
- Create: `lib/job-queue/progress-phase.ts` (`ProgressPhase` type + values)
- Create: `lib/job-queue/errors.ts` (`NonRetryableError`)
- Create: `lib/job-queue/summary-handler.ts`
- Create: `lib/job-queue/ingestion-payload.ts` (`IngestionPayload` + zod validator)
- Create: `tests/integration/summary-handler.test.ts`

**Interfaces:**
- Consumes: Tasks 4 (`getWorkerStorageBundle`, `reserveVideoSlot`, `persistSummary`), 5 (`resolveTranscriptSegments` signal), 6 (`summaryCore`), the `LeasedJob` shape, `CURRENT_DOC_VERSION`.
- Produces (shared, consumed by Task 8): `ProgressPhase = 'transcribing' | 'summarizing' | 'writing'`; `HandlerCtx = { isCancelled(): Promise<boolean>; signal: AbortSignal; setPhase(p: ProgressPhase): Promise<void> }`; `JobHandler = (job: LeasedJob, ctx: HandlerCtx) => Promise<unknown>` (the upgraded handler signature, replacing the 1E-a `JobHandler`); `NonRetryableError extends Error`.
- Produces (this task): `makeSummaryHandler(serviceClient: SupabaseClient): JobHandler`; `IngestionPayload` (§6 of the spec).
- **Testing note:** the handler is tested by calling it directly with a hand-built `HandlerCtx` mock (`{ isCancelled: async () => false, signal: new AbortController().signal, setPhase: async () => {} }`) — it does NOT need `runOnce` (Task 8), so this task stands alone.

- [ ] **Step 1: Write the failing test** — `tests/integration/summary-handler.test.ts` (Gemini mocked, real Supabase): (a) happy path → row persisted with `serialNumber`, `playlistIndex`, `summaryMd`, `ratings`, and `artifacts.summaryMd.status === 'promoted'`; blob present. (b) **idempotent re-run** of the same job → Gemini mock called **once total**, same `serialNumber`, no orphan blob. (c) malformed payload → `NonRetryableError`. (d) over-long video (`durationSeconds` past cutoff) → `NonRetryableError`.

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement** — the handler:
  1. validate payload (`IngestionPayload` zod) → `NonRetryableError` on failure; reject `durationSeconds > MAX_DURATION_SECONDS` (`export const MAX_DURATION_SECONDS = 4 * 3600`).
  2. `bundle = await getWorkerStorageBundle(serviceClient, job.ownerId, job.playlistId)`.
  3. **idempotency skip:** read the video row; if `artifacts.summaryMd.status === 'promoted'` and `docVersion` matches `job.version`, return early.
  4. `serial = await reserveVideoSlot(serviceClient, job.ownerId, job.playlistId, job.videoId)`; `baseName = \`${String(serial).padStart(3,'0')}_${slug(title)}\``.
  5. `await ctx.setPhase('transcribing')` … `core = await summaryCore({ …payload, baseName }, deps, { signal: ctx.signal })` with `setPhase('summarizing')` around Gemini and `setPhase('writing')` before the write.
  6. build the full `Video` = `core.geminiFields` + `{ id, title, youtubeUrl, durationSeconds, channel, serialNumber: serial, summaryMd: \`${baseName}.md\`, playlistIndex: payload.playlistIndex, videoPublishedAt, addedToPlaylistAt, docVersion: CURRENT_DOC_VERSION, archived: false, processedAt: new Date().toISOString() }`.
  7. `putStaged(principal, \`${baseName}.md\`, bytes) → verify exists → persistSummary(…, video, 'committed') → promote → persistSummary(…, video, 'promoted')`.

- [ ] **Step 4: Run** — `npm run test:integration -- summary-handler` → PASS.

- [ ] **Step 5: Full guard** — `npm run test:integration && npx tsc --noEmit` → green.

- [ ] **Step 6: Commit** — `git commit -am "feat(worker): idempotent, self-healing summary handler"`

---

### Task 8: `runOnce` upgrade — heartbeat, composed signal, teardown

**Files:**
- Modify: `lib/job-queue/worker-runner.ts`
- Create: `tests/integration/worker-runner-runtime.test.ts`

**Interfaces:**
- Consumes (from Task 7): `HandlerCtx`, `ProgressPhase`, `JobHandler` (from `handler-context.ts`/`progress-phase.ts`), `NonRetryableError` (from `errors.ts`). `worker-runner.ts` replaces its local `JobHandler` with the imported one.
- Produces: `runOnce(queue, handler, opts)` — signature adds `opts.shutdownSignal?: AbortSignal`; the `ctx` it constructs and passes to the handler is a `HandlerCtx` (`{ isCancelled; signal; setPhase }`); a 30s heartbeat loop; composed `AbortSignal` (`AbortSignal.any([wallClock, leaseLost, opts.shutdownSignal].filter(Boolean))`); `finally` clears the interval; a `settled` flag guards the single terminal call; retryability keyed on `NonRetryableError` (`instanceof` → `fail(retryable:false)`).
- **Testing note:** tested with a trivial inline handler (e.g. one that throws `NonRetryableError`, or sleeps past a heartbeat) — not the real summary handler.

- [ ] **Step 1: Write the failing test** — assert: (a) a handler that runs > one heartbeat interval keeps its lease (heartbeat fired); (b) the interval is cleared on throw (no heartbeat after settle — spy count stops); (c) a `NonRetryableError` → `fail(retryable:false)` → status `failed`; (d) `progress_phase` written to the row.

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement** — add the heartbeat `setInterval(() => queue.heartbeat(...), 30_000)` (on `ok:false`, abort the lease-lost controller); build `signal = AbortSignal.any([...])`; pass `ctx = { isCancelled, signal, setPhase }` where `setPhase` does a lease-fenced `update jobs set progress_phase=$ where id=$ and lease_token=$`; wrap the whole body in `try/finally` (clear interval); track `let settled = false;` so only one of `complete`/`fail` runs; map `NonRetryableError → fail(retryable:false)`.

- [ ] **Step 4: Run** — `npm run test:integration -- worker-runner-runtime` → PASS.
- [ ] **Step 5: Full guard** — `npm run test:integration && npx jest worker && npx tsc --noEmit` → green.
- [ ] **Step 6: Commit** — `git commit -am "feat(worker): runOnce heartbeat loop + composed signal + teardown + retryability"`

---

### Task 9: `worker/main.ts` entrypoint

**Files:**
- Create: `worker/main.ts`
- Modify: `package.json` (add `"worker": "ts-node worker/main.ts"`)
- Create: `tests/integration/worker-main.test.ts` (import the loop function, not the process bootstrap)

**Interfaces:**
- Produces: `runWorkerLoop(deps: { queue; handler; shutdownSignal: AbortSignal; workerId: string }): Promise<void>` (exported for tests); `main()` (bootstrap: env fail-fast, build service client + handler, wire SIGTERM → `AbortController`, call `runWorkerLoop`).

- [ ] **Step 1: Write the failing test** — seed one job; run `runWorkerLoop` with a shutdown signal aborted after the first `runOnce`; assert the job reaches `completed`.

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement** — `runWorkerLoop`: loop `while (!shutdownSignal.aborted) { const r = await runOnce(queue, handler, { workerId, shutdownSignal }); if (r === 'idle') await sleep(POLL_MS, shutdownSignal); }`. `main()`: `validateStorageEnv()` + assert `GEMINI_API_KEY`/`YOUTUBE_API_KEY`/`SUPABASE_SERVICE_ROLE_KEY`; build a service-role client; `handler = makeSummaryHandler(client)`; `process.on('SIGTERM', () => ac.abort())`.

- [ ] **Step 4: Run** — `npm run test:integration -- worker-main` → PASS.
- [ ] **Step 5: Full guard** — `npm run test:integration && npx tsc --noEmit` → green.
- [ ] **Step 6: Commit** — `git commit -am "feat(worker): worker/main.ts entrypoint + loop + SIGTERM shutdown"`

---

### Task 10: Confinement → `worker/` + flaky-test cleanup

**Files:**
- Modify: `scripts/check-service-confinement.ts` (`collectEntrypoints`)
- Modify: `tests/integration/job-queue-worker.test.ts` (harden the `run_after`-reset backoff test)

**Interfaces:** Consumes the confinement scanner; no new production interface.

- [ ] **Step 1: Write the failing test / reproduce** — confirm `npm run check:confinement` currently does NOT scan `worker/`; add a fixture assertion (or run the scanner and confirm `worker/main.ts`'s `service.ts` import is now traced as the sole allowed service_role consumer).

- [ ] **Step 2: Implement** — extend `collectEntrypoints()` to include `worker/**`. For the flaky test: replace the client-clock `run_after` reset with an admin update that sets `run_after = now()` in the DB (avoid client/DB clock skew), or assert on job id rather than re-claim timing.

- [ ] **Step 3: Run** — `npm run check:confinement` → PASS (worker is the only service_role consumer); `npm run test:integration -- job-queue-worker` 3× → stable.

- [ ] **Step 4: Full guard** — `npx jest && npm run test:integration && npm run check:confinement && npx tsc --noEmit` → all green.

- [ ] **Step 5: Commit** — `git commit -am "chore(worker): extend confinement scan to worker/; harden flaky backoff test"`

---

## Notes for the executor

- **Tasks 1 & 2 get the per-task adversarial review** (Codex + Claude) on the SQL — the idempotency, owner-scoping, merge-not-erase, and 0-row-raise properties are the load-bearing correctness of the whole slice.
- After every SQL/integration task: `npx supabase db reset` (re-applies 0008+0009), then `npm run test:integration`, then `npx tsc --noEmit` (the tsc step is mandatory — earlier SQL tasks in 1E-a shipped tsc errors because it was skipped).
- The `slug()` helper and `String(serial).padStart(3,'0')` `baseName` format must match `lib/pipeline.ts`'s existing serial-prefix convention (check `padSerial`/slug there and reuse it, do not re-invent).
- `writeSummaryDoc` stays the local path; the cloud handler never calls it (it calls `summaryCore` + `persistSummary`), avoiding the `localPrincipal`/`getStorageBundle()`-throws problems.
