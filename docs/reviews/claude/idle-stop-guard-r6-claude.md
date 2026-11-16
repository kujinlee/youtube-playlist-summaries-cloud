Reviewed head: e30f8c98e41bc9b8681d9df47fceac82230436c1

# idle-stop-guard — review round 6, Claude half

**Subject:** `git diff 72ba7a3c e30f8c98 -- scripts/check-idle-stop.py` (HEAD `e30f8c98e41bc9b8681d9df47fceac82230436c1`).
**Delta:** the self-test's fixture `git commit` (in `_self_test_body`) now passes `-c user.name=selftest -c user.email=selftest@example.com`,
because a CI runner has no git identity and the commit exited 128 there.
**Mandate:** refute that the delta is correct and complete. Round 6 is past the round cap: only a BLOCKER blocks.

## Findings

None at BLOCKER or MAJOR. One MINOR note, which does not need to be filed:

- **MINOR (no file): the reproduction the brief suggested does not reproduce the CI failure on this Mac.** `HOME=$(mktemp -d) GIT_CONFIG_NOSYSTEM=1
  GIT_CONFIG_GLOBAL=/dev/null` leaves git free to auto-detect an identity from the passwd entry and hostname. On macOS that succeeds:
  a bare `git commit` in that environment returned rc=0. Setting `user.useConfigOnly=true` through `GIT_CONFIG_COUNT` does not help either,
  because the suite runs inside `fixture_git.isolated()`, which replaces `os.environ` with an allow-list (`PASSED_ENV` + `ISOLATION`) and drops
  every `GIT_*` variable. The control that does reproduce CI is a `git` shim on `PATH` (PATH is passed through) that runs
  `git -c user.useConfigOnly=true "$@"`. Results for that control are below. The point to take away: a "no identity" check run locally
  on macOS proves nothing unless auto-detection is disabled.

## Refutation attempts

1. **Does any other git call need an identity?** Every git call reachable from the self-test is listed by
   `grep -n '"git"' scripts/check-idle-stop.py`: lines 467, 608 and 659 are `git init -q` (`init` does not need an identity), and line 469 is the
   patched commit. Production code (`main()`/`run_gh`, before `_self_test_body` at line 258) has exactly one subprocess call, `gh pr list` (line 147).
   It has no git call. `.claude/hooks/check-idle-stop.sh` contains no `git`. The end-to-end launcher cases therefore run no git either.
   **Not refuted.**
2. **Does the delta change the delivered hook's behaviour?** The diff is 3 insertions and 1 deletion, all inside `_self_test_body` (from line 258).
   `--hook`/`main()` code is untouched. **Not refuted.**
3. **Does the fix actually fix it (identity control)?** With the shim that disables auto-detection, I ran the 72ba7a3c tree (copied with its own
   `fixture_git.py`, `check-usage-pace.py`, `bounded_read.py` and hook into a scratch dir) and HEAD:

## Command results (quoted)

Brief's environment, HEAD:
```
$ HOME=$(mktemp -d) GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null python3 scripts/check-idle-stop.py --self-test   → rc=0
61/61 self-test cases passed
```
(Control: a bare `git commit` in that same environment returned rc=0 on this Mac, so this run alone does not discriminate.)

Normal environment, HEAD:
```
$ python3 scripts/check-idle-stop.py --self-test   → rc=0
61/61 self-test cases passed
```

Shim control (`git -c user.useConfigOnly=true`, plus HOME/NOSYSTEM/GLOBAL as above):
```
bare commit:        fatal: no email was given and auto-detection is disabled   (rc=128, the CI failure reproduced)
HEAD rc=0           61/61 self-test cases passed
OLD (72ba7a3c) rc=1 subprocess.CalledProcessError: Command '['git', '-C', '.../repo', 'commit', '-q', '--allow-empty', '-m', 'base']' returned non-zero exit status 128.
```
Without the delta, the suite dies at the fixture commit. With it, all 61 cases pass. No other git call fails once auto-detection is disabled.

VERDICT: CONVERGED
