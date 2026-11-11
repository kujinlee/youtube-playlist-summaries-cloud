# Round 1 — backlog-kinds — claude

Subject: branch `backlog-kinds` (PR #442) at `fcc14858`, against `origin/master` (`30234b4c`).
Scratch work: `/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/a6abe358-4c0b-44cb-a058-5446372998ef/scratchpad/r394c/`.
Codex's two findings (row #222's kind; the uncovered invalid-marker fallback) are NOT repeated here.

## Gates run (all on `fcc14858`)

| Command | Result |
|---|---|
| `gen-backlog-page.py --self-test` | 200/200, rc 0 |
| `check-features.py --self-test` | 54/54, rc 0 |
| `check-reference-namespace.py --self-test` | 31/31, rc 0 |
| `check-features.py` | OK, rc 0 |
| `check-docs.py` | OK, rc 0 |
| `check-reference-namespace.py --base origin/master` | OK, rc 0 |
| `check-backlog-closure.py`, `check-doc-citations.py --base origin/master`, `check-goal-status.py`, `check-group-claims.py` | all rc 0 |
| `check-plan-code.py --mutate . --only <each changed script> --allow-long-local` | MUTATION_RESULTS |

## Findings

### M1 — Major — the "same file" rule is false for a DELETED file: its removed lines are credited to the previous file in the diff

`scripts/check-reference-namespace.py` `removed_lines` (added by this branch, `:236-245`) sets `path` only on `+++ b/`. A deleted
file's header is `+++ /dev/null`, so `path` keeps the PREVIOUS file's name and every line the deleted file loses is filed as
removed from THAT file. `marker_only` then exempts an added line in the previous file that matches it.

Input, built with real git in a temp repo (`r394c/g`), using the module's own `added_diff` + `violations`:
- base: `docs/backlog.md` (one row), `docs/backlog.old.md` holding `| 31 | **Gate** see #17 and #18 | x | S | (tooling) | open |`
- worktree: `git rm docs/backlog.old.md`; append that line plus ` ⟦kind: task⟧` to `docs/backlog.md`.
  `git diff` orders `docs/backlog.md` before `docs/backlog.old.md`, so the deletion's `-` line lands under `docs/backlog.md`.
- RAN: `violations(...)` → `[]`. The same diff with the marker removed → **2** violations (control).

So prose that was never in `docs/backlog.md` (and here came from an OUT-of-scope file, `in_scope("docs/backlog.old.md")` is
False) enters a scoped file unjudged, because a marker was appended. That is the "moving a line between files" route the brief
names, and it contradicts the docstring (`:68-76`, "a line the same diff removes from the same file") and the case
`#394: the marker must match a line removed from the SAME file`, which passes only because its other file has a `+++ b/` header —
an ambient reason. A rename-plus-delete split of the backlog (for example archiving closed rows) is the realistic shape.
Fix: key removed lines on the `--- a/` path (or reset `path` on `+++ /dev/null`), and add the deleted-file case.

### m1 — Minor — kind contradicts the row's own text under ruling 3 / ruling 1

Sample: `random.seed(394)`, `random.sample(rows without #222, 25)` over the branch's parsed backlog (350 rows: 234 defect,
83 task, 33 story). Sampled: 43, 47, 53, 96, 101, 107, 109, 115, 120, 126, 130, 172, 183, 189, 195, 208, 219, 251, 260, 303,
330, 342, 359, 365, 378. 23 of 25 agree with their text. Two do not:
- **#195** is `defect`, but its own Item text says *"NOT a defect in the matcher's logic - it is a missing seam"* and
  *"Design question, not a build"*. Missing coverage with no false claim (ruling 3), and a design question (ruling 1) → `task`.
- **#53** is `defect`; its subject is a missing falsifier (*"What is NOT covered: a release built from a stale tree"*) and it
  records that commit drift *"has never yet happened"*. No claim is shown false because of the gap → `task` by ruling 3.
Borderline cases I checked and accept as defect: #29 (a document's coverage claim is false), #99, #139, #219, #260.

### m2 — Minor — parent links are inconsistent across rows with the SAME provenance sentence

#107, #108 and #109 each say *"Residue carried out of backlog #91 (PR #269)"*. Only #107 declares `part of: backlog #91`;
#108 and #109 declare no parent. Either the relation is a parent (add it to #108/#109) or it is not (remove it from #107).
Found by scanning every row for `residue carried out of / split out of / part of / follow-up to … backlog #N` against its
declared parents; the other two hits (#56, #129) are prose, not parentage, and are correctly unparented.

### m3 — Minor — an Item cell cannot QUOTE the marker syntax, even in inline code, and a single such row stops the whole page

`gen-backlog-page.py` `kind_mark` raises `ShapeError` on any `⟦`/`⟧` left in the text, with no inline-code allowance. RAN:
`kind_mark("x `⟦kind: task⟧` prose ⟦kind: task⟧", "9")` → `ShapeError: row 9: a second ⟦…⟧ marker`. `main()` then refuses
the entire page. Row #394 itself had to put its example in the Status cell. A row that documents this grammar (backlog #395's
successors) will hit it. Either state the restriction where the grammar is documented or skip backticked spans.

## The four directions the lead asked for

1. **Kind/parent sample** — above (m1, m2).
2. **Page cards with and without markers.** Parsed the branch backlog with the branch parser, and the same file with every marker
   stripped with master's parser (`git archive origin/master scripts docs`). Over all 350 rows, fields `sev, title, body, section,
   was, touches, size, bundle, status, closed`: **0 differences**. Card HTML, with the branch's kind chip, parent chips and
   `data-kind` attribute removed: **0 of 350 cards differ** from master's. Master's parser on the MARKED text also reads the same
   severity and closure for every row (the marker trails the Item cell, so the leading severity glyph and the Status ✅ are
   untouched). No card loses text, a ✅ or a severity. The single `⟦` that reaches a card is row #394's Status-cell example.
3. **Other readers of `docs/backlog.md`.** `goal-tree.py`, `gen-features-page.py`, `check-features.py` call `gen-backlog-page.parse`
   (marker-aware). `check-backlog-closure.row_markers` reads the Item cell's FIRST character; `check-group-claims.load_rows` reads the
   last cell; `check-docs.py` counts cells — the marker carries no `|` and is trailing, so none is affected, and each ran green.
   The other grep hits (`check-plan-progress`, `check-ci-watched`, `check-review-recorded`, `check-doc-citations`, `page_markup`,
   `explainer-serve`, `check-roadmap-consistency`, `check-goal-status`, the two regen hooks, `.agents/skills/brief`) cite the file
   or regenerate from it; none parses the Item text. No breakage found.
4. **Leak scan / shared `marker_only`.** `marker_only` and `without_kind_marker` have exactly one caller, `violations`. There is no
   standing plan-content leak scan in this tree (backlog #393 is unbuilt), so nothing shares the exemption. ⚠ `marker_only` is not
   limited to `docs/backlog.md`: it applies to every in-scope path whose second cell ends in a valid marker. It only ever exempts
   old prose, so this is wider than the docstring, not a bypass.

Pre-existing, out of this PR's scope, noted once: an ADDED content line reading `++ b/X` renders as `+++ b/X` under
`--unified=0` and re-points `path` in both `violations` and the new `removed_lines`. RAN: `+++ b/README.x` followed by
`+| 9 | see #44 | … |` in `docs/backlog.md` → 0 violations.

## Mutations

MUTATION_DETAIL

## Verdict

NOT CONVERGED — 1 Major (M1), 3 Minor (m1, m2, m3), plus MUTATION_COUNT.
