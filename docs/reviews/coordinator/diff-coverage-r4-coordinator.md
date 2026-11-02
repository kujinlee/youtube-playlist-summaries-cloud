# Round 4 — `diff-coverage` — coordinator — ⟳ NOT CONVERGED (stable half); DEFER: filed, merge on READY

```yaml
round: 4
fixes_nontrivial: false
subject: diff-coverage
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XP1, severity: Medium, aim: deliverable, fix_induced: true, component: decision-lines, disposition: filed}
  - {id: XP2, severity: Medium, aim: deliverable, fix_induced: false, component: diff-parse, disposition: filed}
  - {id: XP3, severity: Medium, aim: deliverable, fix_induced: true, component: manifests, disposition: filed}
  - {id: XL4, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

REVIEW GAP: claude — round 4 alternates to the Codex half (`review-method.md`, *The protocol*, step 4; backlog #339).

`X` = Codex, tree `2d23154b`. HELD: a function merely named with `self_test` warns; `diff.external`, `GIT_EXTERNAL_DIFF`
and custom prefixes no longer suppress warnings; an added `++ ` line keeps later hunks; working-tree source edits do not
affect HEAD measurement; insertions beside a decision do not cover it; binary diffs are NOT CHECKED; Unicode and tab paths
warn without crashing; `ci.yml` adds only this tool's self-test step; `check-merge-ready.py` is byte-identical to master.

- **XP1 (FILED, backlog #371, fold-induced):** `git show` is read with `text=True`, which translates a lone CR before the r3
  `measurable()` check runs — the protection does not hold; a committed `PIN = 1\rx = 0\nif good:` change was a clean zero.
- **XP2 (FILED, backlog #371):** a `textconv` diff driver in `.gitattributes` empties the diff; `--no-textconv` is missing.
- **XP3 (FILED, backlog #371, fold-induced):** manifests are read from the working tree while sources come from HEAD (the r3
  fix), so an uncommitted manifest edit cleared a committed uncovered decision.
- **XL4 (fixed, prose):** the live PR body still described the removed CI delivery — rewritten to the shipped split.

Route DEFER, pre-committed in the split row: findings filed, not folded. PR #411 merges on READY — a local warn-only tool
whose only CI presence is its own self-test; nothing on master behaves differently. The loop stops.
