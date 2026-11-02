<!-- codex-review: model=gpt-6.1-sol -->

Reviewed `origin/master...e3d23783`, mandate **REFUTE**. Repository unchanged; experiments ran in a `mktemp -d` copy, launched with `GIT_DIR` unset. Primary Git: 2.49.0.

1. **[P2] `--attr-source=HEAD` does not isolate attributes to HEAD.** `scripts/check-diff-coverage.py:296–300`

   Executed against a committed, uncovered `scripts/g.py:2` (`if bad:`). The control prints WARN. Each of these independently changes it to binary NOT CHECKED:

   - `.git/info/attributes` containing `*.py -diff`.
   - Local `core.attributesFile` pointing to that rule.
   - Changing HOME to a directory whose `.gitconfig` supplies that `core.attributesFile`.

   Actual result:

   ```text
   NOT CHECKED scripts/g.py: git reports a BINARY diff, so its lines are unknown
   diff coverage: 0 changed decision line(s) no mutation edits, across 1 manifested script(s) ...; 1 NOT CHECKED
   ```

   An uncommitted `.gitattributes` correctly preserves WARN. The option changes the source of in-tree attributes; it does **not** disable the other attribute sources. HOME remains a configuration channel despite the existing pins. This loses the bet’s “no environment variable or working-tree state changes what is measured” clause, although this reproduction does not claim “every one is edited.”

2. **[P2] A manifest-shaped tree silently disappears instead of being refused.** `scripts/check-diff-coverage.py:264–277`

   Committed `scripts/h.py` and a directory `scripts/mutations/h.json/item`, alongside a valid `g.json`.

   ```text
   040000 tree ... scripts/mutations/h.json
   ```

   Executing the original loader on that checkout raises `IsADirectoryError`. Executing the checker returns **0**, measures `g.py`, and never reports `h.json`: recursive `ls-tree` omits the tree entry itself, so the regular-file refusal never sees it.

   This violates the promised refusal of non-regular manifests and permits a partial manifest set. Enumerate immediate manifest-directory entries with their types before accepting the snapshot.

3. **[P3] The documented Git minimum is incorrect.** `scripts/check-diff-coverage.py:297`, backlog #371

   Built and executed Git **2.39.5 and 2.40.0**. Both reject `--attr-source=HEAD`; the checker returns **2 / CANNOT RUN**, with no fallback. The option was introduced in **2.41**, as recorded in the [official release notes](https://raw.githubusercontent.com/git/git/v2.41.0/Documentation/RelNotes/2.41.0.txt).

   `.github/workflows/ci.yml` uses `ubuntu-latest` without pinning Git. The latest available branch [CI run](https://github.com/kujinlee/youtube-playlist-summaries-cloud/actions/runs/40481017404) records **Git 2.55.0**, but ran round 2 head `fc4a691c`. I cannot establish the runner version for `e3d23783` from an executed run.

Executed validation:

| Check | Result |
|---|---|
| Baseline self-test | **61/61** |
| Suite copied outside any repository | **61/61**; unknown-base case constructs its own repository |
| Suite with victim `GIT_DIR` and command-scope config exported | **61/61**; victim file hashes unchanged |
| Requested mutation command, after copying missing TypeScript dependency | **37 executed, 37 killed, 37 attributed, 0 survivors**; control and re-control passed |
| Fixture-environment, valid-JSON symlink, unknown-base cases | Reach their named scenarios; environment and symlink mutations attributed correctly |
| Ignored/uncommitted manifests, assume-unchanged, skip-worktree, clean filter, working-tree symlink | WARN preserved |
| CR-forged deleted-line header | Later uncovered decision WARNed |
| Source absent from working tree / absent from HEAD | WARN / CANNOT RUN |
| HEAD symlink / submodule manifest | CANNOT RUN |
| Executable manifest, mode `100755` | Accepted; WARN preserved |
| Deeper manifest | Ignored, consistent with loader’s nonrecursive scope |
| Space, Unicode, tab names; detached HEAD | WARN preserved |
| Unborn HEAD; non-UTF-8 error output | CANNOT RUN without traceback |
| 5,000 extra scripts | WARN; approximately **2.2 seconds** |

I found no required variable incorrectly dropped by the allow-list in these local operations; an allow-list-only environment worked. This is not Linux execution evidence. SSH variables serve no purpose for these local object reads.

The working-tree loader attack still produces “every one is edited” when replaced with covering entries. The coordinator and backlog explicitly acknowledge that executable-code boundary, so I am not treating it as a new finding.

The **61/37 counts and original three repairs are real**. The docstring and dashboard accurately describe those repairs. The backlog, dashboard, and live [PR body](https://github.com/kujinlee/youtube-playlist-summaries-cloud/pull/415) overstate HEAD-only attribute isolation; the regular-manifest guarantee misses trees, and the stated Git ≥2.40 requirement is false.

VERDICT: NOT CONVERGED
