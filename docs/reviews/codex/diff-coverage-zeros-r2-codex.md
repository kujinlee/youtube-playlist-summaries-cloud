<!-- codex-review: model=gpt-6.1-sol -->

Reviewed `fc4a691c` against `origin/master`, Git 2.49.0. Repository untouched. Experiments ran in temporary copies with `GIT_DIR` unset at launch; victim tests injected it inside the experiment.

1. **[P2] The snapshot changes symlink semantics instead of preserving the loader’s refusal.** `scripts/check-diff-coverage.py:269–278` checks object type `blob` but ignores mode `120000`. It writes a symlink’s **link text** as a regular manifest.

   Executed fixture: commit `scripts/mutations/g.json` as a dangling symlink whose link text is valid mutation JSON covering `if bad:`. The working-tree loader raises `FileNotFoundError`; the snapshot loader accepts that same link text as mutations. The checker exits **0**, reporting:

   > diff coverage: 0 changed decision line(s) no mutation edits, across 1 manifested script(s) … — every one is edited by a mutation

   An ordinary symlink target string correctly produces CANNOT RUN, but that depends on its text being invalid JSON. Reject unsupported manifest modes explicitly.

2. **[P2] Real-git fixtures still inherit command-scope Git configuration.** At lines `579` and `599–600`, disabling global/system config leaves `GIT_CONFIG_COUNT`, `GIT_CONFIG_KEY_*`, and `GIT_CONFIG_VALUE_*` active.

   Executed with:

   ```sh
   env -u GIT_DIR \
     GIT_CONFIG_COUNT=1 \
     GIT_CONFIG_KEY_0=core.hooksPath \
     GIT_CONFIG_VALUE_0=/tmp/.../hooks \
     python3 scripts/check-diff-coverage.py --self-test
   ```

   A `pre-commit` hook containing `exit 1` crashes the suite at `world()`’s first commit, with `CalledProcessError`. The claim that fixtures are isolated from host configuration remains too broad. Sanitize command-scope config as well.

3. **[P3] One named case still passes for an ambient reason.** The case **“main() over an unknown base exits 2”** checks only the exit code. I copied the scripts into a directory with no repository and ran the suite: **57/57 passed**. Directly running that alleged unknown-base scenario there reports:

   > error: Could not access 'no-such-ref-xyz...HEAD'

   It never establishes an otherwise valid repository and range. Run this case in a real fixture and check the failure reason. This directly loses the bet’s “no case passing for an ambient reason” clause.

Other executed results:

| Attack | Result |
|---|---|
| Ignored manifest, assume-unchanged, skip-worktree, clean filter, working-tree symlink | Uncovered decision still WARNed |
| Deleted line containing lone CR and forged diff header | Later decision WARNed |
| Target exists at HEAD, absent in working tree | WARN |
| Target absent at HEAD, present in working tree | CANNOT RUN |
| Ordinary HEAD symlink manifest | CANNOT RUN |
| HEAD submodule at manifest path | Skipped; with no remaining manifests, CANNOT RUN; with another valid manifest, measurement continues |
| Space, Unicode and tab in script/manifest names | Correct WARN |
| Detached HEAD | Correct WARN |
| Unborn HEAD | CANNOT RUN |
| Non-UTF-8 stderr | Replacement decoding; CANNOT RUN without traceback |
| HEAD with 5,000 extra scripts | Correct WARN; approximately **1.6 seconds** |
| Entire self-test under victim `GIT_DIR` | **57/57**; victim file hashes unchanged |

The broader working-tree-independence bet also fails literally: adding uncommitted `*.py -diff` to `.gitattributes` changes WARN to binary **NOT CHECKED**. This is conservative, but changes what is measured. The loader itself also executes from the working tree (`_plan_code(root)`): replacing it with a loader returning covering edits produced a clean zero against unchanged committed sources/manifests.

**Validation:** baseline **57/57**. After supplying the temporary clone’s missing TypeScript dependency, the requested mutation command completed with **34 executed, 34 killed, 34 attributed to their named cases, zero survivors**, and passing control/re-control. Those counts are real; they do not establish that every case reaches its named failure.

The docstring, backlog #371, dashboard entry and live PR body accurately describe the original three repairs and current counts. Their isolation guarantees need qualification or the fixes above. Backlog #373 correctly remains open; I did not independently reproduce its historical identity-leak accounting or execute all five unrelated fixtures.

VERDICT: NOT CONVERGED
