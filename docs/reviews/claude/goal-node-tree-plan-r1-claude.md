# Review — goal-node-tree plan, round 1, Claude half

- **Subject:** `docs/superpowers/plans/2026-11-24-goal-node-tree.md` (branch `goal-node-tree-plan`, PR #630)
- **Spec:** `docs/superpowers/specs/2026-11-23-goal-node-tree-design.md` (approved; §6.1 is not reopened)
- **Mandate:** try to refute the plan on coverage, grounding, order, tests, and choices C1–C14.
- **Reviewer:** Claude (an adversarial subagent). It read the plan and spec in full, and the code by symbol.

## Summary

Coverage of the spec's §4 rows, the §5.1 slices and the §6.1 answers is close to complete. Every symbol checked
so far exists or is created by an earlier task, including `feature_id`/`FEATURE_ID_PREFIX` (C8 is right),
`ARMED_ANCHORS`, `ROOTS`/`DEPENDS`, `parent_errors`/`registry_anchors`, `parse_registry`/`parse_header`, and
`GOAL_RE`/`REQUEST_RE`/`_sibling`. Three findings would leave a gate red, or let a wrong tree pass, if a builder
followed the plan as written. All three are cheap to fix in the plan text.

## Findings

### F1 — Major — C1 / Task 1 (also Tasks 5 and 12): the parenthesised list grammar does not exist

C1 says list fields keep "today's parenthesised form … one list grammar, the one `areas:` uses". The code has
no such grammar.

- **The parentheses belong to the tag, not the list.** In `docs/features.md` the value is
  `areas: (cloud/frontend), (cloud/UX)`, where each `(…)` is a backlog `(area)` tag (the preamble calls them
  "`(area)` tags"). `anchors:` is a bare list: `anchors: cloud-publishing`.
- **The parser does not strip parentheses.** `parse_features` in `scripts/check-features.py`, for
  `key in LIST_FIELDS`, runs `[a.strip() for a in value.split(",") if a.strip()]`. Run on the plan's own
  example:

  ```
  $ python3 -c 'v="(0001, 0005)"; print([a.strip() for a in v.split(",") if a.strip()])'
  ['(0001', '0005)']
  ```

  So Task 1 Behavior 1 (`adrs: (0001, 0005)` gives `("0001", "0005")`) needs a new paren-stripping arm. That
  is a second list grammar, the opposite of what C1 claims.
- **The spec agrees with bare lists.** §5.1 writes `was: dev-speed-first, harness-speed`, which is the
  `anchors:` form.

**Fix:** make `adrs:` and `was:` bare comma lists, like `anchors:`, and drop C1's rationale. If the plan keeps
the parentheses, Task 1 must name the new stripping rule and add a case for an unbalanced `(0001` value.

### F2 — Major — Task 2 with Tasks 5 and 7: the `absent` rule is unspecified for `adrs` and anchored documents, and live data trips it

- **Today's rule:** `check_nodes` computes `fragments = len(n.areas) + len(n.anchors)`. It refuses an `absent`
  node that names fragments, with "`absent` but names {fragments} fragment(s) — flip it to `built`".
- **Live data:** `harness-ships-elsewhere` is `state: absent`, and spec 4.45 keeps it absent while giving it
  `adrs: 0015`. Task 5 adds that line. Three documents also anchor to it today: ADR-0015, and the
  marketplace-inventory spec and plan. Task 7 passes the live `anchored` set into the check.
- **The gap:** Task 2 says fragments now include `adrs` and anchored documents, and its behaviours cover only
  the `built`-with-zero-fragments case. If the new fragment count also feeds the `absent` arm, then
  `python3 scripts/check-features.py` goes red at Task 5 (one ADR) or at Task 7 (three documents), on a node
  the spec says must stay absent.

**Fix:** state in Task 2 which fragments the `absent` arm counts. The spec-consistent rule is that only
`areas` (backlog rows) contradict `absent`, while ADRs and anchored documents describe a gap and may sit under
an absent node. Add two cases: `absent with an adrs line passes` and `absent with an anchored document passes`.
Add a FAILS IF line that runs the live check after Task 5.

### F3 — Major — Task 5 (and Task 12's insertions): renaming in place re-parents five siblings

- **How a parent is found:** a node's parent is its position, meaning the nearest preceding heading of a
  smaller level (`parse_features`; Task 1 derives `parent` the same way).
- **What Task 5 says:** spec row 4.24 RENAMES `#### harness-speed` to `dev-speed` and lifts it to `###`
  "under DEV INFRASTRUCTURE".
- **What an in-place edit does:** if the heading changes level where it stands (line 136 of
  `docs/features.md`), five nodes move from `guard-and-gate-harness` to `dev-speed`:
  - `review-process`
  - `mutation-and-test-quality`
  - `hooks-and-session-continuity`
  - `backlog-and-page-tooling`
  - `guard-soundness`
- **Why nothing catches it:** no FAILS IF line or case asserts the parent of the surrounding nodes. The area
  claims still resolve, the counts are unchanged and G7 still counts each node once, so every gate stays green
  over a wrong tree.
- **The same risk in Task 12:** wherever it inserts new `###` nodes, any `####` block that follows takes the
  new node as its parent.

**Fix:** Task 5 should say MOVE the block (heading plus its fields) out of `guard-and-gate-harness`'s children,
for example to just after `guard-soundness` ends, at `###`. Add a FAILS IF line that diffs the
`(slug, parent)` pairs before and after the slice: only the moved node's parent may change. Apply the same
before/after parent diff to Task 12.

### F4 — Minor — Tasks 1, 2 and 5: the summary line counts stateless nodes as "declared absent"

`main` in `scripts/check-features.py` prints `len(nodes) - built` as "declared absent". Task 5 creates the
first nodes with no `state:` line: `dev-speed` has its `state:` removed (4.24), and `cloud-publishing` and
`serve-money-guard` are new. Each of these would be reported as absent. Task 7 Behavior 6 changes the summary
line only for the anchor count.

**Fix:** count `absent` nodes explicitly, and print stateless nodes as their own figure or leave them out.

### F5 — Minor — Task 3: G9 makes `check-features.py` CANNOT RUN without `goal-threads.md` even when no node has `done:`

Behavior 6 returns `CANNOT RUN` whenever `docs/goal-threads.md` cannot be read. Behavior 7 ("no node carries
`done:`") is exercised only with the file present. That gives the check a hard dependency on a second file
for a rule that is vacuous today. `gen-features-page.py` loads the module (`_load("check-features")`), and any
self-test world built without a threads file would turn into CANNOT RUN.

**Fix:** read the threads file only when at least one node carries `done:`. Add the case
`no done: and no threads file → no problem`, or state in the plan that the dependency is intended.

## Checked and not refuted

- **C8:** `feature_id` emits `f-<slug>` (`FEATURE_ID_PREFIX = "f-"` in `scripts/page_markup.py`). The plan
  is right that the spec's "bare `<slug>`" is wrong.
- **G3 / R5:** `ROOTS` and `DEPENDS` exist in `scripts/gen-backlog-page.py`. `parent_errors(rows, anchors)`
  is fed by `registry_anchors()`, which reads `check-anchors.parse_registry`, so retiring `anchors.md` must
  re-point it, as Task 7 does. `check-anchors.py` R5 reads `ROOTS_KEY`.
- **G4:** `ARMED_ANCHORS` exists in `scripts/check-goal-status.py`, with 13 entries.
- **Task 3:** `GOAL_RE`, `REQUEST_RE` and `_sibling` exist in `scripts/goal-tree.py`.
- **CI:** `check-anchors.py`, `check-goal-status.py`, `check-features.py` and `goal-tree.py` are all run as
  `ci.yml` steps, each with its `--self-test`. A slice that leaves any of them red puts the PR red, so F2 and
  F3 matter in CI, not only locally.

VERDICT: NOT CONVERGED
