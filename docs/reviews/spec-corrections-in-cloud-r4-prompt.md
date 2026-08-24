# Adversarial review — corrections-in-cloud **slice A** (round 4, SCOPED)

You are an adversarial reviewer. Find defects. **Read the actual files.**

## This round is deliberately narrow

`docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md` was three slices pretending to be
one. Rounds 1–3 all returned NOT CONVERGED from both halves, and **both halves independently
concluded the document needed splitting rather than another revision**. It was split on 2026-08-23:

- **Slice A** — the attended cloud correction. This document.
- **Slice B** — the unattended/worker path. `docs/backlog.md` #60, blocked on #22.
- **Slice C** — reserve/settle money instruments. `docs/backlog.md` #61.

**Do NOT re-litigate the split, and do NOT re-file findings that belong to B or C.** Three round-3
findings died with it by design and are listed in §0: the unattended-survival falsifier (r3 B2), the
structural-validation throw discarding a generation (r3 B3), and the missing `correction_est_cents`
(r3 H1). Re-filing those is noise.

## What to attack: only what changed since round 3

Commit `88214d2` folded the surviving round-3 residue into slice A. **The primary question is the one
this repo keeps losing on: did these fixes introduce new defects?** The standing count of *"a fix that
moved or reintroduced a defect"* is **seven, three of them caused by a review's own fixes.** Weight
your effort there and nowhere else.

The six changed areas, in rough order of how much new surface they add:

### 1. §4.1 — the claim that two open questions are one existing RPC

The spec now asserts that `update_video_annotations` (`supabase/migrations/0021_cloud_sync_signals.sql:19-56`)
writes **only** the `data` column, and that the `updated_at = now()` statements at `:89`
(`merge_video_data`) and `:149` (`persist_summary`) are both outside it — therefore slice A needs no
schema change and no data migration.

**Verify that independently, in the SQL.** If it is wrong, §8's "no migration of any kind" is wrong
and the plan will be built on it.

Then attack the consequence the spec draws: that because both backends stamp `annotationsEditedAt`
unconditionally on set *and* clear (`0021:35`, `:41-43`; `lib/storage/local/local-metadata-store.ts:139-159`),
the caller must read-before-write and issue **no call at all** when the value is unchanged. Is
read-before-write actually sufficient? Consider concurrency, the `{ found }` return, the sync path
writing the same field, and whether "no call at all" can be observed by a test.

### 2. §2 — the magazine envelope deletion (r3 H7)

The spec now requires the caller to run `blobStore.delete(principal, MODEL_KEY(base))` after a
successful correction, arguing that `isFresh` is `sameTitles && generatorVersion` with no content hash
(`lib/html-doc/read-model.ts:12-25`), so a heading-pinned correction leaves the cache permanently
fresh and serving stale gists.

Attack: is **delete** the right operation rather than regenerate-or-overwrite? What does a concurrent
reader see between the body write and the envelope delete? What happens if the delete fails after the
body was written — is that worse or better than the stale cache it replaces? Does `MODEL_KEY(base)`
use the same `base` the correction path has in hand? Is there a second cache with the same problem?

### 3. §7 — the sync falsifier, split in two (r3 H6)

The inverted row is gone. It is now two rows: *"needsRegen goes true → false after a correction"* and
*"nothing moves on a bare press"* (`mdHash`, `mdGeneratedAt`, `docVersionMajor`, `backfilled`, every
`annotationsEditedAt` entry).

Attack: is the first row actually falsifiable, or does it need a fixture where the hash already
matched — which round 3 called vacuous? Read `lib/cloud-sync/reconcile-class-a.ts` and decide whether
`needsRegen` is reachable in the true state the row assumes. Is the second row's field list complete?

### 4. §2 — a server-side length cap on corrections (r3 M8)

New requirement: reject over-length corrections with 400, matching the client's 1,000
(`components/CorrectionsPanel.tsx:105`). Attack the interaction with the sync path, which also writes
this field, and with rows that **already** hold a longer value.

### 5. §5.4 — `maxDuration = 420`

Derived in a table from two Gemini phases: `fixSummary` 3 attempts (`lib/gemini.ts:473`) and
`extractQuickView` → `generateJson` 3 attempts (`lib/gemini-cost.ts:22`), 60 s each
(`lib/gemini.ts:105`), plus backoff. **Recompute it.** Is 362.4 s right, is 420 s enough, and does the
platform honour `maxDuration` on this route at all?

### 6. §2 — the `signal` now claimed to need wiring in two places

The spec says `fixSummary:496` passes no signal where `generateJson:273` does, and `fixSummary:505` is
a bare `new Promise(setTimeout)` where `generateJson:281` uses `abortableSleep`. Verify both.

## Also required

- **Check every citation the fold-in touched.** The claim in the header — that all ten of round 3's
  line references were correct and have been applied — is itself checkable. Report any that are now
  wrong in the *other* direction.
- **Coherence after surgery.** Six edits landed in one pass on a document that was itself rewritten
  the same day. Look for a section that now contradicts another, a cross-reference to a renumbered
  section, or a claim that survived from v3 into a context that no longer supports it.
- **What slice A still does not cover** — bounded to slice A. Not B, not C.

## Output

**Blocking / High / Medium / Low**, each with file:line, the concrete failure scenario, and a
suggested fix. Mark anything you could not run **NOT VERIFIED**. End with `CONVERGED` or
`NOT CONVERGED`.

If your honest verdict is that slice A is now implementable and the remaining items belong in the
plan rather than the spec, **say that plainly** — this round exists to find fix-induced defects, not
to accumulate a fourth round of findings on a document three rounds have already been spent on.
