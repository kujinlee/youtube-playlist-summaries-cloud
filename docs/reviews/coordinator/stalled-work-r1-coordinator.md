# Round 1 — `stalled-work` (PR #452, backlog #410) — coordinator — NOT CONVERGED; route ACCRETE

```yaml
round: 1
fixes_nontrivial: true
subject: stalled-work
halves:
  codex: ran
  claude: ran
findings:
  - id: F1
    severity: Major
    aim: deliverable
    disposition: fixed
    fix_induced: false
  - id: F2
    severity: Major
    aim: deliverable
    disposition: fixed
    fix_induced: false
  - id: F3
    severity: Major
    aim: deliverable
    disposition: fixed
    fix_induced: false
  - id: F4
    severity: Major
    aim: deliverable
    disposition: fixed
    fix_induced: false
  - id: F5
    severity: Major
    aim: deliverable
    disposition: fixed
    fix_induced: false
  - id: F6
    severity: Major
    aim: deliverable
    disposition: fixed
    fix_induced: false
  - id: F7
    severity: Major
    aim: deliverable
    disposition: fixed
    fix_induced: false
  - id: F8
    severity: Minor
    aim: deliverable
    disposition: fixed
    fix_induced: false
  - id: F9
    severity: Minor
    aim: deliverable
    disposition: fixed
    fix_induced: false
  - id: F10
    severity: Minor
    aim: deliverable
    disposition: fixed
    fix_induced: false
```

The two halves agree on F1–F5 and F8–F9; F6 and F7 are Codex's alone, and F10 is Claude's. Deduplicated:

| ID | Severity | Finding |
|---|---|---|
| F1 | Major | review-half file names reach the injected context unshaped (HALF_RE subject is .+) |
| F2 | Major | local branch names and worktree paths are printed unshaped; the path is unquoted in a suggested command |
| F3 | Major | the CANNOT RUN block is unframed and forwards raw multi-line gh stderr |
| F4 | Major | GH_TIMEOUT_S 30 equals the hook timeout 30, so the hook is killed silently and every prompt can wait 30 s |
| F5 | Major | commits on a detached HEAD or a branch with no upstream are never shown |
| F6 | Major | unprocessed review halves disappear: the 48 h window, an in-place rewrite under an unchanged directory mtime, a half in the main checkout |
| F7 | Major | a PR comment resets the stall clock when the head commit is not local |
| F8 | Minor | a squash-merged branch with a pruned remote shows STALLED with 'push it' |
| F9 | Minor | %ct vs %at passes for an ambient reason; --ignore-missing, the real gh wrapper, NOTE forwarding, the prunable filter and the wt- exclusion are untested; gh printing {} or null gives rc 0 |
| F10 | Minor | the summary count of unfolded halves is taken before the 48 h filter |

**Route: ACCRETE.** It is round 1, and every finding is a bounded addition to the existing design:
- shape every printed string through one function, `safe_ref`'s rule generalised;
- frame the CANNOT RUN block as data;
- a gh budget well under the hook's timeout;
- an unpushed rule that does not depend on attachment;
- head-commit age taken from gh's commit date, not `updatedAt`;
- review halves judged by round number with no age window.
