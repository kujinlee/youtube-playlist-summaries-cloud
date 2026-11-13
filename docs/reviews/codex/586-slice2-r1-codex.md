<!-- codex-review: model=gpt-6.1-sol -->

Found **4 Major fail-open defects**. No repository files were changed; GitHub was untouched.

Validation passed:

- Self-test: **92/92**.
- Mutation check: **62/62 killed**, all attributed to their named cases.
- Fixture variation and changed-suite self-test counts passed.
- All five requested wiring points are present.

Reproductions ran through `parse_log`, `process_tree`, and `resolve_calls`, with artifacts outside the repo at `/tmp/strace-review-minimal-yloqo8z8`. Context: copy/cwd `/t`, staged root `scripts`, TMPDIR `/tmp/run`, no repo symlinks. **Every input below returned refusal `None`.**

1. **Major — a filename can disable final-component symlink checking.** `scripts/strace_reads.py:524`

   `_follows_final()` searches the entire argument string for `AT_SYMLINK_NOFOLLOW`, including quoted filenames.

   Input run:

   ```text
   1 symlink("/t/scripts/needed.py", "/tmp/run/AT_SYMLINK_NOFOLLOW") = 0
   1 stat("/tmp/run/AT_SYMLINK_NOFOLLOW", {st_mode=S_IFREG|0644, ...}) = 0
   1 unlink("/tmp/run/AT_SYMLINK_NOFOLLOW") = 0
   ```

   Actual paths:

   ```text
   [['/tmp/run/AT_SYMLINK_NOFOLLOW'],
    ['/tmp/run/AT_SYMLINK_NOFOLLOW'],
    ['/tmp/run/AT_SYMLINK_NOFOLLOW']]
   ```

   `stat` follows this link and probes `/t/scripts/needed.py`; that dependency is missing. Cleanup removes the link before parse-time `realpath` can recover it. Expected: `through a runtime link`. Inspect actual flag operands, restricted to syscalls that support them.

2. **Major — hard-linking a runtime symlink creates an untracked symlink alias.** `scripts/strace_reads.py:509`

   Runtime-link closure accounts for `symlink*` and `rename*`, but not `link*`.

   Input run:

   ```text
   1 symlink("/t/scripts", "/tmp/run/L") = 0
   1 link("/tmp/run/L", "/tmp/run/M") = 0
   1 stat("/tmp/run/M/needed.py", {st_mode=S_IFREG|0644, ...}) = 0
   1 unlink("/tmp/run/M") = 0
   1 unlink("/tmp/run/L") = 0
   ```

   Actual paths:

   ```text
   [['/tmp/run/L'],
    ['/tmp/run/L', '/tmp/run/M'],
    ['/tmp/run/M/needed.py'],
    ['/tmp/run/M'],
    ['/tmp/run/L']]
   ```

   Linux `link()` hard-links the symlink itself. Consequently `M/needed.py` probes `/t/scripts/needed.py`, which is absent from the result. Expected: refusal for the unmodelled alias or `through a runtime link`. Both cleanup calls remain inside the allowed TMPDIR.

3. **Major — cwd races are checked for forks, but not unfinished relative path calls.** `scripts/strace_reads.py:499`

   Input run:

   ```text
   1 clone(child_stack=NULL, flags=CLONE_VM|CLONE_FS|SIGCHLD) = 2
   1 stat("needed.py",  <unfinished ...>
   2 chdir("/t/scripts") = 0
   1 <... stat resumed>{st_mode=S_IFREG|0644, ...}) = 0
   ```

   Actual paths:

   ```text
   [[], ['/t/needed.py'], ['/t/scripts']]
   ```

   The parser fixes `stat`’s path at its entry line. The parent can instead perform kernel path lookup after the shared-context child changes cwd, probing `/t/scripts/needed.py`. This log cannot establish which cwd applied, yet the parser accepts only the old location. Expected: `cwd race` for this unresolved overlap.

4. **Major — a log truncated inside a return label is accepted as complete.** `scripts/strace_reads.py:218`

   Input run, ending immediately after `needed.py`, with no closing `>` or newline:

   ```text
   1 openat(AT_FDCWD</t>, "/tmp/run/preexisting-link/needed.py", O_RDONLY) = 3</t/scripts/needed.py
   ```

   Actual paths:

   ```text
   [['/tmp/run/preexisting-link/needed.py']]
   ```

   `parse_log` accepts the malformed return. `ret_label` treats it as having no label, and resolution silently substitutes the argument path, losing the canonical repository path already visible in the truncated label. Parse-time filesystem inspection cannot establish what an incomplete recording omitted. Expected: `log did not parse`; validate the return syntax and reject incomplete labels.

The committed fixtures have recorded provenance: `samples.json` and both whole logs identify run **42893595762**, targets and shards; `strace-measure.py` captures these raw samples and whole logs. The new suite loads those fixtures and derives variants through substitutions. Slice 1’s documented ptrace success correctly excludes conditional slice 2F. The green mutations prove the 62 named assertions detect their supplied changes; they do not cover the fail-open cases above.

**VERDICT: NOT CONVERGED.**
