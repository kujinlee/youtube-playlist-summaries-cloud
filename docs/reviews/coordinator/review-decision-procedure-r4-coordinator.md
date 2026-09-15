# review-decision-procedure — round 4, coordinator adjudication

```yaml
round: 4
fixes_nontrivial: true
subject: review-decision-procedure
halves:
  codex: ran
  claude: "GAP: this session spawns no subagents"
findings:
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: scope-for, disposition: filed}
  - {id: L1, severity: Low, aim: instrument, fix_induced: true, component: classifier-coupling, disposition: fixed}
```

* Codex: `docs/reviews/codex/review-decision-procedure-r4-codex.md` (`gpt-5.5`) —
  **0 Blocking, 0 High, 1 Medium, 1 Low.**
* **REVIEW GAP: claude** — as rounds 1–3.

**The redesign held.** Codex verified independently that every prefix the deleted lists named
still scores `full-loop` (`worker/`, `.github/workflows/`, `middleware`, `lib/lease`,
`lib/queue`), that `--self-test` passes **inside a staged tree** so the mutation gate is
unaffected, and that no existing review document newly fails to parse.

## ⛔ THE THRASHING QUESTION, ANSWERED — AND OVERRIDDEN IN WRITING

Codex is right on the facts: **M1 is a second consecutive fix-induced finding in the scope
rule**, after r3's `scope-for` Blocking. By the arming condition that is thrashing again.

**The override, and the reason** (`:169` — *can a redesign remove it?*):

> **No.** Any mechanism must be **told** which paths are contained. r1–r3 were the mechanism
> being wrong about blast radius — a shape defect, and a redesign dissolved all three at
> once. M1 is a disagreement about **which paths should be contained**, which survives every
> reshaping because it is an input, not a shape. **Branch-coverage and policy, not
> thrashing.**

⚠ **`:102` requires an override to carry a condition that would prove it wrong, so here it
is:** *this fires to ARCHITECTURE REVIEW if round 5 produces a fix-induced finding in the
scope rule that a redesign WOULD dissolve — a mechanism defect rather than another argument
about which directories belong on which side.*

⟳ **CORRECTED AFTER FILING — the override was being enacted INVISIBLY, by a label.** This
finding was first recorded as `component: scope-policy`, which made
`thrashing_component` see no overlap with r3's `scope-for` and report `ROUND_OWED`. **The
tool agreed with the override for the wrong reason: it did not know one existed, it saw two
names.** That is the metric satisfied by a labelling choice — the defect this header's own
template warns about. Renamed to `scope-for`, which is what it is. The tool now reports
`ARCHITECTURE_REVIEW`, this document overrides it in writing with a falsifier, and round 5
upheld the override independently. **Loud disagreement beats quiet agreement.**

⚠ **And a limitation this exposes: `check-review-decision.py` cannot see an adjudicated
override.** It will keep reporting `ARCHITECTURE_REVIEW` from the headers alone. The header
schema has no `override:` field. **Filed, not patched** — adding one mid-round is how the
last three rounds went.

## M1 — the redesign narrowed the contained set, and that is a POLICY question

**FILED, NOT FIXED.** `tests/`, `.claude/` and `.agents/` were one-round before the redesign
and are full-loop now, because `is_prose` exempts only docs and root prose. Codex measured
all three. It cites the card's own Q1 table, which said *"config, thin wrappers"* were one
round — **so the card and the code disagreed, and the redesign caused that.**

Per §0 Q3, a Medium whose fix is a **policy call** is filed, not fixed. This one is:

- `.claude/hooks/` holds the gate hooks. A change there can disable a guard.
- Deleting the test that proves a spend guard fires is a real loss of protection, and
  `tests/` is where that happens.
- Against that, `:411` explicitly says contained work gets one round, and full-loop on every
  test edit is a real tax.

**What was done instead of deciding it:** the card now describes what the code *does*, states
the narrowing, names the tension with `:411`, and says the question is filed. Until it is
decided the code errs toward the loop — a wrong `full-loop` costs one round; a wrong
`one-round` merges unreviewed risky code. **The asymmetry is the tiebreak, not a preference.**

## L1 — the coupling failed as a traceback, naming nothing

**ACCEPTED AND FIXED, and the first repair was insufficient.** Codex: a rename of
`check-review-recorded.py` crashes `--self-test` before it prints a count. Raising is right;
failing *anonymously* is not.

The first attempt added cases — and the control showed the suite **still** died with a bare
`FileNotFoundError`, because `_repo_is_prose()` was called at the top of the scope section,
before any case ran. **Adding an assertion after the crash point asserts nothing.** The load
is now inside a `try` whose result is itself a case, with a stand-in so the remaining cases
still run and report.

Controlled by renaming the dependency in a staged tree:

```
[FAIL] the borrowed classifier LOADS — a rename fails by name, not as a traceback
[FAIL] a migration needs the full loop
[FAIL] a money path needs the full loop
```

The first line names the cause; the rest are the honest consequence of a rule that cannot
answer without its classifier.

## ⚠ The card drifted again, and the check caught it again

Aligning Q1's table with the code lengthened the section, and **all twelve remaining card
citations moved**. Re-derived by matching each to the sentence it must point at, not by
arithmetic. Drifted after repair: **0**. This is the third time on this branch that editing
the card moved its own citations; it is now the routine last step of any card edit.

## Verified on this tree

```
check-review-decision --self-test  49/49   (47 before)
check-selftest-counts · check-docs                                   rc=0
card citations: 12, drifted 0
control: dependency renamed in a staged tree -> named failure, suite completes
```

**NOT CONVERGED — round 5 owed.** M1 is a finding in the deliverable, and the branch is
full-loop, so convergence needs two consecutive rounds with neither a Blocking/High nor a
deliverable finding.
