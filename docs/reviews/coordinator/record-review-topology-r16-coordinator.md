# record-review-topology — round 16, coordinator adjudication (the LAST review round)

Both halves ran against HEAD `dc9fe107` plus the uncommitted delta.

* Claude: `docs/reviews/claude/record-review-topology-r16-claude.md` — 0 Blocking, **1 High**, 2 Medium, 1 Low. NOT CONVERGED.
* Codex: `docs/reviews/codex/record-review-topology-r16-codex.md` (`gpt-5.5`) — 0 Blocking, 0 High, 0 Medium, **1 Low. CONVERGED.**
* Verdict: `docs/reviews/verdicts/record-review-topology-r16-codex.verdict.json`, `gate_ran: true`.

**⛔ THIS IS THE FINAL ROUND, by the user's decision of 2026-09-14:** fix anything Blocking or High,
merge regardless, file the remainder to `docs/backlog.md` rather than loop again. Taken with the
trade-off stated in full — on this branch a fix has generated the next round's defect five times out
of six, so a pre-commitment to stop can merge a known-imperfect gate.

## ⭐ THE HALVES AGREED, AT DIFFERENT SEVERITIES, AND THE DIFFERENCE IS THE LESSON

Both found the same defect in `prose_exceptions_cover`. Codex filed it **Low** and said why:

```text
['docs/superpowers/specs/**'] -> []        # should report
['docs/**']                   -> []        # should report
```
> *"This is not live against today's workflow. With the actual quoted globs … the helper returns
> `[]` correctly."*

That is true, and it is the whole of the disagreement. Claude filed it **High** because it had also
found the *other half*: the falsifier was fed a **transcription** of the workflow's globs typed into
its own test, so nothing would ever notice the workflow broadening. Alone, the clause is dormant;
combined with the transcription, it is r15's High rebuilt inside the mechanism meant to prevent it.

**The reviewer that traced one observation to a second defect rated it correctly.** Same evidence,
same command output, opposite conclusions about whether it blocks — and the difference was not
diligence but how far each followed the thread. Six rounds in, that is the clearest statement of why
these halves are not redundant: *"zero overlapping findings"* did not survive, but *"they are not
redundant"* keeps being re-earned.

## H1 — the anti-drift falsifier could not see drift, and `main` never called it

`prose_exceptions_cover`'s docstring claimed its case was *"fed the REAL globs from
schema-gates.yml"*. It was fed a literal list. **Copy #1 the workflow, #2 `CODE_UNDER_PROSE`, #3 the
case — and it compared #3 against #2, neither of which is the authority.** Measured by the reviewer:
adding a `docs/` gate directory to the workflow and touching nothing else left the suite at
**134/134, rc=0**, while the new gate's code classified as prose and the gate printed *"no guarded
path changed"* — r15's High, line for line.

Two further facts made it worse: the `e.startswith(prefix)` clause cleared any **broader** glob
(`docs/**` reported full coverage), and **deleting that clause changed no case** — the one clause
creating the hole was the one no case could break. And the rule's answer went to nobody: a pure
function returning a list that `main` never called is not a gate.

**FIXED.** `workflow_docs_globs(text)` is pure and a thin impure reader hands it the real file;
`main` calls the rule before either question, with CANNOT RUN on a missing workflow **and on a scan
that finds zero globs** — a zero over nothing is not a finding. The broader-glob clause is gone and
cased; the trailing-slash tolerance it legitimately provided is kept and separately cased.

**Verified by reproducing the reviewer's own scenario against the repair:**

```text
drift introduced: m5-newgate added to the workflow, script untouched
FAILED — CI path-filters 1 `docs/` director(ies) as gate subjects that this gate still
         classifies as PROSE:  docs/superpowers/specs/m5-newgate/**            rc=1
```

## M1, L1 — false statements in recorded reasoning, corrected rather than filed

Both were mine, and both are the defect class this branch is named for.

* The `.md` carve-out was justified in the **present tense** — *"the spec's own prose lives beside
  its gate scripts"* — when **zero `.md` files are tracked** under either exempted directory, and
  its case pins a path that does not exist. Corrected to prospective policy; the case now says
  *"(none exists there today)"*.
* r15's coordinator cleared four `docs/` artifacts as *"generated"*. **Three are authored** —
  `architecture.html` is the published source of truth and carries two `<script>` blocks; the `.tex`
  and `.css` are build inputs with no producer. The property that matters is *not read by any gate*,
  which is true; "generated" was not.

## M2 — filed, not fixed: backlog #114

`.gitignore` is classified prose, against the scope authority this gate cites: `dev-process.md` puts
**any config** in *"Branch + PR, always"* while docs are merely batched. No live escape was
constructed, and moving it out of `PROSE_FILES` is a **policy** change — every `.gitignore` edit
would then owe a round — so it is the user's call, not a mechanical repair. The blast radius is real
in one direction, and this repo has paid for that exact shape once (backlog #86, a bare `*` making
`git status` answer "clean" about files it could not see).

## ⚠ THREE HARNESS REFUSALS, AND EVERY ONE WAS RIGHT

Getting this round's coverage measured took four attempts, and the three failures are worth more
than the pass:

| run | verdict | cause |
|---|---|---|
| 626 | `NOT MEASURED — 625 of 626` | r15's fix rewrote `second_question`; **anchors bind by TEXT**, so r12's mutation silently stopped applying |
| 629 | `CANNOT RUN — control red at 138/139` | the new case reads `schema-gates.yml`, which `HARNESS_TREE` did not stage |
| 629 | `NOT MEASURED — 628 of 629` | r16's fix rewrote `prose_exceptions_cover` (anchor), **and** the M1 fix RENAMED a case an entry pointed at (expect) |
| 629 | **`629 killed, 629 attributed, 0 survivors`** | — |

⛔ **AN ENTRY BINDS TO ITS TARGET TWICE — by anchor text and by case name — and a pre-flight that
checks one passes exactly when the other breaks.** My first sweep checked only anchors, certified the
tree, and the expensive run died anyway. ⚠ The generalised version of that sweep then produced **169
false positives**, because suite helper names vary across the 44 files; scoped to the two manifests
actually being edited, it is clean. A stand-in weaker than its subject, for the third time in one
session.

⟳ `HARNESS_TREE` gains `.github/workflows` (44 KB, two files) — its own comment already recorded
*"a scripts-only tree gave each a red control"* for four other guards a week ago, and it happened
again for a new subject. The rule became measurable in the same move that made it correct: reading
the real workflow is what forced the workflow into the harness tree.

## Measured on the shipping tree

```
check-review-recorded --self-test  139/139     codex-review --self-test         85/85
check-plan-code       --self-test  128/128     check-ratchet-contract           41/41
check-fixture-variation --self-test 60/60      check-selftest-counts            18/18
check-review-rounds   --self-test   29/29      check-guard-coverage             37/37
--mutate .   44 file(s), 629 mutation(s), 629 killed, 629 attributed, 0 survivor(s)
live: check-selftest-counts, check-fixture-variation, check-ratchet-contract, check-docs,
      check-anchors, check-review-rounds, check-dashboard-entry, check-backlog-closure — rc=0
```

⚠ **A process note, recorded because it cost two hours.** The coordinator waited on Codex r16 by
polling for its *process* rather than reading its *output file*. The review was written at 12:50 and
the process then hung for **1h53m**; three status reports said "still running" over an artifact that
already existed. `docs/plugins.md` states the rule being broken — *"never passively wait on a
background review … within ~2–3 minutes, read the actual Codex task output file … treat as a hang."*

CONVERGED on the Codex half; the Claude half's High is fixed and its remainder is filed. **Round 16
is the last. What follows is one dispatch whose only purpose is to produce a verdict covering the
shipping tree, so the branch's own rule can be satisfied by evidence rather than waived.**
