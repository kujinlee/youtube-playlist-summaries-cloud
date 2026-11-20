# Round 1 — `agenda-stale-wording` — coordinator — NOT CONVERGED (both halves)

Both halves reviewed `77337ca4` (PR #603, backlog #647: the STALE agenda line names who acts, and
`scripts/check-stalled-work.py` reports a stale agenda). Codex (`docs/reviews/codex/agenda-stale-wording-r1-codex.md`)
found 2 MAJOR and 1 MINOR. Claude (`docs/reviews/claude/agenda-stale-wording-r1-claude.md`) found 1 MAJOR and 4 MINOR;
its MAJOR and its first MINOR are Codex's first two findings, which it confirmed after reading Codex. No BLOCKER.
Every finding was reproduced first, in a world outside the repository (a temporary clone, with gh stubbed in-process).

CI's `verify` job was also red on `77337ca4` (run 44695979811). The failing step was `check-fixture-variation.py`:
four parameters were passed one value at every call site (`agenda_facts(main=, gt_loader=)`, `agenda_late(gt=)`,
`shape(keep=)`). Each is now driven at two values in one case (CI below).

```yaml
round: 1
fixes_nontrivial: true
subject: agenda-stale-wording
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: hook-block, disposition: fixed}
  - {id: X2, severity: High, aim: deliverable, fix_induced: false, component: agenda-read, disposition: narrowed}
  - {id: X3, severity: Medium, aim: deliverable, fix_induced: false, component: goal-tree-loader, disposition: fixed}
  - {id: C1, severity: High, aim: deliverable, fix_induced: false, component: hook-block, disposition: fixed}
  - {id: C2, severity: Medium, aim: deliverable, fix_induced: false, component: agenda-read, disposition: narrowed}
  - {id: C3, severity: Medium, aim: deliverable, fix_induced: false, component: agenda-read, disposition: narrowed}
  - {id: C4, severity: Medium, aim: deliverable, fix_induced: false, component: docs, disposition: fixed}
  - {id: C5, severity: Medium, aim: deliverable, fix_induced: false, component: self-test, disposition: fixed}
```

| Id | Finding | Fold |
|---|---|---|
| X1 / C1 | In the hook, a missing or malformed goal-tree log was SILENT when nothing else was stalled: `hook_block` returned `None` for any rc other than STALLED, so the `stale agenda NOT CHECKED` note never printed. Reproduced: `hook_output` returned `None` for a missing log and for `{bad`. | `hook_block` prints the agenda notes alone, framed as data, with a summary line saying the check did NOT run. Every agenda note now opens with the one constant `AGENDA_UNREAD`. Other notes, such as the scratchpad one, still print nothing on their own. Cases: `⭐ r1: nothing stalled but the agenda NOT CHECKED`, `r1: … only a scratchpad note — the hook still prints NOTHING`, `r1: the agenda note is ALSO in a block that has a stalled item — once`, and two END TO END cases through `main --hook`, one with no log and one with a malformed log. The quiet fixture world now holds a clear log, so `main --hook: nothing stalled prints NOTHING` still tests what its name says. |
| X2 / C2 | The note checks only the LAST line, while the page's `read_log` checks every line. Reproduced both inputs: a last line of `{}` read as clear, and `{bad` followed by a stale snapshot gave STALE-AGENDA while `read_log` raised Malformed. | NARROWED. The `{}` case is fixed. goal-tree now has one snapshot test, `is_snapshot` (a dict with `goals` and `at`). `read_log` applies it to every line and `agenda_facts` to the last line. Cases: `r1: a last line that is a dict but not a snapshot` (check-stalled-work) and `a snapshot is a dict with BOTH goals and at` (goal-tree). The earlier-line case is stated as a BOUND in `agenda_facts`' docstring and is not fixed. Reading every line costs about 0.55 s per prompt (measured 11-20 on the real log, 328 snapshots and 20.8 MB, three runs at 0.54-0.62 s), against about 10 ms for the tail. In that case the note still reports the newest snapshot loudly, so the two signals differ but neither one is silent. |
| X3 | Importing goal-tree in the hook path wrote bytecode (`goal-tree.cpython-314.pyc` and others). Reproduced in a copy of `scripts/`. Claude rated this "not a defect" because `__pycache__/` is gitignored. | `_goal_tree` sets `sys.dont_write_bytecode` while goal-tree and the siblings it loads execute, then restores the caller's own setting in `finally`. Case: `r1: loading goal-tree writes NO bytecode, and the caller's own setting is put back`. It runs a fresh interpreter over a copy of `scripts/` with bytecode writing ON and checks that no `__pycache__` appears and that the setting reads back `False`. |
| C3 | The docstring says the page and the note "cannot disagree", but the page's other `stale` line, "every step is done", is not reported. | NARROWED. The claim now reads "cannot disagree ABOUT A LATE MERGE". The docstring and the module header both say that the done line is not reported, because backlog #647 and its Fails-if are about a late merge. A case pins the narrowing: a stand-in goal-tree whose first `stale` line is the done line still yields the late-merge subject. Reporting the done line too would be new behaviour outside #647, so it is left to the coordinator to file. |
| C4 | The module header still listed THREE SIGNALS and a cap order with no agenda tier, and did not state that the signal reads the newest LOGGED snapshot, not live master. | The header now lists FOUR SIGNALS, with (d) STALE AGENDA, its NOTE, the hook printing that note on its own, and the BOUND: a merge after the last goal-tree build is in no snapshot until the next build. The CAP line names the actual tier order. |
| C5 | No case pinned `every_tree[0]` (the main checkout). The end-to-end world had one worktree. | Case `r1: run from a LINKED worktree, the stale agenda is read from the main checkout's log, with no note`. It runs `run --repo <linked worktree>` with the log only in the main checkout. |

**CI (fixture variation).** New cases drive each flagged parameter at two values. `agenda_facts(main=)` gets two
checkouts with two answers. `gt_loader=` gets a loader that raises and a stand-in with no log path. `agenda_late(gt=)`
gets the real goal-tree and a stand-in. `shape(keep=)` gets the default and `AGENDA_KEEP_RE`. The new `is_snapshot`
case calls the function at five literal sites. `check-fixture-variation.py` now ends
`fixture variation OK — 2433 parameter(s) examined across 107 file(s)`.

**Mutations.** There are 11 new mutations, 10 in `check-stalled-work.json` (141 → 151) and 1 in `goal-tree.json`
(440 → 441). `expected_mutations.py` is updated. The r1 edit to `hook_block` unbound one existing anchor (`hook_block:
a clear check still adds a block to every prompt`), and it is re-bound to the new text. A resolve over all manifests
found every anchor exactly once. Each mutation was checked on a scratch worktree outside `.claude/worktrees`: the edit
was applied, the suite was run, and the named case went red. Without the fix, each new case was red. check-stalled-work
was KILLED 151/151, every entry of its manifest. The new goal-tree entry was KILLED 1/1. `check-plan-code.py --mutate .
--only scripts/check-stalled-work.py` itself was NOT run. It runs serially, at about 19 s per mutation (~48 min), past
this fold's 4-minute bound per command, and `--only` cannot be combined with `--shard`. The same edits were run through
a parallel per-entry harness instead.

**Verification.** `check-stalled-work.py --self-test` gives `252/252 self-test cases passed`. `goal-tree.py --self-test`
gives `539/539 self-test cases passed`. On the real 20.8 MB log in the main checkout, `agenda_facts` returns `([], [])`
in 0.20 s.

**Bet for round 2** (one half, by alternation): round 2 finds nothing caused by this fold in hook-block or agenda-read.
