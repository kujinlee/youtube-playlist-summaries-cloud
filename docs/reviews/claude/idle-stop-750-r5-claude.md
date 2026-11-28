Reviewed head: fd76c3ab4856d833d0146b3bfc4fbe02c9745a2d

# Round 5 — `idle-stop-750` (PR #652, backlog #750 step 1) — Claude half

**Reviewed:** `fd76c3ab`, final tree of `scripts/check-idle-stop.py`. The focus is `git diff a382df38 fd76c3ab`, a test-only change: the CONTROL direct call to `log_decision` in the "#751 Y1" case (`:972-979`, asserted at `:986-989`). Round 4's two Medium findings (backlog #753) are not repeated here.

**Mandate:** show that the final tree is wrong. Round cap: only a Blocking finding is fixed in this PR. Everything else is filed.

## Gates (run in the worktree at `fd76c3ab`, clean tree)

| Check | Result |
|---|---|
| `python3 scripts/check-idle-stop.py --self-test` | rc=0, `79/79 self-test cases passed` |
| `python3 scripts/check-fixture-variation.py` | rc=0, `fixture variation OK — 2598 parameter(s) examined across 113 file(s)`. No line about `log_decision` (it reports other scripts' stale KNOWN_UNVARIED entries, which do not fail it) |
| `python3 scripts/check-plan-code.py --mutate . --only scripts/check-idle-stop.py` | rc=0, `83 mutation(s), 83 killed, 83 attributed to the case each names, 0 survivor(s)`. This is a diagnostic slice, not the gate. Took 4m41s |

## Does the control go red when a parameter is ignored? (measured, scratch copy outside the repo)

Each mutant was applied to a copy of the script, its siblings and the hook launcher, under a scratch `git init`. The worktree was never edited.

| Mutant in `log_decision` | Result | Caught by the control? |
|---|---|---|
| `verdict` replaced by `"allow"` | 78/79; red in a #750 case (the control's ALLOW matches) | no: the control alone would miss it. The existing #750 case covers it |
| `verdict` replaced by `"block"` | 77/79; Y1 red | yes |
| `now` replaced by `time.time()` | 78/79; Y1 red (`at` False) | yes |
| `localtime(now)` replaced by `gmtime(now)` | 78/79; Y1 red on this host (PST) | yes on this host; see L2 |
| `cwd` dropped | Y1 red | yes |
| `session_id` dropped | Y1 red | yes |
| `session` and `cwd` swapped | Y1 red | yes |
| `why` dropped | crash `KeyError: 'rule'` in an EARLIER #750 case (`logged()`), with no summary line | does not reach the control. This predates the diff |
| `path` redirected (the control's write goes to another home) | **crash** `FileNotFoundError` at `:977`, with no summary line | only by crashing; see L1 |
| early `return` (nothing is written) | 7 #750 cases red, then a crash in a later case | does not reach the control |

**Shared state with Y1: none found.** The control uses its own home (`buildable-home`) and its own path. It runs after the `redirect_stderr` block has closed and before the `json.dumps` patch starts at `:984`. The `os.write` patch comes later (Y2). The `at` assertion repeats the format literal independently of `log_decision`, so a change to the format string would be caught.

## Findings

### L1 — Low — the control is not crash-safe, so a mutant that breaks only `path` kills the suite instead of failing the case

**Where:** `scripts/check-idle-stop.py:977`. `Path(clog).read_text()` is called outside `tr()`/`bounded()`.

**Scenario:** a change to `log_decision` makes it write somewhere other than `path` but raise nothing. I measured this with a mutant that redirects `buildable-home` to another home. The handler reports the failure on stderr, `clog` never exists, and `:977` raises `FileNotFoundError`. The self-test then aborts with a traceback and no `N/M self-test cases passed` line. The Y2, END TO END and `run_gh` cases never run, and `tmp` (`:1046`) is leaked. Under `check-plan-code`'s rules (`rerun_kill`, and attribution by named `[FAIL]` lines), a red run with no summary line is **not** an attributed kill. A future manifest entry of this shape, naming the Y1 case, would therefore be reported as unattributed even though the case did detect the defect. An empty log (`IndexError` at `[-1]`) or an unparseable line (`JSONDecodeError`) ends the same way.

**Not Blocking:** none of the 83 shipping mutations hits this today (83/83 attributed), and the suite fails loudly rather than passing.

**Fix:** `ctl = tr(lambda: json.loads(Path(clog).read_text().splitlines()[-1]))`, and build `ctl_seen` only when `ctl` is a dict. Otherwise use the string, so the case prints `[FAIL]` and the suite continues.

### L2 — Low — the `at` check cannot tell local time from UTC on a host whose zone is UTC

**Where:** `scripts/check-idle-stop.py:979`.

**Scenario:** `fixture_git.isolated()` replaces `os.environ`, and `TZ` is not passed through. Inside the suite, measured: `os.environ.get("TZ")` is `None` even when the run is started with `TZ=UTC`. The zone is therefore the host's system zone. On this Mac (PST) the `gmtime(now)` mutant writes `2026-11-16T11:24:00-0800`, which is wrong, and the case catches it. On a host whose system zone is UTC (a typical CI runner), `strftime(..., localtime(n))` and `strftime(..., gmtime(n))` are byte-identical: I measured `2026-11-16T11:24:00+0000` for both under `TZ=UTC`. There the mutant would survive.

**Caveat:** this survival is INFERRED. I did not run the suite on a host whose system zone is UTC.

**Not Blocking:** the gmtime mutant is not in the manifest, and the real code uses `localtime`.

**Fix:** pin a non-UTC zone for this assertion. One way is to set `os.environ["TZ"] = "America/Los_Angeles"` plus `time.tzset()` around the control, if `fixture_git` allows it. Another is to also assert that the `%z` suffix is the local offset computed independently, for a zone known to differ from UTC.

### N1 — Note (no action) — the control's ALLOW is the one verdict it cannot distinguish from a hardwired `"allow"`

The control passes `ALLOW` and the Y1 direct call never writes. A `log_decision` that always logs `"allow"` therefore passes the control (measured). It is caught by the existing #750 three-stop case (BLOCK lines), so nothing escapes. The control's comment claims that "each parameter is varied", which holds for the fixture-variation gate, not for detection on its own.

## Conclusion

The new control does what it says: all six parameters are varied. Ignoring `now`, `cwd`, `session_id` or `verdict` (forced to BLOCK) turns the named Y1 case red. Forcing `verdict` to ALLOW is caught by another case (N1). Ignoring `why` or `path` is detected only as a crash (an earlier case's crash for `why`, and L1 for `path`), not as the named case. It shares no patched state with the Y1 halves. All three gates are green. There is no Blocking finding, and L1 and L2 are for filing.

VERDICT: CONVERGED
