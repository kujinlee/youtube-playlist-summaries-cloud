---
name: blob-addressing-spec-state
description: "FIRES-WHEN: resuming or citing the stable blob addressing spec — Stable blob addressing spec — ALL FOUR handoff items merged (PRs #51-#55); 89 assertions, 35/35 mutations; round 7 (cross-derive all four) is the next gate"
metadata: 
  node_type: memory
  type: project
  originSessionId: 18820d36-e0cd-46c7-945b-e5f3417ebb5f
  modified: 2026-08-08T20:25:22.188Z
---

**Merged 2026-08-06: PR #51, squash `a4a410b`.** Docs + spec-adjacent SQL only — zero files under
`lib/ app/ supabase/ worker/ scripts/ components/ tests/`, so merging shipped nothing executable.

**Still NOT CONVERGED** after six dual adversarial rounds (7 → 8 → 10 → 6 → 7 → 8 Blocking).
Merged anyway because the branch was at 33 commits and nothing in it runs.

**The artifact is executable.** `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/`
plus `verify-schema.sh` — runs against the live local Postgres in a rollback, **57 assertions**, each
naming the guard that rejected it. Deliberately NOT in `supabase/migrations/` (that directory is
auto-applied by the integration suite and the design has not converged). Promote when it does.
`mutate-schema.py` sits beside it — a committed mutation harness with three outcomes
(RED / GREEN / INVALID), because a two-outcome one reports its own broken edit as an untested guard.

**Handoff item 1 (`detached` fencing) — ✅ MERGED, PR #52, squash `7e26f58` (2026-08-06).** Of four
measured bypasses, 2 fixed (`P1` delete-after-detach, `P1b` repoint-after-detach), 1 closed by
`art_detached_is_dig` (only a dig may be detached), and **1 was never a defect**. See
[[detached-dig-retention-decision]] for the rule that dissolved it.

**Handoff item 2 (corrections representation) — ✅ MERGED, PR #53, squash `610a31c` (2026-08-06).**
Rung 1 diverged for the whole corpus ⇒ `copyToCloud` on every sync, forever. Fixed by NOT NULL (the
nullable column conflated "no corrections" with "never computed"), a backfill, and a trigger that
stops the denormalized copy drifting. Reverses round 5's C2. See [[defined-not-derived-constants]]
for the move that decoupled it from backlog #23.

**Stacked-PR footgun, learned the hard way here:** `gh pr merge --squash --delete-branch` on the
PARENT **closes** the child PR instead of retargeting it, and then you are stuck — GitHub refuses to
retarget a closed PR and refuses to reopen one whose base branch is gone. Recovery: push the old base
commit back to recreate the branch, reopen, retarget to `master`, delete the branch, then
`git rebase --onto origin/master <old-base-tip>` to drop the commits the squash already absorbed.
Do it in the other order next time: retarget the child FIRST, then merge and delete the parent.

**Handoff item 4 (the reservation protocol) — ✅ MERGED, PR #54, squash `ccc7eb7` (2026-08-07).**
`reserve_artifact_slot` / `renew_artifact_lease` / `record_artifact` replace the round-5 reclaim.
**The reviewer's fix was DECLINED on purpose** — see [[reservation-guards-spending-not-recording]].
73 assertions, 22/22 mutations as expected.

**Handoff item 3 (the generation-write API) — ✅ MERGED, PR #55, squash `1cd884a` (2026-08-07).**
**ALL FOUR ITEMS ARE NOW IN.** Measured defect was bigger than "md_hash has no producer": a cloud
summarize could not reserve a summary slot **at all** — `[23503]` on the artifact FK one way,
`[23514] gen_card_complete` the other, with the paid Gemini call between them. `video_generations`
gained `state` (`pending|complete`, **defaulting to complete**, which is the fail-*closed* default);
the four summary CHECKs gate on it; an artifact-side trigger — **not the gate** — is what stops the
relaxation being a bypass. **89 assertions, 35/35 mutations**, verified on merged `master`.
See [[unsatisfiable-ordering-is-the-tell]] for the pattern this shares with items 1 and 2, and
[[what-mutation-testing-proves]] for the harness bug it exposed.

Closed by item 3 as well: **task #25 dissolved with zero schema change** (`digDeeper` was never bound
to one generation — the FK carries `kind`, so it points at a *digDeeper* generation minted per
rewrite; **third** time a finding came from reasoning about a NAME rather than reading the
constraints), and item 1's `INSERT`-path `detached_at` gap, closed by **bounding** the clock to the
artifact's real lifetime rather than forbidding a supplied value, which sync needs.

**ROUND 7 — NOT CONVERGED (2 Blocking, 3 High, 5 Medium). ✅ FIXES MERGED, PR #56, squash `aad6aee`
(2026-08-07).** **98 assertions, 41/41 mutations**, verified on merged `master`.

**The framing was the finding.** Every Blocking and High was an interaction between two of the four
items and a defect in **none individually** — reproducing round 6's cross-derivation verdict under
the same condition. Both reviewers independently **confirmed** the 89/89 and 35/35 claims as TRUE, so
the defects were all things neither instrument could see. Through-line: item 3 gave the generation a
lifecycle, every fence item 4 built was on the **artifact**, and none followed to the new table.

**B1 is the one to remember: a rule can be overturned by a change that never mentions it.** The
2026-08-07 decision (*the reservation guards spending, not recording*) was silently restored as a
rejection by item 3's freeze trigger — written a day later, in a different file, for an unrelated
reason. Measured as `[23505]` on a worker that merely RESTARTED and forgot its token; no race needed.

**Guard classification + 2 ratchets — ✅ MERGED, PR #57, squash `0b27094` (2026-08-08).** Ran BEFORE
round 8 and found **two defects seven review rounds missed**, both SEQUENCE guards expressed as
rejecters: free renders could never be overwritten (raw `23505` on every re-render — an entire *kind*
of write unreachable) and §8's retention sweep could never run (batch aborted on a permanently-current
row). Also split `dev-process.md` 576 → 190 four ways with CI-enforced line budgets. **103 assertions,
44/44 mutations, 32 guards classified.** See [[guard-classification-shape-vs-sequence]].

**ROUND 8 — NOT CONVERGED (3 Blocking, 5 High, 6 Medium). ✅ ALL FIXES MERGED, PR #58, squash
`dc92859` (2026-08-08).** **119 assertions, 58/58 mutations, 38 guards classified**, verified on
merged `master`. Reviews at `docs/reviews/spec-blob-addressing-r8-{codex,claude,coordinator}.md`.
Both reviewers ran at full strength for the first time (Codex reached Docker), and BOTH re-measured
the 103/44 claims as true — so every defect was something no instrument could see.

**ROUND 10 IS MANDATORY** — round 8 did not converge and PR #58 is entirely new text, which this
spec has repeatedly shown to be the most dangerous kind (round 7's two Blockings were each created
by an earlier round's own fix). Still open: round 8's two Lows (`recorded_after_token_loss` on a
plain idempotent retry; the span recovery justifying only `start_sec`) and `persist_summary` merge
semantics, which neither reviewer could produce a measured failure for — see
[[worker-vs-sync-fencing-gap]]. Promotion into `supabase/migrations/` is still a separate slice and
is the first thing here that touches running infrastructure.

**What round 9 changed, in one line each:** the ownership fence now uses `(worker_id, job_id)`
(see [[a-fence-wrong-both-ways-asks-the-wrong-credential]]); the workspace chain got a producer at
all FOUR levels (profiles→workspaces→playlists→videos/jobs, each seeded once); GC's floor gained
`state = 'complete'`; `produced_at` gained a 5-minute skew tolerance; the free path got a reachable
short-circuit (`NULL = NULL` is never true), a lease-clearing upsert, and tenant confinement; and a
divergent `blob_key` now raises instead of being silently dropped.

**Every function in the schema pins its `search_path`** except `assert_raises`, which is labelled as
the deliberate exception. That rule exists because the same class of bug appeared **four times in one
day** — the last reached from a definer function *through a CHECK constraint*, invisible at every
direct call site. Don't remove a pin to "simplify".

Read `3fb6970` before trusting any verification claim from round 5 or earlier — see
[[test-harness-can-launder-failures]], and note PR #52 hit the *same class twice more* in tests
written that hour.
