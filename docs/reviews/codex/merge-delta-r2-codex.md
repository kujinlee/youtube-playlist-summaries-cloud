Reviewed head: ba86d9c16516abd1fcdb24acb92f93880a3f9219

Round 2, Codex half; PR #491, `merge-delta`. Reviewed the fold from f84fce2b and the complete `master_explains` / `_master_side` / `merge_tree_argv` / `merge_onto` / `_final_entries` path. No `.claude/plans/` files read. Git 2.49.0.

## Findings

### M1 — Medium: the forced `text` driver can itself be redefined in Git config

`scripts/check-review-recorded.py:1115`. `merge.default=text` selects a driver name; Git still honors `merge.text.driver`. Thus the new command does not force the built-in text merger.

Real fixture: base `scripts/a.py` has 20 numbered lines. Reviewed commit R replaces line 2 with `BRANCH`. Master independently replaces it with `MASTER`. Merge master into the branch, resolve by hand to `BRANCH\nMASTER`, and commit H. With ordinary config, `_master_side(R, merge_onto("master"), ...)` reports `scripts/a.py` conflicted and `round_tail` returns `['scripts/a.py']`. Set:

```
git config merge.text.driver 'cp /absolute/fixture/scripts/a.py %A'
```

The same helpers now return an empty conflicted set and tail `[]`: the unreviewed conflict resolution is falsely cleared. The driver copies the existing final worktree bytes to the temporary merge result and exits successfully. The full `round_tails` → `tail_verdict` path changes from rc 1 to rc 0 (`the final tree was in the tree handed to r.verdict.json`). There are no attributes files. Also reproduced when the setting comes from an `includeIf.gitdir:<absolute-real-git-dir>.path` include. Also reproduced with `GIT_CONFIG_COUNT=1`, `GIT_CONFIG_KEY_0=merge.text.driver`, and `GIT_CONFIG_VALUE_0` set to that driver command. This is a local/inherited-config exposure, not a claim that committed repository config is imported by CI.

Measured repair: supplying `-c merge.text.driver=` restores the conflict on this fixture, even with the malicious setting still in repository config. Add that override (or otherwise isolate driver configuration) and a real-Git regression case.

### M2 — Medium: system gitattributes survive the empty-tree attribute source

`scripts/check-review-recorded.py:1114`. The command disables the user attributes file, but does not disable system attributes. `--attr-source=<empty tree>` does not suppress the system layer.

Same fixture and hand-resolved H as M1, with no custom merge driver config. Temporarily create this Git installation's previously absent `/usr/local/etc/gitattributes`:

```
* merge=union
```

`git check-attr merge -- scripts/a.py` confirms `merge: union`. `_master_side` now reports no conflicts, its entry equals H, and `round_tail` returns `[]`; the full `round_tails` → `tail_verdict` path exits 0 instead of the control's 1. Set `GIT_ATTR_NOSYSTEM=1` and the same fixture returns `['scripts/a.py']` with a conflict again. The temporary system file was removed in a `finally` block. The info/attributes refusal does not cover this source.

Set `GIT_ATTR_NOSYSTEM=1` for the synthetic merge and add this regression case. The claimed removal of all attribute sources is incomplete.

## Other probes and fail direction

Real conflict fixtures remained charged under `merge.renormalize=true`, `core.autocrlf=true`, `core.eol=crlf`, both diff3 and zdiff3 conflict styles, `branch.br.mergeOptions=-Xours`, `merge.options=-Xtheirs`, `merge.default=union`, and `GIT_CONFIG_COUNT` injecting that default. A trained rerere resolution did not clear the synthetic merge. `GIT_ATTR_SOURCE` was overridden by the explicit command option. These probes do not establish safety for every possible combination.

Replacement-ref probes replacing the reviewed commit's tree or the common ancestor's tree remained charged in the tested fixture. Replacement refs and grafts can also change the pre-existing diff and ancestry questions; parent grafts via `git replace --graft` in each direction also stayed charged. No independent merge-delta finding is asserted for broader history substitutions. `GIT_INDEX_FILE`, `GIT_MERGE_VERBOSITY`, and `GIT_LITERAL_PATHSPECS` also stayed charged. `.mailmap` does not participate in these tree/entry comparisons.

The new HEAD ls-tree failure raises; merged-tree ls-tree failure, merge-base failure, attribute-path lookup failure, and empty-tree lookup failure all retain the strict rule. Non-{0,1} merge-tree status is rejected, and conflicted paths are excluded even if their synthesized entry equals HEAD. No additional Git-failure false clear found in this path.

The two dropped empty-answer guard mutations are defensible redundant checks on Git 2.49.0: measured `--attr-source=` exits 128 with `fatal: bad --attr-source or GIT_ATTR_SOURCE` on the conflict fixture. Removing the Python guard still reaches Git's rejection and preserves the strict rule. That observation does not justify the broader attribute-isolation claim: M2 uses a valid empty-tree ID and still applies system attributes.

## Validation

- `python3 scripts/check-review-recorded.py --self-test`: **237/237 passed**, rc 0.
- `python3 scripts/check-plan-code.py --mutate . --only scripts/check-review-recorded.py`: rc 0; **90 killed, 90 attributed, 0 survivors**. This is the requested diagnostic slice, not the whole gate. The temporary `node_modules` symlink was removed afterward. Log: `/tmp/merge-delta-r2-sweep-recheck.log`.
- Temporary fixture harness and output: `/tmp/merge-delta-r2-probe.py`, `/tmp/merge-delta-r2-probe-recheck.log`.

VERDICT: NOT CONVERGED
