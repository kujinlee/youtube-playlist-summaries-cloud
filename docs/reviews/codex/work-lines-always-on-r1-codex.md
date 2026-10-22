<!-- codex-review: model=gpt-6.1-sol -->

1. **Major — stale records can assert the wrong parent.** [scripts/begin-plan.py:508](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/begin-plan.py:508)

   The reader verifies only that the recorded path exists, then asks about its recorded branch. It never checks whether that file still represents the finished plan.

   **Executed in a temporary copy:** recorded `old.md`, replaced its contents with an unfinished plan, and supplied an OPEN PR response. `_parent_from_last_finished()` still returned `old`. A separate probe made recording a newly finished `new.md` fail with `PermissionError`; the older record survived and the next parent lookup again returned `old`.

   **Fix:** record and validate a plan identity or content fingerprint and repository/PR identity. When recording fails, invalidate the previous record or otherwise prevent it from silently standing in for the newly finished plan. Add replacement-file and failed-record regression cases.

2. **Major — the PR query can incorrectly conclude that a line ended.** [scripts/begin-plan.py:458](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/begin-plan.py:458)

   `gh pr list --state all` defaults to **30 results**. Seeing no OPEN entry in that bounded response does not establish that none exists. The default is confirmed by installed `gh --help` and the [official CLI manual](https://cli.github.com/manual/gh_pr_list).

   **Executed with an injected runner modeling that limit:** 30 merged PRs followed by an older open PR produced:
   ```
   ('ended', '30 PR(s), none open')
   ```
   The caller consequently writes `parent: -`. **UNVERIFIED against live GitHub:** the ordering scenario was simulated.

   The `_gh_world` fixture returns every matching PR, so it misses this real CLI constraint.

   **Fix:** query OPEN PRs directly first; if none exist, separately check whether any ended PR exists. Test a branch with more than 30 historical PRs.

3. **Major — the new recording path can turn an allowed Stop into a blocking crash.** [scripts/check-plan-progress.py:469](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-progress.py:469)

   Both `current_branch(ROOT)` and `record_last_plan(...)` execute without a boundary protecting the already-computed verdict.

   **Executed in temporary copies:**
   - A fault-injected recorder raised `RuntimeError`; `run_decide(False)` propagated it and retained the sentinel.
   - A fake `git` executable emitted `b"feat/\\xff\\n"`. The actual subprocess decoder raised:
     ```
     UnicodeDecodeError 'utf-8' codec can't decode byte 0xff in position 5
     ```
     The sentinel remained. `current_branch` catches `OSError` and `SubprocessError`, but not decoding errors.

   An uncaught exception exits 1; the hook wrapper treats that as a blocking failure. The previous completed-plan path delivered ALLOW.

   **Fix:** protect the entire optional recording operation, including branch discovery, so failures cannot prevent sentinel clearing or delivery of the original message and return code. Add exception-injection tests at both calls.

4. **Minor — human words are interpolated into Markdown without escaping.** [scripts/begin-plan.py:328](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/begin-plan.py:328)

   **Executed:** an objective containing `ship **bold** and [click](https://example.com)` produced:
   ```
   > **Line:** "ship **bold** and [click](https://example.com)" → `r`
   ```
   Markdown readers interpret the words as formatting and a link. Quotes around the objective do not preserve literal text.

   **Fix:** escape Markdown metacharacters after truncation, and test formatting characters, backticks, and HTML.

Validation: isolated self-tests passed **104/104**, **54/54**, **40/40**, and **203/203**. A rebuild over copies of **123 plans took approximately 122 ms**. Rebuilding is synchronous on every `--tick`, including refusals, but contains no `gh` call. Parent lookup can wait up to 30 seconds when creating a new plan with nothing armed and a usable last-plan record. All test writes used temporary directories and redirected outputs.

VERDICT: NOT CONVERGED
