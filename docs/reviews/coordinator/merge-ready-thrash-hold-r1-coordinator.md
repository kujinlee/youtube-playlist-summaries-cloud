# Round 1 — `merge-ready-thrash-hold` — coordinator — NOT CONVERGED; all six findings fixed

Both halves reviewed d444dcad (backlog #680 part 2: `check-merge-ready.py` HOLDs a READY PR whose review rounds arm
THRASHING with no architecture review in range). Codex: `docs/reviews/codex/merge-ready-thrash-hold-r1-codex.md` (X1
MAJOR; NOT CONVERGED). Claude: `docs/reviews/claude/merge-ready-thrash-hold-r1-claude.md` (C1, C2 MAJOR; C3, C4, C5
MINOR; NOT CONVERGED). Every finding came from the build, not from a fold, so none is fix-induced. Severity below uses
the header grammar's words: MAJOR is `High`, MINOR is `Medium`.

- **X1 = C1, one defect.** An inline `findings:` value (`[a, b]`, `[{...}]`, a bare `# comment` over block items)
  parsed to zero findings and read as a clean round. `parse_round` now reports the text after the key as
  `findings_inline`, and `parse_header` drops that field, so its output on the 850 coordinator docs is unchanged
  (0 differences against master's `parse_header`). `thrash_gate` reads any value other than `[]` (with an optional
  comment) as unreadable. The pre-existing master bug is NOT fixed here: `parse_header` still reads the 39
  validating docs with a non-empty inline list as having no findings.
- **C2.** `ARCH_REVIEW` now also matches `docs/reviews/coordinator/architecture-review-*.md`, where the four newest
  Phase 6 reviews are filed. 9d8d7102, 84e53b9b and 0340751d no longer HOLD.
- **C3.** "Cannot judge" applies only when the unreadable round could change the answer. A lone round does not HOLD.
  Neither does a pair with a readable round that has no fix-induced finding (asked of the rule itself, as
  `thrashing_component([r, r])`).
- **C4.** Only an exact `ValueError` from `parse_round` makes a round unreadable. Any other exception is
  `ThrashUnjudgeable`, which is CANNOT RUN.
- **C5.** Bound stated in `thrash_gate`'s docstring and in backlog row 680: deleting a subject's newest docs makes the
  gate judge the older pair.

Replay over the 41 master commits that touched coordinator docs: 12 HOLDs (7 armed, 5 cannot-judge) before the fold,
8 (5 armed, 3 cannot-judge) after, 0 CANNOT RUN. PR #600 (11d0568d) still HOLDs. check-merge-ready 432/432.
Mutations 197 → 203.

```yaml
round: 1
fixes_nontrivial: true
subject: merge-ready-thrash-hold
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: check-merge-ready-thrash-gate, disposition: fixed}
  - {id: C1, severity: High, aim: deliverable, fix_induced: false, component: check-merge-ready-thrash-gate, disposition: fixed}
  - {id: C2, severity: High, aim: deliverable, fix_induced: false, component: check-merge-ready-thrash-gate, disposition: fixed}
  - {id: C3, severity: Medium, aim: deliverable, fix_induced: false, component: check-merge-ready-thrash-gate, disposition: fixed}
  - {id: C4, severity: Medium, aim: deliverable, fix_induced: false, component: check-merge-ready-thrash-gate, disposition: fixed}
  - {id: C5, severity: Medium, aim: deliverable, fix_induced: false, component: check-merge-ready-thrash-gate, disposition: fixed}
```
