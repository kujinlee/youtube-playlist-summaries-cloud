---
name: push-is-mine-merging-is-theirs
description: "FIRES-WHEN: about to push, about to ask whether to push, or a PR is ready / HOLDs at the merge gate"
metadata:
  node_type: memory
  type: feedback
  originSessionId: a6abe358-4c0b-44cb-a058-5446372998ef
  modified: 2026-10-25T03:39:00.971Z
---

## The rule (current — the slug's "merging is theirs" is HISTORY)

1. ⛔ **PUSH WITHOUT ASKING** (owner 2026-09-30: *"you don't need to ask me for git push. just do it when it is
   necessary."*). Push when work is committed and would otherwise exist on one disk — including a branch that must
   never merge (backlog #190: an unpushed branch is recoverable but *not findable*; just open no PR on it).
2. ⛔ **MERGE WHEN READY — house rule since 2026-10-25, re-stated 2026-11-06.** Run `scripts/check-merge-ready.py --pr N`
   **from the PR's own worktree** (it compares the PR head to the local HEAD). **0 READY ⇒ squash-merge,
   `--match-head-commit` pinned. 3 HOLD ⇒ I VERIFY the HOLD line by line** ([[a-waiver-hold-is-paid-for-with-a-review]]);
   false ⇒ MERGE. Only a HOLD I verify as a REAL gate loosening, a deploy (migration), or data loss goes to the owner,
   with a PushNotification carrying the printed reason. Deploy stays the owner's.
3. **A PR is a separate judgement:** do not open one for work that is NOT CONVERGED — **except a DRAFT PR at slice
   start**, which is how the full mutation sweep runs on CI's shards. CI runs only on PRs to master and pushes to master,
   so a feature-branch push alone starts nothing.

**Why:** pushing a feature branch is trivially reversible and affects nobody; the irreversible half is guarded by a
machine (`block-default-branch-push.sh`: default branch, bare `--force`, `--no-verify`). The owner, 2026-10-25:
*"Let's make this a house rule so that I don't need to specify the condition all the time. For exceptions, hold the
merge and let me know."* And 2026-11-06 16:39: *"if a PR passed all gates, merge without waiting for my decision. This
has been a house rule for a while."*

**How to apply:** never write "holds for the owner by design" in a handoff; a PR "touching the gate itself" is NOT a
category that goes to the owner. HOLD exceptions chosen on a card against base rates over 30 merged PRs: a loosening
(baseline edit, pin/total/case-count drop, a removed line within 5 of a failure path in a gate file — 5/30), a
migration, a `NO-REVIEW:` waiver (`NO-ENTRY` does not hold), app code without a local `test:integration` + `test:e2e`
run at that head (run them myself, then pass `--app-tests-passed <head>`). Matches `docs/dev-process.md` → HITL policy.

See [[process-conventions]], [[a-stacked-pr-dies-with-its-base-branch]], [[defaults-i-decide-myself]],
[[scoped-mutation-run-in-four-seconds]].

## History

- **Origin:** the "push needs the human" line entered at `e09e1edf` (2026-07-12, Conditional AFK): *"…or an
  outward-facing/irreversible step like push/merge/deploy."* The defect was the GROUPING. ⚠ I removed it before
  knowing that rationale — right outcome, missing justification. **Read why a rule exists before deleting it, even
  when told to.**
- **2026-09-30:** sat on 19 commits for a session, asked about pushing three times, closed messages with *"nothing has
  left this machine."* Turning my own incomplete step into their decision is the pattern.
- **2026-10-23 23:19, 10-24 20:38, 10-25 07:33:** three SCOPED overnight merge grants (*"you can merge finished ones
  when they are merge ready…"*, *"…merge backlog fix PRs when they are ready."*, *"merge PRs when they become
  mergeable."*) — each read narrowly, merge only on READY. Superseded ~07:50 on 10-25 by the house rule.
- **2026-10-25:** "no PR until converged" with no exception beat the velocity spec's draft-PR rule: no draft PR → no
  CI sweep → ~3.5h of local sweeps.
- **2026-11-06:** I parked PR #522 (backlog #508) "for the owner BY DESIGN" because its HOLD flagged check-merge-ready's
  own failure paths, and notified instead of verifying. Wrong — the owner's 16:39 line above.
