# Round 3 — `fixture-git-isolation` (backlog #373, PR #420) — Claude half

Subject: `4334b444` (worktree `wt-373`), scope `846a2b82..4334b444` read against `origin/master...HEAD`.
Mandate: refute the SPLIT's stable half. Everything below was executed; scratch lived in `mktemp -d` dirs only.

## What held (executed)

| Check | Result |
|---|---|
| 1. Runner over every `scripts/*.py` with `--self-test`, derived by `grep -l -- --self-test` (80 of 84; the 4 without are `m4_base_db`, `regen-skills-doc`, `session-skill-report`, `skill-usage-audit`), all **9** families, on `4334b444` | **720 runs: 0 victim changes, 0 fixture hits, 0 tree hits.** `brief-compose` is 0 in every family on this head (the docs' "now wrapped" figure was measured on `846a2b82`, before the wrap; this run is the head's evidence). `check-plan-code` and `check-paid-caller-arrival` exit 0 here (this worktree has `node_modules`). |
| Nonzero exits in that run | `subject_status` (see M2); `check-run-hook` rc=1 with no tally in `gitdir`, `home`, `xdg` under 10-way parallel load. Re-run serially in those three families: 72/72, victim same, 0 hits each. A load flake, not a finding. |
| 3. Did wrapping change what `brief-compose` / `gen-backlog-page` test? | Imported each module and ran `self_test()` (wrapped) and the inner body (`_self_test_suite` / `_self_test_body`) unwrapped, in the real worktree: **153/153 and 165/165 both ways, per-case output identical line for line** (diffed). No vacuous pass from the empty `HOME`. (`brief-compose.ROOT` is bound from `Path.home()` at import, so the swap does not move it.) |
| 4. Mutations | `--mutate . --only` on this head: guard **45/45 killed, 45 attributed**; `brief-compose` **27/27**; `fixture_git` **12/12**. Every edit anchor occurs exactly once in its file. `sum(EXPECTED_MUTATIONS) == 2303 ==` the entries counted across all 158 manifests, no per-file mismatch. |
| Self-test counts | guard 84/84, `fixture_git` 42/42; 16 files carry the block (as stated); the live guard prints `ok — 16 … 84 file(s) read`. |
| X4 rule | False positive: none found (`as x`, parenthesised item accepted; `**{}` refused correctly, keywords non-empty). |
| "Over master's `scripts/` it refuses 12 builders" | Measured 14 files refused on `origin/master` = 12 builders + the 2 `GIT_SUITES` files. Accurate as worded. |

## Findings

### M1 — Major — the LIMITS are not complete: five accepted shapes run the suite OUTSIDE the block and write the victim; none is named
`scripts/check-fixture-git-isolation.py:39-40` (rule 3, "otherwise the suite has a second, unisolated way in"), `:63-74` (LIMITS).
Not fix-induced (rule 3 and the closed shape date from round 1).

Rule 3 tests that a function the block **calls** is not **named** elsewhere. "Called inside the block" is not "executed inside the block", and "the functions the block calls directly" is not "everything the suite reaches". Reproduction (`probe.py` in a mktemp dir: each program copied beside `fixture_git.py`, `check_source` run on it, then executed with `GIT_DIR` exported to a fresh victim, whole `.git` snapshotted before/after):

| shape (all `guard_rc=0`, all `victim_written=True`) | how it escapes |
|---|---|
| `_body` is a **generator**; `with isolated(): return _body()`; `sys.exit(sum(_self_test()))` | the generator object is returned, the block exits, the body runs on iteration |
| `with isolated(): return map(_case, [...])`; caller does `all(_self_test())` | lazy `map` evaluated after restore |
| `with isolated(): return _body` (uncalled); `sys.exit(_self_test()())` | `_body` is not a Call, so rule 3 never looks at it |
| `_body()` calls `_helper()`; `__main__` also calls `_helper()` | rule 3 is not transitive |
| `class S: def run(...)` builds and runs git; block does `S().run()`; `__main__` also calls `S().run()` | rule 3 only looks at module-level **functions** |
| `main()`, on `--self-test`, calls `_setup()` (builds + `git config`) and THEN the isolated `_self_test()` | not X5: dispatch reaches the isolated entry, and other code runs first |

X5 ("dispatches to a different, unisolated function") names none of these. The brief's bet clause — "no guard-accepted shape escapes isolation unless the limits name it" — is refuted. No existing script does any of them (the 720-run falsifier above). The fix that fits the SPLIT is cheap. (a) Name the class in LIMITS and in backlog #380: *execution deferred past the block (a generator, a lazy iterator or a returned callable), a callee reachable from the suite and also from outside it (rule 3 is direct-call only, functions only), and code the `--self-test` dispatcher runs outside the entry*. (b) Correct rule 3's sentence at `:39-40`, which claims more than it checks. (c) Add one of these reproductions to #380's FAILS-IF list: the child-interpreter design fixes all five, and today's falsifier list would not notice if it did not. A transitive closure over module functions and classes is an optional code hardening; it does not close the deferred-execution shapes.

### M2 — Minor — `GIT_SUITES` is incomplete: four unlisted suites run git on the checkout with the caller's whole environment, and the instrument named as filling the list cannot see them
`scripts/check-fixture-git-isolation.py:28-33, 103-109`; `docs/backlog.md:355` (#373 row: "`subject_status` … builds no repository and touches neither the victim nor a marker"); PR body ("out of scope").

`GIT_SUITES`'s criterion is "suites that RUN git without building a repository". The docstring says the population that fills it is the marker falsifier. That falsifier only sees hooks and `core.fsmonitor`, so it is structurally blind to read-only git. Measured directly instead: each of the 80 `--self-test`s was run with a per-suite `git` shim first on `PATH` (it survives `isolated()`, which passes `PATH`). The shim logs whether `GIT_CONFIG_GLOBAL=/dev/null` is set and whether `HOME` is a `fixture-home-*` dir. Calls with **neither** (the caller's full config):

| suite | calls | what |
|---|---|---|
| `subject_status` | 6 | `git -C <checkout> log -1 --format=… -- <path>` |
| `gen-dashboard` | 4 | `remote -v`, `config --get-regexp ^remote\..*\.gh-resolved$` |
| `check-ci-watched` | 3 | `rev-parse --git-common-dir`, `rev-parse HEAD` |
| `peer-sites` | 1 | `git -C <checkout> diff -U0 definitely-not-a-ref-2026 -- …` |

(`check-banner-armed`'s one such call was traced. It is `begin-plan.py:2135`, which strips every `GIT_*` including the isolation's, and it ran with a sandbox `HOME` under a tmp dir, not the caller's. Not a finding.) None of the four writes a victim or ran a marker in 720 runs, so the bet's letter holds. Their verdicts do depend on the caller, though: **`subject_status` goes 16/17 → 12/17 under `GIT_DIR`, `GIT_DIR`+`WORK_TREE` and `GIT_OBJECT_DIRECTORY`** (runner tally column), because it reads the victim's history. "Out of scope" and "touches neither" are true of writes and markers only. **Fix:** either wrap and list the four, or narrow the criterion's wording to what was measured (git that executes caller config or writes) and say the list was filled by a hook/fsmonitor instrument. Then correct the #373 row and the PR body's `subject_status` sentence: the plant changes its verdict.

### M3 — Minor — fix-induced (r2 X8): the subcommand rule lost builders the round-2 guard caught
`scripts/check-fixture-git-isolation.py:133-146` (`_subcommand` returns None at the first `Starred`), `:101-102` (`SHELL_BUILD`).

Executed against `git show 846a2b82:scripts/check-fixture-git-isolation.py` and the head, each body wrapped in `def _self_test():`:

| body | `846a2b82` | `4334b444` |
|---|---|---|
| `subprocess.run(["git", *ID, "init", "-q", d])` | 1 | **0** |
| `subprocess.run(["git", "-c", "a=b", *ID, "init"])` | 1 | **0** |
| `subprocess.run('git -C "my dir" init', shell=True)` | 1 | **0** |
| `subprocess.run("git --config-env x=Y init", shell=True)` | 1 | **0** |
| `subprocess.run(["git", "log", "--grep", "init"])` | 1 | 0 (the intended X8 fix) |

`["git", *IDENTITY, "init"]` is an ordinary way to write a fixture. The `init` is a visible literal, so the BOUNDS' "assembled where the parser cannot see it" does not cover it. No current script uses these shapes (`grep -nE '\["git", \*'` shows only `*args` wrappers, which the wrapper rule handles). **Fix:** in `_subcommand`, treat a `Starred` as an unknown run of options and keep scanning for the next literal non-option (conservative toward refusal), with a case for `["git", *ID, "init"]`. In `SHELL_BUILD`, accept a quoted value (`"[^"]*"|'[^']*'|\S+`) and add `--super-prefix`/`--config-env` to the value-taking alternation, matching `GIT_VALUE_OPTS`. Each needs a case and a mutation.

⚠ **For the coordinator's thrashing call:** M3 is caused by round 2's fix, in the `guard` component, and round 2 recorded fix-induced `guard` findings (X3, X5, X9). That is two consecutive rounds of fix-induced findings in one component, which is the arming condition in `dev-process.md`. M3's severity is low and the cause is narrow (one fix's scanning rule), so whether that is thrashing or a one-off is the coordinator's judgement, but it should be answered in the round document rather than missed.

### Prose (check 5)
- #373 row, dashboard entry, PR body: counts (16 entries, 84 cases, 45 mutations, 42/12, 2303) match disk. Inaccurate: "LIMITS name the six shapes it does not stop" (M1), and the `subject_status` sentence (M2). The derived 80-script run is cited at `846a2b82` "under 8 families". This round's run on `4334b444`, under all 9, is the head's evidence and could replace it.
- #380 has a real falsifier: a named set of executed reproductions, and an observable (the victim's `.git` changes, or a caller hook runs), plus X9's false refusal. It is incomplete only as M1(c) says.

## Fixes summary
1. M1: name deferred execution, non-transitive callees and code run by the dispatcher in LIMITS and #380, correct rule 3's sentence, and add a reproduction to #380's FAILS-IF.
2. M2: list and wrap the four read-only suites, or narrow `GIT_SUITES`'s stated criterion. Fix the `subject_status` prose.
3. M3: make the Starred scan conservative and widen `SHELL_BUILD`, with cases and mutations.

VERDICT: NOT CONVERGED
