# Stage 1F-a — Claude Adversarial RE-REVIEW (v6, lease-based single-flight, NO release RPC)

**Spec under review:** `docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md` (v6 — "lease-based single-flight").
**Verifying against:** `docs/reviews/spec-1f-a-claude-v5.md` (the Blocking that must be confirmed closed) + `docs/reviews/spec-1f-a-codex-v5.md`.
**Reviewer mandate:** (1) confirm the v5 Blocking (B-1, the anon-callable `release_serve_model` → free/instant/repeatable $0 global-cap DoS) is *genuinely* gone, not reworded; (2) hunt for any NEW hole the lease redesign introduces; (3) verify the two invariants — (a) no anon-callable release, (b) charge-per-attempt keeps the daily cap the true bound and CANNOT net-to-zero.
**Date:** 2026-07-09 · **Codex status:** an independent Codex pass runs alongside this round; this is the Claude pass.

Each finding tagged **INTENT/DESIGN** (needs a product/architecture decision) or **CORRECTNESS** (a fix that doesn't change intent).

**Severity counts:** Blocking 0 · High 1 · Medium 2 · Low 4

**Headline verdict.** v6 **genuinely closes the v5 Blocking.** There is no `release_serve_model` RPC anywhere in v6; the only money-touching serve RPC is `reserve_serve_model`, and the marker table stays force-RLS + `service_role`-only-write, so **no anon-callable lever can delete/void a marker.** The v5 instant/free/single-doc/infinitely-repeatable ledger drain is unreachable — the per-`(owner,doc,day)` charge can only be repeated after the lease **expires** (`LEASE_TTL ≈ 180 s`), which is server-set and not client-shortenable. Invariant (a): **PASS.** Invariant (b): the ledger is **monotonic** — there is no decrement anywhere in v6, so it **cannot net-to-zero**, and the conditional-UPDATE arbiter keeps total spend ≤ `daily_cap`; **PASS.** The two Postgres-semantics questions the mandate raised (the `ON CONFLICT DO UPDATE … WHERE … RETURNING (xmax=0)` discriminator, and the lease-boundary double-reclaim) both resolve **correctly** (see "Claims that HOLD"). The cap-refusal rollback of a *reclaim* is also sound **provided the savepoint encloses step 4** (it does per the spec text; see L-1 for the test-phrasing gap).

**But the lease redesign trades away a property v4 had and the spec's own security rationale is imprecise about it (H-1).** v4's per-`(owner,doc,day)` idempotency meant a single owner's *maximum* daily contribution to the **global** ledger was `owned-promoted-docs × est` — small and bounded. v6 **charges every attempt** and lets each `(owner,doc,day)` be re-charged once per `LEASE_TTL`, so **a single owner can now drive the entire shared daily cap to `at_capacity`** by TTL-paced reclaims. And because the charge commits inside `reserve_serve_model` **before** `generateMagazineModel` runs, a caller who aborts right after reserve pays **≈ $0 real Gemini** per charge — so the spec's claim that a reclaim is "a real seconds-long Gemini call … never the instant $0 ledger-drain" is only *half* true: it is no longer *instant* (TTL-gated) but it is *not* guaranteed to cost real dollars. This is a **rate-limited, owned-doc-bounded** availability drain — strictly weaker than v5's Blocking — but it is a genuine **new High** vs v4 and the rationale must be corrected. **Not a Blocking; a decision point:** either bound it (a per-`(owner,doc,day)` attempt counter `K`, restoring v4's tightness while keeping the heal path) or explicitly accept-and-defer to 1G with the rationale fixed in-spec.

---

## v5 → v6 scorecard (what this round was called to verify)

| v5 finding | v6 mechanism | Verdict |
|---|---|---|
| **B-1 (Blocking): `release_serve_model` is an anon-callable, unbounded lever — `reserve→release` loop on one owned promoted doc drives the GLOBAL cap to `at_capacity` for all tenants at $0 real spend, instant, repeatable** | v6 **deletes the release RPC entirely.** Recovery = the lease **expires** (`LEASE_TTL`); the next view **reclaims** (`ON CONFLICT DO UPDATE … WHERE lease_expires_at < now()`) and re-charges. No client-callable void of any marker exists. | **FIXED — genuinely.** The specific lever (delete-the-marker) is gone; idempotency can only be "reset" by real wall-clock time (`≥ TTL`), which is not a client lever. See H-1 for the residual the *new* mechanism opens. |
| **M-1 (v5): release on client-abort may never fire → H-1 brick persists for the abort case** | Moot — there is no release to fire. On abort the handler does nothing; the lease self-expires and the next view reclaims. | **DISSOLVED.** The "unfired release re-bricks the doc" failure mode cannot exist; a stuck attempt self-heals at `TTL` for that owner. |
| **M-2 (v5): release under-specified vs reserve** | Moot — no release RPC. `reserve_serve_model` retains its numbered exact-transaction block. | **DISSOLVED.** |
| **M-3 (v5): reserve promoted-check TOCTOU → an unmapped reserve *denial* mid-serve** | Unchanged in v6 — step 2 still re-reads `promoted` inside the definer; step-5 status handling still enumerates only `in_flight | at_capacity | reserved`. | **NOT ADDRESSED — carried forward as M-2 below.** |
| **L-3 (v5): `est` un-pinned number** | Unchanged ("derived roughly …"). | Carried as L-3. |
| **L-4 (v5): `readIndex` no `owner_id` filter (RLS-only)** | Unchanged. | Carried as L-4. |

---

## HIGH

### H-1 — Charge-per-attempt + TTL-reclaim removes v4's per-`(owner,doc,day)` idempotency: a **single owner** can now drive the **entire shared daily cap** to `at_capacity` (global serve outage) via TTL-paced reclaims — and because the charge commits **before** generation, each charge can cost **≈ $0 real Gemini** (abort-after-reserve), so the spec's "each reclaim = a real Gemini call, never a $0 drain" rationale is imprecise — INTENT/DESIGN · **NEW, introduced by the v6 lease redesign** · v4/v5-traceback: re-opens a *bounded* form of the shared-cap single-user drain that v4's per-doc/day idempotency had capped at `owned-docs × est`

**Where:** §3 D10 and §4.1 step 5 ("**CHARGE EVERY ATTEMPT** … each *reclaim* charges `magazine_est_cents` again … never the instant $0 ledger-drain of a release lever … each a real seconds-long Gemini call (slow, bounded)"); §4.2 reserve step 4→5 (the `INSERT … ON CONFLICT DO UPDATE` **commits the ledger charge in step 5 before returning `reserved`**; the route only *then* calls `generateMagazineModel`).

**Two facts the rationale glosses over:**

1. **The charge precedes generation.** `reserve_serve_model` runs the conditional `UPDATE spend_ledger` (step 5) and commits `reserved += est` as soon as it returns `reserved`. The route calls Gemini *after*. So a caller who lets `reserve` commit and then **aborts** (trivial under D13 synchronous — disconnect a few hundred ms in; the `signal` aborts `generateMagazineModel`, which honors it — confirmed `lib/gemini.ts:616` throws `AbortError` on `signal.aborted`) pays the `est` charge with **near-zero real Gemini spend** (at most the `countTokens` preflight). "Each reclaim charges a real seconds-long Gemini call" is therefore **false** for the abort path.

2. **The per-doc/day charge cap is gone.** In v4, `INSERT … ON CONFLICT DO NOTHING` made each `(owner,doc,day)` chargeable **at most once/day**, so one owner's max daily ledger contribution was `owned-promoted-docs × est` — far below `daily_cap` for a normal user. v6 charges **every** attempt and re-arms after `LEASE_TTL`, so one `(owner,doc,day)` can be charged `≈ (seconds-in-day / TTL)` times, and one owner can contribute **up to the entire `daily_cap`**.

**Scenario (rate-limited single-user global outage, ~$0 real spend):**
1. A registered free user owns 20 promoted docs (v4/1D quota allows 20 summaries/mo). *(Anon: 2 docs — same attack, slower.)*
2. Attacker requests all 20 serve URLs; each `reserve` commits `est`, then the attacker **aborts before generation** → 20 × `est` added to the **global** `spend_ledger.reserved_cents`, **≈ $0 Gemini**.
3. If `20 × est ≥ daily_cap` the cap trips in one round; otherwise wait `LEASE_TTL` (~180 s), re-view all 20 (leases expired → reclaim → 20 more charges), repeat. `daily_cap/est` charges trip the global cap in `⌈(cap/est)/20⌉ × TTL` — a few minutes for a registered user, ~50 min for a 2-doc anon.
4. `at_capacity` → **every tenant's** serve-side materialization is refused for the rest of the UTC day.

**Why this is High and not Blocking.** It is materially weaker than the v5 Blocking on three axes the mandate cares about: (i) **not instant** — gated to 1 charge / `TTL` / doc by a server-set lease the client cannot shorten; (ii) **owned-doc-bounded amplification** — you need *N* promoted docs, and creating them cost real quota/Gemini; (iii) the money kill-switch's **primary** job — bounding *real* platform spend — still holds (total ≤ cap, monotonic, cannot net-to-zero). So the platform doesn't *bleed money*; the harm is **availability** (other tenants' serve is refused) plus the spec **claiming** a $0 drain is impossible when a slow one is not. It is a genuine regression vs v4's tight per-doc/day bound, surfaced by the exact change this round is for, so it must be resolved or explicitly accepted.

**Fix (needs a decision).**
- **Preferred — bound it, keep the heal.** Add a per-`(owner,doc,day)` **attempt counter** `attempts int` + a small `max_serve_attempts K` (e.g. 3) in `guardrail_config`. The lease still single-flights concurrency; the reclaim path additionally requires `attempts < K` before charging + regenerating (`attempts >= K` → an `at_capacity`/`exhausted`-class status, no more charges today). This caps one owner at `owned-docs × K × est`/day — restoring v4's bounded property — while still healing transient failures `K−1` times. It composes cleanly with the lease (the counter lives on the same marker row).
- **Alternative — accept + defer, but correct the spec.** If the team accepts the rate-limited single-user drain as within the shared-cap risk already scoped to **1G** (anon-abuse controls / rate-limiting, §9), then §4.1/§3 D10 **must** (a) drop the "each reclaim = a real Gemini call, never a $0 drain" framing — replace it with the true bound: "the charge commits at reserve, before generation, so a charge can cost ~$0 real Gemini; the actual bounds are the `LEASE_TTL` rate-limit per doc and the owner's promoted-doc count, and total spend ≤ `daily_cap`"; and (b) record "a single owner can drive the whole shared daily cap → serve-side outage for all tenants" as an explicit, owner-assigned **deferred 1G risk**. Silent over-claiming is not acceptable for a money-path spec.

Re-review the chosen path under the §8 money-path trigger: confirm the bound cannot be exceeded and that the abort-after-reserve $0 charge is either counted-and-capped (`K`) or explicitly accepted.

---

## MEDIUM

### M-1 — Over-`TTL` honest double-generation is **not** benign "last-writer-wins": both attempts share the **deterministic** staging key `_staging/models/{base}.json`, so the second `promote()` can hit *move-source-missing* and throw → a spurious 500 for the second viewer — CORRECTNESS · **NEW interaction the lease's over-TTL branch exposes**

**Where:** §4.2 step 5 ("a rare over-TTL generation may double-generate (**last-writer-wins, bounded**)") + §4.1 step 5 ("stage → verify → promote"). Ground truth: `lib/html-doc/model-store.ts:23` `MODEL_KEY = models/${base}.json` (deterministic); `lib/storage/supabase/supabase-blob-store.ts:37` `putStaged` uses `tempKey = _staging/${key}` (**also deterministic — same for both concurrent generators**); `promote` (`:44`) is `finalExists ? cleanup+return : move(from,to)` where `move` = copy+**delete** (non-atomic).

**Scenario:** Honest generation A exceeds `LEASE_TTL`; viewer B reclaims the (now-expired) lease → `reserved` → B also generates. Both write the **same** `_staging/models/{base}.json` (upsert, last write wins the staged bytes — fine). Then:
- B `promote`: `finalExists`? **false** (A hasn't promoted yet) → proceeds to `move`.
- A `promote`: `finalExists`? **false** → `move(_staging/…, models/…)` → copies then **deletes** `_staging/…`.
- B `move(_staging/…, models/…)` now runs with its **source already deleted by A** → Supabase `move` returns an error → `promote` **throws** → B's request 500s.

The *final* blob is a valid model (no corruption, isolation intact), and the cost is cap-bounded (two charges). But the spec asserts the double-gen is a "benign wasted duplicate"; the shared deterministic `tempKey` means it can instead **500 the loser**. B retrying gets the now-present final (served), so user impact is one transient 500 then success — hence Medium, not High.

**Fix:** Either (a) make the staging key **attempt-unique** (e.g. `_staging/${key}.${randomSuffix}`) so concurrent generators don't collide, or (b) harden `promote` to treat a `move` "source not found" error as: re-check `finalExists`; if the final is now present, return success (last-writer-wins) instead of throwing. Add a behavior/test row for "two concurrent generators (over-TTL reclaim) → both promote paths resolve to a served 200, no 500." (Option (b) is the smaller change and also protects other concurrent-promote callers.)

### M-2 — Carryover (v5 M-3): the reserve promoted-check TOCTOU still has an **unmapped `denial` branch** — reserve can return a not-owned/absent/not-promoted denial mid-serve after the route already saw `promoted`, and step-5 handling enumerates only `in_flight | at_capacity | reserved` → risk of a 500 — CORRECTNESS · unchanged since v5

**Where:** §4.1 step 4 (route reads `summaryMd.status === promoted`) vs §4.2 step 2 (reserve independently re-reads `data->…->>'status' = 'promoted'` → "generic denial" if not). A concurrent resummarize can demote between the two reads. §4.1 step 5's status switch names `in_flight`, `at_capacity`, `reserved` — a **denial** return (or a `RAISE`) is not mapped.

**Why Medium:** no cost leak (denial → no charge), narrow window, but an unmapped RPC return in the money path is exactly what surfaces as a 500. **Fix:** enumerate it — reserve denial mid-serve → **503 "not ready, retry"** (same as the step-4 `committed` case), never 404/500; add a behavior row. (If reserve `RAISE`s the denial, the route must catch and map it, not bubble a 500.)

---

## LOW

### L-1 — The savepoint MUST enclose **step 4** (the `INSERT … ON CONFLICT DO UPDATE`), not just the ledger UPDATE — else a cap-refused **reclaim** leaves a *fresh* non-expired lease that blocks **that owner's** regeneration for a full `TTL`; and the B7c test phrasing "no leftover marker" is wrong for the reclaim case — CORRECTNESS/test · confirms the mandate's rollback question

The mandate asks whether a cap-refused reclaim rollback restores the prior **expired** lease or leaves a fresh one that bricks the doc. **Answer: it restores the prior expired lease — correctly — *iff* the savepoint/sub-block encloses the step-4 marker mutation.** Subtransaction rollback (PL/pgSQL `EXCEPTION` block) reverts *all* changes since the implicit savepoint, so if step 4 is inside, a `RAISE` at step-5 cap-refusal reverts the `DO UPDATE` and the row's `lease_expires_at` returns to its prior **expired** value → other views (and the same owner) can reclaim. The spec states this ("do the claim (step 4) + charge inside a … sub-block") — **so it HOLDS.** Two residual nits:
- **Implementation guard:** if an implementer scopes the sub-block to *only* the ledger UPDATE (step 4 outside), a cap-refused reclaim leaves `lease_expires_at = now()+TTL` committed → returns `at_capacity` while the row is now non-expired → that **owner's** doc is un-materializable for `TTL` (self-healing, owner-scoped, **not** global — the row is per-`(owner,doc,day)`). Flag as a hard implementation requirement + test.
- **Test phrasing:** §4.2's test list says cap-refusal "**rolls back the lease claim (no leftover marker)**." That is right for the *fresh-insert* case but wrong for the *reclaim* case, where the correct post-state is "marker **reverts to its prior expired lease**" (the row still exists). B7c must assert **both**: fresh insert → no row; reclaim → row present with the *prior* (expired) `lease_expires_at`, still reclaimable.

### L-2 — The `RETURNING (xmax = 0) AS inserted` discriminator is **not load-bearing** (both insert and reclaim charge), so its edge cases can't misclassify anything that matters — Confirmation · answers the mandate's xmax question

The mandate asks whether `xmax = 0` reliably discriminates inserted-vs-reclaimed and whether it can misclassify. **It is reliable in the standard case** (a fresh tuple has `xmax = 0`; an `ON CONFLICT DO UPDATE` tuple carries the updating xid, `xmax ≠ 0`), **but v6 never branches on it** — §4.2 step 4 sends **both** "row inserted" and "row reclaimed" to step 5 (charge). The load-bearing signal is purely **row-returned vs no-row**: a false `WHERE lease_expires_at < now()` (live lease) skips the `DO UPDATE` and returns **no row** → `in_flight`; any returned row → generator. That row-presence semantics is exact and well-defined. So even if `xmax` were misclassified in some exotic concurrent-locker case, no decision changes. Recommendation: keep `inserted` only as an observability field; do not let any future logic branch on it without re-review.

### L-3 — Carryover (v5 L-3): `magazine_est_cents` still an un-pinned "derived roughly" value, gated on the B5 caps actually landing — CARRYOVER · unchanged

`generateMagazineModel` today (`lib/gemini.ts:464`) takes caps/signal only via `opts` and defaults `generateJson` `retries = GENERATE_JSON_RETRIES` (`:217`); worst-case = `(GENERATE_JSON_RETRIES+1)` paid calls, so the est derivation is only meaningful once B5's `maxOutputTokens` bound lands. Accepted under the approximate posture; pin the number in §4.2 and gate it on B5. (Charge-per-attempt makes est *distribution* matter more than in v4, but the daily cap is still the hard bound regardless of est accuracy, so this stays Low.)

### L-4 — Carryover (v5 L-4 / v4 M-3): `readIndex` re-selects by `playlist_key` with no `owner_id` filter (RLS-only defense-in-depth on the index read) — CARRYOVER · unchanged · Low

`playlist_key` is unique per owner, not globally (the `getWorkerStorageBundle` footgun). Under the session client RLS makes it safe; a future refactor passing the wrong client could match a foreign same-keyed playlist. Cheap to make real (`owner_id = auth.uid()` on the index read); still not added.

---

## Claims that genuinely HOLD in v6 (don't re-litigate)

- **No anon-callable release lever (invariant a).** No `release_serve_model` exists; the marker table is force-RLS + `service_role`-only-write; a client cannot delete/void a marker. The v5 instant/free/single-doc/repeatable $0 drain is **unreachable**. Idempotency can only be re-armed by real wall-clock (`≥ TTL`), which is server-set. **B7d confirmed.**
- **Cannot net-to-zero; daily cap is the true bound (invariant b).** No decrement anywhere → `reserved_cents` is monotonic within a UTC day; the conditional `UPDATE … WHERE reserved+actual+est <= daily_cap` keeps total ≤ cap. A `reverse-in-release` cost hole is impossible because there is no release. **PASS** (H-1 concerns *who* consumes the cap and at what real cost, not whether the cap bounds total spend).
- **Lease-boundary double-reclaim serializes to ONE generator.** Two requests both seeing an expired lease both attempt `ON CONFLICT DO UPDATE`. The conflicting row is locked by whichever txn wins; the loser waits, then Postgres re-evaluates the `DO UPDATE … WHERE lease_expires_at < now()` against the **winner's committed new tuple** (EvalPlanQual re-check, READ COMMITTED). The winner set `lease_expires_at = now()+TTL` (future) → the loser's `WHERE` is now **false** → **no row returned** → `in_flight` (no charge). Exactly one generator, one charge. **HOLDS.**
- **Cap-refusal rollback of a reclaim restores the prior expired lease** (savepoint encloses step 4) → no global brick; self-healing, owner-scoped. **HOLDS** (see L-1 for the implementation/test guard).
- **`in_flight` single-flight for concurrent misses.** First caller inserts a live lease → `reserved`; the concurrent caller conflicts on a live lease → `DO UPDATE` `WHERE` false → no row → `in_flight` → 503-retry, no charge, no Gemini. **B6b HOLDS.**
- **Promoted-in-definer + `auth.uid()`-internal owner** (reserve step 1–2) — owned-but-unmaterialized and forged/foreign docs denied (B7b). Unchanged from v5, still holds.
- **CSP** (`default-src/img-src/base-uri/object-src/frame-ancestors/form-action 'none'`, nonce'd script/style, no `unsafe-*`), **Cache-Control private no-store**, **local behavior-parity** (nonce-undefined/dig-true), **MD-blob-missing-behind-promoted → repair-needed** (B13b), **backend precedence** (§5), **model-store principal + putStaged→promote surgery**, **generatorVersion drift-invalidation** — all carried unchanged from v5 and hold. (The one *new* wrinkle in putStaged→promote is M-1's shared-tempKey collision under over-TTL double-gen.)

---

## Bottom line

**v6 genuinely closes the v5 Blocking** (invariant a: no anon-callable release; invariant b: monotonic ledger, cannot net-to-zero, cap is the true bound). The lease's Postgres semantics are correct — the `RETURNING`-row (not `xmax`) is the load-bearing single-flight signal, the boundary double-reclaim serializes to one generator, and the cap-refused-reclaim rollback restores the prior expired lease (no global brick).

**But the redesign surfaces one NEW High (H-1):** charge-per-attempt + TTL-reclaim removes v4's per-`(owner,doc,day)` idempotency, so a single owner can drive the *entire* shared daily cap to `at_capacity` (global serve outage) via TTL-paced reclaims — and because the charge commits *before* generation, an abort-after-reserve makes each charge cost ≈ $0 real Gemini, contradicting the spec's "each reclaim = a real Gemini call, never a $0 drain" rationale. It is strictly weaker than v5 (rate-limited by the server-set lease, bounded by owned-doc count, and the platform's real spend is still capped), so it is **High, not Blocking** — but it is a real availability regression vs v4 and an over-claim in the money-path rationale.

**Convergence: NOT YET — but this is a decision point, not a mandatory redesign.** Per `docs/dev-process.md`, a new High means one more round *or* an explicit accept-and-defer. Resolve H-1 by either (1) adding a bounded per-`(owner,doc,day)` attempt counter `K` (restores v4's tight bound, keeps the heal path — preferred), or (2) explicitly accepting the rate-limited single-user shared-cap drain as a deferred **1G** risk **and correcting the §4.1/§3-D10 rationale** to state the true bound (charge-precedes-generation → possible $0 charge; real bounds = `LEASE_TTL` rate-limit × owned-doc count; total ≤ `daily_cap`). Also close M-1 (attempt-unique staging key or promote move-source-missing hardening) and M-2 (map the reserve-denial-mid-serve branch to 503). If H-1 is bounded (or explicitly accepted with the rationale fixed) and M-1/M-2 resolved, a re-review that surfaces no new Blocking/High converges.
