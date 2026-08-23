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

Every figure here came from a command run when this file was written. Re-derive before trusting.

| Fact | Value |
|---|---|
| Spec-local schema | 4 files, 4,108 lines, at `…/2026-08-03-stable-blob-addressing/schema/` |
| Schema shipped as migrations | **none** — highest shipped is `0025_settle_is_observable.sql` |
| `generation_id` in `lib/`, `app/`, `worker/`, `supabase/` | **zero references** (only 2 ratchet scripts + 1 contract test) |
| App code addressing blobs by `base`/`summaryMd` | **192 call sites across 40 files** |
| Spec convergence | rounds 1–9 all NOT CONVERGED; round 10 marked mandatory |
| ADR-0006 status | `proposed` |
| Unit suite | 2,722 tests / 268 suites, green |
| Production | Fly `v7` (2026-08-18), holds **paid** Gemini content |

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

### M1 — The honest card ✅ plan written

**Plan:** `docs/superpowers/plans/2026-08-22-m1-honest-card.md`

The cloud worker omits `mdGeneratedAt` and `mdCorrectionsHash`; local sets both
(`lib/pipeline.ts:271-272`). Because the payload is silent, `persist_summary`'s layer-2
(`0021:117`) preserves whatever the previous writer left, so the row's provenance can describe a
body that is no longer there. Make the worker stamp its own.

- **No schema. No migration. One object literal plus tests.**
- **Kills:** backlog #19's live harm; backlog #23 clause (a).
- **Does not kill:** #23 clause (b) — carrying corrections forward is still unaffordable.
- **Gate:** dual adversarial review; branch + PR.

### M2 — Corrections as deterministic `{from,to}` pairs

Backlog #23 proper. An LLM authors the pairs (~50 output tokens); application is deterministic,
word-boundary, case-preserving, and **never lets the model rewrite the document** — headings are an
identity anchor (spec §4.2.1) and a reworded heading orphans paid digs.

- Includes re-authoring the **99 existing free-form corrections** and recomputing their hash.
- **Kills:** #23 entirely. Unblocks spec §5.2.2 — without it a generation costs a whole-document
  Gemini round trip to publish.
- **Needs its own spec first** (status cell says so).

### M3 — Converge the design

Spec round 10 (mandatory; rounds 1–9 all NOT CONVERGED), then ADR-0006 → `accepted`.

- **Point round 10 at the ranking that computes `current`.** Append-only moves the entire
  correctness burden there: the spec claims the result is *"identical for every reader, on every
  replica, forever"*, which holds only if the ordering is **total and deterministic** — and
  `mdGeneratedAt`, the field M1 is about, is exactly the kind of key that ties.
- **Kills:** whatever round 10 dissolves. Historically this has been the highest-yield step —
  §14 q8 dissolved most of a five-round CAS spec.
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

- **Any work item for backlog #19.** There is nothing to build for it. Its corrections half is M1,
  its addressing half is M5. It is a symptom and should be re-filed as such, not worked.
- **Un-entangling the rest of the backlog.** That is the milestone contract's job, one boundary at
  a time.

## Known stale artifacts to fix at the M1 boundary

Surfaced 2026-08-22 while investigating #19; none filed yet, all misleading as they stand:

1. `scripts/gen-backlog-page.py:358` — `DEPENDS[19]` says `survives`; under §5.2 it is `dissolved-by`.
2. Same file, `ROOTS` — the root is drawn with no parents; #23 gates it (roadmap :1018).
3. `docs/backlog.md` #17 — still describes *"publication is a conditional update on one row"*, the
   CAS design round 4 deleted.
