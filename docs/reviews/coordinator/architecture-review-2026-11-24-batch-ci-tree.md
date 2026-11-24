# Phase 6 architecture review — `batch-ci`: how the node tree file is merged in a batch

- **Subject:** component `batch-ci` of the subject `goal-node-tree-plan` — Task 16 and choice C7 of the plan
  `docs/superpowers/plans/2026-11-24-goal-node-tree.md` (PR #630, branch `goal-node-tree-plan`).
- **Armed by THRASHING.** `check-merge-ready.py --pr 630`: the component carried fix-induced findings in both
  r2 and r3.
- **Read first:** `CONTEXT.md`; `docs/adr/` (ADR-0010 and ADR-0016 in particular — nothing here re-opens an
  ADR); `docs/review-method.md` → *The stop condition*, *Can a redesign remove it?* and *The arming condition —
  full account*; the r1–r3 halves and coordinator documents of `goal-node-tree-plan`; `scripts/batch-ci.py`
  (`UNION_FILES`, `SECTION`, `resolve_hunk`, `resolve_text`, `_homes`, `postcondition`, `merge_into`,
  `_union_violation`, `_selector`); `scripts/mutations/batch-ci.json`; `scripts/check-features.py`
  (`parse_features`); the earlier review of this same component,
  `docs/reviews/architecture-review-2026-11-07-batch-ci-docs-union.md`.
- **Changed by this review:** the plan's Task 16, choice C7, Review Focus item 4 and one File map row. The
  spec is untouched, and no ESCALATE is raised (§4).
- **Tagging:** **[M]** = measured here, by reading the named symbol or running the named command.
  **[I]** = inferred; a judgement or a prediction.
- **Baseline:** HEAD `76326606`; `origin/master` at `2ea4a5e8`.

---

## Recommendation

**REDESIGN Task 16's judge; keep its resolver.** `docs/features.md` stays a union file under a policy named
`tree`, resolved exactly as `blocks`. What changes is how the merged file is JUDGED: not by a second reader
of headings inside `scripts/batch-ci.py`, but by asking the tree's one parser, `parse_features`, what each of
the four texts means, and requiring

> **P8: the merged tree is the three-way merge of the three trees, attribute by attribute.**

This is option (c) of the brief, made exact. It leaves no copy of the node grammar outside
`scripts/check-features.py`, and it is the same principle the 2026-11-07 review of this component set down:
the resolver only proposes, and the output is checked against a definition that does not depend on how it was
produced. For a tree file, that definition is the parsed tree.

---

## 1. Is the thrashing real? Per-finding evidence

| Round | Finding | Caused by the previous fold? | Can a redesign remove it? | Kind |
|---|---|---|---|---|
| r1 | Codex: the plan claimed outcomes `blocks` does not give (an in-hunk edit surviving, an identical addition landing once) | no — first draft | no; it was a wrong sentence about existing code | editorial |
| r1 | Codex: the entry-removed mutation named no case that reaches `resolve_text`'s path lookup | no | no; any design that adds a `UNION_FILES` entry needs that case | branch coverage |
| r2 | Codex Major: `blocks` unchanged cannot protect the hierarchy — `SECTION` is `^#{1,2} `, so a clean merge re-parents `####` nodes with P4 green | **yes** — the r1 fold adopted `blocks` as it is | **yes** — a judge that reads the file through its own parser has no depth to be blind to | **mechanism** |
| r3 | Claude Low F1: a clause-only assertion lets the both-sides mutation live | **yes** — P8 was new in the r2 fold | no; any three-way rule has two refusal messages, and the case must assert which | branch coverage |
| r3 | Claude Low F2: "every new case is red" is false for the `[]` controls | **yes** | no; today's `postcondition` reads any unknown policy as `blocks`, under every design | editorial |
| r3 | Claude Low F3: the `the policies: …` label is a mutation's `expect` | **yes** | no; it lives in the existing manifest | editorial |

**[M]** The counter is right: r2 and r3 each carry findings the previous fold caused, in this one component
(`fix_induced: true` in both coordinator headers, and each re-derived above against the code).

**[M]** But the two rounds are different kinds. r2 is a mechanism defect. r3 is three Low findings that no
reshaping dissolves; r3's verdict was CONVERGED. By the method's one test, r3 alone is the prose floor.

**[I] The verdict: real thrashing, of a shape the round findings did not name.** The severity trajectory
(Major → Major → three Low) says "converging", and on the plan's text it was. What the rounds could not see,
because each asks only *is this correct?*, is what the r2 fix BUILT: a second reader of the node grammar. The
fix put `NODE_HEADING = ^#{1,6} ` and a parent rule ("nearest preceding heading with fewer `#`") inside
`scripts/batch-ci.py`, while Task 1 of the same plan defines a node's parent in `parse_features` — with a
trunk that is a node only when it carries a `slug:` line, and a skipped level refused. Two definitions of
"parent", in two scripts, of one file. Every later change to the grammar would owe an edit in both, and
nothing would say so. The r3 findings were the first instalment: three corrections to the test plan of a
mechanism that should not exist.

This component has been here before. `docs/reviews/architecture-review-2026-11-07-batch-ci-docs-union.md`
was convened on thrashing in the same union code, and its conclusion is in `postcondition`'s docstring: check
the OUTPUT against definitions independent of how it was produced. The r2 fold kept the letter of that (a
postcondition clause) and missed its point (the definition of a tree is not a heading regex).

## 2. The four designs

Measured for option (b) **[M]**, with `git log origin/master --name-only`:

| File | Touched by, of the last 80 commits | Of the last 300 |
|---|---|---|
| `docs/backlog.md` | 66 | 249 |
| `docs/dashboard-entries.md` | 63 | 264 |
| `docs/goal-threads.md` | 15 | 53 |
| `docs/features.md` | 4 | 7 |
| `docs/anchors.md` (folds into the tree in S2) | 2 | 4 |

Commits that added or changed a `## GOAL` heading in `docs/goal-threads.md`, whole history: 7. The seven
commits touching `docs/features.md` landed on seven different days (09-20, 10-27, 10-28, 11-09, 11-11, 11-14,
11-20). So after the fold, names land in the tree file in roughly 6 of 80 commits. **Not measured:** how
often two OPEN pull requests both touched it — that needs GitHub's open and merge times, which this review
did not read. The table is an upper bound on the rate, not the overlap itself.

| Design | Removes | Costs | Second copy of the grammar? |
|---|---|---|---|
| (a) `tree` as planned after r3: `NODE_HEADING`, `_parents`, P4 homes at any level, P8 on headings | the r2 blind spot | two definitions of "parent"; 7 mutations on a private reader; drifts at the next grammar change | **yes** |
| (b) no union for `docs/features.md`: a conflict ejects | Task 16 entirely, and with it every finding | an ejected pull request runs alone, at a rate bounded by ~6 in 80; **and a CLEAN merge that re-parents a node is then judged by nothing** — `_union_violation` reads only `UNION_FILES`, and behaviour 8 is a clean merge | no |
| (c) union as `blocks`, judged by `parse_features` (P8 as above) | the r2 blind spot, the second reader, P4's any-level home, `_parents` | one lazy load of a sibling script (the `_selector` pattern, already in the file); two small pure functions | **no** |
| (d) teach the resolver the tree, so it never proposes a re-parenting | nothing P8 does not | a tree-aware resolver is a second WRITER of the grammar; and git's clean merges bypass any resolver | yes |

**(d) is rejected** on the 2026-11-07 finding itself: a clean merge never reaches a resolver.

**(b) is the cheapest and is not chosen, for two reasons.** First, it is the one option that changes the
approved spec, whose S3 row says "`batch-ci.py` gains a conflict resolver for `docs/features.md`, where new
names now land". Second, and independent of the spec: taking the file out of the union does not make a batch
safer, it makes it blind. Behaviour 8 — one branch inserts a `###`, another appends a `####` below it, git
merges cleanly and the new node hangs under the wrong parent — passes every gate that exists, because the
result is a valid tree. Only a three-way comparison can see it, and the union's postcondition is the only
place this repository runs one. **[M]** (§5, row 8: `git merge-file` exit 0, the text-level postcondition
`[]`, P8 names the node.)

**[I] One thing for the owner to know, not to decide now.** The spec's reason for the resolver — "where new
names now land" — was not measured when written, and the table above says the file is edited an order of
magnitude less often than any file now in `UNION_FILES` (the comment above it justifies the four entries by
counts of 34 to 73 in 80). The resolver half of Task 16 will rarely fire. The judge half is what earns the
entry. If the owner later prefers no resolver, the cheap form is the entry kept and the `tree` arm of
`resolve_hunk` made to `Refuse` — P8 would still judge clean merges. That is a spec edit and is not made here.

## 3. The chosen design, exactly

- `UNION_FILES["docs/features.md"] = "tree"`. `resolve_hunk` sends `tree` down the `blocks` arm.
- `postcondition(…, "tree")` = every `blocks` clause unchanged (P4 keeps `SECTION`; at the text level the
  trunks are the sections) + P8.
- P8 parses base, ours, theirs and result with `parse_features` and flattens each to
  `{(slug, attribute): value}` over every `Node` attribute but `line`. For every key, a three-way merge: both
  sides changed it differently → refused; else the result must hold the changed side's value. A result the
  parser reports a problem in is refused outright.
- `parent` is one attribute among the others. Re-parenting, a field line under another node, a lost field and
  a doubled node are one comparison, where the r2 design had two clauses and two readers.
- The parser failing to load is `CannotRun`.

**What it deliberately does not judge:** sibling order and field order (no attribute holds them); text before
the first node (the `blocks` clauses do). **What costs an ejection:** a pull request that extends the grammar
before the grammar has merged; a future position-like attribute not excluded beside `line`. Both fail loudly
and in the safe direction.

**Can a redesign remove the r3 findings?** No, and that is the evidence they were the floor: F1's lesson
(assert the reason), F2's (name the controls that are green before the implementation) and F3's (keep the
label) are all carried into the rewritten task, because they hold under (c) too.

## 4. Why this is not an ESCALATE

The spec names no policy and no judge; C7 records that. The S3 row asks for "a conflict resolver for
`docs/features.md`", and (c) delivers one. No spec sentence, guard (G1–G9) or slice boundary moves. Task 16
already consumed S1's parser by order (S1 merges before S3); it now also consumes `Node.parent` from Task 1.

## 5. What was measured for the design

A stand-in for P8 (today's `parse_features`, plus a parent derived from heading levels in place of Task 1's
`Node.parent`, plus the per-attribute merge) was run in a scratch directory over real `git merge-file`
results and the real `resolve_text`. `anchors:` stood in for `adrs:`, which today's parser does not have.
**[M]**

| Plan behaviour | git | text-level postcondition (`blocks`) | P8 stand-in |
|---|---|---|---|
| 1 two added nodes, one parent | conflict, resolved | `[]` | `[]` |
| 6 two sides edit different fields of one node | clean | `[]` | `[]` |
| 8 a clean merge re-parents `a3` | clean | `[]` — **the r2 blind spot** | names `a3.parent`: `B`, the sides make it `A` |
| 8 control | clean | `[]` | `[]` |
| 9 a union that re-parents `a2` | conflict, resolved | `[]` | names `a2.parent` |
| 9 reversed | conflict, resolved | `[]` | `[]` |
| 10 one side re-parents on purpose | clean | `[]` | `[]` |
| 11 both sides re-parent `a1` | conflict; result built by hand | `[]` | both sides changed `a1.parent` |
| 12 a field line under another node | conflict, resolved | `[]` | names `a1.anchors` and `o.anchors` |

Not run: behaviours 13 and 14 (they need the P8 code itself), and anything through Task 1's real
`Node.parent` — the stand-in's parent rule ignores trunk slugs. The builder's cases are the gate.

**Sweep selection follows the new dependency. [M]** `select_manifests("pull_request",
["scripts/check-features.py"], …)` from `scripts/check-plan-code.py` does not select `scripts/batch-ci.py`
today (21 targets), and does once `batch-ci.py`'s source holds `FEATURES_PARSER = "check-features.py"` (24).
So a change to the parser sweeps this script's mutations on its own pull request.

## 6. What changed in the plan

| Where | Change |
|---|---|
| Task 16, title and Files | "judged by the tree's own parser"; produces `FEATURES_PARSER`, `_features`, `_tree_map`, `_merge3`; `NODE_HEADING` and `_parents` are gone |
| Task 16, the policy | P4 keeps `SECTION` for `tree`; P8 is redefined as the per-attribute three-way merge of parsed trees; bounds stated |
| Task 16, behaviours | 6 was "the result parses" (now inside P8 step 1) and is "two fields of one node, edited one per side"; 8, 9, 11, 12 name attributes; 13 (a result the parser refuses) and 14 (the parser cannot load) are new |
| Task 16, Step 1 | `tree P4: a field line keeps its node heading` → `tree P8: a field line keeps its node`; `features union: the result parses as a tree` → `features union: edits of two fields of one node both survive`; two new cases; cases reach P8 through `postcondition` with the real parser |
| Task 16, Step 2 | three cases named green before Step 3, and the `[]` second inputs of 8, 9, 13 |
| Task 16, Step 5 | nine mutations, each with its `expect`; the two on the private heading reader are gone |
| C7 | restated; names this review as where the r2 form was withdrawn |
| Review Focus 4, File map | the renamed case; "no heading reader of its own" |

## 7. What did we decide that is not written down?

One thing, now written in §2: **a union entry in `batch-ci.py` buys two things — a resolver and a judge — and
they have different worth per file.** For the four existing entries the resolver earns the entry (the files
conflict constantly). For the tree file the judge does. The comment above `UNION_FILES` argues only from
conflict counts; Task 16's Step 3 extends that comment with the `tree` policy, and should say this.
