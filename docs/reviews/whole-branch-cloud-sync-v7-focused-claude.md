# Whole-branch cloud-sync — round 7 FOCUSED re-review (Claude)

**Scope (deliberately narrow):** commit `15c32bd` only — `decideCompanion`
(`lib/cloud-sync/companion.ts`) and `companionTransfer` (`lib/cloud-sync/sync-run.ts`),
plus their tests. Six whole-branch rounds preceded this; nothing else was re-reviewed.

**Verification run:** `npx jest tests/lib/cloud-sync/companion.test.ts` → 31/31 pass.

---

## Verdict per change

| Change | Verdict |
|---|---|
| **L-R6-1** — both-match prefers fresher by `generatorVersion` | **INCOMPLETE** — genuinely fixes one sync direction, structurally cannot fix the other |
| **M-R6-1** — `writeModelEnvelope` wrapped, baseline still advances | **GENUINELY FIXED** |

---

## L-R6-1 — matrix, purity, and the freshness axis

### The (sender × receiver) matrix is exhaustive and correct

`senderMatch` / `receiverMatch` are each `envelope && sourceMdHash === winnerMdHash ? envelope : null`
— textually the same predicates the two pre-fix `if` heads used, just hoisted. Walking all
16 combinations of {match, envelope-but-hash-differs, `none`, `unknown`}:

| sender | receiver | branch | action | vs. pre-fix |
|---|---|---|---|---|
| match | match | 1 | tie-break on `generatorVersion` (below) | **CHANGED — the fix** |
| match | hash-differs | 2 | `ship` | same |
| match | legacy (no hash) | 2 | `ship` | same |
| match | `none` / `unknown` | 2 | `ship` | same |
| non-match / `none` / `unknown` | match | 3 | `noop`, flag `false` | same |
| non-match / `none` / `unknown` | hash-differs | 4 | `deleteReceiverModel`, flag `true` | same |
| non-match / `none` / `unknown` | legacy (no hash) | 4 | `noop`, flag `true` | same |
| non-match / `none` / `unknown` | `none` / `unknown` | 4 | `noop`, flag `true` | same |

Branch 1 is reachable only when both are `envelope` **and** both hashes equal the winner,
which is exactly the set branch 2 used to swallow. No other cell moved. In particular
`provablyStale` (companion.ts:118) still reads `receiverModel` directly rather than
`receiverMatch`, which is correct: it is reached only when `receiverMatch` is null, so the
`sourceMdHash !== undefined` test still means "present and *different*". Hoisting introduced
no behavior change for any non-matching case.

Branch 1's own three arms are exhaustive over `(receiverCurrent, senderCurrent)`:
receiver-current → noop; else sender-current → ship; else neither → noop. The legacy
sub-case (both envelopes have `generatorVersion === undefined`) falls to the third arm and
keeps the receiver — correct, since `undefined !== GENERATOR_VERSION` and a write would swap
one not-fresh envelope for another. Covered by the test at companion.test.ts:57.

### Purity: yes, still pure

`decideCompanion` performs no I/O. The new import is `GENERATOR_VERSION` from
`lib/html-doc/constants.ts` — a leaf module holding a single string literal, no renderer or
Gemini graph behind it (the commit's import-guard run confirms this). The function is now a
function of `(args, build-time constant)` rather than `args` alone; deterministic within a
process. That widening is the root of the finding below.

### `sourceSections` is NOT a mis-ranking axis here — no finding

`isFresh` (`lib/html-doc/read-model.ts:20`) is `sameTitles(envelope, titles) &&
generatorVersion === GENERATOR_VERSION`. Ignoring the titles axis is sound in branch 1:
both envelopes match `winnerMdHash`, so both were built from byte-identical MD, and
`sourceSections` is in both cases the section-title list parsed from that MD
(`lib/html-doc/generate.ts:53` — `parsed.sections.map(s => s.title)`; `serve-doc.ts:106` —
`sourceSections: titles`). Equal input to the same parser ⇒ equal titles, so the axis carries
no discriminating information in this branch. The serve-time comparison is against titles
re-derived from the *receiver's* MD, which the Class-A transfer has just made identical to the
winner's. `generatorVersion` really is the whole remaining difference. Correct as written.

---

## Finding — M-R7-1: the freshness guard uses the *local* `GENERATOR_VERSION` to judge a *cloud* receiver

**Severity:** Medium (not a regression — pre-fix behavior in this direction was identical).
**File:** `lib/cloud-sync/companion.ts:85` and `:88`.

`GENERATOR_VERSION` is a source constant compiled into each image
(`lib/html-doc/constants.ts` — currently `'magazine-skim v2'`). The share route that decides
whether a model renders or 503s (`app/s/[token]/route.ts:81` → `readFreshMagazineModel` →
`isFresh`) runs **in the receiver's serving environment** and compares against **that
environment's** constant. The sync CLI runs locally and compares against the **local
checkout's** constant. Those are the same value only when the deploy is in step with the
checkout — and version skew is the exact precondition L-R6-1's own reachability argument
depends on.

So the guard is correct for one direction and inert for the other:

**copyToLocal (cloud wins, receiver = local FS) — GENUINELY FIXED.** Local checkout `L`,
deployed image `D`, `D ≠ L`. Sender = cloud envelope at `D`; receiver = local envelope at `L`;
both match `winnerMdHash`.
- Pre-fix: ship the `D` envelope → local serve `isFresh`: `D === L`? no → not_ready →
  owner re-serve → reserve + charge.
- Post-fix: `receiverMatch.generatorVersion (L) === GENERATOR_VERSION (L)` → noop, no write.
  The fresh local model survives. **The reported harm is eliminated.**

**copyToCloud (local wins, receiver = Supabase) — UNGUARDED.** Same skew. Sender = local
envelope at `L`; receiver = cloud envelope at `D`; both match `winnerMdHash`.
- `receiverMatch.generatorVersion` is `D`; the guard tests `D === GENERATOR_VERSION (L)` → false,
  so the "receiver already fresh" arm does not fire — **even though the cloud's own `isFresh`
  would have accepted that envelope**, because on the cloud the comparison is `D === D`.
- Falls to `senderMatch.generatorVersion (L) === L` → **ship**.
- The cloud now holds an `L` envelope. `app/s/[token]/route.ts` evaluates `L === D` → false →
  `not_ready` → **503 on a share that was rendering a minute ago**, recoverable only by an
  owner re-serve that reserves and charges (`lib/html-doc/serve-doc.ts`).

That is the identical input→wrong-outcome trace L-R6-1 set out to prevent, with the two sides
swapped. Post-fix behavior here is byte-identical to pre-fix, so nothing regressed — but the
guard covers roughly half the case space, and the code comment (companion.ts:65–66) and the
commit message both state the guarantee unconditionally: *"never write when the receiver is
already current."* For a cloud receiver that claim is not true; "current" is being judged
against the wrong constant.

**Why I am not asking for a code fix.** Closing it properly requires the sync CLI to learn the
*receiver's* effective `GENERATOR_VERSION`, which it cannot observe today — the cloud does not
expose it (no version endpoint, and the constant is not carried in any synced artifact). The
honest, cheap actions are:

1. Narrow the claim in the companion.ts:65–66 comment to what holds — e.g. "prefer the fresher
   by the *local* `GENERATOR_VERSION`; when the receiver is the cloud and the deploy is skewed,
   the receiver's own freshness cannot be evaluated here and the sender may still be shipped."
2. Record the residue as a known limitation alongside L-R6-2 (they are the same family: the
   sync run cannot fully reason about a remote serving environment's freshness).

A real fix — e.g. the cloud publishing its `GENERATOR_VERSION`, or the guard degrading to
"never overwrite a receiver that matches the winner hash, regardless of version" — is a design
change and belongs in its own slice, not in a round-7 confirmation pass.

---

## M-R6-1 — best-effort ship: GENUINELY FIXED

**Swallowing is right, and the baseline should still advance.** `transferClassA` has already
committed the winner body durably by the time `companionTransfer` runs. On the next run
`reconcileClassA` returns `'skip'` (bodies now agree), and the companion step is gated on
`decision.action !== 'skip'` (sync-run.ts:639) — so a re-run would **not** retry the ship. Letting
the throw propagate therefore bought nothing except a stalled baseline: the manifest would
diverge from a state that had, in fact, been reached. Advancing is correct.

**No caller contract broken.** The CLI is `return report.errors.length ? 2 : 0`
(`scripts/cloud-sync.ts:70`). Pre-fix, a `writeModelEnvelope` throw propagated to the per-video
`catch` at sync-run.ts:651 and was pushed into `report.errors` anyway — so the exit code was
already 2 in this scenario. The change moves *which* code path populates `errors`, not whether
it is populated. Exit-code behavior is unchanged; nothing treats a non-empty `errors` as
"abort the run". The full companion suite is green (31/31).

**Behavior strictly improves alongside it:** the failure path now also returns
`shareNeedsOwnerServe: true`, so the operator sees the unready share in the report instead of
only a bare error line.

**No partial-write hazard.** `LocalBlobStore.put` (`lib/storage/local/local-blob-store.ts:15-20`)
writes to a UUID-suffixed temp file and `renameSync`s — atomic; on failure it unlinks the temp
and rethrows, leaving `models/<base>.json` untouched. The Supabase store's `put` is a single
server-side upload. Either way a failed ship leaves the receiver's blob at its prior whole
value, never a torn one. And even in a hypothetical torn case, `readModelEnvelope`
(`lib/html-doc/model-store.ts:53-68`) JSON-parses then zod-validates and returns `null` on
either failure — so a later run reads `none`/`unknown`, not a bogus valid envelope. It cannot
be misread.

---

## New defects introduced by these two edits

None found beyond M-R7-1 above, which is an incompleteness in L-R6-1's coverage rather than a
defect the edit introduced — the copyToCloud path behaves exactly as it did before `15c32bd`.

---

**CONVERGED.**

M-R6-1 is fully fixed. L-R6-1 fixes the copyToLocal direction and leaves the copyToCloud
direction exactly where round 6 found it — a residue that is not a regression, is not closable
without new plumbing between the CLI and the deployed image, and is the same family as the
already-deferred L-R6-2. Recommended before merge: tighten the companion.ts:65–66 comment so it
does not over-claim, and log M-R7-1 as a known limitation. Neither is a code change to the
logic, so this round returns no new Blocking or High.
