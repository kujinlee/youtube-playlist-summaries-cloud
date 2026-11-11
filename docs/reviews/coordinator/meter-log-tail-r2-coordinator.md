# Round 2 — `meter-log-tail` (backlog #501, PR #531) — coordinator — ⟳ NOT CONVERGED (Claude half); folded

The Claude half ran on `cddb1902`: NOT CONVERGED, 2 findings (R2-F1 Medium, R2-F2 Low). By alternation, Codex did not
run this round.

REVIEW GAP: codex — alternation (round 2 runs the Claude half; Codex takes round 3)

This is round 2, so both findings are fixed rather than filed.

```yaml
round: 2
fixes_nontrivial: true
subject: meter-log-tail
halves:
  claude: ran
  codex: gap
findings:
  - {id: R2-F1, severity: Medium, aim: deliverable, fix_induced: yes, component: scripts/check-usage-pace.py, disposition: fixed, commit: 97788321}
  - {id: R2-F2, severity: Low, aim: deliverable, fix_induced: yes, component: scripts/check-usage-pace.py, disposition: fixed, commit: 97788321}
```

## ⚠ Both findings were caused by the round-1 fix, in one component

- R2-F1 comes from r1's C1 fix, the order check with no scope.
- R2-F2 comes from r1's F3 fix, which dropped the `at <= midnight` clause.

Both are in `pace_line` in `scripts/check-usage-pace.py`. If round 3 also finds problems in this component that the
round-2 fix caused, that is two rounds in a row of fix-induced findings in one component. That is THRASHING, the
arming condition in `docs/dev-process.md`, so a Phase 6 architecture review follows. It is not armed yet: one round
is not two.

## Each finding: what was done, and which case covers it

The cases were written first. On `6fa1fc68`, 375 of 379 passed, and the four marked "red on base" below failed. The
inside-horizon case was green on the base, because the base checked every row. It exists to stop the horizon being
narrowed, and it goes red under the narrowing mutation.

| Finding | Disposition | Case(s) that cover it |
|---|---|---|
| **R2-F1**: the order check covered all ~280 days of a cut part, so one inverted pair refused the line for ~280 days | **fixed**. Only rows stamped at or after `horizon = resets − 2 × SEVEN_DAY_S` (this window and the one before it) are checked for order. Older rows cannot place today's start, so disorder among them does not refuse. Stated in the docstring and in backlog row 501: disorder ACROSS the horizon (an older-stamped row appended after a horizon row) is not checked. | `⭐ #501 r2 F1: a 1 s inversion 200 days back, in a CUT part, does not refuse…` (the reviewer's repro, through a real `_read_tail` cut; red on base: TAIL_OUT_OF_ORDER); `#501 r2 F1: an inversion INSIDE the horizon … still refuses a cut part` (green on base; pins the horizon's width); `#501 r2 F1: the horizon's boundary — a later row stamped AT it is checked (refused); one a second before it is not (92.5)` (red on base) |
| **R2-F2**: an earlier window's row AFTER midnight that follows this window's rows set `earlier_window`, giving the wrong 94 where the whole log gives 92.5 | **fixed**, both parts the review proposed. (a) Among horizon rows, a `resets_at` SMALLER than the previous row's refuses: TAIL_OUT_OF_ORDER, whose text now says "(or a weekly reset that goes back)". (b) An earlier window's row proves the cut only if it comes BEFORE, in file order, the first row with `resets_at == resets`. R1-F3's case still answers 51. | `⭐ #501 r2 F2: a cut part whose resets_at DECREASES in file order is refused, never the wrong 94…` (all three of the reviewer's variants; red on base: 94.0 ×3); `⭐ #501 r2 F2: an earlier window's row proves the cut only when it PRECEDES this window's first row…` (a stale row stamped before the horizon, so only rule (b) decides; red on base) |

**R1-F5 stays declined.** The reviewer noted that the horizon might make a newest-first walk that stops early sound.
It does not quite: a walk that stops at the first row older than the horizon would skip a horizon row filed before a
late-appended older row. The full walk still reads that row, so the two are not the same rule. The cost was measured
at 0.21 s at the bound. The reason is in `pace_line`'s docstring.

## Mutations

There are 7 new entries in `check-usage-pace.json`, and the r1 F3 entry is re-bound to the new earlier-window line.
The new entries cover:
- the order check widened back to every row;
- `>=` → `>` at the horizon;
- the horizon narrowed to one week;
- the `resets_at` decrease check removed;
- that check never advancing;
- the file-order condition on the earlier window dropped;
- this window's first row never marked.

The pin goes from 171 to 178, with a comment in `expected_mutations.py`. The harness's own `load_manifests`,
`manifest_counts`, `pin_drift` and `anchor_problems` report no load errors, no drift and no anchor problems. Two
entries first shared an anchor with an earlier entry, and `load_manifests` refused them. They were re-bound to
distinct anchors. The sweep `--mutate . --only scripts/check-usage-pace.py` kills all 178, each attributed to the case it names. The fold is `97788321`.
