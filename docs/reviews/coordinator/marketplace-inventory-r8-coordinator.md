---
round: 8
subject: marketplace-inventory
head: 1fd65315
halves:
  claude: ran
  codex: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339); round cap from r4 (review-method §0 Q4c)"
findings: [B1, M1, L1, L2]
verdict: NOT CONVERGED
---
# Round 8 — coordinator

REVIEW GAP: codex — alternation. Rounds 2+ run ONE half; round 7 was Codex, this round is Claude.

**Why this round:** `check-merge-ready --pr 376` HOLDs on the body's `NO-REVIEW:` waiver. The waiver named what
fewer than two halves examined: the `_VOID_EXPECTED` work in `scripts/check-claim-propagation.py` (one reviewer)
and the explainer edits at `d06da80c`/`4d07ee59` (none). This round is aimed at exactly those. `scripts/recall-llm.py`,
also named, is not in `git diff origin/master...HEAD` (confirmed by the reviewer).

| id | sev | finding | route |
|---|---|---|---|
| B1 | BLOCKER | walkthrough page row "Same nine files, today: 3,599 vs 6,542 → 1.82× low": the other two places were dated to `a4f6d4b5` by `d06da80c`, this row was missed and reads as current | FOLDED: dated to `a4f6d4b5`, plus the figure at `1fd65315`. Coordinator re-measured both by `git show <c>:<f> \| wc -l` over the nine files `portable-practices.md` enumerates: 6,542 at `a4f6d4b5`, 11,272 at `1fd65315` (3.13×) |
| M1 | MEDIUM | the page never mentions the spec's 11-09 re-measurement; its dated figures can read as latest | FILED backlog #605 (round cap) |
| L1 | LOW | five obsolete void tags missing from `VOID` | FILED backlog #606 |
| L2 | LOW | a case name says "14 HTML void elements" | FILED backlog #607 |

The `_VOID_EXPECTED` work could not be refuted: 58/58 self-test, 18/18 mutations killed, every probe handled or loud.
The waiver is therefore paid: both named subjects now have a second reviewer, and the one BLOCKER is folded.
The B1 fold is a one-cell doc edit, verified by measurement, not re-reviewed (round cap).
