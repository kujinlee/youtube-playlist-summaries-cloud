# Round 3 — `doc-citations-guard` (backlog #49) — coordinator

⚠ **Header reconstructed 2026-10-15 from the two filed halves; the round-4 call below was written
at the time it was made**, with the owner, after they chose the redesign over a fourth defect hunt.

```yaml
round: 3
fixes_nontrivial: true
subject: doc-citations-guard
halves:
  codex: ran
  claude: ran
findings:
  - {id: H1, severity: High, aim: instrument, fix_induced: true, component: suite, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: diff-extraction, disposition: fixed}
  - {id: CH1, severity: High, aim: deliverable, fix_induced: true, component: diff-extraction, disposition: fixed}
  - {id: CM1, severity: Medium, aim: deliverable, fix_induced: true, component: diff-extraction, disposition: fixed}
  - {id: CM2, severity: Medium, aim: instrument, fix_induced: true, component: suite, disposition: fixed}
  - {id: CM3, severity: Medium, aim: instrument, fix_induced: true, component: suite, disposition: fixed}
```

## Verdict: NOT CONVERGED — 2 High

**The redesign's claim held.** Both halves attacked the class that produced the previous three
fail-opens, and neither could make the guard judge a document under the wrong name. What they broke
was the *new* load-bearing mechanism.

## 6 of 6 findings were caused by round 2's own redesign

| id | Finding | Caused by |
|---|---|---|
| H1 | `-z` is the entire premise of the redesign and **nothing in the suite was watching it** — removing the flag silently disables the guard | the redesign |
| M1 | glob metacharacters in a scoped filename made the per-file pathspec over-match, so findings were misattributed and duplicated | the redesign's per-file diff |
| CH1 | added content beginning `++` was discarded as a header — `startswith("+++")` is not a header test | the redesign's marker parser |
| CM1 | per-file diffing turned a pure rename into newly added citations, contradicting the added-lines-only contract | the redesign's per-file pathspec |
| CM2 | `_nul_witness()` inherited Git configuration and crashed on an ordinary signing requirement | H1's own fix, same round |
| CM3 | the literal-pathspec fix had no regression witness | M1's own fix, same round |

---

# The round-4 call — THRASHING, and the redesign is owed again

`dev-process.md`: *"Reaching four rounds OBLIGES ASKING, and does not fire."* Asked and answered
2026-10-15; the owner chose to redesign the component. The evidence that framed the question:

⚠ **`check-review-decision.py` independently returns `ARCHITECTURE_REVIEW` on this branch** —
*"thrashing: 'diff-extraction' carried fix-induced findings in r2 and r3"* — once the three round
documents exist for it to read, which until 2026-10-15 they did not (it reported `rounds=0` while
six halves sat committed). Its verdict names the Phase 6 instrument. **The owner was offered that
explicitly and chose the narrower subject**: a design review of this one component, which is what
`review-method.md:171` prescribes for thrashing confined to one unit. The signal is not disputed —
the scope is. If the redesign below thrashes in turn, the wider review is the next step and this
paragraph is the reason it was deferred rather than missed.

**The arming condition is met, literally.** Rounds 2 and 3, consecutively, carried findings caused
by the previous round's own fix, in one component: **15 of 15**, 9 then 6, with `diff-extraction`
present in both (3 of 9, then 3 of 6) and the supporting `suite` findings existing only to witness
it. The per-finding evidence is the two tables above.

**Prose floor was not available as a reading.** That shape is defined as the limit of reviewing
*without an executable subject*; this subject executes, and the halves ran it.

**The test that decided what round 4 should be — *can a redesign remove it?*** (`review-method.md:200`)

| r3 finding | Redesign removes it? | Kind |
|---|---|---|
| CH1 `++` bypasses checking | **Yes** — nothing would read content out of diff text | mechanism |
| CM1 rename reports new citations | **Yes** — one diff invocation, no per-file pathspec | mechanism |
| M1 glob pathspec over-match | **Yes** — same | mechanism |
| CM2 `_nul_witness` git-config crash | **Yes** — the probe exists only to prove `-z` plumbing | mechanism |
| H1 `-z` has no witness | No — coverage of a mechanism that would be gone | branch-coverage |
| CM3 pathspec fix has no witness | No — same | branch-coverage |

Four of six are mechanism defects dissolved by **one** reshaping, and the two that are not are
witnesses for mechanisms the reshaping deletes.

**The reshaping, named before the code.** Stop reading content out of the diff. Take the changed
line *numbers* from the `@@` hunk headers, and read the lines themselves from the file. `violations()`
then receives a path, a set of added line numbers, and the document's own lines — no `+` marker, no
`---`, no `\ No newline at end of file`, one git invocation for the whole diff instead of one per
file plus a rename pathspec.

**⭐ And it collapses a DECLINED finding into the same guard.** r1 L2 (fenced code blocks, measured
at 40 of 896 living citations, 4.5%) was declined with the reason *"Fixing it means reading the file
rather than the diff, which is a different guard."* Reading the file is what this reshaping does, so
the fence exemption becomes available here rather than in a hypothetical successor. That is the
strongest evidence that the shape, not the patches, was the problem: the same change closes the
fail-open class *and* the stated false-positive class.

**The one new fail-open this creates, stated before it is built.** A malformed or unparsed `@@`
header would yield no added line numbers, which reads as *"nothing to check"* — the same failure
direction as the three header defects. It must be CANNOT RUN, and its falsifier is the first case
written, not the last.

---

# The design, written before the code (step 2 of the redesign)

## The structural property the shape rests on

**In a unified diff every content line carries a one-character prefix — `+`, `-`, or a space. So no
content line can begin at column 0 with `@@`.** Header-versus-content becomes a question of
POSITION, which git guarantees, instead of a guess from a PREFIX, which it does not.

That is the thing the old shape could never have. It had to distinguish `+++` (a file header) from
`+` plus `++` (an added line beginning `++`), and those are the same four characters. Three
generations of one defect came out of that ambiguity — r1-codex High, r2 High + r2-codex High, and
r3-codex High — each fixed, each replaced.

## The shape

```
changed_files(base, root)            -> ((path, source|None), ...)      UNCHANGED: --name-status -z -M
file_diff(base, root, path, source)  -> that file's unified diff         UNCHANGED, but only @@ is read
added_lines(diff_text)               -> (line_number, ...)              NEW. PURE. Reads ONLY @@ headers.
                                                                        RAISES on a header it cannot parse.
violations(path, added, doc_lines, tracked, read) -> findings            PURE. NO DIFF TEXT AT ALL.
```

`main()` then reads each scoped document's own lines through the *same* injected reader the resolver
uses, and examines `doc_lines[n-1]` for each `n` in `added`.

## What this deletes, and what it makes reachable

| Gone | Because |
|---|---|
| `line.startswith("+")` / `line[1:]` | content no longer comes from the diff |
| the `in_hunk` state machine | `@@` is read for its numbers, not as a mode switch |
| the `++`/`---`/`\ No newline` classes | there is no body parser left to confuse |
| two ambient cases (below) | the property they named becomes checkable |

⭐ **And it makes r1 L2 reachable.** That finding (fenced code blocks, 40 of 896 living citations,
4.5%) was DECLINED with the reason *"Fixing it means reading the file rather than the diff, which is
a different guard."* This reshaping reads the file, so the fence exemption becomes available here.
**It is deliberately NOT implemented in this round** — it changes what the gate asserts, and the
owner authorised a redesign, not a scope change. Filed instead, with this paragraph as its argument.

## ⛔ The one new fail-open, named before it exists

`added_lines` returning `()` for a header it did not understand reads as *"nothing to check"* — the
same failure direction as all three header defects. **It raises, and `main()` turns that into
CANNOT RUN (rc=2).** Its falsifier is case 1, not case 41.

A second invariant falls out of reading the document rather than the diff: if git says line `N` was
added and the document has fewer than `N` lines, the two sources disagree and the guard cannot
proceed. That is CANNOT RUN too, never a skip.

## The falsifiers, each flipped before it is trusted

Every case below names a property, and each one was accepted only after the thing it names was
flipped in the implementation and the case was observed to redden — the method the five previous
ambient cases on this file cost.

| # | Property | Flip that must redden it |
|---|---|---|
| 1 | a malformed `@@` header is CANNOT RUN | `except ValueError: return ()` |
| 2 | `@@ -1,0 +2,3 @@` yields exactly 2,3,4 | any off-by-one in the range |
| 3 | `@@ -1 +2 @@` (count omitted) yields 2 | default the count to 0 |
| 4 | `+c,0` (a pure deletion hunk) yields nothing | include `c` anyway |
| 5 | several hunks accumulate | return after the first |
| 6 | **an added line beginning `@@` is content, not a header** | test the line after stripping its prefix |
| 7 | a line NOT in the added set is not examined | examine every line of the document |
| 8 | a citation that exists only in the PRE-image is invisible | read the pre-image instead |
| 9 | a pure rename adds nothing | drop `source` from the pathspec |
| 10 | a glob-shaped document name does not over-match | drop `--literal-pathspecs` |
| 11 | `changed_files` splits on NUL | drop `-z` |
| 12 | an added line past the document's end is CANNOT RUN | skip it silently |

Case 7 is the one that replaces the two ambient cases. **Measured 2026-10-15, before the redesign:
deleting the marker filter outright (`if not in_hunk or not line.startswith("+")` →
`if not in_hunk`) left the suite at 41/41 green.** The two cases that claimed to witness it —
*"a REMOVED line is not examined"* and *"a context line is not examined"* — pass fixtures with no
`@@` line at all, so `in_hunk` is `False` and the filter is never reached. Ambient cases six and
seven on one file.

## ⛔ And the branch is RED in CI, which three rounds did not notice

`check-fixture-variation.py` — a guard `ci.yml` runs — returns **11 findings, every one against
`scripts/check-doc-citations.py`**, a file that does not exist on `origin/master`. `changed_files`,
`file_diff`, `tracked_files` and all six `main()` parameters are each passed ONE constant value by
the whole suite, so no case can tell them from a literal.

Round 2's Blocking was *"the branch is RED against its own gate."* This is the same defect one guard
over, and its cause is `docs/CLAUDE.md` rule 1 verbatim: **a SUBSET of the document guards was run.**
Every "N guards green" recorded on this branch was true of the guards that were run. The sweep that
found it is the full `python3 scripts/check-*` list taken from `ci.yml`, not from memory.
