# Round 3 — `node-tree-s3` — coordinator — NOT CONVERGED (Claude); THRASHING in check-features, Phase 6 run; findings filed

Claude reviewed the round 2 fold `7a83d09c` (`git diff dcbaa53f 7a83d09c`).

What held:
- The real tree passes `check-features.py` with rc 0. No PRIORITY line exists in `docs/goal-threads.md` today.
- No valid declaration is newly refused.
- On a scratch copy, all 79 check-features mutations are killed, each by the case it names. The pin of 79 equals the manifest, and the self-test count of 130 matches.
- Nothing loosens a gate.

Findings, all in the PRIORITY-attempt detection in `check-features.py`:
- **H1 (Low; Claude MINOR, fix-induced by round 2).** `PRIORITY is decided by the owner · see ADR-0010.` is prose, yet it is refused because the ` ·` branch matches it.
- **H2 (Low; Claude MINOR, not fix-induced; from round 1).** `PRIORITY · a > b` is read as prose, so its ranking is dropped in silence.
- **H3 (Low; Claude NIT).** These near-misses are also dropped in silence: `PRIORITY:`, a tab, leading spaces, lowercase, `·a`, a slash date, curly quotes.

**Thrashing.** Round 2 and round 3 both carry findings caused by the previous round's fix, in one component, so Phase 6 is armed. Its review, `docs/reviews/coordinator/architecture-review-2026-11-27-s3-priority-detection.md` (Fable), concludes:
- **A redesign removes the class.** Under the redesign, the first word after any non-word prefix, in any case, makes the line the declaration, through ONE function shared by the gate and `priority_order`.
- **It should not block S3.** `priority_order` has no caller until S4, and no PRIORITY line exists, so nothing is lost in the gap.

I checked by hand that `- PRIORITY …`, `**PRIORITY** …` and `PRIORITY · a > b` are all read as prose today. So H1–H3 are **filed**, not folded:
- **Backlog #744:** the redesign, amended per the Phase 6 review, as a prerequisite of slice S4. Its STOP: one more fix-induced detector finding goes to the owner as a `## PRIORITY` heading.
- **Backlog #745 and #746:** the same class found elsewhere by the review, `ALSO_FIELD` near-misses (probed by hand) and a mis-typed first `## GOAL` heading (not probed).

A fourth regex fold would be the thrashing the arming condition exists to stop.

REVIEW GAP: codex — alternation (round 3 is Claude's).

```yaml
round: 3
fixes_nontrivial: false
subject: node-tree-s3
halves:
  codex: gap
  claude: ran
findings:
  - {id: H1, severity: Low, aim: deliverable, fix_induced: true, component: check-features, disposition: filed}
  - {id: H2, severity: Low, aim: deliverable, fix_induced: false, component: check-features, disposition: filed}
  - {id: H3, severity: Low, aim: deliverable, fix_induced: false, component: check-features, disposition: filed}
```

Review: `docs/reviews/claude/node-tree-s3-r3-claude.md`.
