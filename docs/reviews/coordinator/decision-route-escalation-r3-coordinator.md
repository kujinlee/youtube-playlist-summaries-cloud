# Round 3, coordinator — `decision-route-escalation`

**REVIEW GAP:** codex — rounds alternate by `docs/plugins.md`; r2 was Codex alone and this round is
the Claude half it owed. ⛔ Not an outage and not a skip: the alternation exists because a
concurrent pair never reviews the FIXES, and every finding in r2 and r3 is in fix code.

```yaml
round: 3
fixes_nontrivial: true
subject: decision-route-escalation
halves:
  codex: "GAP: alternation — r2 was Codex alone; this is the Claude half it owed"
  claude: ran
findings:
  - {id: ZB1, severity: Blocking, aim: instrument, fix_induced: true, component: coverage, disposition: filed}
  - {id: ZH2, severity: High, aim: deliverable, fix_induced: true, component: starvation-ratchet, disposition: filed}
  - {id: ZH3, severity: High, aim: deliverable, fix_induced: true, component: starvation-ratchet, disposition: filed}
  - {id: ZH4, severity: High, aim: instrument, fix_induced: true, component: starvation-ratchet, disposition: filed}
  - {id: ZH5, severity: High, aim: instrument, fix_induced: true, component: starvation-ratchet, disposition: filed}
  - {id: ZH6, severity: High, aim: deliverable, fix_induced: true, component: corpus-cannot-run, disposition: filed}
  - {id: ZH7, severity: High, aim: deliverable, fix_induced: true, component: log-schema, disposition: filed}
  - {id: ZH8, severity: High, aim: deliverable, fix_induced: true, component: log-schema, disposition: filed}
  - {id: ZM9, severity: Medium, aim: deliverable, fix_induced: true, component: accounting, disposition: filed}
  - {id: ZM10, severity: Medium, aim: deliverable, fix_induced: true, component: log-schema, disposition: filed}
  - {id: ZM11, severity: Medium, aim: deliverable, fix_induced: true, component: corpus-cannot-run, disposition: filed}
  - {id: ZM12, severity: Medium, aim: deliverable, fix_induced: true, component: starvation-ratchet, disposition: filed}
  - {id: ZM13, severity: Medium, aim: instrument, fix_induced: true, component: coverage, disposition: filed}
  - {id: ZM14, severity: Medium, aim: deliverable, fix_induced: true, component: log-schema, disposition: filed}
  - {id: ZL15, severity: Low, aim: deliverable, fix_induced: true, component: log-schema, disposition: filed}
  - {id: ZL16, severity: Low, aim: deliverable, fix_induced: true, component: log-schema, disposition: filed}
  - {id: ZL17, severity: Low, aim: deliverable, fix_induced: true, component: starvation-ratchet, disposition: filed}
  - {id: ZL18, severity: Low, aim: deliverable, fix_induced: true, component: log-schema, disposition: filed}
  - {id: ZL19, severity: Low, aim: instrument, fix_induced: true, component: coverage, disposition: filed}
  - {id: ZL20, severity: Low, aim: instrument, fix_induced: false, component: coverage, disposition: declined}
```

**Verdict: NOT CONVERGED.** 1 Blocking, 7 High, 6 Medium, 6 Low. ⛔ **Counts went UP, not down** —
r2 was 0 Blocking / 2 High. My own r2 adjudication said *"consequence is falling"*; it was not.

## ZB1, verified by running the harness's own functions, not a stand-in

**The authority this whole slice defers to cannot run.** `HARNESS_TREE` does not contain `.git`, and
`tree_at` passes `cwd=REPO` explicitly, so inside the staged tree git fails. Measured:

```
scripts/check-decision-scheme.py: rc=1 control_is_green=False
  [FAIL] tree_at answers from a LISTING of the real repository, not from a diff
  [FAIL] ...while a long-standing file IS, so the listing is not simply empty of reviews
scripts/check-review-decision.py: rc=0 control_is_green=True
```

`mutate_delivered` therefore returns `NotMeasured` for **all 1,623 mutations** — the target is in
every one of CI's 8 round-robin shards. ⚠ It fails LOUDLY (CI red, not a false green), and the r1
fold introduced the first git-dependent case while **this** fold added a second instead of removing
the dependency.

⛔⛔ **AND THE CASE I WROTE TO CLOSE r2's YM6 IS VACUOUS.** `file in (_tree or set())` — when git
cannot be read, `_tree` is `None`, the test runs over the empty set, the assertion is `False`, the
expectation is `False`, and **it passes.** Measured in both conditions: it passes whether or not a
tree was read. The case meant to prove the instant is read **cannot fail**. Its sibling is the only
reason the suite reddens. That is *a case can pass for an AMBIENT reason* and *a test that cannot
fail*, in the case written to close the previous round's coverage gap.

## ⛔⛔ THE ARMING CONDITION FIRES. This is a THRASHING determination, not a fourth fold.

`dev-process.md`: *fires when **two consecutive rounds carry findings caused by the previous round's
own fix, in one component***.

| | r2 fix-induced components | r3 fix-induced components |
|---|---|---|
| | corpus-cannot-run, starvation-ratchet, log-schema, coverage | coverage, starvation-ratchet, corpus-cannot-run, log-schema, accounting |

The intersection is **four components**, non-empty, two consecutive rounds, every finding
fix-induced. ⛔ **Fold-and-re-review is refused here.** Per-task review is structurally blind to
composition defects — it only ever sees one change, and r1→r2→r3 is three rounds of individually
correct changes whose structure degraded.

⚠ **AND REACHING FOUR ROUNDS OBLIGES ASKING**, which is why this document stops at the
determination and does not choose the fix. *Thrashing or prose floor?* — **THRASHING**, with
per-finding evidence: every r3 finding but ZL20 is `fix_induced: true`, and the three
`starvation-ratchet` Highs are the THIRD distinct set of doors into one rule that has already been
redesigned twice (path-arrived → path-existed → (subject, round)).

⭐ **The component a convened review EXAMINES is ranked by TOTAL appearances, not by the
consecutive run** — adopted 2026-10-20, `check-review-decision.py:review_scope`. That ranking is
recorded by running the tool, below, rather than argued here.

## What the procedure says, RUN rather than recalled

```
ARCHITECTURE_REVIEW — thrashing: 'corpus-cannot-run' carried fix-induced findings in r2 and r3
  branch=decision-route-escalation  scope=full-loop  rounds=3  tree_reviewed=False
  scope-rank: NO LEAD — 4 components tied at 3 appearance(s) — first place is the tie-break, not evidence
              tied: corpus-cannot-run, coverage, log-schema, starvation-ratchet
              ranking: corpus-cannot-run > coverage > log-schema > starvation-ratchet
```

⭐ **The two halves of the answer disagree, and that is the designed behaviour.**
`thrashing_component` names **`corpus-cannot-run`** — the component that ARMED the review.
`review_scope` **ABSTAINS**: four components tied at three appearances each, so there is no lead to
report. That is exactly the distinction adopted on 2026-10-20 — *the component a convened review
EXAMINES is not necessarily the one that ARMED it* — and on this subject the ranker declines to
name one at all, which is honest: after three rounds every recurring component has appeared in all
three.

⛔ **So the convened review has no single component handed to it, and must not be given one by
argument.** r2's adjudication is the precedent: there, I wrote a route change citing "three doors"
as though it were a count, ran the tool, and it refused to confirm me. The same restraint applies
here and the consequence is larger — a Phase 6 review whose scope is *the composition*, not a unit.

## ⚠ THE QUESTION THIS DOCUMENT CANNOT ANSWER, and the process says to ask it

`dev-process.md`: reaching four rounds **OBLIGES ASKING**. Three facts the owner needs, stated
without spin:

1. **The gate that is supposed to assert this slice's coverage CANNOT RUN** (ZB1), and the case
   written to close the previous round's coverage gap **cannot fail**. Every coverage number in the
   last three commit messages rests on a probe I run by hand.
2. **Counts went UP**: r1 22 findings, r2 8, r3 20. My r2 adjudication said consequence was falling.
   It was not, and saying so was premature rather than wrong-in-detail.
3. **The measured benefit is still zero.** The log holds four rows, two scored, and no outcome has
   been observed for any unit. Everything claimed for the mechanism is about its construction.

⭐ And the one datum on the other side, which is real: using the mechanism found two things three
adversarial rounds did not — that my own validator refuses two routes this slice took, and that
recording an abstention as a miss punishes the ranker for honesty. Both are in backlog #321.
