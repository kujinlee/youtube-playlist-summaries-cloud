# Append-Only Generations — Milestone Roadmap

> **Anchor:** `stable-blob-addressing` — **ADR:** 0006, 0007
> **Goal:** A blob's address stops moving when a title or a serial number changes. THIS IS THE MILESTONE SPINE (M1-M7) for that goal.

> **This is a SPINE, not an executable plan.** It names the milestones and what each one makes
> moot. Each milestone gets its own detailed plan under `docs/superpowers/plans/` before it starts;
> only M1 has one today (`2026-08-22-m1-honest-card.md`). Do not execute from this file.

**Goal:** Move blob addressing from mutable `<serial>_<slug>` to immutable per-generation addresses
with append-only publication, so two concurrent writers can neither destroy each other's paid work
nor leave a row whose card and body came from different runs.

**Why one sentence keeps recurring:** *the blob address is derived from mutable data* — `serial` and
`slug` both move, and one mutable row describes whatever body landed last. Roadmap :722 records that
every hard defect of the last three weeks reduces to it.

**Architecture:** address is `<tenantId>/videos/<videoId>/<generationId>/…`; a run produces a
**generation** = body **and** card together, inseparably (spec §5.2, closing §14 q8 on 2026-08-05);
publication is **append-only** and `current` is a **view** computed by ranking generation rows
(spec §5.1, round 4). No CAS, no loser, nothing to re-run.

**Source of truth:** `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md`
(+ its `schema/` — 4,108 lines of executable SQL), ADR-0006, ADR-0007.

---

## Measured starting position (2026-08-22, commit `9211f74`)

**Each row carries the command that produced it** — round 1 of review found a figure that did not
reproduce, and the defect was the missing command, not the number. Re-run before trusting.

| Fact | Value | Command |
|---|---|---|
| Spec-local schema | 4 files, 4,108 lines | `wc -l docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/*.sql` |
| Schema shipped as migrations | **none** — highest is `0025_settle_is_observable.sql` | `ls -1 supabase/migrations/*.sql \| tail -1` |
| `generation_id` in shipped code | **zero references** (2 ratchet scripts + 1 contract test only) | `grep -rli "generation_id" --exclude-dir=node_modules --exclude-dir=docs .` |
| Blob addressing by `base`/`summaryMd` | **40 files**; call-site count varies with the pattern — 192 for the three-term grep below, 203 for a broader one. Treat the file count as the figure. | `grep -rln "summaryMd\|baseName\|baseOf(" lib/ app/ worker/ components/ --include=*.ts --include=*.tsx \| wc -l` |
| Spec convergence | rounds **1,2,3,4,7,8,10,12,13,14,15,16,17** all NOT CONVERGED. **r17 does not ask for r18** — see M3 | `ls -1 docs/reviews/spec-blob-addressing-r*-coordinator.md` |
| ADR-0006 status | `proposed` | `head -3 docs/adr/0006-*.md` |
| Unit suite | 2,722 tests / 268 suites, green | `npm test -- --ci --json --outputFile=jest-results.json` |
| Production | Fly `v7` (2026-08-18), holds **paid** Gemini content | `flyctl releases --app youtube-playlist-summaries` |

**Read this table as the reason the work is large:** the design is finished and the product is
entirely un-migrated. T1–T4 are marked complete because they were implemented *against the
spec-local schema*, which has never touched a database.

### ⟳ Re-measured 2026-08-24, commit `aaf3422` — four rows moved

The table above is a dated snapshot and is kept as one; this is the delta. **Nothing that makes the
work large changed** — the schema is still un-migrated and `generation_id` still has zero references
in shipped code.

| Fact | 2026-08-22 | 2026-08-24 | Why it moved |
|---|---|---|---|
| Highest migration | `0025_settle_is_observable` | **`0026_record_correction_spend`** (26 files, **0** defining `video_artifacts`/`video_generations`) | M2 slice A |
| Unit suite | 2,722 / 268 | **2,819 / 274** | M2 slice A |
| Production | Fly `v7` (2026-08-18) | **Fly `v10`** (2026-08-24) | M2 slice A, then two fixes found by pressing it live |
| ADR-0006 status | `proposed` | ✅ **`accepted`** (later the same day, M3) | M3 discharged the gate |

⚠ **`0026` is taken, so M4's "migrations `0026+`" now means `0027+`.** Corrected in M4 below.

---

## The milestone contract

**At every milestone boundary, before starting the next one:**

1. Re-read `docs/backlog.md` (and the rendered `backlog-table` page).
2. For each open item, ask: *did this milestone delete it, shrink it, or leave it untouched?*
3. **Delete or revise in the same turn.** A row that survives a milestone it should not have is the
   defect this roadmap exists to stop — see `a-convention-catches-what-you-read`.
4. Update `DEPENDS`/`ROOTS` in `scripts/gen-backlog-page.py` so the graph matches.
5. Tick the milestone here and close its task.

This inverts the usual order deliberately: **the plan drives, the backlog is reconciled behind it.**
Decided with the user 2026-08-22 after an investigation of backlog #19 spent longer on stale
cross-references than the fix would have taken.

---

## Milestones

### M1 — The honest card ⛔ RE-SCOPED AND DEFERRED 2026-08-22 (user decision)

**Do not execute `docs/superpowers/plans/2026-08-22-m1-honest-card.md`.** It is retained as the
record of why, not as instructions.

**What happened.** Two dual-adversarial rounds, and each killed the *mechanism* rather than the
details — v1 stamped unconditionally (wrong: `promote` is create-if-absent, so the bytes usually
never land); v2 stamped conditionally (wrong: the consumer reads
`video.mdGeneratedAt ?? video.processedAt`, `backfill.ts:13`, and `processedAt` is stamped
unconditionally anyway, so the silence reaches nobody). Blockings went **2 → 3** across the rounds —
the opposite of a convergence curve. Reviews: `docs/reviews/plan-append-only-m1-r{1,2}-{codex,claude}.md`.

**The root cause is scope, not defects.** M1 was framed as *"the two omitted fields"*. The real
shape is that **all twelve card fields are written unconditionally for a body that may never have
been published.** Gating two of twelve is a symptom patch, and the coherent version is a money-path
change: withholding `docVersion` stops the idempotency skip firing
(`summary-handler.ts:86-92`), so the next attempt re-runs Gemini and charges again.

**Where its content goes.** The coherent version — *"the card is written as a unit, gated on
publication"* — would also close backlog #22's row-lies-about-`docVersion` half. It is a real slice
needing its own spec, and it is **superseded by M5** (a generation carries card and body
inseparably, §5.2), so it should only be revived if M5 slips badly. Nothing is lost by deferring it;
the live harm it targeted has been live for months and M5 dissolves it properly.

**The measured lesson, for the next milestone plan:** both rounds' fixes were *"certified complete
by tests that measure the mechanism instead of the outcome"* (round-2 reviewer). A test that proves
the payload changed is not a test that proves the consumer sees it. **Assert at the consumer.**

The cloud worker omits `mdGeneratedAt` and `mdCorrectionsHash`; local sets both
(`lib/pipeline.ts:271-272`). Because the payload is silent, `persist_summary`'s layer-2
(`0021:117`) preserves whatever the previous writer left, so the row's provenance can describe a
body that is no longer there. Make the worker stamp its own.

⟳ **Corrected after round 1.** The stamp must be **conditional**: `SupabaseBlobStore.promote` is
create-if-absent (`supabase-blob-store.ts:120-123`), so the worker's bytes often never become the
live body, and stamping for a body it did not publish is worse than the silence it replaces.

- **No schema. No migration.** One guarded stamp plus tests.
- **Kills:** **backlog #23 clause (a)** — for `mdCorrectionsHash`. *(v1 credited this to #19; wrong
  row. #19 is the `transferClassA` content race and has no corrections half.)*
- **Does not kill:** #23 clause (b), the affordability redesign — that is M2. Nor the five other
  optional layer-3 fields that inherit the same way; M1 files those as a new row.
- **Gate:** dual adversarial review; branch + PR.

### M2 — Corrections work in the cloud — ✅ **SLICE A SHIPPED 2026-08-24**

⟳ **REWRITTEN 2026-08-23. The `{from,to}` pairs design this entry used to describe was REJECTED, and
the two facts justifying it were both wrong.** Kept short here; the reasoning is in
`docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md` §0–§1.

- *"Unaffordable by construction"* → **≈0.6¢** per generation. Wasteful, not unaffordable.
- *"A reworded heading orphans paid digs"* → **overstated**. The dig blob is keyed on `startSec`;
  titles are identity in two fallbacks only.
- And pairs **cannot express** *"reword this section"*, so against a requirement of behavioural
  parity with local they are a feature restriction rather than an improvement.

**So `fixSummary` stays** and the work is making it reachable from cloud. Three Phase-1 rounds
(26 → 33 findings, all NOT CONVERGED, Phase 6 fired) established that this is **three slices**:

| | | State |
|---|---|---|
| **A** | the attended cloud route — the feature | ✅ **SHIPPED 2026-08-24** — all 12 tasks, PR #134; prod **v8 → v10** |
| **B** | the unattended correction, in the worker | backlog **#60** — **blocked on #22** |
| **C** | reserve/settle, `correction_est_cents`, the `cap-soundness` extension, the duration ratchet | backlog **#61** — a money-path slice |

**⭐ Slice A shipped, and pressing it live found two defects 2,808 green tests could not.** Both are
worth carrying into every later milestone:

- **The model fenced the corrected document in ```markdown in 6 of 8 real rolls** — invisible because
  *every* test mocks `lib/gemini.ts`. Fixed at the transport seam (`unwrapFencedDocument`, PR #138).
  The lesson is the memory `a-mocked-boundary-tests-the-contract-you-imagined`: **sample the real
  call before believing a green suite about a model's output.**
- **The structural validator compared `▶` timestamps by count, not by bytes**, so a rewritten
  timestamp URL passed (PR #139). M5 and M6 both move documents; a validator that admits a corrupted
  one is worse than none.

Also filed from the live press, and **not** blockers for M3: backlog **#62** (a failed correction can
evade the per-owner bound) and **#63** (the validator's raw string reaches the client).

- **Next action:** **M3** — apply round 17's residue and set ADR-0006 `accepted`. Slices B and C stay
  backlog rows; neither gates M3.
- **Kills:** #23's representation clause, **rejected** rather than deferred. ⚠ It does **not** kill
  #23's own optimisation request — the occurrence check is descoped, see spec §1.2.
- **No 99-correction migration.** The field keeps its type, so nothing needs re-authoring.

### M3 — Discharge the design gate — ✅ **DONE 2026-08-24**

**ADR-0006 and ADR-0007 are both `accepted`.** Phase 1 is closed; no round 18 was run, per round 17's
own recommendation.

⭐ **What M3 turned out to be, measured rather than assumed.** Eight of round 17's nine findings
(B1, H1, H2, H3, M1, M2, M3, L1) were **already folded into ADR-0007** by `efee284` and the
implementation slice `1a7c076` — verified by reading the ADR for each finding's marker, not by
re-applying them. **Exactly one residue was live**, and ADR-0007 named it precisely: H4's knock-on in
the *design spec*, not the ADR. §5.1's rule 19 still asserted *"a crash before recording leaves
nothing — no bytes, no row, no orphan — so spending again is correct rather than a double-charge"*,
which `pending`'s deletion makes **false**; and knock-on (a) still said §8's grace period was narrowed
because *"that state no longer exists"*, when the deletion makes that state **return**. Both are
corrected in place, struck through rather than rewritten, with the residual bounded and named
(`summary_max_attempts` = 1, `max_serve_attempts` = 5) and the mitigation honestly labelled
**specified, not implemented**.

**The lesson for M4-M7:** a finding assigned to "the same slice" lands in whichever document the
sentence lives in — and ADR-0007 said *design spec §5.1*, which is not where anyone was looking.
Read the finding's own words for the file, rather than assuming the ADR is the target.

#### The record of how M3 was scoped, kept because it is what made it small

⟳ **Corrected after round 1.** This milestone previously read *"run spec round 10"*, taken from a
memory note rather than the review directory. Seventeen rounds have run. The latest
(`docs/reviews/spec-blob-addressing-r17-coordinator.md:3`) does **not** ask for an eighteenth:

> *"apply round 17's findings, then stop reviewing this document and start task #36. Blockings across
> rounds ran 4 → 3 → 1 → 1, and the residue is specification-of-implementation rather than
> decision-making. **The next genuine test is the migration, not round 18.**"*

So M3 was: **apply r17's residue, then set ADR-0006 to `accepted`.** No new review round. ✅ Both done.

- ~~Point the next round at the ranking that computes `current`.~~ **Withdrawn — refuted by the
  schema.** `video_summary_current` (`…/schema/04_artifacts.sql:695-782`) already orders by
  corrections-currency, then `doc_version_major`, then the card's `mdGeneratedAt`, then
  `produced_at`, then `generation_id` — which is unique per generation, so the ordering is already
  **total**. The `mdGeneratedAt` rung was introduced by round 5 finding B3 and revisited in round 15.
  The concern was three rounds behind the document.
- **Killed:** ADR-0006 `proposed` → `accepted`; ADR-0007 with it (its status said the two stand or
  fall together); **ADR-0002 becomes PARTLY superseded** — only its *rejection* of video-level
  shared summaries falls, and its `(playlist_id, owner_id)` cross-tenant guard STANDS.
- **Gate:** Phase 1 exit. ✅ Human approval given 2026-08-24.

### M4 — Promote the schema — ⏳ **PR #155 OPEN, NOT MERGED** (merging is a human gate)

> **STATUS 2026-08-27 — `0027` EXISTS, ALL TEN PLAN TASKS DONE, ALL FOURTEEN GATES GREEN.**
> The migration is written, applied locally, proven in both directions, and reviewed to round 11.
> **Production is untouched: release v10, schema `0026`.** M4-β is a SECOND human gate, after merge.
>
> | | |
> |---|---|
> | Plan of record | [`plans/2026-08-25-m4-promote-the-schema-v2.md`](2026-08-25-m4-promote-the-schema-v2.md) — rewritten from ADR-0011 (corrections stay per-playlist), supersedes v5.1 |
> | Merged so far | PR #150 (plan) · #152 (derived manifest) · #153 (round-4 fixes) · **#154 (rounds 5+6, squash `74f450b`)** — **tooling only, no migration** |
> | **OPEN** | **PR #155**, branch `docs/m4-round7`, 31 commits. **Carries `0027` itself** — 1,898 lines, 161 catalog objects |
> | Review rounds | **v2 rounds 1-11.** Rounds 10 and 11 were whole-branch and scoped-to-fixes respectively; both halves ran in both |
> | ⭐ What 2 rounds of review found | **1 Blocking · 8 High · 8 Medium · 6 Low — and NOT ONE was in `0027`.** Every finding was in an INSTRUMENT. Both halves of both rounds independently confirmed the migration: the three `backfill → set not null` pairs are FK-protected upstream and cannot abort; `0027`'s entire pre-M4 footprint (3 columns, 2 FKs, 7 triggers) is in the manifest; the rebuilt base is definitionally identical to the applied `0027` across all 161 objects |
> | ⚠ Each fix round caused the next round's worst finding | r10 H2's `set -uo pipefail` → **r11 B1**, gate 14 green over the violation it detects. r10 H4's regex scanner → **r11 H1**, 240 real comments misread. That is `portable-practices` §12, measured twice in one evening |
> | Phase 6 | ⚠ **CORRECTION 2026-08-25 21:30.** This row previously read *"fired at round 4 and has not run"*, and I repeated that in three commit messages and to the user. **It is false.** Phase 6 **RAN** — [`../../reviews/architecture-review-2026-08-25.md`](../../reviews/architecture-review-2026-08-25.md), 17:54 — after the v5.1 sequence. It dissolved nine of eleven findings into one defect, produced **ADR-0011** (accepted, option (a)) and, as its finding 3, **`check-live-schema.py` itself**. Its disposition — *"M4 does not proceed to a v6, rewrite the plan from the decision"* — is why the v2 plan exists. The trigger has now fired a SECOND time, on the v2 sequence, and the second review's subject is different: the first was about `corrections`/`workspace_videos` composition; rounds 5-7 are entirely about **the gate instrument the first review prescribed** |
> | The gate that now exists | `scripts/check-live-schema.py` — the SUBJECT axis. The other six gates rebuild from spec files and cannot answer *"did the migration apply?"* Verified against production read-only: **prod is pre-M4** |
> | Next | **The human merge gate on PR #155.** After merge: M4-β (plan Task 9 steps 6-7) — `supabase db push --linked`, then `check-live-schema.py --prod --expect-present` and `check-anon-exposure.py --prod`. Both are the user's calls |
> | Deferred out of this PR, by decision | **Instrument hardening as its own slice** (user, 2026-08-27) — r10 L1's leaked-base sweeper (task #145), and any round 12 on the round-11 fixes. The reasoning is the row above: the defects are in the gates, not in the thing being gated, and `0027` is what this PR ships |
>
> ⛔ **Task 6 WAS the point of no return for every developer's local stack, and it has been crossed**
> (`6bf4e18`): `npm run test:integration` now applies M4 on every machine that runs it. Merging is a human gate;
> applying M4-β to production is a second one.
>
> **Why five rounds.** Every round found that the previous round's FIX was the defect — five of round
> 5's nine findings were round 4's repairs. The gates are all predicates over a *projection* of the
> database, and each fix widened the projection just far enough to cover the counter-examples already
> seen. See [`../../reviews/plan-m4-v2-r5-coordinator.md`](../../reviews/plan-m4-v2-r5-coordinator.md).

The four spec `schema/*.sql` files become migrations **`0027+`** (⟳ was `0026+`; `0026` was taken by
`record_correction_spend` in M2 slice A). `05_assert.sql` gets a home in CI or
`scripts/check-schema-gates.sh`. No application caller yet — the schema lands inert.

- **Carries task #45's coupling:** the `doc_key` re-key must ship with the `inflight_uq` deletion.
- **Arms backlog #26** — from here on, a caller reaching `record_artifact` is a 5× spend ceiling
  nobody chose. #26 must close before M7.
- **Kills:** nothing yet. This is the step that makes M5 possible.

### M5 — Write-path cutover

Move every writer onto generations: `summary-handler.ts`, dig generation, `transferClassA` and
`copyAdditiveVideo` in `sync-run.ts`, the regenerate route. `persist_summary` is replaced by the
generation write.

- **Kills:** #20 (title-change orphaning), #21 (dig writes), #22, and #17's residue — all four are
  `dissolved-by`/`partly-dissolved-by` this root in `gen-backlog-page.py`.
- **Kills #19 outright** — its remaining half is exactly "the card can be torn from the body".
- Largest single milestone. Expect to decompose it into its own multi-task plan.

### M6 — Read-path cutover

`current` becomes a computed view. Every reader changes shape: serve, share, PDF, download,
dig-state, `deriveClassASignals`, `readIndex`. The local FS store keeps human-readable
`003_alpha.md` names for Obsidian (ADR-0006), so the manifest becomes a mapping layer.

- **Kills:** #52 unblocks; backlog #25 (render addressing) is decided here.

### M7 — Backfill, GC, and ship

Backfill every existing video into a generation row with its card attached; §8 mark-and-sweep GC
(two items the spec itself marks OPEN); close **#26**; migrate prod.

- ⚠ **Prod holds paid content. A wrong backfill costs real money.** Dry-run against a throwaway
  project first (see the `staging-supabase-project` memory for the pattern).
- **Human gate** — outward-facing and hard to reverse. Do not migrate prod without explicit
  approval, per `docs/dev-process.md` Phase 5.

---

## What is deliberately NOT in this roadmap

- **Any work item for backlog #19.** There is nothing to build for it. Its addressing half dissolves
  at M5; the corrections defect that looks like it is **#23 clause (a)**, a different row. #19 is a
  symptom and should be re-filed as such, not worked.
- **Un-entangling the rest of the backlog.** That is the milestone contract's job, one boundary at
  a time.

## Known stale artifacts to fix at the M1 boundary

Surfaced 2026-08-22 while investigating #19; none filed yet, all misleading as they stand:

1. `scripts/gen-backlog-page.py:358` — `DEPENDS[19]` says `survives`; under §5.2 it is `dissolved-by`.
2. Same file — the root is drawn with no parents, but #23 gates it (roadmap :1018). ⚠ **This edge
   cannot be expressed**: `DEPENDS` is `item → (relation, root, note)` and `ROOTS` has no parent
   field, so there is no way to say a root is blocked by an item. Record it as prose in the root's
   `detail` and file the structural gap separately — do **not** reverse the arrow.
3. `docs/backlog.md` #17 — still describes *"publication is a conditional update on one row"*, the
   CAS design round 4 deleted.
4. **This roadmap itself carried two:** the convergence row was seven rounds stale, and M3's one
   technical instruction was refuted by the schema it pointed at. Both were caught by round 1, not
   by any script. Both are fixed above.
