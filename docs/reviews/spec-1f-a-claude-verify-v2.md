# Stage 1F-a — Claude Adversarial VERIFY Re-Review (v2, post-lazy-pivot)

**Spec under review:** `docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md` (v2)
**Verifying against:** `docs/reviews/spec-1f-a-claude-adversarial-v1.md` + `docs/reviews/spec-1f-a-claude-redteam-v1.md`
**Reviewer mandate:** (1) confirm each v1 Blocking/High is *genuinely* fixed by the pivot, not reworded; (2) hunt for defects the pivot INTRODUCED, with the heaviest weight on **feasibility** of the lazy serve-path design.
**Date:** 2026-07-09 · **Codex status:** unavailable in-sandbox — this Claude pass stands in per `docs/plugins.md` fallback; re-attempt Codex before merge.

Each finding tagged **INTENT/DESIGN** (needs a product/architecture decision) or **CORRECTNESS** (a fix that does not change intent). v1-traceback given where relevant.

**Severity counts:** Blocking 1 · High 2 · Medium 4 · Low 3

**Headline verdict:** The pivot genuinely dissolves the v1 backfill / heal / coupling / recompute Blocker-cluster — that part is sound and well-reasoned. But it **relocated the money-path onto a session/anon client that has no authority to touch the daily-cap ledger**, and the spec never adds the DB surface that relocation requires. So the daily-cap gate (D10 / §4.2 / B6 / Success-Criterion 3) is **not implementable as written** — a new Blocker the pivot introduced. The single genuinely-good-news feasibility answer: the session/anon client *can* write+promote its own model blob (storage RLS allows it), so the lazy-materialize persistence itself is sound.

---

## Feasibility findings (the five attacks)

| # | Question | Verdict | Evidence |
|---|---|---|---|
| 1 | Can the session/anon client WRITE + promote the model blob? | **PASS** | `0007` policy `artifacts_owner_rw` is `for all to authenticated, anon using/with check (split_part(name,'/',1) = auth.uid()::text)`. Blob key is `{owner_id}/{playlist_key}/…` with `owner_id = auth.uid()`, so INSERT/UPDATE/DELETE + `move` (promote) all satisfy the owner-prefix check. Anon has a real `auth.uid()`. The persistence half of the lazy design works. |
| 2 | Can the session client reserve against the daily cap? | **FAIL → Blocking (B-1)** | `spend_ledger` grants only `service_role`, `force row level security`, **no owner policy** → owner role denied all access. The only writer/reader are `enqueue_job` / `enqueue_preflight`, both `security invoker`, both gated `if auth.role() <> 'service_role' then raise`, both granted service_role-only. **No SECURITY DEFINER RPC callable by authenticated/anon touches `spend_ledger` or `guardrail_config`.** |
| 3 | Does adding caps to `generateMagazineModel` break local `runHtmlDoc`? | **OK** | Current signature is 2 positional args `(sections, language)`; local caller passes exactly 2 (`generate.ts:39-42`). An optional 3rd `opts?` param is non-breaking. Spec §4.2 correctly requires "caps optional; absent → current local behavior." |
| 4 | Drift guard soundness (`sourceSections` vs parsed titles) | **SOUND** (one accepted false-negative) | `parseSummaryMarkdown` is deterministic and used symmetrically at write and read; on the cloud lazy path the model is generated from the *same* MD being served, so first-materialization can't false-drift. Residual: same-titles/changed-prose serves stale leads/bullets silently (Low L-3), inherent and accepted per D8. |
| 5 | Is `artifacts.summaryMd.status` readable by the session client? | **YES** | `readIndex` selects the `data` jsonb and returns it as `Video` (`supabase-metadata-store.ts:22-33`); status lives *inside* `data.artifacts.summaryMd` (unlike `owner_id`, which is a column). §4.1 step 4's status read is implementable. |

---

## BLOCKING

### B-1 — The daily-cap reservation (D10 / §4.2 / B6) is NOT implementable by the session/anon serve client; D5 (no service_role) and D10 (reserve against the daily cap) are mutually unsatisfiable with the current DB surface — CORRECTNESS (feasibility) · **NEW, introduced by the pivot**

**Where:** spec D5, D10, §4.1 step 5, §4.2, B6, Success-Criterion 3; SQL `0011_cost_guardrails.sql:12-18` (`spend_ledger` grants/RLS), `:58-138` (`enqueue_job`), `:147-196` (`enqueue_preflight`), `:27-38` (`guardrail_config` grants).

The v1 money-path lived on the **enqueue/worker path**, where a `service_role` client already exists and `enqueue_job` (service_role-only, security-invoker) does the atomic daily-cap reserve. The pivot **moves the paid call to the serve path** and simultaneously mandates (D5) that the serve path use a **session/anon client, never service_role**. But the daily-cap machinery is reachable *only* by service_role:

1. `spend_ledger`: `grant select, insert, update, delete … to service_role` and **nothing to anon/authenticated**; `enable` + `force row level security` with **no owner policy** ⇒ the owner/anon role can neither read nor write it. A session-client `update spend_ledger …` returns zero rows / permission-denied.
2. `enqueue_job` (the existing reserve logic, `0011:111-115`): `language plpgsql security invoker`, first statement `if auth.role() <> 'service_role' then raise 'server only'`, and `grant execute … to service_role` only (explicitly `revoke … from anon, authenticated`). A session client calling it raises.
3. `enqueue_preflight` (reads the cap): same — service_role-only, security-invoker, `raise 'server only'` for others.
4. `guardrail_config` (holds `daily_cap_cents` and the est values): `grant … to service_role` only, `force RLS`, no owner policy ⇒ the serve path cannot even *read* the cap or the fixed estimate.

So **every** primitive D10 depends on — read the cap, read the fixed estimate, atomically reserve — is closed to the session/anon client. §4.2's "reserve a fixed approximate per-model estimate against the daily cap (`spend_ledger`)" and B6's "day over budget → 503; no Gemini call" describe an operation the serve principal **has no grant to perform**. As written, the money kill-switch on the serve path either does nothing (silently skipped) or 500s — and if it's silently skipped, the paid Gemini call runs **ungated by any daily cap**, which is precisely the invariant Stage 1D exists to guarantee.

The spec does not acknowledge that a **new SECURITY DEFINER RPC** (callable by `authenticated, anon`, running as definer to bypass RLS on `spend_ledger`/`guardrail_config`, doing check-and-reserve atomically) is *required* to make D10 real. §4.2 even asserts "the Stage 1D … guard are UNCHANGED … no migration," which is false: a serve-side reservation needs new DB surface (a migration + a new RPC + its GRANT). This is the load-bearing dependency of the whole lazy money-path and it is missing.

**Fix (needs a decision + design):** Add an explicit `reserve_serve_spend(p_est_cents int)` (or similar) SECURITY DEFINER RPC that (a) reads `guardrail_config` for the cap, (b) does the same atomic `insert … on conflict do nothing` + guarded `update spend_ledger set reserved = reserved + est where reserved+actual+est <= cap` as `enqueue_job:111-115`, (c) is granted to `authenticated, anon`, (d) returns admitted/at-capacity. State the migration. Then **re-review it under the money-path trigger** — because handing owner-role clients a lever on the *global* ledger is itself a new attack surface (see H-1). Until this exists, B6 is untestable and Success-Criterion 3 ("the daily-cap gate refuses model generation when the day is over budget") cannot hold.

---

## HIGH

### H-1 — The obvious fix for B-1 (an owner/anon-callable reserve RPC) is a new money-path attack surface: any client can drive the GLOBAL daily-cap ledger → cheap DoS on the kill-switch; the spec neither designs nor guards it — INTENT/DESIGN · **NEW**

**Where:** consequence of B-1; §4.2, §8 trigger 1 (money-path re-review mandate), D10 ("no per-account quota debit").

Once a `reserve_serve_spend`-style RPC is granted to `authenticated, anon`, **every serve request** can move `spend_ledger.reserved_cents`, which is the *global, all-owners* dollar kill-switch. Combined with D10's explicit **"no per-account quota debit"** on the serve path, there is **no per-owner bound** on how many reservations one principal can drive. Attack: an owner (or anon-churned uids) hammers `GET /api/html/{their-own-doc}` with cache-busting so the model keeps re-materializing (or targets docs whose model is absent/drift), each request reserving the fixed estimate, quickly exhausting the day's `daily_cap_cents` → **every other owner's serve materialization 503s "at capacity."** The serve reservation, like 1D's, is **never released and never reconciled**, so even *failed* materializations permanently inflate `reserved_cents` toward the cap. This is a denial-of-service on the money kill-switch itself, reachable by unprivileged clients — a materially different threat model than 1D's enqueue path (which is service_role-mediated *and* per-account quota-debited).

**Fix (needs a decision):** Before adding the RPC, decide the serve-path abuse controls: (a) a per-owner serve-materialization ceiling or velocity limit (the D10 "no quota debit" choice is what removes the only natural bound — reconsider it, or add a serve-specific counter); (b) release/decrement the serve reservation on materialization failure so retries don't permanently burn the global cap; (c) idempotency so N concurrent misses for one doc reserve once, not N times (B7 covers the *blob* idempotency but not the *reservation*). Route this through the §8 money-path re-review trigger explicitly.

### H-2 — Model persistence helpers can't be reused as-is: `writeModelEnvelope`/`readModelEnvelope` hardcode `localPrincipal` and use plain `put` (not stage→promote); the cloud serve path (§4.1 step 5, B7) needs Principal-parameterized, staged writes — CORRECTNESS · **NEW (unstated shared-code change)**

**Where:** spec §4.1 step 5 ("stage → verify → promote `models/{base}.json` … idempotent"), B7; code `lib/html-doc/model-store.ts:29-38, 41-61` (both helpers call `localPrincipal(outputFolder)` and `blobStore.put(...)`), `generate.ts:49-54` (local caller).

The spec leans on the existing on-view model pattern ("exactly as the local `runHtmlDoc` … already does"), but the concrete persistence helpers are **local-principal-bound**: `writeModelEnvelope`/`readModelEnvelope` construct `localPrincipal(outputFolder)` internally, so a cloud session principal `{id: ownerId, indexKey: playlist_key}` cannot flow through them — the blob would be written under the *local sentinel* prefix, not `{auth.uid()}/…`, and would then violate the storage RLS owner-prefix check on write. Additionally `writeModelEnvelope` does a single `blobStore.put(upsert:true)`, **not** the `putStaged → promote` sequence §4.1 step 5 and B7 mandate for concurrent-first-view idempotency. So "reuse the local helper" is not available; the plan must either (a) add a `Principal` parameter to both helpers (touching the local caller — a parity concern like B14) or (b) write a cloud-specific staged variant. Either way this is real shared-code surgery the spec presents as a given.

**Fix:** State the model-store change: parameterize the principal (or add a cloud helper), and use `putStaged`+`promote` for the cloud write with a JSON-parse+schema-validate "verify" step between them. Add a local-parity note (the local caller must keep writing under the local principal via plain put, unchanged).

---

## MEDIUM

### M-1 — Source-of-truth **MD** repair-needed behind a `promoted` status is unhandled → 500, not a defined response — CORRECTNESS

**Where:** spec §4.1 steps 4-6; glossary "Repair needed" / "Source-of-truth blob" (the summary MD *is* source-of-truth). 

The pivot correctly reclassifies the **model** as lazily-materialized (never repair-needed). But it says nothing about the **MD** going missing behind a `promoted` status — which the glossary explicitly defines as genuine *repair-needed* (a source-of-truth blob committed in the index but absent from storage: post-hoc storage GC, errant delete, partial restore). §4.1 step 4 branches on status and step 6 calls `parseSummaryMarkdown(md)` assuming the MD blob is present; a `promoted`-status-but-absent-MD makes `get(md)` return null → `parseSummaryMarkdown(null/'')` throws → **unhandled 500**. There is no behavior row for it (B13 covers "no summary artifact," i.e. status absent — not MD-blob-missing-behind-promoted).

**Fix:** After the status check, if `get(md)` is null while status is `promoted`, return a defined repair-needed response (e.g. 409/503 with a machine reason), not 500. Add a behavior row.

### M-2 — The "fixed approximate per-model estimate" is undefined, unreconciled, and never released → the global daily-$ kill-switch can be silently under- or over-counted — CORRECTNESS/INTENT · v1-traceback: adv B-2 (dissolved, but its soundness concern reappears here)

**Where:** spec D10, §4.2, §9 ("reconcile-to-actual … 1G"). v1 B-2 (recompute omits input) is genuinely *dissolved* — the spec no longer extends `perRunWorstCents` and the worker cap-soundness is untouched (correct). But the concern it protected — that the money bound be *sound* — now attaches to the new "fixed approximate estimate," which the spec never pins to a number and never proves ≥ the real worst-case magazine cost (`MAGAZINE_MAX_PASSES × (input+output cents)` where input ≈ `MAX_SUMMARY_OUTPUT_TOKENS` + overhead). If the estimate is set too low, many concurrent first-views can overshoot the *real* `daily_cap_cents` (the global kill-switch) before the ledger reflects it; with no reconcile and no release on failure, the direction of error is unbounded either way.

**Fix:** Pin the estimate to a derived worst-case (reuse the magazine caps: `MAGAZINE_MAX_PASSES × per-pass cents from the same price constants`) so it is provably ≥ actual, even if reconcile stays deferred. State the number and its derivation in §4.2.

### M-3 — Redundant + RLS-only playlist resolution: §4.1 resolves `playlistId → playlist_key` (with owner assert), then `readIndex` re-selects the playlist **by `playlist_key` with no owner filter** — CORRECTNESS · v1-traceback: redteam M-4

**Where:** spec §4.1 steps 2-3; code `supabase-metadata-store.ts:14-18` (`readIndex` does `.eq('playlist_key', p.indexKey).maybeSingle()`, no `owner_id`). 

`playlist_key` is unique *per owner*, not globally (the exact `getWorkerStorageBundle` footgun). Under the session client RLS makes the re-select safe, but the spec advertises a defense-in-depth owner assert (D6) while the actual index read re-resolves by key and relies solely on RLS — and it's a wasted round-trip after step 2 already resolved the row. If a future refactor passed the wrong client, `.maybeSingle()` could match a foreign same-keyed playlist or throw on multiple matches.

**Fix:** Pass the already-resolved `playlistId` into the read path (owner-assert on it) or add `owner_id = auth.uid()` to the `readIndex` query; don't advertise defense-in-depth while resting the read on RLS alone.

### M-4 — `type=dig-deeper → 400` (§5/B14) must be scoped to the cloud backend, or it regresses the preserved local path — INTENT/ambiguity · v1-traceback: redteam M-1

**Where:** spec §5, B14, §4.1 ("local path preserved … keeps its current … `outputFolder` behavior"); code `app/api/html/[id]/route.ts:23-26` + `buildDocHtml` currently serve `dig-deeper` locally.

The current route serves `dig-deeper` for the local backend. If 1F-a validates `type` to `summary`-only unconditionally, it regresses local `dig-deeper`. The spec intends the 400 for the **cloud** backend only, but §5/B14 state it globally.

**Fix:** State the 400-on-`dig-deeper` applies only when `STORAGE_BACKEND=supabase`; local retains `dig-deeper`.

---

## LOW

### L-1 — Nonce refactor scope is real (const strings, not functions) — CORRECTNESS · v1-traceback: adv L-1
`THEME_HEAD_SCRIPT`, `THEME_TOGGLE_SCRIPT`, `NAV_SCRIPT`, `PRINT_BUTTON` are module-level `const` strings (`theme.ts:78,88,97`, consumed at `render.ts:110,114,122`). Threading a per-request nonce means converting them to nonce-taking builders (or string-surgery injection) while preserving byte-identical no-nonce output. D11/§4.3 acknowledge this; keep it explicit so the plan sizes it as a refactor, not "add a param."

### L-2 — Local/cloud branch trigger still dual-keyed — CORRECTNESS · v1-traceback: adv L-3
§4.1 keys local on `STORAGE_BACKEND=local`; §5 keys it on `playlist` vs `outputFolder` param. Define precedence when a request carries the "wrong" param for the active backend (reject 400 vs ignore).

### L-3 — Drift guard false-negative (same titles, changed prose) serves stale leads/bullets silently — CORRECTNESS
Inherent to the title-only `sourceSections` comparison and identical to the local path; acceptable per D8 (model is an acceptable re-render, not ground truth). Note it so it isn't mistaken for a bug later.

---

## v1 Blocking/High resolution scorecard

| v1 finding (source) | v2 mechanism | Verdict |
|---|---|---|
| **caps-unbounded** (adv B-1) | D10 + §4.2 + B5: `generateMagazineModel` gains `maxOutputTokens` + schema `maxItems` + `thinkingBudget:0` + `countTokens` preflight + `signal`; feasible as optional param (Feasibility 3). | **FIXED** — stated as a load-bearing code change; local caller preserved. |
| **cost-recompute-omits-input** (adv B-2) | D10 + §4.2: **no** strict recompute; magazine is *not* added to `perRunWorstCents`; a fixed approximate estimate is used instead; worker cap-soundness untouched. | **FIXED / DISSOLVED** — the recompute is no longer claimed. Residual soundness of the *approximate estimate* → M-2. |
| **print-button-CSP** (adv B-3 / redteam B-3) | D11: convert `PRINT_BUTTON onclick` → nonce'd `addEventListener`; relax byte-identical to **behavior-identical** (B14/B21). | **FIXED** — the decision the v1 review demanded is made; feasible. |
| **backfill-dead-end** (redteam B-1) | D3/D8/B2: lazy serve-path materialization; pre-1F-a docs (no model) materialize on first view; worker unchanged, no backfill needed. | **FIXED in principle** — but every materialization is gated behind the non-implementable daily-cap reserve (B-1), so the heal path can't actually run until B-1 is resolved. |
| **repair-heal-deadend** (redteam B-2 / adv H-1) | D8/B3/B4: absent/unparseable/drifted → regenerate on view; corrupt treated as absent (never 500). | **FIXED in principle** — same B-1 contingency. (MD-blob repair-needed still unhandled → M-1.) |
| **coupling-rebill** (adv H-3) | Worker unchanged; magazine decoupled from the atomic summary run entirely. | **FIXED / DISSOLVED.** |
| **D6-not-implementable** (adv M-3 / redteam H-1) | D6 rewritten: **no** video-row owner assert (readIndex carries no `owner_id`); playlist-row assert + RLS are the guarantees. | **FIXED** — claim corrected to match code reality; playlist assert is implementable. |
| **committed-vs-missing** (adv H-2 / redteam H-2/H-3) | §4.1 step 4 + B12: read `artifacts.summaryMd.status`; promoted→proceed, committed→503 retry, absent→404. Status readable from `data` jsonb (Feasibility 5). | **FIXED** — feasible and correctly branched. |
| **non-UUID-500** (adv H-4) | §4.1 step 2 + B15: UUID-pre-validate `playlistId` before any DB call → 400. | **FIXED.** |
| **cache-control** (redteam H-5) | §4.1 step 7 + B17: `Cache-Control: private, no-store`. | **FIXED.** |

**Are the v1 Blockers genuinely resolved?** Yes — all three original-review Blockers and both red-team Blockers are genuinely (not cosmetically) dissolved by the lazy pivot, and the fixes are principled, not reworded. The caveat is that two of them (backfill, heal) are only *operationally* fixed once B-1 is resolved, because the heal path runs through the daily-cap gate that isn't currently implementable.

---

## Bottom line

The pivot is the right call and genuinely closes the v1 Blocker-cluster. But it introduced **one new Blocker (B-1): the daily-cap money-gate cannot be enforced by the session/anon serve client** — `spend_ledger`, `enqueue_job`, `enqueue_preflight`, and `guardrail_config` are all service_role-only, and the spec adds no owner-callable reserve RPC while D5 forbids service_role. Fixing it requires new DB surface (a SECURITY DEFINER reserve RPC + migration), which then needs its own money-path re-review (H-1: owner-driven global-ledger DoS). Two more genuine gaps the pivot glossed: model-store helpers are local-principal-bound and non-staged (H-2), and MD-blob repair-needed behind a promoted status 500s (M-1). Do **not** treat convergence as reached: B-1 is a fresh Blocking, so another dual round is mandatory per dev-process.
