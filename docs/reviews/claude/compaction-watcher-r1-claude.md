Reviewed head: 2d69761cf82669fce479bd46f4b556a4941a6178

# compaction-watcher — round 1, Claude half (adversarial)

Subject: `git diff origin/master...HEAD`, which covers `scripts/check-compaction-boundary.py`,
`scripts/mutations/check-compaction-boundary.json` and `scripts/check-plan-code.py`, plus docs rows.
The diff adds `question_watcher` and `WATCHER_RE`. It exempts the explainer question watcher from the
`monitor` signal (backlog #537).

## What I measured, and what held

- **`--self-test`:** 87/87 passed in the worktree.
- **Missed-exemption claim, re-measured independently.** I wrote my own extractor over
  `~/.claude/projects/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/*.jsonl`. It found 22 files
  and 356 Monitor tool_use commands.
  - 141 commands mention `questions.md`; `question_watcher` matches 141 of 141.
  - It matches 0 of the 215 others.
  - The claim holds. The live shapes are:
    - 137× `tail -n 0 -F ~/explainers/questions.md 2>/dev/null | awk …`
    - 2× `-n0` with no redirect
    - 1× `2>&1` with an absolute path
    - 1× `~` with `2>&1`
  - Bound: top-level `*.jsonl` only. Subagent transcripts under subdirectories were not scanned.
- **The fix does what the defect needs, replayed against the real session.** I replayed
  `f7c144b8-1b6c-4db3-8ef1-932d4e701b12.jsonl` with the new code. I truncated it at each `block-monitor` offer in
  `.claude/compaction-boundary.log`: 11:00:34, 11:01:53, 11:04:48 and 11:07:37.
  - At every offer, `signals()` is now `[]`.
  - The only live monitor at every offer is `toolu_01CuG3we1BSZp9GpbNVesbcm`, with `watcher=True`.
  - The log carries no `plan` or `agent` signal on those rows, so nothing else would have held them.
- **Interaction with the other signals.** The change is confined to the `monitor` term of `signals()` (line 279).
  - The `plan` and `agent` branches are untouched.
  - `decide()` still tests the ceiling first.
  - A CI monitor beside the watcher still blocks. This is tested and mutation-pinned.
  - No regression found.
- **The 8 new mutations, re-run by hand.** `check-plan-code.py --mutate . --only …` printed CANNOT RUN in this
  worktree (no `node_modules/typescript`), so I treated it as NOT RUN.
  - Instead I applied each manifest edit to a copy and ran `--self-test`. All 8 were KILLED by their named
    `expect` cases.
  - In that copy, 11 location-dependent `hook:` cases fail even with no mutation. I excluded them, and no
    watcher case is among them.

## Findings

### F1 — MINOR — chaining bypasses: the "nothing chained outside quotes" claim is false
`scripts/check-compaction-boundary.py:128` (`CHAINED_RE`), `:271` (quote strip), docstring `:52-55`, comment `:123-125`.

The docstring says the rule requires "nothing chained outside quotes". The comment at `:124` adds "so a later stage
can only filter". `CHAINED_RE` covers only `;`, `&&`, `||`, `$(` and a backtick. The following real commands
return `question_watcher(...) == True`, so they are exempt from the `monitor` signal while they run unrelated
long work:

| Command | Bypass |
|---|---|
| `tail -n 0 -F ~/explainers/questions.md \| cat & gh run watch 123 --exit-status` | background `&` |
| `tail -n 0 -F ~/explainers/questions.md \| cat⏎gh run watch 123` | newline as a separator |
| `tail -n 0 -F ~/explainers/questions.md \| tee >(gh run watch 123)` | process substitution, which starts at once |
| `tail -F ~/explainers/questions.md \| grep "it's" ; gh run watch 1 ; echo "'"` | `'` inside double quotes: the strip removes the span that holds the real `;` |
| `tail -F ~/explainers/questions.md \|& cat` | harmless, but shows `\|&` is unconsidered |

- **Verified in bash:** `tail -n 0 -F /dev/null | cat & echo CHAINED-RAN` prints `CHAINED-RAN` immediately.
- **Failure scenario:** a combined monitor such as "watch for questions AND for CI" is exempt. Auto-compaction then
  fires mid-CI-wait, which is the defect class #440 exists for.
- **Severity bound:** 0 of 356 live commands take any of these shapes. The ceiling and the snapshot still apply.
  So it is MINOR, but the docstring states a property the code does not have.
- **Fix, either way:**
  - Restate the bound honestly in the docstring.
  - Or add `&` that is not part of `>&`/`2>&1`, `\n`, `<(` and `>(` to `CHAINED_RE`. Then strip quotes in a way that
    respects double quotes, or reject any `"` that contains `'`.
  - ⚠ A naive `&` would break the 2 live `2>&1` shapes.

### F2 — MINOR — test strength: 4 further mutants of the new rule survive the suite
`scripts/check-compaction-boundary.py:126-128,270-271`; cases at `:714-727`.

Each mutant was applied to a copy and run under `--self-test`. Excluding the 11 location-dependent `hook:` cases,
which fail on the unmutated copy too, each produced zero new failures, so all four SURVIVE:

| # | Mutant | Why it survives |
|---|---|---|
| 1 | `CHAINED_RE = re.compile(r";")` | Drops `&&`, `\|\|`, `$(` and backtick. No negative case has `\|\|`, `$(` or a backtick after a valid watcher prefix. The one `&&` negative (`gh run watch 1 && tail -F …`) already fails `WATCHER_RE`, so it masks the `&&` alternative (two clauses answer it). |
| 2 | Terminator `(?:\|\|\Z)` → `(?:\|\|\Z\|&)` | Admits `tail -F …questions.md & gh run watch 1`. |
| 3 | Quote strip `'[^']*'` → greedy `'.*'` | Would hide `; gh …` between two single-quoted args. |
| 4 | `WATCHER_RE.match` → `.search` | "Not the FIRST stage" is pinned only by the `&&` negative, which `CHAINED_RE` also rejects. |

- **Failure scenario:** a later edit weakens the chaining test or the first-stage anchor, and the suite stays green.
  The 8 manifest mutations do not cover these clauses.
- **Fix:** add one ADJACENT negative per clause. Each should be a valid watcher prefix followed by:
  - `|| gh run watch 1`
  - `$(gh run watch 1)`
  - a backtick form
  - `| grep 'a'; gh run watch 1; echo 'b'` (pins the non-greedy strip)

  Also add a first-stage negative that has no chaining token, such as `echo hi | tail -F ~/explainers/questions.md`.
  Then add manifest entries for mutants 1-4.

### F3 — NIT — the docstring's offer count undercounts the measured log
`scripts/check-compaction-boundary.py:55-56`.

- The docstring says the watcher "held all 3 offers of 2026-11-06 11:00-11:05 (238k-241k)".
- `.claude/compaction-boundary.log` has **4** `block-monitor` rows for this session: 11:00:34, 11:01:53, 11:04:48 and
  11:07:37. Their ctx runs from 237,702 to 247,039.
- My replay shows all 4 were the watcher alone.
- Fix the number, or cite the log as the source.

## Not reviewed

- `docs/` rows: backlog, dashboard entry, goal-threads.
- The `check-plan-code.py` count bump (47 → 55): I checked only that it equals 47 + 8.
- The real mutation harness was not run (CANNOT RUN, above).

VERDICT: NOT CONVERGED
