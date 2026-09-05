<!-- codex-review: model=gpt-5.5 -->

**Findings**

**Medium** — Failed edit attempts count as “edited a file,” so the new WARN fires when no repo work happened.

Evidence: [edited_paths_of](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-banner-armed.py:142) records `Edit` / `Write` / `NotebookEdit` `tool_use` paths only, and never checks the paired `tool_result` for `is_error` at [lines 149-164](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-banner-armed.py:149). `run_decide()` turns that into `edited` at [line 386](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-banner-armed.py:386), then the new branch warns at [lines 224-239](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-banner-armed.py:224).

I reproduced with a temp transcript: armed plan, 1 unticked step, no banner, `Edit` tool_use followed by `tool_result is_error: true`; the target file did not exist, but `run_decide()` returned `1` and appended `unbannered`. Real transcript schema supports this: scanning this project’s `~/.claude/projects/...jsonl` found `3572` edit tool uses and `31` failed edit results, e.g. `d7a5f5f3-e...jsonl:337` failed an `Edit` on a repo file with `<tool_use_error>Found 2 matches...`.

The same root cause appears in `_edit_inside_repo()`: despite its docstring saying “FILE,” it returns true for an existing directory inside the repo because [lines 349-358](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-banner-armed.py:349) never call `is_file()`. Probe: `_edit_inside_repo([ROOT / "scripts"], ROOT) == True`.

The self-test is vacuous on this point. F4 creates only an `Edit` `tool_use` at [lines 601-606](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-banner-armed.py:601) and asserts only rc/log at [lines 612-616](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-banner-armed.py:612); it would pass for an attempted edit even if the edit failed.

Smallest fix: pair edit `tool_use.id` with later `tool_result.tool_use_id` and count only successful results; also require the resolved path to be a file, or at least not an existing directory. Add self-tests for failed `Edit`, failed `Write` to a directory, and successful edit.

Verified: `python3 scripts/check-banner-armed.py --self-test` passed `55/55`; `bash -n .claude/hooks/block-idle-stop.sh` passed. Hook fixture over all `(BANNER_RC, PLAN_RC, CI_RC)` combinations preserved plan-block precedence and kept CI skipped when plan blocks. Search found no script reader of the changed banner warning log grammar outside this writer/self-test/docs.

VERDICT: NOT CONVERGED
