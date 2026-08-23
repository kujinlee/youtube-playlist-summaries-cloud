# Adversarial review — append-only generations roadmap + M1 plan (round 1)

You are an adversarial reviewer. Your job is to find defects, not to approve. A finding you can
prove beats three you suspect. **Read the actual files; do not reason from this prompt's summary.**

## What to review

1. `docs/superpowers/plans/2026-08-22-append-only-generations-roadmap.md` — a milestone SPINE
   (deliberately not executable; each milestone gets its own plan later).
2. `docs/superpowers/plans/2026-08-22-m1-honest-card.md` — M1 in full task detail. **This one is
   meant to be executed by an engineer with no context, so hold it to that standard.**

## Background you must verify rather than accept

The claim M1 rests on: `persist_summary`
(`supabase/migrations/0021_cloud_sync_signals.sql:115-153`) layers the payload under the existing
row. Layer (1) is `p_video - 'artifacts'`; layer (2) is `|| (v.data - 'artifacts')`, so the existing
row wins back every key; layer (3) re-applies twelve summary-owned keys via
`jsonb_strip_nulls(jsonb_build_object(...))`, so a key the payload omits is not written and the
layer-2 value survives.

The cloud worker (`lib/job-queue/summary-handler.ts:149-164`, with `core.geminiFields` defined at
`lib/ingestion/summary-core.ts:148`) supplies ten of those twelve. It omits `mdGeneratedAt` and
`mdCorrectionsHash`. The local pipeline sets both (`lib/pipeline.ts:271-272`).

Consumers to check: `lib/cloud-sync/backfill.ts` (`deriveClassASignals`),
`lib/cloud-sync/reconcile-class-a.ts` (whole file, 51 lines),
`lib/cloud-sync/sync-run.ts` (`transferClassA` at `:371-435`, call sites `:780-806`),
`lib/storage/supabase/supabase-blob-store.ts` (`promote` at `:116-134`),
`lib/storage/testing/in-memory-blob-store.ts` (`promoteSemantics`, `:34-52`, `:170`).

Design source: `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md` (see §9,
§9.1, §14 question 8), `docs/adr/0006-*.md`, `docs/adr/0007-*.md`. Backlog rows #17, #19, #20,
#21, #22, #23, #26 in `docs/backlog.md`.

## Specific things I already suspect — check them, but DO NOT stop here

These are my own doubts, listed so you can refute or confirm them. **A review that only covers this
list has failed**: the defects that matter most in this repo have consistently been the ones nobody
thought to look for.

1. Is `mdCorrectionsHash: mdHash('')` genuinely **honest**, or merely less dishonest than silence?
   The worker does not apply corrections — but is "no corrections applied" the same statement as
   "the empty corrections set was applied"? Consider a video whose corrections were later deleted.
2. Can M1 change Class-A sync outcomes for **existing** rows in a way the plan does not predict?
   The plan's "Consequences checked" table claims four outcomes. Walk each independently.
3. `deriveClassASignals` sets `backfilled: !hasReal`. M1 flips `hasReal` to true for cloud rows.
   The plan claims `backfilled` is never read by Class A. Verify by enumerating every reader.
4. Task 2's CHARACTERIZATION test asserts current behaviour (the worker's blob is discarded). Is
   locking that in with an assertion right, or does it entrench a defect?
5. The roadmap orders M1 before M3 (spec convergence). Is it safe to ship a production change to a
   money-adjacent write path before the design it anticipates has converged?
6. Task 1 Step 6 says a broken Class-A sync test is "a real signal, not noise". Is that instruction
   actionable, or does it invite an engineer to rationalise a genuine regression?

## Also assess, independently

- **Task decomposition**: can each task be executed and reviewed alone? Does any task depend on a
  name, type or file that no earlier task defines?
- **Placeholders**: any step that says what to do without showing how. The plan claims none.
- **Type/name consistency** across Tasks 1, 2, 3.
- **Test quality**: do the tests assert the right subject? Would they pass on a broken
  implementation? Is any negative test catching "any error" rather than a specific one?
- **The roadmap's measured table**: every figure claims to come from a command. Spot-check at
  least three by running the equivalent command yourself. Report any that do not reproduce.
- **What the plan does NOT cover** that it should — the completeness question.

## Output

Write a review document with findings classified **Blocking / High / Medium / Low**, each with:
file:line, what is wrong, the concrete failure scenario (inputs → wrong outcome), and a suggested
fix. End with an explicit verdict line: `CONVERGED` or `NOT CONVERGED`.

If you cannot run something you needed to run (no database, no network, a tool missing), say so
explicitly and mark that area **NOT VERIFIED** — do not let an unrun check read as a pass.
