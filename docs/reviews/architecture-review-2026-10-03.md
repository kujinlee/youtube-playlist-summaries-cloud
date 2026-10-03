# Architecture review — 2026-10-03 — the rule that refused the repair it demanded

**Armed by THRASHING, not a count.** `dev-process.md`: two consecutive rounds carrying findings
caused by the previous round's own fix, in one component. Round 2's findings were caused by round
1's fixes; round 3's were caused by round 2's and its own. Put to the human as a selection card;
they chose a scoped review over a fourth fold, and then chose its recommendation over a stopgap.

**Scope: one question — is reading the wrong instrument for `check-main-drivable.py`?** Not a code
review.

Independent read by a spawned agent with a REFUTE mandate, told in advance that the conclusion it
was most likely to reach — *"it is a hand-rolled abstract interpreter, and that is the wrong
instrument"* — was already the closing sentence of `docs/reviews/claude/main-drivable-r3-claude.md`
and therefore proved nothing. It was also handed one candidate (answer the question dynamically) as
something to COST rather than propose.

⛔ **Every load-bearing claim below was re-derived by the coordinator, in this repository, before it
was written down.** Three of the read's numbers were wrong and are corrected in place with the
measurement that replaced them.

---

## The answer, in one line

**Reading is not the wrong instrument. Dispatching on the top node of an expression is.**

---

## The mechanism — and it is TWO defects, which were masking each other

`check-main-drivable.py` has to decide, of an expression like `root=Path(td)` or `root=str(ROOT)`,
whether it names a world the case BUILT or the LIVE repository. Both are calls; the difference is
what is inside them.

### Defect 2 first, because it is the one that produced every credit

`_element_is_constructed` matched **6 of Python's 29 expression kinds** — `Starred`, `Constant`,
`Name`, `Attribute`, and `List`/`Tuple` only when reached through a resolved `Name`. The other 23
reached a bare `return True` **without a single child being examined.**

✅ **MEASURED, by instrumenting that branch and re-running the whole population: of the 21
element-level credits on disk, 21 exit through it. Zero come from a rule that examined the
expression.**

```
check-fixture-variation.py   11 credits   11 via the un-recursed default
check-main-drivable.py        5            5
check-plan-code.py            4            4
check-ci-watched.py           1            1
                             --           --
                             21           21        (100%)
```

Severing that branch drops compliance 10 → 8 (`check-plan-code.py` and `check-selection-card.py`
lose it outright) and the suite from 188 to 149 — so the branch that does no work also carries 39
cases. It was never dead code; it was the whole of the positive output.

### Defect 1 — and it is why the examining rules only ever said no

`guard_globals` came from `module_globals(tree)`, which counts **imports** — deliberately, for the
`globals()["subprocess"].run` substitution case its own docstring cites. Reusing it here made
`Path`, `tempfile`, `os`, `io` and `json` "the guard's own globals", i.e. the live world.

✅ **You cannot build a temporary world without naming one of them.** Measured consequence:

```
main([], root=Path(td))        # ADR-0014's Decision block, verbatim   -> DEBT
main([], root=Path(_td))       # _td = tempfile.mkdtemp()              -> DEBT
main([os.path.join(_td,'f')])                                          -> DEBT
main([str(Path(_td)/'f')])                                             -> DEBT
main([], root=io.StringIO())                                           -> DEBT
```

**The rule written to enforce ADR-0014 refused ADR-0014's own worked example** — and not
hypothetically: `check-ratchet-contract.py` is the one guard D1 was actually applied to, in PR #360,
and it uses that idiom at `:941`, `:965` and `:980`. All three failed the param test. The file
stayed compliant only because it also holds a `rebind` credit.

### The interaction, which is the part no round could have found by probing

The two defects were **cancelling each other** for some shapes. Fixing defect 1 alone — a four-line
edit making the guard's world its module-level *assignments* instead of `module_globals` — takes
false refusals to zero and pushes false credits **up**, because the cells that stop being wrongly
refused then fall out through the default branch:

| 35-cell matrix (7 wrappers × 5 worlds) | today | imports removed only |
|---|---|---|
| cells wrong | 19 | 18 |
| false **credit** | 15 | **18** |
| false **refusal** | 4 | **0** |
| wrapper rows whose verdict IGNORES the world | **7 / 7** | 6 / 7 |

That last row is the whole diagnosis. **The verdict was a function of the expression's syntax and
independent of the world.** Widened to 15 wrappers × 6 worlds: 45 of 90 cells wrong, and 15 of 15
wrapper rows constant across all six worlds.

### Why this produced exactly this thrashing shape

Every live credit rode on the branch that examined nothing; every live refusal rode on the rule that
examined the wrong set. A reviewer can only probe the spelling they think of. Each probe landed in
one of those two blind rules, and moving a shape out of one left the other — and the default —
untouched. Hence `root=ROOT` → `cwd=ROOT` → `str(ROOT)`, and four binding forms → five more → and
eleven wrappers → seventeen.

⟳ **So "hand-rolled abstract interpreter" is the wrong name for it, and that matters.** An abstract
interpreter propagates a property through the grammar. This propagated nothing: it pattern-matched
six node kinds and defaulted. The fix is therefore not "stop reading" but "read the leaves".

---

## What was built, and what it measures

The rule is now **three leaf classes** — `LIVE` / `BUILT` / `INERT` — recursing over whatever the
grammar hands it (`world_class`). `Path(td)` is judged by what `td` is; `str(ROOT)` by what `ROOT`
is; a wrapper nobody enumerated contributes nothing of its own.

| | HEAD (top-node) | NEW (leaf-first) |
|---|---|---|
| 90-cell matrix, cells wrong | **45 / 90** | **0 / 90** |
| false credits / false refusals | 30 / 15 | **0 / 0** |
| wrapper rows whose verdict ignores the world | **15 / 15** | **0 / 15** |
| canonical ADR-0014 repairs credited | 0 of 5 | **5 of 5** |
| live-world expressions refused | 3 of 3 | 3 of 3 |
| compliance over 44 guards | 10 / 27 / 7 | **identical** |
| existing cases | 188 | **198 pass, none rewritten to accommodate the rule** |
| lines in the replaced region | 191 | **166** |

One route changes: **`check-ratchet-contract.py` regains the `param` credit D1 earned it.** That is
the only verdict movement in the repository, and it is a gain.

### Three things found while building it, all of which DELETED a rule

1. **`ast.keyword` is not an `ast.expr`**, so a plain child walk skips keyword arguments. That was
   the entire residual false-credit class — `dict(a=w)['a']` over the live world, credited 3 of 3.
2. **A "call over nothing but literals is a literal in a wrapper" clause cost `check-ci-watched.py`
   its `param` route**, because its stub stream is built as `_S(True, '{"session_id": …}')`. What
   that clause protected — a bare literal in `argv` — is already refused one line earlier by
   `Constant → INERT`. It earned nothing and refused an exemplar: deleted.
3. **A `seen` set of names beside the depth bound was redundant.** Its mutation SURVIVED the sweep;
   measured, deleting it changes 0 of 44 verdicts and leaves the suite green, because the depth
   bound already answers every cycle the same way. Two mechanisms for one property is the duplicate
   this project has measured seventeen times. Deleted, mutation retired with it.

⭐ **The pre-committed falsifier was: *any future round fixing a defect in this by adding a node kind
to a list inside it.* All three of the above went the other way** — one added a traversal of a
category the grammar already defines, two deleted clauses. There is no node list left to extend.

---

## Rejected alternatives, costed by running them

**Fix the imports only (four lines).** Credits 10 of 10 canonical repairs and removes every false
refusal, including the live one. ⛔ Rejected because it leaves the false-credit class and measurably
worsens it (15 → 18 of 35 cells), for the reason above: the defects were masking each other. Offered
to the human as a stopgap and declined.

**Answer the question dynamically** — run a guard's `--self-test` with the repository absent, on the
theory that a suite genuinely driving `main` over a built world still passes. ⚠ The read costed two
forms. A per-`main`-call runtime filesystem observer ran over all 44 guards in 87 s with 0
cannot-run and found 7 compliant; the brief's own cruder form (whole suite, repo absent) ran in
22.8 s and agreed with only 14 of 37, signal inverted, because many suites legitimately read the
real repository for their *other* cases. **Not rejected on principle — it is structurally blind to 3
of the 10 current credits, so it belongs beside a static rule rather than instead of one.** Filed.

**Change nothing.** Argued seriously, because the honest half of it is true: **not one of today's 44
verdicts was wrong**, both round-3 halves and the coordinator confirmed no false green among the 10
and no compliant guard among the 27 pins, and every defective matrix cell is a shape no guard on
disk uses. ⛔ What breaks it: the gate exists to be satisfied **27 more times**, it refused 8 of 10
spellings of the repair it demands with no diagnosis, and that refusal was live on the single file
D1 had been applied to. The conservatism everyone priced at zero is what would have met the next
author.

---

## ⛔ Corrections — three of the read's numbers were wrong

| claim | read said | re-derived | verdict |
|---|---|---|---|
| mutation anchors orphaned by the replacement | 14 of 66 | **16**, then **19** | ❌ |
| lines in the 7 replaced functions | 191 | **191** | ✅ |
| element-level credits exiting the default | 21 of 21 | **21 of 21** | ✅ |
| guards whose compliance rests on the default | 2 | **2** — `check-plan-code.py`, `check-selection-card.py` | ✅ |
| B2's single verdict disagreement | `check-ratchet-contract.py`, a gain | **confirmed**, and it is the ADR's own exemplar | ✅ |

The anchor count was derived by text-matching, which the read itself flagged as not a sweep. It
missed three anchors whose text changed through a renamed parameter rather than a deleted function,
and three more that mentioned the `seen` set deleted later in the build. **The sweep is what found
all six**, which is the standing lesson about a count nobody re-derives.

---

## Decided here, and written down nowhere before

⭐ **ADR-0014 asks D2 as a question about a RUN — *"does this guard's `--self-test` invoke `main()`
over a world the case constructed?"* — and the implementation answers it about SOURCE TEXT: *"can
any case point `main` at such a world?"*** That substitution was never recorded in the ADR, in a
docstring limit, or in a backlog row, and three review rounds argued about the consequences of a
fork nobody had named. It is the reason the dynamic instrument reads as an exotic alternative rather
than as the literal reading of the decision.

**Recorded as backlog #224** rather than resolved here: this review's scope was one question, and
whether D2 should be answered by running is a different one.

---

## Falsifiers

- **The leaf rule:** any future round fixing a defect in it by adding a node kind to a list inside
  it. That would mean propagation is not actually delegated to the grammar and the subject is
  irreducibly enumerative — in which case changing nothing was right, because an enumerative rule
  with 198 cases beats a fresh one with none.
- **The claim that the two defects were masking each other:** a measurement showing false credits do
  NOT rise when the import conflation is fixed alone.
- **The claim that today's verdicts were sound:** a guard among the 10 whose credited call site
  cannot observe a wiring defect in its `main`, or a guard among the 27 pins that is compliant.
  Three independent reads looked; none found one.

## Not measured

Repo-wide `--mutate .` had not completed when this document was written — the 71 entries for this
file are clean via `partial-sweep.py` over a green control and after-control, and the other 1,178
are certified only by the full run. The dynamic instrument was costed by the read and **not
re-derived by the coordinator**: its 87 s / 7-compliant figures are the read's, labelled as such,
and nothing in this document rests on them.
