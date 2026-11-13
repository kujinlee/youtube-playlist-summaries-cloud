<!-- codex-review: model=gpt-6.1-sol -->

1. **High — `scripts/strace-measure.py:308–311`: stale creation evidence still hides removal of pre-existing external files. FIX-INDUCED: NO; the fold retains this blind spot.**

   Ran through `_read`:

   ```text
   1 mkdir("/external/d", 0700) = 0
   1 rmdir("/external/d") = 0
   1 rename("/t/preexisting", "/external/d") = 0
   1 unlink("/external/d/valuable") = 0
   ```

   Result: `external_removals=[]`, unresolved **0**. Creation evidence for the removed directory survives, so importing a pre-existing directory at that pathname exempts its contents. Moving the created directory away instead of removing it produces the same missed final unlink.

   **Proposed fix:** invalidate creation evidence on successful removals and rename sources; replace destination evidence when another object arrives. Conservatively invalidate affected subtrees when provenance is uncertain.

2. **Medium — `scripts/strace-measure.py:520–559`: merging measured and unmeasured pairing data reports a falsely complete result. FIX-INDUCED: YES.**

   Ran:

   ```python
   a = _shard(1, 2, "measured.py", 1, 2, {"unpaired_halves": 0})
   b = _shard(2, 2, "unknown.py", 1, 2)
   _merge([[a, b]], "unpaired_halves")
   ```

   Result: `{}`. The second target never measured pairing, but one measured record sets the global `pairing_read=True`. The output loses the distinction between “none observed” and “not measured.”

   **Proposed fix:** track measurement coverage per target/seed; preserve unknowns explicitly or return `null` whenever coverage is incomplete.

3. **Medium — `scripts/strace-measure.py:755–759`: the sample-ownership test supplies the only sample it checks. FIX-INDUCED: YES.**

   Applied this mutation in memory:

   ```diff
   - samples[(name, tag)] = {"line": line, "target": who}
   + pass
   ```

   Result: **37/37 passed**. Assigning `"wrong"` as every newly inserted sample’s owner also leaves **37/37 green**. The fixture already supplies `("unlink", "= N")` with owner `first.py`; no assertion checks a newly inserted sample.

   **Proposed fix:** assert insertion and ownership from an empty store, alongside preservation of an existing entry. The new `analyse_log.samples` exemption currently overstates what the case verifies.

4. **Medium — `scripts/strace-measure.py:760–761`: the two-directory case does not prove both directories are read. FIX-INDUCED: YES.**

   Applied this mutation in memory:

   ```diff
   - for d in dirs for p in d.rglob("shard-*.json")
   + for d in dirs[-1:] for p in d.rglob("shard-*.json")
   ```

   Result: **37/37 passed**. The expected factor, **7**, comes entirely from the last directory. Dropping the first directory loses its target and measurements without failing the case.

   **Proposed fix:** assert both target identities or another aggregate requiring both shards, and verify shard coverage. The new `merge.dirs` exemption cites a case that does not establish its stated property.

5. **Low — `scripts/strace-measure.py:318–347`: unfinished calls survive process exit and can pair across PID lifetimes. FIX-INDUCED: YES.**

   Ran:

   ```text
   7 unlinkat(3</external>, <unfinished ...>
   7 +++ exited with 0 +++
   7 <... unlinkat resumed>"victim", 0) = 0
   ```

   Result: a fabricated completed removal of `/external/victim`, with **0 unpaired halves** and **0 unresolved removals**. The exit boundary is ignored.

   **Proposed fix:** orphan and clear a PID’s pending half when its exit is recorded. Treat a later resumed half as independently unpaired.

The original round-1 constructed inputs now produce the intended results: nonexclusive `O_CREAT` deletions are reported; failed renames do not exempt later deletions; quoted `) = 7` does not supply the return; resumed ioctl arguments yield `TCGETS`; malformed remover arguments become unresolved; label escapes decode; and `200.01 / 10` produces factor **21**. The `???` pair and added signal/exit/spawn fixtures also pass. Finding 1 means the broader creation-provenance claim remains incomplete.

Interleaved PIDs passed. Nested signal-handler calls were conservatively reported as unpaired/unresolved. Relative removal after `chdir` remains unresolved, as documented. Decorated dirfds and escaped quotes resolved correctly; truncated strings became unresolved.

All **37 cases were made red by production-code mutations**, but the surviving mutations above show that this does not establish coverage of each claimed property.

The committed JSONs match the documented syscall counts, ioctl table, largest-ratio table, shard times, timing sums, and run-specific leaders. Run **42893595762** gives ceiling **20**; **42901768433** gives **12**. Taking their maximum, **20**, is sound as the documented empirical timeout choice; it is not a demonstrated upper bound for future runs.

The isolation guard has **no diff**. The variation guard’s implementation is unchanged, but its new exemptions bypass structural variation checks for these parameters:

```diff
+ "strace-measure.py:analyse_log.samples": "... its callers vary samples ..."
+ "strace-measure.py:merge.dirs": "... two directories each holding one shard ..."
```

Findings 3–4 show those exemptions lack the claimed behavioral evidence.

Validation: reader **37/37**, isolation **141/141**, ratchet **56/56**, merge-ready **400/400**; fixture-variation main and Python-pin check passed. The corrected probe stopped on a stubbed `strace` failure. Local interpreter: Python **3.14**, versus CI **3.12**.

**NOT RUN:** fresh runner/ptrace measurement, actionlint, Python 3.12 execution, full fixture-variation mutation sweep, or re-merging original raw shards unavailable in the worktree. No repository changes, commits, GitHub access, or `.claude/plans/` reads.

**VERDICT: NOT CONVERGED**
