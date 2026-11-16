<!-- codex-review: model=gpt-6.1-sol -->

Reviewed `08dc620bc3e615126c5697b0fd5e5585bcf68974`. Five findings; one staging regression is caused by the fold, falsifying its bet.

1. **MAJOR — case aliases bypass the private-path exclusion.** `scripts/mkt_stage.py:159`  
   **Breaking input:** in a temporary repository on this case-insensitive macOS filesystem, create `.claude/plans/secret` containing `PRIVATE FIXTURE`, then track its spelling as `.CLAUDE/PLANS/secret` using `git update-index --force-remove` and `git add -f`. Declare `files=[".CLAUDE/PLANS/secret"]`.  
   **Wrong output:** staging succeeds and writes `p/.CLAUDE/PLANS/secret` containing `PRIVATE FIXTURE`. The tracked-path check accepts that spelling, while the case-sensitive `PRIVATE` comparison misses it. No real plans directory was accessed.  
   **Fix:** enforce private-directory identity across filesystem case aliases, including renamed paths, before traversal or copying.  
   **fix_induced:** false — the original private-source leak remains reachable. **component:** staging.

2. **MAJOR — resolving parents hides untracked and ignored directory symlinks.** `scripts/mkt_stage.py:155`  
   **Breaking input:** track `target/data`; create an untracked directory symlink `alias -> target`; declare `files=["alias/data"]`. Repeat with `alias` gitignored.  
   **Wrong output:** both stage successfully as `p/alias/data`. `path.parent.resolve()` discards the symlink before tracking checks, so neither check sees the untracked entry. A fresh checkout lacks the declared source path.  
   **Fix:** inspect every symlink component before resolving it, requiring each link and its final file to be tracked.  
   **fix_induced:** false — this shipping behavior predates the fold; its new tracking guard incompletely closes it. **component:** staging.

3. **MINOR — an unrelated non-UTF-8 index filename crashes staging.** `scripts/mkt_stage.py:139`  
   **Breaking input:** track ordinary `good.py`, then add an index entry named `b"bad-\xff.py"` using `git update-index --index-info`. Stage only `good.py`. Git accepts and lists both entries; the unusual entry need not exist on disk.  
   **Wrong output:** `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 4: invalid start byte`, instead of staging the valid declared file. `_tracked()` decodes every index path, including unrelated entries, with strict UTF-8.  
   **Fix:** use filesystem decoding (`os.fsdecode`) consistently, or compare filesystem-encoded path bytes.  
   **fix_induced:** true — the fold introduced this unconditional index decoding. **component:** staging.

4. **MINOR — package isolation is not “VERIFIED per run” through the direct API.** `docs/marketplace/isolation-baseline.md:24`; `scripts/mkt_isolate.py:407`  
   **Breaking input:** build a world whose allowed `python3` resolves to `/usr/bin/python3`, then call `run_isolated()` with `python3 -c "import sys; print(sys.path)"`.  
   **Wrong output:** execution returns rc 0 with Command Line Tools `python3.9/site-packages` present. Calling preflight separately correctly reports that path and installed distributions including `pip`, `setuptools`, and `wheel`; `run_isolated()` does not enforce that refusal. Its boundary check verifies environment values, not interpreter package isolation.  
   **Fix:** qualify the prose to require successful preflight before direct API execution, or enforce interpreter verification at execution.  
   **fix_induced:** true — the per-run verification claim was added by the fold. **component:** docs.

5. **MINOR — authentication status does not establish absence of keychain reads.** `docs/marketplace/isolation-baseline.md:79`  
   **Breaking input/evidence:** the recorded `claude auth status → loggedIn: false` and `gh auth status → not logged in`.  
   **Wrong output:** the prose concludes “so neither tool reads it today.” Those outputs establish unauthenticated status, not whether either process queried the keychain. Non-Python file access is expressly unobservable here.  
   **Fix:** say the measurements found neither tool authenticated; leave keychain access unverified. The stated same-OS-user boundary itself is honest.  
   **fix_induced:** true — this inference was added by the fold. **component:** docs.

Round-1 closure checks:

| Finding | Round-2 result |
|---|---|
| Codex 1: private sources | Original direct-file, directory, and recursive symlink inputs refused; case-alias route remains above. |
| Codex 2: site-packages | Normal world interpreter has no site-packages; macOS shim is refused by preflight. Direct API limitation above. |
| Codex 3: Git config | `GIT_CONFIG_NOSYSTEM=1` present; world Git credential/rewrite query returned rc 1, empty stdout. Keychain remains explicitly unisolated. |
| Codex 4: environment values | Changed `HOME`, `PYTHONPATH`, and `GIT_CONFIG_NOSYSTEM` values refused at execution. |
| Claude M1: detached audit events | Harmless detached child reproduced: late events retained, survivor capture gap named, next record did not claim its opens. |
| Claude M2: repository cwd | Direct execution with this repository’s `scripts/` cwd refused. |
| Claude M3: untracked shipping | Original untracked `.DS_Store` and ignored-file inputs refused; parent-symlink route remains above. |
| Claude m1: competing plan clauses | Both clauses and the chosen interpretation are now explicit. |
| Claude m2: baseline overclaims | Package measurement and Git correction present; remaining prose issues above. |
| Claude m3: spend row | Task 3 row present, explicitly marking unavailable data. |

Additional fixtures refused a renamed untracked file, submodule descendants absent from the superproject’s tracked file set, and declarations containing `..`. The spike record withdraws its unsupported Git claim and explicitly says the corrected isolation was not rerun.

Both requested self-tests exited 0:

```text
67/67 self-test cases passed
72/72 self-test cases passed
```

Staging also reported its uncounted live marketplace-validation case passed. No repository files were edited; Git status remained clean. No prohibited paths or tokens were read, no live stranger world was run, and GitHub was untouched.

VERDICT: NOT CONVERGED
