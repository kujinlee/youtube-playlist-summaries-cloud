# Round 3 — `false-hold-judgment` (backlog #508) — coordinator — CONVERGED (Claude); folded

The Claude half ran on `57a1def7` and returned CONVERGED with 1 MAJOR and 2 MINOR findings. All three are fixed in this
fold, so nothing is left to file. Claude: `docs/reviews/claude/false-hold-judgment-r3-claude.md`.
REVIEW GAP: codex — alternation

```yaml
round: 3
fixes_nontrivial: true
subject: false-hold-judgment
halves:
  codex: gap
  claude: ran
findings:
  - {id: M1, severity: High, aim: deliverable, fix_induced: false, component: scripts/check-merge-ready.py, disposition: fixed}
  - {id: m1, severity: Low, aim: deliverable, fix_induced: true, component: scripts/codex-review.py, disposition: fixed}
  - {id: m2, severity: Low, aim: deliverable, fix_induced: false, component: docs/review-method.md, disposition: fixed}
```

**`fix_induced`, as classified.** M1 is `false`. It is Codex r2 #1's ORIGINAL defect, which r2 fixed only partly; it was
not caused by that fix. Under r1's two separate lists, the mirror order was exempted too: each exemption drew from its own
list. m1 is `true`. Reading after the LAST heading came from r2's section redesign. m2 is `false`: r1 made the
decision, and nobody wrote it down.

## Each finding: what was done, and which case covers it

Every code fix was written test-first. Each new case was run and seen red before the fix, then green after it.

| Finding | Disposition | Case(s) that cover it |
|---|---|---|
| **M1**: the shared added-line budget was spent GREEDILY in hunk order, so in Codex r2 #1's MIRROR order a rise took a moved line's addition and the real change went unflagged (round 2 recorded this class as fixed, and it was not) | **fixed**. `failure_path_removals` now pairs in two passes per file. First, every EXACT re-add claims its addition, across all hunks. Then a rising count may use only an addition no exact re-add claimed. Each exempted removal has its own distinct added line, whatever the order. Pairing among rises can only pair lines that are identical apart from a raised count, and when it cannot pair them it flags them, which fails closed. | The reviewer's reproduction VERBATIM, through real git and `gather`: `⭐ #508 r3 M1 real git: the MIRROR order (b() before a(), a() padded) is flagged and HELD too` (red before: `([], False)`, the fail-open). Codex's order still passes: `⭐ #508 r2 Codex 1 real git: ...`. Pure: `#508 r3 M1: in the MIRROR order (the rise first) ...`, `...and a move in a LATER hunk still claims its addition before an earlier hunk's rise`, `...and one raised-count addition excuses ONE rise, not two` |
| **m1**: only the LAST exact `## Loosening answers` heading was read, so a later heading erased an earlier section's dissent. A stray `VERDICT:` line inside the section also cut it short and dropped the findings after it | **fixed**. `loosening_answers` reads from the FIRST heading. A second exact heading, or any id named after the section's `VERDICT:` line, makes the section malformed: no assent, and every id after the first heading is a finding. An empty section followed by a finding is caught too, by an early return. | `#508 r3 m1: the reviewer's three reproductions, verbatim — an earlier section's finding is never lost`; `...TWO exact headings are malformed`; `...an answer AFTER the VERDICT: line is not read as assent`; `...a stray VERDICT:CONVERGED inside the section does not drop the findings after it`; `...even when the section is EMPTY` |
| **m2**: "commit the backlog and dashboard ticks BEFORE the final round" was not written where a coordinator reads it | **fixed**. One sentence in `docs/review-method.md`'s #508 paragraph, which now also states the r3 parser rule. | Docs only: `check-docs.py` OK |

**Two existing expectations changed, both toward failing closed.**
- r2's `...and a line a rising count consumed cannot also excuse a move` is renamed `...and one addition cannot excuse
  both a move and a rising count`. With the move now claiming the single addition first, the flagged line is the
  unpartnered `6 cases`, not the `9 cases` move. There is still exactly one flag for two removals and one addition.
- r2's `...and only the LAST section is read` is replaced: two headings are now malformed. The first case's answer line
  after `VERDICT:` is now a malformed section (its own case). The original case keeps a non-id trailer
  (`Reviewed head: <40 hex>`, which `HEX_ID` does not match) to show that normal text after the verdict is harmless.

**Bound, stated:** any 12-hex word after the `VERDICT:` line now makes the section malformed. A Claude review ends at
its `VERDICT:` line. A Codex body could quote a 12-character short sha after it, and that costs a false HOLD, never a pass.
The six review documents of this subject on disk still parse as before.

## Mutations

Each new or re-anchored entry was applied to a staged COPY (`check-plan-code.stage_tree` → `run_mutations`), never in
place. Every anchor in both touched manifests matches exactly once.

- **`check-merge-ready.json` 141 → 143.** Four were re-anchored to the two-pass code: the move removed, the move
  compared stripped, the move kept in the budget, and the move compared without trailing whitespace. Entry 20 now
  disables the move (`if False`) rather than emptying the loop, which had been a syntax error the harness could not
  attribute. The rise-kept-in-the-budget entry no longer survives behind a move. It now guards against one addition
  excusing TWO rises, a new case. Two were added: the greedy order restored, killed by both M1 mirror cases; and the
  `n not in moved` skip removed. **7/7 killed** through their named cases.
- **`codex-review.json` 87 → 91.** Five were re-anchored: the lower-case id, a malformed line skipped, only the bad
  line's ids, the LAST heading read (now named for m1), and no stop at `VERDICT:`. Four were added: a second
  heading not malformed; an id after `VERDICT:` not malformed; the malformed tail judged only inside the loop
  (the empty section); and the findings taken only from before `VERDICT:`. **9/9 killed** through their named cases.
  The first run had one entry, the second heading, killed by a case other than the one it named: a second heading
  INSIDE the section is already a malformed line. The check matters only after `VERDICT:`, so its `expect`
  now names the reproductions case.

`record-review-verdict.json` is unchanged.

## The decision gate

`python3 scripts/check-review-decision.py` at this fold: **`ARCHITECTURE_REVIEW — thrashing: 'scripts/codex-review.py'
carried fix-induced findings in r2 and r3`**. That is not the `ROUND_OWED` that was expected. The classification is the
honest one: r2's X2, X4 and X6 came from r1's parser patches, and r3's m1 came from r2's section redesign. Both are
in the answers parser. M1 was re-checked and is NOT fix-induced (see above). It is not relabelled to avoid the
gate; whether a Phase 6 review of the answers parser is convened is the coordinator's call.
