# Round 2 — `review-round-cap` — coordinator — NOT CONVERGED (Codex); REDESIGN (fixed positions, not a Markdown parser)

REVIEW GAP: claude — round 2 alternates to the Codex half alone (rounds 2+ alternate, `review-method.md` → *Round topology*, step 4).

```yaml
round: 2
fixes_nontrivial: true
subject: review-round-cap
halves:
  codex: ran
  claude: gap
findings:
  - {id: X-H1, severity: High, aim: deliverable, fix_induced: true, component: head-declaration, disposition: fixed}
  - {id: X-M2, severity: Medium, aim: deliverable, fix_induced: true, component: verdict-word, disposition: fixed}
  - {id: X-M3, severity: Medium, aim: deliverable, fix_induced: true, component: verdict-word, disposition: fixed}
  - {id: X-n1, severity: Low, aim: deliverable, fix_induced: false, component: blocker-definition, disposition: fixed}
```

Codex on `08597dfb` (`docs/reviews/codex/review-round-cap-r2-codex.md`). **X-H1 (BLOCKER by Q4c's three tests)**: a
declaration of the head inside an HTML comment, an indented code block, or a lazy blockquote continuation was read
as the reviewer's own, and the real final-tree gate credited a tree the review never saw. **X-M2**: a nested fence
(four backticks around three, or around `~~~`) toggled the parser's fence state, so an example verdict was read and
the real one suppressed; an HTML-commented verdict was accepted. **X-M3**: `startswith` read `CONVERGEDNESS` as
`CONVERGED`. **X-n1** (closing note): an r5 BLOCKER "notified to the human" did not explicitly hold the PR.

**Why patching cannot win:** all three come from one cause, r1's own fix. It searched free Markdown for "the
reviewer's own line", and each repro is a Markdown construct it did not model. A comment, an indented block, a lazy
continuation and a nested fence are four of many; another round would find a fifth. **Route: REDESIGN.** The
declaration and verdict now live at FIXED POSITIONS: the first line is exactly `Reviewed head: <full sha>`
(`HEAD_LINE.fullmatch`, compared to the head, no token resolved), and the last non-empty line is exactly
`VERDICT: CONVERGED` or `VERDICT: NOT CONVERGED` (`VERDICT_LINE.fullmatch`). Nothing else in the file is read for
either, so no Markdown construct can move them. Lines are split on `\n` only, so a Unicode line separator Markdown
renders inline cannot create a "last line".

**Thrashing?** X-H1–X-M3 are fix-induced by r1's head-declaration and verdict-word repairs, the first such round in
this component. The redesign removes the parsing they came from rather than adding to it. Round 3 is the last
ordinary round (§0 Q4c).

## Dispositions

- **X-H1 — fixed** (redesign above). Codex's three inputs, each also in the new declaration form, plus a blank first
  line, a prefix, an abbreviated head and a trailing note after the sha: all ten are refused `HEAD NOT NAMED` end to
  end with nothing written. The same review with the declaration on line 1 is recorded, and line 1 naming the other
  full sha is `HEAD MISMATCH`.
- **X-M2 — fixed.** Codex's nested-fence input (old form) gives no verdict. In the new form the last line decides:
  `NOT CONVERGED` under both the backtick and `~~~` variants. A file ending in a fence or in an HTML comment states no
  verdict.
- **X-M3 — fixed.** `CONVERGEDNESS`, `VERDICT: CONVERGEDNESS` and `VERDICT: CONVERGED.` give no verdict.
- **X-n1 — fixed.** Q4c's r5 row now says a BLOCKER notified to the human HOLDS the PR until they answer.
- **Brief text** (`review-method.md` Q2 step 4) now tells a Claude half to write the two fixed lines. No other file
  carries a Claude-half brief template (grep `Reviewed head` / `## Verdict` outside `docs/reviews/`). Backlog #434 and
  #435 and the dashboard entry describe the new form.
- **Kept from r1:** `TREE MOVED`, the observed overlay, symlink refusal and no overwrite are unchanged, with their
  cases and mutations.

## Evidence

- `record-review-verdict.py --self-test`: 24 new r2 cases written first. Against `08597dfb`'s parser **19 were red**
  (79/98), every Codex repro among them. Then 98/98.
- `check-plan-code.py --mutate . --only scripts/record-review-verdict.py --allow-long-local`: 21 mutations, 21 killed,
  21 attributed, 0 survivors. Pin 19 → 21. Eight entries were retargeted onto the fixed-position reads (the parser
  they named is gone). Two were added: the `\n`-only split, and reading line 1 from the unstripped body.
- `check-fixture-variation`: `declared_heads.text` → `declared_head.text`; `review_problem.resolve` retired with
  its parameter.
