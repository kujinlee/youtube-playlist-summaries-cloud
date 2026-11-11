---
name: push-is-mine-merging-is-theirs
description: "FIRES-WHEN: about to push, or about to ask whether to push"
metadata:
  node_type: memory
  type: feedback
  originSessionId: a6abe358-4c0b-44cb-a058-5446372998ef
  modified: 2026-10-25T03:39:00.971Z
---

⛔ **PUSH WITHOUT ASKING. Merging is the gate; pushing never was.** The user, 2026-09-30:
*"you don't need to ask me for git push. just do it when it is necessary."*

⭐ **THE ORIGINAL RULE'S RATIONALE, traced — because the user asked whether I knew it, and I did
not.** The line entered at `e09e1edf` (2026-07-12), the Conditional-AFK commit: *"…or an
outward-facing/irreversible step like push/merge/deploy."* The category was **outward-facing AND
irreversible**, and the defect was the GROUPING: merge and deploy are hard to reverse and affect
everyone, while **pushing a feature branch is trivially reversible and affects nobody**. ⛔ And the
irreversible half is guarded by a MACHINE — `block-default-branch-push.sh` blocks the default
branch, bare `--force`, and `--no-verify` on every Bash call. The prose was redundant where it
mattered and over-broad where it did not.
⚠ **I removed it before knowing any of that.** The outcome was right and the justification was
missing; I argued from a doc contradiction instead of from the rule's purpose. **Read why a rule
exists before deleting it, even when told to delete it.**

⚠ **It also resolves a real contradiction in the repo's own docs, so do not re-derive it.**
`docs/dev-process.md:106` says *"Merging stays a human gate: open the PR, notify, do not merge"* —
which makes push+PR the standard path. `:36` lists *"push"* among outward-facing actions needing the
human. Specific beats general, and the user has now ruled explicitly. **The ruling governs.**

⭐ **Why it cost something.** On 2026-09-30 I sat on 19 commits for a whole session, asked about
pushing three separate times, and closed several messages with *"nothing has left this machine."*
The user's reply was not "yes push" — it was that I should not have been asking. **Turning my own
incomplete step into their decision is the pattern**; that session did it three times (a dashboard
card, the push framing, and a dual-review half I should simply have run).

**How to apply.** Push when the work is committed and would otherwise exist on one disk. Push a
branch that must NEVER merge too — preservation is a reason on its own, and backlog #190 measured
that an unpushed branch is recoverable but *not findable*; just open no PR on it.
⚠ **A PR is a separate judgement**: do not open one for work that is NOT CONVERGED, because a PR
asserts the work is ready for the human gate.
⛔ **EXCEPT A DRAFT PR, opened at slice start — that is HOW THE FULL MUTATION SWEEP RUNS** (on CI's
shards; owner's decision, velocity spec, restated 2026-10-25). A draft asserts nothing about readiness.
This line once read as "no PR until converged" with no exception, and on 2026-10-25 it beat the
unloaded spec that said otherwise: no draft PR → no CI sweep → ~3.5h of local sweeps. See
[[scoped-mutation-run-in-four-seconds]]. Check CI triggers first — here CI runs only on PRs to
master and pushes to master, so a feature-branch push starts nothing.

See [[process-conventions]], [[a-stacked-pr-dies-with-its-base-branch]],
[[defaults-i-decide-myself]].

⟳ **2026-10-23 23:19 — A SCOPED MERGE GRANT, not a reversal.** Going to sleep, the user said: *"you can
merge finished ones when they are merge ready. No need to wait for me for backlog fixes."* Read it
narrowly: **backlog-fix PRs during that overnight run**, merged only when `check-merge-ready.py --pr N`
prints READY, squash with `--match-head-commit` pinned to the reviewed head. It is NOT a standing
change to "merging is theirs" — approval in one context does not extend to the next. Ask again
next time, or quote this line with its date if the same night's work is still running.

⟳ **2026-10-24 20:38 — the SAME SCOPED GRANT, given again for that night:** *"continue in AFK for sleep,
merge backlog fix PRs when they are ready."* Same reading: backlog-fix PRs from that night's run, merged
only on `check-merge-ready.py --pr N` READY, squash, `--match-head-commit` pinned. ⚠ Earlier that evening
(18:00–20:37) there was NO grant, and PRs were left READY-but-unmerged — that was correct, not timidity.
Two grants on consecutive nights is a pattern, not a standing rule: still ask (or quote the dated line).

⟳ **2026-10-25 07:33 — A THIRD SCOPED GRANT, given while AFK:** *"merge PRs when they become mergeable."*
Given mid-wait on PR #398 (trigger 4 → WARN pending backlog #327), with PR #397 queued behind it. Same reading:
the PRs of THAT run (#398, then #397 once it carries master), merged only on `check-merge-ready.py --pr N`
READY — ⚠ run FROM THE PR's WORKTREE, since it compares the PR head to the local HEAD — squash,
`--match-head-commit` pinned. Not standing: ask again next session.

⛔⟳ **2026-10-25 ~07:50 — SUPERSEDED BY A HOUSE RULE: MERGE WHEN READY.** The owner, after three scoped grants
in three days: *"Let's make this a house rule so that I don't need to specify the condition all the time. For
exceptions, hold the merge and let me know."* The grant entries above are now HISTORY.
**How to apply:** for every PR, run `scripts/check-merge-ready.py --pr N` **from the PR's own worktree** (it
compares the PR head to the local HEAD). **0 READY ⇒ squash-merge, `--match-head-commit` pinned. 3 HOLD ⇒ do
NOT merge; PushNotification the owner with the printed reason.** The exceptions, chosen on a card against base
rates over 30 merged PRs: a LOOSENING of a gate (baseline edit, pin/total/case-count drop, a removed line within
5 of a failure path in a gate file — 5/30), a migration (deploy first), a `NO-REVIEW:` waiver (NO-ENTRY does not
hold), and app code without a local `test:integration` + `test:e2e` run at that head — which I run myself, then
pass `--app-tests-passed <head>`. ⚠ Deploy is still the owner's; a merge HOLD is theirs. Branch `merge-when-ready-rule`.
