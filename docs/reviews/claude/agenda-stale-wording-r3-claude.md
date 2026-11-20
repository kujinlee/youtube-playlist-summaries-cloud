Reviewed head: b4ab6f01140d6cb3ccbe9645cef59b9600f9fa39

# agenda-stale-wording — round 3, Claude half

Scope: the round 2 fold, `git diff a22a7b16..b4ab6f01`: the `agenda_facts` docstring in
`scripts/check-stalled-work.py`, backlog row 679 in `docs/backlog.md`, the r2 coordinator doc and a decision-log row.

## What was measured

A probe (scratchpad `r3probe.py`) built a temp remote plus a clone as the main checkout, wrote
`.claude/goal-tree-log.jsonl`, and called `agenda_facts(main)`, goal-tree's `read_log(log)` and
`main(["--repo", main, "--hook"], '{"session_id":"s"}', prs=[])` through `_drive_main`:

| Log | `agenda_facts` | `read_log` | hook stdout |
|---|---|---|---|
| A: `{bad` then `{"goals":[],"at":"2026-01-01"}` | `([], [])` | raises `Malformed: … line 1 is not a snapshot` | `''` (nothing) |
| B: `{bad` then a STALE snapshot (backlog #40 merged after the plan) | `([{'kind':'agenda','subject':'backlog #40 (merged 11-04 10:00)'}], [])` | raises `Malformed` | one block with `STALE-AGENDA  agenda   backlog #40 …` |
| C (control): the STALE snapshot alone | same fact as B | OK | same block as B |
| D (control): `{bad` alone | `([], ['agenda-unread:JSONDecodeError: …'])` | raises `Malformed` | `Nothing is stalled, but one check did NOT run: … stale agenda NOT CHECKED: JSONDecodeError …` |

The page path refuses on `Malformed`: `scripts/goal-tree.py:2934-2937` (`log = read_log(log_path)` /
`except Malformed as exc: print(f"MALFORMED — {exc}"); return 1`).

**The new docstring is TRUE of the code.** "Only the LAST line is read, so a malformed EARLIER line … is not seen
here" — B: the earlier `{bad` changes nothing against C. "When the newest snapshot is clear, the note then says
NOTHING while the page refuses: a SILENT clear" — A: `([], [])`, hook prints `''`, `read_log` raises. The r2 finding's
complaint (the old text said the note still reports the newest snapshot "loudly", false for a clear one) is gone: the
word is removed and the clear case is named.

**No behaviour change.** `ast.dump` of `scripts/check-stalled-work.py` at `a22a7b16` and `b4ab6f01`, with every
docstring blanked, is equal (`True`). The only code file the diff touches is that one.

**Row 679's measured claims are accurate.** The main checkout's log today: `wc -lc` → 328 lines, 20,827,206 bytes
(the row says 328 snapshots, 20.8 MB). `read_log` over it, three runs here: 0.454 s, 0.391 s, 0.645 s (the row says
~0.55 s, three runs 0.54-0.62 s; same order, machine-load variance). `_last_line` alone: 0.0006 s (the row's "~10 ms
for the tail" is the whole tail path, consistent). `agenda_facts` → `([], [])` for the two-line log is reproduced (A).

**Row 679's Fails-if goes red on today's code:** in world A the hook prints nothing — exactly the stated failing
observation. A fix that makes `agenda_facts` return a note for that log would print D's NOT CHECKED block, so it
goes green. ID 679 is unique in the file and absent from `origin/master`; the row is 6 cells like its neighbours;
`gen-backlog-page.py --self-test` 247/247.

`python3 scripts/check-stalled-work.py --self-test` → `252/252 self-test cases passed`.

## Findings

- **MAJOR — `docs/backlog.md:627` (row 679, area column `(dev speed)`).** Input: the fold's backlog →
  `python3 scripts/check-features.py` prints `FAILED — 1 feature-map problem(s): ✗ backlog area \`dev speed\` is
  claimed by no node — its rows cannot appear`. Control: the same check over `a22a7b16:docs/backlog.md` (temp swap,
  restored, `git diff --quiet` clean) → `29 backlog areas all claimed exactly once`. So the fold alone puts CI red
  (`.github/workflows/ci.yml:641` runs `check-features.py`) and row 679 cannot be displayed. `(dev speed)` is used by
  no other row; `docs/features.md` claims `(tooling/hooks)`, `(tooling/pages)`, `(tooling)` etc. The rows naming
  `scripts/check-stalled-work.py` use `(tooling/hooks)` 5×, `(tooling)` 2×, `(tooling/pages)` 1×. Fix: `(tooling/hooks)`
  (the per-message hook is where the defect shows), then re-run `check-features.py` and the full doc-guard list from
  `ci.yml`. Measured. Fix-induced: yes (the row is new in this fold).
- **MINOR — `docs/backlog.md:627` (row 679, Fails-if).** Input: the live repo, where some other line is stalled
  (an open PR, an unpushed tip, an unfolded half — the usual state) plus the two-line log → the hook prints a block
  for the OTHER line, so "`--hook` prints nothing" is false, and the falsifier reads as passing with the defect
  present. The observation only isolates the defect in a world where nothing else is stalled, and it accepts ANY
  output as a fix. Sharper: "with that two-line log and nothing else stalled, `check-stalled-work.py --hook` prints no
  `stale agenda NOT CHECKED` line" (or: `agenda_facts` returns no `agenda-unread` note). Measured (A vs D above;
  the other-stalled case inferred from `hook_block`, which prints whenever any stalled line exists). Fix-induced: yes
  (the row is new in this fold), in a filed row's wording, not code. Non-blocking: amend the sentence in place; it
  needs no further review round.

No BLOCKER. One MAJOR, in the filed row's AREA column, not the code: the docstring, the code and the row's
measurements all agree with what was run. Both findings are one-cell / one-sentence edits to row 679.

## Loosening answers

- The fold changes no code (AST-equal ignoring docstrings), so no gate, check or case is loosened.
- It accepts a known silent clear (row 679) rather than fixing it. That is a documented BOUND with a cost reason
  measured above, filed with a falsifier, not a loosening of an existing check: before the fold the code already
  behaved identically and the docstring overstated it; the fold makes the docstring weaker and TRUE.
- No self-test case was removed or weakened: 252/252 at the head, the same count the r2 Codex half reported.

VERDICT: NOT CONVERGED
