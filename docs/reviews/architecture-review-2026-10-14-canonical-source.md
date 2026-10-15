# Architecture review — one canonical source per mechanism (backlog #282)

**Armed by THRASHING**, per `docs/dev-process.md` Phase 6: *two consecutive rounds whose findings
came from the previous round's own fix, in one component*. Convened on the
`plugins-handoff-citations` branch at `dd595394`, and written AFTER the redesign it records, because
the owner approved the redesign when the arming condition was reported.

⚠ **This document is the record of a decision, not its justification after the fact.** The decision
rests on round 6's per-round evidence table, reproduced below, and on three measurements I made by
hand. Where I accepted a reviewer's claim without re-deriving it, the finding says so.

---

## The question, and the answer

*Thrashing, or a prose floor?* — **thrashing.** Round 6's Codex half tabled six findings, each
traced to the fix that caused it, and I verified the two load-bearing ones by hand:

| finding | the fix that caused it |
|---|---|
| r4 Claude H1 | `2ad7038a` replaced "reads the index" with "reads working-tree content"; index-masked fixtures refuted the replacement |
| r4 Claude H2 | that fold substituted another store-position label instead of the requested comparison, and its own `data_dir=notes` control contradicted it |
| r4 Claude H3 | the fold edited the memory paragraph and left its retired "ONE INSTRUMENT" headline standing |
| r5 Codex H1 | `7bf8867c` added "two that agree can"; matching filenames concealed different indexed and disk content |
| r5 Codex H2 | that fold introduced the immediate-child label, refuted by `./notes` and `..`, and left `docs/plugins.md` unrepaired |
| r5 Claude H1 | `1a2cc8de` withdrew a false label by DELETING the true linked-worktree clause, reopening r4 M3 |

⭐ **Verified by hand, and it is the finding that settles the question** (F1 below): the round-5 fix
for the "iff" overclaim reached `.agents/skills/handoff/SKILL.md` and never reached
`.claude/hooks/enforce-handoff-path.sh`, so the hook's own refusal message printed a claim AND its
withdrawal together. A reader being blocked was handed both.

**Can a redesign remove it?** Yes — and that is the test `docs/review-method.md` prescribes. The
defect is not any one sentence; it is that one mechanism had six independently maintained
descriptions and nothing compared them.

---

## Findings verified by hand

### F1 · The hook and the skill disagreed because nothing could compare them — not because either was careless

Measured at `dd595394`, newline-folded (a single-line `grep` cannot see a clause that wraps, and
that instrument error cost three measurements on this branch in one day): the biconditional
withdrawn in the skill survived in the hook, and the hook's refusal contained both statements.
⭐ Six sites, no comparator, five rounds, five drifts — the per-round table above is the shape of a
STRUCTURAL defect, not of five careless folds. This is the repo's most-measured defect class, *a
second implementation of one rule drifts*, applied to prose instead of code.

### F2 · The repo had already solved this once and the solution did not travel

`scripts/check-explainer-delivery.py` exists because the explainer delivery loop was written out in
two skills and a third would have made three copies. Its docstring states the governing rule in its
own words — *a prose rule saying "don't restate it" is exactly the shape this project has measured
as insufficient: a convention catches what you READ, a script catches what is THERE.*
⛔ **That rule was correct, recorded, enforced for skills, and not applied here for fifteen months
of this branch's lifetime.** Instance, not class — which is itself a finding this repo files often.
⭐ The redesign generalises that guard rather than inventing a mechanism: any mechanism, any kind of
citing file (a skill, a hook, a script comment, a doc, a memory note).

⟳ **2026-10-14, r6 CLAUDE H5 — THE SENTENCE ABOVE IS WRONG AND IS LEFT STANDING BECAUSE THIS IS A
RECORD.** It does not generalise that guard; it is a second guard beside it, which is this branch's
own most-cited defect committed at the guard layer — and the composition finding this very review
should have produced. What the two share is a PATTERN (canonical file, marker, declared citing
sites, a guard). What differs is the KIND of thing each forbids, and that is why they cannot be one:

* `check-explainer-delivery.py` forbids a **runnable procedure** — oracle: a FENCED CODE BLOCK
  carrying a delivery command, or a `Monitor({` arming block — scoped to `.agents/skills/*/SKILL.md`;
  and it alone asserts **enumeration completeness** (a page-producing skill absent from `PAGE_SKILLS`
  escapes the check). Folding it away would DELETE that falsifier, which nothing else makes.
* `check-canonical-source.py` forbids a **symbol** — oracle: a token substring over four directories
  and three extensions.

⭐ **Measured, which is what settles it rather than taste:** in the canonical-source population
`explainer-serve.py` carries **34** non-exempt sites and `brief-compose.py` **26**, fourteen of them
the scripts that call or test the tool. A token oracle for the delivery procedure would fire on its
own implementation. ⚠ H5's own supporting figure — "nine live non-review sites" — names no
population and does not reproduce; 34 is derived by importing this guard's `_tracked_textfiles` and
`EXEMPT` rather than by a separate walk.
⚠ **The residual hole, stated rather than discovered later:** the delivery procedure restated in a
file that is NOT a `SKILL.md` is invisible to both guards. Filed as backlog **#288**.

### F3 · The canonical statement is not self-validating, and the redesign does not claim it is

Round 6 stated this limit and it is worth preserving: collapsing six copies into one removes
*copies disagreeing with each other*. It does **not** establish that the surviving description
interprets the vendor correctly. Behavioural controls remain necessary, and they are what caught
every refuted label — `./notes`, `..`, the bare-repo worktree, the submodule, the absolute
`data_dir`. ⚠ A single source that is wrong is wrong in one place instead of six: better, not safe.

### F4 · Three guards each refused a different shortening of the new guard, and all three were right

Recorded because the sequence is the useful part, not the destination:
`check-main-drivable.py` refused a `main()` no case drives, and refused again when the two driving
calls used the real repo and a nonexistent path (*"none over a world the case built"*);
`check-fixture-variation.py` refused an `argv` that only ever received `[]`; and removing `argv`
to satisfy that broke main-drivable, whose `_passes_extra_world` reads `positional[1:] | kwonly`
and so needs the world to sit BEYOND argv, which is ADR-0014's D1 shape.
⭐ ADR-0014 is not re-litigated here — it was complied with, and complying with it is what exposed
the interaction. ⚠ I found the resolution by calling `world_class` and `classify` directly on my own
call sites after guessing twice, which is the method, not the anecdote.

### F5 · The exempt surfaces are a real residual gap, and they are exempt deliberately — backlog #282

`docs/reviews/**` is frozen testimony and `docs/dashboard-entries.md` holds dated entries: a record
of what was true on a day, not a rule a reader follows at the moment of need. Both are exempt from
`check-canonical-source.py`, so **drift inside them is not caught.** The dashboard currently carries
a description of the cross-check that the canon now owns, and nothing compares the two.
⛔ **Second half of the same gap:** the guard's `CANONS` table is hardcoded, so a THIRD mechanism
described at two live sites is unprotected until someone adds it. That is the same accepted risk
`PAGE_SKILLS` carries in the explainer guard, and like it, a missing canonical FILE errors loudly
while a missing table ENTRY is silent.
**FAILS IF:** a mechanism is described at two non-exempt live sites and `check-canonical-source.py`
exits 0.

### F6 · What we decided this round that was not written down

Phase 6 asks this explicitly. Two things:
* **That a vendored file may cite a repo file at all.** `.agents/skills/handoff/SKILL.md` is reverted
  by `npx skills@latest add`, so its citation is layer 3 — convenience, not mechanism. The canon
  plus the guard is the durable part. That layering already existed in `docs/plugins.md`; what was
  new is that the citation strategy depends on it, and that is now stated in the canon itself.
* **That counts in prose are a liability, not evidence.** Round 6 could not replay `13/14/12/14`
  because a file explaining the difference had been committed in between. The canon now states the
  SHAPES each tool misses and says counts move whenever a file is committed. ⚠ That is a general
  lesson this repo has paid for repeatedly and had not written where a reader meets it.

---

## Not run, and not passes

* The `--mutate .` shard matrix, and `check-test-counts.py` (no `jest-results.json`).
* Host or UI delivery of the hook's refusal: shell exit codes and stderr do not establish what a
  reader sees, and that has never been measured on this branch.
* Round 6 L2 — the figures in `docs/memory/an-instrument-that-edits-the-repo-corrupts-its-peers.md`
  still name no script, arguments, interpreter or ref. Filed as backlog #283, not fixed here.
* I did not independently reproduce round 6's bare-repository-worktree or submodule controls; I
  accepted them and wrote the redirect's conditions from its table. The canon's claim is therefore
  as strong as that reviewer's measurement, which is stated there rather than implied.
