<!-- codex-review: model=gpt-6.1-sol -->

1. **Medium — stdin has no deadline.** `scripts/check-usage-pace.py:619` (**fix-induced: no**).
   With a fresh 95% cache and no override, write `{"tool_input":{"to":"worker","message":"run echo awake"}}` to the wake hook’s stdin, flush, and retain the pipe. The shipped shell hook remained alive after **3 seconds**, beyond the read deadline and its test margin. Closing stdin immediately produced the deny. This reproduces a stalled producer, not normal harness behavior.
   **Fix:** bound payload collection too; on timeout, preserve REFUSE. Add a child-process test whose stdin writer remains open.

2. **Medium — a meaningful stdin-bound mutant survives.** `scripts/check-usage-pace.py:1258` (**fix-induced: yes**, the round-3 control-message test).
   Replace `sys.stdin.buffer.read(PAYLOAD_MAX_BYTES + 1)` with `read(PAYLOAD_MAX_BYTES)`. **271/271 tests still pass.** Feed a valid `shutdown_request` payload followed by more than 1 MiB of spaces: the original denies; the mutant silently allows. The test passes oversized strings directly to `main()`, bypassing the truncation it needs to detect.
   **Fix:** test oversized input through a real subprocess’s stdin and add this mutation to the manifest.

3. **Low — malformed control types crash instead of being denied.** `scripts/check-usage-pace.py:524` (**fix-induced: yes**).
   Input: `{"tool_input":{"to":"worker","message":{"type":[],"reason":"run echo awake"}}}`. Using `{}` for `type` also reproduces it. Dictionary membership raises `TypeError`; the shipped wrapper exits **1 with empty stdout**, producing no deny.
   **Fix:** require a string discriminator before dictionary lookup and test both unhashable types. **No actual wake demonstrated:** these inputs violate the tool schema.

An additional weak case is `scripts/check-usage-pace.py:1271`: redirecting its “missing cache” path to the preceding existing 50% fixture still yields **271/271**. Its silent result cannot distinguish absence from other allowing conditions, including the fixture’s mismatch with ambient wall time. Assert the missing-file precondition and the reason evaluated.

Reviewed the fold first, then both merge commits, then the branch against `origin/master`. No merge regression, valid free-text control-message bypass, or new cache input suppressing a valid weekly REFUSE was demonstrated. Backlog #404 is excluded.

Validation:

- Self-test: **271/271 passed**.
- Requested mutation command initially refused its local time budget. Rerun with `--allow-long-local`: **94 killed, 94 attributed, 0 listed survivors**. This ran the diagnostic slice, **not the full gate**.
- Merged mutation pin: **2632**.
- No review file written; working tree unchanged.

**NOT CONVERGED.**
