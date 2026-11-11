Reviewed head: 2334e26463cf38b28b370178d37c970945b0986f

# suite-cost-a — round 1, Claude half (adversarial, mandate: REFUTE)

Branch `suite-cost-a` (PR #537, backlog #231 / #406). Subject: `git diff origin/master...HEAD` and commit `cf4b409b`.
All probes ran in a scratch copy (`git archive HEAD`, re-initialised as its own git repository), never in the worktree.

## What was run, and the results

| Check | Result |
|---|---|
| `check-usage-pace.py --self-test` | 393/393, rc 0 |
| `goal-tree.py --self-test` | 431/431, rc 0 |
| `check-main-drivable.py --self-test` | 462/462, rc 0 (51 s wall) |
| Consumers: `check-fixture-git-isolation.py` (imports `suite_entries`), `check-agent-long-call.py` and `check-agent-large-read.py` (import check-usage-pace) | 141/141, 43/43, 108/108; the `check-fixture-git-isolation` gate ok |
| Real guard `check-main-drivable.py --report`, HEAD against `origin/master`'s script over the same tree | byte-identical; the gate prints `D2 OK`, rc 0 |
| Manifest entry counts against `expected_mutations.py` | goal-tree 327=327, main-drivable 208=208, usage-pace 175=175 |

## The concerns from the mandate, one at a time

**Purity over the key.**
- `meter_row(line)` reads only `parse_json`, which is `json.loads(text, parse_int=float)`. The one global the suite patches nearby (`RISE_END_S`/`LAST_NIGHT_S`, `check-usage-pace.py:1146`) is not read by it.
- `classify(text, path)`: nothing before the self-test reads a file, an env var, the clock or `sys.version` (I grepped `.exists(`, `read_text(`, `open(`, `environ`, `getenv` and `time.` above `_self_test_body`; the only hits are inside `assess`'s reader and docstrings). The module-level sets (`LIVE_WORLD_NAMES`, `SPAWNERS`, and the others) are never mutated: no `.add`/`.update`/`.clear` on an upper-case name, and no `globals()[...]` write outside fixture strings.
- The five tree helpers read only the tree and constants.
- `_sibling_at` reads the file at `path`, and the key carries `(mtime_ns, size)`. See F1 and F2.

**Shared state and cross-case answers.**
- There is no monkeypatch in `check-main-drivable`'s suite. The `_memo_by_node` key is the identity of a node it keeps alive, and that contract is pinned at the top of the suite (backlog #427).
- An equivalence probe called each of the five helpers, then its `__wrapped__`, then `classify` and `classify.__wrapped__`, over every `scripts/**/*.py` (100 files), shuffled ×3 and interleaved. Result: **300 checks, 0 mismatches**. The cache info was `hits=200, misses=100`.
- A `pace_line` equivalence probe compared HEAD against `origin/master`'s script over 4,000 random logs with both `cut` values. The lines held list, dict, bool, `1e400`, string and missing readings, plus truncated JSON. Result: **0 mismatches**, cache `hits=100135, misses=267`.

**Mutable returns.**
- `Verdict` is `frozen=True` and its `routes` is a `frozenset`.
- `_memo_by_node` freezes what it returns: a set becomes a frozenset and a dict a `MappingProxyType`. Every caller only reads the answer. I checked the call sites at `:407`, `:594`, `:696-698`, `:1353-1354`, `:2274` and `:2322`, and `check-fixture-git-isolation.py:208`: `named | frozenset` gives a set, so nothing breaks.
- `meter_row` can hand back a cached list or dict reading. `pace_line` passes it through `is_number`, which refuses it before anything touches it, and the random probe above included such values.
- `_sibling` now returns one shared module. A caller that writes an attribute leaks it to the next caller: I measured `m.V = 99`, and the next `_sibling("sib").V` was 99. This is documented in the docstring, and no caller in `goal-tree.py` writes a sibling attribute (grepped). The one patcher among the siblings, `_with_legend` (`gen-backlog-page.py:4283`), runs only in that file's own self-test.

**The mutation harness.**
- `check-plan-code.py:run_suite_parts` (`:1154-1156`) runs `subprocess.run([sys.executable, name, "--self-test"], cwd=d, …)` once per mutant. Each mutant therefore gets a fresh interpreter, and every cache here lives in memory only. Confirmed.

**Production effect.**
- The real `check-main-drivable` gate goes through `classify`. Its `--report` output is identical to master's.
- The usage-pace hooks (`.claude/hooks/usage-pace-*.sh`) start a fresh process per invocation.
- `explainer-serve.py` runs `goal-tree.py` as a subprocess (`:1449`) and imports none of the three scripts.
- I found no long-lived importer of any of the three.

## Hand-checked mutations

| Mutation | Result |
|---|---|
| goal-tree: `_sibling_at(name, str(path), 0, 0)` | red on its named case only (430/431) |
| usage-pace: drop `@functools.lru_cache(maxsize=METER_ROW_MEMO)` | red on its named case only (392/393): `meter_row(l_50) is first_50` is False |
| main-drivable: named cases classify under `f"{f.name}"` | red on "the live reconcile reuses the seven named real-guard verdicts" |

The reconcile's hit count, instrumented, is **exactly 7**. So the `>= 7` bound is tight, and losing any one named hit goes red.

## Findings

### R1-F1 — Low — the sibling key's two stamp components are each unwitnessed
`scripts/goal-tree.py:192` (`return _sibling_at(name, str(path), st.st_mtime_ns, st.st_size)`). The case at `:2348-2360` rewrites `V = 1` as `V = 22`, which changes the size **and** the mtime together.

- **Input:** two mutants: `_sibling_at(name, str(path), st.st_mtime_ns, 0)` and `_sibling_at(name, str(path), 0, st.st_size)`.
- **Result:** **both survive, 431/431.** Under the size-only mutant, a same-size rewrite in a later second would hit the LRU entry and be served stale, while Python's own `.pyc` check would have refreshed it.
- **Fix:** add one same-size rewrite with the mtime pushed forward (`os.utime`), and one size change with the mtime pinned. Bind a mutation to each.

### R1-F2 — Low — the `_sibling` docstring promises more freshness than the import system gives
`scripts/goal-tree.py:185-188` says *"a sibling rewritten in this process is imported afresh rather than served stale"*.

- **Input:** write `V = 1`, call `_sibling`, then write `V = 2` (same size, same second) and call it again.
- **Result:** `mtime_ns` differs and the LRU **misses** (a new module object), but `V` is still **1**. The stale value comes from `__pycache__`, whose check is mtime in seconds plus size. With `sys.dont_write_bytecode = True` the answer is 2.
- This predates the PR, since the old per-call import had the same `.pyc` behaviour, so the cache adds no staleness. The docstring should still say what the guarantee is bounded by (`.pyc`: seconds plus size). It should also not imply that `mtime_ns` buys anything beyond that.

## Note (not a finding)
`classify`'s cache is full by the time of the reconcile: `currsize=256=maxsize`, 455 misses. The seven named entries survive because they were inserted late. Inserting more than about 249 distinct `classify` calls between those cases and the reconcile would evict them. The hit case would then go **red** (loud), not silently stale, so it is a maintenance trap, not a defect.

No cache was found that makes a mutant read as killed or survived wrongly, or that makes the real guard return a stale verdict.

VERDICT: CONVERGED
