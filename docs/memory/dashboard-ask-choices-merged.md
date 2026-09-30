---
name: dashboard-ask-choices-merged
description: "FIRES-WHEN: citing the ask-choices slice or PR #186 — Ask-choices slice MERGED (PR #186, cadd7348) — and the round where THREE parties agreed on a premise that one git diff refuted"
metadata: 
  node_type: memory
  type: project
  originSessionId: b9c3a19c-65b0-4c1b-a6a3-02051a3869e5
  modified: 2026-09-01T00:45:17.533Z
---

**MERGED 2026-08-31 — PR #186, squash `cadd7348`.** Dashboard asks now state their choices;
`heads-up` is a second category; badges are derived. 12 commits, spec v3 + plan v2 + 4 review docs.
`gen-dashboard` 217→266 cases, `check-dashboard-entry` 46→77, `EXPECTED_MUTATIONS` 105→**120**,
`--mutate .` 120/0 survivors.

**Reported by the user from the live page**, not by any gate: three cards said *needs you* while the
tray said *Nothing needs you.* The tray derived `unresolved()`; the card printed the raw authored
flag. One page, one question, two sources — inside the very renderer built to stop docs recording
stale state.

## ⭐ CONSENSUS IS NOT VERIFICATION — and it cost a whole spec revision

v1 asserted `git diff -U0` leaves an added entry's body out of the patch. **False.** An appended
entry is entirely additions; `-U0` suppresses only *context*. Measured: 39 added lines.

**The author and BOTH round-1 reviewers agreed on it.** Three independent parties, none of whom ran
the command. v2 then built a second-revision read, ordinal matching and a cutover date on top of it —
and every one of round 2's three Blockings was a regression *from that machinery*. v3 deleted it.

Sibling of [[the-control-refuted-the-premise]], but the new part is the count: agreement among
reviewers is not evidence. Ask *"did anyone EXECUTE this?"*, not *"does anyone disagree?"*

## What only the PLAN gate could find, because it had code to run

Spec rounds can only read. The plan round executed, and found **six parser shapes silently broken** —
worst: a 4-space nested bullet ended the option list, so every later option **vanished from the page**
while the validator reported *"offers 1 option(s)"* about an ask that had three. On a feature for
listing choices, silently dropping choices. **My own probe missed all six because I only ran the
fixtures the plan already listed** — a suite validates the cases its author imagined.

It also predicted the branch would take the suite 217→**216 on a PRE-EXISTING case**, and it did
exactly: `ents3` is an unresolved `[needs-you]` fixture with no decision block. I had verified the
real STORE (all three asks resolved) and never the SUITE'S FIXTURES. ⚠ **And my first fix was
wrong** — the case asserts `"Decide the thing."` *with a trailing period*, which was the entry TITLE;
the tray now renders the QUESTION. Adding a decision block did not clear it; the question needed the
period. See [[measure-the-population-the-code-actually-sees]].

## Design decisions that stuck

- **Renderer-only enforcement** (user's call). The CI gate half is **backlog #78**: `verdict()`
  short-circuits when only exempt paths changed, `docs/dashboard-entries.md` is in `EXEMPT_FILES`
  (pinned by a self-test at `:183`), and it runs only on `pull_request` while the dashboard skill
  regenerates the page immediately. **The reader sees the page long before CI sees the branch.**
- **Validate only UNRESOLVED entries, AFTER `unresolved()` — and never write `entry["error"]`.** That
  one ordering choice dissolved four findings at once: no five-entry cascade, no cutover date, no
  ask filtered out of its own tray, no false *SHIPPED WITH NO ENTRY*.
- **`PR #N`, never a bare `#N`** — this repo writes `#N` for backlog rows constantly.
- **`decision_errors` lives in `check-dashboard-entry.py`**, the grammar owner; the arrow already
  points generator→gate. v2 had the gate importing the generator: a cycle.

## Two refusals by the tooling, both correct

`--mutate .` declined to report verdicts over a red control run (its own self-test pins the declared
total, which I had moved). Then it rejected two mutations that **crashed** the suite rather than
reddening the case they named — *caught, but by no named guard*. Weakened both until each failed via
its own case. See [[a-report-format-is-a-contract]].

## ✅ CLOSED — heads-up expiry: NO EXPIRY (PR #187, `4eb208c5`)

**Re-taken by the user 2026-08-31 AFTER the original justification was withdrawn**, so it rests only
on the argument that survives: a heads-up that ages out on its own is indistinguishable from one that
was dealt with. v1 had cited `check-vocabulary-collisions.py`, which compares **database column-name
stems across tables** and could never have fired on a dashboard entry.

⚠ **The withdrawn reasoning is KEPT in spec §3, not deleted.** A decision whose stated reason turned
out to be false is worth being able to re-check; deleting the bad argument leaves a conclusion with
no visible history. ⚠ And nothing *enforces* no-expiry — §3 says so rather than implying a guard,
which is precisely the failure the original justification committed.

**Final state, verified from ground truth on master:** `unresolved()` `[]`,
`unresolved_heads_up()` `[]`, tray *"Nothing needs you."*, **0 stale needs-you badges, 4 resolved**,
no open PRs. `[resolved: 2026-08-31/3]` was the first exercise of the resolution mechanism on an
entry written in the new grammar — and the reason no expiry was needed: both categories clear through
the same marker.
