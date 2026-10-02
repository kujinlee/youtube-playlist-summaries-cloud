---
name: a-mechanical-edit-damages-what-it-preserves
description: "FIRES-WHEN: running a bulk, scripted or AST-driven edit across files — An AST pruner broke SURVIVING code three times in one session, once leaving five tests that could never fail — every instance found by RUNNING against a control, none by reading the diff"
metadata:
  node_type: memory
  type: feedback
---

**MEASURED 2026-09-09, `retire-plan-mode` PR 2 (#271).** Deleting 143 test cases by hand was
not viable, so I wrote an AST pruner. It worked — and it damaged code that was supposed to
survive **three separate times**, each by a different blind spot in how it modelled Python:

1. ⭐ **It recursed into a nested `def` whose PARAMETERS its binding-scan could not see**, judged
   the reads unsatisfied, and deleted the body of `_constructs` — leaving **five cases that could
   no longer fail**. The suite still said `passed`. A vacuous green is strictly worse than a red.
2. **Reads were counted before subtracting what a statement binds itself**, so a `for` target
   looked like an unsatisfied dependency on something already deleted.
3. **A `def` binds its name through `FunctionDef.name`, not an `ast.Name` store**, so deleting a
   helper did not propagate to the cases calling it — they survived, reading a symbol nothing
   defined.

**Every one was caught by running the suite against a control taken FIRST (229/229), never by
reading the output.** Two produced a crash or a `NameError` — loud. The first produced a *pass*.

## What to do

- **Take the control before the first edit**, and compare the count after every chunk. "Watch the
  number fall by the amount you intended" is the whole method; without the control it is nothing.
- **Never let a mechanical tool touch a nested scope.** Function bodies, comprehensions and lambdas
  bind names your outer analysis cannot see. Treat them as ATOMIC: they live or die whole.
- **A prune that leaves a container empty is an `IndentationError`, not a smaller suite** — a
  container whose body all dies must die with it.
- **Automation stops where dependencies leave the AST.** The last residue here flowed through the
  FILESYSTEM (`write_text` → a later read); no name-based rule can see it. Expect a hand pass and
  budget for it, rather than trusting the tool to have finished.

⚠ **The tell that a mechanical edit went wrong is a test that still passes.** After any scripted
deletion, ask of every surviving assertion: *could this still fail?* See
[[fixing-a-premise-is-not-covering-the-branch]] and [[the-control-refuted-the-premise]].

## ⟳ 4th instance, 2026-09-09 (PR #278) — the ESCAPED DELIMITER

Editing one cell of `docs/backlog.md` row 91 with `line.split("|")` + `" " + cell.strip() + " "`.
The description holds an **escaped** pipe — `` `Measured \| NotMeasured` `` — which the naive split
treats as a boundary. Re-padding inserted a space between backslash and pipe, turning `\|` into
`\ |` and **promoting a literal into a structural boundary**: 6 columns became 7.

⭐ **The guards were all true and all useless**: no newline in a cell, no bare pipe, exactly one row
91, unchanged row count — every one about a cell I **changed**, while the damage was in a cell I
merely **reformatted**. Caught by `check-docs.py`, never by my own assertions.

**Two rules this yields.** (1) A re-serialising edit must assert on the cells it does NOT intend to
touch — here, `old.count("\|") == new.count("\|")`. (2) **Do not re-implement the consumer's
splitter.** `check-docs.py` exports `CELL_SPLIT`, whose whole purpose is this escaping rule; my
`split("|")` was a second implementation that drifted. Same day, same change, I also re-implemented
`check-backlog-closure.py`'s `CLOSING` regex from its docstring, omitted the optional `(#PR)` squash
suffix, got 0 matches against the script's 7, and nearly reported *"the gate is broken"*.
See [[a-second-implementation-of-one-rule-drifts]].
