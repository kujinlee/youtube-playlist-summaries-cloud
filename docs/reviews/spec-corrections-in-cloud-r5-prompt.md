# Adversarial review — corrections-in-cloud **slice A**, round 5. SCOPED TO ONE BLOCK.

You are an adversarial reviewer. Find defects. **Read the actual files.**

## Read ONLY this, and attack ONLY this

`docs/superpowers/specs/2026-08-22-corrections-in-cloud-design.md`, **§2's block headed
`#### ✅ DECIDED 2026-08-23 (user) — option (e)`**, plus the §5 and §7 rows that depend on it.
Everything else in the spec is out of scope for this round. Commit `9eb11d2` is the change.

Rounds 1–4 are on disk (`docs/reviews/spec-corrections-in-cloud-r{1,2,3,4}-*`). Round 4 returned
NOT CONVERGED from both halves with 2 Blocking; those are fixed and are **not** yours to re-file.

## Why this round exists

Round 4 found that **the magazine-invalidation design was built on a false premise** — the spec said
*"there is no content hash"*, when `sourceMdHash` has existed on the envelope since Stage 3 and only
`isFresh` ignores it. The user then chose option (e). The design below was derived **in one pass, by
me, without a review**, and it is the third different answer this question has had in two days.

**Assume it is wrong somewhere. Your job is to find where.**

## The design, stated so you can attack it precisely

1. `isFresh` (`lib/html-doc/read-model.ts:20-25`) gains one conjunct:
   `(envelope.sourceMdHash === undefined || envelope.sourceMdHash === currentMdHash)`.
2. `readFreshMagazineModel` takes `currentMdHash`. Claim: its only two callers are
   `lib/html-doc/serve-doc.ts:78` and `:141`, both inside `resolveModel`, whose `mdBody: string` is a
   **required** param (`:67`, destructured `:70`) — so the hash is available at both.
3. **The correction path writes no envelope at all.** Invalidation is derived from the body write.
4. `readTitleStableModel` (`:57-69`) is untouched, so `/s/<token>` and the `owner_over_budget`
   fallback keep serving.

## Attack these, hardest first

**A. Is claim 2 complete?** I grepped `lib/`, `app/`, `components/`. **Check tests, scripts, e2e
fixtures, and any dynamic/re-exported reach.** A caller I missed is a compile break at best and an
uncapped behaviour change at worst. This exact question — *"what else touches this?"* — produced both
of round 4's Blockings, so treat my grep as a hypothesis.

**B. Can this regenerate more than once per correction — i.e. is there a charge loop?** I argue no,
because both writers build fresh object literals (`serve-doc.ts:174-182`, `generate.ts:50-60`) with no
spread. **Verify that, and then look for the case I did not:** what if `mdBody` at serve time is not
byte-identical to the `mdBody` the envelope was written from for reasons unrelated to corrections —
normalisation, line endings, a callout re-inserted at read time, `parsed.sourceMd` vs the raw blob?
**If `mdHash(mdBody)` is not stable across two serves of an unchanged document, every serve
regenerates and every serve charges.** That is the failure mode that would matter most, and I have not
proven it cannot happen.

**C. `sync-run.ts:464` ships a whole envelope between sides** (`decideCompanion` → `kind: 'ship'`).
Does adding this conjunct change companion behaviour, cause double regeneration across local+cloud, or
interact badly with `decideCompanion`'s own `sourceMdHash` tests (`lib/cloud-sync/companion.ts`)? Two
mechanisms now read the same field for related-but-different purposes.

**D. The local path.** `generate.ts:59` writes `sourceMdHash: mdHash(md)` unconditionally, but the
local pipeline has no caps and no reserve. Does making `isFresh` stricter change local behaviour —
extra local Gemini calls, a re-render loop, or a behaviour difference between local and cloud that the
spec does not mention?

**E. The unmeasured wave.** The spec admits, marked NOT VERIFIED, that every already-drifted document
pays ~6¢ once on its next owner serve, and defers counting to a plan task. **Is deferring the
measurement legitimate, or is it the spec dodging a load-bearing number?** If you can bound the
population from the repo (when `sourceMdHash` started being written, which paths write it, whether
migrations backfilled it), do so.

**F. Does (e) actually fix the thing it was chosen for?** Trace one cloud correction end to end and
show the corrected gists reaching the reader — or show where they do not.

## Also

- Every falsifier added to §7 for this block: is it falsifiable, and would it fail on a plausible
  wrong implementation? Round 3 shipped a row that a *correct* implementation failed, and round 4
  shipped one the *defect* passed. Assume the third attempt has the same disease.
- Citation accuracy in the changed block only.
- Whether the block contradicts §5's cost model or §8's scope list.

## Output

**Blocking / High / Medium / Low**, each with file:line, the concrete failure scenario, and a
suggested fix. Mark anything you could not run **NOT VERIFIED**. End with `CONVERGED` or
`NOT CONVERGED`.

If the honest answer is that this block is sound and the rest belongs in the plan, **say so plainly**
— this round is a targeted check on one newly-written design, not an invitation to re-open a spec that
has already had four rounds.
