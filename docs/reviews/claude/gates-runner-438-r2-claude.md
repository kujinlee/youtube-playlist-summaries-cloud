Reviewed head: f48be5701c961f1278defc5ff742adbc2d70eb08

# Round 2 — `gates-runner-438` — Claude half (adversarial)

REVIEW GAP: codex — alternation (round 1 ran both halves; rounds 2-3 run one half each, `docs/review-method.md` §0 Q4).

**Subject:** `git diff a09cc99c..f48be570` (the fold that REMOVED the skip ledger, the tracer and the digest) and PR #465
as a whole. **Read from a clean detached worktree at `f48be570`**, because the assigned worktree (`wt-438`) had
UNCOMMITTED edits to `scripts/gates-for-pr.py`, `docs/backlog.md`, `docs/dashboard-entries.md` and the r1 coordinator
doc appearing while I read it (they change the docstring count to 35 and wrap `Popen` in `try/except OSError`).
Everything below is about the committed head; where that WIP touches a finding, I say so.

**Claim tested:** every gate in the set runs every time; no non-zero, timed-out, killed or un-run gate reads as passing;
exit 0 only when every gate passed; the set equals CI `verify`'s one-line Python steps with everything else OUT OF SET;
the runner's self-test passes under the runner; nothing removed left a dangling reference.

**Result: the claim holds. I found no path to a false green.** The findings are about the run being red when nothing is
wrong — which matters for a tool whose whole value is its exit code — and none is a BLOCKER under §0 Q4c.

## What I ran

| Check | Input | Result |
|---|---|---|
| Full real battery | `python3 scripts/gates-for-pr.py` (default `--base master`, default `--timeout 300`) in the clean worktree at `f48be570`, `node_modules` symlinked from `wt-438`, `origin/master` = `8fe725ec` | **84 gates, 1,013 s (16m53s), exit 1.** `81 pass · 1 fail · 1 cannot run · 1 timeout · 14 CI steps and jobs out of set`. 81+1+1+1 = 84 = the header's count. Exit 1 is what `exit_code` must return when a FAIL is present — **the exit code matches.** |
| The three non-passes, read from their logs | `076-…`, `080-…`, `081-…` under the run's log dir | FAIL `reference namespaces are qualified` — 8 bare refs in `docs/dev-process.md` / `docs/plugins.md`, files this branch does NOT touch (F2). TIMEOUT `mutations of scripts/check-fixture-variation.py` — at mutation 24 of 42 when killed at 300 s (F1). CANNOT RUN `mutations of scripts/check-plan-code.py` — `REFUSED LOCALLY — this run would take over 19.2 min here (local budget 10 min); … 149 mutation(s)` (F1). **None of the three is a defect in this PR.** |
| Self-test at head, standalone | `python3 scripts/gates-for-pr.py --self-test` (clean head; the WIP tree prints 35/35) | 33/33 by count of `case(` calls reached; and **inside the battery, under `run_gate`, `gates-for-pr self-test` PASSED (12.9 s)** — the r1 X5/C2 recursion is gone. |
| `Declared self-test counts match the suites` inside the battery | head docstring `# 33 cases` | PASS (293.5 s — see F3) |
| The set against `ci.yml`, independently | `grep -E '^\s+run: python3 '` over the `verify` job's lines (26-957), `"origin/$GITHUB_BASE_REF"` → `origin/master`, sorted, diffed against `--list`'s `GATE … ci.yml job verify` lines | 81 one-line `python3` steps in CI; 80 gates in the runner. The ONE difference is `check-test-counts.py --results jest-results.json`, which is `NOT_LOCAL` and printed OUT OF SET. The two multi-line PR-only Python steps (`check-dashboard-entry`, `check-review-recorded`) are OUT OF SET as multi-line. Every non-`verify` job (`mutation-sweep`, `mutation-sweep-complete`) and `schema-gates.yml` are printed. **The set matches.** |
| Every path out of `run_gate` (`scripts/gates-for-pr.py:200-216`), by reading | — | `wait` returns → `rc` bound. `TimeoutExpired` → `_kill` (`killpg` + `p.wait()`) → `rc = p.returncode`, status forced to TIMEOUT by `timed_out` whatever `rc` is (`:184`). Any other `BaseException` → kill and re-raise. `rc is None` or negative → KILLED (`:186`). `exit_code` (`:191`) returns 0 only if every tally key is PASS. **pyright's "`rc` possibly unbound" is a false positive on the committed code** — no path reaches `Outcome(...)` with `rc` unassigned. The one path pyright could not see is `Popen` raising (`OSError`): it is NOT caught, so it escapes `main` as a traceback, exit 1, no summary line and the remaining gates unrun (F5) — loud, never green. The uncommitted WIP catches it as CANNOT RUN. |
| `exit_code({})` | `:191-197` | returns 0 — "no gates" would be green. **Unreachable from `main`**: `ci_gates` refuses an empty set (`:147-148`), and the self-test pins that refusal. Noted, not filed. |
| Derivation probes | `ci_gates(WF_HEAD + <step> + <the NOT_LOCAL step>, "master")` for each step shape below | `env:` → IN the set, env dropped; `working-directory:` → IN, ignored; `continue-on-error: true` → IN (stricter than CI: fine); `if: github.event_name == 'pull_request' && steps.x…` → IN; `if: "!(github.event_name == 'pull_request')"` → IN (stricter: fine); `run: python3 scripts/a.py && python3 scripts/b.py` → gate `a.py` with args `('&&','python3','scripts/b.py')`; `run: python3 scripts/a.py > /tmp/x.json` → args `('>','/tmp/x.json')`. No live `ci.yml` step has any of these shapes today (F4). |
| Dangling references to the removed ledger/tracer | `grep -rn` for `last-green`, `.claude/gates-for-pr`, `sitecustom`, `digest`, `SKIPPED` outside `docs/reviews/` | Only the docstring's own history paragraph (`:23-26`) and backlog row 438's account of the removal. `.gitignore` line reverted; `EXPECTED_MUTATIONS` 23 → 10 matches `scripts/mutations/gates-for-pr.json` (10 entries); `EXAMINED_KEYS` lists only symbols that exist; `ci.yml`'s comment updated. **Nothing dangles in the repository.** On disk, the main checkout still holds an untracked `.claude/gates-for-pr/` (the r1 ledger dir), now un-ignored — delete it locally so it cannot be `git add -A`'d. Not a repo finding. |

## Findings

### F1 — Medium — FILE — not fix-induced — on a PR that edits `check-plan-code.py`, the runner can never exit 0

**Where:** `mutation_targets` (`scripts/gates-for-pr.py:158-165`) puts a slice in the set for every moved script with a
manifest; `DEFAULT_TIMEOUT = 300` (`:53`). **Input:** this PR, which edits `scripts/check-plan-code.py` (the
`EXPECTED_MUTATIONS` pin) and `scripts/check-fixture-variation.py` (`EXAMINED_KEYS`). **Observed:** the
`check-plan-code.py` slice is REFUSED by that script's own local budget (149 mutations × 8 s ≈ 19 min > 10 min) →
CANNOT RUN, every time; the `check-fixture-variation.py` slice (42 mutations) is killed at 300 s at mutation 24 →
TIMEOUT, every time on this machine. Both are structural: no edit to the PR can make them pass locally, and the owner's
rule (2026-10-25) is that the full sweep is CI's. **How often:** 18 of the last 40 first-parent commits on
`origin/master` touch `scripts/check-plan-code.py` — any PR that adds or retires a mutation bumps its pin. So for roughly
half of PRs the battery's best possible result is exit 2. That is safe (never green), but a gate red from birth gets
ignored (backlog #56), and then the one real FAIL in the same run is read past — which is exactly what happened in this
run: the real-looking FAIL sat between two structural non-passes. **Not fix-induced:** r1's head touched both files too,
and neither r1 real run exited 0 (Codex r1: `2 cannot run, 1 timeout`). **Fix direction (FILE):** a slice the local
budget will refuse is OUT OF SET with that reason (`check-plan-code` can be asked for its estimate without running), and
a slice's timeout is derived from that estimate rather than the per-gate default.

### F2 — Medium — FILE — not fix-induced — a branch behind its base gets a false FAIL from the PR-only gates

**Where:** the PR-only rewrite (`:138`) passes `--base origin/<base>`; the guard then diffs `origin/master` against
`HEAD`. **Input:** this branch, merge-base `549cfb4d`, `origin/master` at `8fe725ec` (PR #458 rewrote
`docs/dev-process.md` and `docs/plugins.md`). `git diff --stat 549cfb4d HEAD -- docs/dev-process.md docs/plugins.md` is
EMPTY; `git diff --stat origin/master HEAD -- …` is 173+/74−. **Observed:** `reference namespaces are qualified` FAILS
with 8 bare `#N` in those two files — master's own pre-#458 text, seen as "added" by a branch that never touched it. CI
runs on the merge ref and would not see them. False RED, never false green, but nothing in the output says the branch is
behind. **Fix direction (FILE):** print `HEAD is N commits behind origin/<base> — PR-only gates compare against it;
rebase, or read their FAILs as possibly about master's changes` before the run (`git rev-list --count HEAD..origin/<base>`).

### F3 — Low — FILE — not fix-induced — one ordinary gate runs at 98% of the per-gate timeout

`Declared self-test counts match the suites` (`check-selftest-counts.py`, which runs every suite) took 293.5 s against
`DEFAULT_TIMEOUT = 300` in this run (the machine was shared with other agents). Under slightly more load it is a TIMEOUT
→ exit 2 with nothing wrong. Never a false green. Either raise the default or give gates known to fan out their own
budget.

### F4 — Low — FILE — not fix-induced — a step's `env:`, `working-directory:` and shell operators are silently dropped

`step_keys` (`:100-109`) reads only `name`/`run`/`if`; `PY_RUN` takes the rest of the line through `shlex.split`
(`:146`). Probed above: an `env:` step runs without its env; `&& python3 scripts/b.py` becomes ARGUMENTS to `a.py` and
`b.py` never runs; `> /tmp/x.json` becomes arguments. **No live step has these shapes**, so today's set is exact. The
docstring's promise is that everything the runner cannot reproduce is printed OUT OF SET; these shapes would be run
wrongly instead. Fix: a step with `env:`/`working-directory:`/`shell:`, or a `run:` containing an unquoted shell
operator, is OUT OF SET with that reason.

### F5 — Low — FILE — not fix-induced — `Popen` failing aborts the battery with a traceback

At `:204`, an `OSError` from `Popen` (cwd missing, interpreter gone) escapes `run_gate` and `main`: exit 1, no summary,
the remaining gates unrun. Loud, so not a false green. **The uncommitted WIP in `wt-438` already turns it into CANNOT
RUN with a reason in the log and adds two cases**; if that lands, F5 is closed — but it was not on the reviewed head.

## Round shape

Fix-induced findings: **0**. The fold removed ~540 lines and every r1 finding with them; nothing the fold added produced
a finding. Every finding is FILE; none is a BLOCKER (§0 Q4c) — none produces a false green, and the claim the round was
asked to refute holds on every part I could test, including one full real battery whose exit code matches its lines.

VERDICT: CONVERGED
