Reviewed head: 4565f2b2e6af1912d914c30fb3db8720809f06ee

# sweep-affine-shards — round 1, Claude half (backlog #588, PR #590)

**Range:** `origin/master..4565f2b2` on branch `sweep-affine-shards`: `scripts/check-plan-code.py` (the cost
partition, `sweep_shard`, `parse_sweep_costs`, `shard_refusal`, the `main` PARTITION line), the new
`scripts/sweep-costs.py`, `scripts/sweep-costs.json`, the fixture log, three mutation manifests, ci.yml
comments, the backlog rows for #588 and #231, and the dashboard entry.

**Method.** Every claim below marked EXECUTED was run. All runs used the worktree's own modules through
`importlib`, or a **temporary copy outside the repository** for the mutations. Nothing was run inside the
tree while Codex worked, and no `git` command changed the tree.

- EXECUTED: `python3 scripts/check-plan-code.py --self-test` → `471/471 passed`, rc 0, 29 s.
- EXECUTED: `python3 scripts/sweep-costs.py --self-test` → `16/16 passed`, rc 0.
- EXECUTED: property sweep of `sweep_partition`/`sweep_shard`. It used 1,500 random cases plus the real
  manifest (5,151 mutations, 95 costed targets), at N ∈ {1, 2, 37, 38, 39, count−1, count, count+5}. Each
  case also covered all-zero costs, one dominant item, ties and float costs. All of these HELD:
  - coverage
  - disjointness
  - order preserved
  - exactly N parts
  - no empty part where count ≥ N
  - the docstring's BOUND
  - `sweep_shard(i) == sweep_partition()[i-1]`

  The real N=38 cut takes 0.04 s (in-process). Its estimated slowest/fastest shard is 752.8 / 711.0 s.
- EXECUTED: determinism. The inputs are integer ms, the manifest glob is sorted, and the table path is
  relative to the root. A table re-serialised with shuffled key order gives an identical partition, so 38
  independent shards cannot disagree. **No defect.**
- EXECUTED: all 13 `scripts/mutations/sweep-costs.json` entries, on a temp copy. Each went red through the
  case its manifest names.
- EXECUTED: the 18 `check-plan-code.json` entries that name #588, on a temp copy. The result is in
  *Mutation re-run* below.
- EXECUTED: five mutations of my own (R1–R5), listed below.
- UNVERIFIED: real CI wall-clock. I compared only the model's own estimates. This PR's CI run had not
  finished when I reviewed it.

---

## M1 — MAJOR — a table that PARSES but no longer describes the manifest is used silently, and can make the slowest shard WORSE than round-robin

**Where:**
- `scripts/check-plan-code.py:1666-1673` (`_item_cost`): an unknown target is costed at
  `costs["mutation"]`/`costs["fixed"]`.
- `:1655` (`load_sweep_costs`) and `parse_sweep_costs`: they validate the table's SHAPE only.
- `:8096-8100`: the fallback WARNING fires only when `_costs is None`.

**Input (EXECUTED, `t2.py`).** Every row uses the model's own `shard_estimate` against the CORRECT table
as the measure of truth:

| Table fed to the cut | parses? | fallback? | true slowest shard |
|---|---|---|---|
| the committed table | yes | no | **753 s** |
| round-robin (today's behaviour) | — | — | **1,215 s** |
| keys lack the `scripts/` prefix (every target "unknown") | yes | **no** | **2,280 s** |
| all-zero costs | yes | **no** | 2,439 s |
| table lacks only the costliest target (`scripts/check-plan-code.py`, e.g. after a rename) | yes | **no** | **3,216 s** |
| table lacks the 3 costliest targets | yes | **no** | 3,408 s |
| table lacks the 10 costliest targets | yes | **no** | 2,458 s |

In every one of those rows the cut is worse than round-robin, and most of them are past the job's
1,800 s cap. None of them reaches the fallback. The cause is that the defaults are **medians**:
fixed 0.63 s, mutation 1.992 s. A median is the optimistic guess for exactly the target that matters,
the big expensive suite that was renamed or is new. The greedy cut then packs that target's whole block
into one shard. Two facts show this is already happening:
- `scripts/sweep-costs.py` is in the manifest and is **already uncosted** in the committed table.
- Nothing measures table staleness: no source-run age, and no coverage of manifest targets.

Round-robin is the safe failure. This design falls back to it only for an *unreadable* table, while a
*misleading* table does more damage and is accepted without a word.

**Fix (any one closes the hole; the first two together are the robust form):**
1. Score the table's coverage against the manifest in `load_sweep_costs`, or wherever `main` already has
   `_muts`. If more than a small fraction of the mutations, say 5%, belong to targets the table does not
   cost, return `(None, "covers only k of n mutations")`. The run then goes ROUND-ROBIN through the
   existing loud path.
2. Make the unknown-target default **conservative**: the table's max or p90 per-mutation and fixed
   cost, not the median. An uncosted target then gets spread out rather than packed.
3. Add a whole-manifest case: every manifest target is a key of the committed table. It goes red when a
   new or renamed script lands without a table refresh. A self-test case against the real tree is
   enough.

## M2 — MINOR — the fallback is a GREEN job with a stderr line; no annotation, and the WARNING line is pinned by nothing

**Where:** `scripts/check-plan-code.py:8099`, which prints the stderr `WARNING — …`. The stdout `PARTITION —`
line is printed just above it.

**Input (EXECUTED, my mutation R3):** I deleted the stderr WARNING print. The suite stayed 471/471 apart
from the temp copy's ambient `node_modules` cases. **No case notices.**

A round-robin shard does pass, so the only consequences of a fallback are a slow sweep and a log line
inside one of 38 collapsed jobs. ci.yml already uses `::warning::` annotations elsewhere, for example
around lines 189-340 and 1413, and those surface on the run summary.

**Fix:**
- Emit `::warning title=sweep partition::…` when `GITHUB_ACTIONS` is set, alongside the existing line.
- Add one case asserting that the fallback prints it: stderr captured, under a fixture root with no
  table.

## M3 — MINOR — `sweep-costs.py` crashes with a traceback, not `Refused`, on malformed input that its regexes accept

**Where:**
- `scripts/sweep-costs.py:81` and `:83`: `int(env.split(":", 1)[1])`.
- `:60-62` `_secs`: `dt.datetime.fromisoformat`.

**Input (EXECUTED, `t4.py`), each run against the committed fixture log:**
- `SHARD_INDEX: four` → `ValueError: invalid literal for int()`
- a timestamp `2026-13-15T01:21:33` → `ValueError: month must be in 1..12`

Both are uncaught, so the tool's own contract fails: every other bad input gets a `Refused` reason.

**Fix:** wrap both conversions and raise `Refused(f"{label}: …")`. Add one self-test case per input.

## M4 — MINOR — `sweep-costs.py` attribution and tabulation accept inputs that skew the table

**Where:** `scripts/sweep-costs.py:184-208` (`tabulate`) and `attribute`.

**Input (EXECUTED or read):**
- **Duplicate shard logs.** Two logs for the same (index, total), such as a re-run attempt downloaded
  next to the first, pass the `seen` check. The `seen` set dedups for the run-completeness test, yet both
  logs' timings are pooled, so that shard's targets count twice in every median and mean. The fix is to
  refuse a second log for a seen (index, total), or keep only the last.
- **Seed count not checked.** A log from a `schedule` run, which by the ci.yml comments runs more than one
  seed, is accepted. Its per-target time can then be up to twice a PR run's. EXECUTED: I injected an
  `EVENT: schedule` env line and the log was accepted. The fix is to read the event/seed env lines and
  refuse a mix, or normalise per seed.
- **Truncated label (nit).** A progress label of `…` matches ANY expected name at that position in
  `attribute`, which weakens the order check that is its whole defence. EXECUTED: a manifest with a
  different name at that position was accepted.

## M5 — MINOR — the docs compare a predicted WORK-ONLY figure with a measured WALL clock, which overstates the gain about 1.3x

**Where:**
- the dashboard entry, 2026-11-14 (`docs/dashboard-entries.md`)
- the backlog #588 row (`docs/backlog.md:567`)
- the ci.yml comments at `:1162-1166` and `:1270-1273`

They put the predicted 746 s cut ("about 25 → about 13 minutes") beside measured job wall-clocks of
1,438-1,611 s.

**Input (EXECUTED):** the model's own like-for-like estimate of round-robin on the current manifest is
**1,215 s**. So the predicted improvement is 1,215 → 753 s, about **1.6x**, not about 2x. "That fixed
cost is about half" is **38-41%** by the same model. The "~63 targets" figure is consistent with the 59-68
measured.

**Fix:** state both numbers on one basis (model → model). If one of them is a wall clock, label it as one
and add the non-modelled overhead the job pays: setup, install and upload.

## M6 — MINOR — the BOUND case is loose; balance is pinned by one case

**Where:** the `#588` self-test cases at `scripts/check-plan-code.py:5813-5960`.

**Input (EXECUTED, R1/R5 below):** in the bound case at N=7, target `b`'s whole block (201 s) already
fits inside the asserted bound (~278 s). A cut much worse than greedy-optimal therefore still satisfies
it. Doubling the final cap (R1), and a wrong bisection lower bound (R5), were caught only by the separate
"beats a COUNT cut by over 1.5x" case.

The suite does kill both mutations, so this is not a hole today. It is one case away from one.

**Fix:** add an exact-partition assertion on one small fixture (the expected parts written out), so a
looser cap goes red on two cases rather than one.

## N1 — nit — a nested `main()` call leaks a `PARTITION —` line to the self-test's stdout

`--self-test` prints one stray `PARTITION — ROUND-ROBIN FALLBACK: no cost table at …` line before
`471/471 passed`. A wiring helper's `main()` call writes it without capturing stdout. The output is
harmless, but a consumer that parses this output (the mutation harness reads the `n/m passed` line)
would now see one extra line. Capture it at the call site.

## Checked and NOT a defect

- **Pyright Optional warnings** at `sweep-costs.py:93-97` and `:169-171`. `verdict`/`vm` are read only
  after `end`/`VERDICT` matched. `spec` is built from a `.py` path whose existence was already checked.
  Both are safe.
- **Diff-scoped `--select` pool on PRs**, `check-plan-code.py:2269-2278`. It is cut by the same partition,
  the refusal is correctly skipped for it, and an empty shard returns a green `Measured(…0…)`. A
  346-mutation pool at N=38 splits cleanly (EXECUTED).
- **`shard_refusal`.** It applies only to the whole manifest, which is what it should be.
- **Every self-test case named #588.** Each fails for the reason its name gives (the mutation re-run
  below). The round-robin fallback's property cases still hold.

## Mutation re-run (temp copy, outside the repo)

- `scripts/mutations/sweep-costs.json`: **13/13** killed, each by its named case.
- `scripts/mutations/check-plan-code.json`, the 18 entries naming #588: **18/18** killed, each by its named case.
- My own extras:

| id | mutation | killed? | by |
|---|---|---|---|
| R1 | final cap doubled | yes | "beats a COUNT cut by over 1.5x" only |
| R2 | force-split picks the CHEAPEST run | yes | "fewer greedy runs than N are FORCE-SPLIT" |
| R3 | stderr fallback WARNING removed | **no** | — (M2) |
| R4 | unknown-target fixed default halved | yes | "an UNKNOWN target is costed at the table's defaults" |
| R5 | bisection lower bound starts at hi//2 | yes | "beats a COUNT cut by 1.5x", "zero-cost table" |

## Verdict

One MAJOR finding (M1): the fail-open path for a table that parses but is wrong or stale. It can make the
sweep slower than the round-robin it replaces, and nothing says so. The remaining findings are MINOR.
The partition itself held: correct, deterministic and well tested.

VERDICT: NOT CONVERGED
