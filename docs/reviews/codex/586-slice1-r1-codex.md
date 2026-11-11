<!-- codex-review: model=gpt-6.1-sol -->

1. **High — `scripts/strace-measure.py:168`: `O_CREAT` does not prove a path was created.**  
   Executed input:
   ```text
   1 openat(AT_FDCWD</copy>, "/external/existing", O_CREAT|O_WRONLY, 0600) = 3</external/existing>
   1 unlink("/external/existing") = 0
   ```
   Result: `external_removals=[]`. The open can succeed on a pre-existing file, so the subsequent deletion is incorrectly exempted.  
   **Proposed fix:** require evidence of creation, such as successful `O_CREAT|O_EXCL`; otherwise retain the path as potentially pre-existing.

2. **Medium — `scripts/strace-measure.py:160–166`: failed renames mark their destination as created.**  
   Executed input:
   ```text
   1 renameat(3</external>, "absent", 3</external>, "existing") = -1 ENOENT (No such file or directory)
   1 unlinkat(3</external>, "existing", 0) = 0
   ```
   The failed rename adds `/external/existing` to `created`, suppressing the subsequent successful unlink. Both rename destination additions occur outside `if ok:`.  
   **Proposed fix:** record destinations only after successful renames, and distinguish newly created directories from other paths when exempting descendants.

3. **Medium — `scripts/strace-measure.py:283`: return matching searches inside quoted arguments.**  
   Executed input:
   ```text
   1 openat(AT_FDCWD</copy>, "/external/) = 7", O_CREAT|O_WRONLY, 0600) = -1 EACCES (Permission denied)
   1 unlink("/external/) = 7") = 0
   ```
   Result: `external_removals=[]`. `RETURN.search(body)` matches `) = 7` inside the filename, treats the failed open as successful, and exempts the deletion.  
   **Proposed fix:** parse the return only after the matching, unquoted closing parenthesis identified by the argument scanner.

4. **Medium — `scripts/strace-measure.py:254–272`: resumed argument tails are silently discarded.**  
   Executed constructed input:
   ```text
   1 ioctl(3</dev/tty>, <unfinished ...>
   1 <... ioctl resumed>TCGETS, 0x123) = 0
   ```
   Result: `syscalls={"ioctl":2}`, `ioctls={}`, `unparsed_lines=[]`. Similarly, a removal whose path is in the resumed tail produces neither an external-removal entry nor an unresolved-removal entry. The comment that unfinished arguments are always whole is not enforced.  
   **Proposed fix:** join unfinished/resumed calls by PID before interpreting arguments and results; report incomplete pairs explicitly. This demonstrates an instrument gap, not evidence that this run’s seven-token union is wrong.

5. **Medium — `scripts/strace-measure.py:457,482`: rounding before taking the ceiling can understate `TRACE_FACTOR`.**  
   Executed synthetic merge with a spawner taking `10` seconds plain and `200.01` seconds traced. The driver emitted **20**; the required ceiling of `20.001` is **21**.  
   **Proposed fix:** choose the maximum using unrounded ratios and apply `ceil` directly; round only for display. The committed run’s factor **20** remains correct.

6. **Medium — `docs/reviews/measurements/2026-11-10-strace-on-runner.md:94–96`: the recording budget incorrectly halves elapsed time.**  
   The committed JSON’s 184 ratio records sum to **1,595.36 seconds traced** and **472.84 seconds plain**. Therefore the stated **1,300–1,400 seconds traced work** understates already measured traced execution time, before staging overhead. Halving the number of executions does not halve elapsed time when tracing causes substantial slowdown.  
   **Proposed fix:** use the traced-duration sum as the measured baseline and account separately for staging overhead.

Validation: re-merging the six locally available original shards exactly reproduced the committed JSON, excluding the separately supplied `jobs` field. The documented syscall counts match that JSON. The spike reduction matches its original source; historical `today` selections match `d206e066`; the 47/33/three-reader counts hold. Sample lines match original artifacts after trimming; whole-log differences are explained by documented path shortening, including truncated argv paths. Each fixture names its run. Generic `/home/runner/...` paths remain in `whole-git.log`; no secret was identified.

No gate loosening found. The merge-ready addition is:
```diff
+    ("strace-measure.yml", "pull_request:"):
+        (1, "the workflow TRIGGER ...")
```
It accounts for the new trigger. Neither check implementation otherwise changed; splitting `"--self" + "-test"` avoids classifying the measurement instrument as a suite owner. The `NO-MUTATIONS:` declaration uses an existing escape.

Self-tests passed: isolation **141/141**, merge-ready **400/400**, ratchet **56/56**. Python-pin check passed. Workflow configuration matches the requested triggers, read-only permissions, probe, retention, and Python pin. **NOT RUN:** fresh runner/ptrace measurement and actionlint; neither executable is installed locally. No files changed or GitHub actions taken.

VERDICT: NOT CONVERGED
