<!-- codex-review: model=gpt-5.5 -->

**Verification**

Ran from `/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud` at `77316edc`, branch `shard-mutation-sweep`. Dirty file `docs/explainers/questions.md` was ignored as instructed.

```text
$ python3 scripts/check-plan-code.py --self-test

161/161 passed
```

The prompt expected 160; HEAD has intentionally moved to 161 after the r2 fold added the staged-`__pycache__` property case.

```text
$ python3 scripts/check-plan-code.py --mutate . --shard 6/8

OK — delivered scripts mutated: 52 file(s), 149 mutation(s), 149 killed, 149 attributed to the case each names, 0 survivor(s) — measured over shard 6 of 8 (round-robin)
```

Additional executed probes:

```text
$ gh pr checks 366 --repo kujinlee/youtube-playlist-summaries-cloud
mutation-sweep (1..8) pass
mutation-sweep-complete pass
schema-gates pass
verify pass
```

Targeted anchor checks in a staged tree:

```text
#217 main call-site anchor_count 1 -> caught by:
  --shard without --mutate is CANNOT RUN, not a silent whole-manifest run

pure shard_mode_refusal anchor_count 1 -> caught by:
  ⛔ a shard alongside --self-test is refused...
  --shard without --mutate is CANNOT RUN...

child_env bytecode-write anchor_count 1 -> caught by:
  ...no suite the harness spawns may WRITE a cache either...

stage_tree bytecode-read anchor_count 1 -> caught by:
  ⛔ no bytecode cache reaches a staged tree...
```

The `progress=progress)` entry also binds once and dies via its named progress case.

Could not run: unsharded `--mutate .`, per instruction. I did not independently enumerate the coordinator’s “39 of 39 document guards”; I did verify current CI `verify` is green.

**Findings**

### Medium — Nested scrubbed hook observers still drop `PYTHONDONTWRITEBYTECODE`, so the bytecode fix is not complete for nested Python spawns

**Finding.** The main harness spawn is correct: [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:547) runs suites with `env=child_env(d)`, and `child_env` sets `PYTHONDONTWRITEBYTECODE=1`.

But two nested hook observers construct a fresh allow-listed environment and still omit that variable:

- [scripts/check-rc-contract.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-rc-contract.py:295), allow-list at [check-rc-contract.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-rc-contract.py:332)
- [scripts/check-surface-recall.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-surface-recall.py:158), allow-list at [check-surface-recall.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-surface-recall.py:49)

Concrete exhibiting input, run against current HEAD:

```text
parent env: 1
allowlist: ('PATH', 'HOME', 'TMPDIR', 'LANG')
observed: PYC=YES
patched allowlist: ('PATH', 'HOME', 'TMPDIR', 'LANG', 'PYTHONDONTWRITEBYTECODE')
observed patched: PYC=NO
```

That probe used `check-rc-contract.observe()` with a hook that creates `scripts/helper.py` and runs `PYTHONPATH="$ROOT/scripts" python3 -c 'import helper'`. The parent process had `PYTHONDONTWRITEBYTECODE=1`; the observer scrubbed it away; Python wrote `scripts/__pycache__/helper*.pyc`. Adding the variable to the allow-list stopped the write.

This is exactly the spawn path Claude r2 named, and it is still present at `77316edc`. It does not appear to bite today’s shipped hooks, but the current property case says “no suite the harness spawns may WRITE a cache,” and nested scrubbed Python can still write one.

**Proposed fix — UNVERIFIED.** Add `PYTHONDONTWRITEBYTECODE` to the shared allow-list in both `check-rc-contract.py` and `check-surface-recall.py`, and add a property-shaped case that runs a scrubbed hook importing a helper module and asserts no `__pycache__` appears. The existing “allowlists are the same” case is insufficient because both copies can agree on the wrong set.

**Answers To The Four Questions**

1. **Is `PYTHONDONTWRITEBYTECODE=1` sufficient and complete?**  
   For direct suite spawns, yes: `run_suite_parts` uses `child_env`, and shard 6 completed with green re-controls. For inbound caches, yes after the r2 fold: `stage_tree` now ignores `__pycache__`, and the new staged-cache mutation binds and dies. For nested scrubbed observers, no: the finding above is a live bypass.

2. **Was deleting the `.claude/` restore right?**  
   Yes. I staged residue files `_selftest-999999.sh` and `_selftest-999999.marker` under `.claude/hooks/` and ran the three most relevant suites:

   ```text
   scripts/check-ratchet-contract.py rc=0 self-test: 56/56 passed
   scripts/check-surface-recall.py rc=0 58/58 self-test cases passed
   scripts/check-banner-armed.py rc=0 160/160 self-test cases passed
   ```

   I could not construct a current control break from that residue. The deletion looks right.

3. **The two retargeted anchors: still bound and still dying via named cases?**  
   Yes. The `if _mode_why:` call-site entry binds once and dies via `--shard without --mutate is CANNOT RUN...`. The `progress=progress)` entry binds once and dies via `every phase of --mutate reports its position when a caller asks`. The newer bytecode-read and bytecode-write entries also bind once and die via their named cases.

4. **Anything else order-dependent through `__pycache__`?**  
   The inbound repo-cache route Claude r2 found is closed by `stage_tree(..., ignore=shutil.ignore_patterns("__pycache__"))`. The remaining order-dependent route I could exhibit is nested scrubbed Python: a hook observer can write a fresh cache inside the staged tree because its allow-list drops `PYTHONDONTWRITEBYTECODE`.

**What I Tried To Refute And Could Not**

- Current CI green: `mutation-sweep (1..8)`, `mutation-sweep-complete`, `verify`, and `schema-gates` are green.
- Required shard 6/8: green, 149/149 killed and attributed.
- Current self-test: green, `161/161`.
- The inbound `__pycache__` fold: the staged-cache anchor binds and its mutation is caught.
- `.claude/` restore deletion: residue did not break the relevant controls I tried.
- Retargeted anchors: bound once and attributed.

I did refute the claim that Claude r2’s nested-spawn finding was fully folded: the allow-lists still omit the bytecode variable.

**Q4(a)**

| Severity | Aim | Deliverable or instrument | Caused by the fold itself? |
|---|---|---|---|
| Medium | Keep bytecode caches impossible during mutation measurement, including nested hook observers | Instrument | Partly. The allow-list predates the fold, but the fold’s bytecode completeness claim makes the omitted variable load-bearing |

**Verdict**

**NOT CONVERGED**

The big r2 cache-read hole is fixed, and shard 6 plus CI are green. But the nested scrubbed observer path still drops `PYTHONDONTWRITEBYTECODE`, and I reproduced a `.pyc` write through it on current HEAD. That is small to fix, but it sits in the measurement instrument itself, so I would not call this converged yet.
