# Round 3 — `regen-fresh` (PR #536, backlog #408) — coordinator — Claude NOT CONVERGED; THRASHING → Phase 6; all folded under a stated threat model

```yaml
round: 3
fixes_nontrivial: true
subject: regen-fresh
halves:
  claude: ran
  codex: gap
findings:
  - {id: R3-F1, severity: Medium, aim: deliverable, fix_induced: true, component: regen-runner, disposition: fixed}
  - {id: R3-F2, severity: Low, aim: deliverable, fix_induced: true, component: regen-runner, disposition: fixed}
  - {id: R3-F3, severity: Low, aim: deliverable, fix_induced: false, component: regen-runner, disposition: fixed}
```

REVIEW GAP: codex — alternation

Claude (`docs/reviews/claude/regen-fresh-r3-claude.md`) reproduced R3-F1 in a scratch repository: a symlink swapped in at
`<private>/tree` right after `clone` sends `checkout --detach`, `update-ref` and `remote set-url` to the main checkout,
and `read_back` accepts it through `realpath`. HEAD moved, and no file content was lost. R3-F2 was reproduced:
`REGEN_MAIN_CHECKOUT` naming another repository's main checkout is accepted. R3-F3 comes from reading the code and was
not reproduced. It is the r2 F4 pattern, older than r2, in `_git`.

`fix_induced`: F1 and F2 come from round 2's clone design (`read_back` and the `REGEN_MAIN_CHECKOUT` hand-off). F3
predates it.

## THRASHING → Phase 6

r2's F1, F2, F3, F4 and F6 were caused by r1's fix, and r3's F1 and F2 by r2's fix, all in `regen-runner`. That is two
consecutive rounds, so the arming condition (`docs/dev-process.md` → *Phases*) is met. The narrow review is
`docs/reviews/architecture-review-2026-11-08-regen-runner-threat-model.md`.

**Its verdict:** every data-loss repro after r1 needed a same-user process rewriting paths inside the runner's own
directories mid-run. Such a process can delete the checkout without the runner's help, so no redesign removes it. The
runner now STATES its threat model: it is safe against accidents, and same-user tampering is out of scope. R3-F1 gets
the cheap exact-path fix with no race-freedom claim. R3-F2 and R3-F3 are accident-class and are fixed. **BLOCKERs:
none.**

## Next

This is the last fixing round (`review-method.md` §0 Q4c). r4 runs ONE half, Codex, by alternation. Its findings are
FILED unless BLOCKING, and a same-user swap finding is out of scope under the review's §2.
