<!-- codex-review: model=gpt-6.1-sol -->

1. **Major — a partial clear loses the finished plan and exposes an older parent.** `scripts/check-plan-progress.py:595–603`

   **Executed in a temporary copy:** an older valid `.claude/last-plan` named `old`; the sentinel named fully-ticked `new`; `.claude/executing-plan.state` was a directory, making its unlink fail.

   ```
   STOP PermissionError
   sentinel exists False
   NEXT PARENT old
   ```

   The sentinel is deleted before state cleanup and recording. When state cleanup raises, recording never runs; the sentinel’s saved identity disappears with the process. A subsequent Stop returns 0 because nothing is armed. With the same session and an injected OPEN response, the next parent lookup selects `old`.

   **Fix:** run the protected recorder before deleting either file, while keeping mandatory clear failures outside `run_optional`. Add a partial-clear regression case.

2. **Minor — a recorder exception also suppresses the independent page rebuild.** `scripts/check-plan-progress.py:601`

   Both operations share one sequential expression:

   ```python
   lambda: (record_last_plan(...), refresh_work_lines(...))
   ```

   **Executed:** injected a raising recorder and a rebuild spy:

   ```
   RAISING RECORDER RC 0 CALLS ['record']
   ```

   The verdict survives, but the rebuild never runs after the successful clear.

   **Fix:** give recording and rebuilding separate `run_optional` calls. Assert that rebuilding happens when recording raises.

3. **Minor — the second PR answer can explicitly contain OPEN and still produce “ended.”** `scripts/begin-plan.py:529–534`

   A PR can open or reopen between the two requests.

   **Executed with an injected runner:** OPEN query returned `[]`; ALL query returned `[{"state":"OPEN"}]`.

   ```
   ('ended', 'PRs exist for it and none is open')
   ```

   The caller consequently starts a new line despite receiving positive OPEN evidence. **UNVERIFIED against live GitHub:** the intervening state change was simulated.

   **Fix:** recognize OPEN in the second response before returning `ended`; add a changing-response fixture.

4. **Minor — `md_literal` still permits formatting and entity interpretation.** `scripts/begin-plan.py:280–293`

   **Executed using the installed `markdown-it` renderer:** objectives passed through `md_literal` produced:

   ```
   ship ~~deleted~~  → ship <s>deleted</s>
   a &copy; b       → a © b
   ```

   Neither `~` nor `&` is escaped, so the displayed objective differs from the supplied words. A pipe is harmless in the current blockquote paragraph; backslash handling correctly escapes the original backslash first.

   **Fix:** escape all ASCII punctuation supported by Markdown backslash escaping, including `~` and `&`, and test rendered text.

5. **Minor — two “branch lookup that RAISES” cases never invoke that lookup.** `scripts/check-plan-progress.py:987–1001`; `scripts/begin-plan.py:1655–1670`

   The clear paths now copy the sentinel’s branch and never call `current_branch`.

   **Executed with a raising lookup and call counter:**

   ```
   STOP branch calls []
   FINISH branch calls []
   ```

   Those cases pass without exercising their named exception.

   **Fix:** rename them to assert that clearing never queries the current branch, and explicitly assert zero calls. Retain exception coverage at ARM time.

Validation: self-tests passed **118/118**, **63/63**, **40/40**, and **203/203**. All **27 changed mutation entries** failed at every expected case label. Legacy records without `session:` returned no parent and made no PR query. UTF-8/CRLF fingerprints matched between recording and reading. An errored first PR query returns immediately without asking the second question.

VERDICT: NOT CONVERGED
