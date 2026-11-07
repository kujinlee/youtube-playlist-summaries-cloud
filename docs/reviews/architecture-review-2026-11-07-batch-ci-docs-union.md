Reviewed head: 7df960aa (branch `batch-ci`, PR #529, backlog #534)

> **For the r4 fold of `batch-ci`.** This review was triggered by **THRASHING**, by the letter of
> `docs/dev-process.md` → *Phases*: three consecutive rounds found defects in ONE component, the docs union in
> `scripts/batch-ci.py`, and each round's finding came from the previous round's fix to it.
>
> **Verdict:** yes, a redesign removes the class. The defect class is *a placement decided per conflict hunk and
> validated per conflict hunk*. A hunk is git's artefact, while correctness is a property of the whole file. **R3-F1
> is not even a resolver bug.** Git merges the heading insertion cleanly, and the repro below shows git misplacing
> a line with no conflict at all. No hunk-level check can see that.
> **Recommendation:** option (a). Run ONE whole-file postcondition (§4) on every union file that both sides changed,
> after every merge step, clean or conflicted. On any violation, EJECT the member. Delete `_moved`/`_sections`
> (the hunk-level validation it replaces). Keep the resolvers. Do not patch their hunk logic a fourth time.
> **Measured cost:** on 437 replayed member pairs from the last 200 master commits, the postcondition false-ejected
> **0**. Its one ejection was a real defect, found by this review: the `rows` policy re-sorts base rows.
> **No BLOCKER.** R3-F3 is outside this component. It is a separate fold item (§7).

# Phase 6 architecture review (narrow, triggered by thrashing): the docs union in `batch-ci` (PR #529, backlog #534)

**Scope:** `scripts/batch-ci.py`, from `merge_into` through `_moved`. That is `UNION_FILES`, `parse_conflicts`, `_rows`,
`_added`, `resolve_hunk`, `_tagged`, `_sections`, `_moved`, `_blocks`, `_trim`, `resolve_text` and `merge_into`.

**How:** read only. `CONTEXT.md` and `docs/adr/` were read, and no ADR governs batch assembly or the union. Every
experiment ran on a scratch copy (`git archive HEAD | tar -x`) or in throwaway git repositories. Nothing in the
worktree was touched except this file, and GitHub was not contacted. The probe scripts are outside the repository, in
`/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/f7c144b8-1b6c-4db3-8ef1-932d4e701b12/scratchpad/arch/bin/`:
- `repro.py` and `repro_clean.py`: the five findings' shapes through the scratch copy's real `merge_into`.
- `pc.py`: a prototype of the §4 postcondition.
- `shapes2.py`: the shape of each master change.
- `replay*.py`: replays pairs of master commits as two members.

**Self-test at 7df960aa (scratch copy):** `batch-ci.py --self-test` 145/145. `scripts/mutations/batch-ci.json` has 83
entries.

## 1. The thrashing evidence

| Round | Finding | What the previous fix did | How this finding follows from it | Shape |
|---|---|---|---|---|
| r1 | R1-F2 / C4 (High): a per-line dedupe fused two same-day dashboard entries | (r0's `lines` policy) | — | the original defect |
| r2 | R2-F1 (High): a headless addition is reattached under the OTHER side's new `## ` section | r1 (`f9fd9c40`) split additions into blocks at `## ` headings and appended theirs' blocks after ours | It was fixed only for additions that START with a heading. The r2 coordinator marks it "the fix left incomplete" | residual of r1's fix |
| r3 | R3-F1 (High): per-hunk validation cannot see a heading that git inserted CLEANLY outside the hunk | r2 (`a1bdd0ca`) added a headless-prefix placement plus `_moved`, a section check over the conflict hunk only | The check's scope (one hunk) is r2's own design | **patch-on-patch** |
| r3 | R3-F2 (Medium): theirs' base-line preservation check (`_added(theirs, base, "theirs")`) is gone | r2 rewrote the `blocks` branch around `_tagged` and dropped the call | Deleted by r2's own rewrite | **patch-on-patch** |

Two consecutive rounds (r2→r3) carry findings caused by the previous round's fix, in one component. That is the
arming condition. Every finding is a code defect with a run reproduction, not a prose floor.

**The repros, re-run at 7df960aa through the real `merge_into` and real git (`repro.py`):**
- **R3-F1, Codex's literal shape.** `merge_into` returns `None`, and the result reads
  `## GOAL billing / > breq / - existing / - A product thread / - B billing thread`. A's product thread is filed under
  billing.
- **R3-F2.** `merge_into` returns `None`, and the result reads `- original / - A addition / - replaced by B`. B's
  replacement of `- original` is silently undone.
- **R3-F1-CLEAN, new in this review (`repro_clean.py`).**
  - Setup: B inserts `## GOAL billing` in the MIDDLE of the product section, far from the end of the file. A appends
    a product thread at the end of the file.
  - Git reports **no conflict**: `merge --no-commit` exits 0, and `merge_into` returns at its first line
    (`if r.returncode == 0: return None`). A's product thread lands under billing.
  - **This proves the class is not in the resolver.** No change to `resolve_hunk` can reach it. The check must
    read whole files, and it must run on the clean path too.

## 2. What the real files look like (measured)

`shapes2.py` classified each first-parent `origin/master` commit's change by git's own `-U0` hunks. The window is the
last 200 commits, from 1bbb2fe2 (2026-09-18) to 8c5f75a7.

| File | Commits touching it | Hunk shapes |
|---|---|---|
| `docs/backlog.md` | 164 | **row edits in place: 337 hunks, in 107 commits (65%)**. Appends at the end of the Items table: 110. Inserts mid-section: 20. Replace: 1 |
| `docs/dashboard-entries.md` | 181 | **appends at end of file: 171 hunks; 169 commits (93%) are pure appends at end of file.** A whole entry inserted between entries: 11. Replace: 2 |
| `docs/goal-threads.md` | 36 | **inserts mid-section: 21** (a thread or a `>` request inside a goal). Replace: 12 (a thread line edited, e.g. a PR number added). Appends at end of a section: 10. Appends at end of file: 8 |
| `decision-log.jsonl` | 89 | appends at end of file: 84. Inserts mid-file: 9. Delete: 1 |

So `goal-threads.md` is **not** append-only: 8 of its 36 commits edit a thread in place. That is R3-F2's shape (an
edit of a line next to the other member's append), and it is ordinary here. In `backlog.md`, in-place row edits are
the majority operation.

## 3. Options, with their cost in ejections (measured)

**The replay (`replay.py`, `replay_cls.py`, `replay_naive.py`).**
- Take two consecutive master commits A and B that touch a union file. Rebuild them as two SIBLING members of one
  base: base = `f@A^`, ours = `f@A`, and theirs = B's own change (A→B) transplanted onto base by the base lines around
  it.
- Merge with `git merge-file --diff3`. On a conflict, resolve with HEAD's `resolve_text`. Then score each option.
- `truth` is `f@B`, which is what master actually did.

437 pairs were replayed. 29 more were skipped because B edited lines A had added, which cannot be modelled as two
siblings.

| File | Pairs | Git-clean | Conflicted | HEAD's result differs from truth |
|---|---|---|---|---|
| backlog | 138 | 41 | 97 | 1, **order**: the `rows` policy re-sorted base rows (§6, a real defect) |
| dashboard | 180 | 14 | 166 | 26 blank lines only; 7 order only (ours first versus master's landing order); **0 content** |
| decision log | 87 | 5 | 82 | 6 order only; 0 content |
| goal-threads | 32 | 16 | 16 | 1 blank lines only; 6 order only; 0 content; 2 refused by HEAD |

**Bound of this measurement.** The pairs are master's real changes, but their pairing as siblings is synthetic. A
transplant can place B's line differently from where its author put it: on 7 pairs, `truth` itself fails the
postcondition, and those are the pairs whose landing order interleaves the two members. The replay measures the
**shapes** that occur. It does not measure how often two such shapes are in one batch. Under (c) that is almost
always, because 93% of PRs append a dashboard entry.

| Option | What it would have caught: R1-F2 / R2-F1 / R3-F1 / R3-F2 | Ejections on the 361 conflicted pairs (and on the 76 clean ones) | Complexity |
|---|---|---|---|
| **(a) whole-file postcondition, eject on failure** (resolvers kept) | **all four**, run on the defective outputs: R1-F2 by P1, R2-F1 by P4, R3-F1 by P4 (the clean variant too), R3-F2 by P3 | **3 / 361 (0.8%)**: the 1 backlog reorder (a TRUE defect, correctly ejected) and HEAD's own 2 goal-thread refusals. **0 false ejections**, including on the 76 clean merges | about 70 lines plus one call site. It REPLACES `_moved` and `_sections`. Independent of every resolver |
| (b) union only pure appends at end of section; eject anything else (whole-file shape) | R3-F1 and R3-F2, by refusing the input shape. **Not** R1-F2 or R2-F1: both are pure appends that the RESOLVER misplaced, so (b) still needs a correct resolver and has no check on it | **97 / 361 (27%)**: backlog 82/97 (in-place row edits); goal-threads 9/16 (56%); decision log 4/82; dashboard 2/166 | small, but it keeps the resolver and so keeps the risk |
| (c) dashboard and goal-threads refuse any non-trivial merge | R3-F1 and R3-F2 (the merge refuses); R1-F2 and R2-F1 never resolve | **182 of the 212 pairs** in those two files (every conflicted one). 166/180 dashboard pairs conflict. In a batch, members 2..k all append a dashboard entry, so **each batch lands one member**: the outcome the r2 coordinator rejected | trivial, and it defeats the batch |
| (d1) (a) plus deleting the `blocks` placement logic: per conflict hunk, ours verbatim, then theirs' non-base lines verbatim | same as (a): the postcondition is the safety | blocks files: **3 / 182** (dashboard 1, goal-threads 2); HEAD's resolver ejects 2 (its refusals). The naive union RESOLVES both of those and ejects 3 others, all among the 7 pairs whose own truth fails the postcondition | deletes `_tagged`, `_blocks`, `_trim`, the R2-F1 prefix placement and the identical-block dedupe (about 45 lines) |
| (d2) a structural, section-keyed merge (parse B, O and T into sections and merge per section) | all four, if written correctly | not built | it is **a fourth resolver**, and its own placement bugs would ship as wrong trees unless (a) checks it. So it reduces to (a) plus a resolver |

**Why (a) and not (b) or (c):**
- (b) and (c) restrict INPUTS, so a resolver bug still writes a wrong tree. They catch R3-F1 and R3-F2 only because
  those inputs are unusual. R1-F2 and R2-F1 had ordinary inputs and a wrong resolver.
- (a) checks the OUTPUT against definitions that do not depend on how it was produced. A resolver defect can then only
  cost an ejection, which is the property asked for.
- (a) is also the only option that sees R3-F1-CLEAN, where git, not the resolver, did the damage.

## 4. THE POSTCONDITION, specified for test-first

`postcondition(base: str, ours: str, theirs: str, result: str, policy: str) -> list[str]`. It is PURE. It returns the
violations, each starting with its clause id, and `[]` means it holds. `pc.py` is a PROTOTYPE of P1–P4, P6 and P7. It
has no `policy` argument (it applies P6 everywhere) and no call site. It was run on §5 cases 1–14, each with the
stated result; case 14 took 0.03 s. It is evidence for the rule, not code to copy.

### 4.1 Where it runs (the call site; this part is not optional)

In `merge_into`, after `git merge --no-commit` and after the union resolution, and **on the clean path too**:
- `git merge-base --all HEAD <sha>` must print exactly ONE commit. If it prints several, and some `UNION_FILES` file
  differs from HEAD on both sides, REFUSE with "several merge bases". A virtual base cannot be read back with
  `git show`.
- For each `f` in `UNION_FILES`: B = `git show <mb>:f`, O = `git show HEAD:f`, T = `git show <sha>:f`, and R = the
  worktree file. A side where `f` is missing is the empty text.
- Skip `f` when O == B or T == B. Then git takes the other side whole, and nothing was merged.
- Otherwise, a non-empty `postcondition(...)` → `git merge --abort` and return
  `f"{f}: {violations[0]}"`. The member is EJECTED, exactly like an unresolvable conflict.
- `clean_only` still refuses any conflict first. The postcondition runs only when the merge would otherwise be
  accepted.

### 4.2 Definitions

- A line is a `"\n"`-split element. A line is **blank** iff `x.strip() == ""`. `NB(F)` = F's non-blank lines, in
  order, text exact. **Blank lines are outside every clause** (§6, bound 1).
- A **heading** is a line matching the existing `SECTION` (`^#{1,2} `).
- **Prefix cut** (part of the definition; it is there so the 18,918-line dashboard stays fast):
  - Let n be the length of the longest common prefix of NB(B), NB(O), NB(T) and NB(R).
  - Let c be the index of the last heading among the first n lines of NB(B), or 0 if there is none.
  - Drop the first c lines of all four lists.
  - This is sound because each dropped line is identical in all four, so it is a base line both sides kept, present
    and under the same heading. The heading at c stays in all four as the shared context.
  - **Measured:** without the cut, `difflib` over the full dashboard did not finish in 5 minutes. With it, 437×3
    calls plus the git work took 231 s.
- `match(X, Y)` = the monotone partial map X-index → Y-index, from
  `difflib.SequenceMatcher(None, X, Y, autojunk=False).get_matching_blocks()`. This exact algorithm is part of the
  rule, so cases are deterministic.
- **Identities.**
  - For S ∈ {O, T}, `mS = match(NB(S), NB(B))`. Line j of S has identity `("b", mS[j])` if j ∈ mS (a base line S
    kept), else `(S, j)` (a line S added).
  - `KEPT_S` = the image of mS.
  - A base line i has identity `("b", i)`.
- **Home.** `home_F(k)` = the identity of the nearest heading at or before line k of F, or `None` if there is none.
  B's lines use base identities, and S's lines use S's identities.
- **Attribution of R.**
  - `mRO = match(NB(R), NB(O))`. R line r gets O's identity of line mRO[r].
  - `REST` = the R indices not in mRO, in order.
  - `TADD` = the T indices whose identity is `(T, j)`, in order.

### 4.3 Clauses (each is one failing message; all are checked, and all are reported)

- **P1 — theirs' additions, exactly once, in theirs' order, and nothing else.**
  `[NB(R)[r] for r in REST] == [NB(T)[j] for j in TADD]`. When it holds, REST[k] gets identity `(T, TADD[k])`.
  - A violation is either a line of theirs that is missing or out of order, or "a line from no side": a duplicate,
    an invented line, a base line that ours deleted, or a reordered base line.
- **P2 — ours' additions, exactly once.** Every j with identity `(O, j)` is in the image of mRO.
- **P3 — base lines.** For each base i, `("b", i)` is among R's identities **iff** i ∈ KEPT_O ∩ KEPT_T.
  - A base line one side deleted or replaced must be absent. That is **R3-F2**.
  - A base line both sides kept must be present.
- **P4 — every line stays in its section.** For each R line r with identity id:
  - `(O, j)`: the expected home is `home_O(j)`.
  - `(T, j)`: the expected home is `home_T(j)`.
  - `("b", i)`: let h0 = `home_B(i)`, and let hO and hT be its homes in O and T.
    - If both hO ≠ h0 and hT ≠ h0, both sides re-sectioned it: VIOLATION.
    - Otherwise the expected home is whichever of hO and hT differs from h0, or h0 if neither does. A side that
      inserts a heading above existing lines moves them, and the result must honour that move.
  - Then require `home_R(r) ==` the expected home, comparing identities, not heading text. That is **R2-F1, R3-F1
    and R3-F1-CLEAN**.
  - Identities, not text, are what separate two same-date dashboard headings (**R1-F2**).
- **P6 — `rows` files only: no backlog row number twice.** Over R's lines matching `ROW`, every number appears at most
  once.
  - P1–P3 alone pass when two members both file `| 545 |` and both rows land. Measured with `pc.py` before P6
    existed: HOLDS.
- **P7 — no base line changed on both sides.** A base i in neither KEPT_O nor KEPT_T is a VIOLATION. Both sides
  edited or deleted the same line, and a union cannot decide that. `rows` already refuses this per row. P7 makes it
  independent of the resolver.

(P5 is deliberately left unassigned. See §6, bound 1.)

**What "holds" certifies:**
- R's non-blank lines are exactly the base lines both kept, plus every line each side added, once each.
- Ours' lines are in ours' order, and theirs' additions are in theirs' order.
- Every line sits under the very heading instance it sits under in the side it came from.
- No backlog number is duplicated, and no line was edited on both sides.

**Why it cannot pass a wrong tree:**
- The clauses are checked under one explicit attribution. If that attribution satisfies all of them, R IS a valid
  merge by this definition.
- If the alignment picks a poor match among duplicate texts, the clauses fail, and the cost is an EJECTION, never a
  pass.
- The prototype measured 0 such false ejections on the replay. 7 appear only on `truth` orderings that interleave the
  two members, which no resolver here produces.

## 5. The cases that must exist (write them first; each must be red on HEAD's postcondition-free code)

**Pure cases, on `postcondition(base, ours, theirs, result, policy)`:**

| # | Case | Expect |
|---|---|---|
| 1 | **R3-F2.** base `## GOAL product / - fix · PR #1 · original`; ours appends `- fix · PR #2 · A addition`; theirs replaces line 2 with `- fix · PR #1 · replaced by B`; result = HEAD's output `original / A addition / replaced by B` | `P3` naming `original` |
| 2 | **R3-F1 (Codex's literal shape).** base `# T / ## GOAL product / > req / - fix · PR #1 · existing`; ours appends `- fix · PR #2 · A product thread`; theirs inserts `## GOAL billing / > breq` before `existing` and appends `- fix · PR #3 · B billing thread`; result = HEAD's output | `P4` naming `A product thread` |
| 3 | **R2-F1, the r1-era output** (theirs' product thread after ours' new `## GOAL billing`) | `P4` |
| 4 | **R1-F2, the fused output** (the second `## 2026-11-06` and its `<!--tech-->` lost) | `P1` (and P4) |
| 5 | **The correct outputs for 1–4** (two separate same-date entries; the product thread under product; and so on) | `[]` |
| 6 | **R3-F1 with the new goal ABOVE an existing goal** (`## GOAL billing` inserted directly before `## GOAL product`, so no base line changes section) | `[]`, so that a new goal between goals is not ejected |
| 7 | **The rows reorder.** base `| 5 |`, `| 1 |`; ours ticks 5; theirs appends `| 9 |`; result = HEAD's `rows` output `1, 5✅, 9` | `P1` and `P2`, so the reorder is ejected |
| 8 | Two members each add a DIFFERENT `| 3 |`, and both land | `P6` |
| 9 | One row edited differently on both sides, and both versions land | `P6` and `P7` |
| 10 | The same added line on both sides, landed once | `P1` (stated bound 3) |
| 11 | Theirs' two additions landed in reverse order | `P1` |
| 12 | A base line both kept is missing; an added line of ours is missing | `P3`; `P2` |
| 13 | A base line re-sectioned by ONE side (it inserts a heading above it), with the result honouring it | `[]` |
| 14 | The prefix cut: an input of 20,000 identical leading lines plus a case-2 tail | same verdict as case 2 (`P4`); measured 0.03 s with the prototype |

**Real-git cases, through `merge_into` (extend `_e2e_union`):**

| # | Case | Expect |
|---|---|---|
| 15 | **R3-F1-CLEAN.** base `## GOAL product / > req / - one / - two / - three / - four`; theirs inserts `## GOAL billing / > breq` after `- one`; ours appends `- fix · PR #2 · A product thread`. Git merges with NO conflict | a refusal naming `docs/goal-threads.md` and `P4`; `git status` clean afterwards (the merge aborted) |
| 16 | Case 2 through real git (one conflict hunk; the heading merged cleanly) | refusal, `P4` |
| 17 | Case 1 through real git | refusal, `P3` |
| 18 | Two same-day dashboard entries (the existing R1-F2 e2e) | `None`, both entries whole |
| 19 | Several merge bases (a criss-cross built in the fixture) with a union file changed on both sides | refusal, "several merge bases" |
| 20 | A union file changed on ONE side only | `None`, and the postcondition is not called (the skip) |

**Mutations to add to `scripts/mutations/batch-ci.json`:**
- the call site's clean-path return restored, which must turn case 15 red;
- the call replaced by `[]`, which must turn cases 15–17 red;
- each of P1, P2, P3, P4, P6 and P7 deleted, each red on its own case above;
- the prefix cut's `c` set to `n`, which must turn case 2 or 14 red. Cutting past the last shared heading loses the
  section context.

**Retire:**
- `_moved` and `_sections`, whose hunk-level validation the postcondition replaces;
- the two manifest entries that mutate `_moved`'s call (`batch-ci.json` around line 882);
- the R3-F2 suggestion "restore `_added(theirs, …)`". P3 covers it from outside the resolver, so do not restore the
  hunk check.

## 6. Bounds: what the postcondition does not see (stated, not hidden)

1. **Blank lines.** The replay found HEAD adding blank lines that differ from master's: 26 dashboard pairs and 1
   goal-threads pair, where one blank line landed inside a goal. Both grammars accept these. A clause like "a heading
   preceded by a blank line in its side is preceded by one in the result" (the would-be P5) is **not measured** and
   is filed, not built.
2. **Order within a section.** Ours' lines and theirs' additions may interleave in a section. `goal-tree.py`
   `parse_threads` collects requests and threads irrespective of position, so this costs nothing there.
3. **An identical addition on both sides is EJECTED** (case 10). It occurs when a stacked PR still carries a parent
   that has already landed. Its fix is a rebase, and the next batch takes it. No such pair occurred in the replay.
4. **The `rows` policy re-sorts base rows (a real defect, found by this review).** `resolve_hunk("rows")` emits
   `sorted(set(o) | set(b) | set(t))`. `origin/master`'s `backlog.md` has **8 adjacent row-number inversions**
   (31→18, 18→6, 7→5, 5→1, 4→2, 15→14, 16→12, 545→9). So a conflict hunk spanning them is silently reordered at HEAD.
   - Reproduced: `resolve_hunk("rows", [r5✅, r1], [r5, r1], [r5, r1, r9])` returns `[r1, r5✅, r9]`. The replay hit
     it on master pair ffb3aa8b/a34f8924.
   - With the postcondition in place this becomes an EJECTION (case 7). Emitting rows in ours' order would make it
     resolve instead. That fix is filed.
5. **The attribution is one fixed alignment.** Among duplicate texts, a poor match costs an ejection, never a pass
   (§4).

## 7. What is built in the r4 fold, and what is filed

**Build (r4):**
- §4 in full: P1–P4, P6, P7, the prefix cut, and the call site on BOTH paths.
- The §5 cases and mutations.
- The deletion of `_moved` and `_sections`.

**Fold item outside this component:** **R3-F3 (Low).** `plan`'s cleanup must also cover a partial worktree creation.
`_worktree(run, root, "-b", branch, base)` runs before the `try/finally`. Git can create `batch/<time>` and then fail
the checkout, which leaves the branch behind, so a same-minute re-run refuses. Move the creation inside the `try`,
and delete the branch only if this run created it. Codex reproduced it with a failing required smudge filter. Fix it
as an ordinary r4 item. It is unrelated to the union.

**File (backlog rows, not built now):**
1. **The `rows` policy re-sorts base rows** (bound 4). Fix: emit the hunk's rows in ours' order, then theirs' new rows.
   It is Low because the postcondition already turns it into an ejection.
2. **Option (d1): delete the `blocks` placement logic** (`_tagged`, `_blocks`, `_trim`, the R2-F1 prefix placement,
   the identical-block dedupe) in favour of "ours verbatim, then theirs' non-base lines".
   - Measured: 3 ejections against HEAD's 2, on 182 conflicted pairs in the blocks files.
   - Worth it if the placement logic draws another review finding. With the postcondition, such a finding can only
     cost an ejection, so it is at most Low.
3. **The blank-line clause** (bound 1), with a measurement of what `gen-dashboard.py` does with a heading that has no
   blank line before it.
4. **The identical-addition ejection** (bound 3), only if a stacked-PR batch ever hits it.

**The stop condition for this component.** After r4, a review finding against the union resolvers is a BLOCKER only if
it shows the postcondition HOLDING on a wrong tree. "The resolver ejects a member it could have resolved" is Low and
filed, never folded under the round cap.
