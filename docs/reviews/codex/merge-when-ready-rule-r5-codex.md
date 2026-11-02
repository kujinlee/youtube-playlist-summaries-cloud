<!-- codex-review: model=gpt-6.1-sol -->

1. **High — equal counts can silently misassign gate hunks and produce false READY.** `scripts/check-merge-ready.py:603`, `:721`.

   Executed with Git 2.49.0 in a scratch repository, using the exact commands from `diff_commands()`:
   
   - Change `docs/a` from regular file to symlink.
   - Change `scripts/check-x.py` from `return 1` to `return 0`.
   - Update gitlink `zmodule`, with `git config diff.submodule log`.

   The machine list contains three entries:
   ```text
   T docs/a
   M scripts/check-x.py
   M zmodule
   ```
   The patch contains three `diff --git` sections:
   ```text
   docs/a                 # deletion half of type change
   docs/a                 # addition half of type change
   scripts/check-x.py
   ```
   The submodule log has no `diff --git` section. Counts match, so the join assigns the symlink addition to the gate and the gate’s weakening to `zmodule`.

   Executed result:
   ```text
   hold_reasons(...) == []
   final_verdict(0, "READY", holds) == (0, "READY")
   ```
   Independently reproduced an equal-count false READY using `.gitattributes` with a configured `textconv=true` or external `command=true` driver suppressing the gate’s section. Production must normalize patch generation and handle type-change sections explicitly; count equality cannot establish correspondence.

2. **Medium — ordinary type changes alone refuse valid diffs.** `scripts/check-merge-ready.py:600`.

   Executed a regular-file-to-symlink change without special configuration. `--name-status -z -M` emitted one `T` entry; `-U5 -M` emitted two sections. Result:
   ```text
   PathsDisagree: the patch has 2 file section(s) and --name-status lists 1
   ```
   This becomes CANNOT RUN. A submodule update with `diff.submodule=log` independently produced one status entry and zero sections. Both refute the logged count-agreement bet.

Executed verification:

- Required self-test: **164/164 passed**.
- All **57 mutations**, independently applied over the green control: **57/57 killed through their named cases**; no ambient-only kill observed.
- First-parent replay of 40 commits at `origin/master`: **8/40 held**, specifically **#398, #387, #386, #382, #381, #367, #366, #360**; **zero join refusals**.
- Production paths/statuses come from the machine list; header path parsing remains confined to calls without `status`. Hunk parsing reads ordinary patches correctly, but the positional join can attach those hunks to the wrong file.
- Additional real-Git probes preserved correspondence for `diff.orderFile`, binary deletion, empty-file deletion, mode changes, copy-as-add, and rename similarities **49%, 50%, 51%, 100%**. These passing cases do not cover the demonstrated section imbalance.

VERDICT: NOT CONVERGED
