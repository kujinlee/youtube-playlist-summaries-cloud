---
name: a-convention-catches-what-you-read
description: "FIRES-WHEN: relying on a written convention plus a careful manual pass instead of a script — MEASURED 2026-08-18 — a written convention plus a careful hand pass caught 2 stale rows; a 20-line script found 3 MORE in the same file, next day, on the same defect"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a00a513a-4135-416e-bbf4-48c0416ca19d
  modified: 2026-08-18T23:31:31.449Z
---

**A convention catches what someone happens to read. A script catches what is there.**

`dev-process.md` already says *"Before adding a rule here, ask whether it can be a script."* This is
the measurement that shows why skipping that question is expensive, and it is unusually clean because
both halves ran on the same file within 24 hours:

- **2026-08-17, prose.** Closed backlog rows still led with their filing-time severity marker
  (🔴/🟠), so scanning for red reported blockers that did not exist. I wrote the convention at the
  top of the table — *on close, write `✅ (was 🔴)`* — and hand-corrected the two rows I had found
  (#36, #37). It felt complete.
- **2026-08-18, script.** ~20 lines in `check-docs.py` (`check_backlog_closed_markers`) found
  **three more** — #43, #46, #50 — closed, still flagged, in the file I had just edited, on the exact
  defect I had just written a rule about.

**The rule I keep needing:** when I catch myself writing a convention *and* fixing the instances I
happened to notice, that pairing is the tell. The hand pass is evidence the defect is mechanically
detectable — otherwise I could not have detected it by hand.

**Also: the check must be seen to fail.** Restoring one bad row made the gate exit 1 and name the row;
putting it back made it exit 0. A gate never observed failing is indistinguishable from one that
cannot fail — see [[test-harness-can-launder-failures]] and
[[a-test-that-cannot-fail]].

**And say what stays unscripted.** The same stale-state pattern hit a *task subject*, and tasks live
outside the repo, so no ratchet can see them. That instance is still a convention, and it is recorded
as an open weakness rather than folded into the success. Related:
[[hardcode-only-what-fails-loudly]], [[gates-detect-defects-not-design]].
