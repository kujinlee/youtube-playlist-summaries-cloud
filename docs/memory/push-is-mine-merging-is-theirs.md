---
name: push-is-mine-merging-is-theirs
description: "FIRES-WHEN: about to push, or about to ask whether to push"
metadata:
  type: feedback
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
asserts the work is ready for the human gate. Check CI triggers first — here CI runs only on PRs to
master and pushes to master, so a feature-branch push starts nothing.

See [[process-conventions]], [[a-stacked-pr-dies-with-its-base-branch]],
[[defaults-i-decide-myself]].
