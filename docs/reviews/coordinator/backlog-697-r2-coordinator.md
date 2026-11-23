# Round 2 — `backlog-697` — coordinator — quote-check every shipped file, and read the builder through an exact contract

```yaml
round: 2
fixes_nontrivial: true
subject: backlog-697
halves:
  codex: ran
  claude: gap
findings:
  - {id: X4, severity: Major, aim: deliverable, fix_induced: true, component: closure-guard, disposition: accepted}
  - {id: X5, severity: Major, aim: deliverable, fix_induced: true, component: closure-guard, disposition: accepted}
```

Codex reviewed 654aa29f: [`codex/backlog-697-r2-codex.md`](../codex/backlog-697-r2-codex.md). Its verdict is NOT CONVERGED, with 2 MAJOR findings.

REVIEW GAP: claude — alternation (round 2)

**What held:**
- The branch meets row 697's literal **Fails if** at 654aa29f.
- Colliding basenames are both checked.
- A non-`.md` corpus file is checked.
- A timeout is CANNOT RUN.
- The scratch directory is outside the repository and is removed.
- Backlog #707's area is claimed, and the inventory row matches the 179-file declaration.
- Three new mutations die in a full clone.

## Is this thrashing?

**Not yet.** Both findings are fix-induced and in closure-guard, but round 1's closure-guard finding (X2) was not. So these are not two consecutive fix-induced rounds. A fix-induced finding there in round 3 WOULD be thrashing and would arm Phase 6.

That is why this fold is a **redesign, not another patch**. Both findings come from a choice the round-1 fold made:
- X4: it chose a subset of the files to quote-check.
- X5: it chose a loose reading of the builder's success.

The redesign removes both choices.

## Dispositions

- **X4 (MAJOR, fix-induced) — ACCEPT. Quote-check every file every package ships, whatever its path.**
  - Remove the `CORPUS_DIRS` filter from `decision5_quotes`.
  - **Measure first:** run the builder's `--check` over the real shipped set of every package. A hit on a file that is not group-D material is a false alarm.
  - If false alarms occur, report how many and on which files. Do not invent an allowlist.
  - Cases:
    - The input from the review (a group-D source plus one added line, shipped as a path outside the corpus directories) is red.
    - The same file shipped by a package other than recall is red.
    - The real tree stays at 0 gaps.
  - The docstring's BOUND about outside-directory files is deleted, because it is no longer true.
  - **Fixed in 45847ecf.**
- **X5 (MAJOR, fix-induced) — ACCEPT. Read the builder through an exact success contract.**
  - A PASS requires all three:
    - rc 0;
    - stderr empty after stripping whitespace;
    - every stdout line is one the builder prints on a clean run, with the final line exactly the builder's PASS line. Read the builder's `check()` to enumerate these lines, and name the symbol you took them from.
  - Anything else is CANNOT RUN (rc 2).
  - FAIL keeps its existing strict parse.
  - Cases, each CANNOT RUN:
    - rc 0, a stderr message, then a fabricated `PASS:` line;
    - rc 0, a garbage line, then `PASS:`;
    - rc 0, a `PASS:` line with different text.
  - A mutation per clause.
  - **Fixed in 45847ecf.**

Round 3 alternates to the Claude half. From round 4, findings are FILED unless a BLOCKER (`review-method.md` §0 Q4c).

## The fold's measurement (X4)

Over every file every package ships, the check found **1 hit**: `scripts/gen-backlog-page.py`, a code comment in the comprehensibility package that quotes the owner's 2026-11-02 request word for word. That is one of group D's quotes.

**This is a true positive, not a false alarm.** An owner quote was shipping unparaphrased, which is exactly what decision 5 forbids. The round-1 fold's directory filter hid it.

**Decision (coordinator, 11-23 07:32):** paraphrase the comment. The rule stays whole, and the check gets no allowlist.
