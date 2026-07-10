# Stage 1G — Per-Owner Serve Budget (G1) — Design Spec

**Status:** draft (pending dual-adversarial review → user approval)
**Date:** 2026-07-10 · **Branch:** `feat/stage-1g-per-owner-serve-budget` (off master @ 4052c7d, after 1F-c PR #9)
**Scope:** ONE item from the Stage 1G backlog — G1, the registered-account serve residual. G2–G8 remain a separate prioritized backlog.

---

## 1. Problem

The cloud cost-control model (Stages 1D + 1F-a) has three mechanisms:

1. **Global shared daily cap** — `spend_ledger` is **one row per UTC day** (`guardrail_config.daily_cap_cents = 500` = $5/day). BOTH enqueue reservations (`summary_est_cents = 150`/job) AND serve-model charges (`magazine_est_cents = 6`/attempt) reserve against this single shared pool via a conditional-UPDATE arbiter. Full pool → enqueues get `daily_cap_exceeded` (PJ002), serves get `at_capacity` (PJ004).
2. **Per-owner monthly enqueue quota** — `usage_counters` + `quota_allowance` (registered summary = 20/mo, anon = 2/mo). Bounds *jobs*, not serves.
3. **Serve charge** — `reserve_serve_model` (0012): 6¢/attempt, bounded by **K=5 attempts per `(owner, doc, UTC-day)`** (`max_serve_attempts`). **No per-owner cross-doc bound.**

**The gap (G1):** the K=5 bound is *per-doc*. Anonymous owners are naturally bounded (≤2 docs → ≤ 2·5·6 = 60¢/day of serve residual). **Registered owners accumulate unbounded docs** (20/mo, persisting for months), so one registered owner serving/re-materializing ~17 of their own docs (`500 ÷ 30`) can consume the **entire shared daily cap**, starving every other tenant's enqueues *and* serves. A `GENERATOR_VERSION` bump amplifies this: it invalidates every cached model, so a heavy owner's subsequent views re-charge en masse.

This is a per-owner **fairness** hole in the shared pool — the 500¢ cap still bounds *total* spend, but nothing bounds any *single owner's share* of it.

**Invariant this spec adds:** *No single owner can consume more than a fixed per-owner slice of the shared daily serve pool.*

---

## 2. Scope (approved decisions)

| # | Decision | Choice |
|---|---|---|
| **S1** | What the budget covers | **Serve-only.** Enqueue is already per-owner monthly-quota-bounded; leave it unchanged. |
| **S2** | Bound shape | **Per-owner cents/day cap** (cents-consistent with the whole existing money model). |
| **S3** | Status when per-owner cap blocks | **New distinct status `owner_over_budget`** (owner's own doc → no cross-tenant leak; honest UX). |
| **S4** | Graceful degradation | **Serve-stale on `over_budget` only** (owner path, HTML only): when over budget and a previously-materialized model exists, serve that stale rendering instead of failing. |

**Out of scope (recorded 1G follow-ups):** G2 config-drift guard, G3 storage/row GC, G4 anon rate-limit/cache, G5 version-bump staleness heal-at-mint, G6 cosmetic, G7 test-strength, G8 1D live-Gemini gate. Also out of scope: extending serve-stale to global `at_capacity` / `attempts_exhausted` / `busy` (a broader change to already-merged 1F-a behavior — deferred); a visible in-document "previous version" banner (frontend / Sub-project 2); splitting the per-owner cap by anon vs registered (single knob suffices).

---

## 3. Design decisions

### D1 — New per-owner counter table (`serve_owner_budget`)
The per-owner analog of the global `spend_ledger`. Migration `0014_serve_owner_budget.sql`:
```sql
create table serve_owner_budget (
  owner_id uuid not null references profiles(id) on delete cascade,
  day date not null,                                  -- (now() at time zone 'utc')::date
  spent_cents int not null default 0 check (spent_cents >= 0),
  primary key (owner_id, day));
alter table serve_owner_budget enable row level security;
alter table serve_owner_budget force row level security;   -- writable only inside the definer RPC
grant select, insert, update, delete on serve_owner_budget to service_role;   -- no anon/authenticated policy
```
Rationale: a dedicated single-row-per-(owner,day) counter is required for an **atomic conditional-UPDATE arbiter** (the same race-free pattern as `spend_ledger`). Deriving the per-owner sum from `serve_model_charge.attempt_count` would be a scan, not atomically enforceable. force-RLS + service_role-only mirrors `spend_ledger`/`serve_model_charge` — never client-writable.

### D2 — New config column (`per_owner_serve_daily_cents`)
```sql
alter table guardrail_config add column per_owner_serve_daily_cents int not null
  default 60 check (per_owner_serve_daily_cents >= magazine_est_cents);
```
Default **60¢** = 10 first-attempt materializations/day, and equals anon's existing *natural* bound (2 docs · K=5 · 6¢). One knob for all owners; tunable up if legitimate registered use needs more headroom. The `>= magazine_est_cents` CHECK guarantees at least one attempt always fits (no owner is permanently locked out by a misconfiguration).

### D3 — Second atomic arbiter in `reserve_serve_model`
Inside the existing step-5 sub-block (the implicit savepoint that already rolls back the lease claim on `at_capacity`), **after** the global-cap arbiter, add a per-owner arbiter:
```sql
-- 5a. global daily cap (UNCHANGED) → PJ004 → 'at_capacity'
insert into spend_ledger (day) values (v_day) on conflict do nothing;
update spend_ledger set reserved_cents = reserved_cents + v_cfg.magazine_est_cents, updated_at = now()
  where day = v_day and reserved_cents + actual_cents + v_cfg.magazine_est_cents <= v_cfg.daily_cap_cents;
if not found then raise exception 'serve_at_capacity' using errcode = 'PJ004'; end if;

-- 5b. per-owner daily cap (NEW) → PJ005 → 'owner_over_budget'
insert into serve_owner_budget (owner_id, day) values (v_owner, v_day) on conflict do nothing;
update serve_owner_budget set spent_cents = spent_cents + v_cfg.magazine_est_cents
  where owner_id = v_owner and day = v_day
    and spent_cents + v_cfg.magazine_est_cents <= v_cfg.per_owner_serve_daily_cents;
if not found then raise exception 'serve_owner_over_budget' using errcode = 'PJ005'; end if;
```
The exception handler gains a second arm:
```sql
exception
  when sqlstate 'PJ004' then v_result := 'at_capacity';
  when sqlstate 'PJ005' then v_result := 'owner_over_budget';
```
**Ordering & rollback:** both arbiters and the step-4 lease claim live inside the same `begin … exception … end` sub-block, so **any** raise rolls the whole block back to the implicit savepoint — the lease claim (attempt_count increment), the global-ledger increment, and the per-owner increment all revert together. Consequence: an `owner_over_budget` outcome leaves `spend_ledger`, `serve_owner_budget`, and `serve_model_charge.attempt_count` **all unchanged** — the attempt is not consumed and the global pool is not touched. Global cap is checked first (5a before 5b): a genuinely global-full pool reports `at_capacity` even for an owner who is also over budget, which is the more actionable signal (the whole system is full, not just them). New RPC return value: **`owner_over_budget`** (in addition to the existing `reserved`/`in_flight`/`attempts_exhausted`/`at_capacity`/`denied`).

### D4 — Caller plumbing (`lib/html-doc/serve-doc.ts`)
`resolveMagazineModel`'s `ResolveResult` union changes:
- `{ status: 'ok'; model: MagazineModel }` → gains an optional `stale?: boolean`.
- add `{ status: 'over_budget' }`.

The `reserve_serve_model` result switch (currently `denied`/`in_flight`/`attempts_exhausted`/`at_capacity`/`reserved`/`default: throw`) gains a `case 'owner_over_budget'` **before** the `default: throw` (an unhandled status throws → 500, so this thread-through is mandatory). That case invokes the serve-stale fallback (D5).

### D5 — Serve-stale fallback (owner path, HTML only)
On `case 'owner_over_budget'`, perform a **gate-free** read of the cached model envelope — the same `readModelEnvelope(principal, base, blobStore)` that `readFreshMagazineModel` wraps, **without** the `isFresh` (version + titles) gate:
- **Envelope exists** → `return { status: 'ok', model: envelope.model, stale: true }`. The route renders and serves it (no charge — the reserve rolled back in D3).
- **No envelope** (never materialized) → `return { status: 'over_budget' }`.

"Stale" = the last-materialized model, whether staleness is `GENERATOR_VERSION`-driven or titles/content-driven (`isFresh` checks both). The served rendering reflects the doc's state when it was last materialized; current content remains available via the MD path (D7). This read is pure (no Gemini, no reserve, no write) and does **not** reopen the fleet-wide re-charge hole 1F-a's Option A closed (that hole was about *overwriting* stale models; here we only *read*).

### D6 — Route mapping (`app/api/html/[id]/route.ts`, owner serve/download)
- `resolved.status === 'ok'` and `resolved.stale === true` → serve as normal **plus** a response header **`X-Magazine-Stale: 1`** on the HTML response (both view and `format=html` download). Applies to the HTML path only.
- `resolved.status === 'over_budget'` → `return json({ error: 'daily refresh budget reached, try tomorrow' }, 503)` (honest message; owner's own doc → no leak).
- The `X-Magazine-Stale` header is threaded through `fileResponse` (1F-c) — `fileResponse` gains an optional `staleMarker?: boolean` opt (html kind only) rather than the route mutating a built Response.

### D7 — MD path and share path unaffected
- **MD download** (`format=md`) returns before `resolveMagazineModel` — pure blob passthrough, never charges, no "stale model" concept. An over-budget owner can always download the raw markdown of any promoted doc. **Unchanged.**
- **Share path** (`app/s/[token]`, `readFreshMagazineModel`) **never calls `reserve_serve_model`** — the never-charge invariant (1F-b) is preserved and `owner_over_budget` / serve-stale can never appear there. Share stays fresh-or-not-ready. **Unchanged.**

### D8 — Config-invariant guard
The canonical-seed / cap-soundness guard (`tests/**/cost-guardrails*.test.ts`, `lib/clients.ts ensureGuardrailHeadroom` if it enumerates columns) must include `per_owner_serve_daily_cents` in the canonical `guardrail_config` seed so the drift guard doesn't false-negative on the new column.

---

## 4. Money invariants preserved (must hold post-change)

- **Total spend still ≤ `daily_cap_cents`/day** — the global arbiter (5a) is unchanged and runs first.
- **Per-doc K=5 bound unchanged** — step 4 lease claim is untouched.
- **No release RPC / charge-per-attempt** — unchanged; the per-owner counter only ever increments (per UTC day; a fresh day starts at 0 via the `on conflict do nothing` insert).
- **Atomicity / no race** — the per-owner increment uses the identical conditional-UPDATE-as-arbiter pattern; concurrent reserves for the same owner serialize on the `serve_owner_budget` row lock, so two racing attempts cannot both pass a cap they jointly exceed.
- **`owner_over_budget` consumes nothing** — full rollback (attempt, global ledger, owner ledger all revert).
- **Share path never charges** — structurally unchanged; asserted by extending the 1F-b B18 money proof.
- **Serve-stale never charges** — it is a gate-free blob read after a rolled-back reserve.

---

## 5. Behaviors (test contract)

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| **P1** | Under budget, fresh model | owner view/serve, `spent < cap`, model fresh | 200, served free, no reserve call (existing B1) |
| **P2** | Under budget, needs materialize | fresh absent, `spent + 6 ≤ cap`, global ok | `reserved` → generate → 200; `serve_owner_budget.spent += 6`; `spend_ledger += 6` |
| **P3** | Per-owner cap blocks | `spent + 6 > per_owner_serve_daily_cents`, global has room | RPC `owner_over_budget`; **full rollback** — `serve_owner_budget`, `spend_ledger`, `serve_model_charge.attempt_count` all unchanged |
| **P4** | Global cap blocks first | global full AND owner also over | RPC `at_capacity` (5a before 5b); rollback |
| **P5** | Over budget + stale model exists | P3 AND `readModelEnvelope` returns an envelope | 200, serve **stale** rendering, `X-Magazine-Stale: 1`, **no charge** |
| **P6** | Over budget + no model | P3 AND no envelope | 503 `daily refresh budget reached` |
| **P7** | Over budget + MD download | P3, `format=md` | 200 raw markdown (never reaches reserve), no header, no charge |
| **P8** | Owner isolation | owner A at cap | owner B (under cap) unaffected — separate `serve_owner_budget` rows |
| **P9** | Daily reset | new UTC day after P3 | `serve_owner_budget` keyed on new `day` → `spent` starts 0 → owner can materialize again |
| **P10** | Cap boundary exactness | `spent = cap - 6` then one more | that attempt succeeds (`spent + 6 = cap ≤ cap`); the next is blocked |
| **P11** | Share path never reserves | share serve (fresh/stale/any) `format=md`/html | no `reserve_serve_model` call, no `serve_owner_budget` write (extend 1F-b B18 proof) |
| **P12** | Config drift guard | canonical seed check | includes `per_owner_serve_daily_cents`; guard passes |
| **P13** | Stale-then-recovered | P5 stale served, next UTC day under budget | doc re-materializes to current version, `X-Magazine-Stale` absent |
| **P14** | Fresh doc never over-budgets | model fresh, owner over cap | 200 free — resolve returns `ok` before ever calling reserve (P1 path); cap irrelevant |

---

## 6. Files touched

- **Create:** `supabase/migrations/0014_serve_owner_budget.sql`
- **Modify:** `supabase/migrations/0012_serve_model_charge.sql`? **No** — new migration only; `reserve_serve_model` is `CREATE OR REPLACE`d in `0014` (Postgres functions are replaced, not altered in place; keep 0012 immutable as shipped). `0014` adds the table + config column + `create or replace function reserve_serve_model`.
- **Modify:** `lib/html-doc/serve-doc.ts` (ResolveResult + `owner_over_budget` case + stale read), `lib/html-doc/read-model.ts` (export a gate-free `readAnyMagazineModel` or reuse `readModelEnvelope` directly — implementer's call), `app/api/html/[id]/route.ts` (over_budget 503 + stale header), `lib/html-doc/file-response.ts` (optional `staleMarker` opt).
- **Tests:** RPC/integration for P2–P13; unit for the stale-read fallback + fileResponse stale header; extend the 1F-b B18 money proof (P11); config guard (P12).

---

## 7. Open questions / risks for adversarial review

- **R1** — Is `create or replace function reserve_serve_model` in `0014` the right mechanism vs a fresh function name? (Signature is unchanged; replace preserves grants — verify grants survive `create or replace`.)
- **R2** — `readModelEnvelope` gate-free read: does the envelope always carry a renderable `model` even when stale by titles (content changed)? Confirm the stale model is structurally valid to render (it was a prior successful materialization).
- **R3** — Header on downloads: `X-Magazine-Stale` is lost once an `.html` file is saved. Accept as backend signal only; visible banner deferred to frontend.
- **R4** — Cap default 60¢ vs registered legitimate use: is 10 materializations/day too tight for a power user during a `GENERATOR_VERSION` storm? (Tunable; storm re-materializes ≤10 docs/day, stale served meanwhile via D5 — acceptable.)
- **R5** — Interaction with the K=5 lease reclaim: on a reclaim (attempt 2..5), 5b still charges the per-owner counter each attempt — confirm a doc that fails K times counts K·6¢ against the owner budget (intended: attempts cost real money).
