# Round 3 — `scaled-deadlines` (PR #454, backlog #407) — coordinator — NOT CONVERGED (Claude half); REDESIGN

Claude half: `docs/reviews/claude/scaled-deadlines-r3-claude.md`, reviewing `3582941c`. No Codex half this round:
REVIEW GAP: codex — rounds 2+ alternate (`docs/review-method.md`, *Round topology*); round 2 was Codex. Round 4 is Codex.

```yaml
round: 3
fixes_nontrivial: true
subject: scaled-deadlines
halves:
  codex: alternation
  claude: ran
findings:
  - {id: F1, severity: Medium, aim: instrument, fix_induced: false, component: skip-coverage, disposition: deferred}
  - {id: F2, severity: Low, aim: instrument, fix_induced: false, component: ci-guard, disposition: fixed}
  - {id: F3, severity: Low, aim: instrument, fix_induced: false, component: skip-coverage, disposition: deferred}
  - {id: F4, severity: Low, aim: instrument, fix_induced: false, component: merge, disposition: fixed}
  - {id: F5, severity: Info, aim: instrument, fix_induced: false, component: skip-coverage, disposition: deferred}
  - {id: F6, severity: Info, aim: instrument, fix_induced: false, component: merge, disposition: informational}
  - {id: F7, severity: Info, aim: instrument, fix_induced: false, component: skip-coverage, disposition: informational}
```

**Route: REDESIGN.** This is the third round in a row to refute the universal coverage claim, "under the marker no
mutant the real-time suite kills survives", each time with new mutants. A review cannot close a claim like that by
enumeration, so the claim changes rather than the cases growing. It now states what is MEASURED: under the marker the
sweep proves exactly that each manifest entry is killed by its named case; the skipped real-time cases still run on
every PR in CI's ordinary step, which `ci_runs_real_time` pins. No kill cases are added in this PR, and no code in
`compaction-state` changes, only docstrings.

- **F1 (capture killed before its deadline: MB, MA; Medium), F3 (`STDIN_WAIT = 20.0`) and F5 (MA2, MK, MN, MP) —
  deferred to backlog #424.** The row lists each mutant, the mode it survives in, and the structural fix: an injectable
  clock or scaled deadlines, so the event-ordered CR1 runs cheaply and the skip can be removed.
- **F3's wording is fixed here:** "the stdin read's bound" is removed from the covered list.
- **F2 — fixed in the docs.** `ci_runs_real_time`'s docstring no longer says "unconditionally". Its BOUND names what
  it does not see: a `needs:` on a skipped job, a step-level `shell:`, and `defaults.run.shell`. No code changed.
- **F4 — merged.** `origin/master` (`60a4b363`, PR #452) is merged. Conflicts were resolved mechanically:
  - `check-plan-code.py`: the per-file pins equal the manifests, and the declared sum is computed with `ast` and is
    2980 (2896 plus `check-stalled-work.py`'s 84); its sum case now says so.
  - `decision-log.jsonl`: a union of both sides.
  - `docs/backlog.md`: #424 follows #423, with no duplicate numbers.
- **F6 and F7 — informational.** Neither asks for a change.

**Decision log:** the ACCRETE row's outcome is now `continued`, with the r3 observation, and a REDESIGN row was added
with its bet and its named failure observation. The route after a failed REDESIGN is SPLIT.
