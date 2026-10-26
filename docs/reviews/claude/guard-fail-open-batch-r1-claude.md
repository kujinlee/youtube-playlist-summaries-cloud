# guard-fail-open-batch — round 1, Claude half

Subject: branch `guard-fail-open-batch` at `b7843454` (PR #404), diff `origin/master...HEAD`.
Mandate: refute.

## What I ran

- All four touched `--self-test`s on the branch: ci-watched 84/84, banner-armed 237/237, closing-table
  155/155, handoff-path 15/15, all rc 0.
- The same suites on `origin/master` (from a `git archive` copy): 82, 236, 154, 10.
- I flipped each fix in a mktemp copy and checked that the case naming it went red:
  - `arms_newest_first`: `except FileNotFoundError` changed to `except ZeroDivisionError`. The #253 case
    went `[FAIL]` (83/84). The race case is aimed correctly: the record is unlinked inside `is_file()`,
    after the real check returns True, so `stat()` is the call that raises.
  - `--clear` with no HEAD: removed the `return CANNOT_RUN`. The #255 case went `[FAIL]`.
  - `_parse_records`: changed `isinstance(obj, dict)` to `True`. The #152 case went `[FAIL]` (236/237).
  - The hook: made `*)` exit 0. The "BROKEN interpreter" case went `[FAIL]`, got 0 want 1 (14/15).
- I fed hand-built transcripts to the real `--decide` entry points (results below).

## Findings

### M1 — Medium — #152's class is still open in `check-banner-armed`'s own Stop-hook path, and in `check-transcript-references`. The PR body says otherwise.

`scripts/check-banner-armed.py:1315` (`wins = windows(all_records)`) is called with no handler. The
only `try` at `:1304` catches `OSError` around the read. The new filter at `:295` drops records that
are not objects at the top level. It does nothing for an object record whose `message` is not an object.
That record still reaches `_is_tool_result` (`:539`–`540`, `(rec.get("message") or {}).get("content")`)
and raises. `block-idle-stop.sh:75` runs this script as a Stop hook. Per the #152 row, that hook folds
any non-zero code into exit 1, the warning code.

Executed. The transcript was `{"type":"user","message":{"content":"hi"}}` followed by
`{"type":"user","message":"x"}`:

```
check-banner-armed.py --decide         -> AttributeError: 'str' object has no attribute 'get'   rc=1
check-transcript-references.py --decide -> same traceback (:140)                                rc=1
check-closing-table.py --decide        -> CANNOT RUN: the turn rule raised AttributeError …     rc=2
```

`{"type":"assistant","message":5}` also gives banner-armed rc=1 with `AttributeError: 'int' …`.

So the handler fixed closing-table only. The PR body credits "`check-banner-armed` / `check-closing-table`"
with "a raising turn rule → CANNOT RUN, never exit 1". The dashboard entry says "Each one now says
plainly that it could not run". Neither is true of banner-armed's own `--decide`. The #152 row asked
for exactly this choice: "decide there whether the filter or the handler is the right layer". The PR
chose the filter for banner-armed. The filter only covers the top-level shape, and the row's subject is
"tracebacks out of the Stop hook and reports as a WARNING".

The likelihood is as low as the row's 🟡 rating says. Real transcripts do not do this. The defect is
that the claim is wider than the fix.

Fix, either:
- give `run_decide` in banner-armed (and in transcript-references) the same `except Exception →
  CANNOT RUN` around `windows`/`judged_window`, with a case for each; or
- narrow the PR body and dashboard entry, and file the remaining instances as a row.

### L1 — Low — "10 new cases" is 9.

Measured on master vs branch: ci-watched 82→84 (+2), banner-armed 236→237 (+1), closing-table 154→155
(+1), handoff-path 10→15 (+5). That is 9. The figure "10" appears in the PR body and in
`docs/dashboard-entries.md` (the 2026-10-26 entry). The mutation figure 2105→2109 (+4) checks out:
EXPECTED_MUTATIONS moves +1, +1 and +2.

### L2 — Low — when HEAD is unreadable, `--clear` now also skips tidying the legacy file.

`scripts/check-ci-watched.py`: the early `return CANNOT_RUN` comes before the `legacy = SENTINEL.parent /
"ci-watching"` tidy. Before this change, a HEAD-less `--clear` still removed the pre-directory file. The
read path already ignores that file, so this is harmless. It is an unmentioned behaviour change, though,
and the `head and …` / `(head or '?')` guards below it are now dead. Evidence: code reading only, not
executed.

I searched for callers of `--clear` that depend on a QUIET return. There are none outside the script's
own suite and manifests (`grep -rn -- --clear .claude scripts docs/*.md`). The rc change breaks nothing.

### L3 — Low — a truncated envelope still gives a silent 0.

`.claude/hooks/enforce-handoff-path.sh:36`: the result of `cat > "$TMP"` is not checked. A short or
failed read produces JSON that does not parse, the detector maps that to 3 ("not mine"), and the hook
exits 0. Executed: `printf '{"tool_name": "Skill", "tool_input": {"ski' | bash
.claude/hooks/enforce-handoff-path.sh` gives `rc=0`.

`enforce-selection-card.sh:35` has the same line. This copies the precedent and is not a regression.
"Not JSON → not mine" is a choice both hooks state. I am recording it because the brief asked about
`cat`.

## Checked and found sound

- `mktemp` failure: warns and exits 1.
- `python3` missing (rc 127) or broken: warns and exits 1.
- If the detector passes and the verdict call (`VERDICT_OUT`) then fails, any non-zero code falls
  through to the block, `exit 2`. That fails closed, which is correct for a hook already known to be
  looking at `/handoff`.
- The closing-table `except Exception` wraps only the computation of `judged`, not `decide` or the warn
  path, so it cannot swallow a real WARNING.
- `arms_newest_first` cannot be handed a non-directory. `run_decide` checks `SENTINEL.is_dir()` first,
  and nothing in the script removes the directory.
- In the backlog rows, #253, #255 and #111 describe what was built. #152's ✅ text says "at both
  layers". That is true for closing-table and, per M1, partial for banner-armed.

VERDICT: NOT CONVERGED
