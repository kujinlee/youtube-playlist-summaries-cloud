---
name: defaults-i-decide-myself
description: "FIRES-WHEN: about to ask the user about a small spend, a cheap experiment, verification depth, or a bounded prod write — ⭐ Standing permissions: small decisions are mine (money, a bounded prod-data write, a cheap reversible experiment — the TEST, not the list; measure the ledger anyway), and lighter verification is the DEFAULT (CI runs the mutation sweep; run it locally only for a DELETION or NEW manifest entries). ⛔ NOT the CI wait — `--auto` is unsafe here"
metadata:
  type: feedback
---

**CURRENT RULE — small decisions are mine. The test, on ANY axis:**

> *Is the thing I am about to ask about CHEAPER TO RUN THAN TO ASK ABOUT, and reversible?*
> If yes, RUN IT and bring the result — and report what it cost and what it bought.

What stays the user's: spend that is open-ended or irreversible, deploy, moving the goal, and a merge that
`check-merge-ready.py` HOLDS (owner 2026-10-25: MERGE WHEN READY — `docs/dev-process.md`; see
[[push-is-mine-merging-is-theirs]], [[a-gate-can-be-blocked-on-a-decision-not-work]]). A thrashing review
*arms* an architecture review; it does not turn a cheap experiment into a human gate.

**⚠ NO standing money threshold exists, deliberately.** The user: *"Let's see how frequently this kind of
cost related decision is made. if frequent enough, that would be the time to have some default value that
you can spend your own."* Do not invent one; keep counting occurrences (3 so far — money, prod data,
compute/time). Keep measuring money either way — the before/after ledger read stays mandatory.

**CURRENT RULE — lighter verification is the DEFAULT:**
- **Skip the local mutation sweep for additive work**; CI runs it (the FULL sweep is CI's, on shards;
  locally `check-plan-code.py --mutate .` is PARTIAL and refuses runs estimated past 10 min — use
  `--only <script>`; `docs/process-checklists.md`).
- **Run it locally, once, last** (`--mutate . --only <script>`) for a **DELETION of code or cases**
  (2026-09-09) and for **NEW mutation-manifest entries** (2026-09-20). Cheap partial substitute for a
  manifest edit: assert every entry's `(name, tuple(edits))` is distinct across the file.
- **Do not re-run the full gate battery twice** or re-verify what this session already measured.
- **Keep:** the control run when adding/changing a guard; the browser pass when what a reader sees
  changes; the self-tests and gates guarding the files touched.
- ⛔ **NOT the CI wait. Never `gh pr merge --auto` here** — unpredictable (once merged immediately over a
  running check and put a red on master; once refused). Wait for CI, then merge explicitly. Agents do not
  wait on CI — the coordinator polls in a background shell ([[agent-blocking-call-over-5-min-rewrites-its-cache]]).
  Never read a CI exit through a pipe: redirect, then `echo $?`.

**Why:** the user pays wall-clock for verification CI duplicates, and a round-trip on a question whose
answer is already written can cost a whole night. This trades local latency for CI latency; it does NOT
lower the bar — "cannot run" is still a failure and a red is still a stop ([[a-test-that-cannot-fail]]).

> Merged 2 memories. Former names (still referenced by other memories): `small-spend-decisions-are-mine`, `feedback-lighter-verification-mode`

## History

**Axis 1 — money, 2026-08-17.** I asked whether to spend ~8¢ proving backlog #36 fixed in prod (+150¢
reserved, ~8¢ real). User: *"8 cent expense isn't something you should hesitate to decide yourself."*
Not spending would have left "deployed, unverified" sounding like "fixed". See
[[putting-a-choice-to-the-user]], [[a-retrospective-number-needs-provenance]].

**Axis 2 — prod data, 2026-08-24.** I declined to run the slice-A live verification because it writes to a
real summary in the prod account. User: *"let's prioritize progress and avoid stopping due to small fee or
other small decisions"*. Proceeding found a Blocking prod defect within one press
([[a-mocked-boundary-tests-the-contract-you-imagined]]).

**Axis 3 — a review round, 2026-10-06.** PR #366 had thrashed three rounds; my A/B/C card's own option A
said round 4 would decide patch-vs-redesign, and I waited ~7 hours overnight. User: *"your recommended
option (A) costs about 15 min of experiment which will decide whether fix by patching or redesign. If that
is the case why haven't you go ahead and find decisive evidence? Instead you paused whole night waiting for
me. If cost is small or revertable, just make progress instead of halting indefinitely"*. If an option's own
rationale is "this produces decisive evidence", it is the work, not a fork. The next re-litigation will be on
a fourth axis — apply the TEST. Same failure from the other side:
[[a-retreat-you-author-for-yourself-is-not-a-gate]].

**Lighter verification, set 2026-09-01** after PRs #194/#195 drew *"why does this take so long?"* (I had run
the ~4-min local sweep twice). Same day, **`--auto` merged PR #197 immediately while `verify` was
`IN_PROGRESS`** (auto-merge is not enabled here); the check then failed on master (an anchor orphaned by the
same PR). Skipping the local sweep "because CI runs it" is sound only if CI is awaited.
⟳ 2026-09-20: PR #324, all green → merged immediately; PR #326, checks pending → refused
(`GraphQL: Auto merge is not allowed for this repository (enablePullRequestAutoMerge)`). I rediscovered this
and called it new ([[it-already-exists-under-a-name-i-didnt-search]]). PR #175 shipped a visual change
without a browser pass → six defects in two rounds. The control run proved two shipped cases vacuous on
2026-09-01 ([[the-control-refuted-the-premise]], [[fixing-a-premise-is-not-covering-the-branch]]).

**Deletion exception, 2026-09-09** (PR #271). Skipped local sweep; CI red: **3 survivors + 2 `expect` fields
matching 0 red cases** over a local suite at **74/74** and seven gates rc=0 — the deleted region held the only
red cases of five mutations. `--self-test` cannot see a case that no longer exists. And
`gh pr checks --watch | tail` exited **0** (`tail`'s) over a failing run. See [[a-mutation-loses-its-binding]],
[[a-hang-is-not-a-diagnosis]], [[a-check-result-is-not-the-claim]].

**Manifest exception, 2026-09-20** (PR #324). My per-entry loop passed **12/12**; CI refused: *"entry '…'
repeats the edit anchors of an earlier entry — it measures nothing new"*. Uniqueness is a property of the SET.
The fix was to SPLIT THE CONDITION so each half owns an anchor, not to rename the entry.
