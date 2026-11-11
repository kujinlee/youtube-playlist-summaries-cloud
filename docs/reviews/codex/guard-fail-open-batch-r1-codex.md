<!-- codex-review: model=gpt-6.1-sol -->

1. **Medium — unchecked payload copy still fails open.** `.claude/hooks/enforce-handoff-path.sh:36`
   
   Executed the real hook with a valid `/handoff` envelope and a PATH shim making `cat` exit 1. Result: **exit 0, empty stdout and stderr**. The unchecked copy leaves an empty file; JSON parsing exits 3, which means “not mine.” Check the copy’s status and distinguish file-read failure from an unrelated envelope.

2. **Medium — the banner guard still crashes into the warning code.** `scripts/check-banner-armed.py:1316`
   
   Executed `--decide` against a transcript containing `{"type":"user","message":123}`. Result: **exit 1**, `AttributeError` in `_is_tool_result`. The new dictionary filter accepts this record, and the guard’s own `windows()` call remains unprotected. The identical input correctly produces **CANNOT RUN, exit 2** in `check-closing-table.py`.

3. **Medium — failure of the second interpreter call falsely reports a policy violation.** `.claude/hooks/enforce-handoff-path.sh:65`
   
   Used a shim that delegates envelope detection to real Python but exits 1 for the checker invocation. Result: **exit 2**, with “BLOCKED — the handoff skill would write where nothing reads.” No skill inspection occurred. This contradicts the PR/dashboard claim that inability to check is reported explicitly; distinguish checker failure from a measured bad path.

4. **Low — unreadable HEAD now bypasses legacy-file cleanup.** `scripts/check-ci-watched.py:1193`
   
   Created the legacy `ci-watching` file, patched `_run` to return `None`, and invoked `main(["--clear"], None)`. Result: **exit 2; legacy file remains**. Returning CANNOT RUN is correct, but the early return prevents the independent cleanup promised at lines 1202–1205. Repository search found no production caller requiring the previous QUIET result.

Additional executed checks:

- All touched Python self-tests passed: banner **237/237**, CI watcher **84/84**, closing table **155/155**, handoff **15/15**, mutation harness **239/239**.
- All four new manifest mutations reddened their named cases, including the re-aimed stat race.
- Restoring the old hook produced **13/15**, failing exactly the chatty and broken-interpreter cases.
- `mktemp` failure correctly warns and exits 1.
- `arms_newest_first()` on a file raises `NotADirectoryError`. Removing the directory after `run_decide`’s `is_dir()` gate raises `FileNotFoundError`. The record-removal fix works; it does not protect directory enumeration.
- The backlog’s narrow fix descriptions are supported. The PR/dashboard’s blanket CANNOT RUN claim is overstated by findings 1–3. I stopped the optional 185-mutation sweep before completion; its claimed full result was not independently verified.

VERDICT: NOT CONVERGED
