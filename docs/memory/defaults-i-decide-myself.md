---
name: defaults-i-decide-myself
description: "FIRES-WHEN: about to ask the user about small spend, verification depth, or a bounded prod write — ⭐ Standing permissions: small spend decisions are mine (incl. a bounded prod-data write — measure the ledger anyway), and lighter verification is the DEFAULT (skip local `--mutate .`, CI runs it). ⛔ NOT the CI wait — `--auto` is unsafe here"
metadata:
  type: feedback
---

> Merged 2 memories, bodies kept VERBATIM. Former names (still referenced by other memories): `small-spend-decisions-are-mine`, `feedback-lighter-verification-mode`

## small spend decisions are mine

**Do not escalate a small, purposeful spend as if it were a gate.** User, 2026-08-17, after I asked
whether to spend ~8¢ proving backlog #36 was actually fixed in production:

> *"8 cent expense isn't something you should hesitate to decide yourself."*

**Why:** the question wasn't a real fork. The spend was routine, bounded, and directly bought the one
thing missing — an *observation* instead of an *inference*. Handing it back cost the user a
round-trip and delayed the answer, which is the failure mode
[[putting-a-choice-to-the-user]] already names. It also inverted the actual risk: not spending
would have left the status as "deployed, unverified" while sounding like "fixed".

**How to apply:** for a bounded verification spend in this class, decide, spend, and *report what it
cost and what it bought*. Reserve the ask for genuinely irreversible or open-ended spend. Keep
measuring the money either way — the before/after ledger read is the part that stays mandatory.

**⚠ NO standing limit exists yet, and that is deliberate.** The user explicitly declined to set a
default number now:

> *"Let's see how frequently this kind of cost related decision is made. if frequent enough, that
> would be the time to have some default value that you can spend your own."*

So: **do not invent a threshold and do not treat this as one.** The open task is to *notice and
record* when a spend decision comes up, so the frequency question can be answered from data rather
than impression — the same discipline as [[a-retrospective-number-needs-provenance]]. Occurrences so
far: **2**.

1. 2026-08-17 — the #36 prod verification: +150¢ reserved, ~8¢ real Gemini cost.
2. 2026-08-24 — I declined to run the slice-A live verification myself because it **writes to a real
   summary document in the production account**, and handed the call back. The user widened the rule
   rather than answering it:

   > *"let's prioritize progress and avoid stopping due to small fee or other small decisions"*

**⭐ THE RULE IS NOT ABOUT MONEY.** It is about small decisions generally — a ~1¢ spend and a bounded,
recoverable write to the user's own prod data are both mine. The escalation reflex re-derived itself
from a *different* premise (data, not cost) and produced the same stall, which is the tell that the
narrow version of a rule gets re-litigated on the next axis. Reserve the ask for genuinely
irreversible, outward-facing, or open-ended actions. **And the payoff was concrete: proceeding found
a Blocking defect in production within one press** (see [[a-mocked-boundary-tests-the-contract-you-imagined]]).

## feedback lighter verification mode

**Lighter verification is the DEFAULT.** Set 2026-09-01 after a session that shipped two PRs
(#194, #195) and drew *"why does this take so long?"*.

## Drop these

- **`python3 scripts/check-plan-code.py --mutate .` locally.** ~4 min a run; it spawns a full suite
  per mutation (140 of them). **CI runs it anyway** (`.github/workflows/ci.yml`), so skipping it
  locally costs a later red, not a missed defect. I ran it *twice* in that session because I added a
  manifest entry after the first pass — if a local run is genuinely needed, batch all manifest
  changes and run it **once, last**.
- ⛔ **NOT the CI wait. `--auto` DOES NOT QUEUE ON THIS REPO — measured 2026-09-01, and it put a red
  on master.** Auto-merge is not enabled here, so `gh pr merge --auto` silently falls back to
  merging **immediately**. PR #197 merged while `verify` was `IN_PROGRESS`; the check then ran on
  master and failed (a mutation anchor orphaned by the same PR's colour retune). **Two decisions
  compounded**: skipping the local `--mutate .` *because CI runs it* is sound ONLY if CI is actually
  awaited. Together they are how a red reaches the trunk.
  **So: keep waiting** — `gh pr checks <n> --watch --fail-fast`, then merge. Re-enable the `--auto`
  shortcut only after confirming `gh repo view --json autoMergeAllowed` is true.
  [[a-check-result-is-not-the-claim]] applies to a check that has not finished, not just one that went red.
  ⟳ **RE-MEASURED 2026-09-20, and it did NOT behave as recorded — so trust neither shape.** Two runs
  the same evening: PR #324, every check already green -> merged immediately (benign, and it LOOKED
  like `--auto` working). PR #326, checks not yet reported -> **REFUSED outright**:
  `GraphQL: Auto merge is not allowed for this repository (enablePullRequestAutoMerge)`. So today it
  errored where 2026-09-01 saw it silently merge. ⚠ The safe reading is that `--auto` is
  *unpredictable* here, not that it is now safe: one of its two observed behaviours put a red on
  master. Keep waiting on CI and merge explicitly.
  ⚠ I also REDISCOVERED this the hard way — hit the refusal, called it a new finding, and only found
  this bullet when going to write it down. [[it-already-exists-under-a-name-i-didnt-search]].
- **Re-running the full gate battery more than once**, and re-verifying things already measured this
  session.

## Keep these — they are cheap, or nothing else covers them

- **The control run when adding or changing a guard.** Seconds on a temp copy, and it is the whole
  difference between a guard and a decoration: on 2026-09-01 it proved two shipped cases were
  vacuous. See [[the-control-refuted-the-premise]] and
  [[fixing-a-premise-is-not-covering-the-branch]].
- **The browser pass when the change alters what a reader sees.** No script closes that gate, and
  PR #175 shipped a cross-page visual change unreviewed → six defects in two rounds.
- **The self-tests and the gates guarding the files actually touched.** Fast, and `check-docs` /
  `check-selftest-counts` catch stale declared counts that nothing else reads.

**Why:** the user is paying wall-clock for verification that is either duplicated by CI or already
done. Thoroughness that repeats itself is not thoroughness.

⚠ **This trades local latency for CI latency; it does NOT lower the bar.** "Cannot run" is still a
failure, a red is still a stop, and a claim still needs a measurement — see
[[a-test-that-cannot-fail]].

---

## ⭐ QUALIFIED 2026-09-09 — RUN `--mutate .` LOCALLY FOR A DELETION. It is the only gate that sees one.

`retire-plan-mode` PR 2 (#271) followed this note and skipped the local run. CI went **red**:
**3 survivors + 2 `expect` fields matching 0 red cases**, over a local suite at **74/74 green**
with all seven doc/ratchet gates rc=0. Five mutations guarding code the PR did not touch lost
their only red case, because that case lived in the deleted region. See
[[a-mutation-loses-its-binding]].

**The rule stands for ADDITIVE work and is wrong for DELETIONS**, and the reason is structural,
not a matter of care: `--self-test` cannot see a case that no longer exists — it is green *by
construction*. `--mutate .` is the only instrument that checks both ends of a mutation, the anchor
AND the case. A deletion is exactly the change that can break the second end while every local
signal stays green.

    additive / a fix / a new guard   -> skip it, CI runs it        (unchanged)
    a DELETION of code or cases      -> RUN IT LOCALLY, once, last

**The cost of skipping it was not the CI red** — that is cheap. It was that the red arrived after
the PR was open and described as verified, so the write-up had to be corrected in public.

⚠ **And the red was nearly missed.** `gh pr checks --watch | tail` reported exit **0** — `tail`'s,
not `gh`'s — over a failing run, while being used as the MERGE signal. Redirect, never pipe:
`gh pr checks <n> --watch > /tmp/ci.txt 2>&1; echo $?`. See [[a-hang-is-not-a-diagnosis]].

---

## ⭐⭐ QUALIFIED AGAIN 2026-09-20 — ALSO RUN IT WHEN YOU ADD MANIFEST ENTRIES. CI's check is STRONGER than a local loop, not merely slower.

PR #324 added two mutation entries. I verified them the way I had verified every entry all
session, with a loop that for each entry checks (i) the `edits` anchor resolves EXACTLY ONCE in
the delivered source and (ii) the mutation reds the case its `expect` names. **12/12 passed.** CI
then refused the manifest:

    ✗ check-merge-ready.json: entry '…' repeats the edit anchors of an earlier entry
      — it measures nothing new

**Both entries anchored the same compound condition**, so the second pinned nothing the first
already did. ⛔ **My loop could not have caught it, and the reason is structural rather than
careless: anchor-resolves-once and kills-through-its-case are PER-ENTRY properties. Uniqueness is
a property of the SET, and I never checked the set.** Every entry was individually valid while the
manifest as a whole was not.

**So the earlier framing — "skipping the local run costs a later red, not a missed defect" — was
right about DEFECTS and wrong about COVERAGE.** `--mutate .` is not a slower copy of what a local
loop does; it enforces manifest-level invariants (distinct anchors, distinct names, the declared
count, the pinned sum) that no per-entry check reaches.

    additive code / a fix / a new guard   -> skip it, CI runs it          (unchanged)
    a DELETION of code or cases           -> RUN IT LOCALLY, once, last   (2026-09-09)
    NEW MUTATION-MANIFEST ENTRIES         -> RUN IT LOCALLY, once, last   (2026-09-20)

⚠ **The cheap partial substitute, if the full run is too slow:** after editing a manifest, assert
the SET property directly — every entry's `(name, tuple(edits))` distinct across the file. Three
lines, instant, and it is the exact invariant CI refused on. A per-entry loop plus this is most of
what the full run buys for a manifest-only change.

⚠ And the fix was to SPLIT THE CONDITION, not to rename the entry: "is this a comment" and "does
this line mention gating" are two decisions that read better apart and each then owns an anchor.
Renaming would have satisfied the guard while leaving one line with two mutations pointed at it.
See [[a-mutation-loses-its-binding]] — the same file had an anchor orphaned FOUR
times in one session, which is the other half of this: manifest entries are coupled to source
lines, and both ends move.

