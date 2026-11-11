<!-- codex-review: model=gpt-6.1-sol -->

**NOT CONVERGED**

Reviewed the fold `64cb2e8d..791c4791` first, then the branch against `origin/master`. Findings below reference `791c4791`; later uncommitted edits were left untouched.

1. **High — a worker’s name bypasses the coordinator exception.** `scripts/check-usage-pace.py:345`. **Fix-induced: yes.** Concrete input at weekly 95%:
   ```json
   {"tool_input":{"to":"main [abcdef]","message":"resume work"}}
   ```
   The gate strips the suffix and allows it. Claude 2.1.309’s installed resolver checks exact registered agent names before interpreting `[ref]`. Executing that resolver with `"main [abcdef]"` registered as a worker returned that worker. Thus the report exception can authorize a wake. No live message was sent. **Fix:** validate the resolved recipient’s coordinator identity; do not infer identity from its display-name prefix.

2. **High — a huge integer disables a valid weekly refusal.** `scripts/check-usage-pace.py:156`. **Fix-induced: no; round-1 defect remains.** With `--now 1800000000`, use:
   ```python
   {"at": 1800000000, "rate_limits": {
       "seven_day": {"used_percentage": 95, "resets_at": 1800086400},
       "five_hour": {"used_percentage": 10**400, "resets_at": 1800000100}
   }}
   ```
   Serialize this as JSON. `math.isfinite()` raises `OverflowError` converting the integer. Pinned prompt, spawn, and wake invocations all exited 1 with **empty stdout**: no notice and no denial. **Fix:** handle oversized integers during numeric validation, preserving weekly REFUSE when five-hour validation fails. The decision to preserve weekly refusal is correct; its implementation is incomplete.

3. **High — regular-file reads still have no time bound.** `scripts/check-usage-pace.py:247` and `:257`. **Fix-induced: no; incomplete stall fix.** Concrete fault injection: delay each `os.read` by 1.2 seconds while reading a two-byte regular cache. The checker took **2.4 seconds**. `O_NONBLOCK` and a byte limit do not bound regular-file disk latency; a stuck filesystem can hold the prompt hook until the harness timeout. **Fix:** put the cache read behind an enforceable deadline and return loud CANNOT RUN on timeout. This was a delayed-read simulation, not a physical slow-disk measurement.

4. **Low — hostile-input coverage passes without reaching its advertised target.** `scripts/check-usage-pace.py:642`. **Fix-induced: yes.** In the “TOTAL over hostile seven-day × five-hour resets” case, every seven-day reset is already invalid or expired. Evaluation returns before examining five-hour data. Its green result therefore cannot establish five-hour totality; finding 2 escapes it. **Fix:** cross hostile five-hour values with a valid weekly 95% window.

   A separate measured survivor: at `scripts/check-usage-pace.py:275`, remove `"GIT_WORK_TREE"` from the environment-sanitization tuple. The pinned suite still passes **192/192**. Add independent relocation-variable cases.

Verification:

- Required self-test: **192/192 passed**, also reproduced against a pinned copy.
- Required mutation command: **63/63 killed and attributed, zero survivors**. Its output explicitly calls this a **diagnostic slice, not the full gate**.
- FIFO, directory, and sparse 1 GiB caches returned promptly. Far-future, negative, garbage, and nonfinite override expiries were inactive; an unreadable file returned a permission-error reason. Ordinary model-facing hook fields contained no bypass instructions.
- Plain alternate spellings and `*` were denied. A broadcast-shaped payload carrying `to: "main"` was exempt, but actual broadcast delivery was not established.
- Pinned full prompt-hook timings, 20 runs per level: **141.6 ms median at 50%**, **109.2 ms at 95%**. The claimed **76–94 ms** range did not reproduce.
- No `.claude/plans/` files were read, no `~/.claude` files were modified, and no review file was written.

**NOT CONVERGED**
