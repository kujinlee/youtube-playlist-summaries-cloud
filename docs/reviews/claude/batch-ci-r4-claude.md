Reviewed head: 8fd71df98051646b0fa5eaaee1b7f25deef1a8d8

# Round 4 — `batch-ci` (PR #529, backlog #534) — Claude half (REFUTE mandate, round cap in force)

REVIEW GAP: codex — alternation (round 4 runs the Claude half)

Scope: the r3 fold `8fd71df9` (the whole-file `postcondition`, its call site `_checked`/`_union_violation`, the
R3-F3 worktree move, the 14 new mutations), read against
`docs/reviews/architecture-review-2026-11-07-batch-ci-docs-union.md` §4–§7,
`docs/reviews/coordinator/batch-ci-r3-coordinator.md` and `docs/reviews/codex/batch-ci-r3-codex.md`.
All experiments ran on a `git archive HEAD` scratch copy; nothing in the worktree was modified except this file.

## Gates run (at `8fd71df9`)

| Check | Result |
|---|---|
| `python3 scripts/batch-ci.py --self-test` | 168/168 passed (58 s) |
| `python3 scripts/check-merge-ready.py --self-test` | 348/348 passed |
| `python3 scripts/check-decision-scheme.py` | rc 0 (only the standing WARNs 4, 6, 8, 10, 11, 12) |
| The 14 NEW mutations in `scripts/mutations/batch-ci.json` (diffed against `4e4678fb`), each applied by hand to a scratch copy, full self-test run | **14/14 red on EVERY case they name**; 0 anchors missing or ambiguous |
| Randomised oracle fuzz of the pure `postcondition` (an independent checker with hidden TRUE line identities; ~52,000 candidate results over generated B/O/T) | 0 wrong passes with unique body lines EXCEPT the class in R4-F2 and identical-line identity ambiguity (below) |
| Real-git merges through `merge_into` (9 shapes: mid-section heading, new goal above/below, CRLF, lone CR, the R3-F1 family) | every one either correct or ejected, except the byte-level class in R4-F1 |

## The focus questions, answered

**1. Can the postcondition be made to pass a WRONG tree?**
- Duplicate headings, the same line added by both sides, a line moved across headings, a renamed heading, blank-line
  games: no wrong pass found. Each either held on a correct tree or EJECTED (P1 for a both-sides addition — §6
  bound 3; P4 or P1 for a moved line; P3 for a renamed heading kept by the other side).
- The fuzz's apparent "wrong passes" with DUPLICATE body lines are identity ambiguity, not defects. Example:
  B = `z z z`, T deletes ONE `z`. Which one it deleted is not recoverable from any text, so no tool can be wrong
  about it. I discount those.
- Two real classes remain. R4-F1 is reachable through `merge_into`: line-ending bytes. R4-F2 is pure only: the
  POSITION of a section theirs added.
- Several merge bases: `_union_violation` skips a file when EACH base equals one side
  (`scripts/batch-ci.py:804-812`). That is looser than §4.1's wording, but the only history that reaches the mixed
  case (base 1 = ours' file, base 2 = theirs' file) is one where each side reverted the other's addition. Git's
  virtual-base answer then drops both, which is what both histories say. It is not a wrong tree. No finding.
- CRLF: R4-F1.

**2. The six departures.**
1. "No correct output for case 2." Sound. My own reasoning agrees, and so does PC5b's 120 arrangements: ours orders
   `existing` before its thread, and theirs re-sections `existing` under billing.
2. "`c`→`n` is EQUIVALENT." **Not exactly, but harmless**, and the stronger fact is below. Over 120,000 random
   inputs, `c`→`n` changed the verdict on 2. In both it is STRICTER: a false ejection on stacked empty duplicate
   headings (`## A\n## A`). It never produced a pass where HEAD fails. More important: **removing the cut entirely
   (`cut = 0`) changed 0 of 120,000 verdicts.** It also ran the real 18,918-line dashboard append in 0.3 s, a
   header edit plus append in 0.3 s, and a 150-commit-old base in 0.19 s. And PC14's `< 5 s` bound passes without the
   cut (0.14 s), because its 20,000 filler lines are unique. So the cut is unguarded code whose stated reason did not
   reproduce. That is R4-F3.
3. "P6 reads the WHOLE result." Sound. PC6b is red under its mutation. Neither the base nor `origin/master`'s
   `backlog.md` has a duplicate row number today, so this ejects nothing now.
4. "Two real-git cases now expect an ejection." Consistent with §6 bound 3, and filed as backlog 549.
   - The decision-log row's `outcome: null` is the scheme's documented arrival state (`check-decision-scheme.py`
     docstring: *append-only with `outcome: null` on arrival*).
   - Reusing the unit string is how the scheme is MEANT to see a second attempt on the same unit
     (accrete → redesign).
   - `check-decision-scheme.py` exits 0 on it. Sound.
5. "Case 20 green on postcondition-free code by construction." Sound. Its falsifier mutation ("a union file one side
   left alone is checked anyway") is red on PC20.
6. (R3-F2's "restore `_added(theirs, …)`" not done.) Sound. P3 catches it (PC1, PC17).

**3. Does the postcondition run on every path?**
- `merge_into` returns through `_checked` on the clean path (`:760`) and the resolved path (`:780`).
- Every other exit is an abort: a conflict outside the union files, `clean_only`, a delete/modify conflict, or a
  `Refuse`.
- Both callers go through `merge_into`: `plan` (`:902`) and `_refresh` (`:1201`), whose tree must equal the batch's.
- A member-supplied `.gitattributes` `merge=union` or `merge=ours` driver makes git merge "cleanly", so the clean-path
  check covers it.
- A `CannotRun` while reading aborts the merge and re-raises.
- R3-F3: reproduced with REAL git (a required smudge filter that fails). `worktree add -b` leaves the branch and no
  registered worktree. `git branch -D` then succeeds, so the fold's clean-up works on real git, not only on the
  self-test's simulated failure.

**4. Each new mutation is red on its named cases.** 14/14 (table above).

## Findings

### R4-F1 — Low — the postcondition reads every side through newline translation, so a resolved union file can rewrite every line ending (or split a line at a lone CR) and still hold

`scripts/batch-ci.py:721` (`_run`: `text=True`, which applies universal newlines to `git show` in `_blob`),
`:818` (`read_text` of R), `:775` and `:778` (the resolver reads the conflicted file with `read_text` and writes it
back with `write_text`).

**Scenario.**
- B, O and T are all read with `\r\n` and lone `\r` translated to `\n`, and so is R.
- On the CONFLICTED path the resolver also reads the file translated and writes `\n`. So every CR in the file
  disappears, including in base lines that both sides kept byte-for-byte.
- The postcondition compares translated texts, so it cannot see this, and it holds.

**Repro** (scratch copy, real git, `merge_into`; tool kept at
`/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/f7c144b8-1b6c-4db3-8ef1-932d4e701b12/scratchpad/r4/tools/crlf.py`).
`docs/backlog.md`: ours appends `| 3 |`, theirs appends `| 4 |`, and the end-of-file conflict is resolved.

| Base | `merge_into` returns | CR bytes in the result |
|---|---|---|
| CRLF throughout | `None` (accepted) | 0, from 5 |
| `\| 1 \| a\rstill row 1 \|` (lone CR inside a base row) | `None` | 0; the row is now two lines, `\| 1 \| a` and `still row 1 \|` |

**Why it is not a BLOCKER.**
- No consumer can tell the difference. CommonMark treats CR, LF and CRLF alike as line endings, and every repo reader
  (`gen-dashboard.py`, the backlog checks) reads with universal newlines.
- The four union files hold 0 CR bytes today (`grep -c $'\r'`).
- The resolution is deterministic, so CI sweeps the very tree that lands, and `_refresh` re-creates it.
- So it is not "a tree other than the one CI swept", and not a consumer-visible wrong tree. It is a byte-level
  blind spot, filed.

**Fix (cheapest).** Eject a union file whose B, O or T contains `"\r"`: "a CR in a union file; resolve by hand".
Alternatively, read bytes (`text=False`, then decode) and use `open(..., newline="")` in the resolver.

### R4-F2 — Medium — a section THEIRS added may land at any section boundary: P4 gives a heading line itself as its home, so the postcondition never checks where a section sits

`scripts/batch-ci.py:419-426` (`_homes`: a heading's home is its OWN identity) and `:496-509` (P4).

**Scenario.**
- A heading line's expected home is itself, and its body follows it. So a block theirs added (its heading plus its
  lines) passes P1–P7 wherever it sits, provided it sits between two sections.
- That includes ahead of BASE sections. In `docs/dashboard-entries.md` that is a wrong tree:
  - ids are `date/ordinal` in file order (`gen-dashboard.py:414`);
  - "an earlier entry cannot resolve a later one" (`gen-dashboard.py:1783`, a self-test case).
- §6 states bound 2 as order WITHIN a section. The order OF sections is not stated as a bound.

**Repro** (pure).
- B = `# Dashboard entries` plus two entries, `## 2026-11-06 [needs-you]` and `## 2026-11-06`.
- O appends `## 2026-11-07`.
- T appends `## 2026-11-07 [resolved: 2026-11-06/1]`.

| Result | `postcondition` returns |
|---|---|
| T's resolving entry moved to the TOP of the file | `[]` |
| T's entry moved BETWEEN the two base 2026-11-06 entries, which shifts the second one's ordinal | `[]` |

- The oracle fuzz's only wrong passes with unique body lines were this class, including empty duplicate headings that
  float.

**Why it is not a BLOCKER.**
- The stop condition's wrong tree is one a merge can PRODUCE, and the mandate says to build it through `merge_into`.
  I could not:
  - git places an insertion where theirs put it;
  - `blocks` emits theirs' heading-led blocks at the END of the hunk, so never EARLIER than theirs had them;
  - dashboard entries are only ever appended.
- 6 real-git goal-threads shapes (a new goal above product, crossed with ours under the heading, at the end of dev,
  or at the end of product; with and without a second product thread from theirs) all produced the correct order
  (tool `float.py` beside `crlf.py`).
- So the safety net has a hole that no current producer reaches.
- ⚠ **Coordinator's call.** By the letter of the decision-log bet ("Refuted if r4 shows the postcondition passing a
  wrong tree") the PURE function does pass one. If the bet is read at the level of the pure function rather than of
  a landable tree, record it as refuted on this point.

**Fix (one clause, P8).** For each heading in R, the nearest PRECEDING heading with a base identity `("b", ·)` must
equal the one before it in the side it came from. Base headings already keep their order through the monotone R→O
match, so this pins every added section between the same two base sections. Two new sections appended after the same
base section stay legal in either order. That is the only order freedom left, and it is the honest one.

### R4-F3 — Low — the prefix cut is semantically dead and its speed guard does not guard it

`scripts/batch-ci.py:455-461` (the cut) and the PC14 case (`< 5 s`).

**Scenario.**
- `cut = 0` (no cut at all) changed **0 of 120,000** random verdicts against HEAD, under both policies.
- No cut was also fast on the real file: the 18,918-line dashboard append took 0.3 s; a header edit plus append took
  0.29 s; a base 150 dashboard commits old took 0.19 s.
- PC14's 20,000 filler lines are UNIQUE, which is difflib's fast case, so PC14 passes in 0.14 s without the cut. The
  mutation "remove the cut" therefore survives.
- The review's measurement ("without the cut, `difflib` over the full dashboard did not finish in 5 minutes") did not
  reproduce on any shape I built. It may hold on some replayed pair I did not build, so I state that as unmeasured,
  not refuted.
- Departure 2's "`c`→`n` is equivalent" is nearly right (above). The real point is that the WHOLE cut is equivalent
  in verdict, and only its claimed speed justifies it.

**Repro.** `tools/cuteq.py` and `tools/hdr.py` beside `crlf.py`.

**Why it is not a BLOCKER.** It cannot change a verdict and so cannot pass a wrong tree. It is unguarded code.

**Fix.** Either delete the cut (P6's whole-result read then needs no special case), or keep it and give PC14
DUPLICATE-heavy filler (e.g. repeated `Result: passed` / `<!--tech-->` blocks) that is slow without the cut. Then add
the "cut = 0" mutation against it.

## Not findings (checked, sound)

- §4's "a poor alignment costs an ejection, never a pass" held under the oracle for every class except R4-F2. R4-F2
  is not an alignment problem: the definition simply does not cover section order.
- The several-merge-bases refusal (PC19) is red without the guard. Its per-base skip is discussed above.
- `merge_into`'s `abort` on a `CannotRun` inside `_checked` runs before the re-raise, so the worktree is never left
  mid-merge.

## Disposition under the round cap

None of the three findings is a BLOCKER under the adopted stop condition:
- **R4-F1:** no consumer-visible wrong tree, and CI sweeps exactly what lands.
- **R4-F2:** no wrong tree is producible through `merge_into`. The coordinator's call is flagged above.
- **R4-F3:** it cannot change a verdict.

All three are FILED, not folded. Nothing found lets `land` merge a tree other than the one CI swept, or merge a HOLD
PR.

VERDICT: CONVERGED
