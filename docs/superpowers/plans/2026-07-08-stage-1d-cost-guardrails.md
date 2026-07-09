# Stage 1D — Cost Guardrails Implementation Plan (v3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the server-side money kill-switch (atomic per-account monthly quota + a global daily spend cap with a *provable* worst-case estimate) as unbypassable preflight gates on the 1E-c producer enqueue path, before the paid Gemini path is exposed in 1H.

**Architecture:** Migration `0011` adds four guardrail tables + two `jobs` columns + a velocity index, and reworks `enqueue_job` into a `service_role`-only RPC that atomically debits monthly quota and reserves a worst-case dollar estimate (never released in 1D) inside the INSERT branch, with a duration backstop. The producer route splits into a **session bundle** (auth/reads/`resolvePlaylistId`, RLS) and a service **`Enqueuer`** (preflight + enqueue + non-secret config read, no tenant-read path). The estimate is a genuine upper bound via **cloud-scoped enforced token caps** threaded as a `CloudGeminiCaps` option through `summaryCore` to all three cloud Gemini calls (local pipeline unchanged), verified by a DB-live + code-constant **guard test**.

**Tech Stack:** Supabase Postgres (RLS, SECURITY INVOKER RPCs, `service_role` BYPASSRLS), Next.js API routes, `@google/generative-ai` 0.24.1 (Gemini 2.5 Flash), jest + ts-jest (unit) / `jest.integration.config.ts` (live PG), SWC (no type-check in jest → `npx tsc --noEmit` is a mandatory gate).

## v3 — round-2 plan-review fixes (both reviewers: no new Blocking)
Round-2 (`docs/reviews/plan-stage-1d-{codex,claude}-v2.md`) confirmed B1 genuinely closed; applied its High/Medium: `VideoMeta.liveBroadcastContent` is **`.optional()`** (required would break 4 existing typed fixtures; producer blocks only on explicit `'live'|'upcoming'`); T10 **migrates the existing `tests/lib/producer.test.ts`** (old 3-arg signature/`jobQueue` fake — a build-breaker T13's grep missed); T3 `admitted` corrected — the `max_free_users` ceiling is on **registered** users, anon always admitted (spec §5); T2/T3 **`revoke all … from public, anon, authenticated`** on the new RPCs + client tests assert `42501`; T6 **deletes `gemini.ts`'s local `MAX_SUMMARY_ATTEMPTS`** and imports it (single source); `beforeEach` also clears `jobs` + resets all config columns/4 allowance rows; T11 fake implements `getGuardrailConfig`; `ON CONFLICT` predicate matches `jobs_idem_active`.

## v2 — round-1 plan-review fixes (`docs/reviews/plan-stage-1d-{codex,claude}.md`)
Critical: T2 now drops the **actual 0009 6-arg `enqueue_job(uuid,text,int,text,text,jsonb)`** (v1 dropped a non-existent signature → the client-callable 6-arg fn would have survived, leaving the bypass OPEN) + tests the 6-arg client call is denied. Config source: `Enqueuer.getGuardrailConfig()` (T4/T5) feeds the producer's duration block (T9). Retry/pass constants: single source in `gemini-cost.ts`, imported by `gemini.ts` (T6). Test helpers corrected to the real `clients.ts` signatures + `beforeEach` singleton reset + varied velocity IP (all integration tasks). New Task 9 adds the `liveBroadcastContent` field for VOD-only. `SupabaseJobQueue.enqueue`/`JobQueue.enqueue` removed (T10). `jobs_velocity` index (T1). `failed` formula includes in-loop `tooLong` (T10). Missing §8 cases added (T2). T12 guard recomputes independently. T13 uses the real grep inventory.

## Global Constraints

- **Spec:** `docs/superpowers/specs/2026-07-08-stage-1d-cost-guardrails-design.md` (v7 CONVERGED). Every task's requirements implicitly include it.
- **SQLSTATEs:** quota=`PJ001`, daily-cap=`PJ002`, too-long=`PJ003`. **Never the `PT` class** (PostgREST HTTP-status override).
- **UTC everywhere:** `period_start = date_trunc('month', now() at time zone 'utc')::date`; day = `(now() at time zone 'utc')::date`.
- **Only `summary` is enqueuable** — reject `job_kind <> 'summary'` (`unsupported_job_kind`).
- **Never-release:** no reservation is ever decremented in 1D; `fail_job`/`sweep_expired_leases`/`request_cancel_job` unchanged.
- **`enqueue_job` runs as `service_role`** (SECURITY INVOKER). **Replace EVERY `auth.uid()` with `p_owner_id`**; the caller check becomes `auth.role() <> 'service_role'`.
- **Two-client split:** the service client lives ONLY inside the `Enqueuer` (enqueue + preflight + non-secret config, NO tenant read). `listByPlaylist`/status/cancel run on the session client. Never place the service client into a `StorageBundle.jobQueue`.
- **Cloud token caps are OPTIONS** (default off) → local pipeline unchanged. Byte truncation measures **UTF-8 bytes** (`Buffer.byteLength(...,'utf8')`), never JS `.length`.
- **Model pinned:** priced model `gemini-2.5-flash`; assert resolved `SUMMARY_MODEL`/`TRANSCRIBE_MODEL` (post-`??`) equals it at handler init + guard test.
- **Test helpers (`tests/integration/helpers/clients.ts`, verified):** `adminClient(): SupabaseClient`; `newUser(): Promise<{user:{id},email,password}>` → owner id is **`u.user.id`**; `signInAs(email,password): Promise<{client,userId}>` → **`const {client} = await signInAs(u.email,u.password)`**; `anonSession(): Promise<{client,userId}>`.
- **Two jest configs:** unit `npm test`; integration `npm run test:integration -- --runInBand` (needs local Supabase + `.env.test.local`; `npx supabase db reset` applies the whole current `0011` file). Run `npx tsc --noEmit` before every commit.
- **Commit trailers:** `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_01GRJf1wQQNmT5Q8T6SPNaej`.

## Constant defaults (spec §3)

DB `guardrail_config`: `daily_cap_cents`=500, `summary_est_cents`=`dig_est_cents`=150, `summary_max_attempts`=`dig_max_attempts`=1, `max_duration_seconds`=1800, `max_free_users`=100, `max_queue_depth`=200, `velocity_per_ip_hourly`=15, `captcha_soft_threshold`=5. Allowances `(false,'summary',20),(false,'dig',5),(true,'summary',2),(true,'dig',0)`.

**Code constants — single source of truth in `lib/gemini-cost.ts`** (`gemini.ts` imports the retry constants for its signature defaults; `gemini-cost.ts` imports nothing from `gemini.ts`, so no cycle): `MAX_TRANSCRIBE_INPUT_TOKENS`=300000, `MAX_TRANSCRIBE_OUTPUT_TOKENS`=32768, `MAX_TRANSCRIPT_INPUT_BYTES`=40960, `MAX_SUMMARY_OUTPUT_TOKENS`=8192, `TRANSCRIBE_RETRIES`=2, `GENERATE_JSON_RETRIES`=2, `MAX_SUMMARY_ATTEMPTS`=4, `TRANSCRIBE_MAX_PASSES`=`TRANSCRIBE_RETRIES`+1, `SUMMARY_MAX_PASSES`=`MAX_SUMMARY_ATTEMPTS`×(`GENERATE_JSON_RETRIES`+1), `QUICKVIEW_MAX_PASSES`=`GENERATE_JSON_RETRIES`+1, `PROMPT_SCHEMA_OVERHEAD_TOKENS`=4000, `PRICE_IN_PER_1M_CENTS`=30, `PRICE_AUDIO_IN_PER_1M_CENTS`=100, `PRICE_OUT_PER_1M_CENTS`=250, `AUDIO_TOKENS_PER_SEC`=32, `PRICED_MODEL`='gemini-2.5-flash'. (`gemini.ts` re-exports `TRANSCRIBE_RETRIES`/`GENERATE_JSON_RETRIES`? No — it *imports* them and uses them as the `retries=` default param values; the guard test imports the `*_MAX_PASSES` from `gemini-cost.ts`.)

---

## File Structure

| File | Responsibility |
|---|---|
| `supabase/migrations/0011_cost_guardrails.sql` | tables + `jobs` cols + `jobs_velocity` index + grants/RLS; REVOKE client INSERT; **DROP the 0009 6-arg `enqueue_job`**; new 8-arg `enqueue_job`; `enqueue_preflight`. |
| `lib/gemini-cost.ts` | **Create** — all cost/cap/retry/pass/price constants (single source) + `perRunWorstCents(cfg)` + `CloudGeminiCaps` type. |
| `lib/gemini.ts` | **Modify** — import `TRANSCRIBE_RETRIES`/`GENERATE_JSON_RETRIES` as signature defaults; export resolved `SUMMARY_MODEL`/`TRANSCRIBE_MODEL`; optional `caps` in `opts` for the three calls → `maxOutputTokens`+`thinkingConfig.thinkingBudget:0`; `countTokens` preflight in `transcribeViaGemini`; `CLOUD_TRANSCRIBE_FALLBACK` fail-closed flag. |
| `lib/transcript-timestamps.ts` | **Modify** — `truncateSegmentsToByteCap(segments, maxBytes)`. |
| `lib/transcript-source.ts` | **Modify** — `resolveTranscriptSegments` opts gains `caps`. |
| `lib/ingestion/summary-core.ts` | **Modify** — `opts.caps?`; truncate; forward caps to the 3 deps. |
| `lib/job-queue/summary-handler.ts` | **Modify** — build `CloudGeminiCaps`; read `guardrail_config.max_duration_seconds`; assert model==`PRICED_MODEL`; set fallback flag fail-closed. |
| `lib/job-queue/enqueuer.ts` | **Create** — `Enqueuer` interface (`enqueue`,`preflight`,`getGuardrailConfig`) + `SupabaseEnqueuer`. |
| `lib/job-queue/errors.ts` | **Modify** — `QuotaExceededError`/`DailyCapError`/`VideoTooLongError` + `mapEnqueueError`. |
| `types/index.ts`, `lib/youtube.ts`, `lib/job-queue/video-meta-to-payload.ts` | **Modify** — `VideoMeta.liveBroadcastContent` from `snippet.liveBroadcastContent` (VOD-only). |
| `lib/job-queue/producer.ts` | **Modify** — new signature + buckets + VOD/too_long block + corrected `failed`. |
| `lib/storage/supabase/supabase-job-queue.ts`, `lib/storage/job-queue.ts` | **Modify** — remove `enqueue` (dropped RPC; producer uses `Enqueuer`). |
| `app/api/jobs/route.ts` | **Modify** — POST two-client wiring + preflight→HTTP. |
| tests | `tests/integration/{cost-guardrails,cap-soundness,gemini-live-gates}.test.ts` (create), `tests/lib/{gemini-caps,transcript-bytecap,producer-guardrails}.test.ts` (create), `tests/api/jobs-route-guardrails.test.ts` (create); modify `schema.test.ts` + the enqueue-calling integration files (T13). |

---

### Task 1: Migration 0011 — tables, columns, velocity index, grants

**Files:** Create `supabase/migrations/0011_cost_guardrails.sql`; Modify `tests/integration/schema.test.ts`; Test `tests/integration/cost-guardrails.test.ts`.

**Interfaces produced:** the four tables (spec §3), `jobs.reserved_cents int`, `jobs.enqueue_ip inet`, `create index jobs_velocity on jobs (enqueue_ip, created_at);`.

- [ ] **Step 1: Write failing tests** (`cost-guardrails.test.ts`) with a `beforeEach` reset and the **correct helper signatures**:

```ts
import { adminClient, newUser, signInAs } from './helpers/clients';
const svc = adminClient();
beforeEach(async () => {
  await svc.from('jobs').delete().neq('id', '00000000-0000-0000-0000-000000000000');   // clear accumulated jobs (velocity/queue-depth counts) — round-2 L1
  await svc.from('spend_ledger').delete().neq('day', '1900-01-01');           // clear all ledger days
  await svc.from('usage_counters').delete().neq('owner_id', '00000000-0000-0000-0000-000000000000');
  await svc.from('guardrail_config').update({ daily_cap_cents: 500, summary_est_cents: 150, dig_est_cents: 150,   // reset EVERY column — round-2 L
    summary_max_attempts: 1, dig_max_attempts: 1, max_duration_seconds: 1800, velocity_per_ip_hourly: 15,
    max_queue_depth: 200, max_free_users: 100, captcha_soft_threshold: 5 }).eq('id', true);
  await svc.from('quota_allowance').update({ monthly: 20 }).match({ is_anonymous: false, kind: 'summary' });
  await svc.from('quota_allowance').update({ monthly: 5 }).match({ is_anonymous: false, kind: 'dig' });     // all 4 allowance rows
  await svc.from('quota_allowance').update({ monthly: 0 }).match({ is_anonymous: true, kind: 'dig' });
  await svc.from('quota_allowance').update({ monthly: 2 }).match({ is_anonymous: true, kind: 'summary' });
});

it('seeds quota_allowance and the singleton guardrail_config', async () => {
  const { data: allow } = await svc.from('quota_allowance').select('*');
  expect(allow).toEqual(expect.arrayContaining([{ is_anonymous: false, kind: 'summary', monthly: 20 }]));
  const { data: cfg } = await svc.from('guardrail_config').select('*').single();
  expect(cfg).toMatchObject({ daily_cap_cents: 500, summary_est_cents: 150, summary_max_attempts: 1, max_duration_seconds: 1800 });
});
it('lets an owner read only their own usage_counters and denies spend_ledger/guardrail_config reads', async () => {
  const a = await newUser(); const b = await newUser();
  await svc.from('usage_counters').insert([
    { owner_id: a.user.id, kind: 'summary', period_start: '2026-07-01', used: 1 },
    { owner_id: b.user.id, kind: 'summary', period_start: '2026-07-01', used: 1 }]);
  const { client: sa } = await signInAs(a.email, a.password);
  const { data: mine } = await sa.from('usage_counters').select('owner_id');
  expect(mine).toEqual([{ owner_id: a.user.id }]);
  const led = await sa.from('spend_ledger').select('*');   // no client grant → error, not []
  expect(led.error).toBeTruthy();
  const g = await sa.from('guardrail_config').select('*');
  expect(g.error).toBeTruthy();
});
it('rejects client writes to guardrail_config and usage_counters', async () => {
  const a = await newUser(); const { client: sa } = await signInAs(a.email, a.password);
  expect((await sa.from('guardrail_config').update({ daily_cap_cents: 999999 }).eq('id', true)).error).toBeTruthy();
  expect((await sa.from('usage_counters').insert({ owner_id: a.user.id, kind: 'summary', period_start: '2026-07-01', used: 999 })).error).toBeTruthy();
});
```

- [ ] **Step 2: Run — FAIL** (relations do not exist). `npm run test:integration -- --runInBand cost-guardrails`.
- [ ] **Step 3: Write the migration** — the four `create table` blocks + grants/policies + the two `alter table jobs add column` lines **verbatim from spec §3 (lines 76–116)**, plus `create index jobs_velocity on jobs (enqueue_ip, created_at);` (covers the preflight velocity count — Claude M3).
- [ ] **Step 4: Update `schema.test.ts`** — (a) add `usage_counters`/`spend_ledger`/`quota_allowance`/`guardrail_config` to the "RLS enabled AND forced" assertion; (b) **update its exact `pg_policies` assertion** to include the new `usage_counters_owner_read` (cmd SELECT) and `quota_allowance_read` (cmd SELECT, `using true`) policies, or scope the "one owner ALL policy per table" assertion to the owner-owned data tables only (Codex H2).
- [ ] **Step 5: Apply + run.** `npx supabase db reset && npm run test:integration -- --runInBand cost-guardrails schema` → PASS. `npx tsc --noEmit`.
- [ ] **Step 6: Commit** (`feat(1d): migration 0011 tables + jobs cols + velocity index`).

---

### Task 2: `enqueue_job` rework — drop the 0009 6-arg fn, new 8-arg service-role RPC

**Files:** Modify `supabase/migrations/0011_cost_guardrails.sql`; Test `tests/integration/cost-guardrails.test.ts`.

**Interfaces produced:** `enqueue_job(p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_section_id int, p_job_kind text, p_job_version text, p_payload jsonb, p_enqueue_ip inet) returns table(job_id uuid, status text, joined boolean)`; raises `PJ001/PJ002/PJ003`; sets `jobs.max_attempts` per kind.

- [ ] **Step 1: Write failing tests** (append; reuse the `beforeEach`). Helper `seedPlaylist` + `enq` use **`svc` (service_role)** and correct helper sigs:

```ts
import { randomUUID } from 'crypto';
async function seedPlaylist(ownerId: string) {
  const { data } = await svc.from('playlists').insert({ owner_id: ownerId, playlist_key: `k-${randomUUID()}`, playlist_url: `https://x/${randomUUID()}` }).select('id').single();
  return data!.id as string;
}
const payload = (d: unknown) => ({ youtubeUrl: 'https://y', title: 't', durationSeconds: d, playlistIndex: 1 });
async function enq(ownerId: string, pl: string, vid: string, p: unknown, kind = 'summary', ip = '1.2.3.4') {
  return svc.rpc('enqueue_job', { p_owner_id: ownerId, p_playlist_id: pl, p_video_id: vid, p_section_id: -1, p_job_kind: kind, p_job_version: '1.0', p_payload: p, p_enqueue_ip: ip });
}
```

Cases (each §8 row): **quota debit + PJ001** (set `quota_allowance.monthly=2`, third enq → `error.code==='PJ001'`); **JOIN does not re-debit** (`used===1` after enq+enq of same key); **UTC-month rollover** (seed a `usage_counters` row for last month `used=99`, current-month enq still succeeds and creates a fresh row `used=1`); **same-owner parallel distinct-video quota race** (`monthly=3`, `Promise.all` of 5 distinct-video enqs → exactly 3 succeed, 2 `PJ001`); **anon vs registered allowance** (an `anonSession()`-provisioned owner gets `is_anonymous=true` → allowance 2; a `newUser()` owner → 20); **`jobs.max_attempts===1`**; **daily cap + PJ002 + quota unchanged** (`daily_cap_cents=150`; second enq `PJ002`; `used===1`); **duration PJ003** for `1801`, `1800.999999`, `null`, `{}` (missing), **and a live-job JOIN with a drifted over-cap payload returns `joined:true`**; **sweep at max_attempts=1 → dead_letter** (claim, expire lease, `sweep_expired_leases`, assert `dead_letter`); **fail_job retryable → dead_letter, no ledger change** (never-release); **dig reject** (`kind='dig'` → `unsupported_job_kind`); **owner-safety FK** (`p_owner_id` not owning `p_playlist_id` → error); **bypass closure — BOTH signatures:** a client session `rpc('enqueue_job', {…8 args…})` **and** `rpc('enqueue_job', {p_playlist_id, p_video_id, p_section_id, p_job_kind, p_job_version, p_payload})` (the old **6-arg** shape) are **denied/absent** (Claude B1), and `sa.from('jobs').insert(...)` is denied.

- [ ] **Step 2: Run — FAIL.**
- [ ] **Step 3: Append to `0011`:** (a) **`drop function if exists enqueue_job(uuid,text,int,text,text,jsonb);`** — the live 0009 6-arg signature (removes its `anon/authenticated` grants; **do NOT** write the 0008 `(text,int,text,text,jsonb)` — that no longer exists). (b) `revoke insert on public.jobs from anon, authenticated;` (keep select). (c) `create function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) ...` per spec §4 body (lines 146–178): `declare v_id uuid; v_status text; v_payload jsonb; v_cfg guardrail_config; v_est int; v_maxatt int; v_dur text; v_anon boolean; v_allow int; v_period date; v_day date; v_tries int := 0;` — preserve the insert-or-join loop; **`ON CONFLICT (owner_id, playlist_id, video_id, section_id, job_kind, job_version) WHERE status in ('queued','active','completed') DO NOTHING`** (Codex M1); the JOIN-branch SELECT keys on all six of those columns with `owner_id = p_owner_id`; **every `auth.uid()` → `p_owner_id`**; INSERT sets `playlist_id=p_playlist_id, enqueue_ip=p_enqueue_ip, max_attempts=v_maxatt`; steps 0/2/3/4/5 exactly as spec §4. **The `ON CONFLICT ... WHERE status in (...)` predicate must match the `jobs_idem_active` partial-index predicate** (0008) — copy the 0009 aliased form so it binds (round-2 L3). (d) **`revoke all on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) from public, anon, authenticated;`** then `grant execute ... to service_role;` (repo precedent 0009:45/0010:21 — round-2 Codex H). The bypass tests assert the client calls fail with a **permission/absence** error (code `42501` or "does not exist"), not merely "any error".
- [ ] **Step 4: Apply + run.** `npx supabase db reset && npm run test:integration -- --runInBand cost-guardrails` → PASS. `npx tsc --noEmit`.
- [ ] **Step 5: Commit** (`feat(1d): enqueue_job rework (drop 0009 6-arg; 8-arg service-role; PJ001/2/3)`).

---

### Task 3: `enqueue_preflight`

**Files:** Modify `0011`; Test `cost-guardrails.test.ts`.
**Interfaces produced:** `enqueue_preflight(p_ip inet, p_owner_id uuid) returns table(admitted boolean, at_capacity boolean, velocity_exceeded boolean, challenge_required boolean)`; execute → `service_role` only.

- [ ] **Step 1: Failing tests** (reuse `beforeEach`): set `velocity_per_ip_hourly=2`; enqueue 3 from `ip='9.9.9.9'`; `enqueue_preflight('9.9.9.9', ownerId)` → `velocity_exceeded:true`, row has exactly keys `admitted/at_capacity/velocity_exceeded/challenge_required`. A **different** IP with 0 recent jobs → `velocity_exceeded:false`. **admitted ranking (round-2 H3):** a registered owner within the first `max_free_users` → `admitted:true`; set `max_free_users=0` and assert a registered owner → `admitted:false` while an `anonSession()` owner → `admitted:true` (anon is not ceiling-capped). A client-session `rpc('enqueue_preflight',...)` → `error` with code `42501` (execute revoked).
- [ ] **Step 2: Run — FAIL.**
- [ ] **Step 3: Implement** per spec §5: `security invoker`, guard `auth.role()='service_role'`, read `guardrail_config`; `velocity_exceeded = (select count(*) from jobs where enqueue_ip=p_ip and created_at > now()-interval '1 hour') >= velocity_per_ip_hourly` (uses `jobs_velocity`); `at_capacity = today reserved+actual >= daily_cap_cents OR (count queued+active) >= max_queue_depth`; **`admitted = is_anonymous(p_owner_id) OR (registered rank by profiles.created_at <= max_free_users)`** — the `max_free_users` ceiling is on **registered** users (spec §5 / parent "free sign-in ceiling N=100"); anon is always admitted (velocity-limited) (round-2 H3); `challenge_required = is_anonymous AND per-IP hour count > captcha_soft_threshold`. Booleans only. **`revoke all on function enqueue_preflight(inet,uuid) from public, anon, authenticated; grant execute ... to service_role;`**
- [ ] **Step 4: Apply + run → PASS.** `npx tsc --noEmit`.
- [ ] **Step 5: Commit** (`feat(1d): enqueue_preflight advisory gate + jobs_velocity use`).

---

### Task 4: TS errors + `Enqueuer` interface (incl. `getGuardrailConfig`) + producer types

**Files:** Modify `lib/job-queue/errors.ts`; Create `lib/job-queue/enqueuer.ts` (types); Test `tests/lib/enqueuer-errors.test.ts`.

**Interfaces produced:** `class QuotaExceededError/DailyCapError/VideoTooLongError extends Error`; `function mapEnqueueError(pgError: { code?: string } | null | undefined): unknown` (PJ001→Quota, PJ002→DailyCap, PJ003→VideoTooLong instances; anything else → returned unchanged — typed `unknown` since a Supabase error object need not be an `Error`, Codex M5); `interface EnqueueCtx { ownerId: string; enqueueIp: string | null }`; `interface PreflightVerdict { admitted; atCapacity; velocityExceeded; challengeRequired: boolean }`; `interface GuardrailConfigView { maxDurationSeconds: number }`; `interface Enqueuer { enqueue(ctx: EnqueueCtx, key: JobKey, payload: IngestionPayload): Promise<EnqueueResult>; preflight(ip: string | null, ownerId: string): Promise<PreflightVerdict>; getGuardrailConfig(): Promise<GuardrailConfigView>; }` (NO read/list method).

- [ ] **Step 1: Failing test** — `mapEnqueueError({code:'PJ001'}) instanceof QuotaExceededError`; PJ002/PJ003 likewise; `mapEnqueueError({code:'23505'})` returns the same object (`===`).
- [ ] **Step 2: FAIL.** **Step 3: Implement** errors + `mapEnqueueError` + the interfaces.
- [ ] **Step 4: PASS + `npx tsc --noEmit`. Step 5: Commit** (`feat(1d): enqueue errors + Enqueuer interface`).

---

### Task 5: `SupabaseEnqueuer`

**Files:** Modify `lib/job-queue/enqueuer.ts`; Test `cost-guardrails.test.ts` (Enqueuer slice).
**Interfaces produced:** `class SupabaseEnqueuer implements Enqueuer` (ctor `(serviceClient)`). `enqueue` → `rpc('enqueue_job', { p_owner_id: ctx.ownerId, p_playlist_id: key.playlistId, p_video_id: key.videoId, p_section_id: key.sectionId, p_job_kind: key.kind, p_job_version: key.version, p_payload: payload, p_enqueue_ip: ctx.enqueueIp })`; on `error` `throw mapEnqueueError(error)`; else map row → `EnqueueResult`. `preflight` → `rpc('enqueue_preflight', { p_ip: ip, p_owner_id: ownerId })`, snake→camel. `getGuardrailConfig` → `from('guardrail_config').select('max_duration_seconds').single()` → `{ maxDurationSeconds }`.

- [ ] **Step 1: Failing test** (build `new SupabaseEnqueuer(adminClient())`): valid enqueue → `{joined:false}`; past `monthly=1` → throws `QuotaExceededError`; `preflight` → a `PreflightVerdict`; `getGuardrailConfig()` → `{maxDurationSeconds:1800}`. (Exact `p_*` arg names — Codex H1.)
- [ ] **Step 2: FAIL. Step 3: Implement. Step 4: apply + PASS + `npx tsc --noEmit`. Step 5: Commit** (`feat(1d): SupabaseEnqueuer (enqueue/preflight/getGuardrailConfig)`).

---

### Task 6: `lib/gemini-cost.ts` (single-source constants + `perRunWorstCents`); wire into `gemini.ts`

**Files:** Create `lib/gemini-cost.ts`; Modify `lib/gemini.ts`; Test `tests/lib/gemini-caps.test.ts` (constants slice).

**Interfaces produced:** `gemini-cost.ts` exports every code constant above + `interface CloudGeminiCaps { transcribeInputTokens; transcribeOutputTokens; transcriptInputBytes; summaryOutputTokens: number }` + `function perRunWorstCents(cfg: { maxDurationSeconds: number }): number` (spec §3: `audio = AUDIO_TOKENS_PER_SEC*cfg.maxDurationSeconds`; `video = Math.max(0, MAX_TRANSCRIBE_INPUT_TOKENS - audio)` [Claude L2]; transcribe/pass = audio@100 + video@30 + OVERHEAD@30 in, + MAX_TRANSCRIBE_OUTPUT@250 out; ×`TRANSCRIBE_MAX_PASSES`; summary = `SUMMARY_MAX_PASSES` × ((`MAX_TRANSCRIPT_INPUT_BYTES`+OVERHEAD)@30 + `MAX_SUMMARY_OUTPUT_TOKENS`@250); quickview = `QUICKVIEW_MAX_PASSES` × same; return `Math.ceil(totalCents)`). `gemini.ts` exports resolved `SUMMARY_MODEL`/`TRANSCRIBE_MODEL`; its `transcribeViaGemini`/`generateJson` use `retries = TRANSCRIBE_RETRIES` / `= GENERATE_JSON_RETRIES` imported from `gemini-cost.ts` (single source — Codex B3).

- [ ] **Step 1: Failing test** — `perRunWorstCents({maxDurationSeconds:1800})` in `[110,130]`; `SUMMARY_MAX_PASSES===12`; `TRANSCRIBE_MAX_PASSES===3`; `import { SUMMARY_MODEL } from '@/lib/gemini'` === `'gemini-2.5-flash'` (env unset).
- [ ] **Step 2: FAIL. Step 3: Implement** `gemini-cost.ts`; refactor `gemini.ts` to import `TRANSCRIBE_RETRIES`/`GENERATE_JSON_RETRIES`/`MAX_SUMMARY_ATTEMPTS` from `gemini-cost.ts` (**delete the local `const MAX_SUMMARY_ATTEMPTS = 4` at gemini.ts:201** and use the imported one in the summary loop + log — round-2 M1/H2; single source, else the guard's `SUMMARY_MAX_PASSES` couples to a stale duplicate) + export the resolved models. `gemini-cost.ts` imports nothing from `gemini.ts` (no cycle).
- [ ] **Step 4: PASS + `npx tsc --noEmit`. Step 5: Commit** (`feat(1d): gemini-cost constants + perRunWorstCents`).

---

### Task 7: Enforce caps in `gemini.ts` (maxOutputTokens, thinkingBudget:0, countTokens preflight, fail-closed flag)

**Files:** Modify `lib/gemini.ts`; Test `tests/lib/gemini-caps.test.ts`; update `tests/lib/gemini.test.ts`, `tests/lib/gemini-signal.test.ts` (existing exact-call assertions — Codex M3).

**Interfaces produced:** optional `caps?: CloudGeminiCaps` **inside the existing `opts` object** of `transcribeViaGemini`/`generateSummary` and as a **2nd positional** for `extractQuickView(summaryMarkdown, caps?)` (Claude M4). When `caps` present: `generationConfig.maxOutputTokens` + `generationConfig.thinkingConfig={thinkingBudget:0}`. `transcribeViaGemini` runs a `countTokens` preflight (same LOW-res `generationConfig`) → `NonRetryableError` if `totalTokens > caps.transcribeInputTokens`. Export `const CLOUD_TRANSCRIBE_FALLBACK_VERIFIED = false` (fail-closed default — Codex B1/Claude L1): when false and `caps` present, `transcribeViaGemini` throws `NonRetryableError` (fallback disabled) rather than billing; T12 flips it after live verification.

- [ ] **Step 1: Failing tests** (mock `GoogleGenerativeAI`): each of the three calls with `caps` in the request carries `maxOutputTokens` + `thinkingConfig.thinkingBudget:0`; `transcribeViaGemini` calls `countTokens` with the same LOW-res config and throws `NonRetryableError` at `totalTokens = cap+1`; with `CLOUD_TRANSCRIBE_FALLBACK_VERIFIED=false` + `caps`, transcribe throws `NonRetryableError` before any `generateContent`; **no `caps` ⇒ none of these appear** (local path). Update the existing exact-call assertions in `gemini.test.ts`/`gemini-signal.test.ts` to the new opts shape.
- [ ] **Step 2: FAIL. Step 3: Implement. Step 4: PASS (`npm test gemini`) + `npx tsc --noEmit`. Step 5: Commit** (`feat(1d): cloud gemini caps + countTokens preflight + fail-closed flag`).

---

### Task 8: Byte truncation + `summaryCore`/`transcript-source` threading + `summary-handler` wiring

**Files:** Modify `lib/transcript-timestamps.ts`, `lib/transcript-source.ts`, `lib/ingestion/summary-core.ts`, `lib/job-queue/summary-handler.ts`; Test `tests/lib/transcript-bytecap.test.ts`; update `tests/lib/summary-core.test.ts`, `tests/lib/transcript-source.test.ts` (exact-call assertions — Codex M3); add a handler config-read integration test (Codex M4).

**Interfaces produced:** `truncateSegmentsToByteCap(segments, maxBytes): TranscriptSegment[]` (drop whole trailing segments until `Buffer.byteLength(buildIndexedTranscript(kept),'utf8') ≤ maxBytes`); `summaryCore` `opts.caps?: CloudGeminiCaps` forwarded to all three deps (caps in `opts` for `resolveTranscriptSegments`/`generateSummary`, 2nd positional for `extractQuickView`); truncation applied to the segment list used for **both** the prompt and `resolveTranscriptTokens`. `summary-handler` builds `CloudGeminiCaps` from `gemini-cost` constants, passes it, reads `guardrail_config.max_duration_seconds` (via a service client or the worker's existing client) for its duration guard, and asserts `SUMMARY_MODEL===PRICED_MODEL` at init.

- [ ] **Step 1: Failing tests** — `truncateSegmentsToByteCap` on a **CJK/emoji** set whose rendered `buildIndexedTranscript` UTF-8 byte length exceeds the cap drops whole trailing segments until `Buffer.byteLength(...,'utf8') ≤ cap` (assert with `Buffer.byteLength`, not `.length`); a ≤cap set returned unchanged; the returned list is fed to `resolveTranscriptTokens` (so `[[TS:n]]` in-range). `summaryCore` with `caps` truncates + forwards to all three deps (spy exact call shapes); no `caps` ⇒ no truncation. Handler integration test: set `guardrail_config.max_duration_seconds` low, assert the handler rejects an over-value payload (and accepts under).
- [ ] **Step 2: FAIL. Step 3: Implement. Step 4: PASS (`npm test transcript-bytecap summary-core` + the handler integration test) + `npx tsc --noEmit`. Step 5: Commit** (`feat(1d): byte-cap truncation + caps threading + handler wiring`).

---

### Task 9: `VideoMeta.liveBroadcastContent` (VOD-only data source)

**Files:** Modify `types/index.ts` (`VideoMetaSchema` gains **`liveBroadcastContent: z.string().optional()`** — YouTube `videos.list` `snippet.liveBroadcastContent` returns `'none'|'live'|'upcoming'`), `lib/youtube.ts` (`fetchPlaylistVideos` — which builds `VideoMeta` from `videos.list` — maps `snippet.liveBroadcastContent`); Test `tests/lib/youtube.test.ts`.

**Why optional (round-2 H1):** `VideoMeta = z.infer<>` uses the zod *output* type; a required field (`z.string()` or even `.default()`) forces every existing typed `: VideoMeta` literal to include it → `npx tsc --noEmit` breaks in `producer-roundtrip.test.ts:11`, `pipeline.test.ts:41`, `video-meta-to-payload.test.ts:4`, `producer.test.ts:13` (none in this task's scope). `.optional()` keeps those compiling. **T10's producer must therefore block ONLY on an explicit `'live'|'upcoming'`** (absent/`'none'` → not blocked) — safe, since production always sets it and only test fixtures omit it.

- [ ] **Step 1: Failing test** — `fetchPlaylistVideos` fixture with `snippet.liveBroadcastContent:'live'` surfaces `liveBroadcastContent:'live'`; a normal video → `'none'`.
- [ ] **Step 2: FAIL. Step 3: Implement** the optional schema field + youtube mapping. **Step 4: PASS + `npx tsc --noEmit` (confirm the four existing VideoMeta fixtures still compile untouched). Step 5: Commit** (`feat(1d): VideoMeta.liveBroadcastContent (optional) for VOD-only`).

---

### Task 10: Producer two-client split + buckets + VOD/too_long block; remove `SupabaseJobQueue.enqueue`

**Files:** Modify `lib/job-queue/producer.ts`, `lib/storage/supabase/supabase-job-queue.ts`, `lib/storage/job-queue.ts`; **migrate the existing `tests/lib/producer.test.ts`** (round-2 H2 — it calls the old 3-arg `enqueuePlaylist(bundle, principal, url)`, uses a `jobQueue:{enqueue}` fake, asserts the old 4-bucket disjoint sum, and has "no jobQueue"/"broken jobQueue" tests that no longer apply; T13's grep is scoped to `tests/integration/` and misses it → `tsc`/`npm test` break otherwise); Create `tests/lib/producer-guardrails.test.ts`.

**Interfaces produced:** `enqueuePlaylist(sessionBundle: StorageBundle, enqueuer: Enqueuer, principal: Principal, playlistUrl: string, ctx: { ownerId: string; enqueueIp: string | null }): Promise<ProducerResult>`; `ProducerCounts { enqueued; joined; skipped; failed; quotaBlocked; capBlocked; tooLong }`; `ProducerResult` gains `challengeRequired?`/`dailyCapReached?`; `JobFanoutResult |= { videoId; blocked: 'quota_exceeded'|'daily_cap'|'too_long' }`. **Removes `enqueue` from `SupabaseJobQueue` and the `JobQueue` interface** (the 6-arg RPC is dropped; producer uses `Enqueuer`) — Claude M2.

- [ ] **Step 1: Failing tests** (fake `Enqueuer` implementing `enqueue`/`preflight`/**`getGuardrailConfig`→`{maxDurationSeconds:1800}`**): over-duration video **and** a video with `liveBroadcastContent==='live'` (and one `'upcoming'`) → `too_long`, never passed to `enqueue`; a fixture with `liveBroadcastContent` **absent** or `'none'` is NOT blocked; quota exhausts mid-list → per-video `quota_exceeded`, rest still enqueue; `DailyCapError` mid-loop → that + remaining `daily_cap`, `dailyCapReached:true`; enqueue receives `{ownerId, enqueueIp}`; **disjoint sum** `enqueued+joined+skipped+failed+quotaBlocked+capBlocked+tooLong === videos.length`. Add a case where the PJ003 backstop fires **inside** the loop (duration passes the producer check but the RPC throws `VideoTooLongError`) → counted in `tooLong`, sum still holds. **Also migrate `tests/lib/producer.test.ts`** to the 5-arg signature + a fake `Enqueuer` (drop the `jobQueue`-fake/"no jobQueue"/"broken jobQueue" cases; update its disjoint-sum assertion to the 7 buckets).
- [ ] **Step 2: FAIL. Step 3: Implement** — `maxDurationSeconds = (await enqueuer.getGuardrailConfig()).maxDurationSeconds`; block `durationSeconds > maxDurationSeconds` **or** `liveBroadcastContent === 'live' || liveBroadcastContent === 'upcoming'` before enqueue (`tooLongPreBlock`; absent/`'none'` → not blocked — round-2 H1) — read `liveBroadcastContent` from the original `videos: VideoMeta[]` (in scope), **not** the mapped `IngestionPayload` (which doesn't carry it); zip/iterate the `VideoMeta` alongside the payload (round-3 L); fan out via `enqueuer.enqueue`, catch `QuotaExceededError→quotaBlocked/continue`, `DailyCapError→capBlocked + dailyCapReached + cap-block remaining`, `VideoTooLongError→tooLongInLoop`; **`failed = enqueueable.length - created - joined - quotaBlocked - capBlocked - tooLongInLoop`**; `counts.tooLong = tooLongPreBlock + tooLongInLoop`. **Delete `SupabaseJobQueue.enqueue` + the `enqueue` member of the `JobQueue` interface** (grep `lib/`+`tests/` first to confirm the producer + T13-migrated tests are the only callers).
- [ ] **Step 4: PASS + `npx tsc --noEmit`. Step 5: Commit** (`feat(1d): producer two-client split + guardrail buckets; drop JobQueue.enqueue`).

---

### Task 11: `POST /api/jobs` wiring

**Files:** Modify `app/api/jobs/route.ts`; Test `tests/api/jobs-route-guardrails.test.ts`.
**Interfaces produced:** POST: session `getUser()`→`ownerId`; `enqueuer = new SupabaseEnqueuer(createServiceClient())`; IP from `Fly-Client-IP` else first `X-Forwarded-For` hop; `preflight` → `velocityExceeded→429`+`Retry-After`, `atCapacity→503`, `!admitted→403`; else `enqueuePlaylist(sessionBundle, enqueuer, principal, playlistUrl, {ownerId, enqueueIp})` → 200 with `challengeRequired`. GET unchanged (session client).

- [ ] **Step 1: Failing tests** (mock session client + fake Enqueuer): 429+`Retry-After`; 503; 403; 200 with `challengeRequired`+mixed counts; IP parsed from both headers; write path uses the service Enqueuer, reads use the session client.
- [ ] **Step 2: FAIL. Step 3: Implement. Step 4: PASS (`npm test jobs-route`) + `npx tsc --noEmit`. Step 5: Commit** (`feat(1d): POST /api/jobs preflight + two-client wiring`).

---

### Task 12: Cap-soundness guard test (independent recompute, drift-proof)

**Files:** Create `tests/integration/cap-soundness.test.ts`.

- [ ] **Step 1: Write the test — recompute the derivation INLINE from imported raw constants** (not only via `perRunWorstCents`, so a bug in that helper can't hide — Codex H6):

```ts
import { adminClient } from './helpers/clients';
import * as C from '@/lib/gemini-cost';
import { SUMMARY_MODEL, TRANSCRIBE_MODEL } from '@/lib/gemini';

it('est >= independently-recomputed worst case x max_attempts (live config)', async () => {
  const { data: cfg } = await adminClient().from('guardrail_config').select('*').single();
  const d = cfg!.max_duration_seconds;
  const audio = C.AUDIO_TOKENS_PER_SEC * d;
  const video = Math.max(0, C.MAX_TRANSCRIBE_INPUT_TOKENS - audio);
  const cents = (tok: number, per1m: number) => (tok * per1m) / 1_000_000;
  const tr = C.TRANSCRIBE_MAX_PASSES * (cents(audio, C.PRICE_AUDIO_IN_PER_1M_CENTS) + cents(video, C.PRICE_IN_PER_1M_CENTS)
    + cents(C.PROMPT_SCHEMA_OVERHEAD_TOKENS, C.PRICE_IN_PER_1M_CENTS) + cents(C.MAX_TRANSCRIBE_OUTPUT_TOKENS, C.PRICE_OUT_PER_1M_CENTS));
  const perSummaryPass = cents(C.MAX_TRANSCRIPT_INPUT_BYTES + C.PROMPT_SCHEMA_OVERHEAD_TOKENS, C.PRICE_IN_PER_1M_CENTS) + cents(C.MAX_SUMMARY_OUTPUT_TOKENS, C.PRICE_OUT_PER_1M_CENTS);
  const worst = tr + (C.SUMMARY_MAX_PASSES + C.QUICKVIEW_MAX_PASSES) * perSummaryPass;
  expect(cfg!.summary_est_cents).toBeGreaterThanOrEqual(Math.ceil(worst) * cfg!.summary_max_attempts);
  expect(C.perRunWorstCents({ maxDurationSeconds: d })).toBeGreaterThanOrEqual(Math.ceil(worst)); // helper not under-counting
});
it('resolved models equal the priced model', () => {
  expect(SUMMARY_MODEL).toBe(C.PRICED_MODEL); expect(TRANSCRIBE_MODEL).toBe(C.PRICED_MODEL);
});
```

- [ ] **Step 2: Run → PASS** (150 ≥ ~116). If it fails, fix constants/est — never weaken the test. **Step 3: Commit** (`test(1d): drift-proof cap-soundness guard`).

---

### Task 13: Live impl-verification gates + integration test migration

**Files:** Create `tests/integration/gemini-live-gates.test.ts` (gated by `RUN_LIVE_GEMINI`); Modify the enqueue-calling integration files.

- [ ] **Step 1: Live gates** (`describe.skip` unless `RUN_LIVE_GEMINI=1`): (a) cloud transcribe+summary with `thinkingBudget:0` asserts `usageMetadata.thoughtsTokenCount` **present and === 0** (absent → fail); (b) `model.countTokens` on a real YouTube `fileData` LOW-res request returns a video-scale `totalTokens`. Record the outcome to **`docs/reviews/1d-live-gemini-gates.md`**; if (b) holds, set `CLOUD_TRANSCRIBE_FALLBACK_VERIFIED=true` in `gemini.ts` (else leave fail-closed). Add a normal (non-live) unit test asserting that with the flag false + caps, transcribe rejects caption-less (fallback disabled).
- [ ] **Step 2: Inventory** — run `grep -rln "enqueue_job\|\.enqueue(\|from('jobs')\.insert\|from(\"jobs\")\.insert" tests/integration/` (include the `jobs` insert pattern — `job-queue-schema.test.ts` uses `.insert`, not the enqueue tokens, so the bare grep misses it — round-3 L) and migrate each: `job-queue-schema.test.ts` — **all four client-insert cases** (round-3 M): (a) "insert for another owner … with-check" → grant `42501`; (b) "idempotency index blocks a second live job" → `enqueue_job` join, no `.error`; (c) "a user can insert and read only their own jobs (RLS isolation)" — its **setup** `.insert` (line ~18) now 42501s → re-cast to two admin/service inserts for two owners (SELECT grant retained, so the isolation assertions still hold); (d) "a producer cannot directly update a job" — its **setup** `.insert` (line ~47) now fails → re-cast to an admin/service insert before the update assertion. `cancel-by-playlist`, `cancel-job-rpc`, `job-queue-runner`, `job-queue-store`, `job-queue-producer`, `job-queue-playlist-identity`, `job-queue-worker`, `worker-main`, `jobs-producer-polling`, `producer-roundtrip` — switch direct session `enqueue_job`/`SupabaseJobQueue.enqueue` to the **8-arg service path** (`svc.rpc('enqueue_job',{p_owner_id,…,p_enqueue_ip})` or `SupabaseEnqueuer`); re-baseline `jobs-producer-polling`/`producer-roundtrip` counts against the two-client producer + new buckets. (Classify per file: direct-RPC vs producer-roundtrip vs admin-insert-stays-valid.)
- [ ] **Step 3: Full suites.** `npx supabase db reset && npm run test:integration -- --runInBand` all green; `npm test`; `npx tsc --noEmit`.
- [ ] **Step 4: Commit** (`test(1d): live gates + migrate integration tests to server-mediated enqueue`).

---

## Self-Review

**Spec coverage:** §3 tables/cols/index → T1; est constants/derivation → T6; §4 enqueue_job (drop 0009 6-arg, PJ001/2/3, duration backstop, max_attempts, auth.uid→p_owner_id, ON CONFLICT, grants) → T2; §5 two-client + preflight + config source → T3/T4/T5/T10/T11; §6 error contracts/Enqueuer/counts/failed → T4/T5/T10; §7 security (bypass closure both signatures) → T2; §8 all rows (debit/rollover/race/anon/cap/at-most-once/duration/bypass/owner/dig/preflight/guard/gemini-caps/impl-gates/producer/route) → T2/T3/T7/T8/T10/T11/T12/T13; §9 CloudGeminiCaps threading (3 calls, local unchanged) → T6/T7/T8; §10 handler reads config → T8; VOD-only → T9/T10. Deferred residuals are documented in the spec, not tasks. No gaps.

**Placeholder scan:** none — every code step carries real SQL/TS or an exact command; the two large SQL bodies (T2/T3) reference spec §3/§4 line ranges to copy verbatim from the committed canonical spec.

**Type consistency:** `CloudGeminiCaps` fields identical T6→T7→T8. `EnqueueCtx {ownerId, enqueueIp}` T4→T5→T10→T11. `Enqueuer` (`enqueue`/`preflight`/`getGuardrailConfig`) T4→T5→T10. `ProducerCounts` buckets + `failed`/`tooLong` formula match §6 invariant (T10). PJ001/2/3 → `QuotaExceededError`/`DailyCapError`/`VideoTooLongError` across T4/T5/T10. `perRunWorstCents({maxDurationSeconds})` signature T6 consumed by T12. `SUMMARY_MODEL`/`TRANSCRIBE_MODEL` exported (T6) asserted (T8/T12). Helper signatures (`u.user.id`, `signInAs(email,password).client`) consistent across all integration tasks.
