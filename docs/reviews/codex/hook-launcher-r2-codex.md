<!-- codex-review: model=gpt-6.1-sol -->

Reviewed `7771adfe`, mandate REFUTE. Three findings remain.

1. **[P2] Inherited Bash settings refute the environment-independence bet.** The registered command and `.claude/hooks/run-hook.sh:67` invoke Bash without isolating its startup environment. Through the exact registered command, from a worktree’s `scripts/`:
   - `BASH_ENV` naming a temporary file containing `cd "$CLAUDE_PROJECT_DIR"` made **main’s probe run instead of the worktree’s**, returning 7.
   - `SHELLOPTS=xtrace` preserved exit 7 but added shell traces to stderr.

   `check-run-hook.py` strips these variables through `ENV_ALLOW`, so its green environment cases do not cover this production behavior. The decision-log bet and launcher header need either an explicit trusted-shell-environment boundary or corresponding hardening and regression cases.

2. **[P2] The LIVE-falsifier account omits a necessary default-branch precondition.** The setup described in `docs/backlog.md:346`, the coordinator record at lines 33–36, and PR #419 does not specify the clone’s `refs/remotes/origin/HEAD`.

   I reproduced two fresh clones with local bare origins and separate live `claude -p` Bash calls. Initially **both pushes succeeded**: cloning this branch retained `origin/HEAD → origin/hook-launcher`, which the push gate therefore treated as the default branch. Pointing the bare repository’s HEAD at master alone did not correct that local symbolic ref.

   After explicitly setting `refs/remotes/origin/HEAD → refs/remotes/origin/master`, the claimed comparison reproduced: **this branch blocked; bare master stayed unchanged; the master control pushed successfully**. The launcher works in that experiment, but the published reproduction needs this setup step and an assertion of the resolved default branch.

3. **[P3] Current prose still contradicts the measurements.**
   - `docs/dashboard-entries.md:17868` says the live check has not happened; line 17876 still says **UNVERIFIED**, contradicting the row, coordinator and PR body.
   - `scripts/check-run-hook.py:18` says each launcher mutant “re-runs every world.” The shipped `kill_report()` runs only its named worlds.
   - The stream case named “JSON-shaped stdout” emits `probe-stdout-364\n`, not JSON. It tests stream preservation, but its label overstates the payload exercised.

Execution otherwise supports the fold:

- **72/72** under `env -i PATH=… HOME=…`, with every host `GIT_*` absent and hostile home git config.
- **72/72** through dash with `LANG=C LC_ALL=C`; UTF-8-locale ordinary mode also passed.
- **72/72** with hostile inherited Git variables and `TMPDIR` beneath a `.git` ancestor.
- Independently ran all **19 mutants across every world** under both `/bin/sh` and dash: **19/19 killed each**, with green controls.
- **46/46 manifest mutations killed and attributed**, including both W10-precondition mutations; final controls green.
- Binary stdin/stdout/stderr and exit codes **0, 1, 2, 3, 127, 255** propagated exactly.
- Registration comparison confirmed exactly **14 command-only rewrites**; deleted-cwd probe returned NOT RUN, exit 1.

Dash was exercised on macOS; this does not establish Linux filesystem behavior. Repository unchanged; experiments stayed in temporary copies launched with `GIT_DIR` unset.

VERDICT: NOT CONVERGED
