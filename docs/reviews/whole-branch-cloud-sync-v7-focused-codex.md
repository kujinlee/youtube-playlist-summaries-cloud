Reading prompt from stdin...
OpenAI Codex v0.142.5
--------
workdir: /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
model: gpt-5.5
provider: openai
approval: never
sandbox: danger-full-access
reasoning effort: none
reasoning summaries: none
session id: 019f7635-2af7-70d1-8ed9-297324f59395
--------
user
FOCUSED re-review (round 7) of ONE commit on `feat/stage3-cloud-sync`: `15c32bd`. This is deliberately NARROW — six full whole-branch rounds have already run and converged; do NOT re-review the whole branch.

Read `git show 15c32bd` and `docs/reviews/whole-branch-cloud-sync-v6-rereview-{codex,claude}.md`.

Scope: ONLY `lib/cloud-sync/companion.ts` (`decideCompanion`) and `companionTransfer` in `lib/cloud-sync/sync-run.ts`, plus their tests.

Two changes to verify:
1. **L-R6-1** — when BOTH sender and receiver envelopes match `winnerMdHash`, prefer the fresher by `generatorVersion`: receiver current → noop (no write); else sender current → ship; else → noop. Previously the sender always won, which could overwrite a fresh receiver model with a stale-generator one, 503 the share, and force a paid re-serve.
2. **M-R6-1** — `writeModelEnvelope` is now wrapped: on failure return `{shareNeedsOwnerServe: true, error}` instead of throwing. The caller pushes the error into `report.errors` and STILL advances the baseline (deliberate: the Class-A body already committed durably, and a re-run would not retry the ship since reconcile returns 'skip').

Questions to answer concretely:
- Is the (sender × receiver) matrix still exhaustive and correct after the restructure into `senderMatch`/`receiverMatch`? Walk every combination. Did hoisting the match computations change behavior for any non-matching case (`none`/`unknown`/legacy-no-hash/hash-mismatch)?
- Does `decideCompanion` remain PURE and free of I/O?
- Is `GENERATOR_VERSION` the right freshness axis on its own here, given `isFresh` also compares `sourceSections`? Both envelopes match `winnerMdHash` (same body) — can their `sourceSections` legitimately differ, and if so does ignoring that axis mis-rank them?
- Is swallowing the ship failure right, or does it hide a fault that should abort? Confirm the baseline SHOULD still advance, and that `report.errors` now containing a companion error does not break any caller's contract (e.g. a test or the CLI treating a non-empty `errors` as total failure).
- Does the ship-failure path leave the receiver blob in a partially-written state that a later run misreads?
- Any NEW defect introduced by these two edits.

Do NOT re-report known/deferred items: L-R6-2 (`noop+false` under-reports a version-skewed receiver), L-R5-3 (`readManifest` degrade-on-corrupt, spec §8), Claude-R2-M1, Codex-R2-Medium, Claude-R3-M1, T14-M1/M2, T5, T4. Do NOT report `tests/integration/reservation-release.test.ts` (pre-existing on a clean tree).

Calibration: this is a narrow confirmation pass on two contained clauses. Finding nothing is the expected outcome and is a valid, useful answer — say so plainly. Do not manufacture a finding. Equally, if one of these two edits is genuinely wrong, say so clearly with a file:line and an input→wrong-outcome trace.

Output: verdict per change (GENUINELY FIXED / INCOMPLETE / NOT FIXED with evidence), any new findings with severity + file:line + scenario + fix, and end with **CONVERGED** or **NOT CONVERGED**.

codex
I’ll do this as a narrow code-review pass only. I’ll read the target commit and the two prior review notes first, then inspect just the companion decision path, transfer path, and related tests.
exec
/bin/bash -lc "sed -n '1,240p' docs/reviews/whole-branch-cloud-sync-v6-rereview-codex.md" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
Reading prompt from stdin...
OpenAI Codex v0.142.5
--------
workdir: /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
model: gpt-5.5
provider: openai
approval: never
sandbox: danger-full-access
reasoning effort: none
reasoning summaries: none
session id: 019f7626-e7b7-70a1-9915-5531b29c5032
--------
user
You are an adversarial WHOLE-BRANCH RE-REVIEWER (ROUND 6) for Stage 3 Cloud Sync (M2a), branch `feat/stage3-cloud-sync`. HEAD is `12c850d`.

Trail: R1 `32a164c` (1 Blocking + 2 High) → R2 `1f54c60` (2 High, one a regression from R1's fix) → R3 `3bc8cc7` (1 Blocking) → R4 `66fe6e5` (3 High, one a regression from R3's fix) → R5 `12c850d` (1 High — found by BOTH reviewers independently — plus dead-code removal and a Low). Reviews: `docs/reviews/whole-branch-cloud-sync{,-v2,-v3,-v4,-v5}-rereview-{codex,claude}.md`.

Read `git show 12c850d` first.

**Calibration — read this carefully.** Five rounds have landed real fixes. The severity trend is now decreasing and R5's single High was found independently by both reviewers, which suggests the surface is nearly exhausted. Two failure modes are equally bad here:
- Declaring CONVERGED while a real defect is live. R3 and R4 both had a reviewer do exactly that.
- Manufacturing a marginal finding to look diligent. That costs a real fix cycle, and in this branch every fix round has had roughly a one-in-two chance of introducing a new defect.
If you find nothing, say so plainly and stop. A clean round is the expected terminal state of this loop.

## Part A — verify the round-5 fixes
R5 restructured `decideCompanion` (`lib/cloud-sync/companion.ts`) to take BOTH sides as `ModelRead` tri-states:
1. sender envelope matching `winnerMdHash` → ship
2. else receiver envelope matching `winnerMdHash` → noop, `shareNeedsOwnerServe: false`
3. else delete ONLY when the receiver envelope has a `sourceMdHash` that is present (provably stale); everything else (absent / legacy no-hash / unprovable read) → noop with `shareNeedsOwnerServe: true`

VERIFY:
- Is the matrix exhaustive and correct for every (sender × receiver) combination? Walk all 9. Is there a combination where it ships or deletes something it should not, or keeps something that is provably wrong?
- `provablyStale` is `receiverModel.kind === 'envelope' && receiverModel.envelope.sourceMdHash !== undefined` — note this deletes whenever the receiver has ANY sourceMdHash, having already excluded the matching case at step 2. Confirm that is right, and that a receiver envelope whose `sourceMdHash` matches but whose `sourceSections`/`generatorVersion` are stale is handled sanely by the serve path.
- Does `readReceiverModel` (or however sync-run reads the receiver side) correctly map the receiver's null through `provesAbsence`? A receiver read that is unprovable must NOT delete.
- `shareNeedsOwnerServe` is now carried on `noop`. Confirm it preserves the pre-existing row-7 contract (`tests/integration/cloud-sync/e2e.int.test.ts:236`) and does not now OVER-report — trace how often `noop + true` fires in ordinary syncs (e.g. every video where neither side has a model) and say whether the counter remains meaningful to a user.
- H3 layer 3 was REMOVED and `ensureReceiverSlot` restored to `setPlaylistMeta`-then-`readIndex`. Confirm that ordering is correct on BOTH backends (on local, does `setPlaylistMeta` create the index file that `readIndex` then reads? is the row-exists check still authoritative?).
- L-R5-2: `playlistMetaFor` now prefers the CLOUD title. Confirm no case where that loses a legitimately newer local title.

## Part B — new defects
Re-verify on the shipped state, and hunt for anything the R5 restructure introduced or exposed:
- Baseline-advance correctness on every branch; no advance without a durable write; every "seen" video gets one.
- Money-safety: no enqueue, no `spend_ledger`, no regenerable-cache resurrection; `needsRegen` report-only; and any path that forces the USER to re-spend counts as a money finding (that is what H1 and H-R5-1 both were).
- Atomicity: durable-before-advertise, manifest-after-commit.
- Idempotency reasoned across TWO runs on every branch.
- Cross-backend local-vs-Supabase semantic mismatches.
- RLS / no-service-role unchanged.
- Any remaining "a value meaning absent is also what a failure produces" instance NOT already deferred. Note `readManifest` (`lib/cloud-sync/manifest.ts`) is DEFERRED by decision — spec §8 specifies degrade-on-corrupt and the direction is safe. Do not re-file it.

## Known / deferred — do NOT re-report unless you prove one masks a real bug
T14-M1, T14-M2, T5 coverage gaps, T4 automock comment; Claude-R2-M1 (stale non-`summaryMd` artifact pointers); Codex-R2-Medium (absent companion scalars); Claude-R3-M1 (`build-doc-html` base from `digDeeperMd`); L-R5-3 (`readManifest` degrade-on-corrupt). Do NOT report `tests/integration/reservation-release.test.ts` — pre-existing on a clean tree.

Minor known nit, already logged, no need to re-file: a comment in `companion.ts`/`sync-run.ts` cites "§10 row 7" as if it were in the design spec; the numbered row 7 actually lives in the PLAN (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:2213`) and its wording is about a deleted model, while the implemented+tested contract is "no matching model".

## Scope
SHIPPED state at HEAD. `lib/cloud-sync/*.ts`, `lib/storage/**`, `supabase/migrations/0021_*` + `0009_*`, `lib/html-doc/*`, `lib/dig/*`, tests under `tests/lib/cloud-sync/` and `tests/integration/cloud-sync/`. Spec: `docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md`. Plan: `docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md`.

## Output
Per finding: severity, `file:line`, concrete input→wrong-outcome scenario, fix. Part A: GENUINELY FIXED / INCOMPLETE / NOT FIXED per item with evidence. End with **CONVERGED** or **NOT CONVERGED**.

codex
I’ll start by reading the shipped diff at `12c850d`, then trace the companion decision paths and sync-run call sites before looking for fresh branch-level defects.
exec
/bin/bash -lc 'git show --stat --oneline --decorate --no-renames 12c850d && git show --no-ext-diff --unified=80 --no-renames 12c850d -- lib/cloud-sync/companion.ts lib/cloud-sync/sync-run.ts tests/lib/cloud-sync/companion.test.ts tests/integration/cloud-sync/e2e.int.test.ts' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
12c850d (HEAD -> feat/stage3-cloud-sync) fix(cloud-sync): round-5 whole-branch re-review — key the companion decision to the RECEIVER, drop dead layer, cloud title precedence (H-R5-1/L-R5-2)
 .../whole-branch-cloud-sync-v5-rereview-claude.md  |   241 +
 .../whole-branch-cloud-sync-v5-rereview-codex.md   | 14637 +++++++++++++++++++
 lib/cloud-sync/companion.ts                        |    92 +-
 lib/cloud-sync/manifest.ts                         |    11 +-
 lib/cloud-sync/sync-run.ts                         |    77 +-
 tests/integration/cloud-sync/e2e.int.test.ts       |   172 +-
 tests/integration/helpers/cloud.ts                 |     4 +
 tests/lib/cloud-sync/companion.test.ts             |   101 +-
 8 files changed, 15248 insertions(+), 87 deletions(-)
commit 12c850d34dd8488184ba16233676250bc412d50c
Author: Kujin Lee <kujinlee@gmail.com>
Date:   Sat Jul 18 09:53:04 2026 -0700

    fix(cloud-sync): round-5 whole-branch re-review — key the companion decision to the RECEIVER, drop dead layer, cloud title precedence (H-R5-1/L-R5-2)
    
    Round-5 dual re-review of 66fe6e5. BOTH reviewers independently found the same High — the
    first time they have agreed, after R3/R4 where one cleared a path the other found broken.
    
    H-R5-1 (High) — round 4 made the SENDER model read honest (provesAbsence tri-state) but left
    the whole decision keyed to it, which was wrong in both directions:
      (a) `unknown` → noop KEPT a provably-stale receiver model, and the claimed safety net does
          not exist: isFresh (lib/html-doc/read-model.ts) compares section TITLES and
          generatorVersion, never sourceMdHash, so a prose-only MD change — exactly the
          recency-tiebreak case — is served as fresh indefinitely. `unknown` is also the COMMON
          outcome, since a cloud video never HTML-served has no model blob and Supabase cannot
          prove that 404.
      (b) `none` → delete DESTROYED receiver models that were still valid, because the receiver
          was never consulted.
    The backend ambiguity was only ever about the SENDER. The receiver's staleness is provable
    independently: we hold winnerMdHash, so a receiver sourceMdHash that is present and DIFFERENT
    is definitively stale, no ambiguity involved. decideCompanion now takes both sides as
    tri-states: ship a matching sender envelope; keep a receiver model that matches the winner;
    delete only on PROOF of staleness; keep legacy (no sourceMdHash) and unprovable reads. Money
    rule: a possibly-stale cache is recoverable, a deleted paid artifact is not.
    
    shareNeedsOwnerServe is now carried on `noop` too — it is a separate axis from the blob
    action, and conflating the two is what produced this finding. The report flag preserves the
    pre-existing row-7 contract (e2e.int.test.ts:236, "no matching model flags
    shareNeedsOwnerServe"); under-reporting is the harmful direction since the flag spends nothing.
    
    H3 layer 3 REMOVED as dead code, not as cleanup: both reviewers independently failed to
    construct an input reaching it, and my mutation test (deleting it) failed ZERO tests. Layers 1
    and 2 are what actually fix H3 and they are covered. A comment records why, so it is not
    re-added — dead defense-in-depth reads as load-bearing and hides which layer holds.
    
    L-R5-2 (Low) — playlistMetaFor now prefers the CLOUD title. Titles have no LWW timestamp, so
    this is fixed precedence: the cloud row is maintained by ingest and backfill-titles (both from
    the live YouTube API), whereas a local index title is whatever was captured when that folder
    was last summarized. Preferring local let a stale title overwrite a fresher one.
    
    L-R5-3 (readManifest swallows unreadable as absent → can resurrect a deleted video) is
    DEFERRED with a comment naming spec §8: degrade-on-corrupt is specified and the direction is
    the safe one. Recorded so the next reviewer does not re-file it.
    
    Verification: tsc clean; 2445 unit / 245 suites; cloud-sync integration 44/44 (4 suites).
    
    Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
    Claude-Session: https://claude.ai/code/session_01EfbFViKSSM27WJ5dSchemY

diff --git a/lib/cloud-sync/companion.ts b/lib/cloud-sync/companion.ts
index 17d7022..87d5fb1 100644
--- a/lib/cloud-sync/companion.ts
+++ b/lib/cloud-sync/companion.ts
@@ -1,39 +1,93 @@
 import type { ModelEnvelope } from '@/lib/html-doc/model-store';
 
-/** H1 (round 4) — the result of reading the SENDER's model, as a TRI-state.
+/** H1 (round 4) — the result of reading ONE side's model, as a TRI-state.
  *  `readModelEnvelope` collapses three different situations into one null: the envelope is absent,
- *  it is corrupt/schema-invalid, or its bytes could not be READ. The first two mean the sender has
- *  nothing shippable (the receiver's model is now stale and should go); the third means we simply
- *  do not know, and acting on it destroys a paid artifact. Which of those a null is depends on the
- *  backend — see BlobStore.provesAbsence — so the caller resolves it and hands the answer here. */
-export type SenderModelRead =
+ *  it is corrupt/schema-invalid, or its bytes could not be READ. The first two mean that side has
+ *  nothing usable; the third means we simply do not know, and acting on it destroys a paid artifact.
+ *  Which of those a null is depends on the backend — see BlobStore.provesAbsence — so the caller
+ *  resolves it and hands the answer here.
+ *
+ *  H-R5-1 (round 5) — this is now read for BOTH sides, hence the neutral name. */
+export type ModelRead =
   | { kind: 'envelope'; envelope: ModelEnvelope }
-  | { kind: 'none' }      // the sender PROVABLY has no usable model
+  | { kind: 'none' }      // that side PROVABLY has no usable model
   | { kind: 'unknown' };  // the read failed in a way that cannot prove absence
 
+/** @deprecated round-4 name, kept so the tri-state reads naturally at the sender call site. */
+export type SenderModelRead = ModelRead;
+
+/** H-R5-1 (round 5) — `shareNeedsOwnerServe` is now carried on `noop` too, because it is a SEPARATE
+ *  axis from the blob action and conflating the two is what produced this finding. The action answers
+ *  "what do we do to the receiver's blob?"; the flag is a report-only count of shares that cannot
+ *  render until the owner re-serves. §10 row 7 (neither side holds a model) is exactly the case where
+ *  there is nothing to delete and yet the share IS unready — noop + true. */
 export type CompanionAction =
   | { kind: 'ship'; envelope: ModelEnvelope }
   | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true }
-  | { kind: 'noop' };
+  | { kind: 'noop'; shareNeedsOwnerServe: boolean };
 
-/** Ship the sender's model iff it was generated from the winning MD (§4.2).
+/** Ship the sender's model iff it was generated from the winning MD (§4.2); otherwise decide the
+ *  receiver's fate from the RECEIVER's own envelope.
  *
- *  H1 (round 4) — `unknown` is a NO-OP, not a delete. Deleting the receiver's model costs a paid
- *  Gemini magazine transform to recover (runHtmlDoc → generateMagazineModel locally, or
+ *  H1 (round 4) — `unknown` must not delete. Deleting the receiver's model costs a paid Gemini
+ *  magazine transform to recover (runHtmlDoc → generateMagazineModel locally, or
  *  resolveMagazineModel → reserve_serve_model → spend_ledger on the cloud), and the delete is
  *  silent and sticky: it does not throw, so the caller advances the manifest baseline, and the next
- *  run's Class-A reconcile returns 'skip' and never revisits the companion step. Keeping a possibly
- *  stale receiver model is the cheap side of that trade — a model is only ever a cache, and the
- *  serve path's sourceSections drift guard (lib/html-doc/read-model.ts) rejects a mismatched one
- *  for free. */
+ *  run's Class-A reconcile returns 'skip' and never revisits the companion step.
+ *
+ *  H-R5-1 (round 5) — round 4 made the SENDER read honest but left the whole decision keyed to it,
+ *  which was wrong in both directions:
+ *   (a) `unknown` → noop KEPT a provably-stale receiver model. The claimed safety net does not
+ *       exist: the serve path's drift guard (lib/html-doc/read-model.ts) compares section TITLES and
+ *       generatorVersion, never sourceMdHash, so a prose-only MD change — precisely the
+ *       recency-tiebreak case — is served as fresh forever (dig-deeper merges the cached envelope
+ *       without regenerating). And `unknown` is the COMMON outcome: a cloud video that was never
+ *       HTML-served has no model blob, and the Supabase backend cannot prove that 404.
+ *   (b) `none` → delete DESTROYED receiver models that were still valid, since the receiver was
+ *       never consulted.
+ *  The backend ambiguity was only ever about the SENDER. The receiver's staleness is provable
+ *  independently: we hold winnerMdHash, so a receiver sourceMdHash that is present and DIFFERENT is
+ *  definitively stale — its backing body no longer exists — with no ambiguity involved. So the
+ *  sender read now decides only whether a REPLACEMENT can be shipped, and everything else is keyed
+ *  to the receiver. Deleting a provably-stale model is not a money loss; deleting a matching one is.
+ */
 export function decideCompanion(args: {
   winnerMdHash: string;
-  senderModel: SenderModelRead;
+  senderModel: ModelRead;
+  receiverModel: ModelRead;
 }): CompanionAction {
-  const { winnerMdHash, senderModel } = args;
-  if (senderModel.kind === 'unknown') return { kind: 'noop' };
+  const { winnerMdHash, senderModel, receiverModel } = args;
+
+  // 1. The sender holds a model built from the winning MD → ship it (it supersedes whatever the
+  //    receiver has, so the receiver's own state does not matter here).
   if (senderModel.kind === 'envelope' && senderModel.envelope.sourceMdHash === winnerMdHash) {
     return { kind: 'ship', envelope: senderModel.envelope };
   }
-  return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
+
+  // 2. Nothing shippable, but the receiver already holds a model built from the WINNING MD — it is
+  //    still valid. Do not destroy a paid artifact, and the share renders, so report nothing.
+  if (receiverModel.kind === 'envelope' && receiverModel.envelope.sourceMdHash === winnerMdHash) {
+    return { kind: 'noop', shareNeedsOwnerServe: false };
+  }
+
+  // 3. The receiver's model is not known-good. The two axes now diverge, and DELIBERATELY:
+  //
+  //  - DELETE the blob only on PROOF. A receiver envelope whose sourceMdHash is present and differs
+  //    is definitively stale — its backing body no longer exists — and needs no sender read to
+  //    establish. Everything else is unprovable: `none`/`unknown` say nothing about a model we never
+  //    read, and a legacy pre-1F-a envelope predates sourceMdHash entirely (the field is .optional()
+  //    in model-store.ts), so it cannot be checked. Fail-safe-for-money: KEEP those. A possibly-stale
+  //    cache is recoverable — any regeneration overwrites it, and the existing sourceSections /
+  //    generatorVersion drift guard still catches the common legacy drift — but a deleted paid
+  //    artifact costs a Gemini transform to rebuild.
+  //
+  //  - REPORT on doubt. shareNeedsOwnerServe is a report-only count (§10 row 7): "these shares may
+  //    not render until you re-serve." It spends nothing and destroys nothing, so the harmful
+  //    direction is UNDER-reporting — an anon visitor silently hitting a not-ready share. Note the
+  //    receiver of a copyToCloud is always the Supabase store, which can never return `none`, so
+  //    keying the flag to proof would make §10 row 7 unreportable in the direction it describes.
+  const provablyStale = receiverModel.kind === 'envelope'
+    && receiverModel.envelope.sourceMdHash !== undefined;
+  if (provablyStale) return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
+  return { kind: 'noop', shareNeedsOwnerServe: true };

exec
/bin/bash -lc "sed -n '1,240p' docs/reviews/whole-branch-cloud-sync-v6-rereview-claude.md" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
# Whole-branch re-review (round 6, Claude) — Stage 3 Cloud Sync (M2a)

Branch `feat/stage3-cloud-sync`, HEAD `12c850d`. Read-only review of the shipped state.

Gates run: `npx jest tests/lib/cloud-sync` → **15 suites / 109 tests pass**. `npx tsc --noEmit` → **clean**.

---

## Part A — verification of the round-5 fixes

### A1. The nine (sender × receiver) combinations — **GENUINELY FIXED**

`decideCompanion` (`lib/cloud-sync/companion.ts:54-93`) is exhaustive: step 1 keys on the sender,
steps 2/3 key on the receiver, and step 3's fallthrough (`return { kind: 'noop',
shareNeedsOwnerServe: true }`, :92) is total, so there is no unhandled combination.

Walking sender ∈ {env-match, env-nomatch, none, unknown} × receiver ∈ {env-match, env-stale-hash,
env-legacy-nohash, none, unknown}:

| sender | receiver | result | correct? |
|---|---|---|---|
| env-match | any | ship | yes — except one narrow case, L-R6-1 below |
| env-nomatch / none / unknown | env-match | noop, flag false | yes — paid artifact matching the winner body is kept |
| env-nomatch / none / unknown | env-stale-hash | delete, flag true | yes — provable staleness, no ambiguity |
| env-nomatch / none / unknown | env-legacy-nohash | noop, flag true | yes — unprovable, fail-safe-for-money |
| env-nomatch / none / unknown | none | noop, flag true | yes — nothing to delete, share still unready |
| env-nomatch / none / unknown | unknown | noop, flag true | yes — the R4 destructive case, now closed |

Nothing is deleted without proof, and nothing provably wrong is kept: the only "kept while wrong"
cells are legacy-no-hash and unprovable reads, where wrongness is by definition not established.
`tests/lib/cloud-sync/companion.test.ts:33-64` parametrizes all three non-shipping sender states
across all five receiver states, so the matrix is covered by tests, not just by reading.

### A2. `provablyStale` semantics — **GENUINELY FIXED**

`receiverModel.kind === 'envelope' && receiverModel.envelope.sourceMdHash !== undefined`
(:89-90) is reached only after step 2 has excluded the matching case, so "present" here already
means "present and different". `sourceMdHash` is `.optional()` in `ModelEnvelopeSchema`
(`lib/html-doc/model-store.ts:22`), so `undefined` is exactly the legacy pre-1F-a envelope, which is
correctly excluded from the delete. The reasoning is right.

**Matching-hash-but-stale-`sourceSections`/`generatorVersion` is handled sanely by the serve path.**
A matching `sourceMdHash` means the model was generated from byte-identical MD, so
`sourceSections` cannot diverge; only `generatorVersion` can (replica version skew). In that case
`isFresh` (`lib/html-doc/read-model.ts:20-25`) returns false, and both consumers degrade correctly:
the owner path (`resolveMagazineModel`, `lib/html-doc/serve-doc.ts:56-57`) falls through to
reserve → regenerate → `writeModelEnvelope` (`put`, overwrite) so the cache self-heals; the anon
share path (`app/s/[token]/route.ts:81-82`) 503s "not ready" without generating. No stale render, no
stuck cache. See L-R6-2 for the reporting nit this creates.

### A3. Receiver null mapped through `provesAbsence` — **GENUINELY FIXED**

`companionTransfer` reads both sides through the same resolver
(`lib/cloud-sync/sync-run.ts:388-390` → `readModelSide`, :415-419), and `readModelSide` keys on
`side.blob.provesAbsence` — so the receiver's null is resolved against the *receiver's* backend, not
the sender's. `SupabaseBlobStore.provesAbsence = false` / `LocalBlobStore.provesAbsence = true`
(`lib/storage/supabase/supabase-blob-store.ts:10`, `lib/storage/local/local-blob-store.ts:10`), and
`?? unknown` is the default for a store that omits the optional flag (`lib/storage/blob-store.ts:18`).
An unprovable receiver read yields `unknown` → `provablyStale` false → noop. **No delete.** Correct.

### A4. `shareNeedsOwnerServe` on `noop` — **GENUINELY FIXED, and not over-reporting**

The row-7 contract at `tests/integration/cloud-sync/e2e.int.test.ts:236-247` is preserved: local is
the format-2 winner with no model envelope; the cloud receiver has none either and cannot prove it,
so the decision is `noop + true` and `report.shareNeedsOwnerServe >= 1` still holds. (The test's
inline comment says "→ deleteReceiverModel", which is now wrong — see L-R6-3.)

On over-reporting, the bound is tighter than it first looks. `companionTransfer` is called only when
`decision.action !== 'skip'` (`sync-run.ts:624`) — i.e. only for **two-sided videos that actually
had a Class-A MD transfer**. Additive one-sided creates route through `copyAdditiveVideo` and never
reach it, so a first-device hydrate of N videos contributes **zero** to the counter. Within the
transferred set, `noop + true` fires whenever the receiver holds no model matching the new winning
body — which is precisely the set of shares that genuinely cannot render until the owner re-serves.
The counter stays meaningful.

### A5. `ensureReceiverSlot` ordering after the layer-3 removal — **GENUINELY FIXED on both backends**

`setPlaylistMeta` → `readIndex` → row-exists check → `claimVideoSlot` (`sync-run.ts:168-174`).

- **Local:** `setPlaylistMeta` does `readIndex` then `writeIndex`
  (`lib/storage/local/local-metadata-store.ts:13-21`), which materializes `playlist-index.json`
  before the subsequent `readIndex` — so on a fresh-device hydrate the file exists by the time it is
  read. Combined with `ensureHydrationRoot`'s `mkdir -p` (`sync-run.ts:88-90, 492`), the missing-dir
  throw is also covered.
- **Cloud:** `setPlaylistMeta` upserts the `playlists` row
  (`lib/storage/supabase/supabase-metadata-store.ts:73-82`); `readIndex` then finds it (:29-36,
  returning the empty-index sentinel only when the row is genuinely absent), and `claimVideoSlot`'s
  `requirePlaylistId` resolves (:92). Ordering the meta write first is load-bearing on this backend,
  not merely convenient.

The `idx.videos.some(...)` row-exists check remains authoritative: the read happens after the only
write that precedes it in this run, that write touches the playlists row only (never the video set),
and sync is single-run. The removed layer 3 was genuinely unreachable — I could not construct an
input where `playlistMetaFor` yields no title while the receiver row has one, for the reasons the
comment enumerates (`sync-run.ts:158-167).

### A6. `playlistMetaFor` cloud-title precedence (L-R5-2) — **FIXED, with a bounded and acceptable trade**

`cp?.playlistTitle ?? lp?.playlistTitle` (`sync-run.ts:115`). There *is* a case where a newer local
title loses: the user renames the playlist on YouTube and re-ingests **locally** but not in the
cloud — the local title is fresher and the cloud's stale one now wins. The effect is bounded: the
value is consumed only by `ensureReceiverSlot`'s `setPlaylistMeta` on an additive create, so the
worst outcome is that the cloud keeps a title it already had (a missed refresh, not a clobber), and
the fallback still lets a replica that holds the only title supply it. Since titles carry no LWW
timestamp, either precedence loses in one direction; the chosen one loses the *cosmetic* direction
rather than the destructive one. No change recommended.

---

## Part B — new findings

### L-R6-1 (Low) — `ship` can downgrade a receiver model that was already fresh

`lib/cloud-sync/companion.ts:63-65`. Step 1 fires before step 2, so when **both** sides hold an
envelope with `sourceMdHash === winnerMdHash` and only the **sender's** `generatorVersion` is older,
the ship overwrites a receiver model that `isFresh` accepted with one it will reject
(`lib/html-doc/read-model.ts:24`). The receiver's share flips from rendering to 503, and recovery is
an owner re-serve, which reserves and charges (`serve-doc.ts:60-113`) — the same class of
user-re-spend as H1 / H-R5-1, which is why I am filing it rather than dropping it.

Rated **Low, not High**, because reaching it needs two independent unlikely conditions at once:
(a) `GENERATOR_VERSION` skew between the local checkout and the deployed cloud image, *and* (b) the
transfer **loser** already holding a model built from the **winner's exact body** — which means the
content ping-ponged between the replicas. A guard would be one clause (prefer the receiver when its
envelope matches the winner hash and its `generatorVersion` is not older), but per the calibration
this does not justify a fix round on its own; it is a fine candidate to fold into any future edit of
this function.

### M-R6-1 (Medium) — a failed `ship` write is sticky: no re-run ever retries it

`lib/cloud-sync/sync-run.ts:392-394`. `writeModelEnvelope` is **not** wrapped (unlike the delete on
:401, which is `try`/`catch`), so a transient blob `put` failure throws out of `companionTransfer`,
past `writeVideoBaseline`, into the per-video catch on :633. The error does surface in
`report.errors`, so this is not silent — but it is **unrecoverable by re-running**: `transferClassA`
already committed the winner body to the loser (:335, :373), so the next run's `reconcileClassA`
returns `skip`, and `companionTransfer` is gated on `decision.action !== 'skip'` (:624). The ship is
never attempted again. The receiver keeps the model it had; if that model has matching section
titles and a matching generator version but was built from the pre-sync body — the prose-only-change
case that motivated H-R5-1 — it will be served as fresh indefinitely.

Not a money loss and not R5-introduced (the companion step has been outside the atomic commit since
T7), which is why it is Medium. Cheapest containment is to treat a companion-step failure the way
the delete is treated — swallow it and set `shareNeedsOwnerServe: true` — so the run reports the
share as unready instead of leaving a stale model advertised as fresh. Recommend deferring with an
owner rather than opening a fix round.

### L-R6-2 (Low) — `noop + false` under-reports a matching-hash / version-skewed receiver model

`lib/cloud-sync/companion.ts:69-71` reports `shareNeedsOwnerServe: false` for any receiver envelope
matching `winnerMdHash`, including one whose `generatorVersion` is stale — which the share route
will 503 on (`app/s/[token]/route.ts:81-82`). This is an under-report in the direction the code
comment identifies as the harmful one (:85-86). It is Low because the condition **predates the
sync** (that model was already not-fresh before the run) and `shareNeedsOwnerServe` is scoped to
shares this sync left unready, not to a general share-health audit.

### L-R6-3 (Low, comment rot) — stale inline comment on the row-7 test

`tests/integration/cloud-sync/e2e.int.test.ts:245` reads
`// winner (local) has no model envelope → deleteReceiverModel`. Under R5 that input takes the
`noop + shareNeedsOwnerServe: true` path (receiver has no model and the Supabase store cannot prove
it). The assertion is still correct; only the comment misdescribes the mechanism, and it names the
one branch a future reader would most likely trust when reasoning about deletes.

---

## Money / atomicity / idempotency sweep (no findings)

- **No charging surface reachable from sync.** `grep` over `lib/cloud-sync/*.ts` imports finds no
  `gemini`, `job-queue`, `enqueue`, or `spend` module, and no `createServiceClient` / service-role
  key anywhere in the directory. The cloud principal is `deps.ownerId` = `auth.uid()`
  (`sync-run.ts:495`), so every write stays inside RLS.
- **Regenerable cache is never resurrected.** `sanitizeAdditiveVideo` (:123-140) nulls
  `summaryHtml`/`digDeeperHtml`/`digDeeperMd` and keeps only `artifacts.summaryMd`;
  `transferClassA` clears only the two HTML caches and deliberately preserves the paid
  `digDeeperMd` (:358-367). Consistent, and the asymmetry is correctly justified.
- **`needsRegen` stays report-only** — `report.needsRegen += 1` at :603 and :595, with no
  corresponding write anywhere.
- **Baseline advance.** Every path that advances writes only after a durable, *verified* receiver
  write: additive after the row-exists + promoted-artifact re-read (:231-244) then :520; two-sided
  after `transferClassA` returns (:632); corrections-unresolved writes a non-advancing Class-A
  baseline (:463-471); `skip` advances legitimately (N4). Every throw path skips the baseline, and
  every "seen" two-sided video gets one.
- **Idempotency across two runs.** A second run over a converged state derives equal `mdHash` on
  both sides → `skip` → no transfer, no companion step, no blob write; the baseline rewrite is
  value-identical. No new "absent means failure" instance beyond the deferred `readManifest`.

---

## Verdict

Part A: all six round-5 items **GENUINELY FIXED**. Part B: one Medium (M-R6-1, pre-existing,
recommend deferring with an owner) and three Lows. **No new Blocking or High.** This is the clean
round the loop was converging toward — the remaining items are the residue that always survives, not
a signal that another fix cycle is owed.

**CONVERGED**

exec
/bin/bash -lc 'git show --stat --oneline --decorate --no-renames 15c32bd && git show --no-ext-diff --unified=80 --no-renames 15c32bd -- lib/cloud-sync/companion.ts lib/cloud-sync/sync-run.ts tests 2>/dev/null' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
15c32bd (HEAD -> feat/stage3-cloud-sync) fix(cloud-sync): round-6 whole-branch re-review — never downgrade a fresh receiver model; companion writes are best-effort (L-R6-1/M-R6-1)
 .../whole-branch-cloud-sync-v6-rereview-claude.md  |  196 +
 .../whole-branch-cloud-sync-v6-rereview-codex.md   | 7337 ++++++++++++++++++++
 lib/cloud-sync/companion.ts                        |   47 +-
 lib/cloud-sync/sync-run.ts                         |   26 +-
 tests/integration/cloud-sync/e2e.int.test.ts       |   85 +-
 tests/integration/helpers/cloud.ts                 |   31 +-
 tests/lib/cloud-sync/companion.test.ts             |   55 +-
 7 files changed, 7750 insertions(+), 27 deletions(-)
commit 15c32bd0fe0a3967fa2a224f15f57d1dc1ef0a79
Author: Kujin Lee <kujinlee@gmail.com>
Date:   Sat Jul 18 10:08:53 2026 -0700

    fix(cloud-sync): round-6 whole-branch re-review — never downgrade a fresh receiver model; companion writes are best-effort (L-R6-1/M-R6-1)
    
    Round-6 dual re-review of 12c850d. Claude returned CONVERGED; Codex returned NOT CONVERGED.
    They filed the SAME defect at different severities (Codex High, Claude Low). Adjudicated
    toward fixing: the consequence is a broken share plus a paid re-serve, and the guard is one
    clause. No NEW Blocking from either reviewer, and Claude's Part A cleared all six round-5
    items — including the full nine-combination matrix — as genuinely fixed.
    
    L-R6-1 — decideCompanion's ship branch could DOWNGRADE. When both envelopes match
    winnerMdHash the bodies are identical, so generatorVersion is the whole difference, and
    shipping the sender's blindly overwrote a receiver model isFresh() accepts with one it
    rejects: the share flips from rendering to a 503 (app/s/[token]/route.ts) and the only
    recovery is an owner re-serve, which reserves and charges — the same user-re-spend class as
    H1 and H-R5-1. Reachability is not exotic, which is why this is fixed rather than tolerated:
    it needs GENERATOR_VERSION skew between the local checkout and the deployed image (routine
    when the deploy lags) AND the loser already holding a model built from the winner's exact
    body — the normal state after any prior sync, since reconcile-class-a falls through to a
    transfer on equal mdHash when currency or format disagree. Both-match now prefers the fresher
    by generatorVersion and never writes when the receiver is already current.
    
    M-R6-1 — a failed companion ship was STICKY, not merely noisy. writeModelEnvelope was
    unwrapped, so a transient put failure threw past writeVideoBaseline; but the Class-A body had
    already committed, so the next run's reconcileClassA returns 'skip' and the companion step
    (gated on !== 'skip') never runs again. The receiver kept a model built from the PRE-SYNC
    body, and if its titles and generatorVersion still matched, the serve path's drift guard could
    not see it — served as fresh forever, the prose-only-change case behind H-R5-1. Companion
    writes are now best-effort like the delete already was: swallow, report the share unready, and
    surface the error in report.errors without aborting the per-video flow. The baseline still
    advances, deliberately — the Class-A commit is durable and a re-run would not retry the ship.
    
    Also corrects comment rot on the row-7 test (L-R6-3). Out of scope by decision: L-R6-2
    (noop+false under-reports a version-skewed receiver — the condition predates the sync) and
    L-R5-3 (readManifest degrade-on-corrupt, spec §8).
    
    Verification: tsc clean; 2450 unit / 245 suites; cloud-sync integration 46/46 (4 suites);
    import-guard 17/17 (GENERATOR_VERSION import does not reach gemini or the charging code).
    
    Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
    Claude-Session: https://claude.ai/code/session_01EfbFViKSSM27WJ5dSchemY

diff --git a/lib/cloud-sync/companion.ts b/lib/cloud-sync/companion.ts
index 87d5fb1..f690a2e 100644
--- a/lib/cloud-sync/companion.ts
+++ b/lib/cloud-sync/companion.ts
@@ -1,93 +1,122 @@
+import { GENERATOR_VERSION } from '@/lib/html-doc/constants';
 import type { ModelEnvelope } from '@/lib/html-doc/model-store';
 
 /** H1 (round 4) — the result of reading ONE side's model, as a TRI-state.
  *  `readModelEnvelope` collapses three different situations into one null: the envelope is absent,
  *  it is corrupt/schema-invalid, or its bytes could not be READ. The first two mean that side has
  *  nothing usable; the third means we simply do not know, and acting on it destroys a paid artifact.
  *  Which of those a null is depends on the backend — see BlobStore.provesAbsence — so the caller
  *  resolves it and hands the answer here.
  *
  *  H-R5-1 (round 5) — this is now read for BOTH sides, hence the neutral name. */
 export type ModelRead =
   | { kind: 'envelope'; envelope: ModelEnvelope }
   | { kind: 'none' }      // that side PROVABLY has no usable model
   | { kind: 'unknown' };  // the read failed in a way that cannot prove absence
 
 /** @deprecated round-4 name, kept so the tri-state reads naturally at the sender call site. */
 export type SenderModelRead = ModelRead;
 
 /** H-R5-1 (round 5) — `shareNeedsOwnerServe` is now carried on `noop` too, because it is a SEPARATE
  *  axis from the blob action and conflating the two is what produced this finding. The action answers
  *  "what do we do to the receiver's blob?"; the flag is a report-only count of shares that cannot
  *  render until the owner re-serves. §10 row 7 (neither side holds a model) is exactly the case where
  *  there is nothing to delete and yet the share IS unready — noop + true. */
 export type CompanionAction =
   | { kind: 'ship'; envelope: ModelEnvelope }
   | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true }
   | { kind: 'noop'; shareNeedsOwnerServe: boolean };
 
 /** Ship the sender's model iff it was generated from the winning MD (§4.2); otherwise decide the
  *  receiver's fate from the RECEIVER's own envelope.
  *
  *  H1 (round 4) — `unknown` must not delete. Deleting the receiver's model costs a paid Gemini
  *  magazine transform to recover (runHtmlDoc → generateMagazineModel locally, or
  *  resolveMagazineModel → reserve_serve_model → spend_ledger on the cloud), and the delete is
  *  silent and sticky: it does not throw, so the caller advances the manifest baseline, and the next
  *  run's Class-A reconcile returns 'skip' and never revisits the companion step.
  *
  *  H-R5-1 (round 5) — round 4 made the SENDER read honest but left the whole decision keyed to it,
  *  which was wrong in both directions:
  *   (a) `unknown` → noop KEPT a provably-stale receiver model. The claimed safety net does not
  *       exist: the serve path's drift guard (lib/html-doc/read-model.ts) compares section TITLES and
  *       generatorVersion, never sourceMdHash, so a prose-only MD change — precisely the
  *       recency-tiebreak case — is served as fresh forever (dig-deeper merges the cached envelope
  *       without regenerating). And `unknown` is the COMMON outcome: a cloud video that was never
  *       HTML-served has no model blob, and the Supabase backend cannot prove that 404.
  *   (b) `none` → delete DESTROYED receiver models that were still valid, since the receiver was
  *       never consulted.
  *  The backend ambiguity was only ever about the SENDER. The receiver's staleness is provable
  *  independently: we hold winnerMdHash, so a receiver sourceMdHash that is present and DIFFERENT is
  *  definitively stale — its backing body no longer exists — with no ambiguity involved. So the
  *  sender read now decides only whether a REPLACEMENT can be shipped, and everything else is keyed
  *  to the receiver. Deleting a provably-stale model is not a money loss; deleting a matching one is.
+ *
+ *  L-R6-1 (round 6) — the ship branch could DOWNGRADE. When BOTH envelopes match winnerMdHash the
+ *  bodies are identical, so the only remaining difference is generatorVersion — and shipping the
+ *  sender's blind overwrites a receiver model isFresh() accepts (lib/html-doc/read-model.ts) with one
+ *  it rejects. The share flips from rendering to a 503 (app/s/[token]/route.ts) and the only recovery
+ *  is an owner re-serve, which reserves and charges (lib/html-doc/serve-doc.ts) — the same
+ *  user-re-spend class as H1 and H-R5-1, so it is guarded rather than tolerated.
+ *  Reachability is not exotic: it needs GENERATOR_VERSION skew between the local checkout and the
+ *  deployed cloud image (routine whenever the deploy lags the checkout) AND the loser already holding
+ *  a model built from the winner's exact body — which is the normal state after any prior sync, since
+ *  reconcile-class-a.ts falls through to a transfer on equal mdHash when currency or format disagree.
+ *  So when both match, prefer the FRESHER by generatorVersion, and never write when the receiver is
+ *  already current. (The report flag stays false on every both-match path: a version-skewed receiver
+ *  was already not-fresh BEFORE this run, which is L-R6-2, deliberately out of scope here.)
  */
 export function decideCompanion(args: {
   winnerMdHash: string;
   senderModel: ModelRead;
   receiverModel: ModelRead;
 }): CompanionAction {
   const { winnerMdHash, senderModel, receiverModel } = args;
 
-  // 1. The sender holds a model built from the winning MD → ship it (it supersedes whatever the
-  //    receiver has, so the receiver's own state does not matter here).
-  if (senderModel.kind === 'envelope' && senderModel.envelope.sourceMdHash === winnerMdHash) {
-    return { kind: 'ship', envelope: senderModel.envelope };
+  const senderMatch = senderModel.kind === 'envelope'
+    && senderModel.envelope.sourceMdHash === winnerMdHash ? senderModel.envelope : null;
+  const receiverMatch = receiverModel.kind === 'envelope'
+    && receiverModel.envelope.sourceMdHash === winnerMdHash ? receiverModel.envelope : null;
+
+  // 1. BOTH sides hold a model built from the winning MD (L-R6-1). Same body, so generatorVersion is
+  //    the whole difference: ship ONLY when it is a genuine upgrade, never a downgrade, and never a
+  //    write that changes nothing.
+  if (senderMatch && receiverMatch) {
+    if (receiverMatch.generatorVersion === GENERATOR_VERSION) {
+      return { kind: 'noop', shareNeedsOwnerServe: false }; // receiver already fresh — do not write
+    }
+    if (senderMatch.generatorVersion === GENERATOR_VERSION) {
+      return { kind: 'ship', envelope: senderMatch }; // a real upgrade
+    }
+    return { kind: 'noop', shareNeedsOwnerServe: false }; // neither is current — both need a re-serve
   }
 
-  // 2. Nothing shippable, but the receiver already holds a model built from the WINNING MD — it is
+  // 2. Only the sender holds a model built from the winning MD → ship it (it supersedes whatever the
+  //    receiver has, so the receiver's own state does not matter here).
+  if (senderMatch) return { kind: 'ship', envelope: senderMatch };
+
+  // 3. Nothing shippable, but the receiver already holds a model built from the WINNING MD — it is
   //    still valid. Do not destroy a paid artifact, and the share renders, so report nothing.
-  if (receiverModel.kind === 'envelope' && receiverModel.envelope.sourceMdHash === winnerMdHash) {
-    return { kind: 'noop', shareNeedsOwnerServe: false };
-  }
+  if (receiverMatch) return { kind: 'noop', shareNeedsOwnerServe: false };
 
-  // 3. The receiver's model is not known-good. The two axes now diverge, and DELIBERATELY:
+  // 4. The receiver's model is not known-good. The two axes now diverge, and DELIBERATELY:
   //
   //  - DELETE the blob only on PROOF. A receiver envelope whose sourceMdHash is present and differs
   //    is definitively stale — its backing body no longer exists — and needs no sender read to
   //    establish. Everything else is unprovable: `none`/`unknown` say nothing about a model we never
   //    read, and a legacy pre-1F-a envelope predates sourceMdHash entirely (the field is .optional()
   //    in model-store.ts), so it cannot be checked. Fail-safe-for-money: KEEP those. A possibly-stale
   //    cache is recoverable — any regeneration overwrites it, and the existing sourceSections /
   //    generatorVersion drift guard still catches the common legacy drift — but a deleted paid
   //    artifact costs a Gemini transform to rebuild.
   //
   //  - REPORT on doubt. shareNeedsOwnerServe is a report-only count (§10 row 7): "these shares may
   //    not render until you re-serve." It spends nothing and destroys nothing, so the harmful
   //    direction is UNDER-reporting — an anon visitor silently hitting a not-ready share. Note the
   //    receiver of a copyToCloud is always the Supabase store, which can never return `none`, so
   //    keying the flag to proof would make §10 row 7 unreportable in the direction it describes.
   const provablyStale = receiverModel.kind === 'envelope'
     && receiverModel.envelope.sourceMdHash !== undefined;
   if (provablyStale) return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
   return { kind: 'noop', shareNeedsOwnerServe: true };
 }
diff --git a/lib/cloud-sync/sync-run.ts b/lib/cloud-sync/sync-run.ts
index c400a19..0896660 100644
--- a/lib/cloud-sync/sync-run.ts
+++ b/lib/cloud-sync/sync-run.ts
@@ -300,175 +300,190 @@ async function applyClassBWinners(args: {
       target.p, videoId, set as any, clear as any, { editedAt: m.editedAt },
     );
     if (!found) throw new Error(`Class-B write for ${videoId}.${f} landed on no row`);
     merged += 1;
   }
   return { merged, conflicts };
 }
 
 /** Behaviors #4/#10/#11 — the atomic Class-A transfer. stage the winner MD to the loser → verify it
  *  hashes to the expected mdHash → promote → finalize the receiver record in ONE updateVideoFields
  *  carrying the complete tuple (summaryMd key + promoted artifact status + docVersion + md signals +
  *  the 7 companion scalars). Throws on any fault so the caller does NOT advance the baseline. */
 async function transferClassA(
   winner: Side, loser: Side, winnerVideo: Video, videoId: string,
 ): Promise<{ mdHash: string; verified: boolean }> {
   const body = await readMdBody(winner.blob, winner.p, winnerVideo);
   if (body == null || !winnerVideo.summaryMd) {
     throw new Error(`transferClassA: winner ${videoId} has no MD body to copy`);
   }
   const h = mdHash(body);
   const key = winnerVideo.summaryMd;
 
   const ref = await loser.blob.putStaged(loser.p, key, Buffer.from(body, 'utf8'), 'text/markdown');
   const staged = await loser.blob.get(loser.p, ref.tempKey);
   if (!staged || mdHash(staged.toString('utf8')) !== h) {
     throw new Error(`transferClassA: staged MD verify failed for ${videoId}`);
   }
   // A two-sided Class-A transfer must OVERWRITE the loser's existing (divergent) blob at `key`.
   // promote() is NOT uniform across backends here: local rename overwrites, but SupabaseBlobStore
   // .promote() is create-if-absent (it idempotently SKIPS the move when the final already exists,
   // to tolerate concurrent same-key promoters) — so on the cloud winner-copy path the loser's stale
   // body would survive. Commit the VERIFIED staged bytes to the final key with an atomic upsert
   // (BlobStore.put, overwrite on both backends), THEN drop the staging temp. Durable-before-finalize
   // is preserved: put returns only once the winner body is the live object, and updateVideoFields
   // (below) advertises promoted only after this resolves.
   await loser.blob.put(loser.p, key, staged, 'text/markdown');
   await loser.blob.delete(loser.p, ref.tempKey).catch(() => { /* best-effort temp cleanup */ });
 
   const wv: any = winnerVideo;
   const completeTuple: any = {
     summaryMd: key,
     docVersion: wv.docVersion,
     mdGeneratedAt: wv.mdGeneratedAt ?? null,
     mdCorrectionsHash: wv.mdCorrectionsHash ?? null,
     ratings: wv.ratings,
     overallScore: wv.overallScore,
     videoType: wv.videoType,
     audience: wv.audience,
     tags: wv.tags,
     tldr: wv.tldr,
     takeaways: wv.takeaways,
     // WB-H2 — invalidate the loser's stale regenerable cache. Overwriting the loser's MD body without
     // clearing these leaves summaryHtml/digDeeper* pointing at HTML rendered from the PRE-SYNC body;
     // the serve path (buildDocHtml/ensureHtmlDoc) checks generator-version, NOT MD-body freshness, so a
     // same-format prose change (the recency-tiebreak case) would serve stale HTML indefinitely (§5.1
     // "sync moves MD, not HTML"). merge_video_data stores JSON null / local shallow-merge overrides →
     // readIndex reads falsy → forces re-render.
     //
     // H-R2-2 (round 2) — ONLY the two HTML caches are cleared here. Do NOT add `digDeeperMd: null`
     // back: digDeeperMd is not a render cache, it is the filename pointer to a PAID Gemini-generated
     // dig-deeper markdown file (lib/dig/generate.ts, written by lib/dig/dig-section.ts). Nulling it
     // orphans that file and darkens the dig-state route, VideoMenu, build-doc-html and pdf-path;
     // recovery costs fresh Gemini spend for content already paid for (and dig is out of scope for
     // M2a). digDeeperHtml re-renders for free FROM the preserved digDeeperMd.
     // The round-1 premise "matches sanitizeAdditiveVideo, which already nulls these" was the flaw:
     // sanitizeAdditiveVideo shapes a record for a receiver with NO existing row (nothing to destroy),
     // whereas transferClassA PATCHES a row that already holds its own state.
     summaryHtml: null,
     digDeeperHtml: null,
     // Deep-merged (cloud merge_video_data / local index write). No Class-B key here → no spurious
     // annotationsEditedAt stamp (F2). Never advertise promoted before the blob is durable (above).
     artifacts: { summaryMd: { key, status: 'promoted' } },
   };
   await loser.store.updateVideoFields(loser.p, videoId, completeTuple as Partial<Video>);
 
   return { mdHash: h, verified: true };
 }
 
 /** Behavior #5 — ship the winner's summary MODEL to the loser iff it was generated from the winning
  *  MD; otherwise delete the loser's model (best-effort, OUTSIDE the atomic commit) and flag that the
- *  owner must re-serve — but ONLY when that model proves itself stale (H-R5-1). */
+ *  owner must re-serve — but ONLY when that model proves itself stale (H-R5-1).
+ *
+ *  Every companion write is BEST-EFFORT and never throws (M-R6-1): the caller must still advance the
+ *  baseline, because transferClassA has already committed the winner body durably. A returned `error`
+ *  is surfaced in report.errors by the caller without aborting the per-video flow. */
 async function companionTransfer(
   winner: Side, loser: Side, winnerMdHash: string, winnerVideo: Video,
-): Promise<{ shareNeedsOwnerServe: boolean }> {
+): Promise<{ shareNeedsOwnerServe: boolean; error?: string }> {
   if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
   const base = winnerVideo.summaryMd.replace(/\.md$/, '');
   // H-R5-1 (round 5) — read BOTH sides. The sender read says whether a replacement can be shipped;
   // only the RECEIVER's own envelope can prove the receiver's model stale (see decideCompanion).
   const [senderModel, receiverModel] = await Promise.all([
     readModelSide(winner, base), readModelSide(loser, base),
   ]);
   const decision = decideCompanion({ winnerMdHash, senderModel, receiverModel });
   if (decision.kind === 'ship') {
-    await writeModelEnvelope(loser.p, base, decision.envelope, loser.blob);
-    return { shareNeedsOwnerServe: false };
+    // M-R6-1 — a throw here would be STICKY, not merely noisy: the Class-A body already landed, so the
+    // next run's reconcileClassA returns 'skip' and the companion step (gated on !== 'skip') never
+    // runs again. The receiver would keep a model built from the PRE-SYNC body — and if its section
+    // titles and generatorVersion still match, the serve path's drift guard cannot see it, so it is
+    // served as fresh forever (the prose-only-change case behind H-R5-1). Swallow the failure the way
+    // the delete below already does and report the share as unready, so the staleness is at least
+    // visible; the error is returned so it still surfaces in report.errors.
+    try {
+      await writeModelEnvelope(loser.p, base, decision.envelope, loser.blob);
+      return { shareNeedsOwnerServe: false };
+    } catch (e: any) {
+      return { shareNeedsOwnerServe: true, error: `companion model ship failed: ${e?.message ?? String(e)}` };
+    }
   }
   // H1 (round 4) / H-R5-1 (round 5) — nothing shippable and the receiver's model is not PROVABLY
   // stale: leave the blob alone. The report flag is decided separately (§10 row 7 counts a share
   // with no model even though there is nothing to delete).
   if (decision.kind === 'noop') return { shareNeedsOwnerServe: decision.shareNeedsOwnerServe };
   // deleteReceiverModel — best-effort; a missing model blob is not an error.
   try { await loser.blob.delete(loser.p, `models/${base}.json`); } catch { /* best-effort */ }
   return { shareNeedsOwnerServe: true };
 }
 
 /** H1 (round 4) — resolve `readModelEnvelope`'s single null into the tri-state decideCompanion needs.
  *  A null means absent, corrupt, or unreadable; only a backend that can prove absence
  *  (BlobStore.provesAbsence — the local FS store, whose get is ENOENT-only) lets us tell those
  *  apart. On such a backend a null is definitive either way: the model is genuinely missing, or its
  *  bytes were read and rejected — both mean that side has nothing usable. On the Supabase backend
  *  the same null may be a transient 5xx / timeout / RLS denial, so it proves nothing and must not
  *  drive a destructive delete. A backend that does not declare the capability is treated as unable
  *  to prove absence.
  *  H-R5-1 (round 5) — used for the RECEIVER too (hence the neutral name): a receiver `unknown` must
  *  not be read as "no model", and a receiver `none` leaves nothing to delete. */
 async function readModelSide(side: Side, base: string): Promise<ModelRead> {
   const envelope = await readModelEnvelope(side.p, base, side.blob);
   if (envelope) return { kind: 'envelope', envelope };
   return side.blob.provesAbsence ? { kind: 'none' } : { kind: 'unknown' };
 }
 
 /** The manifest baseline written AFTER a verified reconcile — the AGREED post-reconcile state, not a
  *  winner. Class A = the winning signals + verified mdHash (or the shared state on skip). Class B —
  *  per field: advance to the resolved (value, editedAt) EXCEPT a no-write conflict
  *  (winner==='equal' && conflict), which carries the PREVIOUS baseline unchanged (round-3 H2:
  *  recording the winner there would be a false agreement → next-run silent overwrite). */
 function buildClassBBaseline(
   merges: Record<HumanField, FieldMerge>, previousBaseline: VideoBaseline | undefined,
 ): VideoBaseline['classB'] {
   const classB = {} as VideoBaseline['classB'];
   for (const f of FIELDS) {
     const m = merges[f];
     if (m.winner === 'equal' && m.conflict) {
       classB[f] = previousBaseline?.classB?.[f] ?? { value: undefined, editedAt: undefined };
     } else {
       classB[f] = { value: m.value, editedAt: m.editedAt };
     }
   }
   return classB;
 }
 
 function buildBaseline(
   winnerSignals: ClassASignals, winnerMdHash: string | null,
   merges: Record<HumanField, FieldMerge>, previousBaseline: VideoBaseline | undefined,
 ): VideoBaseline {
   return {
     classA: {
       docVersionMajor: winnerSignals.docVersionMajor,
       mdGeneratedAt: winnerSignals.mdGeneratedAt,
       mdCorrectionsHash: winnerSignals.mdCorrectionsHash,
       mdHash: winnerMdHash,
     },
     classB: buildClassBBaseline(merges, previousBaseline),
   };
 }
 
 /** WB-B1 — the manifest baseline for a corrections NO-WRITE conflict (§5.5). No Class-A copy ran, so
  *  Class A must NOT advance to a winner (that would record a false agreement → next-run silent
  *  overwrite around an unresolved conflict). Preserve the PREVIOUS Class-A baseline so the next run
  *  re-evaluates the currency-based transfer from the live signals. On a first sync (no previous
  *  baseline) record an HONEST unresolved placeholder (mdHash null → "no agreed MD"); Class-A baseline
  *  is write-only (never read by reconcileClassA), so next run re-derives from the actual bodies
  *  regardless. Class B carries the preserved conflict (buildClassBBaseline). */
 function buildCorrectionsUnresolvedBaseline(
   merges: Record<HumanField, FieldMerge>, previousBaseline: VideoBaseline | undefined,
 ): VideoBaseline {
   return {
     classA: previousBaseline?.classA
       ?? { docVersionMajor: 0, mdGeneratedAt: null, mdCorrectionsHash: null, mdHash: null },
     classB: buildClassBBaseline(merges, previousBaseline),
   };
 }
 
 export async function runSync(
   deps: SyncDeps, opts: { playlistKey?: string } = {},
@@ -547,94 +562,97 @@ export async function runSync(
         //
         //    Class-A signals are derived HERE (before the guard) because the guard needs them; the
         //    derivation is PURE (it only reads the record + the MD body), so hoisting it changes no
         //    behavior. Bodies are needed for hashing regardless — Behavior #1.
         const la = deriveClassASignals(lv, await readMdBody(deps.localBlob, localP, lv));
         const ca = deriveClassASignals(cv, await readMdBody(deps.cloudBlob, cloudP, cv));
 
         // ── B1 (round 3) — the two-sided counterpart of copyAdditiveVideo's WB-H1/H-R2-1 guard (:160).
         //    readMdBody returns null for TWO different situations: the record advertises no summaryMd,
         //    or it advertises one whose bytes could not be READ. The backends disagree on which errors
         //    are which: local get throws on anything but ENOENT, but the Supabase get is `if (error)
         //    return null` — it swallows EVERY failure (network, 5xx, timeout, RLS denial), so on the
         //    cloud side an ordinary transient download error is indistinguishable from "no MD".
         //    deriveClassASignals maps a null body to mdHash: null, and reconcileClassA reads
         //    mdHash == null as "this side HAS NO MD" (:21-23) — and those presence branches return
         //    BEFORE the corrections-currency and never-downgrade-format ladder (:38-46). So an
         //    unreadable body made the other replica's body get copied over it (destroying it) and
         //    recorded a full-agreement baseline; run 2 then saw identical bodies and skipped, making
         //    the loss permanent and recoverable only by paid regeneration.
         //    Throwing per-video is caught below, surfaces in report.errors, and advances NO baseline,
         //    so the run heals by itself once the body is readable. With this guard reconcileClassA's
         //    !lHas/!cHas branches mean what they claim: the side genuinely advertises no summaryMd —
         //    which is exactly M-R2-2's "purely additive hydration", so its intent is preserved.
         //    H2 (round 4) — the guard is scoped to the backend that actually needs it. It exists
         //    ONLY because one backend cannot tell absent from unreadable, so only that backend
         //    should pay for it (BlobStore.provesAbsence). On the local FS store a null body IS
         //    proof the file is gone — the user moved or deleted the .md by hand, or a generation
         //    crashed between the index write and the blob write — and that case heals for free:
         //    !lHas → copyToLocal writes the cloud's intact body over the dangling pointer, purely
         //    additive, nothing to destroy. Throwing there stranded the video on EVERY run forever,
         //    never advancing a baseline, with no exit but hand-editing playlist-index.json or
         //    paying to regenerate content sitting intact in the cloud — re-introducing exactly the
         //    stranding M-R2-2 removed. The cloud side stays fail-closed, unchanged.
         if (lv.summaryMd && la.mdHash == null && !deps.localBlob.provesAbsence) {
           throw new Error(`local MD body unreadable for ${id}`);
         }
         if (cv.summaryMd && ca.mdHash == null && !deps.cloudBlob.provesAbsence) {
           throw new Error(`cloud MD body unreadable for ${id}`);
         }
 
         //    M-R2-2 — the skip is narrowed to the genuinely DESTRUCTIVE case: BOTH sides actually hold
         //    an MD body. When one side has none, the Class-A copy is purely ADDITIVE hydration —
         //    nothing can be destroyed and no false agreement about competing bodies is possible — so
         //    skipping would strand the video with no MD forever (safe-but-stuck until a human edits
         //    corrections). The corrections conflict is still logged by Class B and still flags
         //    needsRegen via reconcileClassA (the hydrated MD is corrections-stale).
         const correctionsUnresolved = merges.corrections.winner === 'equal' && merges.corrections.conflict;
         if (correctionsUnresolved && la.mdHash != null && ca.mdHash != null) {
           report.needsRegen += 1;
           if (lv.archived !== cv.archived) report.archivedNotSynced += 1; // R10 — do NOT sync archived
           await writeVideoBaseline(dataRoot, key, id, buildCorrectionsUnresolvedBaseline(merges, base));
           continue;
         }
 
         // ── Class A (la/ca derived above the WB-B1 guard, which needs them — Behavior #1).
         const decision = reconcileClassA({ local: la, cloud: ca, reconciledCorrectionsHash });
         if (decision.needsRegen) report.needsRegen += 1;
 
         let winnerMdHash: string | null = null;
         let winnerSignals: ClassASignals = la;
         let winnerSide: Side | null = null;
         let loserSide: Side | null = null;
         let winnerVideo: Video = lv;
 
         if (decision.action === 'copyToCloud') {
           winnerSide = localSide; loserSide = cloudSide; winnerVideo = lv; winnerSignals = la;
           winnerMdHash = (await transferClassA(localSide, cloudSide, lv, id)).mdHash;
           report.updatedCloud += 1;
         } else if (decision.action === 'copyToLocal') {
           winnerSide = cloudSide; loserSide = localSide; winnerVideo = cv; winnerSignals = ca;
           winnerMdHash = (await transferClassA(cloudSide, localSide, cv, id)).mdHash;
           report.updatedLocal += 1;
         } else {
           report.skippedIdentical += 1;
           winnerMdHash = la.mdHash; winnerSignals = la; // skip: sides already agree
         }
 
         if (decision.action !== 'skip' && winnerMdHash && winnerSide && loserSide) {
           const c = await companionTransfer(winnerSide, loserSide, winnerMdHash, winnerVideo);
           if (c.shareNeedsOwnerServe) report.shareNeedsOwnerServe += 1;
+          // M-R6-1 — companion failures are reported, never thrown: the Class-A commit above is
+          // durable, so the baseline below MUST still advance (re-running would not retry the ship).
+          if (c.error) report.errors.push({ videoId: id, message: c.error });
         }
         if (lv.archived !== cv.archived) report.archivedNotSynced += 1; // R10 — do NOT sync archived
 
         // ── Manifest AFTER the verified commit (Behavior #10); advance even on skip (N4). Pass the
         //    PREVIOUS baseline so a no-write Class-B conflict is NOT falsely advanced (round-3 H2).
         await writeVideoBaseline(dataRoot, key, id, buildBaseline(winnerSignals, winnerMdHash, merges, base));
       } catch (e: any) {
         report.errors.push({ videoId: id, message: e?.message ?? String(e) }); // Behaviors #11/#13
       }
     }
   }
 
   return report;
 }
diff --git a/tests/integration/cloud-sync/e2e.int.test.ts b/tests/integration/cloud-sync/e2e.int.test.ts
index 748488d..4003e27 100644
--- a/tests/integration/cloud-sync/e2e.int.test.ts
+++ b/tests/integration/cloud-sync/e2e.int.test.ts
@@ -1,131 +1,133 @@
 // tests/integration/cloud-sync/e2e.int.test.ts
 //
 // Stage 3 Cloud Sync (§10), Task 14 — the end-to-end keystone. One `it(...)` per §10 scenario,
 // driving the FULL runSync stack against real local FS ↔ local Supabase under an authenticated
 // USER session (never service-role). Where Task 12 proved the additive hydrate path, rows 1/2/7
 // here drive the TWO-SIDED Class-A COPY path (transferClassA + companionTransfer) with DIVERGENT
 // MD bodies — the winner-copy path the Task-12 tests never exercised.
 //
 // Money invariant: a sync copy NEVER charges — every additive/transfer row asserts spendLedgerTotal
 // is unchanged (or a whole-suite money check). No producer/enqueue is on the sync path.
 import { promises as fs } from 'fs';
 import os from 'os';
 import path from 'path';
 import { randomUUID } from 'crypto';
 import {
   makeOwnerContext, prepareSyncCtx, seedCloudVideo, seedLocalVideoFull, seedManifestBaseline,
   cloudVideoRecord, localVideoRecord, cloudBlobBytes, localBlobBytes, putCloudBlob, type Ctx,
 } from '@/tests/integration/helpers/cloud';
 import { adminClient } from '@/tests/integration/helpers/clients';
 import { runSync } from '@/lib/cloud-sync/sync-run';
 import { mdHash } from '@/lib/cloud-sync/content-hash';
+import { GENERATOR_VERSION } from '@/lib/html-doc/constants';
 import { getAuthedClient, NoSessionError, type TokenStore } from '@/lib/cloud-sync/auth';
 import type { VideoBaseline } from '@/lib/cloud-sync/types';
 
 afterAll(async () => {
   const home = os.homedir();
   const dirs = (await fs.readdir(home)).filter((d) => d.startsWith('.cs-syncrun-'));
   await Promise.all(dirs.map((d) => fs.rm(path.join(home, d), { recursive: true, force: true })));
 });
 
 const key = (ctx: Ctx) => `${ctx.videoId}.md`;
 /** `artifacts` lives in the videos.data jsonb but is not on the Video Zod type — read it via a cast. */
 const artifactsOf = (rec: { [k: string]: unknown } | null) =>
   (rec as { artifacts?: { summaryMd?: { status?: string } } & Record<string, unknown> } | null)?.artifacts;
 /** SHA-256 of the canonicalized MD BODY (matches the orchestrator's transfer verify). */
 const bodyHash = (b: string) => mdHash(b);
 /** mdCorrectionsHash value that makes a side "corrections-current" when NO corrections exist:
  *  reconciledCorrectionsHash === mdHash(String(undefined ?? '')) === mdHash(''). */
 const H_NO_CORRECTIONS = mdHash('');
 /** The companion model blob key for this ctx's summary (models/<base>.json, base = summaryMd sans .md). */
 const modelKey = (ctx: Ctx) => `models/${ctx.videoId}.json`;
 /** A schema-valid ModelEnvelope (ModelEnvelopeSchema) whose sourceMdHash is caller-supplied. */
-const modelEnvelope = (sourceMdHash: string) => ({
+const modelEnvelope = (sourceMdHash: string, generatorVersion?: string) => ({
   sourceMd: 'seed.md', generatedAt: '2026-01-01T00:00:00.000Z', sourceSections: ['A'],
   model: {
     sections: [{
       lead: 'lead',
       bullets: [{ label: 'a', text: 'b' }, { label: 'c', text: 'd' }, { label: 'e', text: 'f' }],
     }],
   },
   sourceMdHash,
+  ...(generatorVersion ? { generatorVersion } : {}),
 });
 /** Read the cloud playlist row's title (admin client — assertion only, not a code path). */
 async function cloudPlaylistTitle(ctx: Ctx): Promise<string | null> {
   const { data, error } = await adminClient()
     .from('playlists').select('playlist_title').eq('playlist_key', ctx.playlistKey).single();
   if (error) throw error;
   return (data as { playlist_title: string | null }).playlist_title;
 }
 
 /** A syntactically-complete baseline whose classA/classB are inert for the assertion under test. */
 function baseline(classB: VideoBaseline['classB']): VideoBaseline {
   return {
     classA: { docVersionMajor: 1, mdGeneratedAt: null, mdCorrectionsHash: null, mdHash: null },
     classB,
   };
 }
 const EMPTY_CLASSB = {
   personalNote: { value: undefined, editedAt: undefined },
   personalScore: { value: undefined, editedAt: undefined },
   corrections: { value: undefined, editedAt: undefined },
 } as VideoBaseline['classB'];
 
 describe('cloud-sync §10 end-to-end scenarios', () => {
   // ── Row 1 — Class-A anti-recency: higher-major MD beats a NEWER-timestamp lower-major MD.
   //    Two-sided, DIVERGENT bodies → reconcileClassA returns copyToCloud → transferClassA runs.
   it('row 1: higher-major MD beats a newer lower-major (format beats recency); receiver copies it', async () => {
     const ctx = await makeOwnerContext();
     const bodyHi = '# HiMajor\n\nformat-3 content\n';   // local, docVersion.major=3, OLD timestamp
     const bodyLo = '# LoMajor\n\nformat-1 content\n';   // cloud, docVersion.major=1, NEWER timestamp
     const winnerRatings = { usefulness: 5, depth: 2, originality: 4, recency: 1, completeness: 3 };
     await seedLocalVideoFull(ctx, {
       mdBody: bodyHi, docVersion: { major: 3, minor: 0 }, mdGeneratedAt: '2020-01-01T00:00:00.000Z',
       mdCorrectionsHash: H_NO_CORRECTIONS, ratings: winnerRatings, overallScore: 3,
       tldr: 'the-tldr', takeaways: ['a', 'b'], tags: ['x', 'y'],
     });
     await seedCloudVideo(ctx, {
       mdBody: bodyLo, docVersion: { major: 1, minor: 0 }, mdGeneratedAt: '2026-06-01T00:00:00.000Z',
       mdCorrectionsHash: H_NO_CORRECTIONS,
     });
     const spendBefore = await ctx.spendLedgerTotal();
 
     const report = await runSync(ctx.syncDeps());
 
     expect(report.updatedCloud).toBeGreaterThanOrEqual(1);
     expect(await ctx.spendLedgerTotal()).toBe(spendBefore); // sync copy never charges
 
     // transferClassA promote→finalize genuinely ran: the loser (cloud) blob holds the WINNER bytes.
     const cloudBody = await cloudBlobBytes(ctx, key(ctx));
     expect(cloudBody).not.toBeNull();
     expect(cloudBody!.toString('utf8')).toBe(bodyHi);
     expect(bodyHash(cloudBody!.toString('utf8'))).toBe(bodyHash(bodyHi));
 
     // updateVideoFields finalize carried the winner's docVersion + companion scalars verbatim.
     const cloud = await cloudVideoRecord(ctx);
     expect(cloud?.docVersion?.major).toBe(3);
     expect(cloud?.ratings).toEqual(winnerRatings);
     expect(cloud?.overallScore).toBe(3);
     expect(cloud?.tldr).toBe('the-tldr');
     expect(cloud?.takeaways).toEqual(['a', 'b']);
     expect(cloud?.tags).toEqual(['x', 'y']);
     expect(artifactsOf(cloud)?.summaryMd?.status).toBe('promoted');
   });
 
   // ── Row 2 — corrections-current lower-major MD survives over a corrections-STALE higher-major MD.
   //    Currency beats format → the corrections-current body lands on BOTH sides.
   //    Winner is the CLOUD side here → copyToLocal, exercising the local-overwrite transfer direction.
   it('row 2: corrections-current lower-major beats stale higher-major (currency beats format)', async () => {
     const ctx = await makeOwnerContext();
     const bodyCurrent = '# CurrentCorrections\n\nlower-major but corrections-current\n'; // cloud (winner)
     const bodyStale = '# StaleHiMajor\n\nhigher-major but corrections-stale\n';          // local (loser)
     const winnerRatings = { usefulness: 5, depth: 3, originality: 2, recency: 4, completeness: 1 };
     const editedAt = '2025-06-01T00:00:00.000Z';
     await seedCloudVideo(ctx, {
       mdBody: bodyCurrent, docVersion: { major: 1, minor: 0 }, mdGeneratedAt: '2025-01-01T00:00:00.000Z',
       corrections: 'fix-v2', annotationsEditedAt: { corrections: editedAt },
       mdCorrectionsHash: mdHash('fix-v2'),  // current: matches the reconciled corrections
       ratings: winnerRatings, tldr: 'keep-me', takeaways: ['k1'], tags: ['t1'],
     });
     await seedLocalVideoFull(ctx, {
       mdBody: bodyStale, docVersion: { major: 3, minor: 0 }, mdGeneratedAt: '2026-01-01T00:00:00.000Z',
@@ -165,161 +167,163 @@ describe('cloud-sync §10 end-to-end scenarios', () => {
   });
 
   // ── Row 4 — companion scalars carried VERBATIM (not reconstructed/flattened) on an additive hydrate.
   it('row 4: carries the 5 real ratings + tldr/takeaways/tags verbatim (not reconstructed)', async () => {
     const ctx = await makeOwnerContext();
     const ratings = { usefulness: 5, depth: 2, originality: 4, recency: 1, completeness: 3 }; // NON-flat
     await seedCloudVideo(ctx, {
       mdBody: '# S\n\nbody\n', ratings, overallScore: 3,
       tldr: 'the tldr', takeaways: ['t1', 't2'], tags: ['x', 'y'], docVersion: { major: 3, minor: 3 },
     });
 
     await runSync(ctx.syncDeps()); // hydrate empty local from cloud
     const local = await localVideoRecord(ctx);
     expect(local?.ratings).toEqual(ratings);
     expect(local?.overallScore).toBe(3);
     expect(local?.tldr).toBe('the tldr');
     expect(local?.takeaways).toEqual(['t1', 't2']);
     expect(local?.tags).toEqual(['x', 'y']);
   });
 
   // ── Row 5 — Class-B: a note edit on local + a score edit on cloud → BOTH survive on both sides.
   it('row 5: independent Class-B edits (note local, score cloud) both survive', async () => {
     const ctx = await makeOwnerContext();
     const body = '# Same\n\nidentical current MD\n';
     await seedLocalVideoFull(ctx, {
       mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS,
       personalNote: 'mynote', annotationsEditedAt: { personalNote: '2026-03-01T00:00:00.000Z' },
     });
     await seedCloudVideo(ctx, {
       mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS,
       personalScore: 4, annotationsEditedAt: { personalScore: '2026-03-02T00:00:00.000Z' },
     });
 
     const report = await runSync(ctx.syncDeps());
     expect(report.mergedFields).toBeGreaterThanOrEqual(2);
 
     const local = await localVideoRecord(ctx);
     const cloud = await cloudVideoRecord(ctx);
     expect(local?.personalNote).toBe('mynote');
     expect(local?.personalScore).toBe(4);
     expect(cloud?.personalNote).toBe('mynote');
     expect(cloud?.personalScore).toBe(4);
   });
 
   // ── Row 6 — Class-B cleared field is NOT resurrected (baseline-aware). Local cleared vs cloud stale.
   it('row 6: a cleared Class-B field is not resurrected (baseline-aware)', async () => {
     const ctx = await makeOwnerContext();
     const body = '# Same6\n\nidentical current MD\n';
     // Local cleared personalNote (value gone, but a NEWER edit timestamp); cloud still holds the old value.
     await seedLocalVideoFull(ctx, {
       mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS,
       annotationsEditedAt: { personalNote: '2026-05-02T00:00:00.000Z' }, // cleared: no personalNote value
     });
     await seedCloudVideo(ctx, {
       mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS,
       personalNote: 'old', annotationsEditedAt: { personalNote: '2026-05-01T00:00:00.000Z' },
     });
     await seedManifestBaseline(ctx, baseline({
       ...EMPTY_CLASSB,
       personalNote: { value: 'old', editedAt: '2026-05-01T00:00:00.000Z' },
     }));
 
     await runSync(ctx.syncDeps());
 
     const local = await localVideoRecord(ctx);
     const cloud = await cloudVideoRecord(ctx);
     expect(local?.personalNote == null).toBe(true);
     expect(cloud?.personalNote == null).toBe(true); // the clear propagated; 'old' not resurrected
   });
 
   // ── Row 7 — synced+shared, model missing → anon share not-ready until owner serve (counted).
   it('row 7: a transferred summary with no matching model flags shareNeedsOwnerServe', async () => {
     const ctx = await makeOwnerContext();
     await seedLocalVideoFull(ctx, {
       mdBody: '# Winner7\n\nformat-2\n', docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
     });
     await seedCloudVideo(ctx, {
       mdBody: '# Loser7\n\nformat-1\n', docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
     });
 
-    const report = await runSync(ctx.syncDeps()); // winner (local) has no model envelope → deleteReceiverModel
+    // L-R6-3 — neither side holds a model envelope, and the Supabase receiver cannot prove its own
+    // absence, so this takes the `noop + shareNeedsOwnerServe: true` path (H-R5-1), NOT a delete.
+    const report = await runSync(ctx.syncDeps());
     expect(report.shareNeedsOwnerServe).toBeGreaterThanOrEqual(1);
   });
 
   // ── Row 8 — additive create never calls the metered enqueue (spend_ledger unchanged).
   it('row 8: additive hydrate never charges (spend_ledger unchanged)', async () => {
     const ctx = await makeOwnerContext();
     await seedCloudVideo(ctx, { mdBody: '# Free\n\nno charge\n' });
     const spendBefore = await ctx.spendLedgerTotal();
 
     const report = await runSync(ctx.syncDeps());
 
     expect(report.created).toBeGreaterThanOrEqual(1);
     expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
   });
 
   // ── Row 9 — a baseline-present remote delete is NOT re-created; counted as removed.
   it('row 9: a baseline-present video absent on one side is removed, not re-created', async () => {
     const ctx = await makeOwnerContext();
     // Cloud still holds the video; local deleted it; a baseline records they once agreed.
     await seedCloudVideo(ctx, { mdBody: '# Deleted\n\ngone locally\n' });
     await seedManifestBaseline(ctx, baseline(EMPTY_CLASSB));
 
     const report = await runSync(ctx.syncDeps());
 
     expect(report.removed).toBeGreaterThanOrEqual(1);
     expect(await localVideoRecord(ctx)).toBeNull();          // not re-hydrated
     expect(await cloudVideoRecord(ctx)).not.toBeNull();      // present side untouched (no propagation, M2b)
     expect(report.created).toBe(0);
   });
 
   // ── Row 10 — no-session refusal + a client-forged owner_id is RLS-rejected.
   it('row 10: getAuthedClient throws with no session; a forged owner_id is RLS-rejected', async () => {
     const emptyStore: TokenStore = { read: async () => null, write: async () => {}, clear: async () => {} };
     await expect(getAuthedClient(emptyStore)).rejects.toBeInstanceOf(NoSessionError);
 
     const ctx = await makeOwnerContext();
     const { error } = await ctx.userClient.from('playlists').insert({
       owner_id: randomUUID(), // NOT auth.uid() → RLS with-check rejects
       playlist_key: `k-${randomUUID()}`, playlist_url: 'https://x/forged',
     });
     expect(error).toBeTruthy();
   });
 
   // ── Row 11 — additive create excludes regenerable cache (summaryHtml/PDF null/absent on receiver).
   it('row 11: additive create excludes regenerable cache (no summaryHtml/pdf copied)', async () => {
     const ctx = await makeOwnerContext();
     await seedCloudVideo(ctx, {
       mdBody: '# Cached\n\nhas cache\n',
       summaryHtml: '<html>cached</html>',
       digDeeperHtml: '<html>dig</html>',
       extraArtifacts: { summaryPdf: { key: 'p.pdf', status: 'promoted' } },
     });
 
     await runSync(ctx.syncDeps());
     const local = await localVideoRecord(ctx);
     expect(local?.summaryHtml == null).toBe(true);
     expect(local?.digDeeperHtml == null).toBe(true);
     expect(artifactsOf(local)?.summaryPdf).toBeUndefined();
   });
 
   // ── Row 12 — a backfilled Class-B conflict is preserved across TWO runs (§5.5, round-3 H2).
   it('row 12: backfilled divergent note logs+skips on both runs; neither side overwritten', async () => {
     const ctx = await makeOwnerContext();
     const body = '# Same12\n\nidentical current MD\n';
     // Both sides carry a DIFFERENT personalNote with NO per-field timestamp → both backfilled.
     await seedLocalVideoFull(ctx, { mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS, personalNote: 'note-local' });
     await seedCloudVideo(ctx, { mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS, personalNote: 'note-cloud' });
 
     const r1 = await runSync(ctx.syncDeps());
     expect(r1.conflictsLogged).toBeGreaterThanOrEqual(1);
     expect((await localVideoRecord(ctx))?.personalNote).toBe('note-local');
     expect((await cloudVideoRecord(ctx))?.personalNote).toBe('note-cloud');
     const m1 = await ctx.readManifest();
     expect((m1.videos[ctx.videoId] as VideoBaseline).classB.personalNote.value).toBeUndefined();
 
     const r2 = await runSync(ctx.syncDeps());
     expect(r2.conflictsLogged).toBeGreaterThanOrEqual(1); // re-logs (not silently skipped)
     expect((await localVideoRecord(ctx))?.personalNote).toBe('note-local'); // still not overwritten
     expect((await cloudVideoRecord(ctx))?.personalNote).toBe('note-cloud');
     const m2 = await ctx.readManifest();
@@ -705,160 +709,237 @@ describe('cloud-sync §10 end-to-end scenarios', () => {
     expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
   });
 
   // (ii) The round-4 money bug, preserved: the receiver's model was built from the very body that
   //      just won, so it is still valid. An unprovable sender read must not cost the owner a paid
   //      Gemini magazine transform to rebuild what it already has.
   it('H-R5-1(ii): an unprovable sender read PRESERVES a receiver model that matches the winner (2 runs)', async () => {
     const ctx = await makeOwnerContext();
     const bodyLocalOld = '# LocalOld\n\nlower-major local body\n';
     const bodyCloudWin = '# CloudWin\n\nhigher-major winner body\n';
     await seedLocalVideoFull(ctx, {
       mdBody: bodyLocalOld, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
     });
     await seedCloudVideo(ctx, {
       mdBody: bodyCloudWin, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
     });
     // Receiver (local) model already matches the WINNING cloud body; sender (cloud) holds no model.
     const envelope = modelEnvelope(bodyHash(bodyCloudWin));
     await ctx.localBlob.put(
       ctx.localPrincipal, modelKey(ctx),
       Buffer.from(`${JSON.stringify(envelope)}\n`, 'utf8'), 'application/json',
     );
     const spendBefore = await ctx.spendLedgerTotal();
 
     const r1 = await runSync(ctx.syncDeps());
 
     expect(r1.updatedLocal).toBeGreaterThanOrEqual(1);
     const kept = await localBlobBytes(ctx, modelKey(ctx));
     expect(kept).not.toBeNull();                                     // paid artifact survives
     expect(JSON.parse(kept!.toString('utf8')).sourceMdHash).toBe(bodyHash(bodyCloudWin));
     expect(r1.shareNeedsOwnerServe).toBe(0);                         // no false "share is stale"
     expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
 
     const r2 = await runSync(ctx.syncDeps());
     expect(r2.shareNeedsOwnerServe).toBe(0);
     expect(await localBlobBytes(ctx, modelKey(ctx))).not.toBeNull();
     expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
   });
 
   // (iii) The other half of round 4's conflation, on the backend that CAN prove absence. A local
   //       sender null also covers corrupt/schema-invalid (readModelEnvelope parses and validates),
   //       which round 4 mapped to `none` → delete. But "the sender's envelope is garbage" says
   //       nothing about the receiver's, and here the cloud receiver's matches the winning body
   //       exactly. Deleting it would burn reserve_serve_model → spend_ledger to rebuild.
   it('H-R5-1(iii): a CORRUPT local sender envelope preserves a matching cloud receiver model (2 runs)', async () => {
     const ctx = await makeOwnerContext();
     const bodyLocalWin = '# LocalWin\n\nhigher-major local body\n';
     const bodyCloudOld = '# CloudOld\n\nlower-major cloud body\n';
     await seedLocalVideoFull(ctx, {
       mdBody: bodyLocalWin, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
     });
     await seedCloudVideo(ctx, {
       mdBody: bodyCloudOld, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
     });
     // Sender (local) envelope is unparseable → readModelEnvelope null on a provesAbsence backend.
     await ctx.localBlob.put(
       ctx.localPrincipal, modelKey(ctx), Buffer.from('{not json at all', 'utf8'), 'application/json',
     );
     // Receiver (cloud) model matches the WINNING local body → still valid, must survive.
     await putCloudBlob(
       ctx, modelKey(ctx),
       Buffer.from(`${JSON.stringify(modelEnvelope(bodyHash(bodyLocalWin)))}\n`, 'utf8'), 'application/json',
     );
     const spendBefore = await ctx.spendLedgerTotal();
 
     const r1 = await runSync(ctx.syncDeps());
 
     expect(r1.updatedCloud).toBeGreaterThanOrEqual(1);
     const kept = await cloudBlobBytes(ctx, modelKey(ctx));
     expect(kept).not.toBeNull();
     expect(JSON.parse(kept!.toString('utf8')).sourceMdHash).toBe(bodyHash(bodyLocalWin));
     expect(r1.shareNeedsOwnerServe).toBe(0);
     expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
 
     const r2 = await runSync(ctx.syncDeps());
     expect(r2.shareNeedsOwnerServe).toBe(0);
     expect(await cloudBlobBytes(ctx, modelKey(ctx))).not.toBeNull();
     expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
   });
 
+  // ── L-R6-1 (round 6) — the ship branch must never DOWNGRADE the receiver. Both sides hold a model
+  //    built from the WINNING body, but the sender's was built by an older checkout (GENERATOR_VERSION
+  //    skew between the local tree and the deployed cloud image). Shipping it blind would replace a
+  //    model isFresh() accepts with one it rejects, flipping the share to a 503 whose only recovery is
+  //    a PAID owner re-serve.
+  it('L-R6-1: a ship never overwrites a receiver model that is already generation-fresh', async () => {
+    const ctx = await makeOwnerContext();
+    const bodyLocalWin = '# LocalWin\n\nhigher-major local body\n';
+    const bodyCloudOld = '# CloudOld\n\nlower-major cloud body\n';
+    await seedLocalVideoFull(ctx, {
+      mdBody: bodyLocalWin, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
+    });
+    await seedCloudVideo(ctx, {
+      mdBody: bodyCloudOld, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
+    });
+    // Both envelopes were built from the winning body; only the SENDER's generation is behind.
+    await ctx.localBlob.put(
+      ctx.localPrincipal, modelKey(ctx),
+      Buffer.from(`${JSON.stringify(modelEnvelope(bodyHash(bodyLocalWin), 'magazine-skim v1'))}\n`, 'utf8'),
+      'application/json',
+    );
+    await putCloudBlob(
+      ctx, modelKey(ctx),
+      Buffer.from(`${JSON.stringify(modelEnvelope(bodyHash(bodyLocalWin), GENERATOR_VERSION))}\n`, 'utf8'),
+      'application/json',
+    );
+    const spendBefore = await ctx.spendLedgerTotal();
+
+    const r1 = await runSync(ctx.syncDeps());
+
+    expect(r1.updatedCloud).toBeGreaterThanOrEqual(1);          // the Class-A transfer still ran
+    const kept = await cloudBlobBytes(ctx, modelKey(ctx));
+    expect(kept).not.toBeNull();
+    const keptEnvelope = JSON.parse(kept!.toString('utf8'));
+    expect(keptEnvelope.generatorVersion).toBe(GENERATOR_VERSION); // NOT downgraded to v1
+    expect(keptEnvelope.sourceMdHash).toBe(bodyHash(bodyLocalWin));
+    expect(r1.shareNeedsOwnerServe).toBe(0);                     // the share still renders
+    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
+  });
+
+  // ── M-R6-1 (round 6) — a failed companion ship must not be sticky-silent. transferClassA has
+  //    already committed the winner body durably, so the next run's reconcile returns 'skip' and the
+  //    ship is never retried; the receiver keeps a model built from the PRE-SYNC body. Swallow the
+  //    write failure, keep the baseline advancing (the Class-A commit DID land), and report the share
+  //    as unready so the staleness is visible instead of being served as fresh forever.
+  it('M-R6-1: a failed companion ship reports the share unready, still advances the baseline', async () => {
+    const ctx = await makeOwnerContext();
+    const bodyLocalWin = '# LocalWin\n\nhigher-major local body\n';
+    const bodyCloudOld = '# CloudOld\n\nlower-major cloud body\n';
+    await seedLocalVideoFull(ctx, {
+      mdBody: bodyLocalWin, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
+    });
+    await seedCloudVideo(ctx, {
+      mdBody: bodyCloudOld, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
+    });
+    // Sender (local) holds a shippable model built from the winning body → decideCompanion → ship.
+    await ctx.localBlob.put(
+      ctx.localPrincipal, modelKey(ctx),
+      Buffer.from(`${JSON.stringify(modelEnvelope(bodyHash(bodyLocalWin), GENERATOR_VERSION))}\n`, 'utf8'),
+      'application/json',
+    );
+    const spendBefore = await ctx.spendLedgerTotal();
+
+    const r1 = await runSync(ctx.syncDeps({ failCloudModelPut: true }));
+
+    // The Class-A commit landed durably despite the companion failure.
+    expect(r1.updatedCloud).toBeGreaterThanOrEqual(1);
+    expect((await cloudBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyLocalWin);
+    // Baseline advanced — the transfer is durable, so re-running must not redo it.
+    const m1 = await ctx.readManifest();
+    expect((m1.videos[ctx.videoId] as VideoBaseline).classA.mdHash).toBe(bodyHash(bodyLocalWin));
+    // The share is reported unready rather than left silently stale.
+    expect(r1.shareNeedsOwnerServe).toBe(1);
+    expect(r1.errors.some((e) => e.videoId === ctx.videoId)).toBe(true); // failure stays visible
+    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
+  });
+
   // ── H2 (round 4) — the B1 guard was over-broad on the LOCAL side. B1 exists because the Supabase
   //    backend cannot tell absent from unreadable; the local backend CAN (LocalFsBlobStore.get
   //    returns null ONLY on ENOENT and rethrows every other errno), so a local record advertising a
   //    summaryMd whose body reads back null PROVES the file is gone — a user who moved the .md by
   //    hand, or a generation that crashed between the index write and the blob write.
   //    Before the guard this healed for free (!lHas → copyToLocal → the dangling pointer is
   //    repaired, purely additive). The guard made it throw on EVERY run, forever, never advancing a
   //    baseline, with no exit but hand-editing playlist-index.json or paying to regenerate content
   //    sitting intact in the cloud. Fail-closed must be scoped to the backend that needs it.
   it('H2: a genuinely-absent local MD blob is hydrated from the cloud, not stranded (2 runs)', async () => {
     const ctx = await makeOwnerContext();
     const bodyCloud = '# CloudHasIt\n\nthe body the local record lost\n';
     // Local ADVERTISES summaryMd (+ a promoted artifact) but mdBody is omitted → the blob is
     // genuinely absent on a backend that proves absence.
     await seedLocalVideoFull(ctx, {
       docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
     });
     await seedCloudVideo(ctx, {
       mdBody: bodyCloud, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
     });
     const spendBefore = await ctx.spendLedgerTotal();
 
     const r1 = await runSync(ctx.syncDeps());
 
     expect(r1.errors).toEqual([]);                       // no permanent per-run failure
     expect(r1.updatedLocal).toBeGreaterThanOrEqual(1);   // additive hydration ran
     expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloud);
     const local = await localVideoRecord(ctx);
     expect(local?.summaryMd).toBe(key(ctx));
     expect(artifactsOf(local)?.summaryMd?.status).toBe('promoted');
     expect(await ctx.spendLedgerTotal()).toBe(spendBefore); // healed without any regeneration
 
     // Run 2 — the dangling pointer is repaired, so the sides simply agree.
     const r2 = await runSync(ctx.syncDeps());
     expect(r2.errors).toEqual([]);
     expect(r2.updatedLocal).toBe(0);
     expect(r2.skippedIdentical).toBeGreaterThanOrEqual(1);
     expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloud);
   });
 
   // ── H3 (round 4) — a local-only video wiped the cloud playlist's title on every sync.
   //    playlistMetaFor checked the local registry FIRST and returned { playlistUrl } with no title
   //    (LocalPlaylist never carried one), the cloud-registry branch that does carry a title being
   //    unreachable whenever the playlist also exists locally. ensureReceiverSlot then called
   //    setPlaylistMeta unconditionally, and the Supabase upsert writes
   //    `playlist_title: meta.playlistTitle ?? null` — an explicit NULL. Recurs on every sync that
   //    carries any local-only video (the ordinary case); recovery needs the backfill-titles route
   //    plus a YouTube API key.
   it('H3: an additive publish of a local-only video preserves the cloud playlist title (2 runs)', async () => {
     const ctx = await makeOwnerContext();
     await prepareSyncCtx(ctx);
     const title = 'Deep Learning Lectures';
     // Cloud playlist row carries a title (as lib/job-queue/producer.ts sets it at enqueue) and holds
     // NO videos; the local replica has a title-less index with one video → additive publish to cloud.
     const { data: pl, error } = await adminClient().from('playlists').insert({
       owner_id: ctx.userId,
       playlist_key: ctx.playlistKey,
       playlist_url: `https://www.youtube.com/playlist?list=${ctx.playlistKey}`,
       playlist_title: title,
     }).select('id').single();
     if (error) throw error;
     ctx.playlistId = (pl as { id: string }).id;
     await seedLocalVideoFull(ctx, { mdBody: '# LocalOnly\n\njust summarized locally\n' });
     expect(await cloudPlaylistTitle(ctx)).toBe(title); // fixture precondition
 
     const r1 = await runSync(ctx.syncDeps());
 
     expect(r1.created).toBeGreaterThanOrEqual(1);        // the additive publish ran
     expect(await cloudVideoRecord(ctx)).not.toBeNull();
     expect(await cloudPlaylistTitle(ctx)).toBe(title);   // title NOT cleared
 
     // Run 2 — ensureReceiverSlot's setPlaylistMeta fires on every run, so once is not enough.
     await runSync(ctx.syncDeps());
     expect(await cloudPlaylistTitle(ctx)).toBe(title);
   });
 
   // ── L-R5-2 (round 5) — H3 stopped a sync CLEARING the cloud title, but not OVERWRITING it.
   //    playlistMetaFor preferred `lp?.playlistTitle`, so a local playlist-index.json title — whatever
   //    was captured when that folder was last summarized — clobbered the cloud row's on every
   //    additive local→cloud create. Titles carry no LWW timestamp, so precedence is fixed: the cloud
diff --git a/tests/integration/helpers/cloud.ts b/tests/integration/helpers/cloud.ts
index 35cd437..bbf87f2 100644
--- a/tests/integration/helpers/cloud.ts
+++ b/tests/integration/helpers/cloud.ts
@@ -1,255 +1,278 @@
 // tests/integration/helpers/cloud.ts
 //
 // Shared integration harness for Stage 3 Cloud Sync (Tasks 3, 4, 12, 14). Reuses the existing
 // owner/session/seed helpers (clients.ts, seed.ts) — does not reinvent auth or seeding.
 //
 // Task 3/4 use: makeOwnerContext, seedVideo, ctx.rpc, ctx.readVideoData, ctx.persistSummary.
 // Task 12 (sync-run) adds the real bodies for: seedLocalPlaylist, ctx.syncDeps({failCloudPromote?}),
 // ctx.readManifest, plus the local-store handles (ctx.local, ctx.localBlob, ctx.localPrincipal).
 
 import { promises as fs } from 'fs';
 import os from 'os';
 import path from 'path';
 import { randomUUID } from 'crypto';
 import type { SupabaseClient } from '@supabase/supabase-js';
 import { newUser, signInAs } from './clients';
 import { seedPlaylist, seedPromotedVideo, seedSummaryBlob } from './seed';
 import type { Principal } from '@/lib/storage/principal';
 import { localPrincipal } from '@/lib/storage/principal';
 import type { MetadataStore } from '@/lib/storage/metadata-store';
 import type { BlobStore, StagedRef } from '@/lib/storage/blob-store';
 import { localMetadataStore } from '@/lib/storage/local/local-metadata-store';
 import { localBlobStore } from '@/lib/storage/local/local-blob-store';
 import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';
 import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
 import { ARTIFACTS_BUCKET } from '@/lib/supabase/storage-env';
 import { readManifest as readManifestFile, writeVideoBaseline } from '@/lib/cloud-sync/manifest';
 import type { SyncDeps } from '@/lib/cloud-sync/sync-run';
 import type { VideoBaseline } from '@/lib/cloud-sync/types';
 import type { Video } from '@/types';
 
 export interface SeedLocalPlaylistOpts {
   /** Two-sided: also seed a matching LOCAL video carrying this human note, so it publishes to cloud. */
   localNote?: { value: string; editedAt: string };
   /** Crash-safety: seed a LOCAL-ONLY video (no cloud video) so the sync PUBLISHES it to cloud —
    *  the direction whose durability gate is the Supabase staged→promote (faultable via failCloudPromote). */
   publishToCloud?: boolean;
 }
 
 export interface Ctx {
   readonly userId: string;
   /** RLS-scoped client (anon key + user JWT) — the ONLY client the code-under-test uses. */
   readonly userClient: SupabaseClient;
   /** { id: userId, indexKey: playlistKey } — indexKey is populated by seedVideo() once a
    *  playlist exists (mirrors annotations-rpc.test.ts:31). Empty indexKey before any seed. */
   principal: Principal;
 
   // ---- Task 12 sync-run fixture state (populated by seedLocalPlaylist) ----
   playlistId: string;          // cloud playlist UUID (empty until a cloud playlist is seeded)
   playlistKey: string;         // shared playlist_key (also the YouTube list-id in the url)
   videoId: string;             // the (short, local-index-valid) video id under test
   tempDataRoot: string;        // the ROOT dir passed as deps.dataRoots[0]
   playlistDataRoot: string;    // the per-playlist dir runSync resolves for this key
   local: MetadataStore;        // local metadata store singleton
   localBlob: BlobStore;        // local blob store singleton
   localPrincipal: Principal;   // localPrincipal(playlistDataRoot)
   cloudPrincipal: Principal;   // { id: userId, indexKey: playlistKey }
 
   rpc(name: string, args: Record<string, unknown>): Promise<unknown>;
   readVideoData(playlistId: string, videoId: string): Promise<any>;
   persistSummary(
     playlistId: string, videoId: string, video: Record<string, unknown>, status: string,
   ): Promise<void>;
   /** Build the SyncDeps for a runSync() call. failCloudPromote wraps the cloud blob store so its
-   *  promote() throws AFTER staging (crash-safety fault injection). Cloud stores use the USER
-   *  session client (RLS-scoped) — never service-role — the money/RLS invariant. */
-  syncDeps(opts?: { failCloudPromote?: boolean }): SyncDeps;
+   *  promote() throws AFTER staging (crash-safety fault injection). failCloudModelPut makes only the
+   *  companion `models/*` put throw, leaving the Class-A staged→promote path intact (M-R6-1). Cloud
+   *  stores use the USER session client (RLS-scoped) — never service-role — the money/RLS invariant. */
+  syncDeps(opts?: { failCloudPromote?: boolean; failCloudModelPut?: boolean }): SyncDeps;
   /** Read the sync manifest runSync wrote for this ctx's playlist. */
   readManifest(): Promise<{ version: 1; videos: Record<string, unknown> }>;
   /** Sum of reserved_cents + actual_cents across spend_ledger (money-safety assertions).
    *  spend_ledger is GLOBAL (one row per UTC day, NO owner_id) → whole-table total; money-safety
    *  tests assert via a before/after DELTA. Reads via the service-role admin client because
    *  spend_ledger grants NO client access. */
   spendLedgerTotal(): Promise<number>;
 }
 
 /** Creates an authenticated owner (RLS-scoped session client) — the shared entry point for
  *  every cloud-sync integration test. */
 export async function makeOwnerContext(): Promise<Ctx> {
   const u = await newUser();
   const { client: userClient, userId } = await signInAs(u.email, u.password);
 
   const ctx: Ctx = {
     userId,
     userClient,
     principal: { id: userId, indexKey: '' },
 
     // sync-run fixture state — placeholders until seedLocalPlaylist populates them
     playlistId: '',
     playlistKey: '',
     videoId: '',
     tempDataRoot: '',
     playlistDataRoot: '',
     local: localMetadataStore,
     localBlob: localBlobStore,
     localPrincipal: localPrincipal(''),
     cloudPrincipal: { id: userId, indexKey: '' },
 
     async rpc(name: string, args: Record<string, unknown>): Promise<unknown> {
       const { data, error } = await userClient.rpc(name, args);
       if (error) throw error;
       return data;
     },
 
     async readVideoData(playlistId: string, videoId: string): Promise<any> {
       const { data, error } = await userClient
         .from('videos')
         .select('data')
         .eq('playlist_id', playlistId)
         .eq('video_id', videoId)
         .single();
       if (error) throw error;
       return data!.data;
     },
 
     async persistSummary(
       playlistId: string, videoId: string, video: Record<string, unknown>, status: string,
     ): Promise<void> {
       const { error } = await userClient.rpc('persist_summary', {
         p_owner_id: userId,
         p_playlist_id: playlistId,
         p_video_id: videoId,
         p_video: video,
         p_artifact_status: status,
       });
       if (error) throw error;
     },
 
-    syncDeps(opts: { failCloudPromote?: boolean } = {}): SyncDeps {
+    syncDeps(opts: { failCloudPromote?: boolean; failCloudModelPut?: boolean } = {}): SyncDeps {
       const cloud = new SupabaseMetadataStore(userClient);
       let cloudBlob: BlobStore = new SupabaseBlobStore(userClient, ARTIFACTS_BUCKET);
       if (opts.failCloudPromote) cloudBlob = new FailPromoteBlobStore(cloudBlob);
+      if (opts.failCloudModelPut) cloudBlob = new FailModelPutBlobStore(cloudBlob);
       return {
         local: localMetadataStore,
         cloud,
         localBlob: localBlobStore,
         cloudBlob,
         dataRoots: [ctx.tempDataRoot],
         ownerId: userId, // MUST be auth.uid() — the RLS/storage-path owner segment
       };
     },
 
     async readManifest(): Promise<{ version: 1; videos: Record<string, unknown> }> {
       return readManifestFile(ctx.playlistDataRoot, ctx.playlistKey);
     },
 
     async spendLedgerTotal(): Promise<number> {
       const { adminClient } = await import('./clients');
       const { data, error } = await adminClient()
         .from('spend_ledger').select('reserved_cents,actual_cents');
       if (error) throw error;
       return (data ?? []).reduce(
         (sum, r) => sum + (r.reserved_cents ?? 0) + (r.actual_cents ?? 0), 0,
       );
     },
   };
   return ctx;
 }
 
 /** Wraps a BlobStore so promote() throws AFTER staging succeeded — the crash-safety fault:
  *  a partially-transferred blob whose promote never lands must NOT advance the manifest baseline. */
 class FailPromoteBlobStore implements BlobStore {
   constructor(private inner: BlobStore) {}
   /** Forward the wrapped backend's absence-proving capability — the sync path reads it to decide
    *  whether "no bytes" may be treated as a semantic fact (B1/H1/H2 guards). */
   get provesAbsence(): boolean | undefined { return this.inner.provesAbsence; }
   put(p: Principal, key: string, bytes: Buffer, ct: string) { return this.inner.put(p, key, bytes, ct); }
   get(p: Principal, key: string) { return this.inner.get(p, key); }
   exists(p: Principal, key: string) { return this.inner.exists(p, key); }
   delete(p: Principal, key: string) { return this.inner.delete(p, key); }
   putStaged(p: Principal, key: string, bytes: Buffer, ct: string) { return this.inner.putStaged(p, key, bytes, ct); }
   async promote(_ref: StagedRef): Promise<void> { throw new Error('injected cloud promote failure'); }
   deletePrefix(p: Principal, prefix: string) { return this.inner.deletePrefix(p, prefix); }
   list(p: Principal, prefix: string) { return this.inner.list(p, prefix); }
 }
 
+/** M-R6-1 — wraps a BlobStore so ONLY the companion model put (`models/*.json`) throws. The Class-A
+ *  staged→promote path is untouched, so the transfer still commits durably and the fault isolates
+ *  exactly the companion ship write: the run must report the share as unready rather than leave the
+ *  receiver's pre-sync model advertised as fresh with no re-run that ever retries the ship. */
+class FailModelPutBlobStore implements BlobStore {
+  constructor(private inner: BlobStore) {}
+  /** Delegated — the sync path reads this to decide whether "no bytes" is a semantic fact. */
+  get provesAbsence(): boolean | undefined { return this.inner.provesAbsence; }
+  put(p: Principal, key: string, bytes: Buffer, ct: string) {
+    if (key.startsWith('models/')) throw new Error('injected companion model put failure');
+    return this.inner.put(p, key, bytes, ct);
+  }
+  get(p: Principal, key: string) { return this.inner.get(p, key); }
+  exists(p: Principal, key: string) { return this.inner.exists(p, key); }
+  delete(p: Principal, key: string) { return this.inner.delete(p, key); }
+  putStaged(p: Principal, key: string, bytes: Buffer, ct: string) { return this.inner.putStaged(p, key, bytes, ct); }
+  promote(ref: StagedRef) { return this.inner.promote(ref); }
+  deletePrefix(p: Principal, prefix: string) { return this.inner.deletePrefix(p, prefix); }
+  list(p: Principal, prefix: string) { return this.inner.list(p, prefix); }
+}
+
 /** Seeds the fixture for a sync-run test and populates ctx's sync state. Default: a CLOUD playlist
  *  with one promoted-summary video, local replica empty (hydrate). `localNote` additionally seeds a
  *  matching LOCAL video with that note (two-sided publish). `publishToCloud` seeds a LOCAL-ONLY video
  *  (no cloud video) so the sync publishes local→cloud (crash-safety direction). */
 export async function seedLocalPlaylist(
   ctx: Ctx, opts: SeedLocalPlaylistOpts = {},
 ): Promise<{ playlistId?: string; playlistKey: string; videoId: string }> {
   const { adminClient } = await import('./clients');
   const svc = adminClient();
 
   const key = `k-${randomUUID()}`;
   const url = `https://www.youtube.com/playlist?list=${key}`;
   // VIDEO_ID_RE caps local video ids at 20 chars of [A-Za-z0-9_-]; a full uuid is too long.
   const videoId = `v${randomUUID().replace(/-/g, '').slice(0, 12)}`;
   const base = videoId;
   const md = `# Summary ${videoId}\n\nBody paragraph for the sync fixture.\n`;
 
   ctx.playlistKey = key;
   ctx.videoId = videoId;
   ctx.tempDataRoot = await fs.mkdtemp(path.join(os.homedir(), '.cs-syncrun-'));
   ctx.playlistDataRoot = path.join(ctx.tempDataRoot, key);
   ctx.localPrincipal = localPrincipal(ctx.playlistDataRoot);
   ctx.cloudPrincipal = { id: ctx.userId, indexKey: key };
 
   if (opts.publishToCloud) {
     // Local-only video → sync publishes it to cloud. No cloud playlist/video seeded;
     // ensureReceiverSlot creates the cloud playlist row during the run.
     await seedLocalVideo(ctx, { videoId, base, md });
     return { playlistKey: key, videoId };
   }
 
   // Cloud playlist + one promoted-summary video (hydrate source / two-sided cloud side).
   const { data: pl, error } = await svc
     .from('playlists')
     .insert({ owner_id: ctx.userId, playlist_key: key, playlist_url: url })
     .select('id')
     .single();
   if (error) throw error;
   ctx.playlistId = pl!.id as string;
 
   await seedPromotedVideo(svc, { ownerId: ctx.userId, playlistId: ctx.playlistId, videoId, base });
   await seedSummaryBlob(svc, ctx.userId, key, base, md);
 
   if (opts.localNote) {
     await seedLocalVideo(ctx, { videoId, base, md, note: opts.localNote });
   }
 
   return { playlistId: ctx.playlistId, playlistKey: key, videoId };
 }
 
 /** Seeds a LOCAL playlist dir under tempDataRoot with one video (+ optional note) and its MD blob,
  *  so discoverLocalPlaylists finds it and Class-A sees an identical MD body (skip, no transfer). */
 async function seedLocalVideo(
   ctx: Ctx,
   args: { videoId: string; base: string; md: string; note?: { value: string; editedAt: string } },
 ): Promise<void> {
   const { videoId, base, md, note } = args;
   const lp = ctx.localPrincipal;
   await fs.mkdir(ctx.playlistDataRoot, { recursive: true });
   await ctx.local.setPlaylistMeta(lp, { playlistUrl: `https://www.youtube.com/playlist?list=${ctx.playlistKey}` });
   await ctx.local.claimVideoSlot(lp, videoId);
 
   const video = {
     id: videoId,
     title: videoId,
     youtubeUrl: `https://youtu.be/${videoId}`,
     language: 'en',
     durationSeconds: 600,
     archived: false,
     ratings: { usefulness: 4, depth: 4, originality: 4, recency: 4, completeness: 4 },
     overallScore: 4,
     summaryMd: `${base}.md`,
     processedAt: '2026-01-01T00:00:00.000Z',
     docVersion: { major: 1, minor: 0 },
     ...(note
       ? { personalNote: note.value, annotationsEditedAt: { personalNote: note.editedAt } }
       : {}),
   } as unknown as Video;
 
   await ctx.local.upsertVideo(lp, video);
diff --git a/tests/lib/cloud-sync/companion.test.ts b/tests/lib/cloud-sync/companion.test.ts
index fc8f9e2..4d2bf70 100644
--- a/tests/lib/cloud-sync/companion.test.ts
+++ b/tests/lib/cloud-sync/companion.test.ts
@@ -1,86 +1,125 @@
 import { decideCompanion, type ModelRead } from '@/lib/cloud-sync/companion';
+import { GENERATOR_VERSION } from '@/lib/html-doc/constants';
 import type { ModelEnvelope } from '@/lib/html-doc/model-store';
 
-const env = (sourceMdHash?: string): ModelEnvelope => ({
+const env = (sourceMdHash?: string, generatorVersion?: string): ModelEnvelope => ({
   sourceMd: 'x', generatedAt: '2026', sourceSections: ['A'],
   model: { sections: [{ lead: 'l', bullets: [{ label: 'a', text: 'b' }, { label: 'c', text: 'd' }, { label: 'e', text: 'f' }] }] },
   ...(sourceMdHash ? { sourceMdHash } : {}),
+  ...(generatorVersion ? { generatorVersion } : {}),
 });
-const envelope = (h?: string): ModelRead => ({ kind: 'envelope', envelope: env(h) });
+const envelope = (h?: string, gv?: string): ModelRead =>
+  ({ kind: 'envelope', envelope: env(h, gv) });
+/** An envelope the serve path's isFresh() would accept on generatorVersion. */
+const current = (h?: string): ModelRead => envelope(h, GENERATOR_VERSION);
+/** An envelope built by an older checkout — isFresh() rejects it. */
+const stale = (h?: string): ModelRead => envelope(h, 'magazine-skim v1');
 const decide = (senderModel: ModelRead, receiverModel: ModelRead) =>
   decideCompanion({ winnerMdHash: 'h1', senderModel, receiverModel });
 
 const DELETE = { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
 /** Keep the receiver's blob. `flag` is the SEPARATE report-only axis (§10 row 7). */
 const KEEP = (flag: boolean) => ({ kind: 'noop', shareNeedsOwnerServe: flag });
 
-// ── Rule 1 — the sender has a model built from the WINNING md: ship it, whatever the receiver holds.
+// ── Rule 1 — the sender has a model built from the WINNING md and the receiver holds nothing built
+//    from that same body: ship it. (When BOTH sides match the winner hash, generatorVersion decides —
+//    see the L-R6-1 sub-matrix below.)
 describe('sender ships', () => {
   it.each<[string, ModelRead]>([
     ['receiver absent', { kind: 'none' }],
     ['receiver unreadable', { kind: 'unknown' }],
     ['receiver stale', envelope('h2')],
-    ['receiver already current', envelope('h1')],
+    ['receiver legacy (no sourceMdHash)', envelope(undefined)],
   ])('ships a matching sender envelope (%s)', (_label, receiver) => {
     expect(decide(envelope('h1'), receiver)).toMatchObject({ kind: 'ship' });
   });
 });
 
+// ── L-R6-1 (round 6) — BOTH sides hold a model built from the WINNING body. Shipping unconditionally
+//    could DOWNGRADE the receiver: a sender on an older checkout overwrites a model isFresh() accepts
+//    with one it rejects, flipping the share from rendering to 503 and making recovery a PAID owner
+//    re-serve. When both match the winner hash the bodies are identical, so the only thing left to
+//    compare is generatorVersion — prefer the fresher, and never write when the receiver is already
+//    current.
+describe('both sides match the winner hash — generatorVersion breaks the tie', () => {
+  it('KEEPS a receiver that is already current, even when the sender is older (no downgrade)', () => {
+    expect(decide(stale('h1'), current('h1'))).toEqual(KEEP(false));
+  });
+  it('SHIPS when only the sender is current (a real upgrade)', () => {
+    expect(decide(current('h1'), stale('h1'))).toMatchObject({ kind: 'ship' });
+  });
+  it('KEEPS when NEITHER is current (a pointless write — both need a re-serve anyway)', () => {
+    expect(decide(stale('h1'), stale('h1'))).toEqual(KEEP(false));
+  });
+  it('KEEPS when BOTH are current (identical body, identical generator — nothing to write)', () => {
+    expect(decide(current('h1'), current('h1'))).toEqual(KEEP(false));
+  });
+  it('KEEPS when both are legacy envelopes with no generatorVersion at all', () => {
+    expect(decide(envelope('h1'), envelope('h1'))).toEqual(KEEP(false));
+  });
+});
+
 // ── H-R5-1 (round 5) — rules 2/3. The sender read answers "can a replacement be shipped?"; it does
 //    NOT answer "is the receiver's model stale?". Only the RECEIVER's own sourceMdHash answers that,
 //    and it answers it exactly. So every non-ship sender state funnels into the same receiver-keyed
 //    decision — `unknown` is no longer a decision of its own, and `none` no longer deletes blind.
 describe('receiver-keyed decision (every non-shipping sender state)', () => {
   const nonShippingSenders: [string, ModelRead][] = [
     ['sender provably has none', { kind: 'none' }],
     ['sender read is unprovable', { kind: 'unknown' }],
     ['sender envelope does not match the winner', envelope('h2')],
     ['sender envelope is legacy (no sourceMdHash)', envelope(undefined)],
   ];
 
   describe.each(nonShippingSenders)('%s', (_label, sender) => {
     it('DELETES a receiver model whose sourceMdHash provably differs from the winner', () => {
       expect(decide(sender, envelope('h2'))).toEqual(DELETE);
     });
     it('KEEPS a receiver model whose sourceMdHash matches the winner (still valid — paid artifact)', () => {
       expect(decide(sender, envelope('h1'))).toEqual(KEEP(false));
     });
     it('touches nothing when the receiver PROVABLY has no model, but still counts the unready share', () => {
       // §10 row 7 — nothing to delete, yet the share cannot render until the owner re-serves. The
       // blob action and the report flag are separate axes.
       expect(decide(sender, { kind: 'none' })).toEqual(KEEP(true));
     });
     it('KEEPS but still counts when the receiver read itself could not prove absence', () => {
       // Unprovable, so the DELETE must not fire — but the flag costs nothing and under-reporting
       // is what strands an anon visitor on a not-ready share.
       expect(decide(sender, { kind: 'unknown' })).toEqual(KEEP(true));
     });
     it('KEEPS but still counts a legacy receiver envelope with no sourceMdHash', () => {
       expect(decide(sender, envelope(undefined))).toEqual(KEEP(true));
     });
   });
 });
 
 // ── The report flag on the SHIP branch: the receiver ends up holding a model built from the
 //    winning MD, so the share renders and nothing is owed.
 it('never flags owner-serve when a model was shipped', () => {
-  for (const r of [{ kind: 'none' }, { kind: 'unknown' }, envelope('h2'), envelope('h1')] as ModelRead[]) {
-    expect(decide(envelope('h1'), r)).not.toMatchObject({ shareNeedsOwnerServe: true });
+  for (const r of [{ kind: 'none' }, { kind: 'unknown' }, envelope('h2'), stale('h1')] as ModelRead[]) {
+    expect(decide(current('h1'), r)).not.toMatchObject({ shareNeedsOwnerServe: true });
   }
 });
 
 // ── The money invariant, stated once as its own assertion: the ONLY input that deletes is a receiver
 //    envelope carrying a sourceMdHash that differs from the winner's. Everything else keeps.
 it('deletes only on a proven receiver-side mismatch', () => {
-  const senders: ModelRead[] = [{ kind: 'none' }, { kind: 'unknown' }, envelope('h2'), envelope(undefined), envelope('h1')];
-  const receivers: ModelRead[] = [{ kind: 'none' }, { kind: 'unknown' }, envelope('h1'), envelope(undefined), envelope('h2')];
+  const senders: ModelRead[] = [
+    { kind: 'none' }, { kind: 'unknown' }, envelope('h2'), envelope(undefined),
+    envelope('h1'), current('h1'), stale('h1'),
+  ];
+  const receivers: ModelRead[] = [
+    { kind: 'none' }, { kind: 'unknown' }, envelope(undefined), envelope('h2'),
+    envelope('h1'), current('h1'), stale('h1'),
+  ];
   for (const s of senders) {
     for (const r of receivers) {
       const deleted = decideCompanion({ winnerMdHash: 'h1', senderModel: s, receiverModel: r }).kind === 'deleteReceiverModel';
       const senderShips = s.kind === 'envelope' && s.envelope.sourceMdHash === 'h1';
       const receiverProvablyStale = r.kind === 'envelope' && r.envelope.sourceMdHash !== undefined
         && r.envelope.sourceMdHash !== 'h1';
       expect(deleted).toBe(!senderShips && receiverProvablyStale);
     }
   }
 });

codex
The prior reviews line up with the two edits in `15c32bd`: one tie-break defect in `decideCompanion`, one sticky failure mode in `companionTransfer`. I’m now checking the current implementation with line numbers and tracing the caller contract for `report.errors` and baseline writes.
exec
/bin/bash -lc "nl -ba lib/cloud-sync/companion.ts | sed -n '1,180p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	import { GENERATOR_VERSION } from '@/lib/html-doc/constants';
     2	import type { ModelEnvelope } from '@/lib/html-doc/model-store';
     3	
     4	/** H1 (round 4) — the result of reading ONE side's model, as a TRI-state.
     5	 *  `readModelEnvelope` collapses three different situations into one null: the envelope is absent,
     6	 *  it is corrupt/schema-invalid, or its bytes could not be READ. The first two mean that side has
     7	 *  nothing usable; the third means we simply do not know, and acting on it destroys a paid artifact.
     8	 *  Which of those a null is depends on the backend — see BlobStore.provesAbsence — so the caller
     9	 *  resolves it and hands the answer here.
    10	 *
    11	 *  H-R5-1 (round 5) — this is now read for BOTH sides, hence the neutral name. */
    12	export type ModelRead =
    13	  | { kind: 'envelope'; envelope: ModelEnvelope }
    14	  | { kind: 'none' }      // that side PROVABLY has no usable model
    15	  | { kind: 'unknown' };  // the read failed in a way that cannot prove absence
    16	
    17	/** @deprecated round-4 name, kept so the tri-state reads naturally at the sender call site. */
    18	export type SenderModelRead = ModelRead;
    19	
    20	/** H-R5-1 (round 5) — `shareNeedsOwnerServe` is now carried on `noop` too, because it is a SEPARATE
    21	 *  axis from the blob action and conflating the two is what produced this finding. The action answers
    22	 *  "what do we do to the receiver's blob?"; the flag is a report-only count of shares that cannot
    23	 *  render until the owner re-serves. §10 row 7 (neither side holds a model) is exactly the case where
    24	 *  there is nothing to delete and yet the share IS unready — noop + true. */
    25	export type CompanionAction =
    26	  | { kind: 'ship'; envelope: ModelEnvelope }
    27	  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true }
    28	  | { kind: 'noop'; shareNeedsOwnerServe: boolean };
    29	
    30	/** Ship the sender's model iff it was generated from the winning MD (§4.2); otherwise decide the
    31	 *  receiver's fate from the RECEIVER's own envelope.
    32	 *
    33	 *  H1 (round 4) — `unknown` must not delete. Deleting the receiver's model costs a paid Gemini
    34	 *  magazine transform to recover (runHtmlDoc → generateMagazineModel locally, or
    35	 *  resolveMagazineModel → reserve_serve_model → spend_ledger on the cloud), and the delete is
    36	 *  silent and sticky: it does not throw, so the caller advances the manifest baseline, and the next
    37	 *  run's Class-A reconcile returns 'skip' and never revisits the companion step.
    38	 *
    39	 *  H-R5-1 (round 5) — round 4 made the SENDER read honest but left the whole decision keyed to it,
    40	 *  which was wrong in both directions:
    41	 *   (a) `unknown` → noop KEPT a provably-stale receiver model. The claimed safety net does not
    42	 *       exist: the serve path's drift guard (lib/html-doc/read-model.ts) compares section TITLES and
    43	 *       generatorVersion, never sourceMdHash, so a prose-only MD change — precisely the
    44	 *       recency-tiebreak case — is served as fresh forever (dig-deeper merges the cached envelope
    45	 *       without regenerating). And `unknown` is the COMMON outcome: a cloud video that was never
    46	 *       HTML-served has no model blob, and the Supabase backend cannot prove that 404.
    47	 *   (b) `none` → delete DESTROYED receiver models that were still valid, since the receiver was
    48	 *       never consulted.
    49	 *  The backend ambiguity was only ever about the SENDER. The receiver's staleness is provable
    50	 *  independently: we hold winnerMdHash, so a receiver sourceMdHash that is present and DIFFERENT is
    51	 *  definitively stale — its backing body no longer exists — with no ambiguity involved. So the
    52	 *  sender read now decides only whether a REPLACEMENT can be shipped, and everything else is keyed
    53	 *  to the receiver. Deleting a provably-stale model is not a money loss; deleting a matching one is.
    54	 *
    55	 *  L-R6-1 (round 6) — the ship branch could DOWNGRADE. When BOTH envelopes match winnerMdHash the
    56	 *  bodies are identical, so the only remaining difference is generatorVersion — and shipping the
    57	 *  sender's blind overwrites a receiver model isFresh() accepts (lib/html-doc/read-model.ts) with one
    58	 *  it rejects. The share flips from rendering to a 503 (app/s/[token]/route.ts) and the only recovery
    59	 *  is an owner re-serve, which reserves and charges (lib/html-doc/serve-doc.ts) — the same
    60	 *  user-re-spend class as H1 and H-R5-1, so it is guarded rather than tolerated.
    61	 *  Reachability is not exotic: it needs GENERATOR_VERSION skew between the local checkout and the
    62	 *  deployed cloud image (routine whenever the deploy lags the checkout) AND the loser already holding
    63	 *  a model built from the winner's exact body — which is the normal state after any prior sync, since
    64	 *  reconcile-class-a.ts falls through to a transfer on equal mdHash when currency or format disagree.
    65	 *  So when both match, prefer the FRESHER by generatorVersion, and never write when the receiver is
    66	 *  already current. (The report flag stays false on every both-match path: a version-skewed receiver
    67	 *  was already not-fresh BEFORE this run, which is L-R6-2, deliberately out of scope here.)
    68	 */
    69	export function decideCompanion(args: {
    70	  winnerMdHash: string;
    71	  senderModel: ModelRead;
    72	  receiverModel: ModelRead;
    73	}): CompanionAction {
    74	  const { winnerMdHash, senderModel, receiverModel } = args;
    75	
    76	  const senderMatch = senderModel.kind === 'envelope'
    77	    && senderModel.envelope.sourceMdHash === winnerMdHash ? senderModel.envelope : null;
    78	  const receiverMatch = receiverModel.kind === 'envelope'
    79	    && receiverModel.envelope.sourceMdHash === winnerMdHash ? receiverModel.envelope : null;
    80	
    81	  // 1. BOTH sides hold a model built from the winning MD (L-R6-1). Same body, so generatorVersion is
    82	  //    the whole difference: ship ONLY when it is a genuine upgrade, never a downgrade, and never a
    83	  //    write that changes nothing.
    84	  if (senderMatch && receiverMatch) {
    85	    if (receiverMatch.generatorVersion === GENERATOR_VERSION) {
    86	      return { kind: 'noop', shareNeedsOwnerServe: false }; // receiver already fresh — do not write
    87	    }
    88	    if (senderMatch.generatorVersion === GENERATOR_VERSION) {
    89	      return { kind: 'ship', envelope: senderMatch }; // a real upgrade
    90	    }
    91	    return { kind: 'noop', shareNeedsOwnerServe: false }; // neither is current — both need a re-serve
    92	  }
    93	
    94	  // 2. Only the sender holds a model built from the winning MD → ship it (it supersedes whatever the
    95	  //    receiver has, so the receiver's own state does not matter here).
    96	  if (senderMatch) return { kind: 'ship', envelope: senderMatch };
    97	
    98	  // 3. Nothing shippable, but the receiver already holds a model built from the WINNING MD — it is
    99	  //    still valid. Do not destroy a paid artifact, and the share renders, so report nothing.
   100	  if (receiverMatch) return { kind: 'noop', shareNeedsOwnerServe: false };
   101	
   102	  // 4. The receiver's model is not known-good. The two axes now diverge, and DELIBERATELY:
   103	  //
   104	  //  - DELETE the blob only on PROOF. A receiver envelope whose sourceMdHash is present and differs
   105	  //    is definitively stale — its backing body no longer exists — and needs no sender read to
   106	  //    establish. Everything else is unprovable: `none`/`unknown` say nothing about a model we never
   107	  //    read, and a legacy pre-1F-a envelope predates sourceMdHash entirely (the field is .optional()
   108	  //    in model-store.ts), so it cannot be checked. Fail-safe-for-money: KEEP those. A possibly-stale
   109	  //    cache is recoverable — any regeneration overwrites it, and the existing sourceSections /
   110	  //    generatorVersion drift guard still catches the common legacy drift — but a deleted paid
   111	  //    artifact costs a Gemini transform to rebuild.
   112	  //
   113	  //  - REPORT on doubt. shareNeedsOwnerServe is a report-only count (§10 row 7): "these shares may
   114	  //    not render until you re-serve." It spends nothing and destroys nothing, so the harmful
   115	  //    direction is UNDER-reporting — an anon visitor silently hitting a not-ready share. Note the
   116	  //    receiver of a copyToCloud is always the Supabase store, which can never return `none`, so
   117	  //    keying the flag to proof would make §10 row 7 unreportable in the direction it describes.
   118	  const provablyStale = receiverModel.kind === 'envelope'
   119	    && receiverModel.envelope.sourceMdHash !== undefined;
   120	  if (provablyStale) return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
   121	  return { kind: 'noop', shareNeedsOwnerServe: true };
   122	}

exec
/bin/bash -lc "nl -ba lib/cloud-sync/sync-run.ts | sed -n '360,700p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
   360	    // dig-deeper markdown file (lib/dig/generate.ts, written by lib/dig/dig-section.ts). Nulling it
   361	    // orphans that file and darkens the dig-state route, VideoMenu, build-doc-html and pdf-path;
   362	    // recovery costs fresh Gemini spend for content already paid for (and dig is out of scope for
   363	    // M2a). digDeeperHtml re-renders for free FROM the preserved digDeeperMd.
   364	    // The round-1 premise "matches sanitizeAdditiveVideo, which already nulls these" was the flaw:
   365	    // sanitizeAdditiveVideo shapes a record for a receiver with NO existing row (nothing to destroy),
   366	    // whereas transferClassA PATCHES a row that already holds its own state.
   367	    summaryHtml: null,
   368	    digDeeperHtml: null,
   369	    // Deep-merged (cloud merge_video_data / local index write). No Class-B key here → no spurious
   370	    // annotationsEditedAt stamp (F2). Never advertise promoted before the blob is durable (above).
   371	    artifacts: { summaryMd: { key, status: 'promoted' } },
   372	  };
   373	  await loser.store.updateVideoFields(loser.p, videoId, completeTuple as Partial<Video>);
   374	
   375	  return { mdHash: h, verified: true };
   376	}
   377	
   378	/** Behavior #5 — ship the winner's summary MODEL to the loser iff it was generated from the winning
   379	 *  MD; otherwise delete the loser's model (best-effort, OUTSIDE the atomic commit) and flag that the
   380	 *  owner must re-serve — but ONLY when that model proves itself stale (H-R5-1).
   381	 *
   382	 *  Every companion write is BEST-EFFORT and never throws (M-R6-1): the caller must still advance the
   383	 *  baseline, because transferClassA has already committed the winner body durably. A returned `error`
   384	 *  is surfaced in report.errors by the caller without aborting the per-video flow. */
   385	async function companionTransfer(
   386	  winner: Side, loser: Side, winnerMdHash: string, winnerVideo: Video,
   387	): Promise<{ shareNeedsOwnerServe: boolean; error?: string }> {
   388	  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
   389	  const base = winnerVideo.summaryMd.replace(/\.md$/, '');
   390	  // H-R5-1 (round 5) — read BOTH sides. The sender read says whether a replacement can be shipped;
   391	  // only the RECEIVER's own envelope can prove the receiver's model stale (see decideCompanion).
   392	  const [senderModel, receiverModel] = await Promise.all([
   393	    readModelSide(winner, base), readModelSide(loser, base),
   394	  ]);
   395	  const decision = decideCompanion({ winnerMdHash, senderModel, receiverModel });
   396	  if (decision.kind === 'ship') {
   397	    // M-R6-1 — a throw here would be STICKY, not merely noisy: the Class-A body already landed, so the
   398	    // next run's reconcileClassA returns 'skip' and the companion step (gated on !== 'skip') never
   399	    // runs again. The receiver would keep a model built from the PRE-SYNC body — and if its section
   400	    // titles and generatorVersion still match, the serve path's drift guard cannot see it, so it is
   401	    // served as fresh forever (the prose-only-change case behind H-R5-1). Swallow the failure the way
   402	    // the delete below already does and report the share as unready, so the staleness is at least
   403	    // visible; the error is returned so it still surfaces in report.errors.
   404	    try {
   405	      await writeModelEnvelope(loser.p, base, decision.envelope, loser.blob);
   406	      return { shareNeedsOwnerServe: false };
   407	    } catch (e: any) {
   408	      return { shareNeedsOwnerServe: true, error: `companion model ship failed: ${e?.message ?? String(e)}` };
   409	    }
   410	  }
   411	  // H1 (round 4) / H-R5-1 (round 5) — nothing shippable and the receiver's model is not PROVABLY
   412	  // stale: leave the blob alone. The report flag is decided separately (§10 row 7 counts a share
   413	  // with no model even though there is nothing to delete).
   414	  if (decision.kind === 'noop') return { shareNeedsOwnerServe: decision.shareNeedsOwnerServe };
   415	  // deleteReceiverModel — best-effort; a missing model blob is not an error.
   416	  try { await loser.blob.delete(loser.p, `models/${base}.json`); } catch { /* best-effort */ }
   417	  return { shareNeedsOwnerServe: true };
   418	}
   419	
   420	/** H1 (round 4) — resolve `readModelEnvelope`'s single null into the tri-state decideCompanion needs.
   421	 *  A null means absent, corrupt, or unreadable; only a backend that can prove absence
   422	 *  (BlobStore.provesAbsence — the local FS store, whose get is ENOENT-only) lets us tell those
   423	 *  apart. On such a backend a null is definitive either way: the model is genuinely missing, or its
   424	 *  bytes were read and rejected — both mean that side has nothing usable. On the Supabase backend
   425	 *  the same null may be a transient 5xx / timeout / RLS denial, so it proves nothing and must not
   426	 *  drive a destructive delete. A backend that does not declare the capability is treated as unable
   427	 *  to prove absence.
   428	 *  H-R5-1 (round 5) — used for the RECEIVER too (hence the neutral name): a receiver `unknown` must
   429	 *  not be read as "no model", and a receiver `none` leaves nothing to delete. */
   430	async function readModelSide(side: Side, base: string): Promise<ModelRead> {
   431	  const envelope = await readModelEnvelope(side.p, base, side.blob);
   432	  if (envelope) return { kind: 'envelope', envelope };
   433	  return side.blob.provesAbsence ? { kind: 'none' } : { kind: 'unknown' };
   434	}
   435	
   436	/** The manifest baseline written AFTER a verified reconcile — the AGREED post-reconcile state, not a
   437	 *  winner. Class A = the winning signals + verified mdHash (or the shared state on skip). Class B —
   438	 *  per field: advance to the resolved (value, editedAt) EXCEPT a no-write conflict
   439	 *  (winner==='equal' && conflict), which carries the PREVIOUS baseline unchanged (round-3 H2:
   440	 *  recording the winner there would be a false agreement → next-run silent overwrite). */
   441	function buildClassBBaseline(
   442	  merges: Record<HumanField, FieldMerge>, previousBaseline: VideoBaseline | undefined,
   443	): VideoBaseline['classB'] {
   444	  const classB = {} as VideoBaseline['classB'];
   445	  for (const f of FIELDS) {
   446	    const m = merges[f];
   447	    if (m.winner === 'equal' && m.conflict) {
   448	      classB[f] = previousBaseline?.classB?.[f] ?? { value: undefined, editedAt: undefined };
   449	    } else {
   450	      classB[f] = { value: m.value, editedAt: m.editedAt };
   451	    }
   452	  }
   453	  return classB;
   454	}
   455	
   456	function buildBaseline(
   457	  winnerSignals: ClassASignals, winnerMdHash: string | null,
   458	  merges: Record<HumanField, FieldMerge>, previousBaseline: VideoBaseline | undefined,
   459	): VideoBaseline {
   460	  return {
   461	    classA: {
   462	      docVersionMajor: winnerSignals.docVersionMajor,
   463	      mdGeneratedAt: winnerSignals.mdGeneratedAt,
   464	      mdCorrectionsHash: winnerSignals.mdCorrectionsHash,
   465	      mdHash: winnerMdHash,
   466	    },
   467	    classB: buildClassBBaseline(merges, previousBaseline),
   468	  };
   469	}
   470	
   471	/** WB-B1 — the manifest baseline for a corrections NO-WRITE conflict (§5.5). No Class-A copy ran, so
   472	 *  Class A must NOT advance to a winner (that would record a false agreement → next-run silent
   473	 *  overwrite around an unresolved conflict). Preserve the PREVIOUS Class-A baseline so the next run
   474	 *  re-evaluates the currency-based transfer from the live signals. On a first sync (no previous
   475	 *  baseline) record an HONEST unresolved placeholder (mdHash null → "no agreed MD"); Class-A baseline
   476	 *  is write-only (never read by reconcileClassA), so next run re-derives from the actual bodies
   477	 *  regardless. Class B carries the preserved conflict (buildClassBBaseline). */
   478	function buildCorrectionsUnresolvedBaseline(
   479	  merges: Record<HumanField, FieldMerge>, previousBaseline: VideoBaseline | undefined,
   480	): VideoBaseline {
   481	  return {
   482	    classA: previousBaseline?.classA
   483	      ?? { docVersionMajor: 0, mdGeneratedAt: null, mdCorrectionsHash: null, mdHash: null },
   484	    classB: buildClassBBaseline(merges, previousBaseline),
   485	  };
   486	}
   487	
   488	export async function runSync(
   489	  deps: SyncDeps, opts: { playlistKey?: string } = {},
   490	): Promise<SyncReport> {
   491	  resetConflictDedup();
   492	  const report: SyncReport = {
   493	    created: 0, updatedLocal: 0, updatedCloud: 0, skippedIdentical: 0,
   494	    mergedFields: 0, conflictsLogged: 0, removed: 0,
   495	    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
   496	  };
   497	
   498	  const localPlaylists = await discoverLocalPlaylists(deps.dataRoots);
   499	  const cloudSummaries = await deps.cloud.listPlaylists(deps.ownerId);
   500	  const cloudKeys = cloudSummaries.map((p) => p.playlistKey);
   501	  let keys = unionPlaylistKeys(localPlaylists, cloudKeys);
   502	  if (opts.playlistKey) keys = keys.filter((k) => k === opts.playlistKey);
   503	
   504	  for (const key of keys) {
   505	    const dataRoot = localPlaylists.find((l) => l.playlistKey === key)?.dataRoot
   506	      ?? hydrationRoot(deps.dataRoots, key);
   507	    await ensureHydrationRoot(dataRoot); // mkdir -p BEFORE any local read/write (fresh-device hydrate)
   508	
   509	    const localP = localPrincipal(dataRoot);
   510	    const cloudP: Principal = { id: deps.ownerId, indexKey: key }; // F1 — auth.uid(), NOT 'cloud'
   511	    const localSide: Side = { store: deps.local, p: localP, blob: deps.localBlob };
   512	    const cloudSide: Side = { store: deps.cloud, p: cloudP, blob: deps.cloudBlob };
   513	    const playlistMeta = playlistMetaFor(key, localPlaylists, cloudSummaries);
   514	    const manifest = await readManifest(dataRoot, key);
   515	
   516	    for (const id of await enumerateVideoIds(deps.local, deps.cloud, localP, cloudP)) {
   517	      try {
   518	        const lv = await readVideo(deps.local, localP, id);
   519	        const cv = await readVideo(deps.cloud, cloudP, id);
   520	        const base = manifest.videos[id];
   521	
   522	        // ── Presence / deletes (§5.6, Behaviors #3/#7/#8) — resolve one-sided videos and CONTINUE
   523	        //    before any two-sided reconcile (deriveHumanSnapshot(null) would NPE).
   524	        if (!lv || !cv) {
   525	          const present = (lv ?? cv)!;
   526	          const presentIsLocal = lv != null;
   527	          if (base) {
   528	            report.removed += 1; // in baseline + absent other side → deleted there; no propagation (M2b)
   529	          } else {
   530	            const from: Side = presentIsLocal ? localSide : cloudSide;
   531	            const to: Side = presentIsLocal ? cloudSide : localSide;
   532	            const body = await readMdBody(from.blob, from.p, present);
   533	            await copyAdditiveVideo(to.store, to.p, to.blob, playlistMeta, present, body);
   534	            report.created += 1; // reached only after the receiver row is confirmed
   535	            await writeVideoBaseline(dataRoot, key, id, baselineFromOneSided(
   536	              deriveClassASignals(present, body), body ? mdHash(body) : null,
   537	              deriveHumanSnapshot(present),
   538	            ));
   539	          }
   540	          continue;
   541	        }
   542	
   543	        // ── Both present — reconcile. Class B FIRST (produces the reconciled corrections).
   544	        const localSnap = deriveHumanSnapshot(lv);
   545	        const cloudSnap = deriveHumanSnapshot(cv);
   546	        const merges = reconcileHuman(localSnap, cloudSnap, base?.classB ?? EMPTY_CLASSB);
   547	        const applied = await applyClassBWinners({
   548	          deps, localP, cloudP, videoId: id, merges, localSnap, cloudSnap, dataRoot, key,
   549	        });
   550	        report.mergedFields += applied.merged;
   551	        report.conflictsLogged += applied.conflicts;
   552	        const reconciledCorrectionsHash = mdHash(String(merges.corrections.value ?? ''));
   553	
   554	        // ── WB-B1 — corrections is an UNRESOLVED no-write conflict (both sides changed, ≥1 backfilled →
   555	        //    Class B logs+skips, §5.5). Its value is NOT a settled winner, so it must NOT drive a
   556	        //    currency-based Class-A transfer: reconcileClassA would read one side as corrections-current
   557	        //    and copy its MD body over the loser's (different-correction) body — DESTROYING the loser's
   558	        //    corrected MD and recording a false agreement (sticky: the copied bodies then match forever).
   559	        //    Skip the Class-A copy entirely, flag for regen, and write a baseline that does NOT advance
   560	        //    Class A (so the next run re-evaluates once the human resolves corrections). The video stays
   561	        //    "seen" for delete-inference (baseline present).
   562	        //
   563	        //    Class-A signals are derived HERE (before the guard) because the guard needs them; the
   564	        //    derivation is PURE (it only reads the record + the MD body), so hoisting it changes no
   565	        //    behavior. Bodies are needed for hashing regardless — Behavior #1.
   566	        const la = deriveClassASignals(lv, await readMdBody(deps.localBlob, localP, lv));
   567	        const ca = deriveClassASignals(cv, await readMdBody(deps.cloudBlob, cloudP, cv));
   568	
   569	        // ── B1 (round 3) — the two-sided counterpart of copyAdditiveVideo's WB-H1/H-R2-1 guard (:160).
   570	        //    readMdBody returns null for TWO different situations: the record advertises no summaryMd,
   571	        //    or it advertises one whose bytes could not be READ. The backends disagree on which errors
   572	        //    are which: local get throws on anything but ENOENT, but the Supabase get is `if (error)
   573	        //    return null` — it swallows EVERY failure (network, 5xx, timeout, RLS denial), so on the
   574	        //    cloud side an ordinary transient download error is indistinguishable from "no MD".
   575	        //    deriveClassASignals maps a null body to mdHash: null, and reconcileClassA reads
   576	        //    mdHash == null as "this side HAS NO MD" (:21-23) — and those presence branches return
   577	        //    BEFORE the corrections-currency and never-downgrade-format ladder (:38-46). So an
   578	        //    unreadable body made the other replica's body get copied over it (destroying it) and
   579	        //    recorded a full-agreement baseline; run 2 then saw identical bodies and skipped, making
   580	        //    the loss permanent and recoverable only by paid regeneration.
   581	        //    Throwing per-video is caught below, surfaces in report.errors, and advances NO baseline,
   582	        //    so the run heals by itself once the body is readable. With this guard reconcileClassA's
   583	        //    !lHas/!cHas branches mean what they claim: the side genuinely advertises no summaryMd —
   584	        //    which is exactly M-R2-2's "purely additive hydration", so its intent is preserved.
   585	        //    H2 (round 4) — the guard is scoped to the backend that actually needs it. It exists
   586	        //    ONLY because one backend cannot tell absent from unreadable, so only that backend
   587	        //    should pay for it (BlobStore.provesAbsence). On the local FS store a null body IS
   588	        //    proof the file is gone — the user moved or deleted the .md by hand, or a generation
   589	        //    crashed between the index write and the blob write — and that case heals for free:
   590	        //    !lHas → copyToLocal writes the cloud's intact body over the dangling pointer, purely
   591	        //    additive, nothing to destroy. Throwing there stranded the video on EVERY run forever,
   592	        //    never advancing a baseline, with no exit but hand-editing playlist-index.json or
   593	        //    paying to regenerate content sitting intact in the cloud — re-introducing exactly the
   594	        //    stranding M-R2-2 removed. The cloud side stays fail-closed, unchanged.
   595	        if (lv.summaryMd && la.mdHash == null && !deps.localBlob.provesAbsence) {
   596	          throw new Error(`local MD body unreadable for ${id}`);
   597	        }
   598	        if (cv.summaryMd && ca.mdHash == null && !deps.cloudBlob.provesAbsence) {
   599	          throw new Error(`cloud MD body unreadable for ${id}`);
   600	        }
   601	
   602	        //    M-R2-2 — the skip is narrowed to the genuinely DESTRUCTIVE case: BOTH sides actually hold
   603	        //    an MD body. When one side has none, the Class-A copy is purely ADDITIVE hydration —
   604	        //    nothing can be destroyed and no false agreement about competing bodies is possible — so
   605	        //    skipping would strand the video with no MD forever (safe-but-stuck until a human edits
   606	        //    corrections). The corrections conflict is still logged by Class B and still flags
   607	        //    needsRegen via reconcileClassA (the hydrated MD is corrections-stale).
   608	        const correctionsUnresolved = merges.corrections.winner === 'equal' && merges.corrections.conflict;
   609	        if (correctionsUnresolved && la.mdHash != null && ca.mdHash != null) {
   610	          report.needsRegen += 1;
   611	          if (lv.archived !== cv.archived) report.archivedNotSynced += 1; // R10 — do NOT sync archived
   612	          await writeVideoBaseline(dataRoot, key, id, buildCorrectionsUnresolvedBaseline(merges, base));
   613	          continue;
   614	        }
   615	
   616	        // ── Class A (la/ca derived above the WB-B1 guard, which needs them — Behavior #1).
   617	        const decision = reconcileClassA({ local: la, cloud: ca, reconciledCorrectionsHash });
   618	        if (decision.needsRegen) report.needsRegen += 1;
   619	
   620	        let winnerMdHash: string | null = null;
   621	        let winnerSignals: ClassASignals = la;
   622	        let winnerSide: Side | null = null;
   623	        let loserSide: Side | null = null;
   624	        let winnerVideo: Video = lv;
   625	
   626	        if (decision.action === 'copyToCloud') {
   627	          winnerSide = localSide; loserSide = cloudSide; winnerVideo = lv; winnerSignals = la;
   628	          winnerMdHash = (await transferClassA(localSide, cloudSide, lv, id)).mdHash;
   629	          report.updatedCloud += 1;
   630	        } else if (decision.action === 'copyToLocal') {
   631	          winnerSide = cloudSide; loserSide = localSide; winnerVideo = cv; winnerSignals = ca;
   632	          winnerMdHash = (await transferClassA(cloudSide, localSide, cv, id)).mdHash;
   633	          report.updatedLocal += 1;
   634	        } else {
   635	          report.skippedIdentical += 1;
   636	          winnerMdHash = la.mdHash; winnerSignals = la; // skip: sides already agree
   637	        }
   638	
   639	        if (decision.action !== 'skip' && winnerMdHash && winnerSide && loserSide) {
   640	          const c = await companionTransfer(winnerSide, loserSide, winnerMdHash, winnerVideo);
   641	          if (c.shareNeedsOwnerServe) report.shareNeedsOwnerServe += 1;
   642	          // M-R6-1 — companion failures are reported, never thrown: the Class-A commit above is
   643	          // durable, so the baseline below MUST still advance (re-running would not retry the ship).
   644	          if (c.error) report.errors.push({ videoId: id, message: c.error });
   645	        }
   646	        if (lv.archived !== cv.archived) report.archivedNotSynced += 1; // R10 — do NOT sync archived
   647	
   648	        // ── Manifest AFTER the verified commit (Behavior #10); advance even on skip (N4). Pass the
   649	        //    PREVIOUS baseline so a no-write Class-B conflict is NOT falsely advanced (round-3 H2).
   650	        await writeVideoBaseline(dataRoot, key, id, buildBaseline(winnerSignals, winnerMdHash, merges, base));
   651	      } catch (e: any) {
   652	        report.errors.push({ videoId: id, message: e?.message ?? String(e) }); // Behaviors #11/#13
   653	      }
   654	    }
   655	  }
   656	
   657	  return report;
   658	}

exec
/bin/bash -lc "nl -ba tests/lib/cloud-sync/companion.test.ts | sed -n '1,180p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	import { decideCompanion, type ModelRead } from '@/lib/cloud-sync/companion';
     2	import { GENERATOR_VERSION } from '@/lib/html-doc/constants';
     3	import type { ModelEnvelope } from '@/lib/html-doc/model-store';
     4	
     5	const env = (sourceMdHash?: string, generatorVersion?: string): ModelEnvelope => ({
     6	  sourceMd: 'x', generatedAt: '2026', sourceSections: ['A'],
     7	  model: { sections: [{ lead: 'l', bullets: [{ label: 'a', text: 'b' }, { label: 'c', text: 'd' }, { label: 'e', text: 'f' }] }] },
     8	  ...(sourceMdHash ? { sourceMdHash } : {}),
     9	  ...(generatorVersion ? { generatorVersion } : {}),
    10	});
    11	const envelope = (h?: string, gv?: string): ModelRead =>
    12	  ({ kind: 'envelope', envelope: env(h, gv) });
    13	/** An envelope the serve path's isFresh() would accept on generatorVersion. */
    14	const current = (h?: string): ModelRead => envelope(h, GENERATOR_VERSION);
    15	/** An envelope built by an older checkout — isFresh() rejects it. */
    16	const stale = (h?: string): ModelRead => envelope(h, 'magazine-skim v1');
    17	const decide = (senderModel: ModelRead, receiverModel: ModelRead) =>
    18	  decideCompanion({ winnerMdHash: 'h1', senderModel, receiverModel });
    19	
    20	const DELETE = { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
    21	/** Keep the receiver's blob. `flag` is the SEPARATE report-only axis (§10 row 7). */
    22	const KEEP = (flag: boolean) => ({ kind: 'noop', shareNeedsOwnerServe: flag });
    23	
    24	// ── Rule 1 — the sender has a model built from the WINNING md and the receiver holds nothing built
    25	//    from that same body: ship it. (When BOTH sides match the winner hash, generatorVersion decides —
    26	//    see the L-R6-1 sub-matrix below.)
    27	describe('sender ships', () => {
    28	  it.each<[string, ModelRead]>([
    29	    ['receiver absent', { kind: 'none' }],
    30	    ['receiver unreadable', { kind: 'unknown' }],
    31	    ['receiver stale', envelope('h2')],
    32	    ['receiver legacy (no sourceMdHash)', envelope(undefined)],
    33	  ])('ships a matching sender envelope (%s)', (_label, receiver) => {
    34	    expect(decide(envelope('h1'), receiver)).toMatchObject({ kind: 'ship' });
    35	  });
    36	});
    37	
    38	// ── L-R6-1 (round 6) — BOTH sides hold a model built from the WINNING body. Shipping unconditionally
    39	//    could DOWNGRADE the receiver: a sender on an older checkout overwrites a model isFresh() accepts
    40	//    with one it rejects, flipping the share from rendering to 503 and making recovery a PAID owner
    41	//    re-serve. When both match the winner hash the bodies are identical, so the only thing left to
    42	//    compare is generatorVersion — prefer the fresher, and never write when the receiver is already
    43	//    current.
    44	describe('both sides match the winner hash — generatorVersion breaks the tie', () => {
    45	  it('KEEPS a receiver that is already current, even when the sender is older (no downgrade)', () => {
    46	    expect(decide(stale('h1'), current('h1'))).toEqual(KEEP(false));
    47	  });
    48	  it('SHIPS when only the sender is current (a real upgrade)', () => {
    49	    expect(decide(current('h1'), stale('h1'))).toMatchObject({ kind: 'ship' });
    50	  });
    51	  it('KEEPS when NEITHER is current (a pointless write — both need a re-serve anyway)', () => {
    52	    expect(decide(stale('h1'), stale('h1'))).toEqual(KEEP(false));
    53	  });
    54	  it('KEEPS when BOTH are current (identical body, identical generator — nothing to write)', () => {
    55	    expect(decide(current('h1'), current('h1'))).toEqual(KEEP(false));
    56	  });
    57	  it('KEEPS when both are legacy envelopes with no generatorVersion at all', () => {
    58	    expect(decide(envelope('h1'), envelope('h1'))).toEqual(KEEP(false));
    59	  });
    60	});
    61	
    62	// ── H-R5-1 (round 5) — rules 2/3. The sender read answers "can a replacement be shipped?"; it does
    63	//    NOT answer "is the receiver's model stale?". Only the RECEIVER's own sourceMdHash answers that,
    64	//    and it answers it exactly. So every non-ship sender state funnels into the same receiver-keyed
    65	//    decision — `unknown` is no longer a decision of its own, and `none` no longer deletes blind.
    66	describe('receiver-keyed decision (every non-shipping sender state)', () => {
    67	  const nonShippingSenders: [string, ModelRead][] = [
    68	    ['sender provably has none', { kind: 'none' }],
    69	    ['sender read is unprovable', { kind: 'unknown' }],
    70	    ['sender envelope does not match the winner', envelope('h2')],
    71	    ['sender envelope is legacy (no sourceMdHash)', envelope(undefined)],
    72	  ];
    73	
    74	  describe.each(nonShippingSenders)('%s', (_label, sender) => {
    75	    it('DELETES a receiver model whose sourceMdHash provably differs from the winner', () => {
    76	      expect(decide(sender, envelope('h2'))).toEqual(DELETE);
    77	    });
    78	    it('KEEPS a receiver model whose sourceMdHash matches the winner (still valid — paid artifact)', () => {
    79	      expect(decide(sender, envelope('h1'))).toEqual(KEEP(false));
    80	    });
    81	    it('touches nothing when the receiver PROVABLY has no model, but still counts the unready share', () => {
    82	      // §10 row 7 — nothing to delete, yet the share cannot render until the owner re-serves. The
    83	      // blob action and the report flag are separate axes.
    84	      expect(decide(sender, { kind: 'none' })).toEqual(KEEP(true));
    85	    });
    86	    it('KEEPS but still counts when the receiver read itself could not prove absence', () => {
    87	      // Unprovable, so the DELETE must not fire — but the flag costs nothing and under-reporting
    88	      // is what strands an anon visitor on a not-ready share.
    89	      expect(decide(sender, { kind: 'unknown' })).toEqual(KEEP(true));
    90	    });
    91	    it('KEEPS but still counts a legacy receiver envelope with no sourceMdHash', () => {
    92	      expect(decide(sender, envelope(undefined))).toEqual(KEEP(true));
    93	    });
    94	  });
    95	});
    96	
    97	// ── The report flag on the SHIP branch: the receiver ends up holding a model built from the
    98	//    winning MD, so the share renders and nothing is owed.
    99	it('never flags owner-serve when a model was shipped', () => {
   100	  for (const r of [{ kind: 'none' }, { kind: 'unknown' }, envelope('h2'), stale('h1')] as ModelRead[]) {
   101	    expect(decide(current('h1'), r)).not.toMatchObject({ shareNeedsOwnerServe: true });
   102	  }
   103	});
   104	
   105	// ── The money invariant, stated once as its own assertion: the ONLY input that deletes is a receiver
   106	//    envelope carrying a sourceMdHash that differs from the winner's. Everything else keeps.
   107	it('deletes only on a proven receiver-side mismatch', () => {
   108	  const senders: ModelRead[] = [
   109	    { kind: 'none' }, { kind: 'unknown' }, envelope('h2'), envelope(undefined),
   110	    envelope('h1'), current('h1'), stale('h1'),
   111	  ];
   112	  const receivers: ModelRead[] = [
   113	    { kind: 'none' }, { kind: 'unknown' }, envelope(undefined), envelope('h2'),
   114	    envelope('h1'), current('h1'), stale('h1'),
   115	  ];
   116	  for (const s of senders) {
   117	    for (const r of receivers) {
   118	      const deleted = decideCompanion({ winnerMdHash: 'h1', senderModel: s, receiverModel: r }).kind === 'deleteReceiverModel';
   119	      const senderShips = s.kind === 'envelope' && s.envelope.sourceMdHash === 'h1';
   120	      const receiverProvablyStale = r.kind === 'envelope' && r.envelope.sourceMdHash !== undefined
   121	        && r.envelope.sourceMdHash !== 'h1';
   122	      expect(deleted).toBe(!senderShips && receiverProvablyStale);
   123	    }
   124	  }
   125	});

exec
/bin/bash -lc "rg -n \"shareNeedsOwnerServe|report\\.errors|errors:|companion|writeVideoBaseline|companionTransfer|GENERATOR_VERSION|isFresh|sourceSections|writeModelEnvelope|readModelEnvelope\" lib tests app -g '"'!node_modules'"'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
tests/e2e/dig-slide-captions.spec.ts:8:import type { DugSection } from '../../lib/dig/companion-doc';
tests/e2e/dig-deeper.spec.ts:11:import type { DugSection } from '../../lib/dig/companion-doc';
tests/e2e/dig-deeper.spec.ts:12:import { DIG_GENERATOR_VERSION } from '../../lib/dig/generate';
tests/e2e/dig-deeper.spec.ts:30:// A minimal base64 JPEG (a 1×1 white pixel) to use in the companion HTML fixture.
tests/e2e/dig-deeper.spec.ts:72: * I1/I2 fix: build the companion HTML by calling renderDigDeeperDoc with a real
tests/e2e/dig-deeper.spec.ts:118:      genVersion: DIG_GENERATOR_VERSION,
tests/e2e/dig-deeper.spec.ts:155:      genVersion: DIG_GENERATOR_VERSION,
tests/e2e/dig-deeper.spec.ts:175: * Serve both summary and companion HTML for a video at its canonical API URL.
tests/e2e/dig-deeper.spec.ts:186:  companionHtml: string,
tests/e2e/dig-deeper.spec.ts:194:        body: companionHtml,
tests/e2e/dig-deeper.spec.ts:252:// stubCompanionHtml removed — both summary and companion HTML are served
tests/e2e/dig-deeper.spec.ts:267:  const companionHtml = makeCompanionHtmlWithSlides();
tests/e2e/dig-deeper.spec.ts:269:  await stubHtmlRoutes(page, VIDEO_ID_SLIDES, summaryHtml, companionHtml);
tests/e2e/dig-deeper.spec.ts:313:  const companionHtml = makeCompanionHtmlWithSlides();
tests/e2e/dig-deeper.spec.ts:315:  await stubHtmlRoutes(page, VIDEO_ID_SLIDES, summaryHtml, companionHtml);
tests/e2e/dig-deeper.spec.ts:354:  // Use the dug companion HTML (it has the ↑ summary link in the top bar)
tests/e2e/dig-deeper.spec.ts:355:  const companionHtml = makeCompanionHtmlWithSlides();
tests/e2e/dig-deeper.spec.ts:358:  await stubHtmlRoutes(page, VIDEO_ID_SLIDES, summaryHtml, companionHtml);
tests/e2e/dig-deeper.spec.ts:461:      sourceSections: [sectionTitle],
tests/e2e/dig-deeper.spec.ts:533:    { sectionId: SEC_A, startSec: SEC_A, title: 'Alpha', bodyMarkdown: '## Alpha\n\nDug body.\n', generatedAt: '2026-01-01T00:00:00.000Z', genVersion: DIG_GENERATOR_VERSION },
tests/e2e/dig-deeper.spec.ts:619:// F5c: renderDigDeeperDoc — missing-asset: companion references an asset file
tests/e2e/dig-deeper.spec.ts:650:      genVersion: DIG_GENERATOR_VERSION,
tests/e2e/dig-deeper.spec.ts:673:// F5d: renderDigDeeperDoc — orphan companion section: companion has a section
tests/e2e/dig-deeper.spec.ts:699:    { sectionId: SEC_ORPHAN_SUMMARY, startSec: SEC_ORPHAN_SUMMARY, title: 'Real Section', bodyMarkdown: '## Real Section\n\nMatched.\n', generatedAt: '2026-01-01T00:00:00.000Z', genVersion: DIG_GENERATOR_VERSION },
tests/e2e/dig-deeper.spec.ts:701:    { sectionId: SEC_ORPHAN_COMPANION, startSec: SEC_ORPHAN_COMPANION, title: 'Ghost Section', bodyMarkdown: '## Ghost Section\n\nOrphaned.\n', generatedAt: '2026-01-01T00:00:00.000Z', genVersion: DIG_GENERATOR_VERSION },
tests/e2e/dig-deeper.spec.ts:706:test('F5d (orphan companion section): unmatched companion section → "Unmapped dug sections" region visible', async ({ page }) => {
tests/e2e/dig-deeper.spec.ts:786:  // Envelope with matching sourceSections allows the renderer to emit a .gist block,
tests/e2e/dig-deeper.spec.ts:791:    sourceSections: ['Section Alpha'],
tests/e2e/dig-deeper.spec.ts:805:      genVersion: DIG_GENERATOR_VERSION,
tests/e2e/dig-deeper.spec.ts:1088:      genVersion: DIG_GENERATOR_VERSION,
tests/e2e/dig-deeper.spec.ts:1346:    genVersion: DIG_GENERATOR_VERSION,
tests/e2e/dig-deeper.spec.ts:1748:      genVersion: DIG_GENERATOR_VERSION,
tests/e2e/dig-deeper.spec.ts:1948: * Stale dig-doc HTML: the section is dug but genVersion < DIG_GENERATOR_VERSION,
tests/e2e/dig-deeper.spec.ts:1976:  // genVersion < DIG_GENERATOR_VERSION → isStale=true → .dig-refresh rendered
tests/e2e/dig-deeper.spec.ts:1984:      genVersion: DIG_GENERATOR_VERSION - 1,
tests/e2e/dig-deeper.spec.ts:2025:  // genVersion = DIG_GENERATOR_VERSION → isStale=false → no .dig-refresh badge
tests/e2e/dig-deeper.spec.ts:2033:      genVersion: DIG_GENERATOR_VERSION,
tests/e2e/dig-deeper.spec.ts:2172:        genVersion: DIG_GENERATOR_VERSION,
tests/e2e/dig-deeper.spec.ts:2184:      genVersion: resolved.has(SEC_EA_MIXED_STALE) ? DIG_GENERATOR_VERSION : DIG_GENERATOR_VERSION - 1,
tests/e2e/dig-slide-size.spec.ts:7:import type { DugSection } from '../../lib/dig/companion-doc';
tests/e2e/dig-slide-crop.spec.ts:10:import type { DugSection } from '../../lib/dig/companion-doc';
tests/e2e/dig-slide-crop.spec.ts:11:import { DIG_GENERATOR_VERSION } from '../../lib/dig/generate';
tests/e2e/dig-slide-crop.spec.ts:73:      genVersion: DIG_GENERATOR_VERSION,
app/api/videos/[id]/dig-state/route.ts:4:import { readDugSectionIds } from '../../../../../lib/dig/companion-doc';
app/api/videos/[id]/dig-state/route.ts:5:import { DIG_GENERATOR_VERSION } from '@/lib/dig/generate';
app/api/videos/[id]/dig-state/route.ts:46:    const suffix = `.r${DIG_GENERATOR_VERSION}.md`;
tests/integration/share-route.test.ts:5:import { writeModelEnvelope } from '@/lib/html-doc/model-store';
tests/integration/share-route.test.ts:6:import { GENERATOR_VERSION } from '@/lib/html-doc/constants';
tests/integration/share-route.test.ts:70:/** Seed a fresh model envelope via writeModelEnvelope through a full service-role SupabaseBlobStore
tests/integration/share-route.test.ts:75:  await writeModelEnvelope(
tests/integration/share-route.test.ts:81:      sourceSections: ['Intro'],
tests/integration/share-route.test.ts:82:      generatorVersion: GENERATOR_VERSION,
tests/integration/share-route.test.ts:162:    // Deliberately no writeModelEnvelope call — model absent.
tests/integration/share-route.test.ts:174:    // isFresh() (lib/html-doc/read-model.ts) must reject it just like the absent case above.
tests/integration/share-route.test.ts:177:    await writeModelEnvelope(
tests/integration/share-route.test.ts:183:        sourceSections: ['Intro'],
tests/integration/share-route.test.ts:184:        generatorVersion: 'stale-vX', // deliberately mismatched — must NOT equal GENERATOR_VERSION
tests/integration/html-download.test.ts:15:import { writeModelEnvelope } from '@/lib/html-doc/model-store';
tests/integration/html-download.test.ts:16:import { GENERATOR_VERSION } from '@/lib/html-doc/constants';
tests/integration/html-download.test.ts:251:    await writeModelEnvelope(principal, base, {
tests/integration/html-download.test.ts:254:      sourceSections: titles,          // title-stable: same titles as the current MD
tests/integration/html-download.test.ts:255:      generatorVersion: 'OLD',         // NOT current GENERATOR_VERSION → not fresh, but title-stable
tests/integration/html-download.test.ts:276:    await writeModelEnvelope(principal, base, {
tests/integration/html-download.test.ts:279:      sourceSections: titles,
tests/integration/html-download.test.ts:280:      generatorVersion: GENERATOR_VERSION, // FRESH — matches current version
tests/integration/helpers/cloud.ts:26:import { readManifest as readManifestFile, writeVideoBaseline } from '@/lib/cloud-sync/manifest';
tests/integration/helpers/cloud.ts:65:   *  companion `models/*` put throw, leaving the Class-A staged→promote path intact (M-R6-1). Cloud
tests/integration/helpers/cloud.ts:178:/** M-R6-1 — wraps a BlobStore so ONLY the companion model put (`models/*.json`) throws. The Class-A
tests/integration/helpers/cloud.ts:180: *  exactly the companion ship write: the run must report the share as unready rather than leave the
tests/integration/helpers/cloud.ts:187:    if (key.startsWith('models/')) throw new Error('injected companion model put failure');
tests/integration/helpers/cloud.ts:310:// + companionTransfer), not just the additive hydrate path (copyAdditiveVideo).
tests/integration/helpers/cloud.ts:367: *  worker's promoted-video shape (seed.ts) but with full control over the Class-A/companion signals. */
tests/integration/helpers/cloud.ts:436: *  with full Class-A/companion control). Idempotently creates the local playlist dir + index. */
tests/integration/helpers/cloud.ts:455:  await writeVideoBaseline(ctx.playlistDataRoot, ctx.playlistKey, ctx.videoId, baseline);
tests/api/dig-state.test.ts:14:import * as companionDoc from '../../lib/dig/companion-doc';
tests/api/dig-state.test.ts:16:jest.mock('../../lib/dig/companion-doc');
tests/api/dig-state.test.ts:17:const mockReadDugSectionIds = companionDoc.readDugSectionIds as jest.Mock;
tests/api/dig-state.test.ts:121:it('returns { sectionIds: [60, 120] } when companion doc has two dug sections', async () => {
tests/api/dig-state.test.ts:131:it('calls readDugSectionIds with the resolved companion doc path', async () => {
tests/integration/pdf-cloud.test.ts:35:import { writeModelEnvelope } from '@/lib/html-doc/model-store';
tests/integration/pdf-cloud.test.ts:36:import { GENERATOR_VERSION } from '@/lib/html-doc/constants';
tests/integration/pdf-cloud.test.ts:254:/** Materialize a FRESH magazine model envelope (current GENERATOR_VERSION, section titles matching
tests/integration/pdf-cloud.test.ts:260:  await writeModelEnvelope(principal, base, {
tests/integration/pdf-cloud.test.ts:263:    sourceSections: titles,
tests/integration/pdf-cloud.test.ts:264:    generatorVersion: GENERATOR_VERSION,
tests/api/dig-post.test.ts:17:import { DIG_GENERATOR_VERSION } from '../../lib/dig/generate';
tests/api/dig-post.test.ts:21:import * as companionDocMod from '../../lib/dig/companion-doc';
tests/api/dig-post.test.ts:34:jest.mock('../../lib/dig/companion-doc');
tests/api/dig-post.test.ts:64:const mockUpsertDugSection = companionDocMod.upsertDugSection as jest.Mock;
tests/api/dig-post.test.ts:300:  it('does NOT write any HTML file (GET renders fresh; POST only upserts companion)', async () => {
tests/api/dig-post.test.ts:321:  it('stamps the current DIG_GENERATOR_VERSION on the upserted section', async () => {
tests/api/dig-post.test.ts:326:        section: expect.objectContaining({ genVersion: DIG_GENERATOR_VERSION }),
tests/integration/serve-doc-materialize.test.ts:5:import { readModelEnvelope, writeModelEnvelope } from '@/lib/html-doc/model-store';
tests/integration/serve-doc-materialize.test.ts:6:import { GENERATOR_VERSION } from '@/lib/html-doc/render';
tests/integration/serve-doc-materialize.test.ts:67:  const env = await readModelEnvelope(principal, videoId, blob);
tests/integration/serve-doc-materialize.test.ts:81:  // charge) and the assertion below would pass EVEN IF resolveMagazineModel's isFresh() short-circuit
tests/integration/serve-doc-materialize.test.ts:104:  expect(await readModelEnvelope(principal, videoId, blob)).toBeNull();
tests/integration/serve-doc-materialize.test.ts:107:it('re-materializes on drift (sourceSections mismatch) — B3', async () => {
tests/integration/serve-doc-materialize.test.ts:114:  const drifted = parsed(); drifted.sections[0].title = 'Renamed'; // titles now differ from the cached sourceSections
tests/integration/serve-doc-materialize.test.ts:121:it('re-materializes on a STALE generatorVersion even when sourceSections match (F6 — version gate)', async () => {
tests/integration/serve-doc-materialize.test.ts:127:  // Seed a cached envelope whose sourceSections MATCH the current parse (NO title drift) but whose
tests/integration/serve-doc-materialize.test.ts:131:  await writeModelEnvelope(principal, videoId, {
tests/integration/serve-doc-materialize.test.ts:134:    sourceSections: p.sections.map((s) => s.title),
tests/integration/serve-doc-materialize.test.ts:135:    generatorVersion: `${GENERATOR_VERSION}-STALE`,
tests/integration/serve-doc-materialize.test.ts:143:  // Persistence proof (Option A): writeModelEnvelope upserts (plain `put`), so the stale blob was
tests/integration/serve-doc-materialize.test.ts:147:  const persisted = await readModelEnvelope(principal, videoId, blob);
tests/integration/serve-doc-materialize.test.ts:148:  expect(persisted?.generatorVersion).toBe(GENERATOR_VERSION);
tests/integration/serve-doc-materialize.test.ts:166:  // Seed a CORRUPT models/<base>.json directly via the blob store (bypassing writeModelEnvelope's
tests/integration/serve-doc-materialize.test.ts:168:  // partially-written blob. readModelEnvelope must swallow the JSON.parse failure and return null
tests/integration/serve-doc-materialize.test.ts:174:  const persisted = await readModelEnvelope(principal, videoId, blob);
tests/integration/serve-doc-materialize.test.ts:175:  expect(persisted?.generatorVersion).toBe(GENERATOR_VERSION); // valid envelope now persisted, overwriting the corrupt blob
tests/integration/serve-doc-materialize.test.ts:188:  await writeModelEnvelope(principal, videoId, {
tests/integration/serve-doc-materialize.test.ts:190:    sourceSections: p.sections.map((s) => s.title), generatorVersion: 'OLD', model: staleModel,
tests/integration/serve-doc-materialize.test.ts:218:  await writeModelEnvelope(principal, videoId, {
tests/integration/serve-doc-materialize.test.ts:220:    sourceSections: ['Something Else'], generatorVersion: 'OLD', model: staleModel, // deliberately mismatched titles
tests/integration/serve-doc-materialize.test.ts:234:  await writeModelEnvelope(principal, videoId, {
tests/integration/serve-doc-materialize.test.ts:236:    sourceSections: p.sections.map((s) => s.title), generatorVersion: GENERATOR_VERSION, // FRESH — matches current version
tests/integration/serve-doc-materialize.test.ts:254:  await writeModelEnvelope(principal, videoId, {
tests/integration/serve-doc-materialize.test.ts:256:    sourceSections: p.sections.map((s) => s.title), generatorVersion: 'OLD', model: staleModel,
tests/api/html-serve.test.ts:5:import { GENERATOR_VERSION } from '../../lib/html-doc/render';
tests/api/html-serve.test.ts:83:    `<!DOCTYPE html><head><meta name="generator" content="${GENERATOR_VERSION}"></head><title>ok</title>`);
tests/api/html-serve.test.ts:96:    `<!DOCTYPE html><head><meta name="generator" content="${GENERATOR_VERSION}"></head><title>ko</title>`);
tests/api/html-serve.test.ts:138:// Helper: write a valid companion doc
tests/api/html-serve.test.ts:198:  // No model written → readModelEnvelope returns null → all gists null
tests/api/html-serve.test.ts:220:it('dig-deeper B6: orphan companion section → orphan region rendered, 200', async () => {
tests/api/html-serve.test.ts:253:  // Index says companion exists, but the file has been deleted from disk.
tests/api/html-serve.test.ts:268:it('dig-deeper B8: companion-path ALONE escapes outputFolder → 400 (companion assertWithin fires first)', async () => {
tests/api/html-serve.test.ts:270:  // so this test exercises the companion-path assertWithin independently.
tests/api/html-serve.test.ts:271:  // summaryMd is safe; digDeeperMd escapes → companion assertWithin fires → 400.
tests/api/html-serve.test.ts:275:    digDeeperMd: '../../../etc/companion.md',      // escapes outputFolder immediately
tests/api/html-serve.test.ts:301:    const cached = makeHtmlWithGenerator(GENERATOR_VERSION);
tests/api/html-serve.test.ts:316:    const freshHtml = `<!DOCTYPE html><html><head><meta name="generator" content="${GENERATOR_VERSION}"></head><body>fresh</body></html>`;
tests/api/dig-state-cloud.test.ts:19:import { DIG_GENERATOR_VERSION as V } from '@/lib/dig/generate';
tests/api/jobs-route.test.ts:68:it('POST maps producer errors: 422 / 503', async () => {
tests/integration/dig-serve-interactive.test.ts:68:    // DIG_GENERATOR_VERSION itself — do not hand-roll the frontmatter/version).
lib/cloud-sync/companion.ts:1:import { GENERATOR_VERSION } from '@/lib/html-doc/constants';
lib/cloud-sync/companion.ts:5: *  `readModelEnvelope` collapses three different situations into one null: the envelope is absent,
lib/cloud-sync/companion.ts:20:/** H-R5-1 (round 5) — `shareNeedsOwnerServe` is now carried on `noop` too, because it is a SEPARATE
lib/cloud-sync/companion.ts:27:  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true }
lib/cloud-sync/companion.ts:28:  | { kind: 'noop'; shareNeedsOwnerServe: boolean };
lib/cloud-sync/companion.ts:37: *  run's Class-A reconcile returns 'skip' and never revisits the companion step.
lib/cloud-sync/companion.ts:57: *  sender's blind overwrites a receiver model isFresh() accepts (lib/html-doc/read-model.ts) with one
lib/cloud-sync/companion.ts:61: *  Reachability is not exotic: it needs GENERATOR_VERSION skew between the local checkout and the
lib/cloud-sync/companion.ts:85:    if (receiverMatch.generatorVersion === GENERATOR_VERSION) {
lib/cloud-sync/companion.ts:86:      return { kind: 'noop', shareNeedsOwnerServe: false }; // receiver already fresh — do not write
lib/cloud-sync/companion.ts:88:    if (senderMatch.generatorVersion === GENERATOR_VERSION) {
lib/cloud-sync/companion.ts:91:    return { kind: 'noop', shareNeedsOwnerServe: false }; // neither is current — both need a re-serve
lib/cloud-sync/companion.ts:100:  if (receiverMatch) return { kind: 'noop', shareNeedsOwnerServe: false };
lib/cloud-sync/companion.ts:109:  //    cache is recoverable — any regeneration overwrites it, and the existing sourceSections /
lib/cloud-sync/companion.ts:113:  //  - REPORT on doubt. shareNeedsOwnerServe is a report-only count (§10 row 7): "these shares may
lib/cloud-sync/companion.ts:120:  if (provablyStale) return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
lib/cloud-sync/companion.ts:121:  return { kind: 'noop', shareNeedsOwnerServe: true };
tests/lib/job-queue/dig-handler.test.ts:13:import { generateDig, DIG_GENERATOR_VERSION } from '@/lib/dig/generate';
tests/lib/job-queue/dig-handler.test.ts:32:const job = { id: 'j1', ownerId: 'owner1', playlistId: 'pl-uuid', videoId: 'vid1', sectionId: 132, kind: 'dig', version: `dig-${DIG_GENERATOR_VERSION}`, payload: { durationSeconds: 600 }, attempts: 0, leaseToken: 'lt' };
lib/cloud-sync/manifest.ts:40:export async function writeVideoBaseline(
lib/cloud-sync/types.ts:13:/** The companion scalars carried verbatim with a winning MD (§4.1). */
lib/cloud-sync/sync-run.ts:29:import { decideCompanion, type ModelRead } from './companion';
lib/cloud-sync/sync-run.ts:31:  readManifest, writeVideoBaseline, appendConflict, resetConflictDedup,
lib/cloud-sync/sync-run.ts:35:import { readModelEnvelope, writeModelEnvelope } from '@/lib/html-doc/model-store';
lib/cloud-sync/sync-run.ts:48:  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
lib/cloud-sync/sync-run.ts:49:  errors: { videoId: string; message: string }[];
lib/cloud-sync/sync-run.ts:311: *  the 7 companion scalars). Throws on any fault so the caller does NOT advance the baseline. */
lib/cloud-sync/sync-run.ts:382: *  Every companion write is BEST-EFFORT and never throws (M-R6-1): the caller must still advance the
lib/cloud-sync/sync-run.ts:384: *  is surfaced in report.errors by the caller without aborting the per-video flow. */
lib/cloud-sync/sync-run.ts:385:async function companionTransfer(
lib/cloud-sync/sync-run.ts:387:): Promise<{ shareNeedsOwnerServe: boolean; error?: string }> {
lib/cloud-sync/sync-run.ts:388:  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
lib/cloud-sync/sync-run.ts:398:    // next run's reconcileClassA returns 'skip' and the companion step (gated on !== 'skip') never
lib/cloud-sync/sync-run.ts:403:    // visible; the error is returned so it still surfaces in report.errors.
lib/cloud-sync/sync-run.ts:405:      await writeModelEnvelope(loser.p, base, decision.envelope, loser.blob);
lib/cloud-sync/sync-run.ts:406:      return { shareNeedsOwnerServe: false };
lib/cloud-sync/sync-run.ts:408:      return { shareNeedsOwnerServe: true, error: `companion model ship failed: ${e?.message ?? String(e)}` };
lib/cloud-sync/sync-run.ts:414:  if (decision.kind === 'noop') return { shareNeedsOwnerServe: decision.shareNeedsOwnerServe };
lib/cloud-sync/sync-run.ts:417:  return { shareNeedsOwnerServe: true };
lib/cloud-sync/sync-run.ts:420:/** H1 (round 4) — resolve `readModelEnvelope`'s single null into the tri-state decideCompanion needs.
lib/cloud-sync/sync-run.ts:431:  const envelope = await readModelEnvelope(side.p, base, side.blob);
lib/cloud-sync/sync-run.ts:495:    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
lib/cloud-sync/sync-run.ts:535:            await writeVideoBaseline(dataRoot, key, id, baselineFromOneSided(
lib/cloud-sync/sync-run.ts:581:        //    Throwing per-video is caught below, surfaces in report.errors, and advances NO baseline,
lib/cloud-sync/sync-run.ts:612:          await writeVideoBaseline(dataRoot, key, id, buildCorrectionsUnresolvedBaseline(merges, base));
lib/cloud-sync/sync-run.ts:640:          const c = await companionTransfer(winnerSide, loserSide, winnerMdHash, winnerVideo);
lib/cloud-sync/sync-run.ts:641:          if (c.shareNeedsOwnerServe) report.shareNeedsOwnerServe += 1;
lib/cloud-sync/sync-run.ts:642:          // M-R6-1 — companion failures are reported, never thrown: the Class-A commit above is
lib/cloud-sync/sync-run.ts:644:          if (c.error) report.errors.push({ videoId: id, message: c.error });
lib/cloud-sync/sync-run.ts:650:        await writeVideoBaseline(dataRoot, key, id, buildBaseline(winnerSignals, winnerMdHash, merges, base));
lib/cloud-sync/sync-run.ts:652:        report.errors.push({ videoId: id, message: e?.message ?? String(e) }); // Behaviors #11/#13
lib/job-queue/dig-handler.ts:45:    // DIG_GENERATOR_VERSION must NOT write a current-version blob it never paid for.
tests/lib/cloud-sync/companion.test.ts:1:import { decideCompanion, type ModelRead } from '@/lib/cloud-sync/companion';
tests/lib/cloud-sync/companion.test.ts:2:import { GENERATOR_VERSION } from '@/lib/html-doc/constants';
tests/lib/cloud-sync/companion.test.ts:6:  sourceMd: 'x', generatedAt: '2026', sourceSections: ['A'],
tests/lib/cloud-sync/companion.test.ts:13:/** An envelope the serve path's isFresh() would accept on generatorVersion. */
tests/lib/cloud-sync/companion.test.ts:14:const current = (h?: string): ModelRead => envelope(h, GENERATOR_VERSION);
tests/lib/cloud-sync/companion.test.ts:15:/** An envelope built by an older checkout — isFresh() rejects it. */
tests/lib/cloud-sync/companion.test.ts:20:const DELETE = { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
tests/lib/cloud-sync/companion.test.ts:22:const KEEP = (flag: boolean) => ({ kind: 'noop', shareNeedsOwnerServe: flag });
tests/lib/cloud-sync/companion.test.ts:39://    could DOWNGRADE the receiver: a sender on an older checkout overwrites a model isFresh() accepts
tests/lib/cloud-sync/companion.test.ts:101:    expect(decide(current('h1'), r)).not.toMatchObject({ shareNeedsOwnerServe: true });
tests/integration/cloud-sync/e2e.int.test.ts:6:// here drive the TWO-SIDED Class-A COPY path (transferClassA + companionTransfer) with DIVERGENT
tests/integration/cloud-sync/e2e.int.test.ts:22:import { GENERATOR_VERSION } from '@/lib/html-doc/constants';
tests/integration/cloud-sync/e2e.int.test.ts:41:/** The companion model blob key for this ctx's summary (models/<base>.json, base = summaryMd sans .md). */
tests/integration/cloud-sync/e2e.int.test.ts:45:  sourceMd: 'seed.md', generatedAt: '2026-01-01T00:00:00.000Z', sourceSections: ['A'],
tests/integration/cloud-sync/e2e.int.test.ts:106:    // updateVideoFields finalize carried the winner's docVersion + companion scalars verbatim.
tests/integration/cloud-sync/e2e.int.test.ts:169:  // ── Row 4 — companion scalars carried VERBATIM (not reconstructed/flattened) on an additive hydrate.
tests/integration/cloud-sync/e2e.int.test.ts:238:  it('row 7: a transferred summary with no matching model flags shareNeedsOwnerServe', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:248:    // absence, so this takes the `noop + shareNeedsOwnerServe: true` path (H-R5-1), NOT a delete.
tests/integration/cloud-sync/e2e.int.test.ts:250:    expect(report.shareNeedsOwnerServe).toBeGreaterThanOrEqual(1);
tests/integration/cloud-sync/e2e.int.test.ts:339:    expect(report.errors).toEqual([]);
tests/integration/cloud-sync/e2e.int.test.ts:383:    expect(report.errors.length).toBeGreaterThanOrEqual(1);
tests/integration/cloud-sync/e2e.int.test.ts:475:    expect(report.errors.some((e) => e.videoId === ctx.videoId)).toBe(true);
tests/integration/cloud-sync/e2e.int.test.ts:479:    // Baseline not advanced — the throw aborted before writeVideoBaseline.
tests/integration/cloud-sync/e2e.int.test.ts:607:      // The failure is SURFACED, not silent (the buggy path reported errors: []).
tests/integration/cloud-sync/e2e.int.test.ts:608:      expect(report.errors.some((e) => e.videoId === ctx.videoId)).toBe(true);
tests/integration/cloud-sync/e2e.int.test.ts:642:      expect(report.errors.some((e) => e.videoId === ctx.videoId)).toBe(true);
tests/integration/cloud-sync/e2e.int.test.ts:655:  // ── H1 (round 4) — the B1 conflation one module over, driving a DELETE. companionTransfer read
tests/integration/cloud-sync/e2e.int.test.ts:662:  //    companionTransfer never ran again.
tests/integration/cloud-sync/e2e.int.test.ts:701:    expect(r1.shareNeedsOwnerServe).toBe(1);                      // owner must re-serve the share
tests/integration/cloud-sync/e2e.int.test.ts:704:    // Run 2 — hashes now agree → reconcileClassA 'skip' → companionTransfer never runs again. The
tests/integration/cloud-sync/e2e.int.test.ts:707:    expect(r2.shareNeedsOwnerServe).toBe(0);
tests/integration/cloud-sync/e2e.int.test.ts:739:    expect(r1.shareNeedsOwnerServe).toBe(0);                         // no false "share is stale"
tests/integration/cloud-sync/e2e.int.test.ts:743:    expect(r2.shareNeedsOwnerServe).toBe(0);
tests/integration/cloud-sync/e2e.int.test.ts:749:  //       sender null also covers corrupt/schema-invalid (readModelEnvelope parses and validates),
tests/integration/cloud-sync/e2e.int.test.ts:763:    // Sender (local) envelope is unparseable → readModelEnvelope null on a provesAbsence backend.
tests/integration/cloud-sync/e2e.int.test.ts:780:    expect(r1.shareNeedsOwnerServe).toBe(0);
tests/integration/cloud-sync/e2e.int.test.ts:784:    expect(r2.shareNeedsOwnerServe).toBe(0);
tests/integration/cloud-sync/e2e.int.test.ts:790:  //    built from the WINNING body, but the sender's was built by an older checkout (GENERATOR_VERSION
tests/integration/cloud-sync/e2e.int.test.ts:792:  //    model isFresh() accepts with one it rejects, flipping the share to a 503 whose only recovery is
tests/integration/cloud-sync/e2e.int.test.ts:812:      Buffer.from(`${JSON.stringify(modelEnvelope(bodyHash(bodyLocalWin), GENERATOR_VERSION))}\n`, 'utf8'),
tests/integration/cloud-sync/e2e.int.test.ts:823:    expect(keptEnvelope.generatorVersion).toBe(GENERATOR_VERSION); // NOT downgraded to v1
tests/integration/cloud-sync/e2e.int.test.ts:825:    expect(r1.shareNeedsOwnerServe).toBe(0);                     // the share still renders
tests/integration/cloud-sync/e2e.int.test.ts:829:  // ── M-R6-1 (round 6) — a failed companion ship must not be sticky-silent. transferClassA has
tests/integration/cloud-sync/e2e.int.test.ts:834:  it('M-R6-1: a failed companion ship reports the share unready, still advances the baseline', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:847:      Buffer.from(`${JSON.stringify(modelEnvelope(bodyHash(bodyLocalWin), GENERATOR_VERSION))}\n`, 'utf8'),
tests/integration/cloud-sync/e2e.int.test.ts:854:    // The Class-A commit landed durably despite the companion failure.
tests/integration/cloud-sync/e2e.int.test.ts:861:    expect(r1.shareNeedsOwnerServe).toBe(1);
lib/dig/dig-section.ts:7:import { generateDig, DIG_GENERATOR_VERSION } from '@/lib/dig/generate';
lib/dig/dig-section.ts:10:import { upsertDugSection } from '@/lib/dig/companion-doc';
lib/dig/dig-section.ts:82:  // Step 10: Upsert dug section into companion doc
lib/dig/dig-section.ts:99:      genVersion: DIG_GENERATOR_VERSION,
lib/dig/generate.ts:15:export const DIG_GENERATOR_VERSION = 9;
lib/dig/generate.ts:54: * Note: inline [[TS:i]] transcript citations were removed (DIG_GENERATOR_VERSION 8). Gemini
tests/lib/cloud-sync/manifest.test.ts:5:import { manifestPath, readManifest, writeVideoBaseline, appendConflict } from '@/lib/cloud-sync/manifest';
tests/lib/cloud-sync/manifest.test.ts:25:  await writeVideoBaseline(r, 'PL1', 'v1', base as any);
tests/lib/cloud-sync/model-writer-hash.test.ts:7:// matches, so every synced companion would be wrongly deleted (needless re-charge on serve).
tests/lib/cloud-sync/model-writer-hash.test.ts:14:import { readModelEnvelope } from '../../../lib/html-doc/model-store';
tests/lib/cloud-sync/model-writer-hash.test.ts:79:  const env = await readModelEnvelope(principal, 'a-title');
lib/dig/slide-crop-map.ts:5:import type { DugSection } from './companion-doc';
lib/dig/cloud/parse-dig-section-blob.ts:1:import type { DugSection } from '@/lib/dig/companion-doc';
lib/dig/companion-doc.ts:42:/** Complete in-memory representation of a companion doc. */
lib/dig/companion-doc.ts:335: * Parse the body of a companion doc into a map of sectionId → { title, bodyMarkdown }.
lib/dig/companion-doc.ts:375: * Parse the raw string content of a companion doc into an array of DugSections.
lib/dig/companion-doc.ts:506: * Upsert one dug section into the companion doc at `digDeeperPath`.
lib/dig/companion-doc.ts:532: * of the companion doc at `digDeeperPath`.
tests/lib/cloud-sync/schema.test.ts:29:    sourceMd: 'x', generatedAt: '2026-07-17', sourceSections: ['A'],
tests/integration/cloud-sync/sync-run.int.test.ts:66:    expect(report.errors.length).toBeGreaterThanOrEqual(1);
lib/dig/cloud/write-dig-section-blob.ts:3:import { DIG_GENERATOR_VERSION } from '@/lib/dig/generate';
lib/dig/cloud/write-dig-section-blob.ts:38:    `genVersion: ${DIG_GENERATOR_VERSION}`,
tests/lib/model-store-cloud.test.ts:1:import { ModelEnvelopeSchema, readModelEnvelope, writeModelEnvelope } from '@/lib/html-doc/model-store';
tests/lib/model-store-cloud.test.ts:7:  sourceMd: 'a.md', generatedAt: '2026-07-09T00:00:00.000Z', sourceSections: ['A'],
tests/lib/model-store-cloud.test.ts:37:it('writeModelEnvelope (plain put) round-trips under a cloud principal', async () => {
tests/lib/model-store-cloud.test.ts:39:  await writeModelEnvelope(P, 'a', envelope, store);
tests/lib/model-store-cloud.test.ts:41:  const read = await readModelEnvelope(P, 'a', store);
tests/lib/model-store-cloud.test.ts:45:it('writeModelEnvelope overwrites an existing final via upsert (put, no staging)', async () => {
tests/lib/model-store-cloud.test.ts:48:  await writeModelEnvelope(P, 'a', envelope, store);
tests/lib/model-store-cloud.test.ts:49:  await writeModelEnvelope(P, 'a', { ...envelope, generatorVersion: 'magazine-skim v3' }, store); // overwrites
tests/lib/model-store-cloud.test.ts:50:  const read = await readModelEnvelope(P, 'a', store);
tests/lib/model-store-cloud.test.ts:56:it('readModelEnvelope returns null for a schema-invalid envelope (treated as absent)', async () => {
tests/lib/model-store-cloud.test.ts:59:  expect(await readModelEnvelope(P, 'a', store)).toBeNull();
lib/dig/cloud/load-dig-for-serve.ts:4:import { readModelEnvelope, type ModelEnvelope } from '@/lib/html-doc/model-store';
lib/dig/cloud/load-dig-for-serve.ts:5:import { DIG_GENERATOR_VERSION } from '@/lib/dig/generate';
lib/dig/cloud/load-dig-for-serve.ts:8:import type { DugSection } from '@/lib/dig/companion-doc';
lib/dig/cloud/load-dig-for-serve.ts:30:  const envelope = await readModelEnvelope(load.principal, load.base, load.bundle.blobStore); // cached, free; null if absent
lib/dig/cloud/load-dig-for-serve.ts:33:  const suffix = `.r${DIG_GENERATOR_VERSION}.md`;
lib/dig/cloud/dig-blob-key.ts:1:import { DIG_GENERATOR_VERSION } from '@/lib/dig/generate';
lib/dig/cloud/dig-blob-key.ts:4:/** job_version for a cloud dig job — encodes DIG_GENERATOR_VERSION so a bump lands in a
lib/dig/cloud/dig-blob-key.ts:7:  return `dig-${DIG_GENERATOR_VERSION}`;
lib/dig/cloud/dig-blob-key.ts:22:  const key = `dig/${base}/${sectionId}.r${DIG_GENERATOR_VERSION}.md`;
lib/html-doc/model-store.ts:9: * `sourceSections` is the section titles the model was built against — the drift guard the
lib/html-doc/model-store.ts:12: * still parse; the cloud freshness gate requires it to `=== GENERATOR_VERSION`.
lib/html-doc/model-store.ts:18:    sourceSections: z.array(z.string()),
lib/html-doc/model-store.ts:25:  // must not make an old reader's readModelEnvelope return null (§5.7 round-5 M-2).
lib/html-doc/model-store.ts:43:export async function writeModelEnvelope(
lib/html-doc/model-store.ts:53:export async function readModelEnvelope(
lib/html-doc/constants.ts:2: *  cached model that predates the change is treated as stale (isFresh → false).
lib/html-doc/constants.ts:5:export const GENERATOR_VERSION = 'magazine-skim v2';
lib/html-doc/render.ts:8:import { GENERATOR_VERSION } from './constants';
lib/html-doc/render.ts:9:export { GENERATOR_VERSION };
lib/html-doc/render.ts:113:${share ? '' : `<meta name="generator" content="${GENERATOR_VERSION}">
tests/lib/dig/generate.test.ts:1:import { buildDigPrompt, generateDig, DIG_GENERATOR_VERSION, DEEPDIVE_MODEL } from '@/lib/dig/generate';
tests/lib/dig/generate.test.ts:313:// ── DIG_GENERATOR_VERSION ────────────────────────────────────────────────────────
tests/lib/dig/generate.test.ts:315:describe('DIG_GENERATOR_VERSION', () => {
tests/lib/dig/generate.test.ts:317:    expect(DIG_GENERATOR_VERSION).toBe(9);
tests/lib/dig/slide-crop-map.test.ts:4:import type { DugSection } from '../../../lib/dig/companion-doc';
lib/html-doc/rerender.ts:6:import { readModelEnvelope } from './model-store';
lib/html-doc/rerender.ts:43:  const envelope = await readModelEnvelope(principal, base, resolvedBlob);
lib/html-doc/rerender.ts:67:  if (!sameTitles(mdTitles, envelope.sourceSections)) {
lib/html-doc/rerender.ts:68:    return { status: 'skipped-drift', mdSections: mdTitles, modelSections: envelope.sourceSections };
lib/html-doc/rerender.ts:92:  errors: number;
lib/html-doc/rerender.ts:104:    skippedUnparseable: 0, skippedDrift: 0, errors: 0, details: [],
tests/lib/dig/companion-doc.test.ts:4:import { upsertDugSection, readDugSectionIds, parseDugSections } from '@/lib/dig/companion-doc';
tests/lib/dig/companion-doc.test.ts:5:import { DIG_GENERATOR_VERSION } from '@/lib/dig/generate';
tests/lib/dig/companion-doc.test.ts:13:  section: { ...section, genVersion: section.genVersion ?? DIG_GENERATOR_VERSION },
tests/lib/dig/companion-doc.test.ts:210:    section: { sectionId: 1, startSec: 1, title: 'T', bodyMarkdown: 'body', generatedAt: 'TS', genVersion: DIG_GENERATOR_VERSION },
tests/lib/dig/companion-doc.test.ts:220:    section: { sectionId: 2, startSec: 2, title: 'U', bodyMarkdown: 'body2', generatedAt: 'TS2', genVersion: DIG_GENERATOR_VERSION },
lib/html-doc/generate.ts:5:import { renderMagazineHtml, GENERATOR_VERSION } from './render';
lib/html-doc/generate.ts:6:import { writeModelEnvelope } from './model-store';
lib/html-doc/generate.ts:45:  // Persist the model so future style changes can re-render offline (no Gemini). `sourceSections`
lib/html-doc/generate.ts:50:  await writeModelEnvelope(principal, base, {
lib/html-doc/generate.ts:53:    sourceSections: parsed.sections.map((s) => s.title),
lib/html-doc/generate.ts:54:    generatorVersion: GENERATOR_VERSION,
lib/html-doc/generate.ts:58:    // filename-hash would never match and every synced companion would be deleted.
lib/html-doc/build-doc-html.ts:5:import { GENERATOR_VERSION } from './render';
lib/html-doc/build-doc-html.ts:7:import { readModelEnvelope } from './model-store';
lib/html-doc/build-doc-html.ts:9:import { parseDugSections } from '../dig/companion-doc';
lib/html-doc/build-doc-html.ts:56:    if (cachedVersion === GENERATOR_VERSION) return { ok: true, html: cachedHtml };
lib/html-doc/build-doc-html.ts:124:  const envelope = await readModelEnvelope(getPrincipal(outputFolder), base);
lib/html-doc/serve-doc.ts:5:import { GENERATOR_VERSION } from './constants';
lib/html-doc/serve-doc.ts:6:import { writeModelEnvelope } from './model-store';
lib/html-doc/serve-doc.ts:88:  // The model uses writeModelEnvelope (plain `put` → `upload(upsert:true)`), NOT staged→promote: a
lib/html-doc/serve-doc.ts:103:    await writeModelEnvelope(principal, base, {
lib/html-doc/serve-doc.ts:106:      sourceSections: titles,
lib/html-doc/serve-doc.ts:107:      generatorVersion: GENERATOR_VERSION,
tests/lib/html-doc/render-dig-deeper.captions.test.ts:7:import type { DugSection } from '@/lib/dig/companion-doc';
tests/lib/storage/supabase-metadata-store.test.ts:515:    const client = buildMockClient({ userId: 'owner-uuid', errors: { 'playlists.delete': 'db down' } });
tests/lib/storage/supabase-metadata-store.test.ts:526:    const client = buildMockClient({ errors: { 'playlists.maybeSingle': 'DB error' } });
tests/lib/storage/supabase-metadata-store.test.ts:534:      errors: { 'rpc.claim_video_slot': 'rpc failed' },
tests/lib/dig/dig-section.test.ts:5:// Partial mock: stub only generateDig; keep the REAL DIG_GENERATOR_VERSION const (it is exported
tests/lib/dig/dig-section.test.ts:13:jest.mock('../../../lib/dig/companion-doc');
tests/lib/dig/dig-section.test.ts:23:import * as companion from '../../../lib/dig/companion-doc';
tests/lib/dig/dig-section.test.ts:41:  jest.mocked(companion.upsertDugSection).mockResolvedValue(undefined as any);
tests/lib/dig/dig-section.test.ts:48:  expect(jest.mocked(companion.upsertDugSection)).toHaveBeenCalled();
tests/lib/dig/dig-section.test.ts:58:  expect(jest.mocked(companion.upsertDugSection)).not.toHaveBeenCalled();
tests/lib/dig/dig-section.test.ts:65:  expect(jest.mocked(companion.upsertDugSection)).not.toHaveBeenCalled();
tests/lib/html-doc/model-store.test.ts:5:import { writeModelEnvelope, readModelEnvelope, type ModelEnvelope } from '../../../lib/html-doc/model-store';
tests/lib/html-doc/model-store.test.ts:15:  sourceSections: ['The Foundation'],
tests/lib/html-doc/model-store.test.ts:34:    await writeModelEnvelope(principal, BASE, ENVELOPE);
tests/lib/html-doc/model-store.test.ts:37:    expect(await readModelEnvelope(principal, BASE)).toEqual(ENVELOPE);
tests/lib/html-doc/model-store.test.ts:41:    await writeModelEnvelope(principal, BASE, ENVELOPE);
tests/lib/html-doc/model-store.test.ts:48:    expect(await readModelEnvelope(principal, 'missing')).toBeNull();
tests/lib/html-doc/model-store.test.ts:57:    expect(await readModelEnvelope(principal, 'bad')).toBeNull();
tests/lib/html-doc/model-store.test.ts:65:    const bad = { sourceMd: 'x.md', generatedAt: 'now', sourceSections: ['s'], model: { sections: [{ lead: 'l', bullets: [] }] } };
tests/lib/html-doc/model-store.test.ts:67:    expect(await readModelEnvelope(principal, 'bad2')).toBeNull();
tests/lib/html-doc/model-store.test.ts:74:      sourceMd: 'a-title.md', generatedAt: 'now', sourceSections: ['s'],
tests/lib/html-doc/model-store.test.ts:77:    await expect(writeModelEnvelope(principal, BASE, invalid)).rejects.toThrow();
tests/lib/html-doc/model-store.test.ts:84:    await writeModelEnvelope(principal, BASE, ENVELOPE, fakeBlobStore);
tests/lib/html-doc/model-store.test.ts:100:    const result = await readModelEnvelope(principal, BASE, fakeBlobStore);
tests/lib/dig/cloud/dig-blob-key.test.ts:2:import { DIG_GENERATOR_VERSION } from '@/lib/dig/generate';
tests/lib/dig/cloud/dig-blob-key.test.ts:5:  expect(digSectionKey('0007_intro', 132)).toBe(`dig/0007_intro/132.r${DIG_GENERATOR_VERSION}.md`);
tests/lib/dig/cloud/dig-blob-key.test.ts:8:  expect(digJobVersion()).toBe(`dig-${DIG_GENERATOR_VERSION}`);
tests/lib/dig/cloud/enqueue-dig-core.test.ts:63:it('maps guardrail errors: quota→429, cap→503, too_long→400', async () => {
lib/html-doc/read-model.ts:4:import { GENERATOR_VERSION } from './constants';
lib/html-doc/read-model.ts:5:import { readModelEnvelope } from './model-store';
lib/html-doc/read-model.ts:13:  envelope: { sourceSections: string[] },
lib/html-doc/read-model.ts:16:  return envelope.sourceSections.length === titles.length &&
lib/html-doc/read-model.ts:17:    envelope.sourceSections.every((t, i) => t === titles[i]);
lib/html-doc/read-model.ts:20:export function isFresh(
lib/html-doc/read-model.ts:21:  envelope: { sourceSections: string[]; generatorVersion?: string },
lib/html-doc/read-model.ts:24:  return sameTitles(envelope, titles) && envelope.generatorVersion === GENERATOR_VERSION;
lib/html-doc/read-model.ts:36:  const existing = await readModelEnvelope(principal, base, blobStore);
lib/html-doc/read-model.ts:37:  if (existing && isFresh(existing, titles)) return { status: 'ok', model: existing.model };
lib/html-doc/read-model.ts:51:  const existing = await readModelEnvelope(principal, base, blobStore);
lib/html-doc/render-dig-deeper.ts:14:import type { DugSection } from '../dig/companion-doc';
tests/lib/html-doc/generate.test.ts:140:  expect(envelope.sourceSections).toEqual(['First', 'Conclusion']);
tests/lib/html-doc/dig-merge.test.ts:11:import type { DugSection } from '../../../lib/dig/companion-doc';
tests/lib/html-doc/dig-merge.test.ts:12:import { DIG_GENERATOR_VERSION } from '../../../lib/dig/generate';
tests/lib/html-doc/dig-merge.test.ts:44:function makeEnvelope(sourceSections: string[], modelSections: { lead: string; bullets: { label: string; text: string }[] }[]): ModelEnvelope {
tests/lib/html-doc/dig-merge.test.ts:48:    sourceSections,
tests/lib/html-doc/dig-merge.test.ts:60:function makeDug(sectionId: number, title: string, startSec?: number, genVersion = DIG_GENERATOR_VERSION): DugSection {
tests/lib/html-doc/dig-merge.test.ts:159:      genVersion: DIG_GENERATOR_VERSION,
tests/lib/html-doc/dig-merge.test.ts:167:      genVersion: DIG_GENERATOR_VERSION,
tests/lib/html-doc/dig-merge.test.ts:348:  it('returns gist=null for all sections when titles do not match sourceSections', () => {
tests/lib/html-doc/dig-merge.test.ts:384:    // But sourceSections must match summaryTitles — if they match, model.sections length
tests/lib/html-doc/dig-merge.test.ts:386:    // For this test: sourceSections matches, but we'll use a model with fewer sections
tests/lib/html-doc/dig-merge.test.ts:388:    // Actually: sameTitles compares parsedTitles vs sourceSections, not model.sections.
tests/lib/html-doc/dig-merge.test.ts:389:    // If sourceSections matches but model.sections is shorter, overflow sections get null.
tests/lib/html-doc/dig-merge.test.ts:393:    // Manually construct envelope where sourceSections matches but model.sections is shorter
tests/lib/html-doc/dig-merge.test.ts:397:      sourceSections: summaryTitles, // matches all 4 summary titles
tests/lib/html-doc/dig-merge.test.ts:428:      sourceSections: ['Only Section'],
tests/lib/html-doc/dig-merge.test.ts:524:      genVersion: DIG_GENERATOR_VERSION,
tests/lib/html-doc/dig-merge.test.ts:532:      genVersion: DIG_GENERATOR_VERSION,
tests/lib/html-doc/dig-merge.test.ts:586:      [makeDug(0, 'Intro', 0, DIG_GENERATOR_VERSION - 1)],
tests/lib/html-doc/dig-merge.test.ts:595:      [makeDug(0, 'Intro', 0, DIG_GENERATOR_VERSION)],
tests/lib/html-doc/dig-merge.test.ts:622:    const dug = [makeDug(180, 'Core Concepts', 180, DIG_GENERATOR_VERSION - 1)];
tests/lib/html-doc/dig-merge.test.ts:635:    const dug = [makeDug(180, 'Core Concepts', 180, DIG_GENERATOR_VERSION)];
tests/lib/html-doc/serve-doc-mapping.test.ts:9:import { GENERATOR_VERSION } from '@/lib/html-doc/render';
tests/lib/html-doc/serve-doc-mapping.test.ts:60:    sourceSections: ['Intro'], // must match parsed().sections titles for isFresh() to accept it
tests/lib/html-doc/serve-doc-mapping.test.ts:61:    generatorVersion: GENERATOR_VERSION,
tests/lib/html-doc/serve-doc-mapping.test.ts:112:    expect(blobStore.putMock).toHaveBeenCalledTimes(1); // writeModelEnvelope persisted the new model
tests/lib/html-doc/rerender.test.ts:6:import { writeModelEnvelope } from '../../../lib/html-doc/model-store';
tests/lib/html-doc/rerender.test.ts:44:function envelope(model = MODEL, sourceSections = SECTIONS) {
tests/lib/html-doc/rerender.test.ts:45:  return { sourceMd: 'a-title.md', generatedAt: 'now', sourceSections, model };
tests/lib/html-doc/rerender.test.ts:77:    await writeModelEnvelope(localPrincipal(dir), 'a-title', envelope());
tests/lib/html-doc/rerender.test.ts:91:    await writeModelEnvelope(localPrincipal(dir), 'a-title', envelope());
tests/lib/html-doc/rerender.test.ts:117:    await writeModelEnvelope(localPrincipal(dir), 'a-title', envelope());
tests/lib/html-doc/rerender.test.ts:124:    await writeModelEnvelope(localPrincipal(dir), 'a-title', envelope());
tests/lib/html-doc/rerender.test.ts:130:    await writeModelEnvelope(localPrincipal(dir), 'a-title', envelope());
tests/lib/html-doc/rerender.test.ts:137:    await writeModelEnvelope(localPrincipal(dir), 'a-title', envelope(MODEL, ['First', 'Renamed Conclusion']));
tests/lib/html-doc/rerender.test.ts:148:    await writeModelEnvelope(localPrincipal(dir), 'a-title', envelope({ sections: [MODEL.sections[0]] }, oneTitle));
tests/lib/html-doc/rerender.test.ts:162:    await writeModelEnvelope(localPrincipal(dir), 'a-title', envelope());
tests/lib/html-doc/rerender.test.ts:180:    await writeModelEnvelope(localPrincipal(dir), 'a-title', envelope());
tests/lib/html-doc/rerender.test.ts:199:    await writeModelEnvelope(localPrincipal(dir), 'a-title', envelope());
tests/lib/html-doc/rerender.test.ts:208:    await writeModelEnvelope(localPrincipal(dir), 'a-title', envelope());
tests/lib/html-doc/rerender.test.ts:210:    await writeModelEnvelope(localPrincipal(dir), 'b-title', { sourceMd: 'b-title.md', generatedAt: 'now', sourceSections: ['x'], model: MODEL });
tests/lib/html-doc/rerender.test.ts:222:    await writeModelEnvelope(localPrincipal(dir), 'a-title', envelope());
tests/lib/html-doc/rerender.test.ts:223:    await writeModelEnvelope(localPrincipal(dir), 'b-title', envelope());
tests/lib/dig/cloud/load-dig-for-serve.test.ts:7:import { DIG_GENERATOR_VERSION } from '@/lib/dig/generate';
tests/lib/dig/cloud/load-dig-for-serve.test.ts:21:const V = DIG_GENERATOR_VERSION;
tests/lib/dig/cloud/load-dig-for-serve.test.ts:49:    (modelStore.readModelEnvelope as jest.Mock).mockResolvedValue(null);
tests/lib/dig/cloud/load-dig-for-serve.test.ts:106:    (modelStore.readModelEnvelope as jest.Mock).mockResolvedValue(null);
tests/lib/dig/cloud/load-dig-for-serve.test.ts:118:    (modelStore.readModelEnvelope as jest.Mock).mockResolvedValue(null);
lib/html-doc/batch.ts:8:import { parseDugSections } from '../dig/companion-doc';
lib/html-doc/batch.ts:10:import { DIG_GENERATOR_VERSION } from '../dig/generate';
lib/html-doc/batch.ts:19:/** Dig-eligible sections (have a timeRange) that are missing or stale in the companion doc. */
lib/html-doc/batch.ts:34:  // Use the INDEXED companion path when present (it may differ from the derived name); else derive.
lib/html-doc/batch.ts:35:  const companionRel = video.digDeeperMd ?? `${path.basename(video.summaryMd, '.md')}-dig-deeper.md`;
lib/html-doc/batch.ts:38:    const content = await fs.readFile(path.join(outputFolder, companionRel), 'utf8');
lib/html-doc/batch.ts:40:  } catch { /* no companion yet → all eligible are missing */ }
lib/html-doc/batch.ts:44:    return gv === undefined || gv < DIG_GENERATOR_VERSION;
lib/html-doc/dig-merge.ts:2: * dig-merge.ts — pure function that merges GIST (model) + DUG (companion) data
lib/html-doc/dig-merge.ts:8: *   - GIST trusted only if: envelope non-null AND sameTitles(parsedTitles, envelope.sourceSections)
lib/html-doc/dig-merge.ts:20:import type { DugSection } from '../dig/companion-doc';
lib/html-doc/dig-merge.ts:22:import { DIG_GENERATOR_VERSION } from '../dig/generate';
lib/html-doc/dig-merge.ts:44: * Merge summary GIST (model envelope) and DUG (companion-doc sections) into a
lib/html-doc/dig-merge.ts:50: * @param dug      Dug sections from the companion doc (may be empty).
lib/html-doc/dig-merge.ts:62:    envelope !== null && sameTitles(parsedTitles, envelope.sourceSections);
lib/html-doc/dig-merge.ts:104:        isStale_ = matched.genVersion < DIG_GENERATOR_VERSION;
lib/html-doc/dig-merge.ts:154:    ms.isStale = matched.genVersion < DIG_GENERATOR_VERSION;
tests/lib/dig/cloud/write-dig-section-blob.test.ts:2:import { DIG_GENERATOR_VERSION } from '@/lib/dig/generate';
tests/lib/dig/cloud/write-dig-section-blob.test.ts:32:  expect(key).toBe(`dig/0007_intro/132.r${DIG_GENERATOR_VERSION}.md`);
tests/lib/dig/cloud/write-dig-section-blob.test.ts:39:  expect(written).toContain(`genVersion: ${DIG_GENERATOR_VERSION}`);
tests/lib/html-doc/render-dig-deeper-readonly.test.ts:3:import type { DugSection } from '@/lib/dig/companion-doc';
tests/lib/html-doc/render.test.ts:1:import { renderMagazineHtml, GENERATOR_VERSION } from '../../../lib/html-doc/render';
tests/lib/html-doc/render.test.ts:33:    expect(html).toContain(`<meta name="generator" content="${GENERATOR_VERSION}">`);
tests/lib/html-doc/render-share.test.ts:6:  sections: [{ title: 'S1', prose: 'p', timestamp: null }], sourceSectionsRaw: [],
tests/lib/html-doc/read-model.test.ts:1:// NOTE on mocking technique: the plan's Step 1 draft used `jest.spyOn(modelStore, 'readModelEnvelope')`
tests/lib/html-doc/read-model.test.ts:7:import { readFreshMagazineModel, isFresh, sameTitles, readTitleStableModel } from '@/lib/html-doc/read-model';
tests/lib/html-doc/read-model.test.ts:8:import { GENERATOR_VERSION } from '@/lib/html-doc/constants';
tests/lib/html-doc/read-model.test.ts:11:jest.mock('@/lib/html-doc/model-store', () => ({ readModelEnvelope: jest.fn() }));
tests/lib/html-doc/read-model.test.ts:12:import { readModelEnvelope } from '@/lib/html-doc/model-store';
tests/lib/html-doc/read-model.test.ts:13:const mockReadModelEnvelope = readModelEnvelope as jest.Mock;
tests/lib/html-doc/read-model.test.ts:21:  return { sourceMd: 'x.md', generatedAt: 'now', sourceSections: ['A', 'B'],
tests/lib/html-doc/read-model.test.ts:22:    generatorVersion: GENERATOR_VERSION, model: fakeModel, ...over };
tests/lib/html-doc/read-model.test.ts:25:describe('isFresh', () => {
tests/lib/html-doc/read-model.test.ts:27:    expect(isFresh(envelope(), titles)).toBe(true);
tests/lib/html-doc/read-model.test.ts:30:    expect(isFresh(envelope({ sourceSections: ['A', 'C'] }), titles)).toBe(false);
tests/lib/html-doc/read-model.test.ts:33:    expect(isFresh(envelope({ generatorVersion: 'old' }), titles)).toBe(false);
tests/lib/html-doc/read-model.test.ts:65:    expect(sameTitles(envelope({ sourceSections: ['B', 'A'] }), titles)).toBe(false);
tests/lib/html-doc/read-model.test.ts:66:    expect(sameTitles(envelope({ sourceSections: ['A'] }), titles)).toBe(false);
tests/lib/html-doc/read-model.test.ts:80:    mockReadModelEnvelope.mockResolvedValue(envelope({ sourceSections: ['X', 'B'], generatorVersion: 'OLD' }));
tests/lib/html-doc/build-doc-html.test.ts:5:import { GENERATOR_VERSION } from '@/lib/html-doc/render';
tests/lib/html-doc/build-doc-html.test.ts:29:      `<!DOCTYPE html><head><meta name="generator" content="${GENERATOR_VERSION}"></head><title>ok</title>`);
tests/lib/html-doc/render-dig-deeper.size.test.ts:7:import type { DugSection } from '@/lib/dig/companion-doc';
tests/lib/html-doc/batch.test.ts:5:jest.mock('../../../lib/dig/companion-doc');
tests/lib/html-doc/batch.test.ts:12:import * as companion from '../../../lib/dig/companion-doc';
tests/lib/html-doc/batch.test.ts:15:import { DIG_GENERATOR_VERSION } from '../../../lib/dig/generate';
tests/lib/html-doc/batch.test.ts:123:  jest.mocked(companion.parseDugSections).mockReturnValue([]); // nothing dug yet
tests/lib/html-doc/batch.test.ts:144:    jest.mocked(companion.parseDugSections).mockReturnValue([
tests/lib/html-doc/batch.test.ts:145:      { sectionId: 10, startSec: 10, title: 'A', bodyMarkdown: '', generatedAt: '', genVersion: DIG_GENERATOR_VERSION }, // current → skip
tests/lib/html-doc/render-dig-deeper.test.ts:7:import type { DugSection } from '@/lib/dig/companion-doc';
tests/lib/html-doc/render-dig-deeper.test.ts:8:import { DIG_GENERATOR_VERSION } from '@/lib/dig/generate';
tests/lib/html-doc/render-dig-deeper.test.ts:47:function makeDugWithBody(startSec: number, bodyMarkdown: string, genVersion = DIG_GENERATOR_VERSION): DugSection {
tests/lib/html-doc/render-dig-deeper.test.ts:459:    sourceSections: ['Introduction', 'Main Content'],
tests/lib/html-doc/render-dig-deeper.test.ts:491:    genVersion: DIG_GENERATOR_VERSION,
tests/lib/html-doc/render-dig-deeper.test.ts:637:        sourceSections: ['Conclusion'],
tests/lib/html-doc/render-dig-deeper.test.ts:729:        genVersion: DIG_GENERATOR_VERSION,
tests/lib/html-doc/render-dig-deeper.test.ts:983:    // STALE: genVersion = DIG_GENERATOR_VERSION - 1
tests/lib/html-doc/render-dig-deeper.test.ts:984:    // FRESH: genVersion = DIG_GENERATOR_VERSION
tests/lib/html-doc/render-dig-deeper.test.ts:988:      const staleDug = makeDugWithBody(312, '## Test Section\n\nStale content.', DIG_GENERATOR_VERSION - 1);
tests/lib/html-doc/render-dig-deeper.test.ts:995:      const staleDug = makeDugWithBody(312, '## Test Section\n\nStale content.', DIG_GENERATOR_VERSION - 1);
tests/lib/html-doc/render-dig-deeper.test.ts:1002:      const freshDug = makeDugWithBody(312, '## Test Section\n\nFresh content.', DIG_GENERATOR_VERSION);
tests/lib/html-doc/render-dig-deeper.test.ts:1010:      const freshDug = makeDugWithBody(312, '## Test Section\n\nFresh content.', DIG_GENERATOR_VERSION);
tests/lib/html-doc/render-dig-deeper.test.ts:1017:      const staleDug = makeDugWithBody(312, '## Test Section\n\nStale content.', DIG_GENERATOR_VERSION - 1);
tests/lib/html-doc/render-dig-deeper.test.ts:1027:      const staleDug = makeDugWithBody(312, '## Test Section\n\nStale content.', DIG_GENERATOR_VERSION - 1);
tests/lib/html-doc/render-dig-deeper.test.ts:1099:    generatedAt: 'g', genVersion: DIG_GENERATOR_VERSION,

codex
The core implementation is small: `decideCompanion` is still pure data selection, and `companionTransfer` now returns the companion write error instead of throwing. I’m checking the model-store write semantics next, because the partial-write question depends on whether `put` is overwrite/upsert and whether `readModelEnvelope` rejects corrupt/truncated JSON.
exec
/bin/bash -lc "nl -ba lib/html-doc/model-store.ts | sed -n '1,140p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	import { z } from 'zod';
     2	import { MagazineModelSchema } from './types';
     3	import { localBlobStore } from '@/lib/storage/local/local-blob-store';
     4	import type { BlobStore, ReadOnlyBlobStore } from '@/lib/storage/blob-store';
     5	import type { Principal } from '@/lib/storage/principal';
     6	
     7	/**
     8	 * The persisted summary-model file: the Gemini transform output plus provenance.
     9	 * `sourceSections` is the section titles the model was built against — the drift guard the
    10	 * re-render path compares the current .md's section titles against.
    11	 * `generatorVersion` is optional so pre-1F-a local envelopes (written before this field existed)
    12	 * still parse; the cloud freshness gate requires it to `=== GENERATOR_VERSION`.
    13	 */
    14	export const ModelEnvelopeSchema = z
    15	  .object({
    16	    sourceMd: z.string().min(1),
    17	    generatedAt: z.string().min(1),
    18	    sourceSections: z.array(z.string()),
    19	    generatorVersion: z.string().min(1).optional(),
    20	    model: MagazineModelSchema,
    21	    // Stage 3 (§4.2): MD-body-only digest of the MD this model was generated from.
    22	    sourceMdHash: z.string().optional(),
    23	  });
    24	  // NOTE: .strict() intentionally removed — a new-writer envelope with sourceMdHash
    25	  // must not make an old reader's readModelEnvelope return null (§5.7 round-5 M-2).
    26	
    27	export type ModelEnvelope = z.infer<typeof ModelEnvelopeSchema>;
    28	
    29	const MODEL_KEY = (base: string) => `models/${base}.json`;
    30	
    31	function serialize(envelope: ModelEnvelope): Buffer {
    32	  ModelEnvelopeSchema.parse(envelope); // fail loud on an invalid model
    33	  return Buffer.from(`${JSON.stringify(envelope, null, 2)}\n`, 'utf-8');
    34	}
    35	
    36	/**
    37	 * The single model writer for BOTH the local generate path and the cloud serve path.
    38	 * `put` maps to Supabase `upload(upsert:true)` (atomic per object), so a re-generated model on
    39	 * drift / `generatorVersion` bump OVERWRITES the prior blob — the cache self-heals rather than
    40	 * getting stuck on a stale envelope. (The staged→promote protocol is create-if-absent and stays
    41	 * on the BlobStore for the worker's multi-blob MD commit — it is NOT used for the model.)
    42	 */
    43	export async function writeModelEnvelope(
    44	  principal: Principal,
    45	  base: string,
    46	  envelope: ModelEnvelope,
    47	  blobStore: BlobStore = localBlobStore,
    48	): Promise<void> {
    49	  await blobStore.put(principal, MODEL_KEY(base), serialize(envelope), 'application/json');
    50	}
    51	
    52	/** Read + validate. Returns null if absent, unparseable, or schema-invalid. */
    53	export async function readModelEnvelope(
    54	  principal: Principal,
    55	  base: string,
    56	  blobStore: ReadOnlyBlobStore = localBlobStore,
    57	): Promise<ModelEnvelope | null> {
    58	  const bytes = await blobStore.get(principal, MODEL_KEY(base));
    59	  if (!bytes) return null;
    60	  let json: unknown;
    61	  try {
    62	    json = JSON.parse(bytes.toString('utf-8'));
    63	  } catch {
    64	    console.warn(`[model-store] malformed JSON in models/${base}.json — ignoring`);
    65	    return null;
    66	  }
    67	  const parsed = ModelEnvelopeSchema.safeParse(json);
    68	  if (!parsed.success) {
    69	    console.warn(`[model-store] models/${base}.json failed schema validation — ignoring`);
    70	    return null;
    71	  }
    72	  return parsed.data;
    73	}

exec
/bin/bash -lc "nl -ba lib/storage/blob-store.ts lib/storage/local/local-blob-store.ts lib/storage/supabase/supabase-blob-store.ts | sed -n '1,220p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
usage: nl [-p] [-b type] [-d delim] [-f type] [-h type] [-i incr] [-l num]
          [-n format] [-s sep] [-v startnum] [-w width] [file]

exec
/bin/bash -lc "nl -ba lib/html-doc/read-model.ts | sed -n '1,90p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	import type { MagazineModel } from './types';
     2	import type { Principal } from '@/lib/storage/principal';
     3	import type { ReadOnlyBlobStore } from '@/lib/storage/blob-store';
     4	import { GENERATOR_VERSION } from './constants';
     5	import { readModelEnvelope } from './model-store';
     6	
     7	// GENERATE-FREE LEAF (spec D13/B18c): this module and its entire import graph must never
     8	// reach @/lib/gemini, @/lib/gemini-cost, or serve-doc. Importing it into the anonymous
     9	// /s/[token] route therefore cannot pull in the charging code. Enforced by tests/lib/share/
    10	// import-guard.test.ts (a jest grep guard; the repo has no ESLint).
    11	
    12	export function sameTitles(
    13	  envelope: { sourceSections: string[] },
    14	  titles: string[],
    15	): boolean {
    16	  return envelope.sourceSections.length === titles.length &&
    17	    envelope.sourceSections.every((t, i) => t === titles[i]);
    18	}
    19	
    20	export function isFresh(
    21	  envelope: { sourceSections: string[]; generatorVersion?: string },
    22	  titles: string[],
    23	): boolean {
    24	  return sameTitles(envelope, titles) && envelope.generatorVersion === GENERATOR_VERSION;
    25	}
    26	
    27	/** Read-only, generation-free: returns the cached model iff present AND fresh; otherwise
    28	 *  not_ready. Never reserves spend or generates a model (no charging RPC, no LLM call). */
    29	export async function readFreshMagazineModel(args: {
    30	  blobStore: ReadOnlyBlobStore;
    31	  principal: Principal;
    32	  base: string;
    33	  titles: string[];
    34	}): Promise<{ status: 'ok'; model: MagazineModel } | { status: 'not_ready' }> {
    35	  const { blobStore, principal, base, titles } = args;
    36	  const existing = await readModelEnvelope(principal, base, blobStore);
    37	  if (existing && isFresh(existing, titles)) return { status: 'ok', model: existing.model };
    38	  return { status: 'not_ready' };
    39	}
    40	
    41	/** Title-stable read (spec D5): returns the cached model iff the envelope exists AND its section
    42	 *  titles match `titles` (generator version may differ — the version-bump case). Positionally
    43	 *  coherent to render against current markdown. Never reserves/generates (pure blob read). */
    44	export async function readTitleStableModel(args: {
    45	  blobStore: ReadOnlyBlobStore;
    46	  principal: Principal;
    47	  base: string;
    48	  titles: string[];
    49	}): Promise<{ status: 'ok'; model: MagazineModel } | { status: 'none' }> {
    50	  const { blobStore, principal, base, titles } = args;
    51	  const existing = await readModelEnvelope(principal, base, blobStore);
    52	  if (existing && sameTitles(existing, titles)) return { status: 'ok', model: existing.model };
    53	  return { status: 'none' };
    54	}

exec
/bin/bash -lc "nl -ba lib/html-doc/constants.ts lib/html-doc/render.ts | sed -n '1,80p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
usage: nl [-p] [-b type] [-d delim] [-f type] [-h type] [-i incr] [-l num]
          [-n format] [-s sep] [-v startnum] [-w width] [file]

exec
/bin/bash -lc "rg -n \"runSync\\(|SyncReport|errors\\.|\\.errors|shareNeedsOwnerServe|process\\.exit|exitCode\" app lib tests scripts bin package.json -g '"'!node_modules'"'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 exited 2 in 0ms:
rg: bin: No such file or directory (os error 2)
scripts/repair-timestamps.ts:15:if (!folder) { console.error('Set --folder <outputFolder> or OUTPUT_FOLDER'); process.exit(1); }
scripts/repair-timestamps.ts:26:}).catch((e) => { console.error(e); process.exit(1); });
scripts/check-service-confinement.ts:113:    process.exit(1);
scripts/rerender-html.ts:18:  console.log(`[${outputFolder}] re-rendered ${t.rerendered}, skipped ${skipped}, errors ${t.errors}`);
scripts/rerender-html.ts:38:  process.exit(1);
scripts/rerender-html.ts:40:Promise.all(folders.map((folder) => run(folder))).catch((e) => { console.error(e); process.exit(1); });
scripts/backfill-playlist-titles.ts:9:  if (!apiKey) { console.error('YOUTUBE_API_KEY is not set'); process.exit(1); }
scripts/verify-gemini-release.ts:108:main().catch((e) => { console.error('\n[verify-gemini-release] fatal:', e); process.exit(1); });
scripts/fix-duplicate-summaries.ts:97:  process.exit(1);
scripts/cloud-sync.ts:4:// Supabase client into runSync() so a developer/operator can pull cloud changes into their local
scripts/cloud-sync.ts:68:  const report = await runSync(deps, args.playlistKey ? { playlistKey: args.playlistKey } : {});
scripts/cloud-sync.ts:70:  return report.errors.length ? 2 : 0;
scripts/cloud-sync.ts:74:  main(process.argv.slice(2)).then((code) => process.exit(code)).catch((e) => { console.error(e); process.exit(1); });
scripts/audit-summaries.ts:18:  process.exit(0);
scripts/audit-summaries.ts:31:  .finally(() => process.exit(0)); // read-only report tool — never gate on suspects or data errors
scripts/backfill-serial-prefix.ts:35:if (require.main === module) main().catch((e) => { console.error(e); process.exit(1); });
lib/gemini.ts:279:// share this single budget). Each attempt may still use generateJson's inner retries for hard errors.
scripts/audit-timestamps.ts:18:if (!folder) { console.error('Set --folder <outputFolder> or OUTPUT_FOLDER'); process.exit(1); }
scripts/audit-timestamps.ts:24:    process.exit(r.summaries.noTsStuck > 0 ? 1 : 0);
scripts/audit-timestamps.ts:26:  .catch((e) => { console.error(e); process.exit(1); });
lib/dev-logger.ts:95:    const logFile = path.join(logDir, 'dev-errors.log');
app/api/jobs/route.ts:79:    logError(`jobs:poll:${playlistId}`, err);   // never swallow: surface the real cause to console + dev-errors.log
lib/html-doc/rerender.ts:125:      tally.errors++;
tests/lib/dev-logger.test.ts:119:    const logPath = path.join(tmpDir, 'dev-errors.log');
tests/lib/dev-logger.test.ts:134:    expect(fs.existsSync(path.join(nestedDir, 'dev-errors.log'))).toBe(true);
tests/lib/dev-logger.test.ts:153:    const content = fs.readFileSync(path.join(tmpDir, 'dev-errors.log'), 'utf-8');
tests/lib/cloud-sync/companion.test.ts:20:const DELETE = { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
tests/lib/cloud-sync/companion.test.ts:22:const KEEP = (flag: boolean) => ({ kind: 'noop', shareNeedsOwnerServe: flag });
tests/lib/cloud-sync/companion.test.ts:101:    expect(decide(current('h1'), r)).not.toMatchObject({ shareNeedsOwnerServe: true });
tests/lib/html-doc/rerender.test.ts:216:    expect(tally.errors).toBe(0);
tests/lib/html-doc/rerender.test.ts:235:    expect(tally.errors).toBe(1);
lib/cloud-sync/companion.ts:20:/** H-R5-1 (round 5) — `shareNeedsOwnerServe` is now carried on `noop` too, because it is a SEPARATE
lib/cloud-sync/companion.ts:27:  | { kind: 'deleteReceiverModel'; shareNeedsOwnerServe: true }
lib/cloud-sync/companion.ts:28:  | { kind: 'noop'; shareNeedsOwnerServe: boolean };
lib/cloud-sync/companion.ts:86:      return { kind: 'noop', shareNeedsOwnerServe: false }; // receiver already fresh — do not write
lib/cloud-sync/companion.ts:91:    return { kind: 'noop', shareNeedsOwnerServe: false }; // neither is current — both need a re-serve
lib/cloud-sync/companion.ts:100:  if (receiverMatch) return { kind: 'noop', shareNeedsOwnerServe: false };
lib/cloud-sync/companion.ts:113:  //  - REPORT on doubt. shareNeedsOwnerServe is a report-only count (§10 row 7): "these shares may
lib/cloud-sync/companion.ts:120:  if (provablyStale) return { kind: 'deleteReceiverModel', shareNeedsOwnerServe: true };
lib/cloud-sync/companion.ts:121:  return { kind: 'noop', shareNeedsOwnerServe: true };
lib/cloud-sync/sync-run.ts:4:// T11) into runSync(deps, opts?), reconciling every union video across the local replica and the
lib/cloud-sync/sync-run.ts:45:export interface SyncReport {
lib/cloud-sync/sync-run.ts:48:  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
lib/cloud-sync/sync-run.ts:384: *  is surfaced in report.errors by the caller without aborting the per-video flow. */
lib/cloud-sync/sync-run.ts:387:): Promise<{ shareNeedsOwnerServe: boolean; error?: string }> {
lib/cloud-sync/sync-run.ts:388:  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
lib/cloud-sync/sync-run.ts:403:    // visible; the error is returned so it still surfaces in report.errors.
lib/cloud-sync/sync-run.ts:406:      return { shareNeedsOwnerServe: false };
lib/cloud-sync/sync-run.ts:408:      return { shareNeedsOwnerServe: true, error: `companion model ship failed: ${e?.message ?? String(e)}` };
lib/cloud-sync/sync-run.ts:414:  if (decision.kind === 'noop') return { shareNeedsOwnerServe: decision.shareNeedsOwnerServe };
lib/cloud-sync/sync-run.ts:417:  return { shareNeedsOwnerServe: true };
lib/cloud-sync/sync-run.ts:488:export async function runSync(
lib/cloud-sync/sync-run.ts:490:): Promise<SyncReport> {
lib/cloud-sync/sync-run.ts:492:  const report: SyncReport = {
lib/cloud-sync/sync-run.ts:495:    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
lib/cloud-sync/sync-run.ts:581:        //    Throwing per-video is caught below, surfaces in report.errors, and advances NO baseline,
lib/cloud-sync/sync-run.ts:641:          if (c.shareNeedsOwnerServe) report.shareNeedsOwnerServe += 1;
lib/cloud-sync/sync-run.ts:644:          if (c.error) report.errors.push({ videoId: id, message: c.error });
lib/cloud-sync/sync-run.ts:652:        report.errors.push({ videoId: id, message: e?.message ?? String(e) }); // Behaviors #11/#13
tests/integration/cloud-sync/sync-run.int.test.ts:29:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/sync-run.int.test.ts:51:    await runSync(ctx.syncDeps());
tests/integration/cloud-sync/sync-run.int.test.ts:63:    const report = await runSync(ctx.syncDeps({ failCloudPromote: true }));
tests/integration/cloud-sync/sync-run.int.test.ts:66:    expect(report.errors.length).toBeGreaterThanOrEqual(1);
tests/integration/cloud-sync/e2e.int.test.ts:95:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:138:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:160:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:178:    await runSync(ctx.syncDeps()); // hydrate empty local from cloud
tests/integration/cloud-sync/e2e.int.test.ts:200:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:229:    await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:238:  it('row 7: a transferred summary with no matching model flags shareNeedsOwnerServe', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:248:    // absence, so this takes the `noop + shareNeedsOwnerServe: true` path (H-R5-1), NOT a delete.
tests/integration/cloud-sync/e2e.int.test.ts:249:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:250:    expect(report.shareNeedsOwnerServe).toBeGreaterThanOrEqual(1);
tests/integration/cloud-sync/e2e.int.test.ts:259:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:272:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:303:    await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:318:    const r1 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:325:    const r2 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:338:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:339:    expect(report.errors).toEqual([]);
tests/integration/cloud-sync/e2e.int.test.ts:351:    await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:362:    const r1 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:368:    const r2 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:381:    const report = await runSync(ctx.syncDeps({ failCloudPromote: true }));
tests/integration/cloud-sync/e2e.int.test.ts:383:    expect(report.errors.length).toBeGreaterThanOrEqual(1);
tests/integration/cloud-sync/e2e.int.test.ts:401:    const r1 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:408:    const r2 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:432:    const r1 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:451:    const r2 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:473:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:475:    expect(report.errors.some((e) => e.videoId === ctx.videoId)).toBe(true);
tests/integration/cloud-sync/e2e.int.test.ts:484:    const r2 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:485:    expect(r2.errors.some((e) => e.videoId === ctx.videoId)).toBe(true);
tests/integration/cloud-sync/e2e.int.test.ts:506:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:535:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:563:    const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:605:      const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:608:      expect(report.errors.some((e) => e.videoId === ctx.videoId)).toBe(true);
tests/integration/cloud-sync/e2e.int.test.ts:640:      const report = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:642:      expect(report.errors.some((e) => e.videoId === ctx.videoId)).toBe(true);
tests/integration/cloud-sync/e2e.int.test.ts:697:    const r1 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:701:    expect(r1.shareNeedsOwnerServe).toBe(1);                      // owner must re-serve the share
tests/integration/cloud-sync/e2e.int.test.ts:706:    const r2 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:707:    expect(r2.shareNeedsOwnerServe).toBe(0);
tests/integration/cloud-sync/e2e.int.test.ts:733:    const r1 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:739:    expect(r1.shareNeedsOwnerServe).toBe(0);                         // no false "share is stale"
tests/integration/cloud-sync/e2e.int.test.ts:742:    const r2 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:743:    expect(r2.shareNeedsOwnerServe).toBe(0);
tests/integration/cloud-sync/e2e.int.test.ts:774:    const r1 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:780:    expect(r1.shareNeedsOwnerServe).toBe(0);
tests/integration/cloud-sync/e2e.int.test.ts:783:    const r2 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:784:    expect(r2.shareNeedsOwnerServe).toBe(0);
tests/integration/cloud-sync/e2e.int.test.ts:817:    const r1 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:825:    expect(r1.shareNeedsOwnerServe).toBe(0);                     // the share still renders
tests/integration/cloud-sync/e2e.int.test.ts:852:    const r1 = await runSync(ctx.syncDeps({ failCloudModelPut: true }));
tests/integration/cloud-sync/e2e.int.test.ts:861:    expect(r1.shareNeedsOwnerServe).toBe(1);
tests/integration/cloud-sync/e2e.int.test.ts:862:    expect(r1.errors.some((e) => e.videoId === ctx.videoId)).toBe(true); // failure stays visible
tests/integration/cloud-sync/e2e.int.test.ts:888:    const r1 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:890:    expect(r1.errors).toEqual([]);                       // no permanent per-run failure
tests/integration/cloud-sync/e2e.int.test.ts:899:    const r2 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:900:    expect(r2.errors).toEqual([]);
tests/integration/cloud-sync/e2e.int.test.ts:931:    const r1 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:938:    await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:968:    const r1 = await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:972:    await runSync(ctx.syncDeps());
tests/integration/cloud-sync/e2e.int.test.ts:996:    await runSync(ctx.syncDeps());
tests/integration/helpers/cloud.ts:63:  /** Build the SyncDeps for a runSync() call. failCloudPromote wraps the cloud blob store so its

codex
One caller detail matters: the CLI currently exits non-zero for any `report.errors.length`, so this change still makes injected companion ship failure a CLI failure even though the sync baseline advances. That matches “surface the fault” rather than “abort the per-video flow”; I’m checking whether any tests assume `errors` means no baseline write.
exec
/bin/bash -lc "nl -ba scripts/cloud-sync.ts | sed -n '1,100p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	// scripts/cloud-sync.ts
     2	//
     3	// Stage 3 Cloud Sync (§9) — the local CLI entrypoint. Wires the authenticated USER-session
     4	// Supabase client into runSync() so a developer/operator can pull cloud changes into their local
     5	// replica (and vice versa) without ever touching the service-role key. `login`/`logout` manage a
     6	// long-lived refresh token via lib/cloud-sync/auth's file-backed TokenStore; `sync` (the default)
     7	// reconciles every union playlist, or one via `--playlist <key>`.
     8	//
     9	// Data-root convention: this project's LOCAL playlist roots are NOT an env var — they are
    10	// lib/settings-store.ts's settings.json (`baseOutputFolder` when set, the parent directory that
    11	// holds every playlist subfolder; falling back to the single-playlist `outputFolder`, which itself
    12	// falls back to the OUTPUT_FOLDER env var when settings.json is absent). This mirrors exactly what
    13	// app/api/resolve-folder/route.ts reads, and what lib/cloud-sync/registry.ts's
    14	// discoverLocalPlaylists() expects: a root whose subdirectories are playlist folders. An optional
    15	// CLOUD_SYNC_DATA_ROOTS override (colon-separated) is supported for scripting/testing convenience.
    16	import { getAuthedClient, signIn, signOut, NoSessionError } from '@/lib/cloud-sync/auth';
    17	import { runSync, type SyncDeps } from '@/lib/cloud-sync/sync-run';
    18	import { SupabaseMetadataStore } from '@/lib/storage/supabase/supabase-metadata-store';
    19	import { SupabaseBlobStore } from '@/lib/storage/supabase/supabase-blob-store';
    20	import { ARTIFACTS_BUCKET } from '@/lib/supabase/storage-env';
    21	import { localMetadataStore } from '@/lib/storage/local/local-metadata-store';
    22	import { localBlobStore } from '@/lib/storage/local/local-blob-store';
    23	import { readSettings } from '@/lib/settings-store';
    24	
    25	export interface ParsedArgs { cmd: 'sync' | 'login' | 'logout'; playlistKey?: string; }
    26	
    27	export function parseArgs(argv: string[]): ParsedArgs {
    28	  if (argv[0] === 'login') return { cmd: 'login' };
    29	  if (argv[0] === 'logout') return { cmd: 'logout' };
    30	  const i = argv.indexOf('--playlist');
    31	  return i >= 0 && argv[i + 1] ? { cmd: 'sync', playlistKey: argv[i + 1] } : { cmd: 'sync' };
    32	}
    33	
    34	/** Real local data-root convention (see file header): settings.json's baseOutputFolder/
    35	 *  outputFolder — NOT a DATA_ROOT env var, which does not exist anywhere else in this codebase. */
    36	function resolveDataRoots(): string[] {
    37	  const override = process.env.CLOUD_SYNC_DATA_ROOTS;
    38	  if (override) return override.split(':').filter(Boolean);
    39	  const settings = readSettings();
    40	  const root = settings.baseOutputFolder || settings.outputFolder;
    41	  return root ? [root] : [];
    42	}
    43	
    44	export async function main(argv: string[]): Promise<number> {
    45	  const args = parseArgs(argv);
    46	  if (args.cmd === 'login') {
    47	    const [email, password] = [process.env.CLOUD_SYNC_EMAIL, process.env.CLOUD_SYNC_PASSWORD];
    48	    if (!email || !password) { console.error('Set CLOUD_SYNC_EMAIL and CLOUD_SYNC_PASSWORD to log in.'); return 1; }
    49	    await signIn(email, password); console.log('Signed in.'); return 0;
    50	  }
    51	  if (args.cmd === 'logout') { await signOut(); console.log('Signed out.'); return 0; }
    52	
    53	  let client;
    54	  try { client = await getAuthedClient(); }
    55	  catch (e) { if (e instanceof NoSessionError) { console.error(e.message); return 1; } throw e; }
    56	
    57	  const { data } = await client.auth.getUser();
    58	  const ownerId = data.user!.id;
    59	  const dataRoots = resolveDataRoots();
    60	
    61	  const deps: SyncDeps = {
    62	    local: localMetadataStore,
    63	    cloud: new SupabaseMetadataStore(client),
    64	    localBlob: localBlobStore,
    65	    cloudBlob: new SupabaseBlobStore(client, ARTIFACTS_BUCKET),
    66	    dataRoots, ownerId,
    67	  };
    68	  const report = await runSync(deps, args.playlistKey ? { playlistKey: args.playlistKey } : {});
    69	  console.log(JSON.stringify(report, null, 2));
    70	  return report.errors.length ? 2 : 0;
    71	}
    72	
    73	if (require.main === module) {
    74	  main(process.argv.slice(2)).then((code) => process.exit(code)).catch((e) => { console.error(e); process.exit(1); });
    75	}

exec
/bin/bash -lc "nl -ba tests/integration/cloud-sync/sync-run.int.test.ts | sed -n '1,100p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	// tests/integration/cloud-sync/sync-run.int.test.ts
     2	//
     3	// Stage 3 Cloud Sync (§7), Task 12 — the integration keystone for runSync. Runs against real local
     4	// FS ↔ local Supabase under an authenticated USER session (never service-role). Focuses on
     5	// end-to-end wiring + atomicity + money-safety (the reconcile branches are unit-tested upstream).
     6	//
     7	// F1: cloud Principal uses deps.ownerId (= auth.uid()) so Supabase Storage RLS accepts the path and
     8	//     a hydrate copies the real MD bytes. F2: transfers finalize via updateVideoFields. F3:
     9	//     applyClassBWinners throws on a no-row write. Crash-safety uses a local→cloud publish so the
    10	//     Supabase staged→promote (the faultable durability gate) is on the critical path.
    11	import { promises as fs } from 'fs';
    12	import os from 'os';
    13	import path from 'path';
    14	import { makeOwnerContext, seedLocalPlaylist } from '@/tests/integration/helpers/cloud';
    15	import { runSync } from '@/lib/cloud-sync/sync-run';
    16	
    17	afterAll(async () => {
    18	  const home = os.homedir();
    19	  const dirs = (await fs.readdir(home)).filter((d) => d.startsWith('.cs-syncrun-'));
    20	  await Promise.all(dirs.map((d) => fs.rm(path.join(home, d), { recursive: true, force: true })));
    21	});
    22	
    23	describe('runSync (§7)', () => {
    24	  it('hydrates an empty local replica from a cloud-only video (additive create, no charge)', async () => {
    25	    const ctx = await makeOwnerContext();
    26	    await seedLocalPlaylist(ctx); // cloud has 1 promoted-summary video, local empty
    27	    const spendBefore = await ctx.spendLedgerTotal();
    28	
    29	    const report = await runSync(ctx.syncDeps());
    30	
    31	    expect(report.created).toBeGreaterThanOrEqual(1);
    32	    // money-safety: a sync copy NEVER charges
    33	    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
    34	
    35	    const localIdx = await ctx.local.readIndex(ctx.localPrincipal);
    36	    expect(localIdx.videos.length).toBeGreaterThanOrEqual(1);
    37	
    38	    // F1: the hydrate read the cloud MD off `<ownerId>/<playlistKey>/<key>` and copied NON-NULL
    39	    // bytes to the local replica (a wrong cloud Principal would read null → empty receiver).
    40	    const hydrated = localIdx.videos.find((v) => v.id === ctx.videoId)!;
    41	    expect(hydrated.summaryMd).toBe(`${ctx.videoId}.md`);
    42	    const localBody = await ctx.localBlob.get(ctx.localPrincipal, hydrated.summaryMd!);
    43	    expect(localBody).not.toBeNull();
    44	    expect(localBody!.toString('utf8')).toContain(`# Summary ${ctx.videoId}`);
    45	  });
    46	
    47	  it('publishes a local-only human note to the cloud with the source timestamp', async () => {
    48	    const ctx = await makeOwnerContext();
    49	    await seedLocalPlaylist(ctx, { localNote: { value: 'mine', editedAt: '2026-04-04T00:00:00.000Z' } });
    50	
    51	    await runSync(ctx.syncDeps());
    52	
    53	    const row = await ctx.readVideoData(ctx.playlistId, ctx.videoId);
    54	    expect(row.personalNote).toBe('mine');
    55	    expect(row.annotationsEditedAt?.personalNote).toBe('2026-04-04T00:00:00.000Z');
    56	  });
    57	
    58	  it('does not advance the manifest baseline when the cloud promote is not verified (crash safety)', async () => {
    59	    const ctx = await makeOwnerContext();
    60	    await seedLocalPlaylist(ctx, { publishToCloud: true }); // local-only video → publishes to cloud
    61	    const spendBefore = await ctx.spendLedgerTotal();
    62	
    63	    const report = await runSync(ctx.syncDeps({ failCloudPromote: true }));
    64	
    65	    // The transfer threw at promote → per-video error captured, run did not abort.
    66	    expect(report.errors.length).toBeGreaterThanOrEqual(1);
    67	    // Behavior #10/#11: a partial transfer NEVER advances the manifest baseline.
    68	    const m = await ctx.readManifest();
    69	    expect(m.videos[ctx.videoId]).toBeUndefined();
    70	    // still no charge
    71	    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
    72	  });
    73	});

exec
/bin/bash -lc "nl -ba tests/integration/cloud-sync/e2e.int.test.ts | sed -n '680,920p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
   680	    const ctx = await makeOwnerContext();
   681	    // Same section titles, different prose — the drift guard cannot see the difference.
   682	    const bodyLocalOld = '# Shared Title\n\nthe OLD prose the local model was built from\n';
   683	    const bodyCloudWin = '# Shared Title\n\nthe NEW prose that wins on format major\n';
   684	    await seedLocalVideoFull(ctx, {
   685	      mdBody: bodyLocalOld, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
   686	    });
   687	    await seedCloudVideo(ctx, {
   688	      mdBody: bodyCloudWin, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
   689	    });
   690	    // Receiver (local) model was built from the OLD body; sender (cloud) holds no model at all.
   691	    await ctx.localBlob.put(
   692	      ctx.localPrincipal, modelKey(ctx),
   693	      Buffer.from(`${JSON.stringify(modelEnvelope(bodyHash(bodyLocalOld)))}\n`, 'utf8'), 'application/json',
   694	    );
   695	    const spendBefore = await ctx.spendLedgerTotal();
   696	
   697	    const r1 = await runSync(ctx.syncDeps());
   698	
   699	    expect(r1.updatedLocal).toBeGreaterThanOrEqual(1);            // the Class-A transfer ran
   700	    expect(await localBlobBytes(ctx, modelKey(ctx))).toBeNull();  // provably stale → deleted
   701	    expect(r1.shareNeedsOwnerServe).toBe(1);                      // owner must re-serve the share
   702	    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);       // the delete itself never charges
   703	
   704	    // Run 2 — hashes now agree → reconcileClassA 'skip' → companionTransfer never runs again. The
   705	    // stickiness that would have made a WRONG decision permanent must not resurrect the model.
   706	    const r2 = await runSync(ctx.syncDeps());
   707	    expect(r2.shareNeedsOwnerServe).toBe(0);
   708	    expect(await localBlobBytes(ctx, modelKey(ctx))).toBeNull();
   709	    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
   710	  });
   711	
   712	  // (ii) The round-4 money bug, preserved: the receiver's model was built from the very body that
   713	  //      just won, so it is still valid. An unprovable sender read must not cost the owner a paid
   714	  //      Gemini magazine transform to rebuild what it already has.
   715	  it('H-R5-1(ii): an unprovable sender read PRESERVES a receiver model that matches the winner (2 runs)', async () => {
   716	    const ctx = await makeOwnerContext();
   717	    const bodyLocalOld = '# LocalOld\n\nlower-major local body\n';
   718	    const bodyCloudWin = '# CloudWin\n\nhigher-major winner body\n';
   719	    await seedLocalVideoFull(ctx, {
   720	      mdBody: bodyLocalOld, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
   721	    });
   722	    await seedCloudVideo(ctx, {
   723	      mdBody: bodyCloudWin, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
   724	    });
   725	    // Receiver (local) model already matches the WINNING cloud body; sender (cloud) holds no model.
   726	    const envelope = modelEnvelope(bodyHash(bodyCloudWin));
   727	    await ctx.localBlob.put(
   728	      ctx.localPrincipal, modelKey(ctx),
   729	      Buffer.from(`${JSON.stringify(envelope)}\n`, 'utf8'), 'application/json',
   730	    );
   731	    const spendBefore = await ctx.spendLedgerTotal();
   732	
   733	    const r1 = await runSync(ctx.syncDeps());
   734	
   735	    expect(r1.updatedLocal).toBeGreaterThanOrEqual(1);
   736	    const kept = await localBlobBytes(ctx, modelKey(ctx));
   737	    expect(kept).not.toBeNull();                                     // paid artifact survives
   738	    expect(JSON.parse(kept!.toString('utf8')).sourceMdHash).toBe(bodyHash(bodyCloudWin));
   739	    expect(r1.shareNeedsOwnerServe).toBe(0);                         // no false "share is stale"
   740	    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
   741	
   742	    const r2 = await runSync(ctx.syncDeps());
   743	    expect(r2.shareNeedsOwnerServe).toBe(0);
   744	    expect(await localBlobBytes(ctx, modelKey(ctx))).not.toBeNull();
   745	    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
   746	  });
   747	
   748	  // (iii) The other half of round 4's conflation, on the backend that CAN prove absence. A local
   749	  //       sender null also covers corrupt/schema-invalid (readModelEnvelope parses and validates),
   750	  //       which round 4 mapped to `none` → delete. But "the sender's envelope is garbage" says
   751	  //       nothing about the receiver's, and here the cloud receiver's matches the winning body
   752	  //       exactly. Deleting it would burn reserve_serve_model → spend_ledger to rebuild.
   753	  it('H-R5-1(iii): a CORRUPT local sender envelope preserves a matching cloud receiver model (2 runs)', async () => {
   754	    const ctx = await makeOwnerContext();
   755	    const bodyLocalWin = '# LocalWin\n\nhigher-major local body\n';
   756	    const bodyCloudOld = '# CloudOld\n\nlower-major cloud body\n';
   757	    await seedLocalVideoFull(ctx, {
   758	      mdBody: bodyLocalWin, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
   759	    });
   760	    await seedCloudVideo(ctx, {
   761	      mdBody: bodyCloudOld, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
   762	    });
   763	    // Sender (local) envelope is unparseable → readModelEnvelope null on a provesAbsence backend.
   764	    await ctx.localBlob.put(
   765	      ctx.localPrincipal, modelKey(ctx), Buffer.from('{not json at all', 'utf8'), 'application/json',
   766	    );
   767	    // Receiver (cloud) model matches the WINNING local body → still valid, must survive.
   768	    await putCloudBlob(
   769	      ctx, modelKey(ctx),
   770	      Buffer.from(`${JSON.stringify(modelEnvelope(bodyHash(bodyLocalWin)))}\n`, 'utf8'), 'application/json',
   771	    );
   772	    const spendBefore = await ctx.spendLedgerTotal();
   773	
   774	    const r1 = await runSync(ctx.syncDeps());
   775	
   776	    expect(r1.updatedCloud).toBeGreaterThanOrEqual(1);
   777	    const kept = await cloudBlobBytes(ctx, modelKey(ctx));
   778	    expect(kept).not.toBeNull();
   779	    expect(JSON.parse(kept!.toString('utf8')).sourceMdHash).toBe(bodyHash(bodyLocalWin));
   780	    expect(r1.shareNeedsOwnerServe).toBe(0);
   781	    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
   782	
   783	    const r2 = await runSync(ctx.syncDeps());
   784	    expect(r2.shareNeedsOwnerServe).toBe(0);
   785	    expect(await cloudBlobBytes(ctx, modelKey(ctx))).not.toBeNull();
   786	    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
   787	  });
   788	
   789	  // ── L-R6-1 (round 6) — the ship branch must never DOWNGRADE the receiver. Both sides hold a model
   790	  //    built from the WINNING body, but the sender's was built by an older checkout (GENERATOR_VERSION
   791	  //    skew between the local tree and the deployed cloud image). Shipping it blind would replace a
   792	  //    model isFresh() accepts with one it rejects, flipping the share to a 503 whose only recovery is
   793	  //    a PAID owner re-serve.
   794	  it('L-R6-1: a ship never overwrites a receiver model that is already generation-fresh', async () => {
   795	    const ctx = await makeOwnerContext();
   796	    const bodyLocalWin = '# LocalWin\n\nhigher-major local body\n';
   797	    const bodyCloudOld = '# CloudOld\n\nlower-major cloud body\n';
   798	    await seedLocalVideoFull(ctx, {
   799	      mdBody: bodyLocalWin, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
   800	    });
   801	    await seedCloudVideo(ctx, {
   802	      mdBody: bodyCloudOld, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
   803	    });
   804	    // Both envelopes were built from the winning body; only the SENDER's generation is behind.
   805	    await ctx.localBlob.put(
   806	      ctx.localPrincipal, modelKey(ctx),
   807	      Buffer.from(`${JSON.stringify(modelEnvelope(bodyHash(bodyLocalWin), 'magazine-skim v1'))}\n`, 'utf8'),
   808	      'application/json',
   809	    );
   810	    await putCloudBlob(
   811	      ctx, modelKey(ctx),
   812	      Buffer.from(`${JSON.stringify(modelEnvelope(bodyHash(bodyLocalWin), GENERATOR_VERSION))}\n`, 'utf8'),
   813	      'application/json',
   814	    );
   815	    const spendBefore = await ctx.spendLedgerTotal();
   816	
   817	    const r1 = await runSync(ctx.syncDeps());
   818	
   819	    expect(r1.updatedCloud).toBeGreaterThanOrEqual(1);          // the Class-A transfer still ran
   820	    const kept = await cloudBlobBytes(ctx, modelKey(ctx));
   821	    expect(kept).not.toBeNull();
   822	    const keptEnvelope = JSON.parse(kept!.toString('utf8'));
   823	    expect(keptEnvelope.generatorVersion).toBe(GENERATOR_VERSION); // NOT downgraded to v1
   824	    expect(keptEnvelope.sourceMdHash).toBe(bodyHash(bodyLocalWin));
   825	    expect(r1.shareNeedsOwnerServe).toBe(0);                     // the share still renders
   826	    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
   827	  });
   828	
   829	  // ── M-R6-1 (round 6) — a failed companion ship must not be sticky-silent. transferClassA has
   830	  //    already committed the winner body durably, so the next run's reconcile returns 'skip' and the
   831	  //    ship is never retried; the receiver keeps a model built from the PRE-SYNC body. Swallow the
   832	  //    write failure, keep the baseline advancing (the Class-A commit DID land), and report the share
   833	  //    as unready so the staleness is visible instead of being served as fresh forever.
   834	  it('M-R6-1: a failed companion ship reports the share unready, still advances the baseline', async () => {
   835	    const ctx = await makeOwnerContext();
   836	    const bodyLocalWin = '# LocalWin\n\nhigher-major local body\n';
   837	    const bodyCloudOld = '# CloudOld\n\nlower-major cloud body\n';
   838	    await seedLocalVideoFull(ctx, {
   839	      mdBody: bodyLocalWin, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
   840	    });
   841	    await seedCloudVideo(ctx, {
   842	      mdBody: bodyCloudOld, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
   843	    });
   844	    // Sender (local) holds a shippable model built from the winning body → decideCompanion → ship.
   845	    await ctx.localBlob.put(
   846	      ctx.localPrincipal, modelKey(ctx),
   847	      Buffer.from(`${JSON.stringify(modelEnvelope(bodyHash(bodyLocalWin), GENERATOR_VERSION))}\n`, 'utf8'),
   848	      'application/json',
   849	    );
   850	    const spendBefore = await ctx.spendLedgerTotal();
   851	
   852	    const r1 = await runSync(ctx.syncDeps({ failCloudModelPut: true }));
   853	
   854	    // The Class-A commit landed durably despite the companion failure.
   855	    expect(r1.updatedCloud).toBeGreaterThanOrEqual(1);
   856	    expect((await cloudBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyLocalWin);
   857	    // Baseline advanced — the transfer is durable, so re-running must not redo it.
   858	    const m1 = await ctx.readManifest();
   859	    expect((m1.videos[ctx.videoId] as VideoBaseline).classA.mdHash).toBe(bodyHash(bodyLocalWin));
   860	    // The share is reported unready rather than left silently stale.
   861	    expect(r1.shareNeedsOwnerServe).toBe(1);
   862	    expect(r1.errors.some((e) => e.videoId === ctx.videoId)).toBe(true); // failure stays visible
   863	    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
   864	  });
   865	
   866	  // ── H2 (round 4) — the B1 guard was over-broad on the LOCAL side. B1 exists because the Supabase
   867	  //    backend cannot tell absent from unreadable; the local backend CAN (LocalFsBlobStore.get
   868	  //    returns null ONLY on ENOENT and rethrows every other errno), so a local record advertising a
   869	  //    summaryMd whose body reads back null PROVES the file is gone — a user who moved the .md by
   870	  //    hand, or a generation that crashed between the index write and the blob write.
   871	  //    Before the guard this healed for free (!lHas → copyToLocal → the dangling pointer is
   872	  //    repaired, purely additive). The guard made it throw on EVERY run, forever, never advancing a
   873	  //    baseline, with no exit but hand-editing playlist-index.json or paying to regenerate content
   874	  //    sitting intact in the cloud. Fail-closed must be scoped to the backend that needs it.
   875	  it('H2: a genuinely-absent local MD blob is hydrated from the cloud, not stranded (2 runs)', async () => {
   876	    const ctx = await makeOwnerContext();
   877	    const bodyCloud = '# CloudHasIt\n\nthe body the local record lost\n';
   878	    // Local ADVERTISES summaryMd (+ a promoted artifact) but mdBody is omitted → the blob is
   879	    // genuinely absent on a backend that proves absence.
   880	    await seedLocalVideoFull(ctx, {
   881	      docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
   882	    });
   883	    await seedCloudVideo(ctx, {
   884	      mdBody: bodyCloud, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
   885	    });
   886	    const spendBefore = await ctx.spendLedgerTotal();
   887	
   888	    const r1 = await runSync(ctx.syncDeps());
   889	
   890	    expect(r1.errors).toEqual([]);                       // no permanent per-run failure
   891	    expect(r1.updatedLocal).toBeGreaterThanOrEqual(1);   // additive hydration ran
   892	    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloud);
   893	    const local = await localVideoRecord(ctx);
   894	    expect(local?.summaryMd).toBe(key(ctx));
   895	    expect(artifactsOf(local)?.summaryMd?.status).toBe('promoted');
   896	    expect(await ctx.spendLedgerTotal()).toBe(spendBefore); // healed without any regeneration
   897	
   898	    // Run 2 — the dangling pointer is repaired, so the sides simply agree.
   899	    const r2 = await runSync(ctx.syncDeps());
   900	    expect(r2.errors).toEqual([]);
   901	    expect(r2.updatedLocal).toBe(0);
   902	    expect(r2.skippedIdentical).toBeGreaterThanOrEqual(1);
   903	    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloud);
   904	  });
   905	
   906	  // ── H3 (round 4) — a local-only video wiped the cloud playlist's title on every sync.
   907	  //    playlistMetaFor checked the local registry FIRST and returned { playlistUrl } with no title
   908	  //    (LocalPlaylist never carried one), the cloud-registry branch that does carry a title being
   909	  //    unreachable whenever the playlist also exists locally. ensureReceiverSlot then called
   910	  //    setPlaylistMeta unconditionally, and the Supabase upsert writes
   911	  //    `playlist_title: meta.playlistTitle ?? null` — an explicit NULL. Recurs on every sync that
   912	  //    carries any local-only video (the ordinary case); recovery needs the backfill-titles route
   913	  //    plus a YouTube API key.
   914	  it('H3: an additive publish of a local-only video preserves the cloud playlist title (2 runs)', async () => {
   915	    const ctx = await makeOwnerContext();
   916	    await prepareSyncCtx(ctx);
   917	    const title = 'Deep Learning Lectures';
   918	    // Cloud playlist row carries a title (as lib/job-queue/producer.ts sets it at enqueue) and holds
   919	    // NO videos; the local replica has a title-less index with one video → additive publish to cloud.
   920	    const { data: pl, error } = await adminClient().from('playlists').insert({

exec
/bin/bash -lc "nl -ba lib/storage/local/local-blob-store.ts | sed -n '1,140p' && nl -ba lib/storage/supabase/supabase-blob-store.ts | sed -n '1,180p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	import fs from 'fs'; import path from 'path'; import crypto from 'crypto';
     2	import type { BlobStore, StagedRef } from '@/lib/storage/blob-store';
     3	import { assertLogicalKey } from '@/lib/storage/blob-store';
     4	import type { Principal } from '@/lib/storage/principal';
     5	
     6	/** Byte-for-byte the current -data layout: physical path = join(indexKey, key). */
     7	export class LocalFsBlobStore implements BlobStore {
     8	  /** get/exists below return null/false ONLY on ENOENT and rethrow every other errno, so a null
     9	   *  here genuinely means the object is not there. */
    10	  readonly provesAbsence = true;
    11	
    12	  private abs(p: Principal, key: string): string { assertLogicalKey(key); return path.join(p.indexKey, key); }
    13	
    14	  // contentType unused locally but required by the BlobStore interface (cloud impls will use it)
    15	  async put(p: Principal, key: string, bytes: Buffer, _contentType: string): Promise<void> {
    16	    const dest = this.abs(p, key); fs.mkdirSync(path.dirname(dest), { recursive: true });
    17	    const tmp = dest + '.' + crypto.randomUUID() + '.tmp';
    18	    try { fs.writeFileSync(tmp, bytes); fs.renameSync(tmp, dest); }
    19	    catch (e) { try { fs.unlinkSync(tmp); } catch {} throw e; }
    20	  }
    21	
    22	  async get(p: Principal, key: string): Promise<Buffer | null> {
    23	    try { return fs.readFileSync(this.abs(p, key)); }
    24	    catch (e: any) { if (e.code === 'ENOENT') return null; throw e; }
    25	  }
    26	
    27	  async exists(p: Principal, key: string): Promise<boolean> {
    28	    try { fs.statSync(this.abs(p, key)); return true; }
    29	    catch (e: any) { if (e.code === 'ENOENT') return false; throw e; }
    30	  }
    31	
    32	  async delete(p: Principal, key: string): Promise<void> {
    33	    try { fs.unlinkSync(this.abs(p, key)); } catch (e: any) { if (e.code !== 'ENOENT') throw e; }
    34	  }
    35	
    36	  async putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef> {
    37	    assertLogicalKey(key);  // validate before building tempKey — a leading '/' on key wouldn't appear on tempKey
    38	    const tempKey = `_staging/${crypto.randomUUID()}/${key}`;
    39	    await this.put(p, tempKey, bytes, contentType);
    40	    return { principal: p, tempKey, finalKey: key };
    41	  }
    42	
    43	  async promote(ref: StagedRef): Promise<void> {
    44	    const from = this.abs(ref.principal, ref.tempKey); const to = this.abs(ref.principal, ref.finalKey);
    45	    if (!fs.existsSync(from) && fs.existsSync(to)) return;   // idempotent: already promoted
    46	    fs.mkdirSync(path.dirname(to), { recursive: true }); fs.renameSync(from, to);
    47	  }
    48	
    49	  // '' → path.join(indexKey, '') === indexKey, i.e. the playlist's own index dir (intended
    50	  // target, not above it). force:true makes an absent path a no-op (ENOENT-safe).
    51	  async deletePrefix(p: Principal, prefix: string): Promise<void> {
    52	    assertLogicalKey(prefix);
    53	    await fs.promises.rm(path.join(p.indexKey, prefix), { recursive: true, force: true });
    54	  }
    55	
    56	  async list(p: Principal, prefix: string): Promise<string[]> {
    57	    assertLogicalKey(prefix);
    58	    const root = path.join(p.indexKey, prefix);
    59	    let entries: string[];
    60	    try {
    61	      entries = await fs.promises.readdir(root, { recursive: true }) as string[];
    62	    } catch (e) {
    63	      if ((e as NodeJS.ErrnoException).code === 'ENOENT') return [];
    64	      throw e;
    65	    }
    66	    const out: string[] = [];
    67	    for (const rel of entries) {
    68	      const full = path.join(root, rel);
    69	      if ((await fs.promises.stat(full)).isFile()) {
    70	        out.push(path.posix.join(prefix.replace(/\/$/, ''), rel.split(path.sep).join('/')));
    71	      }
    72	    }
    73	    return out;
    74	  }
    75	}
    76	
    77	export const localBlobStore = new LocalFsBlobStore();
     1	import crypto from 'crypto';
     2	import type { SupabaseClient } from '@supabase/supabase-js';
     3	import type { BlobStore, StagedRef } from '@/lib/storage/blob-store';
     4	import { assertLogicalKey } from '@/lib/storage/blob-store';
     5	import type { Principal } from '@/lib/storage/principal';
     6	
     7	export class SupabaseBlobStore implements BlobStore {
     8	  /** `get` swallows EVERY download failure into null (see the note on it below) and `exists` is
     9	   *  defined in terms of `get`, so this backend can never prove an object is absent. */
    10	  readonly provesAbsence = false;
    11	
    12	  constructor(private client: SupabaseClient, private bucket: string) {}
    13	
    14	  /** Server-side owner prefix — never a client absolute path. */
    15	  private objectKey(p: Principal, key: string): string {
    16	    assertLogicalKey(key);
    17	    return `${p.id}/${p.indexKey}/${key}`;
    18	  }
    19	
    20	  private b() { return this.client.storage.from(this.bucket); }
    21	
    22	  async put(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<void> {
    23	    const { error } = await this.b().upload(this.objectKey(p, key), bytes, { contentType, upsert: true });
    24	    if (error) throw error;
    25	  }
    26	
    27	  async get(p: Principal, key: string): Promise<Buffer | null> {
    28	    const { data, error } = await this.b().download(this.objectKey(p, key));
    29	    // Swallows EVERY failure, not just 404: network, 5xx, timeout and RLS denial all return null,
    30	    // so a null here does NOT prove the object is absent. Callers that treat "no bytes" as a
    31	    // semantic fact (e.g. "this replica holds no MD") must corroborate it against the record that
    32	    // advertises the key — see the B1 guard in lib/cloud-sync/sync-run.ts. Behavior is deliberately
    33	    // left as-is: shared with already-merged read paths where absent-vs-unreadable is immaterial.
    34	    // Note the LOCAL blob store differs — it returns null only on ENOENT and throws otherwise.
    35	    if (error) return null;
    36	    return Buffer.from(await data.arrayBuffer());
    37	  }
    38	
    39	  async exists(p: Principal, key: string): Promise<boolean> {
    40	    return (await this.get(p, key)) !== null;
    41	  }
    42	
    43	  async delete(p: Principal, key: string): Promise<void> {
    44	    const { error } = await this.b().remove([this.objectKey(p, key)]);
    45	    if (error) throw error;
    46	  }
    47	
    48	  async putStaged(p: Principal, key: string, bytes: Buffer, contentType: string): Promise<StagedRef> {
    49	    assertLogicalKey(key); // validate before building tempKey — reject '/absolute' before any upload
    50	    const tempKey = `_staging/${crypto.randomUUID()}/${key}`; // per-attempt-unique (ports local-blob-store)
    51	    await this.put(p, tempKey, bytes, contentType);
    52	    return { principal: p, tempKey, finalKey: key };
    53	  }
    54	
    55	  async promote(ref: StagedRef): Promise<void> {
    56	    const from = this.objectKey(ref.principal, ref.tempKey);
    57	    const to = this.objectKey(ref.principal, ref.finalKey);
    58	    // move = copy+delete (non-atomic). Idempotent: if final already present, ensure temp gone and return.
    59	    if (await this.exists(ref.principal, ref.finalKey)) {
    60	      await this.b().remove([from]).catch(() => {});
    61	      return;
    62	    }
    63	    const { error } = await this.b().move(from, to);
    64	    if (error) {
    65	      // A concurrent promoter (worker job retry / re-run of the same MD key) may have won the race: destination-exists / source-missing.
    66	      // Re-check the final; treat a present final as success, else rethrow.
    67	      if (await this.exists(ref.principal, ref.finalKey)) {
    68	        await this.b().remove([from]).catch(() => {});
    69	        return;
    70	      }
    71	      throw error;
    72	    }
    73	  }
    74	
    75	  async deletePrefix(p: Principal, prefix: string): Promise<void> {
    76	    assertLogicalKey(prefix);
    77	    const root = `${p.id}/${p.indexKey}/${prefix}`.replace(/\/$/, '');
    78	    const objectPaths = await this.collectObjectPaths(root);
    79	    for (let i = 0; i < objectPaths.length; i += 1000) {
    80	      const batch = objectPaths.slice(i, i + 1000);
    81	      const { error } = await this.b().remove(batch);
    82	      if (error) throw error;
    83	    }
    84	  }
    85	
    86	  async list(p: Principal, prefix: string): Promise<string[]> {
    87	    assertLogicalKey(prefix);
    88	    const ownerRoot = `${p.id}/${p.indexKey}/`;
    89	    const dirPath = `${ownerRoot}${prefix}`.replace(/\/$/, '');
    90	    const full = await this.collectObjectPaths(dirPath); // returns full object paths (or [] if absent)
    91	    return full.map((f) => f.slice(ownerRoot.length)); // strip owner root → logical key
    92	  }
    93	
    94	  /** Recursively walks a Supabase Storage "directory" (non-recursive `.list`, paginated at
    95	   *  100/page) and returns every file's full object path. Folder entries surface with
    96	   *  `id === null` and are descended into; file entries (`id !== null`) are collected. */
    97	  private async collectObjectPaths(dirPath: string): Promise<string[]> {
    98	    const paths: string[] = [];
    99	    const limit = 100;
   100	    let offset = 0;
   101	    for (;;) {
   102	      const { data, error } = await this.b().list(dirPath, { limit, offset });
   103	      if (error) throw error;
   104	      const entries = data ?? [];
   105	      for (const entry of entries) {
   106	        const entryPath = `${dirPath}/${entry.name}`;
   107	        if (entry.id === null) {
   108	          paths.push(...(await this.collectObjectPaths(entryPath)));
   109	        } else {
   110	          paths.push(entryPath);
   111	        }
   112	      }
   113	      if (entries.length < limit) break;
   114	      offset += limit;
   115	    }
   116	    return paths;
   117	  }
   118	}

codex
The storage path is consistent with the intended failure behavior: local model writes are temp-file rename, Supabase model writes are `upload(..., upsert: true)`, and corrupt JSON reads as `null`. I’m going to run the focused companion tests and the cloud-sync integration file if feasible, then I’ll summarize the matrix and verdicts.
exec
/bin/bash -lc 'npx jest tests/lib/cloud-sync/companion.test.ts --runInBand' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
exec
/bin/bash -lc 'npx jest tests/integration/cloud-sync/e2e.int.test.ts --runInBand' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 exited 1 in 3386ms:
No tests found, exiting with code 1
Run with `--passWithNoTests` to exit with code 0
In /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
  905 files checked.
  testMatch: /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/lib/**/*.test.ts, /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/api/**/*.test.ts, /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/scripts/**/*.test.ts, /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/smoke.test.ts, /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/components/**/*.test.tsx - 245 matches
  testPathIgnorePatterns: /node_modules/, /.next/ - 560 matches
  testRegex:  - 0 matches
Pattern: tests/integration/cloud-sync/e2e.int.test.ts - 0 matches

 succeeded in 3787ms:
Test Suites: 1 passed, 1 total
Tests:       31 passed, 31 total
Snapshots:   0 total
Time:        0.359 s, estimated 1 s
Ran all test suites matching tests/lib/cloud-sync/companion.test.ts.

codex
The unit companion test passes. The integration file is outside the default Jest `testMatch`, so the direct `npx jest tests/integration/...` invocation does not select it; I’m checking the package scripts for the intended integration command before deciding whether to run more.
exec
/bin/bash -lc 'cat package.json' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
{
  "name": "youtube-playlist-summaries",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "test": "jest",
    "test:watch": "jest --watch",
    "test:e2e": "playwright test",
    "rerender-html": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node scripts/rerender-html.ts",
    "audit-timestamps": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node scripts/audit-timestamps.ts",
    "audit-summaries": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node scripts/audit-summaries.ts",
    "repair-timestamps": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node scripts/repair-timestamps.ts",
    "backfill-serial": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node scripts/backfill-serial-prefix.ts",
    "backfill-playlist-titles": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node scripts/backfill-playlist-titles.ts",
    "test:integration": "jest --config jest.integration.config.ts --runInBand",
    "check:confinement": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node scripts/check-service-confinement.ts",
    "worker": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node -r tsconfig-paths/register worker/main.ts",
    "verify:gemini-release": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node -r tsconfig-paths/register scripts/verify-gemini-release.ts",
    "cloud-sync": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node -r tsconfig-paths/register scripts/cloud-sync.ts"
  },
  "dependencies": {
    "@google/generative-ai": "^0.24.1",
    "@supabase/ssr": "^0.12.0",
    "@supabase/supabase-js": "^2.109.0",
    "googleapis": "^171.4.0",
    "markdown-it": "^14.2.0",
    "next": "16.2.6",
    "playwright": "^1.60.0",
    "react": "19.2.4",
    "react-dom": "19.2.4",
    "server-only": "^0.0.1",
    "youtube-transcript": "^1.3.1",
    "zod": "^4.4.3"
  },
  "devDependencies": {
    "@playwright/test": "^1.60.0",
    "@tailwindcss/postcss": "^4",
    "@testing-library/dom": "^10.4.1",
    "@testing-library/jest-dom": "^6.9.1",
    "@testing-library/react": "^16.3.2",
    "@types/jest": "^30.0.0",
    "@types/markdown-it": "^14.1.2",
    "@types/node": "^20",
    "@types/react": "^19",
    "@types/react-dom": "^19",
    "jest": "^30.4.2",
    "jest-environment-jsdom": "^30.4.1",
    "tailwindcss": "^4",
    "ts-jest": "^29.4.9",
    "ts-node": "^10.9.2",
    "tsconfig-paths": "^4.2.0",
    "typescript": "^5"
  }
}

exec
/bin/bash -lc "rg -n \"integration|e2e\\.int|jest.*integration|testMatch\" package.json jest.config* tests -g '"'!node_modules'"'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
jest.config.ts:11:  testMatch: [
package.json:18:    "test:integration": "jest --config jest.integration.config.ts --runInBand",
tests/e2e/cloud-library.spec.ts:9: *   - Per-route integration tests against a REAL Supabase stack with `signInAs`
tests/e2e/cloud-library.spec.ts:10: *     (tests/integration/{playlists-route,videos-route-cloud,quickview-route-cloud,
tests/e2e/cloud-library.spec.ts:21: *      client (mirror tests/integration/helpers/seed.ts), sign in via Supabase to obtain
tests/api/delete-playlist-route.test.ts:10:// and 6 (second delete ⇒ 404) are covered by the integration test
tests/api/delete-playlist-route.test.ts:11:// (tests/integration/delete-playlist-route.test.ts) against real local Supabase/RLS.
tests/api/dig-cloud-route.test.ts:5: * but jest.config.ts's testMatch only covers tests/lib, tests/api, tests/scripts, tests/smoke,
tests/api/dig-cloud-route.test.ts:6: * and tests/components (verified — no tests/app pattern exists). tests/integration is a SEPARATE
tests/api/dig-cloud-route.test.ts:7: * jest project (jest.integration.config.ts) that runs against a real local Supabase stack, which
tests/api/backfill-titles-route.test.ts:19:// Behaviors 3 and 7 (real backfill + owner isolation) are covered by the integration test
tests/api/backfill-titles-route.test.ts:20:// (tests/integration/backfill-titles-route.test.ts) against real local Supabase/RLS.
tests/integration/share-summary-2c.test.ts:1:// tests/integration/share-summary-2c.test.ts
tests/integration/share-summary-2c.test.ts:3:// Stage 2c Task 8 — real-Supabase integration guard proving:
tests/integration/share-summary-2c.test.ts:9:// Run: npx supabase db reset && npm run test:integration -- share-summary-2c --runInBand
tests/integration/share-summary-2c.test.ts:27:describe('share-summary-2c integration', () => {
tests/integration/middleware-2a.test.ts:3:// This file lives under tests/integration/ per the task brief's required path, but — like
tests/integration/serve-model-charge.test.ts:1:// tests/integration/serve-model-charge.test.ts
tests/integration/delete-playlist-route.test.ts:1:// tests/integration/delete-playlist-route.test.ts
tests/integration/delete-playlist-route.test.ts:4:// tests/integration/archive-route-cloud.test.ts: mock ONLY the next/headers +
tests/integration/delete-playlist-route.test.ts:27:// hoisted above this declaration) — same pattern as tests/integration/archive-route-cloud.test.ts.
tests/integration/blob-store.test.ts:1:// tests/integration/blob-store.test.ts
tests/integration/blob-store.test.ts:5:// Run via: npm run test:integration -- blob-store
tests/integration/blob-store.test.ts:6:// Requires: stack up + .env.test.local present (see tests/integration/setup.ts).
tests/integration/blob-store.test.ts:25: *  validation — integration tests focus on store behaviour, not type fidelity. */
tests/integration/rls-isolation.test.ts:1:// tests/integration/rls-isolation.test.ts
tests/lib/pipeline-async.test.ts:83:describe('B2: runIngestion awaits every store call (delayed-store integration)', () => {
tests/integration/enqueue-dig.test.ts:1:// tests/integration/enqueue-dig.test.ts
tests/integration/enqueue-dig.test.ts:5:// service client — mirrors the setup in tests/integration/summary-handler.test.ts.
tests/integration/review-route-cloud.test.ts:1:// tests/integration/review-route-cloud.test.ts
tests/integration/review-route-cloud.test.ts:4:// Supabase stack. Mirrors tests/integration/quickview-route-cloud.test.ts (Task 6): mock
tests/integration/review-route-cloud.test.ts:16:// hoisted above this declaration) — same pattern as tests/integration/quickview-route-cloud.test.ts.
tests/integration/video-updated-at.test.ts:1:// tests/integration/video-updated-at.test.ts
tests/integration/backfill-titles.test.ts:1:// tests/integration/backfill-titles.test.ts
tests/integration/backfill-titles.test.ts:4:// live local Supabase stack. Run via: npm run test:integration -- backfill-titles
tests/integration/backfill-titles.test.ts:5:// Requires: stack up + .env.test.local present (see tests/integration/setup.ts).
tests/integration/backfill-titles.test.ts:20:describe('setPlaylistTitleIfNull integration', () => {
tests/integration/backfill-titles-route.test.ts:1:// tests/integration/backfill-titles-route.test.ts
tests/integration/backfill-titles-route.test.ts:4:// Supabase stack. Auth plumbing mocked exactly like tests/integration/playlists-route.test.ts
tests/integration/backfill-titles-route.test.ts:19:// hoisted above this declaration) — same pattern as tests/integration/playlists-route.test.ts.
tests/integration/storage-policy.test.ts:1:// tests/integration/storage-policy.test.ts
tests/integration/worker-main.test.ts:36:    // integration test files (e.g. job-queue-producer.test.ts intentionally leaves some
tests/integration/metadata-store.test.ts:1:// tests/integration/metadata-store.test.ts
tests/integration/metadata-store.test.ts:4:// Run via: npm run test:integration -- metadata-store
tests/integration/metadata-store.test.ts:5:// Requires: stack up + .env.test.local present (see tests/integration/setup.ts).
tests/integration/metadata-store.test.ts:21: *  validation — integration tests focus on store behaviour, not type fidelity. */
tests/integration/metadata-store.test.ts:38:describe('SupabaseMetadataStore integration', () => {
tests/integration/job-queue-producer.test.ts:1:// tests/integration/job-queue-producer.test.ts
tests/integration/schema.test.ts:1:// tests/integration/schema.test.ts
tests/integration/cost-guardrails.test.ts:1:// tests/integration/cost-guardrails.test.ts
tests/integration/cost-guardrails.test.ts:284:  // this test/file) — with the full integration suite creating real auth users across many
tests/integration/archive-route-cloud.test.ts:1:// tests/integration/archive-route-cloud.test.ts
tests/integration/archive-route-cloud.test.ts:4:// Supabase stack. Mirrors tests/integration/review-route-cloud.test.ts (Task 7): mock
tests/integration/archive-route-cloud.test.ts:17:// hoisted above this declaration) — same pattern as tests/integration/review-route-cloud.test.ts.
tests/integration/serve-config-invariant.test.ts:1:// tests/integration/serve-config-invariant.test.ts
tests/integration/serve-config-invariant.test.ts:7:// ORDER-SAFETY (Codex Critical #2): the full `test:integration --runInBand` suite shares ONE DB,
tests/integration/concurrency.test.ts:1:// tests/integration/concurrency.test.ts
tests/integration/concurrency.test.ts:5:// Run via: npm run test:integration -- concurrency
tests/integration/annotations-rpc.test.ts:1:// tests/integration/annotations-rpc.test.ts
tests/integration/annotations-rpc.test.ts:4:// REAL local Supabase stack. Run via: npm run test:integration -- annotations-rpc
tests/integration/annotations-rpc.test.ts:5:// Requires: stack up + .env.test.local present (see tests/integration/setup.ts).
tests/lib/cloud-sync/registry.test.ts:26:  // live under $HOME (same constraint the cloud-sync integration harness works around).
tests/integration/pdf-cloud.test.ts:1:// tests/integration/pdf-cloud.test.ts
tests/integration/pdf-cloud.test.ts:5:// tests could only mock. Mirrors tests/integration/html-download.test.ts's auth-plumbing pattern:
tests/integration/pdf-cloud.test.ts:56:// hoisted above these declarations) — same pattern as tests/integration/html-download.test.ts.
tests/integration/provisioning.test.ts:1:// tests/integration/provisioning.test.ts
tests/integration/dig-serve-interactive.test.ts:1:// tests/integration/dig-serve-interactive.test.ts
tests/integration/dig-serve-interactive.test.ts:3:// Task 6 (cloud dig-deeper frontend slice): REAL local-Supabase integration proof that the
tests/integration/dig-serve-interactive.test.ts:7:// tests/integration/archive-route-cloud.test.ts (mock next/headers + @/lib/supabase/server
tests/integration/dig-serve-interactive.test.ts:9:// blob-seeding pattern from tests/integration/dig-cloud.test.ts (writeDigSectionBlob writer,
tests/integration/dig-serve-interactive.test.ts:22:// hoisted above this declaration) — same pattern as tests/integration/archive-route-cloud.test.ts.
tests/integration/dig-serve-interactive.test.ts:58:describe('cloud dig-deeper serve (integration, real DB) — interactive + no-charge', () => {
tests/integration/worker-runner-runtime.test.ts:13:// tests/integration/job-queue-worker.test.ts and job-queue-runner.test.ts.
tests/integration/cloud-sync/sync-run.int.test.ts:1:// tests/integration/cloud-sync/sync-run.int.test.ts
tests/integration/cloud-sync/sync-run.int.test.ts:3:// Stage 3 Cloud Sync (§7), Task 12 — the integration keystone for runSync. Runs against real local
tests/integration/cloud-sync/sync-run.int.test.ts:14:import { makeOwnerContext, seedLocalPlaylist } from '@/tests/integration/helpers/cloud';
tests/integration/cloud-sync/cloud-stamping.int.test.ts:1:// tests/integration/cloud-sync/cloud-stamping.int.test.ts
tests/integration/cloud-sync/cloud-stamping.int.test.ts:7:import { makeOwnerContext, seedVideo } from '@/tests/integration/helpers/cloud';
tests/integration/cloud-sync/stamping.int.test.ts:1:// tests/integration/cloud-sync/stamping.int.test.ts
tests/integration/cloud-sync/stamping.int.test.ts:8:// Runs against local Supabase (jest.integration.config.ts). Uses the shared integration
tests/integration/cloud-sync/stamping.int.test.ts:10:import { makeOwnerContext, seedVideo } from '@/tests/integration/helpers/cloud';
tests/integration/serve-doc-materialize.test.ts:33:// ── Owner-budget helpers (mirrors tests/integration/serve-owner-budget.test.ts — see that file's
tests/integration/gemini-live-gates.test.ts:3: * (Stage 1D). These are NOT part of the normal CI/integration run — they make real, billed
tests/integration/list-playlists.test.ts:1:// tests/integration/list-playlists.test.ts
tests/integration/cloud-sync/e2e.int.test.ts:1:// tests/integration/cloud-sync/e2e.int.test.ts
tests/integration/cloud-sync/e2e.int.test.ts:18:} from '@/tests/integration/helpers/cloud';
tests/integration/cloud-sync/e2e.int.test.ts:19:import { adminClient } from '@/tests/integration/helpers/clients';
tests/integration/job-queue-store.test.ts:1:// tests/integration/job-queue-store.test.ts
tests/integration/summary-handler.test.ts:1:// tests/integration/summary-handler.test.ts
tests/integration/summary-handler.test.ts:8:// Run via: npm run test:integration -- summary-handler
tests/integration/summary-handler.test.ts:9:// Requires: stack up + .env.test.local present (see tests/integration/setup.ts).
tests/integration/gemini-magazine-live.test.ts:9: * mirroring tests/integration/gemini-live-gates.test.ts.
tests/integration/html-download.test.ts:1:// tests/integration/html-download.test.ts
tests/integration/html-download.test.ts:24:// hoisted above this declaration) — same pattern as tests/integration/share-route.test.ts.
tests/integration/html-download.test.ts:90:// ── Stage 1G / Task 3 owner-budget helpers — replicated from tests/integration/serve-owner-budget.test.ts
tests/integration/quickview-route-cloud.test.ts:1:// tests/integration/quickview-route-cloud.test.ts
tests/integration/quickview-route-cloud.test.ts:4:// stack. Mirrors tests/integration/videos-route-cloud.test.ts (Task 5): mock ONLY the
tests/integration/quickview-route-cloud.test.ts:15:// hoisted above this declaration) — same pattern as tests/integration/videos-route-cloud.test.ts.
tests/integration/reservation-release.test.ts:502:    // guards against another integration file having mutated the shared guardrail_config singleton
tests/integration/reservation-release.test.ts:561:    // default, but guards against another integration file having mutated the shared singleton.
tests/integration/worker-storage-bundle.test.ts:1:// tests/integration/worker-storage-bundle.test.ts
tests/integration/serve-owner-budget.test.ts:1:// tests/integration/serve-owner-budget.test.ts
tests/integration/cap-soundness.test.ts:1:// tests/integration/cap-soundness.test.ts
tests/integration/helpers/cloud.ts:1:// tests/integration/helpers/cloud.ts
tests/integration/helpers/cloud.ts:3:// Shared integration harness for Stage 3 Cloud Sync (Tasks 3, 4, 12, 14). Reuses the existing
tests/integration/helpers/cloud.ts:78: *  every cloud-sync integration test. */
tests/integration/playlists-route.test.ts:1:// tests/integration/playlists-route.test.ts
tests/integration/playlists-route.test.ts:8:// metadataStore.listPlaylists) runs for real. Same pattern as tests/integration/html-download.test.ts.
tests/integration/playlists-route.test.ts:18:// hoisted above this declaration) — same pattern as tests/integration/html-download.test.ts.
tests/integration/dig-cloud.test.ts:1:// tests/integration/dig-cloud.test.ts
tests/integration/dig-cloud.test.ts:3:// Task 7 (cloud dig-deeper generation slice): end-to-end integration against a REAL local
tests/integration/dig-cloud.test.ts:4:// Supabase stack. Mirrors tests/integration/pdf-cloud.test.ts for owner-isolation + spend
tests/integration/dig-cloud.test.ts:5:// mutation-control, and tests/integration/summary-handler.test.ts for the direct-handler blob
tests/integration/dig-cloud.test.ts:42:  // dig is the FIRST integration path that goes through enqueue_preflight — pin its admission
tests/integration/dig-cloud.test.ts:66:describe('dig-cloud (integration, real DB)', () => {
tests/integration/helpers/seed.ts:1:// tests/integration/helpers/seed.ts
tests/integration/worker-persistence-rpcs.test.ts:1:// tests/integration/worker-persistence-rpcs.test.ts
tests/lib/html-doc/serve-doc-mapping.test.ts:2:// Unlike tests/integration/serve-doc-materialize.test.ts, these do NOT hit a real Supabase project:
tests/lib/dig/slide-crop.integration.test.ts:1:// tests/lib/dig/slide-crop.integration.test.ts
tests/lib/dig/slide-crop.integration.test.ts:7:describe('ffmpeg profile (integration — real ffmpeg)', () => {
tests/lib/storage/supabase-job-queue-cancel-playlist.test.ts:8: * in supabase-job-queue.ts). Owner-guard/cascade behavior is covered by the integration
tests/lib/storage/supabase-job-queue-cancel-playlist.test.ts:9: * suite (tests/integration/cancel-playlist-jobs.test.ts, delete-playlist-store.test.ts).
tests/integration/pdf-put-atomicity.test.ts:1:// tests/integration/pdf-put-atomicity.test.ts
tests/integration/pdf-put-atomicity.test.ts:32:// when STORAGE_BACKEND==='supabase' — same pattern as sibling *-cloud integration tests.
tests/integration/supabase-blob-delete-prefix.test.ts:1:// tests/integration/supabase-blob-delete-prefix.test.ts
tests/integration/supabase-blob-delete-prefix.test.ts:7:// Run via: npm run test:integration -- supabase-blob-delete-prefix
tests/integration/supabase-blob-delete-prefix.test.ts:8:// Requires: stack up + .env.test.local present (see tests/integration/setup.ts).
tests/integration/videos-route-cloud.test.ts:1:// tests/integration/videos-route-cloud.test.ts
tests/integration/videos-route-cloud.test.ts:9:// tests/integration/playlists-route.test.ts.
tests/integration/videos-route-cloud.test.ts:17:// hoisted above this declaration) — same pattern as tests/integration/playlists-route.test.ts.

codex
The intended integration runner is `npm run test:integration -- cloud-sync/e2e.int --runInBand`. I’ll try that targeted run; if the local Supabase prerequisites are not up, I’ll report that separately from the unit result.
exec
/bin/bash -lc 'npm run test:integration -- cloud-sync/e2e.int --runInBand' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 14141ms:

> youtube-playlist-summaries@0.1.0 test:integration
> jest --config jest.integration.config.ts --runInBand cloud-sync/e2e.int --runInBand

  console.warn
    [model-store] malformed JSON in models/v6b24f743c1eb.json — ignoring

      47 |   blobStore: BlobStore = localBlobStore,
      48 | ): Promise<void> {
    > 49 |   await blobStore.put(principal, MODEL_KEY(base), serialize(envelope), 'application/json');
         |                 ^
      50 | }
      51 |
      52 | /** Read + validate. Returns null if absent, unparseable, or schema-invalid. */

      at readModelEnvelope (lib/html-doc/model-store.ts:49:17)
      at async readModelSide (lib/cloud-sync/sync-run.ts:432:22)
          at async Promise.all (index 0)
      at async companionTransfer (lib/cloud-sync/sync-run.ts:379:42)
      at async runSync (lib/cloud-sync/sync-run.ts:664:31)
      at async Object.<anonymous> (tests/integration/cloud-sync/e2e.int.test.ts:974:20)

Test Suites: 1 passed, 1 total
Tests:       33 passed, 33 total
Snapshots:   0 total
Time:        11.538 s, estimated 12 s
Ran all test suites matching cloud-sync/e2e.int.

codex
**Verdicts**

L-R6-1: **GENUINELY FIXED**. In [companion.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/companion.ts:76), `senderMatch` / `receiverMatch` only hoist exact `sourceMdHash === winnerMdHash` checks. The both-match branch is correct:

- receiver current, sender any currentness -> `noop`, no downgrade
- receiver stale, sender current -> `ship`, real upgrade
- receiver stale, sender stale -> `noop`, no pointless stale write
- both current -> covered by receiver-current `noop`

Non-matching behavior is unchanged: sender `none` / `unknown` / legacy-no-hash / hash-mismatch all produce `senderMatch = null`; receiver `none` / `unknown` / legacy-no-hash / hash-mismatch all produce `receiverMatch = null`, then only receiver envelope with present non-matching `sourceMdHash` deletes at [companion.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/companion.ts:118). No new delete/keep/ship regression in those cells.

`decideCompanion` remains pure: it only imports `GENERATOR_VERSION`, reads object fields, and returns a value. No I/O.

`GENERATOR_VERSION` is the right freshness tie-breaker here. With both envelopes matching `winnerMdHash`, the MD body is byte-identical. `sourceSections` should only differ if an older parser/generator produced different title extraction, and that is exactly represented by generator-version skew. `isFresh` still performs the full `sourceSections + generatorVersion` check at [read-model.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/read-model.ts:20); the tie-break only prevents writing an older generator over a current receiver.

M-R6-1: **GENUINELY FIXED**. `writeModelEnvelope` is wrapped at [sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:404). On failure, `companionTransfer` returns `shareNeedsOwnerServe: true` plus an error, the caller records it at [sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:641), and baseline still advances at [sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:650). That is correct because Class-A has already committed durably, and a rerun would hit `skip` and not retry the companion ship.

`report.errors` contract looks intact. The CLI already exits `2` for any non-empty `errors` at [cloud-sync.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/cloud-sync.ts:68), but the JSON report still exposes the partial success counters and advanced baseline. Existing per-video errors already had this “visible fault, not total rollback” shape.

Partial-write concern: no new issue found. Local model `put` is temp-file then rename; Supabase model `put` is storage upload with `upsert: true`; if corrupt bytes ever exist, `readModelEnvelope` rejects malformed/schema-invalid JSON and returns `null`, so a later read does not misclassify it as fresh.

**New Findings**

None.

**Verification**

- `npx jest tests/lib/cloud-sync/companion.test.ts --runInBand`: passed, 31 tests.
- `npm run test:integration -- cloud-sync/e2e.int --runInBand`: passed, 33 tests.

**CONVERGED**
tokens used
72,043
**Verdicts**

L-R6-1: **GENUINELY FIXED**. In [companion.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/companion.ts:76), `senderMatch` / `receiverMatch` only hoist exact `sourceMdHash === winnerMdHash` checks. The both-match branch is correct:

- receiver current, sender any currentness -> `noop`, no downgrade
- receiver stale, sender current -> `ship`, real upgrade
- receiver stale, sender stale -> `noop`, no pointless stale write
- both current -> covered by receiver-current `noop`

Non-matching behavior is unchanged: sender `none` / `unknown` / legacy-no-hash / hash-mismatch all produce `senderMatch = null`; receiver `none` / `unknown` / legacy-no-hash / hash-mismatch all produce `receiverMatch = null`, then only receiver envelope with present non-matching `sourceMdHash` deletes at [companion.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/companion.ts:118). No new delete/keep/ship regression in those cells.

`decideCompanion` remains pure: it only imports `GENERATOR_VERSION`, reads object fields, and returns a value. No I/O.

`GENERATOR_VERSION` is the right freshness tie-breaker here. With both envelopes matching `winnerMdHash`, the MD body is byte-identical. `sourceSections` should only differ if an older parser/generator produced different title extraction, and that is exactly represented by generator-version skew. `isFresh` still performs the full `sourceSections + generatorVersion` check at [read-model.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/read-model.ts:20); the tie-break only prevents writing an older generator over a current receiver.

M-R6-1: **GENUINELY FIXED**. `writeModelEnvelope` is wrapped at [sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:404). On failure, `companionTransfer` returns `shareNeedsOwnerServe: true` plus an error, the caller records it at [sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:641), and baseline still advances at [sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:650). That is correct because Class-A has already committed durably, and a rerun would hit `skip` and not retry the companion ship.

`report.errors` contract looks intact. The CLI already exits `2` for any non-empty `errors` at [cloud-sync.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/cloud-sync.ts:68), but the JSON report still exposes the partial success counters and advanced baseline. Existing per-video errors already had this “visible fault, not total rollback” shape.

Partial-write concern: no new issue found. Local model `put` is temp-file then rename; Supabase model `put` is storage upload with `upsert: true`; if corrupt bytes ever exist, `readModelEnvelope` rejects malformed/schema-invalid JSON and returns `null`, so a later read does not misclassify it as fresh.

**New Findings**

None.

**Verification**

- `npx jest tests/lib/cloud-sync/companion.test.ts --runInBand`: passed, 31 tests.
- `npm run test:integration -- cloud-sync/e2e.int --runInBand`: passed, 33 tests.

**CONVERGED**
