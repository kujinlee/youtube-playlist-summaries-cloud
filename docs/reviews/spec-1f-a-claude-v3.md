# Stage 1F-a — Claude Adversarial RE-REVIEW (v3, A-lite serve-side spend RPC)

**Spec under review:** `docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md` (v3 — A-lite spend governance)
**Verifying against:** `docs/reviews/spec-1f-a-claude-verify-v2.md` + `docs/reviews/spec-1f-a-claude-redteam-v2.md`
**Reviewer mandate:** (1) confirm the v2 Blocker (B-1 daily-cap infeasibility) + Highs are *genuinely* fixed by the A-lite RPC, not reworded; (2) attack the NEW element — the A-lite `SECURITY DEFINER` reserve RPC — for concurrency / SECURITY DEFINER / free-generation holes.
**Date:** 2026-07-09 · **Codex status:** a real Codex pass runs alongside this round; this is the independent Claude pass.

Each finding tagged **INTENT/DESIGN** (needs a product/architecture decision) or **CORRECTNESS** (a fix that doesn't change intent). v2-traceback given where relevant.

**Severity counts:** Blocking 1 · High 2 · Medium 3 · Low 3

**Headline verdict:** The v3 pivot to the A-lite `SECURITY DEFINER` RPC **genuinely dissolves the v2 Blocker** (the money-gate is now *reachable* by the session/anon client, and the "no migration" claim is retracted). But the new RPC has a **fresh Blocking hole**: the per-`(owner,doc,day)` idempotency bounds the **charge** but not the **Gemini call** — after a failed generate, every same-day reload re-invokes Gemini *uncharged*, and because `actual_cents` is never reconciled the daily-cap ledger cannot see that spend. So the daily cap does **not** bound actual dollars — defeating the exact invariant A-lite exists to provide (and the whole reason A-lite was chosen over Option D). Plus two Highs: the anon-granted definer's owner/doc trust model is unspecified (v2 H-1 global-cap DoS is **not** actually closed for direct RPC callers), and the "single conditional UPDATE" framing mis-describes a construct that must touch **two** tables (marker + ledger) with a specific arbiter + rollback ordering. **Not converged — another round is mandatory.**

---

## Concurrency / SECURITY DEFINER / free-generation — the three attacks

| # | Attack | Verdict | One-line |
|---|---|---|---|
| 1 | Two simultaneous first-views of one doc | **Partial fail → feeds B-1** | With the right arbiter: exactly one *reserves*, one gets "already charged" — **no double-charge**. BUT both still proceed to `generateMagazineModel` → **two Gemini calls, one charge**. Work is not deduped, only the charge is. |
| 2 | SECURITY DEFINER owner/doc trust | **FAIL → High H-1** | Spec never says `owner_id` is derived from `auth.uid()` inside the definer, nor that the definer verifies the doc is a real *owned* artifact. A direct anon RPC call with arbitrary `doc` strings drains the global cap → v2 H-1 DoS persists. |
| 3 | Same-day free-generation DoS | **FAIL → Blocking B-1** | After a FAILED generate the model stays absent; next view → "already charged" → **Gemini re-called, uncharged**. Generate-attempts-per-`(owner,doc,day)` are **not bounded** — unbounded per-day Gemini spend invisible to the cap. |
| — | Two DIFFERENT docs at the cap boundary | **PASS (v2 H-2 fixed)** | The single-day-row conditional `UPDATE … WHERE reserved+actual+est <= cap` row-lock serializes all reservations; the second doc blocks, re-evaluates, and is refused. The overrun is bounded to ≤ one in-flight `est`, the accepted approximation. Credit where due. |

---

## BLOCKING

### B-1 — The per-`(owner,doc,day)` idempotency bounds the CHARGE but not the Gemini CALL; failed-generate reloads (and concurrent first-views) re-invoke Gemini uncharged, and with reconcile deferred the daily-cap ledger never sees that spend → the daily cap does NOT bound actual dollars — CORRECTNESS/DESIGN · **NEW, introduced by the A-lite RPC** · v2-traceback: dissolves v2 verify-B-1 feasibility but reopens the *soundness* it protected (verify-M-2, redteam-H-1)

**Where:** spec D10 (b), §4.1 step 5 ("'already charged' … → proceed. Then `generateMagazineModel(...)`" and "A generation failure after a same-day reservation is **not** re-charged on retry … bounding a reload-loop"), B6b, §8 trigger-1; SQL `0011:113-115` (reserve) + `spend_ledger.actual_cents` "inert in 1D; written by the deferred reconcile".

The v3 design charges **once** per `(owner,doc,UTC-day)` and, on any subsequent same-day miss, returns "already charged" and **still calls `generateMagazineModel`**. Trace the failure path:

1. First view of an un-materialized doc: RPC reserves `est`, marker set. `generateMagazineModel` runs and **fails** (transient Gemini 5xx, a schema-invalid model output that always fails validation, or the client aborts before promote so the model is never persisted).
2. Model blob is still absent → owner reloads.
3. Second view: model absent → miss → RPC → marker exists → **"already charged" → proceed → `generateMagazineModel` called again, no charge.**
4. Repeat. **Every reload fires a fresh, uncharged Gemini call.** Nothing bounds the number of generate attempts per `(owner,doc,day)`.

Because `actual_cents` stays **inert** (reconcile deferred, §9), the ledger only ever records the **count of first-charges** (`reserved_cents += est` once per distinct `(owner,doc,day)`), never the count of Gemini calls. So the daily cap sees `1×est` while real spend is `N×gemini`. The kill-switch is **nominal**: it trips on the number of distinct docs first-viewed, not on dollars spent.

This inverts D10's own safety claim. D10 says "over-reserve-on-failure is acceptable/**conservative**." That was true in 1D (never-released reservation ⇒ reserved ≥ actual ⇒ cap trips early ⇒ safe). But the idempotency marker that v3 adds to kill the "reload re-charge DoS" simultaneously makes the *second and later* generates **free**, so across a failing doc `reserved = 1×est` while `actual = N×gemini` ⇒ **reserved < actual ⇒ UNDER-reserved ⇒ NOT conservative.** You cannot have both "a reload never re-charges" **and** "reservation ≥ actual spend" when a reload triggers a fresh paid call — v3 picked "never re-charge" and thereby lost the dollar bound.

Concurrency makes it worse without even needing failure: two tabs on one un-materialized doc → one charge, **two** Gemini calls (attack #1); N tabs → N calls, 1 charge. An anon owner (2-doc quota) can hold open dozens of concurrent requests per doc and/or reload a reliably-failing doc all day — **unbounded per-day Gemini spend, cap never moves.** §8 trigger-1 explicitly tells the reviewer to verify "the per-`(owner,doc,day)` idempotency genuinely bounds a reload-loop / concurrent miss (no unbounded re-charge)." It bounds re-*charge*; it does **not** bound re-*spend*. This is the hole.

**Why Blocking:** A-lite was chosen over Option D (ungated, defer to 1G) *precisely* to keep serve-side generation "under the hard daily kill-switch (1D's principle)" (D10 rationale, AFK-decision box, Success-Criterion 3). If the cap doesn't bound actual Gemini dollars, A-lite delivers the same real exposure as Option D but with more machinery — the slice's central safety claim is false as written.

**Fix (needs a decision):** dedup the **work**, not just the charge, and couple the reservation to the paid call. Concretely, pick one:
- **(a) Bound generate-attempts and reserve for them up-front.** On the first charge reserve `N×est` (reuse a `summary_max_attempts`-style bound), record an attempt counter in the marker, allow ≤N uncharged retries, and **refuse further generates for that `(owner,doc,day)` once N is hit** (→ 503, no Gemini). This restores conservatism (reserved ≥ worst-case actual for the allowed attempts) and matches 1D's `max_attempts` model.
- **(b) Single-flight the generate** (advisory lock or an in-flight marker with a short TTL keyed by `(owner,doc)`) so concurrent misses **join** one running generate instead of each firing Gemini, *and* each *distinct* generate attempt re-reserves (so failure→retry re-charges, bounded by the daily cap and the attempt ceiling).
Either way, add explicit behavior rows: "N concurrent first-views fire exactly one Gemini call," and "generate attempts per `(owner,doc,day)` are capped at N; the N+1th miss returns 503 without calling Gemini." Then re-review under the §8 money-path trigger.

---

## HIGH

### H-1 — The RPC is granted to `authenticated, anon` and callable **directly** (PostgREST), but the spec never states that `owner_id` is derived from `auth.uid()` inside the definer, nor that the definer verifies the `doc` is a real OWNED artifact; a direct call with arbitrary `doc` strings drains the global cap → v2 H-1 DoS is NOT actually closed — INTENT/DESIGN · **NEW / carryover** · v2-traceback: redteam-H-1, verify-H-1 (claimed fixed by idempotency; the fix has a hole)

**Where:** spec D10 ("granted to `authenticated, anon`"; "a principal reserves at most once per **owned** doc/day; **owned-doc-count is quota-bounded** → no ledger-lever DoS"), §4.2, §4.1 step 5 (verification lives in the serve *code*, before the RPC call — step 4 reads status/ownership, step 5 calls the RPC). Compare `enqueue_job` (`0011:69-70`): trusts `p_owner_id` **only because** it is `service_role`-gated (`if auth.role() <> 'service_role' then raise`) — a trusted server passes the resolved owner.

Two unstated, load-bearing requirements for an **anon-granted** `SECURITY DEFINER` RPC:

1. **Owner must be `auth.uid()`, never a caller param.** A definer runs privileged and bypasses RLS. `enqueue_job` can accept `p_owner_id` because no untrusted caller can reach it (service_role-only). The A-lite RPC is reachable by any anon/authenticated caller, so if it accepts an owner parameter, a caller can attribute charges/markers to arbitrary owners. The spec is silent on this. It **must** state `v_owner := auth.uid()` internally and ignore/reject any caller-supplied owner.

2. **The definer itself must verify the `doc` is a real, owned, promoted artifact — the serve-code check in step 4 does NOT protect a direct RPC call.** D10's entire abuse-bound rests on "owned-doc-count is quota-bounded." But that premise holds only if the marker set is bounded to real owned docs. The serve route (§4.1) does verify the doc (reads the index, asserts `promoted`) *before* step 5 — but the RPC is a directly-invocable PostgREST endpoint granted to anon. An attacker skips the route entirely and calls the RPC with `doc = "x1", "x2", … "xN"` — each a fresh `(owner, doc, day)` → each **reserves `est` against the GLOBAL ledger** → the daily cap drains to zero → **every other owner's serve materialization 503s "at capacity."** The idempotency marker does not stop this: idempotency is *per doc*, and `doc` is attacker-chosen and unbounded. So v2 H-1 (owner-driven global-cap DoS) is **re-opened**, not closed — the "quota-bounded" claim is asserted without the mechanism that would make it true.

**Fix (needs a decision + design):** State in D10/§4.2 that the definer (i) sets owner from `auth.uid()` internally; (ii) **validates `(owner, playlist, video)` against the caller's own real, promoted summary artifact inside the function** (or accepts only a server-signed/opaque doc handle it can re-derive), so the marker set is genuinely quota-bounded; and (iii) rejects a call for a doc the caller does not own. Without (ii) the "no ledger-lever DoS" claim is unsubstantiated. (Borderline Blocking — a single anon client can deny the money kill-switch to all tenants; kept at High only because the *intent* to bound by owned docs is stated, just not mechanized.)

### H-2 — "A single conditional UPDATE" mis-describes the construct: the reserve touches `spend_ledger` but the dedup requires an `INSERT … ON CONFLICT DO NOTHING RETURNING` arbiter on a UNIQUE `(owner,doc,day)` marker in a SECOND table, with a specific insert-then-reserve ordering and rollback-on-refusal — none of which the spec states; the literal reading is racy (double-charge or permanent-free-doc) — CORRECTNESS · **NEW** · v2-traceback: redteam-H-2 (correctly demanded the atomic reserve; v3 mis-states the *marker* half)

**Where:** spec D10 ("in a **single conditional UPDATE**"), §4.2 ("in a **single conditional UPDATE** (never a racy read-then-write)"). Precedent: `enqueue_job` uses **two** statements for its two-table job — `insert … usage_counters … on conflict do nothing; update … where used < allow` (`0011:105-109`) **and** `insert spend_ledger … on conflict do nothing; update … where reserved+actual+est <= cap` (`0011:112-115`), all inside one atomic function body.

The A-lite RPC must do two things against two different tables: (1) claim the per-`(owner,doc,day)` marker (dedup), and (2) reserve on the single-row-per-day `spend_ledger` (cap arbiter). A "single conditional UPDATE" cannot atomically do both. Worse, the correct construct for the **dedup** half is **not** an UPDATE at all:

- A `UPDATE marker SET charged=true WHERE owner=… AND doc=… AND day=… AND NOT charged` matches **zero rows** on the first-ever view (the marker row doesn't exist yet), so it cannot distinguish "already charged" from "never seen." Under two concurrent first-views both UPDATEs match zero rows → the implementer's "not found" branch runs for **both** → depending on how they wired it, **both reserve (double-charge)** or **both skip**. This is exactly the racy read-then-write §4.2 claims to avoid, reintroduced through the wrong primitive.
- The race-free construct is the `enqueue_job` arbiter: `INSERT INTO serve_charge_marker(owner,doc,day) VALUES(…) ON CONFLICT DO NOTHING RETURNING …`; the row lock on the UNIQUE index serializes concurrent inserts, exactly one gets a row (→ do the reserve), the other gets none (→ "already charged"). **This is the construct that guarantees "exactly one reserve" — and the spec never names it.**

**Ordering also matters and is unspecified:** insert-marker **then** conditional-reserve. If the reserve fails (over cap), the function must `raise` so the **whole transaction rolls back, including the marker insert** — otherwise the doc is permanently marked "charged" while never actually charged, and every future view gets a free generate (feeding B-1) and the doc can never obtain a real reservation. The `enqueue_job` "any raise below rolls back this INSERT" comment (`0011:91`) is the pattern to mirror; the spec doesn't mention it.

**Fix:** Replace "single conditional UPDATE" (D10, §4.2) with: "an atomic function body that (1) `INSERT … ON CONFLICT DO NOTHING RETURNING` on a UNIQUE `(owner,doc,day)` marker as the dedup arbiter; if no row returned → 'already charged', return without reserving; (2) else the `enqueue_job` conditional `UPDATE spend_ledger … WHERE reserved+actual+est <= cap`; if `not found` → `raise` (rolls back the marker) → 'at capacity'." Add a behavior row: "two concurrent first-views → exactly one reserve, one 'already charged', zero double-charge."

---

## MEDIUM

### M-1 — MD source-of-truth blob missing *behind a `promoted` status* still → 500, not a defined response — CORRECTNESS · **carryover, NOT fixed** · v2-traceback: verify-M-1

**Where:** §4.1 steps 4–6 unchanged from v2. Step 4 branches on `summaryMd.status`; `promoted` → proceed → step 6 `parseSummaryMarkdown(md)`. If the MD blob is absent behind a `promoted` status (post-hoc storage GC, errant delete, partial restore — the glossary's genuine "repair needed"), `get(md)` returns null → `parseSummaryMarkdown(null/'')` throws → **unhandled 500**. No behavior row covers it (B13 = status absent, not blob-missing-behind-promoted). v3 did not address v2 verify-M-1.

**Fix:** After the status check, if `get(md)` is null while status is `promoted`, return a defined repair-needed response (409/503 + machine reason), not 500. Add a behavior row.

### M-2 — The "fixed approximate per-model estimate" is still un-pinned and, with reconcile deferred + B-1's charge-once/generate-many, the ledger's error direction is UNDER-count (not the claimed "conservative over-reserve") — CORRECTNESS/INTENT · v2-traceback: verify-M-2 (partially carried; interacts with B-1)

**Where:** D10 ("a **fixed approximate per-model estimate**"), §4.2 ("reserves a fixed approximate estimate"), §9 (reconcile → 1G); `guardrail_config.summary_est_cents` precedent (`0011:29`, a *worst-case* upper bound "from ENFORCED token caps incl audio pricing"). v3 never pins the magazine estimate to a number nor proves `est ≥ MAGAZINE_MAX_PASSES × (input+output cents)`. Note the current `generateMagazineModel` (`lib/gemini.ts:464`) has **no** `maxOutputTokens`/`thinkingBudget`/`countTokens`/`signal` — B5's caps are a real, unstated-in-v1 change, and until they land the "worst case" is unbounded, so no `est` can be proven sufficient.

Even once caps land: because B-1 lets one charge cover N calls, an `est` sized for *one* call under-covers the real spend. Pinning `est` alone does **not** fix B-1 — but leaving it unpinned means even the single-call bound is unproven.

**Fix:** Pin `est` to a derived worst-case (magazine caps × per-pass cents from the same price constants as `summary_est_cents`), state the number + derivation in §4.2, and resolve B-1 so the ledger error direction is actually conservative.

### M-3 — Redundant, RLS-only playlist re-resolution: §4.1 resolves `playlistId → playlist_key` with an owner assert (D6), then `readIndex` re-selects by `playlist_key` with **no owner filter** — CORRECTNESS · **carryover, NOT visibly addressed** · v2-traceback: verify-M-3

**Where:** §4.1 steps 2–3; `supabase-metadata-store.ts` `readIndex` selects `.eq('playlist_key', p.indexKey).maybeSingle()` with no `owner_id`. `playlist_key` is unique **per owner**, not globally (the `getWorkerStorageBundle` footgun). Under the session client RLS makes it safe, but the spec advertises a defense-in-depth owner assert (D6) while the actual index read rests solely on RLS and wastes a round-trip. A future refactor passing the wrong client could match a foreign same-keyed playlist.

**Fix:** Add `owner_id = auth.uid()` to the `readIndex` query (or thread the already-resolved owner-checked playlist row into the read) so the advertised defense-in-depth is real, not RLS-only.

---

## LOW

### L-1 — Title-only drift guard still serves a semantically-stale model on same-titles/changed-prose — CORRECTNESS · accepted per D8 · v2-traceback: verify-L-3 / redteam-M-1
Inherent to the `sourceSections` = titles-only comparison; `generatorVersion` (newly added, good) covers schema/format changes but not prose drift under stable titles. Acceptable per D8 (model is a re-render, not ground truth). Pin the cloud "MD immutable per base" assumption with a test so it isn't mistaken for a bug when a resummarize path lands.

### L-2 — CSP omits `frame-ancestors` and `form-action`; an owner-private doc can be framed (clickjacking) — CORRECTNESS/nit
§4.3 lists `default-src 'none'`, `script-src`/`style-src 'nonce'`, `img-src`, `base-uri 'none'`, `object-src 'none'` — no `frame-ancestors 'none'`/`'self'` or `form-action 'none'`. For an owner-private page, add `frame-ancestors 'none'`. (v2 L-2's `connect-src` landmine is now moot since `dig:false` omits `NAV_SCRIPT` entirely per §4.3 — credit.)

### L-3 — The RPC's tri-state result ("reserved" / "already charged" / "at capacity") lets any anon caller probe the GLOBAL daily-spend state — CORRECTNESS/nit
"at capacity" leaks whether the day is over budget. Low sensitivity (1D already exposes `quota_allowance` and `daily_cap_cents` is not secret), but spend *level* is arguably more sensitive than the static cap. Note it; not worth blocking.

---

## v2 Blocking/High resolution scorecard

| v2 finding | v3 mechanism | Verdict |
|---|---|---|
| **daily-cap infeasible on session client** (verify-B-1 / redteam-B-1, Blocking) | D10 + §4.2: new `SECURITY DEFINER` RPC granted to `authenticated, anon`, touching `spend_ledger`/`guardrail_config` only inside the definer; **"no migration" explicitly retracted** ("this slice DOES include a small, self-contained migration"). | **FIXED (mechanism now exists & reachable)** — but the mechanism introduces B-1 (charge-once/generate-many) + H-1 (owner/doc trust) + H-2 (construct mis-stated). Feasibility dissolved; soundness not. |
| **owner-driven global-cap DoS** (redteam-H-1 / verify-H-1, High) | D10 per-`(owner,doc,day)` idempotency + "owned-doc-count is quota-bounded". | **PARTIAL / NOT** — idempotency dedups the *charge* per doc, but `doc` is attacker-chosen on a **direct** RPC call and ownership is verified only in serve *code*, not the definer → DoS persists (H-1). |
| **racy check-then-reserve** (redteam-H-2, High) | §4.2 "single conditional UPDATE (never a racy read-then-write)". | **PARTIAL** — the *ledger reserve* race (two docs at the boundary) is FIXED by the single-day-row conditional UPDATE arbiter. The *dedup marker* half is mis-framed as an UPDATE and is racy as literally written (H-2). |
| **model-store local-principal-bound + non-staged** (verify-H-2, High) | §4.1 step 5 + §4.2: `writeModelEnvelope`/`readModelEnvelope` gain a `principal` param + `putStaged→promote`; local caller unchanged. | **FIXED** — stated as required shared-code surgery; matches code reality (`model-store.ts` hardcodes `localPrincipal` + plain `put`). |
| **opts defaults / local regression** (redteam-M-2) | §4.3 "Opts defaults … `nonce` undefined, `dig` defaults to **true**"; caps optional. | **FIXED.** |
| **generatorVersion missing** (redteam-L-1) | §4.2 envelope gains `generatorVersion`. | **FIXED** (old envelopes lacking the field fail the `.strict()` parse → treated as absent → regenerate — the desired invalidation). |
| **print-button CSP** (v1 B-3) | D11 nonce'd `addEventListener` (unchanged). | **FIXED.** |
| **committed-vs-404** (v1 H-2/H-3) | §4.1 step 4 status branch. | **FIXED** — but MD-missing-behind-promoted still → 500 (M-1, carryover). |
| **non-UUID-400** (v1 H-4) | §4.1 step 2 UUID pre-validate → 400. | **FIXED.** |
| **cache-control** (v1 H-5) | §4.1 step 7 `private, no-store`. | **FIXED.** |

---

## Claims that genuinely HOLD (don't re-litigate)

- **Two-different-docs cap-boundary overrun is closed** by the single-day-row conditional `UPDATE … WHERE reserved+actual+est <= cap` (the `enqueue_job` arbiter) — provided the RPC uses it (v3 does mandate it for the reserve half). v2 redteam-H-2's overrun does not occur.
- **Blob write/promote as a session client is feasible** (`artifacts_owner_rw` `for all to authenticated, anon`, key is server-constructed `{auth.uid()}/{playlist_key}/…`, `promote` stays under the owner prefix). Don't drag service-role onto the blob path.
- **Cross-owner / unauth isolation holds** (RLS `playlists_owner`/`videos_owner` + storage first-segment `= auth.uid()`; foreign/absent `playlistId` → identical 404; anon session uid is a real `auth.uid()`).
- **The lazy pivot's dissolution of the v1 backfill/heal/coupling Blockers stands** — pre-1F-a docs and lost/corrupt models self-heal on view, worker unchanged. Correct; do not re-open.
- **"no migration" retraction is correct** — 1F-a legitimately ships one migration for the reserve RPC + marker table.

---

## Bottom line

The v3 A-lite RPC **fixes the v2 Blocker's feasibility** (the money-gate is now reachable by the session/anon client and the "no migration" error is retracted) and cleanly closes the ledger-reserve race for distinct docs. But it introduces **one new Blocking (B-1): the daily cap no longer bounds actual Gemini dollars** — the per-`(owner,doc,day)` idempotency dedups the charge while leaving generate calls unbounded (concurrent first-views fire N calls for one charge; failed-generate reloads re-call Gemini uncharged all day), and reconcile-off means the ledger never sees it. Two Highs compound it: the anon-granted definer's owner/doc trust model is unspecified so v2's global-cap DoS is **not** actually closed for direct RPC callers (H-1), and "single conditional UPDATE" mis-describes a two-table construct whose dedup arbiter (`INSERT … ON CONFLICT DO NOTHING RETURNING` on a UNIQUE `(owner,doc,day)` marker) + insert-then-reserve-then-rollback ordering is left unstated and is racy as written (H-2).

**Convergence: NO.** A fresh Blocking + two Highs in the money-path element mean another dual adversarial round is mandatory per `docs/dev-process.md`. Re-review must verify: generate-*attempts* (not just charges) are bounded per `(owner,doc,day)`; the reservation is coupled to the paid call so the ledger error direction is genuinely conservative; the definer derives owner from `auth.uid()` and verifies doc-ownership *inside* the function; and the marker uses the `ON CONFLICT DO NOTHING RETURNING` arbiter with rollback-on-cap-refusal.
