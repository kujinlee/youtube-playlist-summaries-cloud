# Round 2 — `goal-tree-superseded` (PR #480, backlog #484) — coordinator — NOT CONVERGED (Codex half); all findings fixed

Codex half: `docs/reviews/codex/goal-tree-superseded-r2-codex.md`, which reviewed `a7af562d`.
REVIEW GAP: claude — alternation (rounds 2+ run ONE half per round, `docs/review-method.md` → *Round topology*).

```yaml
round: 2
fixes_nontrivial: true
subject: goal-tree-superseded
halves:
  codex: ran
  claude: skipped
findings:
  - {id: X2-M1, severity: Medium, aim: deliverable, fix_induced: true, component: fate-read, disposition: fixed}
  - {id: X2-M2, severity: Medium, aim: deliverable, fix_induced: true, component: fate-read, disposition: fixed}
  - {id: X2-L1, severity: Low, aim: deliverable, fix_induced: true, component: multi-ref, disposition: fixed}
  - {id: X2-N1, severity: Low, aim: deliverable, fix_induced: true, component: fate-read, disposition: fixed}
```

All four came from the r1 fold's own grammar. That fold added the `Previously: ` lookbehind, the single-backtick
code-span strip, the per-ref precedence and the reopen BOUND. The fate read now goes through one pure function,
`fate_text(status)`, and the four fixes all live there or next to it.

**X2-M1 — fixed. The cell is CUT at its first `Previously:`.** The r1 lookbehind `(?<!Previously: )` only looked
at the characters just before the glyph. Codex's cell `Previously: pending — ✅ **SUPERSEDED by backlog #12**` read
as superseded, and so did two spaces after the colon. `fate_text` now removes code spans first, then keeps only
the text before the first `Previously:`, and markers are matched in what is left. The lookbehind is gone.
The cases cover intervening prose, extra whitespace, several historical markers, and two `Previously:` in one
cell (cut at the FIRST, not the last). An adjacent case keeps a marker that comes BEFORE `Previously:`.

**X2-M2 — fixed. Code spans are stripped by MATCHING backtick runs, CommonMark style.** A run of N backticks
closes only on a run of exactly N, and an unclosed run is literal (`CODE_SPAN_RE`). The cases cover a double-backtick
span holding a marker, a double-backtick span whose content holds a single backtick, and a triple span. The adjacent
cases keep two things readable: a marker after an UNCLOSED run, and a marker between two single spans. One case
puts the order in a test: a QUOTED `` `Previously:` `` does not cut the cell, because code spans go first.

**X2-L1 — fixed (coverage only; the code was already correct).** A new case uses `backlog #10, PR #999`, with #10
superseded or withdrawn and #999 absent from otherwise successful gh results. It asserts the state AND the detail:
`❓ notfound`, `<fate> · PR #999 is not among the 300 newest PRs gh listed`. Codex's survivor
`state in ("merged", "next", "closed", "notfound")` is registered against that case.

**X2-N1, the reopen note — fixed by a cheap rule; the r1 BOUND's claim is withdrawn.** Codex was right that the
backlog has no universal reopen convention. Row 327 APPENDS `⟳ **2026-10-25 — REOPENED BY THE OWNER, …**` after
its supersession prose and does not move that prose behind `Previously:`. A fate marker is now cancelled by a
LATER bold span that LEADS with `REOPENED`, optionally after a date and a dash (`REOPEN_RE`). The scan starts after
the marker's own closing `**`. The coordinator's suggested spelling, `**REOPENED`, alone would miss row 327's real
shape, because its bold span leads with the date. Each marker is judged on its own, so a row superseded, reopened
and superseded again is still superseded, pointing at the LAST pointer.
- **Cases:** row 327's shape with a supersession marker added, and a bare `**REOPENED 2026-11-02**` after a
  WITHDRAWN marker, both read live. Four adjacent negatives keep the fate: a reopen BEFORE the marker, an unbolded
  REOPENED, a bold span that holds REOPENED without leading with it (`**owner: NOT REOPENED**`), and
  supersede → reopen → supersede.
- **BOUND, now in the code comment:** a reopen written any other way is not seen. That covers lowercase, unbolded,
  and not leading its bold span. A backslash-escaped backtick is also treated as a delimiter.
- **Row 327 today:** still live. Its supersession is lowercase prose, and no marker exists to cancel.

**Real backlog at this fold:** `row_fates(docs/backlog.md)` returns 434 Items rows and no problems. The fated rows
are 124, 125, 127, 189 and 213 (bare `superseded`) and 405 (`superseded → backlog #481`). That is the same set
Codex measured. No real row is cut by `Previously:` or cancelled by a reopen.

Self-test: 192 → 200 cases. Mutations for `scripts/goal-tree.py`: 102 → 112. Five entries were re-anchored off
the r1 regex and lookbehind, and ten new ones each name their killing case.
