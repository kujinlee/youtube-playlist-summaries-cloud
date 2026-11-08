Reviewed head: 551701f76e5aa7f410b71dc130147d04b096d3f9

# suite-cost-b (PR #538; backlog #558 + #231): round 1, Claude half

Mandate: REFUTE. Scope: `git diff origin/master...HEAD` (origin/master = `bd1284b4`), mainly
`scripts/check-plan-code.py` and `scripts/mutations/check-plan-code.json`, and the PR body.

## What I ran, and what it showed

| Check | Result |
|---|---|
| `python3 scripts/check-plan-code.py --self-test` in the worktree | **389/389 passed**, rc 0 (70 s wall, on a loaded machine) |
| Old vs new `_walks_dir` (`__wrapped__`, so the cache is bypassed) over every `scripts/*.py` of BOTH trees (198 files) x 11 directories (`scripts`, `docs`, `docs/reviews`, `docs/reviews/claude`, `scripts/mutations`, `lib`, `tests`, `.claude`, `.github`, `app`, `supabase`) | **2,178 comparisons, 0 differ** |
| ...over the 3 tracked `*.py` outside `scripts/` | 3 of 3 the same |
| ...over 37 constructed inputs (below) | **37 of 37 the same** |
| 3 sampled new mutations, each applied in a full `git archive HEAD` copy with an unmutated control copy beside it | each adds exactly ONE `[FAIL]`, its named case (below) |
| Call paths that still use the flat default | ONE, unreachable from `mutate_delivered` (R1-F2) |

**The "identical answers on all 99 `scripts/*.py`" claim holds**, and holds wider than stated (the 99 on master too, and
11 directories). **The 3 sampled mutations go red on their named case.** The control copy fails 3 cases of its own
(`node_modules/typescript` is not in a `git archive`); every mutant copy fails those same 3 plus its named one:

| Manifest index | Mutation | Extra `[FAIL]` |
|---|---|---|
| 232 | the fixpoint's `grew = True` -> `False` | "...a name assigned from one assigned LATER in the scope is still tainted": got False want True |
| 237 | `min(SUITE_TIMEOUT_CEILING, ...)` -> `min(float("inf"), ...)` | "...a very slow one is CAPPED": got 200000.0 want 600 |
| 249 | the per-seed division dropped | "under 2 seed(s) ... PER-SUITE time": got `[None, None, False x4]` want `[None, None, True x4]` |

**The constructed `_walks_dir` inputs**, all identical old vs new: a nested def reading an outer name, and the reverse
(an inner def's assignment read by its outer def's lister); a class inside a def; a method; a method reading a class
attribute; a class-body lister reading a module name; a class under a top-level `if`; comprehensions in a def and at
the top level; a generator expression in a class body; a lambda in a class body; `global` set in a sibling; `nonlocal`;
a rebinding AFTER the lister call; a walrus; a `with`; lambda and def defaults; a decorator lister, and a decorator
reading a name the decorated def rebinds; `ls-files` literal, through a name, and unrelated; an attribute subject; an
augmented assignment; a tuple target; a three-scope chain; a def under a top-level `if`; `async for`; `*args`; a
keyword; one file vs a glob; an `except` binding; `match`; a syntax error; 40 nested defs.

By reading, the rewrite is equivalent: a node is in `ast.walk(f)` exactly when `f` is an ancestor of it, which is what
`scopes_of` returns; the top-level membership rule (its top-level statement is not a def or class) is the old `top`;
`facts` is keyed by `id` of nodes `tree` keeps alive; the shared `Load`/`Store`/operator singletons that overwrite
`parent` entries are never flows, calls or constants, so `scopes_of` is never asked about them. Several FALSE answers
above (a `global` set in a sibling, a lambda or def default, `ls-files` held in a name) are the same on master, so they
are pre-existing blind spots (the docstring's "NOT SEEN") and not regressions.

**Control vs re-control:** the control runs under the flat `SUITE_TIMEOUT` (`check-plan-code.py:1960`, no `limit=`),
and the mutants and the re-control under `limits[name]` (`:1973`, `:2007`, `:2100`, `:2103`). The re-control's limit is
therefore always >= its control's, by design: it lets a green-but-slower re-control pass. It cannot make a red read
green, and a re-control past its limit is still rc 2, not green.

**Can a slow control mask a real hang?** No, not as a verdict. Because the control itself runs under the flat 120 s,
`control_seconds` per suite is at most ~120 s, so `limits[name]` is at most `SUITE_TIMEOUT_CEILING` (600 s) per suite
run, and a mutant over it is still rc 2, CANNOT RUN, never a catch (`run_mutations` reads rc 2 as `did NOT COMPLETE`).
What a slow control CAN do is give a hang five times as long to run, and that is a cost to the job's budget, not to
its verdict (R1-F1).

## Findings

### R1-F1 — Medium — the 600 s ceiling bounds one suite run, not the shard: a single hung mutant of a slow target now takes the shard's whole headroom

`scripts/check-plan-code.py:124` (`SUITE_TIMEOUT_CEILING = 600`), `:1211` (`suite_limit`), `:1973`;
`.github/workflows/ci.yml:1055` (`timeout-minutes: ${{ github.event_name == 'schedule' && 60 || 30 }}`).

**Input:** any target whose control runs at >= 30 s per suite on the runner. 20 x 30 = 600, so every one of its mutants
and its re-control runs under the 600 s ceiling. By the PR's own measurements `check-fixture-variation.py` takes
35-43 s under load in CI, which puts it at the ceiling; `check-plan-code.py`'s suite (~27-35 s locally per the PR body;
70 s wall in this review on a loaded machine) is in the same range and carries 254 entries, about 10-11 per shard at
N=24.

**Result (arithmetic, from the numbers recorded in `ci.yml`):**

| | flat 120 s (master) | this branch, a target at the ceiling |
|---|---|---|
| one hung mutant, push/PR (1 seed) | 120 s | 600 s |
| one hung mutant, schedule (2 seeds, `seed_runs` runs every seed) | 240 s | 1,200 s |
| a hung re-control, schedule | 240 s | 1,200 s |
| slowest shard measured (N=24, run 41564172713) | 1,111 s | 1,111 s |
| headroom inside `timeout-minutes: 30` | 689 s: ~5 hung mutants fit | 689 s: **one** fits, two exceed 1,800 s |

The schedule's slowest shard is PREDICTED at ~2,400 s in `ci.yml` itself (not measured), which leaves ~1,200 s inside 60
minutes: exactly one hung mutant at the ceiling.

**Why it matters although it fails closed:** a job killed by `timeout-minutes` is not green (the sweep's aggregate
`needs.mutation-sweep.result` cannot be `success`), so no verdict is forged. But the harness's own `CANNOT RUN — <name>
--self-test did not finish in 600.0s` line, which names the hung mutant, is never printed; every later verdict in the
shard, survivors included, is lost; and the shard reads as an infrastructure timeout. That is the failure mode the
PR's constants block claims to bound ("an infinite loop still times out — after at most 600 s instead of 120"): the
claim is true per suite run, and silent on the job. The mutation most likely to produce a real hang is exactly the
kind this PR adds (`grew = False -> True` in a fixpoint, an index increment dropped in the new BFS loop), and they all
target `check-plan-code.py`, one of the slow suites.

**Possible fixes (the author's choice):** derive the ceiling from the job budget left rather than a constant; or fall
back to the flat limit for a target after its first timeout; or state the per-shard bound in the constants block and
add it to `ci.yml`'s shard arithmetic. No case pins any of this today.

### R1-F2 — Low — `run_mutations`' seeded-without-trees branch drops `limits`, so that path still runs under the flat 120 s

`scripts/check-plan-code.py:2054`:

```python
            return run_mutations(d, muts, known, progress, seeds, seed_trees(d, seeds, cleanup))
```

`limits` is not forwarded, and `seed_runs` (`:397`) does forward its `limit`, so this is the one hand-off the threading
missed.

**Input:** `run_mutations(d, [one mutation on m.py], {"m.py"}, seeds=(3, 5), limits={"m.py": 333.0})` with `trees`
omitted, and `run_suite_parts` replaced by a recorder.
**Result:** the recorded limits are `[None, None]`, i.e. the flat `SUITE_TIMEOUT` under both seeds. The same call
unseeded records `[333.0]`.

Not reachable from `mutate_delivered` today, which always passes `trees` when `seeds` is set (`:1940`), so this does
not change a CI verdict. It is a latent instance of exactly the class the PR set out to close (`check-fixture-variation`
already found the direct-call variants once), and no case or manifest entry covers it: the direct case at `:2863` is
unseeded, and manifest entries 243-253 cover every other hand-off. Fix: pass `limits=limits` there, and add the seeded,
tree-less call to the direct case.

## Not findings (checked)

- `suite_limit` arms: `None` -> 120; `0.5` -> 120 (floor); `15.8` -> 316; `10_000` -> 600. Always finite; a 0-second
  control is floored. A FAILED control sets no limit (`continue` comes before `:1973`), and its run returns before
  `run_mutations`.
- Per-seed division: `control_parts` runs the suite once per seed, so `control_seconds / len(seeds)` is per suite; the
  unseeded `max(1, len(())) = 1` path is right.
- `limits` is keyed by `targets`, which is the set of `m["file"]`, the same string `run_mutations` looks up.
- The two new self-test cases that monkeypatch `subprocess.run` and `run_suite_parts` restore them in `finally`.

VERDICT: NOT CONVERGED
