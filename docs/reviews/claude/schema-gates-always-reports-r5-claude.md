# Round 5 — Claude half — `schema-gates-always-reports`, the r4-fix diff only

**Subject: `git diff 72f3aefa..2ed629e8`** — the single commit `2ed629e8` *"r4: 7 Low, prose floor,
safe to merge — and a gate found what the reviewer cleared"*, on branch `schema-gates-always-reports`,
PR #315. Confirmed by `git log --oneline -6` (HEAD `2ed629e8`, parent `72f3aefa`) and
`git diff --stat 72f3aefa..2ed629e8` — 7 files, 633 insertions, 11 deletions, of which
`docs/reviews/claude/schema-gates-always-reports-r4-claude.md` (566 lines) is the r4 record itself.
Rounds 1–4 reviewed everything up to `72f3aefa`; this commit is the only code no round has seen.

**VERDICT: CONVERGED — one Low, and it does not block.**
**This DIFF is SAFE TO MERGE.** The one finding is a stale denominator in a backlog sentence the
diff itself adds; it changes no gate answer and no code.

| Severity | Count |
|---|---|
| Blocking | 0 |
| High | 0 |
| Medium | 0 |
| Low | **1** |

I did **not** inherit the r5 codex verdict. Every claim below was executed against a clean checkout
of `2ed629e8`; all scratch work was done in `/tmp/r5claude`, which is deleted. No tracked file was
modified — `git status --porcelain` at the end shows only the two untracked r5-codex artefacts that
were already present.

---

## LOW 1 — the backlog paragraph this diff adds states a denominator of **165** that the same commit moves to **168**

**VERIFIED.** `docs/backlog.md:166` (row **138**), in the `+`-side paragraph
*"⚠ **TWO r4 FALSIFIABILITY GAPS CARRIED HERE RATHER THAN FIXED**"*, clause (2):

> (2) One of **165** cases computes its WANT from the subject (an AST-derived expectation), so it
> can never be a unique falsifier — invisible to `check-fixture-variation.py`, which sees parameters
> and not expectations.

**ORIGIN: (a) fix-induced.** The sentence is new in `2ed629e8`. `165` is r4's measurement, taken at
`72f3aefa` (`…-r4-claude.md:105`: *"the **only** one of the file's 165 static `case()` calls"*). The
same commit adds three `case()` calls, so the denominator was already 168 by the time the sentence
was written.

**Failure scenario.** A reader deciding whether the gap is still open re-derives the ratio, finds
1-of-168, and cannot tell whether a second such case was added and then removed, whether three cases
were dropped, or whether the row is simply stale. This is the shape the branch has already paid for
five times — r1 Medium 11, r3 Medium 3, r4 Low 5, and the two *corrections* in
`…-r3-coordinator.md` — and the r3-coordinator sentence corrected **in this very diff** ends with
*"Third time a count in this branch's coordination has been stated rather than derived."*
It is the fourth, committed alongside the third's repair.

**EXECUTED evidence.** The static call count, derived by AST at all three points:

```
$ python3 -  # ast.walk for Call(func=Name('case')) over scripts/check-review-recorded.py
origin/master   static case() calls: 120
72f3aefa        static case() calls: 165
2ed629e8        static case() calls: 168
```

The substantive claim is still true and still singular — it is the *denominator* that is wrong:

```
$ python3 -  # per case(name, got, want): does `want` name a module-level symbol?
static case() calls: 168
WANT references a subject symbol: 1 [(1855, ['diff_argv'])]
```

**Observation that proves it fixed:** the sentence carries no bare count, or carries 168 with the
derivation beside it. Given how often this cell has moved, dropping the denominator
(*"one case computes its WANT from the subject"*) is the fix that cannot go stale again.

**Not blocking.** It is prose in a backlog row, the claim it qualifies is correct, and no gate reads
it.

---

# The attacks that found NOTHING — with what was run

At this point these are the valuable result, so each is recorded with its evidence.

## 1. The `is_prose` split (`scripts/check-review-recorded.py:218-225`) — behaviourally identical

The change is `return <expr>` → `is_root_md = <expr>; return is_root_md`. That is a language-level
identity (bind a local, return it; no `global`/`nonlocal`, no rebinding, and `is_root_md` occurs on
exactly two lines in the file — `grep -n is_root_md` returns `224` and `225` only). I did not rely on
that argument alone. I reconstructed the pre-split function and differentially tested both against a
corpus far wider than the nine classes codex checked:

```
inputs compared: 3919
DISAGREEMENTS: 0 []
type mismatches: 0 []
```

The corpus was **every tracked path in the repository at HEAD** (`git ls-tree -r --name-only HEAD`),
every member of `PROSE_FILES`, `PROSE_DIRS` and `CODE_UNDER_PROSE`, all 2- and 3-way concatenations
of 18 structural fragments (`""`, `"/"`, `".md"`, `"md"`, `"docs"`, `"docs/"`, `"\n"`, `" "`, `"\\"`,
`".."`, `"."`, `"é"`, …), and an explicit oddity set: `NOTES.md`, `.gitignore`, `.md`, `/x.md`,
`x.md/`, `lib/README.md`, `README.md ` (trailing space), ` README.md` (leading space), `README.mdx`,
`Readme.MD` (case), `é.md`, `a\nb.md` (embedded newline), `docs\notes.md` (backslash),
`./README.md`, and both a `.md` and a `.sql` under `docs/superpowers/specs/m4/` — the
`CODE_UNDER_PROSE` early-return arm that the fallback never reaches. Zero disagreements, and the
return **type** matched on every input (both arms yield `bool`; the `and` chain cannot leak a
non-bool because both operands are comparisons).

I also checked the split did not orphan a text dependency elsewhere: no file outside
`scripts/mutations/check-review-recorded.json` mentions `is_root_md`, and no other manifest anchors
the old expression.

## 2. The two `KNOWN_UNVARIED` deletions (`scripts/check-fixture-variation.py:196-204`) — the variation is real, not gamed

This was the attack most likely to land, and it does not. Three things had to hold.

**(a) The comment's own measured claim is true.** Re-inserting both entries into a `/tmp` copy:

```
EXIT=0
  ⭐ check-review-recorded.py: `review_added.paths` now varies — delete it from KNOWN_UNVARIED
  ⭐ check-review-recorded.py: `verdict.pr_body` now varies — delete it from KNOWN_UNVARIED
fixture variation OK — 551 parameter(s) examined across 52 file(s); 126 known-unvaried ratcheted …
```

The ratchet does print *"delete it from KNOWN_UNVARIED"* and does exit **0** — a dead entry really
was sitting there pre-authorising a regression behind a green exit code.

**(b) The ratchet re-fires if either parameter stops varying.** Removing one case at a time from a
`/tmp` copy:

```
$ # new pr_body case deleted
✗ check-review-recorded.py: `verdict(pr_body=…)` is passed the SAME value at every call site
  in the suite (10x `''`). …                                                       rc=1

$ # `review_added(["docs/reviews/verdicts/x.json"])` case deleted
✗ check-review-recorded.py: `review_added(paths=…)` is passed the SAME value at every call site
  in the suite (1x `['docs/notes.md']`). …                                         rc=1
```

**(c) The varying cases are NOT ratchet-bait — each is the *unique* falsifier of a killed
mutation.** This is the specific HIGH the prompt asked me to look for, and it is absent. Running the
66 manifest entries against a staged copy (via `check-plan-code.py`'s own `stage_tree` /
`run_mutations`, not a reimplementation), each new case appears as the sole entry in its mutation's
`fails` list:

| Mutation | `fails` |
|---|---|
| `the root-.md prose fallback goes…` | `['a root .md NOT named in PROSE_FILES is still prose, via the fallback']` |
| `verdict stops reading the PR body…` | `['the pr_body is a real PARAMETER: a NO-REVIEW marker in it waives the round']` |

`review_added`'s two call sites are `["docs/notes.md"]` and `["docs/reviews/verdicts/x.json"]`; each
asserts a value and each is the named `expect` of a distinct caught mutation (*"review_added stops
requiring docs/reviews/"* and *"any file under docs/reviews/ counts as a review, not just .md"*) —
they falsify the two clauses of a two-clause predicate. No case exists whose only function is to move
a parameter.

**(d) Fixed as a class, not as an instance.** r4 Low 7 was one dead entry; the concern is siblings.
Repo-wide, `python3 scripts/check-fixture-variation.py | grep -c ⭐` returns **0** — no dead entry
remains anywhere in `KNOWN_UNVARIED`.

## 3. `_declared_reason` (`scripts/check-review-recorded.py:1342-1345`) — the new case passes for the REAL reason

The branch has produced seven ambient-reason cases, so I drove the boundary directly rather than
reading the lambda:

```
'NO-REVIEW: infrastructure only' -> (0, 'NO-REVIEW: infrastructure only')
''                              -> (1, '1 guarded path(s) changed and no review round was recorded…')
'NO-REVIEW:'                    -> (1, 'NO-REVIEW: was declared with no reason after it')
'NO-REVIEW:   '                 -> (1, 'NO-REVIEW: was declared with no reason after it')
'infrastructure only'           -> (1, '… no review round was recorded…')
'no-review: lowercase'          -> (1, '… no review round was recorded…')
'x\nNO-REVIEW: trailing'        -> (0, 'NO-REVIEW: trailing')

--- ambient probe: identical body, reason_of forced to ignore it ---
forced-empty: (1, '… no review round was recorded…')
```

`changed`, `added` and `reason_of` are held constant across the pair at `:1394-1397`; only `pr_body`
moves, and the verdict moves with it. The last line is the decisive one — feeding the *same* body
through a `reason_of` that cannot see it restores exit 1, which is precisely the mutation
`reason_of(pr_body)` → `reason_of("")` that the case kills. The pass is caused by the body.

The stub's whitespace/empty semantics also match the live parser's (`''` for a bare marker, refused
by `verdict`), and the LIVE parser is separately pinned by *"the shared parser reads NO-REVIEW:
through the same rules"*, so the stub is not standing in for it.

## 4. The prose (`docs/backlog.md`, `…-r3-coordinator.md`) — re-derived, not read

**Every number in the diff is right except the one filed above.**

`docs/backlog.md` row 137, three cells, each `from`-value taken from `origin/master` and each
`to`-value executed at HEAD:

| Cell | Diff | From-value checked | To-value executed |
|---|---|---|---|
| manifest | `43→64` ⇒ `43→66` | `origin/master:check-plan-code.py:796` says `43` ✓ | manifest holds **66** entries for the file ✓ |
| total | `714→735` ⇒ `714→737` | `origin/master:check-plan-code.py:3187` says `714` ✓ | `sum(EXPECTED_MUTATIONS.values())` = **737**, and `len(load_manifests())` = **737** ✓ |
| self-test | `139→182` ⇒ `139→187` | `origin/master:check-review-recorded.py:5` says `139` ✓ | `--self-test` prints **187/187 passed** ✓ |

The middle column matters: `182` was itself wrong (the docstring at `72f3aefa` already said **184**),
which is what r4 Low 5 filed; `187` is measured, not incremented.

**The corrected asymmetry sentence is now arithmetically exact.** Derived from the round documents'
own headers rather than from the sentence:

```
r1 claude 14 · r2 claude 9 · r3 claude 8 · r1 codex 1 · r2 codex 1 · r3 codex 2   TOTAL 35
neither (6): r1 M11, r2 M5, r2 L9, r3 H1, r3 M3, r3 M4
#137   (2): r1 M10, r1 L14        (the two the document itself names at :77-79)
=> collateral derivation: 35 - 6 - 2 = 27
```

`~27` is not an approximation — it is the exact figure, and `~2` is the pair the document defines
three paragraphs above. The self-contradiction r4 Low 6 found (`:64` calling r3 High 1 a coordinator-
document defect while `:94` counted it in the derivation) is resolved: the correction names r3 High 1
explicitly as *"the workflow plus the r2 coordinator document"*, matching `:64`, and the per-half
breakdown is dropped rather than re-stated — the second of the two remedies r4 Low 6 offered.

I also verified the r4 measurement the new backlog paragraph reports, since it is a claim the diff
introduces. Both mutations against `_is_file`'s `except (OSError, ValueError)` really do survive,
over a control proved green first:

```
control green: True
_is_file re-raises          -> caught: False  fails: []
_is_file narrows to OSError -> caught: False  fails: []
survivors: ['_is_file re-raises', '_is_file narrows to OSError']
```

## 5. The manifest — 66, unique, all killed, all attributed, declared == accepted

Run against a staged tree with `$HOME` redirected, through the harness's own functions:

```
manifest entries for scripts/check-review-recorded.py: 66
EXPECTED_MUTATIONS says: 66
unique names: 66     unique anchor-sets: 66     unique find-texts: 66 of 66
CONTROL green: True  rc=0  tail= 187/187 passed
survivors: []
… 66/66 with caught=True, attributed=True, measured=True
RE-CONTROL green: True
```

Repo-wide, with no per-file filtering:

```
manifest load problems: []
DRIFT: []                      (no target's count differs from EXPECTED_MUTATIONS)
undeclared targets: []
total manifest entries: 737    declared sum: 737
duplicate names repo-wide: []
```

Five anchor collisions have been paid for on this branch; there is no sixth. The old anchor
`return path.endswith(".md") and "/" not in path` is gone from the manifest, the two replacements are
each unique in the file, and `home_escapes` is clean on both targets and both replacement texts (the
drift list is empty, which is where that check reports).

## 6. Anything simply wrong — the guard suite, run

```
check-docs.py               rc=0  Documentation integrity OK
check-ratchet-contract.py   rc=0  ratchet contract OK
check-anchors.py            rc=0  12 registered, all claimed; floor 22 held
check-guard-coverage.py     rc=0  every SEQUENCE guard reconciles and is mutation-covered
check-selftest-counts.py    rc=0  40 script(s) declare a count, every one verified by running it
check-backlog-closure.py    rc=0  WARN — 2 row(s) may be stale, 0 orphaned (hygiene, not a failure)
check-test-counts.py        rc=0  2,819 unit / 274 suites
check-fixture-variation.py  rc=0  551 parameters, 52 files, 124 ratcheted, 7 exempt
check-plan-code.py          --self-test 128/128
check-dashboard-entry.py    rc=0  an entry block was added
check-review-rounds.py      rc=1  ← EXPECTED: "round 5: only codex" — this document is the fix
check-review-recorded.py    rc=1  ← EXPECTED and CORRECT: the gate refuses the merge because
                                    r4's closest verdict never saw the four files in this diff
```

Both reds are the repo's own gates correctly describing the situation that made this round
necessary, and both clear when this round is committed. No other guard reports anything.

**Incidental, outside the diff, no severity:** `check-fixture-variation.py` prints the
`verdict.pr_body` "now varies" line **twice** when the entry is present (see §2a). Pre-existing
reporting duplication in the ratchet, not introduced here, and it does not affect the verdict.

**Also outside the diff, flagged not filed:** `docs/backlog.md` row 137 still reads
*"`schema-gates.yml` filters by `paths:` at the workflow level (`:60-82`)"*. That text is byte-
identical on both sides of this diff (the only backlog changes are the three numbers and the new
paragraph), and the branch deletes those filters — `:32` of the workflow now carries *"WHY THERE IS
NO `paths:` FILTER HERE ANY MORE"*. The passage reads as history explaining why the row exists, and
the row's tail states the post-merge action correctly, so I am not filing it; a reader following
`:60-82` will land somewhere else, which is worth one sentence if the row is ever touched again.

---

## Verdict

**CONVERGED. 0 Blocking, 0 High, 0 Medium, 1 Low.**

The diff does what it says. The `is_prose` split is a provable no-op that buys two opposite mutation
anchors; both `KNOWN_UNVARIED` deletions are backed by variation that is real, necessary and
mutation-pinned, and the class was swept rather than the instance; `_declared_reason` makes
`pr_body` a genuine parameter with its own paired control; and the corrected arithmetic in the
coordinator document is exactly right for the first time on this branch. The single Low is a
denominator in a backlog sentence, stale the moment it was committed because the same commit moved
it.

**This diff is safe to merge.** The Low should be fixed or filed, but it blocks nothing: it changes
no code, no gate answer, and no decision.

**Review method note:** no `REVIEW GAP` — both halves of round 5 ran. The codex half
(`docs/reviews/codex/schema-gates-always-reports-r5-codex.md`, verdict `gate_ran: true`, `head:
2ed629e8`) found nothing; this half was conducted without reading its conclusions as evidence, and
reached the same verdict by independent execution plus one finding it did not report.
