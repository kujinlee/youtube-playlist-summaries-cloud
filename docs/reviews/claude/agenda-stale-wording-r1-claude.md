# agenda-stale-wording r1 — Claude half

PR #603, branch `agenda-stale-wording`, HEAD 77337ca4, diff `7a6ffa00..HEAD`. Read-only review (this file is the only write).

## Commands run (last lines)

- `python3 scripts/check-stalled-work.py --self-test`, rc 0: `239/239 self-test cases passed` (18 s)
- `python3 scripts/goal-tree.py --self-test`: `538/538 self-test cases passed` (4 s)
- `python3 scripts/check-docs.py`: `Documentation integrity OK` (ADR advisory only)

## What I tried to refute, and what happened

- **Page and note disagree on a late merge.** `agenda_late` slices goal-tree's own `agenda_context` "stale" line between
  `AGENDA_STALE_HEAD` and `AGENDA_STALE_TAIL`, and `agenda_html` renders that same list (goal-tree.py `for kind_, text in
  agenda_context(snap, ag)`). A late merge cannot be reported by one and missed by the other. HELD. One other kind of
  disagreement remains (MINOR 1).
- **Missing, malformed or empty log.** I called `agenda_facts` on a copy of the real 20 MB log (outside the repo) and on
  crafted ones. Real log: `([], [])` in 10 ms. Each crafted log was a NOTE: `b""`, blank lines and `\xff\xfe` give
  JSONDecodeError or UnicodeDecodeError; `[]` gives "its last line is not a snapshot"; `{"agenda":{"malformed":…}}`
  and `{"agenda":{"id":1}}` give "agenda is malformed"; a missing file gives `agenda-no-log`. A snapshot with no
  `agenda` key, or `agenda: null`, is a silent clear. That matches `snap_agenda`'s "absent"/"none", and the page shows
  "none recorded" without a warning, so the two still agree. HELD at the `agenda_facts`/`note_lines` level and in the
  CLI. **REFUTED in the hook** (MAJOR 1). I tested the function and not the hook, and found this only after reading Codex.
- **Time bound and repo writes.** Loading goal-tree.py in-process takes 71 ms and the tail read 10 ms. That work runs
  outside `Budget`, but it is local and fast. The load writes `scripts/__pycache__/goal-tree.cpython-314.pyc`, which is
  gitignored (`.gitignore:73 __pycache__/`), and session-state's loader already wrote files there. Nothing tracked is
  written. A `SystemExit` raised while goal-tree loads gets past `except Exception`, but then `stalled-work.sh` prints
  its framed CANNOT RUN, so it stays loud. HELD.
- **Mutations bind and go red.** I ran every manifest entry on a `git archive` copy outside the repo. 10 entries in
  `check-stalled-work.json` contain #647 or STALE-AGENDA: KILLED 10/10. The 2 new `goal-tree.json` entries: KILLED 2/2.
  I also made three mutations of my own: `every_tree[0]`→`[-1]` went red; dropping `agenda-unread:` from `note_lines`
  was KILLED; removing the note's who-acts tail was KILLED.

## Findings

- **MAJOR — scripts/check-stalled-work.py:752 (`hook_block`):** in the hook, a missing or unreadable goal-tree log is a
  SILENT pass. `hook_block` returns `None` whenever `rc != STALLED_RC`, so the `stale agenda NOT CHECKED` NOTE prints
  only when some other item is already stalled. Input: `--hook` over a checkout with nothing stalled and no
  `.claude/goal-tree-log.jsonl`, or with `{bad` as its last line. Observed from the code: `render` returns CLEAR, then
  `hook_block` returns None, and nothing is printed. The new cases test the NOTE through `agenda_facts`/`note_lines`
  only, never through `hook_block`, so no case goes red. The per-message hook is the channel #647 exists for, and
  this breaks the "fails loudly" requirement. Codex reported this first (its MAJOR at :751); I confirmed it by reading
  `hook_block`. Fix: let an `agenda-*` note on its own reach the hook block, with a hook-level case.
- **MINOR — scripts/check-stalled-work.py:670 (`agenda_facts`):** the note checks only the LAST line, but the page's
  log reader validates every line. Codex's input was `{bad` followed by a valid stale snapshot. Observed (Codex): the
  hook says STALE-AGENDA while the page refuses the log. That breaks "cannot disagree", though in the loud direction.
  I agree with the finding and grade it MINOR, because the user still gets a signal.

- **MINOR — scripts/check-stalled-work.py:635 (`agenda_late`):** the docstring and the backlog #647 row both say "the
  two cannot disagree", but the note reads only the late-merge STALE line. `agenda_context` also produces a second
  `stale` line, `⚠ every step is done — the plan is finished. Record the next one.`, and the page renders it as
  `<p class="warn">`. Input: a snapshot whose agenda's steps are all `merged` and that has no late merges. Observed:
  the page warns, `agenda_late(...) is None`, and the note says nothing. This is the same "someone has to trigger the
  work" case the owner raised on 11-17, and the line also does not say who acts. Fix: report both, or narrow the
  claim to "a late merge".
- **MINOR — scripts/check-stalled-work.py:12-75 (module header):** the header still lists "THE THREE SIGNALS" and a
  CAP ordering with no agenda signal. It also does not state the bound: the note reads the NEWEST LOGGED goal-tree
  snapshot, not live master. Input: a merge lands on master after the last goal-tree build. Observed: no snapshot
  holds the merge, so neither the page nor the note shows it until the next build. The page has the same limit, but
  this is the bound #647's "Fails if" turns on ("an agenda older than a merge it does not name produces no line"), so
  it should be written down.
- **MINOR — scripts/check-stalled-work.py (self-test, `collect` wiring):** no case pins `every_tree[0]` as the main
  checkout. The end-to-end case uses a checkout with one worktree. My `[-1]` mutation went red, but on some other
  case, not on the end-to-end one. If `[0]` regressed in a repo with linked worktrees, the hook would print the loud
  `agenda-no-log` NOTE, so it fails loud. No manifest entry carries this.

## Agreement with Codex

I wrote the three MINORs at the end before reading Codex. After reading it I added the MAJOR and the MINOR at :670,
both Codex's. Its bytecode MINOR overlaps my "repo writes" check. I grade that one as not a defect: the files go to
gitignored `__pycache__/`, which session-state's loader already writes. My MINOR 1 (the "every step is done" line is
missing from the note) is not in Codex's review.

VERDICT: NOT CONVERGED
