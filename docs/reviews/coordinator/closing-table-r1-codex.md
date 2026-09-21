<!-- codex-review: model=gpt-5.5 -->

**Findings**

**Blocking** — Mutation evidence is not honest for this guard. In [scripts/check-closing-table.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-closing-table.py:340), failures are printed as `  ✗ ...`, but `check-plan-code.run_mutations()` only attributes kills from lines beginning `[FAIL] `. Running the 10 declared mutations showed 9 red-but-unattributable mutations and 1 survivor. The survivor is the manifest entry “a table row no longer has to close with a pipe...”; its named case still passes after the edit because `_cells()` then chops the final `t` from `result`, so the mutated behavior is not exercised. This directly falsifies “10 mutations” as usable evidence.

**High** — Tool-only closing turns fail open. [decide()](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-closing-table.py:251) returns `QUIET` when `final_text is None`, even if the judged turn successfully ran `git push`. Concrete transcript:

```json
{"type":"user","message":{"role":"user","content":"do it"}}
{"type":"assistant","message":{"content":[{"type":"tool_use","id":"t1","name":"Bash","input":{"command":"git push"}}]}}
{"type":"user","message":{"role":"user","content":"next"}}
{"type":"assistant","message":{"content":[{"type":"text","text":"working"}]}}
```

`check-closing-table.py --decide` returns `0` with no stderr. That is not “partway” in the guard’s own trigger model: the job-closing act completed, and no CHECK / RESULT table exists.

**High** — The trigger is lexical, so it both misses real closes and fires on non-closes. In [CLOSING_ACTS](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-closing-table.py:110), these real close spellings are missed:

```bash
git -C /tmp/repo push
alias g=git; g push
python3 - <<'PY'
import subprocess
subprocess.run(["git", "push"])
PY
```

And these non-closes fire:

```bash
grep -R "git push" docs
printf %s "git push"
cat <<EOF
git push
EOF
git push --dry-run
git push --help
gh pr merge --help
```

Skipping `is_error` is directionally reasonable for refused hooks, but not complete: a `git push` can update one ref and fail another, or push commits and fail post-push cleanup/reporting. Treating any paired `is_error: true` as “no close happened” can hide partial success.

**Medium** — The marker accepts non-tables and rejects some human-readable tables. [has_closing_table()](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-closing-table.py:137) accepts this code fence as a closing table:

```markdown
```
| check | result |
|---|---|
not a closing table
```
```

It also accepts a header/separator with no claim rows. Conversely, it rejects an HTML table with `Check` and `Result` headers:

```html
<table><tr><th>Check</th><th>Result</th></tr><tr><td>tests</td><td>pass</td></tr></table>
```

I would not count alternate wording like `Evidence | Status` as a defect: [docs/process-checklists.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/process-checklists.md:459) specifically names a `CHECK / RESULT` table and shows `check` / `result`.

**Medium** — The hook ordering comment is wrong for this guard. In [.claude/hooks/block-idle-stop.sh](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/hooks/block-idle-stop.sh:128), the comment says a blocked stop is unfinished, so no closing table is owed. But this guard judges the previous completed turn, not the blocked live turn. If the previous turn missed a required table and the current stop is blocked by `check-plan-progress`, the new observer never runs and the one-turn-late warning is skipped.

**Medium** — Borrowing `check-banner-armed.py` is a semantic dependency, not just a symbol dependency. [_load_banner_guard()](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-closing-table.py:160) only checks that `_parse_records`, `windows`, `judged_window`, and `texts_of` exist. If `judged_window()` changes from “previous completed turn” to “live turn” without renaming, this guard silently changes subject. The `hasattr` sweep catches removals only; it is not load-bearing for semantics. Also, the second `_load_banner_guard()` call in [run_decide()](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-closing-table.py:319) is not caught, so an import failure there escapes as a traceback/exit 1, not the documented `CANNOT_RUN` exit 2. Calling it twice is not a correctness problem when stable; it is small cost plus an avoidable second failure site.

**Low** — Logging is claimed more strongly than implemented. The docstring says every firing is appended to a log, and [decide()](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-closing-table.py:264) tells the user “it is appended.” But [_append_log()](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-closing-table.py:275) returns `False` on `OSError`, and [run_decide()](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-closing-table.py:329) ignores that. With `WARN_LOG=/dev/null/x`, `_append_log()` returns `False` while the warning still says it was appended.

**Bounds Check**

The stated bounds are incomplete. Add at least: final session turns may never be judged, blocked next stops skip the observer, command spellings through `git -C`/aliases/scripts are invisible, literal command text in read-only shell commands causes false warnings, code fences can satisfy the marker, no-text closing turns pass quietly, parser semantic drift is unchecked, and log write failure is hidden.

The TABLE_RC exit folding itself is correct when reached: [.claude/hooks/block-idle-stop.sh](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/hooks/block-idle-stop.sh:148) maps any non-zero observer result, including `2`, to hook exit `1`, not blocking `2`.
