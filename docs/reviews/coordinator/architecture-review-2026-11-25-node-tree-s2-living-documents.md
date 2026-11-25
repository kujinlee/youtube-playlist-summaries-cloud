# Architecture review (Phase 6) — PR #637, node tree slice S2: how `check-goal-status` reads a document's anchor

- **Subject:** `living_documents`, `with_document_anchors`, `armed` and `main` in `scripts/check-goal-status.py`, and
  the header reader they call, `parse_header` in `scripts/check-anchors.py` (now with a `lenient` flag).
- **Armed by:** THRASHING. `check-review-decision.py` reports ARCHITECTURE_REVIEW: the component
  `scripts/check-goal-status.py living_documents` carried fix-induced findings in review rounds 3 and 4 (and round 2).
- **Read first:** `CONTEXT.md`, ADR-0010 and ADR-0016, `docs/review-method.md` (the stop condition, *can a redesign
  remove it?*), the four coordinator round documents, the Codex half of round 2, the Claude halves of rounds 1, 3
  and 4, the spec (`2026-11-23-goal-node-tree-design.md` §2.5 G4, §6 Q6) and the plan (Task 9, choices C10 and C12).
- **Changed by this review:** this file only. No code, no other document, no commit.
- **Tagging:** **[M]** = measured by me (a command run, or code quoted). **[I]** = inferred.
- **Baseline:** worktree head `635644df`; `origin/master` and the merge base are both `68529dd9`. Self-tests at the
  head **[M]**: check-goal-status 41/41, check-anchors 24/24, check-features 101/101, gen-goals-page 85/85. The live
  `check-goal-status` run is rc 0 with the same 13 armed slugs master hard-coded. Mutation sweeps were NOT run by me.
- **Instrument:** a differential probe. One synthetic repository per case (a tree of five nodes and one spec), run
  through `main()` of four versions of `check-goal-status`: master, the Task 9 commit `214a4fe7`, the round-1 fold
  `a07f901c`, and the head. The probe scripts are in the session scratch directory, not in the repository.

## Conclusion

**The thrashing is real, the cause is structural, and a redesign removes it. The redesign is not needed before the
merge.**

The cause is not quite the one proposed in the brief. It is this: **since Task 9, one guard answers "which slug does
this document name" twice, with two readers that use two grammars, and nothing written says which answer is the
rule.** The only standard any round used was "what master's regular expression did". Each fold moved the guard to a
different approximation of that expression, and each review round found the remainder.

**The observation that would make this conclusion wrong:** a finding on the redesigned guard (§3) of the form "reader
X and reader Y disagree about header H". If that appears, the next step is already chosen (§3, last paragraph) and
is not another patch.

## 1. The finding chain, per finding

| Round | Finding | The code that caused it | Caused by the previous fold? | Can a redesign remove it? |
|---|---|---|---|---|
| r1 MINOR-4 | `living_documents` keeps its own `ANCHOR_LINE` beside the strict reader | Task 9, `214a4fe7` | no (first round) | — (a duplication report, not a defect) |
| r2 Xm1 (Codex) | a bare `Anchor:` line now reads as no anchor | r1 fold `a07f901c`, `check-goal-status.py:224`: `"anchor": parse_header(text)[0],` | **partly.** The fold widened it; Task 9 introduced it (below) | yes |
| r3 F1 (Claude) | the same, plus the window: 10 lines instead of 18 | the same line. Round 2 changed no script (`git show --stat ae6ed876` lists none **[M]**) | **no — it is r2's finding found again**, labelled as induced by "the previous round's fix" | yes |
| r4 R4-F1 (Claude) | with two Anchor lines, the well-formed one beats an earlier bare one | r3 fold `bdaeff75`, `check-anchors.py:130`: `if anchor is None and lenient:` | yes | yes |

So the chain holds **two distinct defects, not three**. Both are mechanism defects by the method's one test: a
different shape dissolves them (§3). Neither is branch coverage.

**Task 9 already carried the defect, before any fold [M].** At `214a4fe7` the armed set came from the strict reader
(`:301`, `armed(ca.anchored_slugs(root))`) while each document's own slug still came from the lenient
`ANCHOR_LINE` (`:208`). A slug named only by a bare header was therefore never armed. Measured over 14 cases, the
count of inputs that master refuses and the version passes:

| Version | Master refuses, version passes |
|---|---|
| Task 9 `214a4fe7` | 7 of 14 |
| r1 fold `a07f901c` | 7 of 14 |
| head `635644df` | 2 of 14 |

The r1 fold did make one input worse: a bare-header document beside a well-formed sibling naming the same slug was
rc 1 at Task 9 and became rc 0 after the fold (master and the head: rc 1) **[M]**. So `fix_induced: true` on r2 is
defensible, and incomplete.

## 2. The structural cause, and what the evidence says about the brief's guess

The guess: one header reader serves two consumers with opposite strictness needs, and a `lenient` flag on one shared
parser makes every strictness fix leak into the other consumer.

| Part of the guess | Evidence | Verdict |
|---|---|---|
| The two consumers need opposite strictness | `check-anchors` asks "is this header well formed". The status guard asks "does this document claim a goal at all", and its failure mode is a silent pass, so it needs the wider reading | **supported** |
| The `lenient` flag is the mechanism | The flag did not exist until the r3 fold. The r2 and r3 findings predate it. It explains R4-F1 only | **refuted for 2 of the 3 rounds** |
| Fixes leak into the other consumer | Since the r1 fold, `check-anchors.py` changed only by an added branch behind `lenient` **[M]** (`git diff a07f901c..HEAD`); no caller in that file passes it; its own behaviour never changed in any round | **refuted.** The leak ran one way, once: the r1 fold imposed the strict grammar on the status guard |

What the evidence points to instead, in three parts:

1. **Two derivations of one relation.** `main` reads every document twice: `ca.anchored_slugs(root)` (strict, ten
   lines, includes ADRs) and `living_documents` (lenient, 18 lines). `with_document_anchors`
   (`check-goal-status.py:115-123`) then merges the two maps. A function whose only job is to reconcile two readings
   of the same files is the tell. The r3 fold needed both halves ("each half of the F1 fix cut in turn turns the F1
   case red"), and the second half exists only because there are two readings.
2. **No written rule, only an oracle.** Every finding in the chain is stated as "master rc 1, branch rc 0". The code
   says the same in five places ("master's arming rule": `check-anchors.py:78-81`, `:121`, `:342`;
   `check-goal-status.py:161`, `:409`). Under that oracle the only reader that cannot produce a finding is master's
   own regular expression, which the r1 fold deleted. After the merge "master's rule" names nothing.
3. **Two review goods collided.** r1 MINOR-4 asked for one reader (the duplication rule). The merge gate asks that
   nothing master refused passes. The reviewer offered a second option in the same finding — "record why two readers
   are intended, and add a case where the two must agree" — and the fold took the first.

The strict reader also takes the LAST matching line (the loop overwrites `anchor`, `check-anchors.py:123-125`, the
same on master) while master's status reader took the FIRST. Nobody chose either.

## 3. Can a redesign remove the class?

Yes. The smallest change that does:

1. **`check-anchors.py`: one pure tokenizer, `anchor_claims(text)`.** It returns every anchor-like claim in the first
   18 lines, in order, each with the slug and a `well_formed` mark (the line matches `ANCHOR` and sits in the first
   ten). `parse_header` loses the `lenient` flag and returns to master's signature.
2. **`check-goal-status.py`: the guard states its own rule, with no precedence in it.** *A spec or plan must declare
   a Status when ANY claim in its head names an armed slug.* The slug shown in messages and checked by
   `misnamed_anchors` is the well-formed claim when there is one, else the first.
3. **One reading.** The armed set is the union of the documents' own claims minus `UNARMED`. The
   `ca.anchored_slugs(root)` call and `with_document_anchors` are deleted.

Why this removes the class and does not move it: master's answer was the first match of its expression, and the
first match is always one of the claims. So "any claim is armed" contains master's rule by construction, whatever
the order of the lines. There is no first, last or fallback left for a later round to find wrong.

**Measured on a prototype of that rule (scratch only) [M]:**

| Variant | Master refuses, variant passes (of 14) | New refusal of a correct document |
|---|---|---|
| head `635644df` | 2 — a bare armed line then a well-formed exempt one; two well-formed lines, armed then exempt | none |
| backlog #731's "Do" (the lenient first match decides) | 0 | **1** — a sentence that mentions `**Anchor:** \`slug\`` above a correct header fails as "`slug` is not a node" |
| the prototype rule above | 0 | none |

The middle row matters: **folding backlog #731 as it is written would create the next fix-induced finding.**

On the live tree the change is invisible **[M]**: of 207 specs and plans, 67 carry a claim, 0 carry two, 0 carry a
claim that is not well formed; the armed set from one reading equals today's 13; no slug is named only by an ADR.

Cost **[I]**: about 30 lines across the two scripts; 3 mutation entries to rebind (`check-anchors.json:75`,
`check-goal-status.json:150` and `:164`); 3 self-test cases to reword.

**The observations that would show the redesign FAILED:**

- **A case that must go red.** A document with two Anchor lines naming different slugs, one armed and one exempt,
  and no Status, returns rc 0 in ANY order or form (bare then well-formed, well-formed then bare, two well-formed).
  At the head two of those orders return rc 0.
- **A property case.** The self-test keeps an independent literal copy of master's expression and a grid of headers
  (form: bare / blockquote without the ADR part / well-formed; line 3, 12 or 19; a second line naming another slug
  before or after). For every header where the literal's first match is an armed slug, `main` must return rc 1.
- **In review.** A later finding of the form "two readers disagree about a header" on this component. The next step
  is then pre-committed: give `check-goal-status` master's reader back verbatim as its own named function, with an
  agreement case against the strict reader over the corpus (r1 MINOR-4's second option). Do not add a case.

## 4. Is the redesign needed before this PR merges?

**No.** What master refuses and this branch lets through, in full, as far as I could construct **[M]**:

> a spec or plan with TWO Anchor lines in its head that name different slugs, where the line the branch prefers
> names `dev-speed` or `harness-ships-elsewhere` (the two exempt nodes) and the line master read first names an
> armed slug, and the document has no Status line.

- This is wider than backlog #731 says. Two WELL-FORMED lines, armed then exempt, also pass (master rc 1, branch
  rc 0); no bare line is needed.
- Exposure today is zero: no spec or plan has two Anchor claims in its first 18 lines.
- It needs a header that contradicts itself. A document cannot reach it by omission or by a typo.
- It is not a BLOCKER under §0 Q4c **[I]**: nothing false reaches a gate today and nothing is lost.

In the other direction the branch is stricter than master on 4 of the 14 cases: a node outside master's 13 is now
armed; a lenient slug that is no node now fails; two well-formed lines, exempt then armed, now fail; a head padded
with form feeds is read further. All four are refusals, and the live run is rc 0.

One of those is a refusal nobody decided: a document with no header whose opening prose mentions
`**Anchor:** \`slug\`` now fails with "`slug` is not a node" (master: rc 0). No document does this today.

**What the merge gate does with this is the gate's and the owner's call, not this review's.** The branch does carry
one latent loosening. If `check-merge-ready.py` holds on it, this section is the evidence for that decision.

## 5. What did this slice decide that is not written down?

1. **The arming rule itself.** The code calls it "master's arming rule" in five places. No document states it, and
   after the merge the phrase points at nothing. In words: a spec or plan is held to a Status when an anchor-like
   line in its first 18 lines names a node that is not exempt.
2. **"Armed" stopped being a property of an audited goal.** Q6 made it "every node a document names, minus two".
   The set is now redundant: a document is enforced exactly when its own slug is not in `UNARMED`. The docstring
   still says the opposite one sentence after saying this (`check-goal-status.py:71-73`: "an anchor joins the armed
   set when its threads have been audited"), and the warning still advises "Arm an anchor once its threads are
   audited" (`:290-291`), which no longer names an action anyone can take.
3. **"ONE header reader" is asserted in six places and is not true.** `gen-goals-page.py:109` and `:143` keep a
   character-identical copy of `ANCHOR` and their own `parse_header` (the same on master). With the `lenient` mode
   that is three implementations of two grammars.
4. **The status guard covers documents the goals page does not show.** The guard reads leniently; the page reads
   `anchored_slugs`, strictly. A document with a bare header must declare a Status that the page never renders. The
   guard's first line says "and the goals page renders it".
5. **A lenient claim is now judged as a name.** `misnamed_anchors` fails a slug found only by the lenient reader.
   G1 in the spec speaks of a declared header.
6. **Which of two Anchor lines wins.** The strict reader takes the last, the lenient search the first.
   `check-anchors` accepts a document that names two goals.
7. **An ADR can arm a slug.** `anchored_slugs` includes ADRs, and no ADR is ever checked for a Status. Harmless
   today: no slug is named only by an ADR.
8. **A re-found finding counts as fix-induced.** r3 F1 was r2's filed finding seen again; the round document marked
   it as caused by the previous round's fix, and the thrash detector counted it. The detector reached the right
   answer here, on two fix-induced defects out of two folds, but the label measured less than it claimed.

## 6. File as backlog

| # | Item | Fails if |
|---|---|---|
| B1 | **Rewrite backlog #731** as the §3 redesign: tokenizer, the "any claim" rule, one reading. Its current "Do" is measured to refuse a correct document | any order of two Anchor lines, one armed and one exempt, with no Status, returns rc 0; or the property case in §3 is absent |
| B2 | `check-anchors`: a head that names two different slugs is refused, in any date | such a document yields no finding from `audit` |
| B3 | `gen-goals-page.py` reads the header through `check-anchors` and drops its copy of `ANCHOR` | `git grep -c 'Anchor:\\\*\\\*' scripts/gen-goals-page.py` counts a regular expression |
| B4 | The `check-goal-status` docstring and warning say what arming now is (item 2 above); "master's arming rule" is replaced by the rule in words (item 1) | `git grep -n "master's arming rule" scripts` prints a line |
| B5 | Decide and record whether a bare-header document belongs on the goals page (item 4) | — a decision, not a gate; it is the owner's |

## Recommendation

MERGE-THEN-FILE

1. **Do not fold R4-F1 on this pull request, and do not fold backlog #731 as written anywhere.** Its "Do" trades the
   loosening for a new false refusal (§3, measured).
2. **Correct backlog #731 in this pull request's records** (a document edit, no code): the exposure is two Anchor
   lines of ANY form, not "a well-formed one beats an earlier bare one"; replace the "Do" with the §3 redesign and
   its three failure observations. File B2–B5 beside it, and add them to the roadmap in the same turn.
3. **State the one latent loosening in the merge record**, in the words of §4, so that a HOLD for "loosens a gate"
   is answered with the measured input and its zero exposure. Whether that is enough to release a HOLD is the
   owner's decision.
4. **Finish what the gate still owes that this review does not replace:** the Codex pass that re-clears the 12 ids
   Codex answered as findings, and the CI sweeps not run locally.
5. **Build the redesign as its own small pull request after the merge**, test-first on the two red cases of §3. If
   that pull request draws a "two readers disagree" finding, take the pre-committed step in §3 and stop.
