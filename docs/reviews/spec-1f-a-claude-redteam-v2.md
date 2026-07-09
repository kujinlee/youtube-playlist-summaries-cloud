# Stage 1F-a — Claude Red-Team Review (v2, post-lazy-pivot independent adversarial pass)

**Spec:** `docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md` (v2 — lazy pivot)
**Reviewer mandate:** actively BREAK the v2 safety claims — daily-cap gate, owner-scoped cost bound,
session-client feasibility of the write+reserve path, local parity, drift gating. Default to "breakable."
**Codex status:** Codex CLI unavailable in this sandbox — this is a Claude adversarial pass standing in for
the Codex round (per `docs/plugins.md` fallback). **Re-attempt the Codex-specific pass before merge.**

**Severity counts:** Blocking 1 · High 2 · Medium 2 · Low 3

Each finding is a concrete failure sequence (or a precise reason it holds), tagged **INTENT/DESIGN**
(needs a product/architecture decision) or **CORRECTNESS** (a fix that doesn't change intent).

---

## BLOCKING

### B-1 — The serve-side daily-cap gate is INFEASIBLE on the mandated session/anon client, and the only two fixes are both explicitly foreclosed by the spec (§4.2 "no migration" + D5 "never service-role"). [INTENT/DESIGN + CORRECTNESS]

**Claim attacked:** D5 ("session/anon-scoped client; **never service-role**"), D10 / §4.1 step 5 / §4.2
("before the call, **reserve** a fixed approximate estimate **against the daily cap (`spend_ledger`)**;
refuse with 503 if the day is over budget"), plus §4.2 ("**no migration**") and B6/B20.

**Ground truth in the schema (`supabase/migrations/0011_cost_guardrails.sql`):**

```
grant select, insert, update, delete on spend_ledger to service_role;   -- no client access (global infra)
...
alter table spend_ledger  enable row level security; alter table spend_ledger  force row level security;
alter table guardrail_config ... force row level security;
grant select, insert, update, delete on guardrail_config to service_role;   -- no client access
```

`spend_ledger` and `guardrail_config` have **RLS forced** and **NO policy for `authenticated`/`anon`** —
only `service_role` grants. Every spend RPC (`enqueue_job`, `enqueue_preflight`) is `security invoker`
with `grant execute ... to service_role` **only** (0011:137-138, 195-196), and each opens with
`if auth.role() <> 'service_role' then raise exception 'server only'`.

**Therefore, on the serve path with a session/anon client (D5):**
1. It **cannot read `guardrail_config.daily_cap_cents`** → cannot "check the daily cap."
2. It **cannot read or write `spend_ledger`** → cannot reserve or detect over-budget.
3. It **cannot call `enqueue_job`/`enqueue_preflight`** (service_role-gated, and they'd insert a job anyway).

So B6 ("daily cap reached → 503, no Gemini call, no partial promote") is **unimplementable as written**,
and it is in direct tension with B20 ("service-role never on the serve path"): you cannot honor the
daily-cap gate *and* keep service-role off the serve path *and* add no migration.

**The two escape hatches the spec forecloses:**
- **(a) Use a service_role client for the reservation.** Violates D5 and reopens the Stage-1D
  service-confinement gate that B20 exists to test. A `service_role` key on a public GET route (anon-
  reachable) is exactly the surface 1D confined; unacceptable.
- **(b) Add a `SECURITY DEFINER` RPC** (e.g. `reserve_serve_spend(p_est int)`) granted to
  `authenticated, anon`, that internally checks+reserves against `spend_ledger` while *called by the
  session client*. This is the clean design — **but it is a migration**, contradicting §4.2's flat
  "no migration," and it needs its own RLS/definer-safety review (it must be owner-agnostic, must not
  leak the cap, must be the sole writer). The spec neither specifies it nor budgets for it.

**Impact:** The central money-path mechanism of the whole slice has no valid implementation under the
stated constraints. Either the "never service-role" invariant, the "no migration" claim, or the daily-cap
gate itself must give — this is a genuine design contradiction, not a wording nit.

**Fix (decision required):** Adopt (b) explicitly — specify a `SECURITY DEFINER` reservation RPC
(check + atomic reserve, see H-2), grant it to `authenticated, anon`, and **retract §4.2's "no migration"**
(1F-a *does* ship a migration for the serve-side reservation). Keep the session client for all reads/blob
writes; the DEFINER RPC is the *only* thing that touches `spend_ledger`, so B20's "session client only for
the bundle" still holds (the RPC is not a service_role *client*). State this in D5/D10 so the "never
service-role" and "no migration" claims are corrected rather than silently violated at build time.

---

## HIGH

### H-1 — The reservation and the Gemini call are NOT deduplicated per doc: concurrent first-views and reload-on-miss each reserve+charge, so one doc can be materialized (and billed) N times — directly breaking re-review trigger #1's "concurrent misses cannot double-charge beyond the accepted approximate model." [CORRECTNESS + INTENT/DESIGN]

**Claim attacked:** D10 ("owner-scoped … cached-after-first-view makes exposure small"), B7 ("idempotent
stage→promote; last-writer-wins … both serve 200"), §8 trigger-1 ("concurrent misses cannot double-charge
beyond the accepted approximate model").

**Why B7 is a fig leaf for cost:** B7 only makes the **blob** idempotent (last-writer-wins on an equivalent
model). It says nothing about the **reservation** or the **Gemini call** — and there is no advisory lock,
no "generating" marker, no job-row dedup on the serve path (unlike `enqueue_job`, whose partial unique
index joins duplicate work). So:

**Concrete sequence A (concurrency):**
1. Owner opens the same un-materialized doc in two tabs simultaneously (or a client prefetch + click).
2. Both requests miss the model, both pass the cap check, **both reserve `est`** (2× against the cap),
   **both call `generateMagazineModel`** (2 paid passes), both stage→promote (one wins; B7's "equivalence"
   holds for the blob only). Net: **one doc, two charges, two Gemini calls.** N tabs → N charges.

**Concrete sequence B (reload / failure — worse, unbounded per doc):**
1. Owner opens an un-materialized doc. The synchronous generate is slow (D13: client waits) or Gemini
   returns a transient 5xx / the promote fails.
2. The model blob is still absent, so the owner reloads. **Every reload is a fresh miss → a fresh
   reservation → a fresh Gemini call.** Nothing dedups it and nothing joins it.
3. Because D10 removes the per-account quota debit **and** the serve path has **no velocity limit**
   (velocity is enqueue-only, `enqueue_preflight`), a single anon owner can reload a stuck/failing doc
   arbitrarily and **drain the entire global daily cap to zero** — a demo-wide denial of service that the
   "you only materialize your own docs" bound does not stop.

**Compounding: reservation is never released** (D10 mirrors 1D's "reconcile deferred; never released").
On `enqueue_job` that is safe because the job row dedups and the work runs once. On the serve path there is
no such dedup, so every failed/duplicated attempt **permanently** consumes cap budget with zero successful
output. A burst of transient Gemini failures during a launch spike can exhaust the day's cap without
serving a single doc.

**This is exactly what §8 trigger-1 tells the reviewer to verify cannot happen — and it can.** The "you
only materialize your own quota-bounded docs (2 for anon, 20 registered)" bound holds only if each doc
materializes **exactly once**; concurrency and reload break "exactly once," so the per-owner ceiling is not
a real spend ceiling.

**Fix (decision required):** Give the serve materialization a single-flight / dedup story before it is
called safe. Options, cheapest first: (a) make the DEFINER reservation RPC also record an in-flight marker
keyed by `(owner_id, playlist_id, base)` with a short TTL so concurrent/rapid re-requests **join** instead
of re-reserving (mirror the `enqueue_job` join semantics on the serve path); (b) a Postgres advisory lock
on the `base` for the generate window; (c) at minimum, a serve-path velocity/velocity-by-owner limit so a
reload loop cannot drain the global cap, and **release the reservation on generation failure** so failures
don't permanently burn budget. Add explicit behavior rows for "second concurrent first-view joins (no
second charge)" and "reload during generation does not re-charge."

### H-2 — The reservation must be a single atomic conditional UPDATE (the `enqueue_job` arbiter pattern); the spec's "check the cap … then reserve" prose (§4.1 step 5) reads as a two-step read-then-write that a burst bypasses entirely. [CORRECTNESS]

**Claim attacked:** §4.1 step 5 ("**check** the daily cap (over budget → 503); **reserve** the fixed
approximate estimate"), the "approximate spend is genuinely bounded" premise of trigger-1.

**The trap:** §4.1 phrases the gate as *check* (a SELECT of the ledger vs cap) **then** *reserve* (an UPDATE).
If implemented literally as two statements, a burst of concurrent misses all execute the SELECT, all see
`spent < cap`, all proceed to the UPDATE — and the **global** daily cap is blown past by up to (concurrency
× est), regardless of owner-scoping. Given synchronous generate-on-miss and no serve-path concurrency limit,
the overrun is bounded only by how many requests land inside the check-window — i.e. **not usefully
bounded**. This is the difference between "approximate reservation" (accepted: est ≈ actual ± a bit) and
"unbounded concurrent overrun" (not accepted). The spec conflates the two.

**The working precedent already exists** in `enqueue_job` (0011:112-115):

```
insert into spend_ledger (day) values (v_day) on conflict do nothing;
update spend_ledger set reserved_cents = reserved_cents + v_est, updated_at = now()
  where day = v_day and reserved_cents + actual_cents + v_est <= v_cfg.daily_cap_cents;
if not found then raise exception 'daily_cap_exceeded'; end if;
```

The **conditional UPDATE is the arbiter** — the row lock serializes concurrent reservations and the WHERE
clause is the ceiling, so the total can never exceed `daily_cap_cents` no matter the concurrency. **As long
as the serve reservation is implemented this way (inside the B-1 DEFINER RPC), attack #1's global overrun
does NOT occur** — the overrun is bounded to at most one in-flight `est` over the cap per successful
reservation, which is the accepted approximation. As written ("check … reserve"), the spec invites the racy
two-step and must be corrected to mandate the atomic pattern with the UPDATE as the sole arbiter (no prior
SELECT gate that a caller could act on).

**Fix:** In §4.1/§4.2 replace "check … then reserve" with "**atomically reserve-or-refuse** via a single
conditional UPDATE (the `enqueue_job` pattern); a prior SELECT is advisory only and must not be the gate."
Add a concurrency behavior row asserting total reserved never exceeds the cap under N simultaneous misses.

---

## MEDIUM

### M-1 — Title-only drift guard serves a semantically-STALE model: if the summary MD body changes but section titles don't, `sourceSections` still matches and the stale leads/bullets are served silently. [CORRECTNESS/DESIGN]

**Claim attacked:** D8 / B3 (drift-gated re-materialization heals staleness), Success-Criterion 2.

`sourceSections` is captured as **section titles only** (`generate.ts:52`:
`parsed.sections.map((s) => s.title)`), and the drift check compares titles (§4.1 step 5). The magazine
model's `{lead, bullets}` are derived from each section's **prose**, not its title. So a summary whose
**body** is rewritten under the **same base name with unchanged titles** passes the drift guard and serves a
model built against the old prose — mismatched leads/bullets with no visible signal. In today's cloud this
is low-likelihood (the worker writes the MD once and there's no in-place MD edit), but it becomes reachable
the moment any resummarize/DocVersion-minor path reuses the base name with stable titles — and §9 leaves
"whole-doc resummarize" adjacent to this slice, so the coupling is real. The renderer is re-run fresh each
serve (D4), so *renderer* staleness is genuinely handled; it's the *model↔MD content* drift that the
titles-only guard misses.

**Fix:** Either (a) hash the section **prose** (or the whole MD) into the envelope and drift-check on that,
not just titles; or (b) state explicitly that in cloud the MD is immutable per base and a body change always
implies a new base (so titles-only is sufficient) — and add a test pinning that assumption. Don't leave the
guard silently weaker than "drift-gated" implies.

### M-2 — `renderMagazineHtml` / `generateMagazineModel` optional-opts defaults are unspecified; a wrong default (`dig` defaulting off, or caps applied when absent) silently regresses the local path. [CORRECTNESS]

**Claim attacked:** D4/D11/D12/§4.2 ("the local caller must keep working unchanged"; B21 local parity).

The refactor adds optional params to two shared functions. Local parity holds **only if the absent-opts
default reproduces today's behavior**, and the spec never pins the defaults:
- `renderMagazineHtml(parsed, model, opts?)`: local (`generate.ts:57`) calls it with **no opts** and today
  emits **dig controls**. If the implementer makes `dig` default to `false` (matching the cloud D12 call
  site) instead of `true`, **local loses its dig controls** — a silent regression B21 must catch. The
  no-opts default must be `dig: true, nonce: undefined`.
- `generateMagazineModel(sections, language, caps?)`: local (`generate.ts:39`) passes **no caps** and today
  sets no `maxOutputTokens`/`thinkingBudget`. Parity holds **iff** `caps` is optional and absent ⇒ current
  behavior. This holds as long as the third param is optional — but the spec should say so, because a
  non-optional caps param would break the local call site at compile time and a defaulted-to-CLOUD_CAPS
  value would change local cost/latency.

**Fix:** State the absent-opts defaults explicitly (`dig:true`, `nonce:undefined`, `caps:undefined ⇒
current behavior`) and make B21 assert the local render still emits dig controls and the print listener,
byte-for-byte against the post-D11 local baseline.

---

## LOW

### L-1 — The envelope carries no model-generator version; a change to the magazine prompt/schema won't invalidate cached models, so post-change views serve old-shaped models (matches the local limitation, but worth pinning). [CORRECTNESS]
The envelope is `{sourceMd, generatedAt, sourceSections, model}` — no `modelVersion`. Only `sourceSections`
(titles) gates re-materialization. If `generateMagazineModel`'s schema evolves (new fields, changed bullet
shape), every cached model stays valid-by-drift and is fed to the new renderer. If the serve path validates
`.model` **strictly** against the current `MagazineModelSchema` (recommended in v1 M-2) an old shape is
rejected → treated as absent → regenerated, which is fine. If validation is lenient, `render.ts` reads
`m.lead`/`m.bullets` off a stale shape and renders `undefined`/mismatched content. Pin: validate strictly,
or add a `modelVersion` to the envelope and drift on it too. `GENERATOR_VERSION` (renderer) staleness is
genuinely a non-issue (HTML re-rendered every serve, D4) — the gap is model-generator versioning only.

### L-2 — `default-src 'none'` + no `connect-src` is safe for the summary today only because `NAV_SCRIPT` early-returns without `outputFolder`; it is fragile and will break the moment dig serving (1F-c) lands. [CORRECTNESS/forward-risk]
The summary render has no `<img>` and no inline `style=""` attributes, so `default-src 'none'` with a
nonce'd `<style>`/`<script>` does not break the FOUC theme script or theming — that claim **holds**. But if
`NAV_SCRIPT` is still emitted under `dig:false`, it contains `fetch('/api/videos/.../dig-state?...')`; under
cloud it early-returns because `outputFolder` is absent (`nav.ts:212`), so no request is blocked *now*. When
1F-c wires dig serving, that `fetch`/`EventSource` will be silently blocked by `default-src 'none'` with no
`connect-src`. Either omit `NAV_SCRIPT` entirely under `dig:false` (cleaner) or document that `connect-src`
must be added when dig serving arrives. Not a 1F-a defect; a landmine for the next slice.

### L-3 — Serve-path model write feasibility HOLDS as a session client — call it out so the plan doesn't defensively add service-role for the blob write. [reason it holds]
Attack #3's "the serve path must WRITE" splits: the **blob** write (stage→promote the model) is feasible as
a session client — `storage.objects` policy `artifacts_owner_rw` is `for all to authenticated, anon` with
`with check split_part(name,'/',1)=auth.uid()::text` (0007:12-15), the key is server-constructed
`{owner_id}/{playlist_key}/{key}` (`supabase-blob-store.ts:10-13`) with the owner segment from `auth.uid()`,
and `promote`'s move=copy+delete stays under the owner prefix (0007 RLS covers insert+delete for the owner).
So the owner genuinely can write/promote their own model blob with no service-role. The infeasibility is
**only** the spend reservation (B-1), not the blob write — keep them separate so the fix for B-1 doesn't
drag service-role onto the blob path.

---

## Claims that genuinely HOLD (so the plan doesn't over-fix)

- **Cross-owner / unauth isolation holds** on the session-client path: RLS `playlists_owner` + `videos_owner`
  (0002) + `storage.objects` first-segment `= auth.uid()` (0007) confine every row and blob read to the
  owner; a foreign/absent `playlistId` yields no row ⇒ identical 404 (no existence leak, B10); the anon
  *session* uid is a real `auth.uid()`, so the `anon` storage policy isolates it identically (B9). This is
  the v2 spec's strongest area and needs no further hardening beyond keeping the session client throughout.
- **Path traversal holds:** `assertLogicalKey` rejects `..`/absolute/null and the key is server-constructed;
  the client supplies only `playlistId`+`videoId` and cannot forge another owner's prefix.
- **The v2 lazy pivot genuinely dissolves the v1 Blockers (B-1/B-2/H-1 backfill+heal dead-ends):** because a
  missing/stale model is regenerated **on view** (D8), pre-1F-a docs and lost/corrupt models self-heal with
  no worker change and no migration for the *model* itself. This is a real, correct resolution — do not
  re-litigate it.
- **D6's revised stance holds:** dropping the non-implementable video-row owner assert and relying on RLS +
  the implementable playlist-row assert (the `getWorkerStorageBundle` pattern minus service_role) is the
  correct fix for v1 M-3/H-1.
- **Committed-vs-404 (v1 H-2/H-3) is resolved:** step 4 now reads `artifacts.summaryMd.status` and branches
  promoted / committed→503 / absent→404. `Cache-Control: private, no-store` (v1 H-5) and the UUID
  pre-validation→400 (v1 H-4) are both now present.
- **Print button under strict CSP (v1 B-3) is resolved by D11** (nonce'd `addEventListener`, listener emitted
  unconditionally for local); the FOUC theme head script runs fine under a nonce'd `script-src` — no
  `unsafe-*` needed. Parity risk is contained to M-2's default-pinning.
- **Renderer (`GENERATOR_VERSION`) staleness is a non-issue:** D4's render-fresh-every-serve removes it.

---

## Codex gap

Codex CLI is unavailable in this sandbox; per `docs/plugins.md` this Claude adversarial pass stands in for
the Codex round. **The Codex-specific v2 pass must be re-attempted before merge** (frontier-model sync +
one run), especially against B-1 (schema/grant feasibility) and H-1/H-2 (concurrency + reservation
semantics) — the money-path findings most worth a second independent engine.

---

## Recommended spec edits before implementation

1. **Resolve B-1:** specify a `SECURITY DEFINER` serve-reservation RPC granted to `authenticated, anon`
   (the only writer of `spend_ledger` from the serve path), and **retract §4.2's "no migration"** — 1F-a
   ships one. Correct D5/D10 so "never service-role" and "no migration" are not both claimed.
2. **Resolve H-1:** add single-flight/dedup + a serve-path velocity bound + release-on-failure so concurrent
   views and reloads cannot re-charge or drain the global cap; add the two dedup behavior rows.
3. **Resolve H-2:** mandate the atomic conditional-UPDATE reservation (the `enqueue_job` arbiter); forbid a
   read-then-write gate; add the "N concurrent misses never exceed the cap" behavior row.
4. **M-1:** drift on MD-body content (or pin MD-immutability-per-base with a test), not titles alone.
5. **M-2:** pin absent-opts defaults (`dig:true`, `nonce:undefined`, `caps:undefined⇒current`) and extend
   B21 to assert local dig controls + print listener survive.
6. **L-1/L-2:** strict `.model` schema validation (or a `modelVersion` envelope field); decide `NAV_SCRIPT`
   emission + `connect-src` posture before 1F-c.
