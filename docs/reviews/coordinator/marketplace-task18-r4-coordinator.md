# Round 4 — `marketplace-task18` — coordinator — a line mixing a real link and a pseudo-link hides a quote; FILED as backlog #698 (past the round cap)

Codex reviewed 2856ce3c (the round 3 fold of plan Task 18, PR #617): `docs/reviews/codex/marketplace-task18-r4-codex.md`.
It reports X1 MAJOR, `fix_induced: false`, with verdict NOT CONVERGED. Its loosening answer is "not a loosening".

REVIEW GAP: claude — alternation

## The round cap (`review-method.md` §0 Q4c)

From round 4, a finding is FILED unless it is a BLOCKER.
- **X1 is not a BLOCKER.** It needs a deliberately crafted line: a real link and a bracketed pseudo-link interleaved inside one quote. That is not an ordinary case.
- **The corpus is written by this repository's own paraphrase step, not by an adversary.**
- **Its six paraphrases were checked word by word in rounds 1 and 3:** no owner quote, name, date or PR number survives.
- **No check passes without running.** Round 1's C2 made a D file with no quote CANNOT RUN.

## Thrashing or prose floor?

Neither in the arming sense. Round 3's finding was fix-induced; round 4's is not. That is two rounds, but not two
CONSECUTIVE fix-induced ones, so Phase 6 does not arm.

The pattern is still recorded:
- Every round found a NEW evasion of the same regex model of Markdown: punctuation, links, pseudo-links, and now mixed links.
- That says the model is the defect, so the filed fix replaces it with rendered visible text, not another regex.

## Dispositions

- **X1 (MAJOR, not fix-induced): `I [almost](https://example.com) never [pay](attention to)` passes `--check`. FILE: backlog #698.**
  - Reproduced by the coordinator at 2856ce3c: PASS.
  - The script's docstring section *What this cannot see* already names this shape: "a quote whose words are split by a link in one place" and by visible bracketed text in another.
  - Fix, filed: match on the visible text produced by a real CommonMark renderer.
  - Must land before Task 21 publishes the corpus. This leaves backlog #697 and backlog #698 both standing between Task 21 and publishing.

## Verdict for the merge

The branch merges with backlog #698 filed. Codex confirmed the fresh real build passes `--check` and all 27
mutations are killed and attributed in a full clone.
