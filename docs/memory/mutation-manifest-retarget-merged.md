---
name: mutation-manifest-retarget-merged
description: "FIRES-WHEN: citing backlog #70, PR #176, or --mutate . — Backlog #70 CLOSED — PR #176 MERGED 2026-08-29 (squash da5cd27): --mutate . now mutates the DELIVERED scripts, 44/0; the plan-as-CI-dependency is retired. Residue: six uncovered survivors, and a live guard with no falsifier"
metadata: 
  node_type: memory
  type: project
  originSessionId: 7e830c04-6e2d-4fff-b4c9-baee2d50d9a8
  modified: 2026-08-30T00:39:31.371Z
---

**MERGED 2026-08-30T00:37Z — PR #176, squash `da5cd27`, branch deleted, master gates re-verified
green AFTER the squash:** `--mutate .` **44/0** · check-plan-code 136/136 · gen-dashboard 113/113 ·
gen-backlog-page 73/73 · check-dashboard-entry · check-docs · check-anchors · check-review-rounds ·
check-arch-findings · check-test-counts (2,819 unit / 274 suites) · tsc clean.

`check-plan-code.py --mutate .` replaces `<plan> --compare . --verify-evidence` in CI. The manifest
is data (`scripts/mutations/*.json`) applied to the **delivered** scripts over a green control.
2,128 duplicated lines deleted from the plan. Coupling reduced, not eliminated: 1,541 lines of
byte-identity → 45 source anchors (~3%), recorded in the CI step's own comment.

## The thing worth remembering: the late reviewer was right, and about the RIGHT layer

`branch-mutation-retarget-r1-claude.md` opened by **declaring its own gap** — the dispatched
independent reviewer had not returned, so that half was the coordinator's self-verification. It
returned ~90 minutes later, **re-measured against `d16dcd8` instead of the `e006604` it started on**
(three commits had landed under it), and reached CONVERGED. Recorded where the gap was declared, not
as a new round — a lone review half is what turned `check-review-rounds.py` red on this very branch
once already. Same shape as the gap itself. See [[dual-review-what-it-catches]].

Its one pre-merge fix, verified by RUNNING it: the plan's Step 5 / 5a still told a reader to run
`--compare .`, which now exits **1** — T6 deleted the blocks it assembled from. **Dead instructions
in a document that calls them not optional.** Generalises: when work removes a mechanism, grep for
who *describes* it — the same class as `docs/dev-process.md:155` asserting a dead gate one commit
earlier. See [[after-fixing-search-for-the-class]].

## ⚠ A count pinned to a PAST event is NOT the defect ff5857b fixed

The reviewer flagged "your control says 43, live is 44 — fix before the PR body." The PR body was
already right (*"43 → 44"*). The two genuinely stale 43s were in `ci.yml` and the closed backlog
row, and **both pin a one-off equivalence demonstration** (*"both paths green at 43 on the same
tree"*), which is TRUE of the tree it measured. Correcting those to 44 would have made them **false**.
Marked as history instead; the live count lives in `EXPECTED_MUTATIONS`.
**The rule "delete a count, don't correct it" has a carve-out for counts bound to a past
measurement, and telling the two apart is the whole skill.** Extends [[a-retrospective-number-needs-provenance]].

## Residue — carried in the review doc, NOT ticked, NOT filed

- **Six survivors the manifest does not cover.** Two proven to change behaviour:
  `check-dashboard-entry.py:112` (`probe[end+3:]`→`end+4` makes a valid `NO-ENTRY:` return `None`,
  so the gate refuses it) and `gen-dashboard.py:1156` (`!=`→`==` inverts a three-way store
  distinction). **Not a regression** — identical holes existed against the plan's copy. The problem
  is that a step named *"Mutation manifest against the delivered scripts"* prints a bare survivor
  count, inviting a completeness reading the manifest cannot support.
  **DECISION DEFERRED to backlog #69** (task #171) by the user merging on that recommendation.
- **`check-plan-code.py:392` has no falsifier** — `for target in []:` leaves the suite at 136/136.
  Backlog #69's shape exactly.
- **Two Lows:** `--mutate` returns only 0/1, so a control **timeout** is indistinguishable from a
  survivor in the one mode CI runs; a red control prints an empty detail tail.

## Not done, batched deliberately

`docs/dashboard-entries.md` is **append-only** and its #70 entry says "43-entry manifest" / "43
mutations". A correction must be APPENDED, not edited. Not worth a standalone PR — batch it with
the #69 slice ([[process-conventions]] says batch, not push direct).

## Queue after this

**#69** (task #171, external `--self-test` count ratchet — needs Phase 1) → **#67** (task #164) /
**#68** (task #172). See [[launch-roadmap-state]] and [[link-contrast-slice-merged]].
