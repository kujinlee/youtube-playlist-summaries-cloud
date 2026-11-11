Reviewed head: 9dd8ea9967dc0d799a958f426c7d85f4a49dcca8

Claude review half, round 1, subject `agenda-refs-check` (backlog #504). Adversarial: I tried to refute the change.

**Summary.** I found no BLOCKER and no MAJOR. The three fixes (`_ref_ok` and `REF_KINDS` on the log side, `_locked`'s
whitespace truncate, and `_steps_ok`'s list and unique-`n` checks on the snapshot side) close the crashes the row names.
Evidence, each from a command I ran in this worktree:

- **Fuzz of the snapshot readers.** I took the newest real snapshot that has an ok agenda and an `agenda_history` (from
  the main checkout's `.claude/goal-tree-log.jsonl`, 15 steps and 5 history agendas). I mutated 1–3 step fields at
  random (`n`, `state`, `text`, `when`, `detail`, `refs`), using values such as None, ints, bools, strings, `[1]`,
  `["PR"]`, `[["issue",1]]`, `[["PR",True]]`, `[[["PR"],1]]`, `[[{}, 1]]`, dicts, floats and deleted keys. Each mutated
  snapshot went through `snap_agenda`, `snap_history`, `agenda_lines`, `changes()` (against itself and against the
  base) and `render_page([base, s])`. **At HEAD: 0 exceptions in 3,000 snapshots.** The control was the same fuzz on
  `origin/master`'s `goal-tree.py`: 24 `TypeError`s each in `snap_history`, `agenda_lines` and `render_page`, all at
  the old `_steps_ok` line, all from a history `refs` that was not a list. So the fuzz can detect this crash, and the
  change removes it.
- **The writers.** `record_agenda` is the only producer of agenda records (`kind="agenda"`, line 1234). It writes
  `parse_agenda` output, whose refs come from `REF_RE = page_markup.KEY_REF = \b(backlog|PR) #(\d+)\b`. That regex is
  case-sensitive, so a writer emits exactly `"backlog"` and `"PR"`, which equals `REF_KINDS`. `agenda_history()` is the
  only producer of history steps. It copies steps from records that have already passed `_agenda_records`, and gives
  them `n` from `enumerate`, so their `n` values are unique. No other script writes `agenda-log.jsonl` or
  `agenda_history` (grep over `*.py`, `*.sh`, `*.js` and `*.mjs`).
- **Data written before this change is still accepted.** The main checkout's real agenda log (12 records) replays.
  Across 170 real snapshots, `snap_history` refuses 0. One snapshot's agenda reads `malformed`, and it reads
  `malformed` on `origin/master` too, so this change did not cause it. Every ref kind in the real history is
  `backlog` or `PR`.
- **Mutations.** I applied each of the 7 new and 2 re-bound mutations to a TEMP COPY of `scripts/`, never in place.
  Each anchor occurs exactly once. All 9 are KILLED, each by its named `expect` case. The other cases that failed
  under each mutation (1–5 of them) were all expected. `goal-tree.json` holds 305 entries, which equals the
  `EXPECTED_MUTATIONS` pin.

## Findings

**F1 — MINOR — the case "the known ref kinds are exactly the kinds the step grammar writes" cannot catch the drift it names.**
The case runs `REF_RE.findall("backlog #1 · PR #2")` on a fixed string. That string contains only the two kinds already
known, so a new kind added to the grammar never reaches it.
Concrete failing input: in a temp copy, I changed `page_markup.KEY_REF` to `\b(backlog|PR|issue) #(\d+)\b`.
- `--self-test` still reports **404/404 passed**.
- In that copy, `parse_agenda("window: w\n## today\n- issue #3 · a\n")` followed by `record_agenda` and a read raises
  `Malformed … an agenda step's refs are [kind, number] pairs of a known kind (backlog #504)`.

So the writer produces a log that its own reader refuses, and the agenda block then reads MALFORMED. The guard case
stays green the whole time. This is latent: it needs a future edit to `KEY_REF`, which lives in a different file
(`page_markup.py`).
Fix: derive `REF_KINDS` from `KEY_REF`'s alternation group, or make the case assert on that group. For example:
`re.search(r"\(([^()]*)\)", REF_RE.pattern).group(1).split("|") == list(REF_KINDS)`. Either version reads the
grammar itself rather than a sample of its output.

**F2 — MINOR — a whitespace last line after a record still leaves a blank line.**
The truncate covers only a log that is entirely whitespace. Take a log that is `<record>\n` followed by `"   "` (spaces,
no final newline). `_locked` sees non-empty text with no final `\n`, so it appends `\n`. On disk the lines become
`[<record>, '   ', <replaced>, <agenda>, '']`. I reproduced this with `record_agenda` twice in a scratch file. Replay
ignores the blank line (`read_agenda_log` returns 3 records), so nothing crashes. It is the same cosmetic Low class
as the row's own Low, in a shape the row did not name.
Fix (optional): replace the whitespace-only special case with one general step. Strip trailing whitespace from `text`
(truncate to `len(text.rstrip())`), then add the `\n` repair. That covers both the whitespace-only log and this one.
Otherwise, file it.

Checked and not a finding:
- `_ref_ok` with an unhashable kind (a list or dict) cannot raise: `x in tuple` compares with `==`, it does not hash.
- The unique-`n` set comprehension only runs after `all(...)` has proved every `st["n"]` is an int.
- `"refs": None` in a history step was accepted before (`or []`) and is now refused. No writer produces it, and 0 real
  snapshots carry it.
- The truncate runs even when `write()` later refuses (for example, ticking with no agenda). It only empties a log
  that was already whitespace, so it changes nothing that matters.
- The `"a+"` handle plus `truncate(0)` works on this platform. The new case proves it: the file ends with 1 newline
  and starts with `{`.

`python3 scripts/goal-tree.py --self-test` → `404/404 self-test cases passed`

VERDICT: CONVERGED
