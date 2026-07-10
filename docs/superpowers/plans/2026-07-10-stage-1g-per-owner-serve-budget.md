# Stage 1G / G1 — Per-Owner Serve Budget Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bound any single owner's daily serve-model spend (a per-owner cents/day cap) so no one owner can exhaust the shared 500¢/day pool, and — when over budget — serve a previously-materialized ("title-stable stale") rendering instead of failing.

**Architecture:** A new per-`(owner,day)` cents counter (`serve_owner_budget`) is enforced by a **second atomic arbiter inside `reserve_serve_model`, checked BEFORE the existing global arbiter**, both in the RPC's existing savepoint sub-block. A new coarse status `owner_over_budget` flows through `resolveMagazineModel`, which on that status does a gate-free "title-stable" model read and serves it (labeled `X-Magazine-Stale`) or returns `over_budget` → 503. Share path and the never-charge invariant are untouched.

**Tech Stack:** Supabase Postgres (SECURITY DEFINER plpgsql RPC, force-RLS), Next.js route handlers, TypeScript strict, jest + ts-jest (unit), real-DB integration (`npm run test:integration -- --runInBand`).

**Spec:** `docs/superpowers/specs/2026-07-10-stage-1g-per-owner-serve-budget-design.md` (v3 CONVERGED). Behaviors P1–P17 (spec §5) are the test contract.

## Global Constraints

- **Per-owner arbiter is checked FIRST, global second** — both inside the existing `begin … exception … end` sub-block so any raise (PJ005 or PJ004) rolls back the lease claim + BOTH increments. An `owner_over_budget` outcome must leave `serve_owner_budget`, `spend_ledger`, and `serve_model_charge.attempt_count` all unchanged (spec D3, P3, P4b).
- **`create or replace function reserve_serve_model` MUST restate the complete header** `returns text language plpgsql security definer set search_path = public` and re-affirm `revoke all … from public` + `grant execute … to authenticated, anon`. **Never `drop function`** (same signature preserves ACL + ownership). Omitting `security definer`/`search_path` silently reverts to INVOKER → RLS blocks the service_role-only writes → every serve 500s (spec Blocking/H2).
- **Serve-stale is gated on `sameTitles` (title-stable), NOT the full `isFresh`** — serving a stale model against current markdown is only positionally coherent when section titles line up (spec H1 fix). Titles drifted OR no envelope → `over_budget` → 503.
- **Serve-stale never charges** — it is a pure blob read after a rolled-back reserve. `read-model.ts` stays a generate-free leaf (no gemini/charging import); the 1F-b import-guard must stay green.
- **Default `per_owner_serve_daily_cents = 60`, CHECK `>= magazine_est_cents`.** Cap boundary is `spent + est <= cap` (exact; P10).
- **Share path (`app/s/[token]`, `readFreshMagazineModel`) never calls `reserve_serve_model`** — unchanged; re-assert via the 1F-b B18 money proof (P11).
- **Next.js:** read the route-handler guide under `node_modules/next/dist/docs/` before editing the handler (AGENTS.md).
- **`gh` two-remotes footgun:** any `gh` command MUST pass `--repo kujinlee/youtube-playlist-summaries-cloud`.
- **§8 iterative dual-review triggers:** Task 1 (money RPC + schema + concurrency) and Task 2 (serve-stale logic) get per-task iterative Codex+Claude review. Task 3 (route/header wiring) is single-pass.

---

## File Structure

**Create:**
- `supabase/migrations/0014_serve_owner_budget.sql` — `serve_owner_budget` table (force-RLS, service_role grant) + `per_owner_serve_daily_cents` config column + `create or replace reserve_serve_model` with the per-owner-first arbiter.
- `tests/integration/serve-owner-budget.test.ts` — RPC-level behaviors P2–P17.

**Modify:**
- `lib/html-doc/read-model.ts` — extract `sameTitles`; add generate-free `readTitleStableModel`.
- `lib/html-doc/serve-doc.ts` — `ResolveResult` gains `stale?`/`over_budget`; new `owner_over_budget` case.
- `app/api/html/[id]/route.ts` — `over_budget` → 503; `X-Magazine-Stale` on stale HTML.
- `lib/html-doc/file-response.ts` — optional `staleMarker?: boolean` opt (html kind only).
- `tests/integration/serve-config-invariant.test.ts` (+ `serve-model-charge.test.ts` `beforeEach`) — include `per_owner_serve_daily_cents` in the canonical config (P12).
- `tests/lib/html-doc/read-model.test.ts` (or new) — unit for `readTitleStableModel` / `sameTitles`.
- `tests/lib/html-doc/file-response.test.ts` — `staleMarker` header unit.
- `tests/integration/share-route.test.ts` — re-assert P11 (share never reserves; no `serve_owner_budget` write).

---

## Task 1: Migration 0014 — table + config column + `reserve_serve_model` (per-owner-first arbiter)

**§8 re-review trigger — money RPC + schema + concurrency.**

**Files:**
- Create: `supabase/migrations/0014_serve_owner_budget.sql`, `tests/integration/serve-owner-budget.test.ts`
- Modify: `tests/integration/serve-config-invariant.test.ts`, `tests/integration/serve-model-charge.test.ts` (`beforeEach` reset)

**Interfaces:**
- Produces: RPC `reserve_serve_model(p_playlist_id uuid, p_video_id text) → text` now also returns `'owner_over_budget'`; table `serve_owner_budget(owner_id uuid, day date, spent_cents int)`; config column `guardrail_config.per_owner_serve_daily_cents int`.

- [ ] **Step 1: Write the failing RPC tests** (`tests/integration/serve-owner-budget.test.ts`)

Mirror `serve-model-charge.test.ts`'s harness (`adminClient`, `newUser`, `signInAs`, `seedPlaylist`, `seedPromotedVideo`). Reset in `beforeEach` (add `per_owner_serve_daily_cents`):

```ts
import { adminClient, newUser, signInAs } from './helpers/clients';
import { seedPlaylist, seedPromotedVideo } from './helpers/seed';

const svc = adminClient();

async function seedPromotedDoc(ownerId: string, videoId?: string) {
  const { playlistId } = await seedPlaylist(svc, ownerId);
  const { videoId: vid } = await seedPromotedVideo(svc, { ownerId, playlistId, videoId });
  return { playlistId, videoId: vid };
}
const expire = (docKey: string) =>
  svc.from('serve_model_charge').update({ lease_expires_at: '2000-01-01T00:00:00Z' }).eq('doc_key', docKey);

beforeEach(async () => {
  await svc.from('serve_model_charge').delete().neq('owner_id', '00000000-0000-0000-0000-000000000000');
  await svc.from('serve_owner_budget').delete().neq('owner_id', '00000000-0000-0000-0000-000000000000');
  await svc.from('spend_ledger').delete().neq('day', '1900-01-01');
  await svc.from('guardrail_config').update({
    daily_cap_cents: 500, magazine_est_cents: 6, max_serve_attempts: 5, lease_ttl_seconds: 180,
    per_owner_serve_daily_cents: 60,
  }).eq('id', true);
});

// ── Helpers (CRITICAL — review Blocking): the migration adds CHECK (per_owner_serve_daily_cents >=
// magazine_est_cents=6), so you CANNOT set the cap to 3 to force over-budget (the UPDATE would violate
// the CHECK). Instead keep cap >= 6 and PRE-SEED serve_owner_budget at the cap, so the next attempt's
// (spent + 6 > cap) triggers owner_over_budget. Use this pattern for every over-budget scenario. ──
const utcDay = () => new Date().toISOString().slice(0, 10); // YYYY-MM-DD (UTC) — matches (now() at tz 'utc')::date
const setOwnerCap = (cents: number) =>
  svc.from('guardrail_config').update({ per_owner_serve_daily_cents: cents }).eq('id', true); // cents MUST be >= 6
const preseedBudget = (ownerId: string, spent: number, day: string = utcDay()) =>
  svc.from('serve_owner_budget').insert({ owner_id: ownerId, day, spent_cents: spent });
const snapshot = async (ownerId: string) => ({
  ob: (await svc.from('serve_owner_budget').select('spent_cents').eq('owner_id', ownerId)).data ?? [],
  led: (await svc.from('spend_ledger').select('reserved_cents')).data ?? [],
  smc: (await svc.from('serve_model_charge').select('attempt_count').eq('owner_id', ownerId)).data ?? [],
});

it('P2/P12: config has per_owner_serve_daily_cents default 60', async () => {
  const { data } = await svc.from('guardrail_config').select('per_owner_serve_daily_cents').single();
  expect(data!.per_owner_serve_daily_cents).toBe(60);
});

it('P2: first reserve charges owner budget and global ledger by 6 each', async () => {
  const u = await newUser();
  const { playlistId, videoId } = await seedPromotedDoc(u.user.id);
  const { client } = await signInAs(u.email, u.password);
  const { data: st } = await client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId });
  expect(st).toBe('reserved');
  const { data: ob } = await svc.from('serve_owner_budget').select('spent_cents').eq('owner_id', u.user.id).single();
  expect(ob!.spent_cents).toBe(6);
  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
  expect(led![0].reserved_cents).toBe(6);
});

it('P3: per-owner cap blocks with owner_over_budget and FULL rollback from an existing budget row', async () => {
  const u = await newUser();
  const { playlistId, videoId } = await seedPromotedDoc(u.user.id);
  await setOwnerCap(6);                 // valid (>= est=6)
  await preseedBudget(u.user.id, 6);    // already at cap → next attempt (6+6>6) is blocked
  const { client } = await signInAs(u.email, u.password);
  const before = await snapshot(u.user.id);
  const { data: st } = await client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId });
  expect(st).toBe('owner_over_budget');
  const after = await snapshot(u.user.id);
  // Full rollback: all three tables byte-identical to before (no increment, no attempt/lease marker).
  expect(after).toEqual(before);
});

it('P4: over budget AND global full → owner_over_budget (per-owner checked first)', async () => {
  const u = await newUser();
  const { playlistId, videoId } = await seedPromotedDoc(u.user.id);
  await setOwnerCap(6);
  await preseedBudget(u.user.id, 6);
  await svc.from('guardrail_config').update({ daily_cap_cents: 3 }).eq('id', true); // global also full (no CHECK vs est on daily_cap)
  const { client } = await signInAs(u.email, u.password);
  const { data: st } = await client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId });
  expect(st).toBe('owner_over_budget'); // NOT at_capacity — per-owner arbiter runs first
});

it('P4b: under budget, global full → at_capacity, 5a per-owner increment rolled back (no phantom spend)', async () => {
  const u = await newUser();
  const { playlistId, videoId } = await seedPromotedDoc(u.user.id);
  await svc.from('guardrail_config').update({ daily_cap_cents: 3 }).eq('id', true); // owner cap stays default 60 (under budget)
  const { client } = await signInAs(u.email, u.password);
  const before = await snapshot(u.user.id);
  const { data: st } = await client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId });
  expect(st).toBe('at_capacity');
  const after = await snapshot(u.user.id);
  expect(after).toEqual(before); // 5a serve_owner_budget increment AND the step-4 claim rolled back by 5b PJ004
});

it('P9: a maxed-out PRIOR-day budget row does not block today (daily reset)', async () => {
  const u = await newUser();
  const { playlistId, videoId } = await seedPromotedDoc(u.user.id);
  await setOwnerCap(6);
  const yesterday = new Date(Date.parse(utcDay()) - 86400000).toISOString().slice(0, 10);
  await preseedBudget(u.user.id, 6, yesterday); // yesterday maxed
  const { client } = await signInAs(u.email, u.password);
  const { data: st } = await client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId });
  expect(st).toBe('reserved'); // today's (owner, today) row starts fresh at 0 → 0+6<=6
  const { data: today } = await svc.from('serve_owner_budget').select('spent_cents').eq('owner_id', u.user.id).eq('day', utcDay()).single();
  expect(today!.spent_cents).toBe(6);
});

it('P8: owner isolation — A at cap does not block B (independent rows, valid cap)', async () => {
  const a = await newUser(); const b = await newUser();
  const da = await seedPromotedDoc(a.user.id); const db = await seedPromotedDoc(b.user.id);
  await setOwnerCap(6);                 // valid for everyone
  await preseedBudget(a.user.id, 6);    // ONLY A is maxed today; B has no row
  const ca = await signInAs(a.email, a.password); const cb = await signInAs(b.email, b.password);
  const { data: sa } = await ca.client.rpc('reserve_serve_model', { p_playlist_id: da.playlistId, p_video_id: da.videoId });
  const { data: sb } = await cb.client.rpc('reserve_serve_model', { p_playlist_id: db.playlistId, p_video_id: db.videoId });
  expect(sa).toBe('owner_over_budget'); // A blocked by A's own row
  expect(sb).toBe('reserved');          // B unaffected — proves per-owner keying, not shared/misconfig
});

it('P10: cap boundary is exact (spent + 6 <= cap)', async () => {
  const u = await newUser();
  const d1 = await seedPromotedDoc(u.user.id); const d2 = await seedPromotedDoc(u.user.id);
  await svc.from('guardrail_config').update({ per_owner_serve_daily_cents: 6 }).eq('id', true); // exactly one slot
  const { client } = await signInAs(u.email, u.password);
  const { data: s1 } = await client.rpc('reserve_serve_model', { p_playlist_id: d1.playlistId, p_video_id: d1.videoId });
  const { data: s2 } = await client.rpc('reserve_serve_model', { p_playlist_id: d2.playlistId, p_video_id: d2.videoId });
  expect(s1).toBe('reserved');           // 0 + 6 <= 6
  expect(s2).toBe('owner_over_budget');  // 6 + 6 > 6
});

it('R5: each of the K reclaim attempts charges the owner budget (K·6¢ total)', async () => {
  const u = await newUser();
  const { playlistId, videoId } = await seedPromotedDoc(u.user.id);
  await setOwnerCap(60); // headroom for all K attempts (5×6=30 <= 60)
  const { client } = await signInAs(u.email, u.password);
  const docKey = `${playlistId}/${videoId}`;
  for (let i = 1; i <= 5; i++) {
    const { data: st } = await client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId });
    expect(st).toBe('reserved');
    await expire(docKey);
  }
  const { data: ob } = await svc.from('serve_owner_budget').select('spent_cents').eq('owner_id', u.user.id).single();
  expect(ob!.spent_cents).toBe(30); // 5 attempts × 6
});

// P17 (definer preservation) is written in Step 3 — it depends on the `reserve_serve_model_meta`
// catalog-probe helper that the migration creates, so it can't be a failing test before the migration
// exists. Its two assertions (catalog + end-to-end) are given in Step 3.
```

> **P17 depends on the migration (written in Step 3):** the catalog assertion needs to read `pg_proc.prosecdef`/`proconfig`, which the migration exposes via a tiny read-only `reserve_serve_model_meta()` helper (defined in Step 3's migration). So P17's tests are authored in Step 3 alongside that helper, not here. They assert (a) `secdef === true` + `proconfig` contains `search_path=public`, and (b) a `signInAs` session client gets `'reserved'` on a promoted doc — the end-to-end proof that writes to the service_role-only tables still succeed (they'd RLS-fail if the function reverted to SECURITY INVOKER).

- [ ] **Step 2: Run the tests — confirm they fail**

Run: `npm run test:integration -- --runInBand -t "serve-owner-budget"`
Expected: FAIL — `serve_owner_budget` table and `per_owner_serve_daily_cents` column don't exist; RPC never returns `owner_over_budget`.

- [ ] **Step 3: Write the migration** (`supabase/migrations/0014_serve_owner_budget.sql`)

```sql
-- supabase/migrations/0014_serve_owner_budget.sql
-- Stage 1G / G1: per-owner daily serve-spend cap. Adds a per-(owner,day) cents counter enforced by a
-- second atomic arbiter in reserve_serve_model, checked BEFORE the global arbiter (spec D1/D2/D3).

-- 1. Per-owner counter (analog of spend_ledger). force-RLS + service_role-only (no client policy).
create table serve_owner_budget (
  owner_id uuid not null references profiles(id) on delete cascade,
  day date not null,
  spent_cents int not null default 0 check (spent_cents >= 0),
  primary key (owner_id, day));
alter table serve_owner_budget enable row level security;
alter table serve_owner_budget force row level security;
grant select, insert, update, delete on serve_owner_budget to service_role;

-- 2. Config column. CHECK guarantees >= one attempt always fits (spec D2).
alter table guardrail_config add column per_owner_serve_daily_cents int not null
  default 60 check (per_owner_serve_daily_cents >= magazine_est_cents);

-- 3. Replace reserve_serve_model: per-owner arbiter (5a) FIRST, then global (5b). CREATE OR REPLACE with
--    the UNCHANGED signature preserves ACL + ownership, but the definer/search_path attributes are part
--    of the definition and MUST be restated verbatim (spec Blocking/H2). Do NOT drop the function.
create or replace function reserve_serve_model(p_playlist_id uuid, p_video_id text)
  returns text
  language plpgsql security definer set search_path = public as $$
declare
  v_owner uuid := auth.uid();
  v_cfg guardrail_config;
  v_doc_key text;
  v_day date;
  v_promoted boolean;
  v_claimed int;
  v_existing int;
  v_lease_live boolean;
  v_result text;
begin
  if v_owner is null then raise exception 'reserve_serve_model: unauthenticated'; end if;

  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
    into v_promoted
    from videos v join playlists p on p.id = v.playlist_id
    where v.playlist_id = p_playlist_id and v.video_id = p_video_id and p.owner_id = v_owner;
  if v_promoted is distinct from true then
    return 'denied';
  end if;

  select * into v_cfg from guardrail_config where id = true;
  v_doc_key := p_playlist_id::text || '/' || p_video_id;
  v_day := (now() at time zone 'utc')::date;

  begin
    -- 4. Claim/reclaim the lease atomically, bounded by K attempts/day (UNCHANGED from 0012).
    insert into serve_model_charge (owner_id, doc_key, day, lease_expires_at, attempt_count)
      values (v_owner, v_doc_key, v_day, now() + make_interval(secs => v_cfg.lease_ttl_seconds), 1)
    on conflict (owner_id, doc_key, day) do update
      set lease_expires_at = now() + make_interval(secs => v_cfg.lease_ttl_seconds),
          attempt_count = serve_model_charge.attempt_count + 1
      where serve_model_charge.lease_expires_at < now()
        and serve_model_charge.attempt_count < v_cfg.max_serve_attempts;
    get diagnostics v_claimed = row_count;

    if v_claimed = 0 then
      select attempt_count, lease_expires_at > now()
        into v_existing, v_lease_live
        from serve_model_charge
        where owner_id = v_owner and doc_key = v_doc_key and day = v_day;
      v_result := case
                    when v_lease_live then 'in_flight'
                    when v_existing >= v_cfg.max_serve_attempts then 'attempts_exhausted'
                    else 'in_flight'
                  end;
    else
      -- 5a. PER-OWNER daily cap (checked FIRST) → PJ005 → 'owner_over_budget'.
      --     Over-budget owners fail here without ever locking the global spend_ledger money row.
      insert into serve_owner_budget (owner_id, day) values (v_owner, v_day) on conflict do nothing;
      update serve_owner_budget set spent_cents = spent_cents + v_cfg.magazine_est_cents
        where owner_id = v_owner and day = v_day
          and spent_cents + v_cfg.magazine_est_cents <= v_cfg.per_owner_serve_daily_cents;
      if not found then raise exception 'serve_owner_over_budget' using errcode = 'PJ005'; end if;

      -- 5b. GLOBAL daily cap (unchanged logic) → PJ004 → 'at_capacity'.
      insert into spend_ledger (day) values (v_day) on conflict do nothing;
      update spend_ledger set reserved_cents = reserved_cents + v_cfg.magazine_est_cents, updated_at = now()
        where day = v_day
          and reserved_cents + actual_cents + v_cfg.magazine_est_cents <= v_cfg.daily_cap_cents;
      if not found then raise exception 'serve_at_capacity' using errcode = 'PJ004'; end if;

      v_result := 'reserved';
    end if;
  exception
    when sqlstate 'PJ005' then v_result := 'owner_over_budget';  -- 5a claim + any 5a state rolled back
    when sqlstate 'PJ004' then v_result := 'at_capacity';        -- 5a increment + step-4 claim rolled back
  end;

  return v_result;
end $$;

-- Same signature → grants/ownership preserved; restate for auditability (spec §6).
revoke all on function reserve_serve_model(uuid, text) from public;
grant execute on function reserve_serve_model(uuid, text) to authenticated, anon;

-- P17 catalog probe helper (read-only; lets the test assert definer preservation without admin catalog access).
create function reserve_serve_model_meta()
  returns table(secdef boolean, cfg text[])
  language sql security definer set search_path = public as $$
    select p.prosecdef, p.proconfig
    from pg_proc p
    where p.oid = 'public.reserve_serve_model(uuid,text)'::regprocedure  -- exact overload, not proname match
  $$;
revoke all on function reserve_serve_model_meta() from public;
grant execute on function reserve_serve_model_meta() to authenticated, anon, service_role;
```

Finalize the P17 test using the helper:
```ts
it('P17: reserve_serve_model retains SECURITY DEFINER + search_path', async () => {
  const { data } = await svc.rpc('reserve_serve_model_meta');
  expect(data![0].secdef).toBe(true);
  // Tolerant matcher — proconfig element may render quoted / with spacing depending on PG.
  expect((data![0].cfg ?? []).some((v: string) => v.replace(/\s/g, '') === 'search_path=public')).toBe(true);
});
it('P17: an authenticated session can still reserve (writes to service_role-only tables succeed)', async () => {
  const u = await newUser();
  const { playlistId, videoId } = await seedPromotedDoc(u.user.id);
  const { client } = await signInAs(u.email, u.password);
  const { data: st } = await client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId });
  expect(st).toBe('reserved'); // would be an RLS/permission error if it reverted to SECURITY INVOKER
});
```
(Delete the placeholder P17 block from Step 1.)

- [ ] **Step 4: Update the canonical config guard** (`tests/integration/serve-config-invariant.test.ts`)

Add `per_owner_serve_daily_cents: 60` to the canonical `guardrail_config` assertion/seed there (read the file; mirror how it already lists `magazine_est_cents`/`max_serve_attempts`/`lease_ttl_seconds`). Also add `per_owner_serve_daily_cents: 60` to the `beforeEach` config reset in `tests/integration/serve-model-charge.test.ts` so its existing tests still see a known cap (default 60 is above their 6¢/30¢ spends → no behavior change).

- [ ] **Step 5: Run — confirm green (incl. no regression in the existing serve-model-charge suite)**

Run: `npx supabase db reset && npm run test:integration -- --runInBand -t "serve-owner-budget" && npm run test:integration -- --runInBand -t "serve-model-charge" && npm run test:integration -- --runInBand -t "serve-config-invariant"`
Expected: all PASS; existing serve-model-charge behaviors unchanged (owner cap 60 doesn't bite their small spends).

- [ ] **Step 6: Add spec-P15 (concurrency at the boundary) and spec-P16 (over-budget + live lease)**

**Spec P15 — same owner, two docs, one slot, concurrent** (this is spec P15, not P16 — the plan's earlier draft mislabeled it):
```ts
it('P15: concurrent same-owner, two docs, one slot → one reserved, one owner_over_budget (+6 not +12, one marker)', async () => {
  const u = await newUser();
  const d1 = await seedPromotedDoc(u.user.id); const d2 = await seedPromotedDoc(u.user.id);
  await setOwnerCap(6); // exactly one 6¢ slot; both start at 0
  const { client } = await signInAs(u.email, u.password);
  const [r1, r2] = await Promise.all([
    client.rpc('reserve_serve_model', { p_playlist_id: d1.playlistId, p_video_id: d1.videoId }),
    client.rpc('reserve_serve_model', { p_playlist_id: d2.playlistId, p_video_id: d2.videoId }),
  ]);
  expect([r1.data, r2.data].sort()).toEqual(['owner_over_budget', 'reserved']); // exactly one wins
  const { data: ob } = await svc.from('serve_owner_budget').select('spent_cents').eq('owner_id', u.user.id).single();
  expect(ob!.spent_cents).toBe(6);                              // +6 not +12 — serve_owner_budget row lock serialized them
  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
  expect(led!.reduce((a, r) => a + r.reserved_cents, 0)).toBe(6); // global charged once (loser's 5a rolled back before 5b)
  const { data: smc } = await svc.from('serve_model_charge').select('doc_key').eq('owner_id', u.user.id);
  expect(smc!.length).toBe(1);                                  // only the winner holds a lease marker (loser's step-4 claim rolled back)
});
```

**Spec P16 — over budget AND a live lease → `in_flight`, NOT owner_over_budget** (step-4 can't claim → 5a/5b never run → serve-stale not reached):
```ts
it('P16: over budget + a live lease → in_flight (budget arbiter never runs), no charge', async () => {
  const u = await newUser();
  const { playlistId, videoId } = await seedPromotedDoc(u.user.id);
  await setOwnerCap(6);
  await preseedBudget(u.user.id, 6); // over budget
  // Plant a LIVE lease for this doc (so step-4 ON CONFLICT finds attempt_count < K but lease_expires_at > now() → no claim).
  await svc.from('serve_model_charge').insert({
    owner_id: u.user.id, doc_key: `${playlistId}/${videoId}`, day: utcDay(),
    lease_expires_at: new Date(Date.now() + 180_000).toISOString(), attempt_count: 1,
  });
  const before = await snapshot(u.user.id);
  const { client } = await signInAs(u.email, u.password);
  const { data: st } = await client.rpc('reserve_serve_model', { p_playlist_id: playlistId, p_video_id: videoId });
  expect(st).toBe('in_flight');                 // live lease wins over the budget check (step-4 precedes 5a)
  const after = await snapshot(u.user.id);
  expect(after.led).toEqual(before.led);        // no global charge
  // serve_owner_budget untouched by this call (the pre-seeded row is unchanged)
  const { data: ob } = await svc.from('serve_owner_budget').select('spent_cents').eq('owner_id', u.user.id).single();
  expect(ob!.spent_cents).toBe(6);
});
```
Run both focused tests; confirm PASS.

- [ ] **Step 7: Full integration + tsc, then commit**

Run: `npm run test:integration -- --runInBand && npx tsc --noEmit`
```bash
git add supabase/migrations/0014_serve_owner_budget.sql tests/integration/serve-owner-budget.test.ts \
  tests/integration/serve-config-invariant.test.ts tests/integration/serve-model-charge.test.ts
git commit -m "feat(1g): serve_owner_budget + per-owner-first arbiter in reserve_serve_model (0014)"
```

---

## Task 2: Caller — `readTitleStableModel` + `resolveMagazineModel` over-budget/serve-stale

**§8 re-review trigger — serve-stale logic + never-charge leaf.**

**Files:**
- Modify: `lib/html-doc/read-model.ts`, `lib/html-doc/serve-doc.ts`
- Test: `tests/lib/html-doc/read-model.test.ts` (unit), `tests/integration/serve-doc-materialize.test.ts` (integration), `tests/integration/share-route.test.ts` (P11)

**Interfaces:**
- Consumes: RPC `owner_over_budget` status (Task 1).
- Produces: `ResolveResult` gains `| { status: 'ok'; model; stale?: boolean } | { status: 'over_budget' }`; `readTitleStableModel(args) → { status: 'ok'; model } | { status: 'none' }`; exported `sameTitles(envelope, titles) → boolean`.

- [ ] **Step 1: Write the failing unit tests** (`tests/lib/html-doc/read-model.test.ts` — add to it)

**Add these to the EXISTING `tests/lib/html-doc/read-model.test.ts`**, reusing its already-defined `jest.mock('@/lib/html-doc/model-store', …)` factory + `mockReadModelEnvelope`, and its `envelope()` / `roStore` / `principal` / `fakeModel` / `titles` fixtures (lines 11–23). Do NOT introduce a `fakeBlobWithEnvelope`/blob stub — a partial envelope would fail `readModelEnvelope`'s `ModelEnvelopeSchema.strict()` parse (it needs the full `{sourceMd, generatedAt, sourceSections, generatorVersion, model}`); mock `readModelEnvelope` instead (the repo convention, per the file's header note). Also import the two new symbols in the existing import line: `import { readFreshMagazineModel, isFresh, sameTitles, readTitleStableModel } from '@/lib/html-doc/read-model';`

```ts
describe('sameTitles', () => {
  it('true iff same length and same order', () => {
    expect(sameTitles(envelope(), titles)).toBe(true);                       // ['A','B'] === ['A','B']
    expect(sameTitles(envelope({ sourceSections: ['B', 'A'] }), titles)).toBe(false);
    expect(sameTitles(envelope({ sourceSections: ['A'] }), titles)).toBe(false);
  });
});

describe('readTitleStableModel', () => {
  afterEach(() => mockReadModelEnvelope.mockReset());

  it('ok with the model when the envelope exists and titles match — version ignored (stale ok)', async () => {
    mockReadModelEnvelope.mockResolvedValue(envelope({ generatorVersion: 'OLD' })); // stale VERSION, same titles
    const r = await readTitleStableModel({ blobStore: roStore, principal, base: 'b', titles });
    expect(r).toEqual({ status: 'ok', model: fakeModel });
    expect(mockReadModelEnvelope).toHaveBeenCalledWith(principal, 'b', roStore);
  });
  it('none when titles drifted (positional mis-pair would occur → refuse)', async () => {
    mockReadModelEnvelope.mockResolvedValue(envelope({ sourceSections: ['X', 'B'], generatorVersion: 'OLD' }));
    const r = await readTitleStableModel({ blobStore: roStore, principal, base: 'b', titles });
    expect(r).toEqual({ status: 'none' });
  });
  it('none when no envelope', async () => {
    mockReadModelEnvelope.mockResolvedValue(null);
    const r = await readTitleStableModel({ blobStore: roStore, principal, base: 'b', titles });
    expect(r).toEqual({ status: 'none' });
  });
});
```

- [ ] **Step 2: Run — confirm fail** (`npx jest read-model` → `sameTitles`/`readTitleStableModel` not exported).

- [ ] **Step 3: Implement in `read-model.ts`** (keep it a generate-free leaf — no new imports beyond what's there)

```ts
export function sameTitles(
  envelope: { sourceSections: string[] },
  titles: string[],
): boolean {
  return envelope.sourceSections.length === titles.length &&
    envelope.sourceSections.every((t, i) => t === titles[i]);
}

export function isFresh(
  envelope: { sourceSections: string[]; generatorVersion?: string },
  titles: string[],
): boolean {
  return sameTitles(envelope, titles) && envelope.generatorVersion === GENERATOR_VERSION;
}

/** Title-stable read (spec D5): returns the cached model iff the envelope exists AND its section
 *  titles match `titles` (generator version may differ — the version-bump case). Positionally
 *  coherent to render against current markdown. Never reserves/generates (pure blob read). */
export async function readTitleStableModel(args: {
  blobStore: ReadOnlyBlobStore;
  principal: Principal;
  base: string;
  titles: string[];
}): Promise<{ status: 'ok'; model: MagazineModel } | { status: 'none' }> {
  const { blobStore, principal, base, titles } = args;
  const existing = await readModelEnvelope(principal, base, blobStore);
  if (existing && sameTitles(existing, titles)) return { status: 'ok', model: existing.model };
  return { status: 'none' };
}
```

- [ ] **Step 4: Implement in `serve-doc.ts`**

Extend the union and add the case (import `readTitleStableModel` alongside `readFreshMagazineModel`):
```ts
export type ResolveResult =
  | { status: 'ok'; model: MagazineModel; stale?: boolean }
  | { status: 'busy' }
  | { status: 'attempts_exhausted' }
  | { status: 'at_capacity' }
  | { status: 'over_budget' }
  | { status: 'denied' };
```
```ts
    case 'at_capacity': return { status: 'at_capacity' };
    case 'owner_over_budget': {
      // Spec D5: serve the title-stable stale rendering instead of failing; else 503.
      const staleRead = await readTitleStableModel({ blobStore, principal, base, titles });
      return staleRead.status === 'ok'
        ? { status: 'ok', model: staleRead.model, stale: true }
        : { status: 'over_budget' };
    }
    case 'reserved': break;
```

- [ ] **Step 5: Write the integration tests FIRST (RED), then implement Step 4** (`tests/integration/serve-doc-materialize.test.ts` — add)

> TDD note (review L1): author these BEFORE the Step-4 `serve-doc.ts` change so they fail first. They hit a real Supabase, so the over-budget state is forced with the cap-preseed pattern (NOT `cap=3` — that violates the CHECK), and "no charge" is proven by an observable before/after snapshot (a `jest.spyOn` on the RPC is not possible against the real DB — drop it). Follow this file's existing convention for mocking `generateMagazineModel` and for `writeModelEnvelope`.

Setup helpers (mirror Task 1): `setOwnerCap(6)` + `preseedBudget(owner, 6)` to force over-budget; `writeModelEnvelope(principal, base, { …, sourceSections, generatorVersion, model }, blobStore)` to materialize a cached model. A **title-match** stale envelope uses `sourceSections = parsed.sections.map(s=>s.title)` with `generatorVersion: 'OLD'`; a **title-drift** envelope uses `sourceSections` deliberately different from the current parsed titles.

```ts
// P5 — over budget + title-match stale model → ok+stale, NO charge.
it('P5: over budget + title-stable model → { ok, stale:true }, no charge', async () => {
  // seed promoted doc + parsed; writeModelEnvelope with matching titles + generatorVersion 'OLD'
  await setOwnerCap(6); await preseedBudget(ownerId, 6);
  const before = await snapshot(ownerId);
  const r = await resolveMagazineModel({ /* over-budget owner client, parsed, base, … */ });
  expect(r).toEqual({ status: 'ok', model: expect.anything(), stale: true });
  expect(await snapshot(ownerId)).toEqual(before); // reserve rolled back → no charge, no new lease
});

// P6 — over budget + no cached model → over_budget.
it('P6: over budget + no model → { over_budget }', async () => {
  await setOwnerCap(6); await preseedBudget(ownerId, 6);
  const r = await resolveMagazineModel({ /* … no envelope written … */ });
  expect(r).toEqual({ status: 'over_budget' });
});

// P6b — over budget + title-DRIFTED model → over_budget (NOT stale — avoids positional mis-pair).
it('P6b: over budget + titles drifted → { over_budget } (not stale)', async () => {
  // writeModelEnvelope with sourceSections that DIFFER from the current parsed titles
  await setOwnerCap(6); await preseedBudget(ownerId, 6);
  const r = await resolveMagazineModel({ /* … */ });
  expect(r).toEqual({ status: 'over_budget' });
});

// P14 — fresh model + owner over budget → ok WITHOUT reserving (observable no-charge, no rpc spy).
it('P14: fresh model + over budget → { ok } served free (reserve never runs)', async () => {
  // writeModelEnvelope with matching titles AND current GENERATOR_VERSION (fresh)
  await setOwnerCap(6); await preseedBudget(ownerId, 6);
  const before = await snapshot(ownerId);
  const r = await resolveMagazineModel({ /* … */ });
  expect(r).toEqual({ status: 'ok', model: expect.anything() }); // no `stale` — fresh path (serve-doc returns at readFreshMagazineModel)
  expect(await snapshot(ownerId)).toEqual(before); // reserve never called → nothing changed
});

// P13 — stale-then-recovered: stale served over budget; under budget it re-materializes to current version.
it('P13: recovers to fresh (no stale) once under budget', async () => {
  // writeModelEnvelope with matching titles + generatorVersion 'OLD'
  await setOwnerCap(6); await preseedBudget(ownerId, 6);
  const stale = await resolveMagazineModel({ /* … */ });
  expect(stale).toMatchObject({ status: 'ok', stale: true });
  // Clear the over-budget state (fresh day OR delete today's budget row), leaving the stale envelope:
  await svc.from('serve_owner_budget').delete().eq('owner_id', ownerId);
  const fresh = await resolveMagazineModel({ /* same args; generateMagazineModel mocked per file convention */ });
  expect(fresh.status).toBe('ok');
  expect((fresh as { stale?: boolean }).stale).toBeUndefined(); // re-materialized to current version, not stale
});
```

- [ ] **Step 6: Run — confirm pass** (`npx jest read-model && npm run test:integration -- --runInBand -t "serve-doc-materialize" && npx tsc --noEmit`).

- [ ] **Step 7: Re-assert the never-charge leaf + share invariant (P11)**

Run `npx jest import-guard` (read-model.ts must still be a leaf — `readTitleStableModel` added no forbidden import). Extend `tests/integration/share-route.test.ts`'s B18 money proof to assert, across the share serves, that `reserve_serve_model` is never called AND `serve_owner_budget` gets no row for the share owner. Run: `npm run test:integration -- --runInBand -t "share-route"`.

- [ ] **Step 8: Commit**
```bash
git add lib/html-doc/read-model.ts lib/html-doc/serve-doc.ts tests/lib/html-doc/read-model.test.ts \
  tests/integration/serve-doc-materialize.test.ts tests/integration/share-route.test.ts
git commit -m "feat(1g): title-stable serve-stale read + owner_over_budget handling in resolveMagazineModel"
```

---

## Task 3: Owner route 503 + `X-Magazine-Stale` header + `fileResponse` staleMarker

**Files:**
- Modify: `app/api/html/[id]/route.ts`, `lib/html-doc/file-response.ts`
- Test: `tests/lib/html-doc/file-response.test.ts`, `tests/integration/html-download.test.ts`

**Interfaces:**
- Consumes: `ResolveResult` `over_budget`/`stale` (Task 2).

- [ ] **Step 1: Write the failing `fileResponse` unit test** (`tests/lib/html-doc/file-response.test.ts` — add)

```ts
it('staleMarker sets X-Magazine-Stale on html; absent by default', () => {
  const on = fileResponse('<html>', { kind: 'html', download: false, base: 'b', cache: 'private, no-store', csp: 'x', staleMarker: true });
  expect(on.headers.get('X-Magazine-Stale')).toBe('1');
  const off = fileResponse('<html>', { kind: 'html', download: false, base: 'b', cache: 'private, no-store', csp: 'x' });
  expect(off.headers.get('X-Magazine-Stale')).toBeNull();
});
```

- [ ] **Step 2: Run — confirm fail** (`npx jest file-response`).

- [ ] **Step 3: Implement `staleMarker` in `file-response.ts`**

Add `staleMarker?: boolean` to the opts type; after the existing header assignments (guard on `kind === 'html'` so the "html only" invariant is enforced in code, not just by the caller — review L2):
```ts
  if (opts.staleMarker && opts.kind === 'html') headers['X-Magazine-Stale'] = '1';
```
Add a unit assertion that `staleMarker: true` with `kind: 'md'` does NOT set the header.

- [ ] **Step 4: Write the failing owner-route integration tests** (`tests/integration/html-download.test.ts` — add)

```
- P6 (route): owner over budget, no model → GET (html) returns 503 { error: 'daily refresh budget reached, try tomorrow' }.
- P5 (route): owner over budget, title-stable model exists → 200, body is the rendered magazine, header X-Magazine-Stale: 1.
- P1 (route): fresh model, owner over budget → 200, NO X-Magazine-Stale (served free).
- P7 (route): owner over budget, format=md&download=1 → 200 raw markdown, no X-Magazine-Stale (returns before resolveMagazineModel — unchanged 1F-c path).
```
Force over-budget with the cap-preseed pattern (`per_owner_serve_daily_cents` stays ≥ 6): `svc.from('guardrail_config').update({ per_owner_serve_daily_cents: 6 })` + `svc.from('serve_owner_budget').insert({ owner_id, day: <utc today>, spent_cents: 6 })`. **Do NOT set the cap to 3** (violates the CHECK). Materialize a matching-title stale model (`writeModelEnvelope` with `generatorVersion:'OLD'`) for the P5 case; use the existing owner-serve integration harness.

- [ ] **Step 5: Implement in `serveCloud`** (`app/api/html/[id]/route.ts`)

In the `resolved.status` switch add before `case 'ok'`:
```ts
    case 'over_budget': return json({ error: 'daily refresh budget reached, try tomorrow' }, 503);
```
Thread the stale marker into the final html `fileResponse` (the `title` var already exists from the 1F-c M1 fix):
```ts
    const nonce = generateNonce();
    const html = renderMagazineHtml(parsed, resolved.model, { nonce, dig: false });
    return fileResponse(html, {
      kind: 'html', download, base, title,
      cache: 'private, no-store', csp: buildSummaryCsp(nonce),
      staleMarker: resolved.stale === true,
    });
```
(After the switch, `resolved` is narrowed to `{ status: 'ok', model, stale? }`, so `resolved.stale` is in scope.)

- [ ] **Step 6: Run — confirm pass + tsc + full owner-serve regression**

Run: `npm run test:integration -- --runInBand -t "html-download" && npx jest file-response && npx tsc --noEmit && npx jest html`
Expected: PASS; existing owner-serve + 1F-c download tests still green (no header on fresh/non-stale responses; MD path unchanged).

- [ ] **Step 7: Commit**
```bash
git add "app/api/html/[id]/route.ts" lib/html-doc/file-response.ts \
  tests/lib/html-doc/file-response.test.ts tests/integration/html-download.test.ts
git commit -m "feat(1g): owner route over_budget 503 + X-Magazine-Stale on served-stale HTML"
```

---

## Verification (end of stage)

1. `npx tsc --noEmit` — 0 errors.
2. `npx jest` — full unit suite green (grows with read-model + file-response units).
3. `npx supabase db reset && npm run test:integration -- --runInBand` — all green (Tasks 1–3 integration; existing serve-model-charge / share-route / cost-guardrails suites unaffected).
4. Behaviors P1–P17 each have a covering test.
5. `npx jest import-guard` — read-model.ts still a generate-free leaf.
6. Each of Tasks 1, 2 cleared per-task dual adversarial review (Claude + Codex) with §8 iterative re-review; reviews saved to `docs/reviews/task-1g-N-<name>-{review,codex}.md`.
7. Stage-complete: `superpowers:finishing-a-development-branch` → whole-branch review → PR to `master` (`gh … --repo kujinlee/youtube-playlist-summaries-cloud`).

## Self-Review notes (author)

- **Spec coverage:** D1 (T1 table), D2 (T1 column+CHECK), D3 (T1 arbiter+definer+P17), D4 (T2 ResolveResult+case), D5 (T2 title-stable read), D6 (T3 route+header), D7 (unchanged — asserted by P7/P11), D8 (T1 config guard). **Behaviors — every P1–P17 covered:** P2/P3/P4/P4b/P8/P9/P10/P15/P16/P17 + R5 (T1, RPC-level); P5/P6/P6b/P13/P14/P11 (T2, resolve-level); P1/P5/P6/P7 (T3, route-level); P12 (T1). Note the label corrections from plan-v1 (review): the two-doc concurrency test is spec **P15** (was mislabeled P16); spec **P16** is the new live-lease→in_flight test; the K·6 test is **R5** (spec §4), not P15.
- **Over-budget test pattern (review Blocking):** NEVER set `per_owner_serve_daily_cents < magazine_est_cents` (violates the CHECK). Force over-budget via `setOwnerCap(6)` + `preseedBudget(owner, 6)` (helpers in Task 1 Step 1). Rollback tests use `snapshot()` before/after and assert full-table equality.
- **Type consistency:** `readTitleStableModel` returns `{status:'ok'|'none'}` (distinct from `readFreshMagazineModel`'s `'ok'|'not_ready'` — deliberate, different callers); `ResolveResult.ok.stale?` threaded to `fileResponse.staleMarker`. `owner_over_budget` (RPC string) → `over_budget` (ResolveResult) → 503 — three distinct names, intentional and mapped in T2/T3.
- **Confirm during execution:** the exact `read-model.test.ts` fake-blob helpers (build a minimal `ReadOnlyBlobStore` stub if absent); the `serve-config-invariant.test.ts` canonical-config shape; that `pg_proc.proconfig` renders as `['search_path=public']` in this Postgres (adjust the P17 `arrayContaining` matcher if the format differs, e.g. quoted).
