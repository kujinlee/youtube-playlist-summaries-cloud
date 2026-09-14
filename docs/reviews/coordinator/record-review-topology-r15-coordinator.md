# record-review-topology — round 15, coordinator adjudication

Both halves ran against HEAD `dc9fe107` plus the uncommitted delta.

* Claude: `docs/reviews/claude/record-review-topology-r15-claude.md` — 0 Blocking, **1 High**, 1 Medium, 1 Low. **NOT CONVERGED.**
* Codex: `docs/reviews/codex/record-review-topology-r15-codex.md` (`gpt-5.5`) — **0 findings. CONVERGED.**
* Verdict: `docs/reviews/verdicts/record-review-topology-r15-codex.verdict.json`, `gate_ran: true`.

**The halves split for the SECOND consecutive round, the same way. The finding-reviewer is now right
five times out of five on this branch.** Codex ran the right commands, reported everything green, and
was not careless — every claim it made is true. It reviewed the *repair*. Claude reviewed the
*deliverable*, and the deliverable is where the defects were.

## ⚠ A CORRECTION TO THIS BRANCH'S OWN NARRATIVE, RECORDED BEFORE THE FINDINGS

The r14 adjudication and the coordinator's status reporting both argued that severity was falling and
findings were migrating AWAY from the deliverable — and predicted r15 would close the loop. **That
prediction was wrong, and the shape of the error matters more than the error.** r15 found the two
most serious defects since r11, both fail-opens, both in `check-review-recorded.py` itself. The trend
was read off *severity labels* rather than off *what the rounds were looking at*: r12 and r13
attacked the instrument and found instrument defects; r11, r14 and r15 attacked the deliverable and
each found a fail-open in it. The variable was never the round number.

## H1 — `docs/` IS NOT PROSE IN THIS REPOSITORY

`PROSE_DIRS = ("docs/",)` classified every path under `docs/` as prose. Two of the **fifteen schema
gates are files under `docs/`**:

| path | mode | run by |
|---|---|---|
| `docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh` | `755` | `check-schema-gates.sh:19` — gate 1/15 |
| `docs/superpowers/specs/2026-08-03-stable-blob-addressing/mutate-schema.py` (73 KB) | `755` | gate 2/15 |
| `docs/superpowers/specs/m4/live-manifest.txt`, `accepted-additions.txt`, `*.sql` | | gates 10 and 14 |

`.github/workflows/schema-gates.yml:80-81,103-104` lists both directories as **path-filter
triggers** — the workflow itself declares them gate subjects. Verified independently by the
coordinator before acting:

```text
is_prose(mutate-schema.py)  = True      guarded_changes(all three) = []
verdict(...)         -> (0, 'no guarded path changed — a review round is not required')
second_question(...) -> (False, None)        # the final-tree question is never asked
```

**Both halves of this gate went silent over executable CI gate code.** A branch weakening a mutation
in `mutate-schema.py`, or relaxing a line in `live-manifest.txt` so a gate stops noticing a schema
object, merged with no round and no declaration — the 2026-09-09 night in WHY THIS EXISTS, reached
through the classifier instead of through the diff.

⭐ **It falsifies a claim this branch filed itself.** The r11 Claude half states it *"searched `docs/`
for executable or consumed artefacts that would be wrongly exempt: everything found is `*.md` and
`docs/reviews/verdicts/*.json`."* Two exist. r15 found them by **re-deriving that claim rather than
inheriting it** — the identical move that found r14's rename fail-open one round earlier. Two rounds
running, the defect was inside a sentence a previous round had already marked clean.

**FIXED** — `CODE_UNDER_PROSE`, honoured first in `is_prose`.

⚠ **And the first draft of the fix was too broad, caught by a case in the same commit.** It exempted
the whole directory, so the spec's own prose would have obliged a review round — backlog #56's shape.
What the gates actually consume was then ENUMERATED from `check-schema-gates.sh` (`helper*.sh`,
`mutate-schema.py`, `verify-schema.sh`, `live-manifest.txt`, `accepted-additions.txt`, `*.sql`) and
**no `.md` is read by any gate**, so `.md` stays prose inside the exception. Measured, not assumed.

**The anti-drift falsifier.** `CODE_UNDER_PROSE` is a second copy of a path set, which this repo
refuses elsewhere. `prose_exceptions_cover(globs)` is pure, takes the workflow's globs as an
argument, and its case feeds it the real ones — so a new `docs/` gate directory CI guards but the
tuple does not know about is reported. Run against the live workflow: **`[]`**.

## M1 — an EMPTY `NO-REVIEW:`, which question one REFUSES, fully waived question two

`verdict()` refuses a bare marker (*"declared with no reason after it"*, pinned by a case AND a
mutation). `second_question()` tested `waiver is not None`, and `reason_of` returns `''` — not
`None`. The two rules only ever met when a review document was also filed, because then `verdict`
returns 0 at its review-document branch and never reaches its own refusal. Measured `rc=2 → rc=0`,
with a log line where only a double space betrays it. **FIXED**: one marker, one meaning, both
questions.

## L1 — `--pr-body-file` on a missing file

`FileNotFoundError` straight out of `main`: rc=1 with a traceback where the docstring promises 2.
The r1 Major recorded twelve lines below — *"'Cannot run' collapsing into an ordinary failure is the
exact shape this repo refuses"* — fixed there for the git calls, one statement short of the class.
**FIXED**, now `rc=2` with a CANNOT RUN sentence. Not reachable from CI, which `printf`s the file.

## ⭐ THE GATE CAUGHT MY OWN REPAIR ORPHANING AN OLDER MUTATION

The 626-entry run came back **`NOT MEASURED — 625 of 626 declared mutations produced a verdict`**:

```text
✗ mutation 'the second question is switched off entirely': anchor NOT FOUND — it was not
  applied, so its 'caught' verdict would be meaningless
```

r15's fix rewrote `second_question`'s body, and **anchors bind by TEXT**, so r12's mutation silently
stopped applying. This is a named recurring failure in this project, and the thing worth recording is
that **the harness refused rather than passing**: 625 kills with one unapplied entry is exactly the
shape that would otherwise read as success. Re-anchored and re-proved; then every anchor in every
manifest was swept — **633 anchors, 0 orphaned, 0 ambiguous**.

## The exhaustiveness pass, run on the CLASSIFIER this time

r14's pass covered git *flags*. H1 proved the same question was unasked of the *classifier*, so it
was run: of **2,213 tracked files**, 1,347 classify as prose; of those, 101 are not `.md` — **96 are
`docs/reviews/verdicts/*.json`** (which must be prose, or filing a verdict would oblige a round),
plus `.gitignore` and four documentation artifacts (`architecture.html`, a print CSS, a TeX source,
a PDF). **None is read by any gate.** The class is closed by enumeration, not by assertion.

⟳ **r16 Low corrected the word used here.** This paragraph said those four were *"generated"*. Three
are **authored**: `architecture.html` is the published source of truth per
`scripts/publish-arch-page.sh:6` and carries two `<script>` blocks, and the `.tex` and `.css` are
LaTeX/print build INPUTS with no producer anywhere in the repo. Only the PDF is an output.
Classifying all four as prose is still right on the blast-radius axis — the property that matters is
*not read by any gate*, which is true — but "generated" was false, and the next person re-deriving
this list would have read it and stopped.

## Measured on this tree

```
check-review-recorded --self-test  134/134     codex-review --self-test        85/85
check-plan-code       --self-test  128/128     check-ratchet-contract          41/41
check-fixture-variation --self-test 60/60      check-selftest-counts           18/18
check-review-rounds   --self-test   29/29      check-guard-coverage            37/37
live: check-selftest-counts, check-fixture-variation, check-ratchet-contract, check-docs,
      check-anchors, check-review-rounds — all rc=0
EXPECTED_MUTATIONS: 44 files, sum 626 · anchors: 633 checked, 0 orphaned
```

## ⛔ ROUND 16 IS THE LAST ROUND — a human decision, recorded

The r15 repair is unreviewed code, so a round is owed. **The user's decision (2026-09-14) is that
round 16 is the final one: fix anything Blocking or High it returns, then merge regardless, and file
any remainder to `docs/backlog.md` rather than looping again.**

The decision was taken with the trade-off stated in full: on this branch a fix has generated the next
round's defect four times out of five, so a pre-commitment to stop can merge a known-imperfect gate.
Against that — every defect found has been fail-CLOSED-able, none shipped, and the defect class the
last three rounds found (an under-specified input classifier: rename pairing, prose directories,
empty declaration) has now had its exhaustiveness pass and comes back clean by enumeration. That is
what `review-method.md` prescribes for a branch-coverage defect, and all three findings pass its test
— *can a redesign remove it?* — as **no**.

NOT CONVERGED — r16 owed, and final.
