# Append-Only Generations — Milestone Roadmap

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

### M2 — Corrections work in the cloud ◀ **THE WORK STARTS HERE**

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
| **A** | the attended cloud route — the feature | **specced**, `…-corrections-in-cloud-design.md`. Post-hoc spend recording, no reservation protocol (user decision 2026-08-23) |
| **B** | the unattended correction, in the worker | backlog **#60** — **blocked on #22** |
| **C** | reserve/settle, `correction_est_cents`, the `cap-soundness` extension, the duration ratchet | backlog **#61** — a money-path slice |

- **Next action:** slice A's spec has round-3 residue to fold, then `writing-plans`.
- **Kills:** #23's representation clause, **rejected** rather than deferred. ⚠ It does **not** kill
  #23's own optimisation request — the occurrence check is descoped, see spec §1.2.
- **No 99-correction migration.** The field keeps its type, so nothing needs re-authoring.

### M3 — Discharge the design gate (smaller than it looks)

⟳ **Corrected after round 1.** This milestone previously read *"run spec round 10"*, taken from a
memory note rather than the review directory. Seventeen rounds have run. The latest
(`docs/reviews/spec-blob-addressing-r17-coordinator.md:3`) does **not** ask for an eighteenth:

> *"apply round 17's findings, then stop reviewing this document and start task #36. Blockings across
> rounds ran 4 → 3 → 1 → 1, and the residue is specification-of-implementation rather than
> decision-making. **The next genuine test is the migration, not round 18.**"*

So M3 is: **apply r17's residue, then set ADR-0006 to `accepted`.** No new review round.

- ~~Point the next round at the ranking that computes `current`.~~ **Withdrawn — refuted by the
  schema.** `video_summary_current` (`…/schema/04_artifacts.sql:695-782`) already orders by
  corrections-currency, then `doc_version_major`, then the card's `mdGeneratedAt`, then
  `produced_at`, then `generation_id` — which is unique per generation, so the ordering is already
  **total**. The `mdGeneratedAt` rung was introduced by round 5 finding B3 and revisited in round 15.
  The concern was three rounds behind the document.
- **Kills:** whatever r17's residue dissolves.
- **Gate:** Phase 1 exit. Human approval on the ADR status change.

### M4 — Promote the schema

The four spec `schema/*.sql` files become migrations `0026+`. `05_assert.sql` gets a home in CI or
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
