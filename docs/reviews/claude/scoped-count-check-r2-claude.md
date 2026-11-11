Reviewed head: 17cd4e577aba4fe639894a8b59ccedb5374e516a

# Round 2 — `scoped-count-check` (PR #450) — Claude half

REVIEW GAP: codex — alternation (round 1 ran both halves; §0 Q4c rounds 2–3 run one half each).

Scope: the fold `d5b90f8d..17cd4e57`, then the PR as a whole. Merge base = `origin/master` tip `bf32f927`
(the branch is current). Experiments ran in a throwaway clone of the head with `origin/master` set to the
head (so only the probe's own edits are "the branch"), deleted afterwards. Nothing tracked was edited
except this file.

## What I ran, and what held

| Check | Input | Result |
|---|---|---|
| Touched self-tests | `check-selftest-counts.py --self-test`, `gates-for-pr.py --self-test`, `check-plan-code.py --self-test` | 40/40, 37/37, 281/281 |
| Mutation slices | `check-plan-code.py --mutate . --only scripts/<x>.py --allow-long-local` for both scripts | 23/23 and 12/12 killed, all attributed |
| Scoped gate on this PR (foreground) | `check-selftest-counts.py --changed` in the PR worktree | rc 0, **50 of 75** suites, 3m47s |
| r1 rename false green, retried | `git mv .claude/hooks/run-hook.sh …-renamed.sh`, staged, then committed | `check-run-hook.py` in scope both times — **fixed** |
| NEW: file-load chain two hops deep | `check-anchors.py` names `zz_a.py`; `zz_a.py` loads `zz_b.py` by `spec_from_file_location`; edit only `zz_b.py`, uncommitted then committed | `check-anchors.py` in scope both times — **holds** |
| NEW: helper renamed AND edited | `git mv zz_b.py zz_b2.py` plus a content change, staged then committed (`git diff -M` shows `D`/`A`) | changed set = both names; `check-anchors.py` in scope — **holds** |
| `gates-for-pr` maps the step | `gates-for-pr.py --list` | `--changed --base origin/master … SCOPED locally`; full run printed OUT OF SET as CI's — **holds** |
| CI keeps the full run | `.github/workflows/ci.yml:704` | `run: python3 scripts/check-selftest-counts.py`, unscoped — **holds** |

## Findings

### F1 — Medium · FILE · not fix-induced. A suite that reads the repository by GLOB is never selected by the file it globs: a new guard on its own is a false green

`scripts/check-selftest-counts.py:511` (`reached`) only follows a name: an import of a stem, or a basename
inside a string. `check-main-drivable.py`'s self-test runs over **every real guard**, found by
`live_root.glob(GUARD_GLOB)` (`scripts/check-main-drivable.py:5376`, `GUARD_GLOB = "scripts/check-*.py"`
at `:116`), and no string anywhere holds the name of a guard that does not exist yet.

Ran, in the throwaway clone: added ONLY an untracked `scripts/check-zz-new.py` whose `main()` takes no
argument (so no case can drive it over a constructed world).

- `check-selftest-counts.py --changed` → rc **0**: *"self-test counts: nothing to check (scope: --changed
  against origin/master) — no changed file reaches a pinned suite"*.
- `check-selftest-counts.py --only check-main-drivable.py check-ratchet-contract.py check-guard-coverage.py`
  → rc **1**: *"✗ check-main-drivable.py: --self-test exited 1 — its own cases are red"*; the red case is
  *"…and the committed MAIN_DEBT reconciles against it with no findings"*.
- Control: the same suite with the new file moved away → **455/455 passed**. The red is caused by the new file.

So the claim *"selects every suite whose count can change"* does not hold for the bare shape. It is
bounded in three ways, which is why this is FILE and not a Q4c BLOCKER:

1. The docstring already disclaims *"a dependency built at runtime from pieces"*. A glob is that class,
   though the docstring does not name it, and it should.
2. The realistic shape is rescued, by accident: a new guard ships with an `EXPECTED_MUTATIONS` bump in
   `check-plan-code.py`, and `reached({check-plan-code.py, the new guard, its manifest})` does contain
   `check-main-drivable.py`. That happens only through name-list edges (see F2). Also, a lone edit of each
   of the 59 existing `check-*.py` reaches `check-main-drivable.py`, 59 of 59.
3. Inside `gates-for-pr.py` the hole is covered: `check-main-drivable self-test` is its own GATE in the
   local set (`--list`). The false green reaches a reader only through a standalone `--changed` run, which
   the docstring calls *"the local gate"*.

**Fix (local):** name the glob class in the docstring's NOT-seen sentence. Or, more soundly, let a suite
declare what it globs (for example a module-level `READS_GLOB = "scripts/check-*.py"` that `reached`
matches with `fnmatch` against changed paths). Checked by hand, not exhaustively: the other suites whose
self-test reads live state should be listed when this is fixed.

### F2 — Low · FILE · fix-induced (fold prose). The cost attribution for 50-of-75 is measured wrong, in the code and in the round record

`reached`'s docstring (`scripts/check-selftest-counts.py:514-520`) and the r1 coordinator record both say
the scope grew to 50 *because `check-plan-code.py` holds every script's path as a dictionary KEY
(`EXPECTED_MUTATIONS`)*. I ran `reached` again with every string dict key removed from
`check-plan-code.py`, and then from **all** scripts:

| Variant | PR #450's scope | a lone `check-anchors.py` edit |
|---|---|---|
| as shipped | 50 | 43 |
| `check-plan-code.py` dict keys dropped | 50 | 43 |
| every script's dict keys dropped | 50 | — |

The dict keys contribute **nothing** to the scope. The density comes from name **lists** and sets: the
manifest-list case in `check-plan-code.py`'s own suite (`:4801`, `"scripts/check-anchors.py",` …),
`MAIN_DEBT` in `check-main-drivable.py:124`, and the per-guard tables in `check-fixture-variation.py:166`.
On this PR, `check-plan-code.py` is also edited directly, and 10 pinned suites really do load it by path.
Over all 75 single-suite edits the median scope is **31**, the mean 33.3 and the maximum 75. **Fix:** state the
measured cause, or drop the sentence.

### F3 — Low · FILE · fix-induced. `gates-for-pr.py`'s docstring still says every one-line step runs as written

`scripts/gates-for-pr.py:15-18` (*THE GATE SET IS DERIVED*) lists what becomes OUT OF SET: node, a
multi-line block, another CI variable, `NOT_LOCAL`. It does not mention that a `SCOPED_LOCALLY` step runs
with **different arguments** than CI's. Also, `:154-157` replaces the step's whole `run:` argument list, so
a future CI-side argument on that step would be dropped silently locally. That is harmless today, because
the step has none. **Fix:** one clause in the docstring.

## The precision question: should string edges be narrowed to load sites?

**No. Narrowing misses real dependencies, including round 1's own BLOCKER.** I simulated the narrowing:
strings count only inside a `spec_from_file_location` / `run_path` / `open` call.

| | PR #450's scope | lone `check-anchors.py` edit | `run-hook.sh` rename reaches `check-run-hook.py` | of 5 sampled guards, a lone edit reaches `check-main-drivable.py` |
|---|---|---|---|---|
| as shipped | 50 | 43 | **yes** | 5/5 |
| load-site only | 8 | 3 | **no** | **0/5** |

- **The miss that matters:** `check-run-hook.py` names its launcher through a module constant
  (`LAUNCHER_REL = ".claude/hooks/run-hook.sh"`, `:68`) and reads it with `.read_text()` (`:268`, `:513`).
  That is not a load call. Narrowing brings back exactly the false green both round-1 halves reproduced.
  Most real references bind a name to a constant first, then load the variable.
- **The second miss:** today the name-list edges are what put `check-main-drivable.py` (a live-glob reader,
  F1) in scope when a guard is edited. Narrowing turns all five sampled guard edits into misses.
- **Realistic impact:** narrowing would cut this PR from 50 suites (3m47s) to 8, a saving of roughly two to
  three minutes per local run. The cost is a false green on a launcher rename and on any guard edit that
  breaks drivability. CI still runs the full set, so a miss is caught at the PR rather than shipped, but
  the local gate exists to catch it before the push. **Recommendation: keep the shipped rule.** If
  precision is wanted later, the sound route is a declared-dependency mechanism (F1's `READS_GLOB` idea,
  generalised), not a narrower guess at which strings are loads. The expected count under the rejected
  narrowing is 8 for this PR and 3 for a lone leaf edit.

## Verdict

The fold fixes what it set out to fix. The r1 rename false green is gone at both diff sources. Both edges
now close to a fixed point, and the two new probes I built (a two-hop file-load chain, and a helper renamed
and edited) select the right suite. `gates-for-pr` runs the scoped check locally while CI keeps the full
one. The mutation slices and self-tests are green.

What remains is one Medium that was there before the fold (F1, glob readers) and two Low prose defects
(F2, F3). All three are FILE. None is Blocking or High.

VERDICT: CONVERGED
