<!-- codex-review: model=gpt-6.1-sol -->

Reviewed head: a09cc99cc53f32007449ca4b6147c4199ea7f490

1. **High — BLOCKER — cached imports disappear from the digest.** `scripts/gates-for-pr.py:242,295`  
   Ran `python3 /tmp/review438-pyc-fixed.py`: copied the existing grouping gate and its dependencies into an isolated repository, warmed its bytecode cache, recorded green, then changed `gen-backlog-page.py`’s `INDEX_TITLE`.
   > `SKIPPED     Every grouping is a claim with a falsifier  (last green 10989645efdd3d0d)`  
   > Forced: `FAIL ... rc=1`

   The ledger contained only `docs/backlog.md` and the gate script. Cached imports open `.pyc` files, which both filters discard; their source files are never recorded. **Local fix:** capture bytecode dependencies and their corresponding sources, and invalidate existing digests. **Siblings searched:** imported generator dependencies were also absent. **Fix-induced: no.**

2. **High — BLOCKER — unseen external filesystem state hides a real memory-gate failure.** `scripts/gates-for-pr.py:208,285`  
   Ran `python3 /tmp/review438-actual.py` against the existing `check-memory-link.py`, with an isolated HOME and ledger. First recorded its advisory green with no memory link; then created a dangling symlink pointing at the wrong corpus.
   > `SKIPPED     Memory corpus link  (last green b94c216f770e3142)`  
   > `exit 0`  
   > Forced: `FAIL ... rc=1`

   Neither the existence check nor `readlink()` becomes an input. **Local fix:** keep this gate unbounded until those dependencies can be tracked. **Siblings searched:** compared with directory-listing and repository-file-appearance probes, which correctly reran; other external metadata readers were not exhaustively audited. **Fix-induced: no.**

3. **High — FILE — resolved HEAD omits branch identity.** `scripts/gates-for-pr.py:456,479`  
   Ran `python3 /tmp/review438-more-fixed.py`. A fixture gate checks `git symbolic-ref --short HEAD` and fails outside `master`. After recording green, `git switch -qc bad` preserved the commit and file contents:
   > `SKIPPED     branch-only  (last green 6ab8c57b23691b8d)`  
   > `runner exit 0`  
   > Forced: `FAIL ... rc=1`

   Resolving `HEAD` through `cat-file` preserves the object ID, losing its symbolic target. **Local remedy:** digest symbolic identity or make this command unbounded. **Siblings searched:** the repository’s `symbolic-ref` use is in `check-ci-watched.py`, outside `verify`; moving a named base ref correctly forced execution. **FILE:** current-CI reachability of this fixture failure was not established. **Fix-induced: no.**

4. **High — FILE — a loaded tracer does not establish bounded inputs.** `scripts/gates-for-pr.py:203,208,422,517`  
   Ran `/tmp/review438-probe.py`, `/tmp/review438-extra.py`, and `/tmp/review438-startup.py`. Each recorded green, changed only the indicated input, then compared skipping with forced execution:

   | Input actually changed | Observed false green | Forced result |
   |---|---|---|
   | `REVIEW438_FAIL=1` | `SKIPPED env-only` | `FAIL rc=1` |
   | File read through `ctypes`/libc | `SKIPPED c-read` | `FAIL rc=1` |
   | Local TCP server response, A → B | `SKIPPED network` | `FAIL rc=1` |
   | Same-day clock crossing a deadline | `SKIPPED clock` | `FAIL rc=1` |
   | Repository setting read by chained `sitecustomize` before hook installation | `SKIPPED startup` | `FAIL rc=1` |

   **Siblings searched:** tested all five paths rather than assuming subprocess classification covered them. These are fixture counterexamples; existing-CI failures were not established. **FILE:** the general guarantee needs a boundedness policy; date hashing and an environment allowlist cannot establish it. **Fix-induced: no.**

5. **Medium — FILE — nested tracers recurse and break the runner’s own gate.** `scripts/gates-for-pr.py:198`  
   Standalone `--self-test` passed **61/61**. Both real battery runs failed `gates-for-pr self-test`. Ran `/tmp/review438-nested.py` to isolate it:
   > `inner PASS (None, 'the tracer did not load, so what it read is unknown')`  
   > `RecursionError: maximum recursion depth exceeded`

   The two generated hooks discover and chain one another. **Local fix:** prevent generated-tracer chaining cycles. **Siblings searched:** the runner’s mutation control fails through the same path. **FILE:** this causes refusal/failure, not a demonstrated false green. **Fix-induced: no.**

6. **Medium — FILE — structurally corrupt JSON crashes instead of running gates.** `scripts/gates-for-pr.py:545,558`  
   Ran `/tmp/review438-probe.py` with:
   ```json
   {"green":[{"gate":"scripts/env.py","mode":"(no arguments)","inputs":7,"digest":"x"}]}
   ```
   > `AttributeError 'int' object has no attribute 'get'`

   **Local fix:** validate record fields before accepting the ledger. **Siblings searched:** malformed JSON correctly falls back to execution; nested record shapes bypass that validation. **FILE:** no false green, but it violates the requested “run, not skip” recovery behavior. **Fix-induced: no.**

Foreground verification completed:

- Default real run: **78 pass, 3 fail, 2 cannot run, 1 timeout**.
- Second real run, `--timeout 40`: **35 pass, 43 skipped, 2 fail, 2 cannot run, 2 timeout**.
- All **91 verify run steps** accounted for: 80 gates and 11 exclusions; schema workflow printed separately.
- Concurrent ledger writers from two worktrees preserved both records.
- Working tree unchanged.

VERDICT: NOT CONVERGED
