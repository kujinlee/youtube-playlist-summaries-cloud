# Stage 1G — Per-Owner Serve Budget (G1) — Design Spec

**Status:** v3 — CONVERGED (round-2 dual re-review: 0 new Blocking/High both passes; round-1 fixes verified genuine; round-2 Low wording clarified). Pending user spec-approval.
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

**Out of scope (recorded 1G follow-ups):** G2 config-drift guard, G3 storage/row GC, G4 anon rate-limit/cache, G5 version-bump staleness heal-at-mint, G6 cosmetic, G7 test-strength, G8 1D live-Gemini gate. Also out of scope: extending serve-stale to the *pure* global `at_capacity` / `attempts_exhausted` / `busy` cases for an **under-budget** owner (a broader change to already-merged 1F-a behavior — deferred). Note the reorder (D3) *does* give an **over-budget** owner serve-stale even when the global pool is also full, because per-owner is checked first and `owner_over_budget` wins. Also out of scope: a visible in-document "previous version" banner (frontend / Sub-project 2); splitting the per-owner cap by anon vs registered (single knob suffices).

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
Rationale: a dedicated single-row-per-(owner,day) counter is required for an **atomic conditional-UPDATE arbiter** (the same race-free pattern as `spend_ledger`). Deriving the per-owner sum from `serve_model_charge.attempt_count` would be a scan, not atomically enforceable. force-RLS + service_role-only mirrors `spend_ledger`/`serve_model_charge` — never client-writable. **Known consequence (review L3):** unlike `usage_counters` (which grants `select` to clients so the UI can show "X of N remaining"), `serve_owner_budget` has **no** client-read grant. This is correct for a spend-guard, but a future "daily refresh budget remaining" UX in Sub-project 2 would need a dedicated read RPC — flagged, not a defect.

### D2 — New config column (`per_owner_serve_daily_cents`)
```sql
alter table guardrail_config add column per_owner_serve_daily_cents int not null
  default 60 check (per_owner_serve_daily_cents >= magazine_est_cents);
```
Default **60¢** = 10 first-attempt materializations/day, and equals anon's existing *natural* bound (2 docs · K=5 · 6¢). One knob for all owners; tunable up if legitimate registered use needs more headroom. The `>= magazine_est_cents` CHECK guarantees at least one attempt always fits (no owner is permanently locked out by a misconfiguration). **Operational note (review L2):** this cross-column CHECK re-validates on updates to *either* column, so an admin raising `magazine_est_cents` above the current `per_owner_serve_daily_cents` will have the UPDATE rejected until the per-owner cap is raised first — order config changes accordingly (raise the per-owner cap before the per-attempt est).

### D3 — Second atomic arbiter in `reserve_serve_model` (via `create or replace`)
`reserve_serve_model` is `CREATE OR REPLACE`d in migration `0014` (Postgres functions are replaced, not altered piecemeal). **Critical (review Blocking / H2):** a same-signature `create or replace` PRESERVES the ACL (execute grants to `anon`/`authenticated`) and ownership, but `SECURITY DEFINER` and `SET search_path` are part of the *function definition* — if the replacement body omits them it silently reverts to `SECURITY INVOKER`, and the force-RLS, service_role-only tables (`serve_model_charge`, `spend_ledger`, `serve_owner_budget`) then reject every write → **every owner serve 500s**. Therefore 0014 MUST restate the complete header verbatim and re-affirm the grants (see §6), and a test MUST assert `pg_proc.prosecdef = true` + `proconfig` contains `search_path=public` + an `authenticated`/`anon` session can still execute it.

Inside the existing step-5 sub-block (the implicit savepoint that already rolls back the lease claim), run the **per-owner arbiter FIRST, then the global arbiter** (review Medium — reorder):
```sql
-- 5a. per-owner daily cap (NEW, checked FIRST) → PJ005 → 'owner_over_budget'
insert into serve_owner_budget (owner_id, day) values (v_owner, v_day) on conflict do nothing;
update serve_owner_budget set spent_cents = spent_cents + v_cfg.magazine_est_cents
  where owner_id = v_owner and day = v_day
    and spent_cents + v_cfg.magazine_est_cents <= v_cfg.per_owner_serve_daily_cents;
if not found then raise exception 'serve_owner_over_budget' using errcode = 'PJ005'; end if;

-- 5b. global daily cap (UNCHANGED logic) → PJ004 → 'at_capacity'
insert into spend_ledger (day) values (v_day) on conflict do nothing;
update spend_ledger set reserved_cents = reserved_cents + v_cfg.magazine_est_cents, updated_at = now()
  where day = v_day and reserved_cents + actual_cents + v_cfg.magazine_est_cents <= v_cfg.daily_cap_cents;
if not found then raise exception 'serve_at_capacity' using errcode = 'PJ004'; end if;
```
The exception handler gains a second arm:
```sql
exception
  when sqlstate 'PJ005' then v_result := 'owner_over_budget';
  when sqlstate 'PJ004' then v_result := 'at_capacity';
```
**Rollback:** the per-owner increment, the global increment, and the step-4 lease claim all live inside the same `begin … exception … end` sub-block, so **any** raise rolls the whole block back to the implicit savepoint — all three revert together. An `owner_over_budget` (or `at_capacity`) outcome leaves `spend_ledger`, `serve_owner_budget`, and `serve_model_charge.attempt_count` **all unchanged** — the attempt is not consumed and no pool is touched.

**Why per-owner FIRST (reorder rationale):** (1) an over-budget owner fails at 5a *without ever locking the global `spend_ledger` money row* — so a heavy/abusive owner repeatedly hitting their cap cannot contend on the shared money row and slow other tenants' valid reserves (the whole point of G1 is to isolate a heavy owner's impact; making their rejection lock-free furthers it). (2) An owner who is over BOTH their budget AND the global cap now reports `owner_over_budget` (the more actionable, self-owned signal) rather than the transient global `at_capacity` — and this is what lets serve-stale (D5) apply even in a globally-full window, where serving the free stale rendering *relieves* pool pressure. An UNDER-budget owner in a global-full window still passes 5a and correctly gets `at_capacity` at 5b (its increment rolls back). New RPC return value: **`owner_over_budget`** (added to the existing `reserved`/`in_flight`/`attempts_exhausted`/`at_capacity`/`denied`).

### D4 — Caller plumbing (`lib/html-doc/serve-doc.ts`)
`resolveMagazineModel`'s `ResolveResult` union changes:
- `{ status: 'ok'; model: MagazineModel }` → gains an optional `stale?: boolean`.
- add `{ status: 'over_budget' }`.

The `reserve_serve_model` result switch (currently `denied`/`in_flight`/`attempts_exhausted`/`at_capacity`/`reserved`/`default: throw`) gains a `case 'owner_over_budget'` **before** the `default: throw` (an unhandled status throws → 500, so this thread-through is mandatory). That case invokes the serve-stale fallback (D5).

### D5 — Serve-stale fallback (owner path, HTML only) — title-stable staleness
**Corrected per review H1 (the critical fix).** The owner route renders the **current** `parsed` markdown against `resolved.model`, and `render.ts` pairs `parsed.sections[i]` with `model.sections[i]` **by array position**. So a stale model may only be safely rendered against current markdown when the section titles still line up. If the summary's titles were edited/reordered since materialization, positional pairing would emit a current heading with a *different* section's stale lead/bullets (and drop extra current sections) — silently-wrong hybrid content. So serve-stale is gated on **titles-match** (`sameTitles`):

**Precise guarantee (review round-2 Low):** `sameTitles` compares section *headings* only, so the gate guarantees **positional coherence** (each heading is paired with the lead/bullets generated *for that same heading* — H1 is fully closed), but it does **not** prove the *body prose* under a heading is unchanged. Two staleness sub-cases pass the gate: (a) pure `GENERATOR_VERSION` bump, same source → the stale render is byte-equivalent content in an older generator style (ideal); (b) body prose edited under an unchanged heading → the stale render is *coherent* (correct heading↔lead pairing) but reflects the *older* prose. Both are honest degradations (not mismatched hybrids), signalled by `X-Magazine-Stale`; current content is always available via the MD path (D7). This is acceptable for an over-budget owner's own doc; a source-content hash to distinguish (a) from (b) is deliberately out of scope (YAGNI — the coherence property is what matters for correctness).

On `case 'owner_over_budget'`, read the cached envelope (`readModelEnvelope(principal, base, blobStore)`) and compute `sameTitles` (the same title-equality check `isFresh` uses):
- **Envelope exists AND `sameTitles` is true** (version may differ — the generator-storm case, which is exactly G1's motivation) → `return { status: 'ok', model: envelope.model, stale: true }`. The route renders current `parsed` against this model — positional pairing is correct because titles align; the only difference is the older generator's leads/bullets for the *same* sections. No charge (reserve rolled back in D3).
- **No envelope, OR `sameTitles` is false** (titles/content drifted — stale model would mis-pair) → `return { status: 'over_budget' }` → 503. Current content stays available via the MD path (D7).

This read is pure (no Gemini, no reserve, no write) and does **not** reopen the fleet-wide re-charge hole 1F-a's Option A closed (that hole was about *overwriting* stale models; here we only *read*). **Import-guard (review L1):** the gate-free read MUST stay a pure blob read — if exposed as a new helper (e.g. `readAnyMagazineModel`) it belongs in the generate-free leaf `lib/html-doc/read-model.ts` and must import nothing from gemini/charging; the 1F-b import-guard test must still pass. (`serve-doc.ts` already imports gemini, so calling `readModelEnvelope` directly from there is equally safe — implementer's choice, but the pure-read invariant is mandatory either way.)

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

- **Total spend still ≤ `daily_cap_cents`/day** — the global arbiter (now 5b) is unchanged in logic; whether it runs first or second, its increment only commits when `reserved+actual+est ≤ daily_cap`, and it rolls back on any raise in the block.
- **Per-doc K=5 bound unchanged** — step 4 lease claim is untouched.
- **No release RPC / charge-per-attempt** — unchanged; the per-owner counter only ever increments (per UTC day; a fresh day starts at 0 via the `on conflict do nothing` insert). Each of the K=5 reclaim attempts that reaches the arbiters charges the per-owner counter 6¢ (review R5 — a doc that fails K times costs the owner K·6¢, intended: attempts cost real money).
- **Atomicity / no race** — the per-owner increment uses the identical conditional-UPDATE-as-arbiter pattern; concurrent reserves for the same owner serialize on the `serve_owner_budget` row lock, so two racing attempts cannot both pass a cap they jointly exceed.
- **`owner_over_budget` consumes nothing** — full rollback (attempt, global ledger, owner ledger all revert). Because per-owner is checked first, an over-budget owner's rejected attempt never even touches the global `spend_ledger` row (no lock contention on the shared money row).
- **Share path never charges** — structurally unchanged; asserted by extending the 1F-b B18 money proof.
- **Serve-stale never charges** — it is a gate-free blob read after a rolled-back reserve.

---

## 5. Behaviors (test contract)

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| **P1** | Under budget, fresh model | owner view/serve, `spent < cap`, model fresh | 200, served free, no reserve call (existing B1) |
| **P2** | Under budget, needs materialize | fresh absent, `spent + 6 ≤ cap`, global ok | `reserved` → generate → 200; `serve_owner_budget.spent += 6`; `spend_ledger += 6` |
| **P3** | Per-owner cap blocks | `spent + 6 > per_owner_serve_daily_cents`, global has room | RPC `owner_over_budget`; **full rollback** — `serve_owner_budget`, `spend_ledger`, `serve_model_charge.attempt_count` all unchanged |
| **P4** | Over budget wins over global (reorder) | owner over budget AND global also full | RPC `owner_over_budget` (per-owner 5a checked first); full rollback; → serve-stale path (D5) applies even in a globally-full window (free stale serve relieves pool pressure) |
| **P4b** | Under budget, global full | owner under cap, global pool full | RPC `at_capacity` (passes 5a → `serve_owner_budget` +6, then fails 5b); **the 5a `serve_owner_budget` increment rolls back** (no per-owner phantom spend), attempt_count unchanged; **no** stale fallback (deferred — §2) → 503 |
| **P5** | Over budget + stale model, titles match | P3 AND envelope exists AND `sameTitles` true (title-stable stale) | 200, serve **stale** rendering (positionally coherent; may reflect older prose per D5), `X-Magazine-Stale: 1`, **no charge** |
| **P6** | Over budget + no model | P3 AND no envelope | 503 `daily refresh budget reached` |
| **P6b** | Over budget + stale model, titles DRIFTED | P3 AND envelope exists AND `sameTitles` false | 503 (NOT served stale — positional mis-pairing avoided, review H1); current content still via MD (P7) |
| **P7** | Over budget + MD download | P3, `format=md` | 200 raw markdown (never reaches reserve), no header, no charge |
| **P8** | Owner isolation | owner A at cap | owner B (under cap) unaffected — separate `serve_owner_budget` rows |
| **P9** | Daily reset | new UTC day after P3 | `serve_owner_budget` keyed on new `day` → `spent` starts 0 → owner can materialize again |
| **P10** | Cap boundary exactness | `spent = cap - 6` then one more | that attempt succeeds (`spent + 6 = cap ≤ cap`); the next is blocked |
| **P11** | Share path never reserves | share serve (fresh/stale/any) `format=md`/html | no `reserve_serve_model` call, no `serve_owner_budget` write (extend 1F-b B18 proof) |
| **P12** | Config drift guard | canonical seed check | includes `per_owner_serve_daily_cents`; guard passes |
| **P13** | Stale-then-recovered | P5 stale served, next UTC day under budget | doc re-materializes to current version, `X-Magazine-Stale` absent |
| **P14** | Fresh doc never over-budgets | model fresh, owner over cap | 200 free — resolve returns `ok` before ever calling reserve (P1 path); cap irrelevant |
| **P15** | Per-owner concurrency at the boundary (review Low) | same owner, two DIFFERENT docs, exactly one 6¢ slot left, global has room, concurrent | exactly one `reserved` + one `owner_over_budget`; `serve_owner_budget.spent` and `spend_ledger.reserved` each +6 (not +12); only the winner gets a `serve_model_charge` marker |
| **P16** | Over budget + concurrent live lease (review M2) | owner over budget AND a live lease exists for the doc (concurrent attempt) | RPC `in_flight` → resolve `busy` → 503; **no** serve-stale (step-4 can't claim the lease, so 5a/5b never run) — serve-stale is not guaranteed for every over-budget view |
| **P17** | `create or replace` preserves definer (review Blocking/H2) | after 0014 migration | `pg_proc.prosecdef = true` for `reserve_serve_model`; `proconfig` contains `search_path=public`; an `authenticated`/`anon` session can `execute` it (writes to the service_role-only tables still succeed) |

---

## 6. Files touched

- **Create:** `supabase/migrations/0014_serve_owner_budget.sql` — the `serve_owner_budget` table + force-RLS + service_role grant; the `per_owner_serve_daily_cents` config column; and `create or replace function reserve_serve_model(p_playlist_id uuid, p_video_id text) returns text language plpgsql **security definer set search_path = public** as $$…$$` restating the COMPLETE header verbatim (0012 body + the two new arbiter steps), followed by `revoke all on function reserve_serve_model(uuid, text) from public;` and `grant execute on function reserve_serve_model(uuid, text) to authenticated, anon;` restated for auditability. **Do NOT `drop function`** (same signature → replace preserves ACL + ownership). Keep 0012 immutable as shipped.
- **Modify:** `lib/html-doc/serve-doc.ts` (ResolveResult `ok` gains `stale?`, new `over_budget` variant, `owner_over_budget` case with the titles-match stale read), `lib/html-doc/read-model.ts` (if a gate-free reader is exported here it MUST stay a pure blob leaf — no gemini/charging import, 1F-b guard still green — review L1), `app/api/html/[id]/route.ts` (over_budget → 503, `X-Magazine-Stale` on stale HTML), `lib/html-doc/file-response.ts` (optional `staleMarker?: boolean` opt, html kind only).
- **Tests:** migration/RPC integration for P2–P16; **P17 definer-preservation** (assert `prosecdef`/`proconfig search_path`/anon-executable after 0014); unit for the titles-match stale-read fallback + fileResponse stale header; extend the 1F-b B18 money proof that the share path still never calls `reserve_serve_model` (P11); config drift guard includes the new column (P12).

---

## 7. Risk log

**Resolved in v2 (round-1 dual review, Codex + Claude):**
- **R1 (was Blocking/H2) → RESOLVED** — `create or replace` preserves ACL + ownership, but NOT `security definer`/`search_path`; 0014 restates the complete header verbatim + re-grants (§6, D3) and P17 tests `prosecdef`/`proconfig`/anon-executable.
- **R2 (was High/H1) → RESOLVED** — serve-stale gated on titles-match (version-only staleness, D5); titles-drifted → 503 (P6b), never a positional mis-pair.
- **Reorder (was Medium) → ADOPTED** — per-owner arbiter checked first (D3): over-budget owners don't lock the global money row, and `owner_over_budget` wins over `at_capacity` so serve-stale applies in a globally-full window (P4). Resolves the "global at_capacity suppresses serve-stale" concern.
- **R5 (K·6¢ per-attempt charge) → CONFIRMED intended** — §4 + P16 document it; a doc failing K times costs the owner K·6¢.

**Accepted design choices (remaining, non-blocking):**
- **R3** — `X-Magazine-Stale` is a header only, lost once an `.html` file is saved. Accepted as a backend signal; a visible in-document "previous version" banner is a frontend / Sub-project 2 follow-up.
- **R4** — Default 60¢ = 10 materializations/day. During a `GENERATOR_VERSION` storm a heavy owner re-materializes ≤10 docs/day, serving title-stable-stale meanwhile (P5). Tunable if legitimate registered use needs more.
