<!-- codex-review: model=gpt-5.5 -->

**Verdict: NOT CONVERGED.** This is not a clean round, so it is neither first nor second consecutive clean round. The red gate is justified: the final tree has fold-caused mutation-sweep failures.

**Findings**

High · instrument · caused by this fold: the new self-test cases can start a nested real mutation sweep when the mutation they are supposed to catch breaks the refusal path.

Concrete exhibit from CI at `56eafeef`, `mutation-sweep (1)`:

```text
✗ mutation 'the shard flags are enumerated again by hand instead of derived ... round 8 M1':
the suite did NOT COMPLETE
(CANNOT RUN — scripts/check-plan-code.py --self-test did not finish in 120s. NOT CHECKED.)
NOT MEASURED — ... measured over shard 1 of 8
```

Same shape in CI shard 4:

```text
✗ mutation '#217: a malformed --shard does not stop the run ...':
the suite did NOT COMPLETE
(CANNOT RUN — scripts/check-plan-code.py --self-test did not finish in 120s. NOT CHECKED.)
```

Cause: the round-8 added cases in [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:4058) call `main(["--mutate", ".", ...])`. If the mutation severs the intended early refusal, self-test enters the real sweep inside a mutation run.

Fix, UNVERIFIED: use an empty temp root for these call-through cases so a severed refusal reaches a fast manifest/count failure, not the real delivered sweep.

High · instrument · caused by this fold: the `shard_dest` prefix-strip mutation survives; the case does not test the prefix-strip behavior it names.

CI shard 2:

```text
✗ mutation SURVIVED — `shard_dest` drops argparse's prefix-strip step, so a leading-hyphen flag name resolves to `_shard_x` where argparse named it `shard_x` — round 8 L1
FAILED — ... 1 survivor(s)
```

I reproduced the core locally without editing tracked files:

```text
mutated_self_test_rc 0
mutated_self_test_tail 177/177 passed
leading_key_raise AttributeError 'Namespace' object has no attribute '_shard_x'
```

The existing self-test uses `shard-x`, which still passes if `lstrip("-")` is deleted. The breaking input is a future key such as `-shard-x`, whose argparse option is `---shard-x`.

Fix, UNVERIFIED: add a case for a leading-prefix key, e.g. `_roundtrip("-shard-x")`, or better drive `SHARD_FLAGS["-shard-x"]` through `main()` and require a sentence rather than `AttributeError`.

Low · instrument · caused by the abstraction shape: keys that collide with existing argparse destinations can traceback or produce misleading sentences.

Measured by monkeypatching `SHARD_FLAGS`:

```text
collision mutate => raise ArgumentError: argument --mutate: conflicting option string: --mutate
collision compare => raise ArgumentError: argument --compare: conflicting option string: --compare
collision self_test => rc=2 CANNOT RUN — --self_test True only means something with --mutate ROOT
collision plan => rc=1 175/177 passed
```

Fix, UNVERIFIED: validate `SHARD_FLAGS` keys against reserved option strings and argparse dests when constructing the parser, and refuse bad internal declarations with one explicit error.

**Verification**

Commands and real outputs:

```text
git rev-parse --short HEAD
56eafeef

python3 scripts/check-plan-code.py --self-test
177/177 passed

independent manifest/count scan:
declared_sum 1210
check_plan_code_declared 105
manifest_entries 1210
check_plan_code_entries 105
anchors 1218
unresolved 0
ambiguous 0
duplicate_anchor_tuples 0

python3 scripts/check-docs.py
Documentation integrity OK

python3 scripts/check-selftest-counts.py
self-test counts: 50 script(s) declare a count, every one verified by running it

python3 scripts/check-anchors.py
anchors: 13 registered, all claimed ...

python3 scripts/check-ratchet-contract.py
ratchet contract OK

python3 scripts/check-vocabulary-collisions.py
✅ no unjustified duplicate mechanism

python3 scripts/check-dashboard-entry.py
ok — an entry block was added
```

Shard runs:

```text
python3 scripts/check-plan-code.py --mutate . --shard0 4/8
OK — delivered scripts mutated: 53 file(s), 151 mutation(s), 151 killed,
151 attributed to the case each names, 0 survivor(s) — measured over shard 5 of 8
```

```text
python3 scripts/check-plan-code.py --mutate . --shard0 0/8
NOT MEASURED ... check-plan-code.py --self-test did not finish in 120s ...
check-rc-contract.py --self-test did not finish in 120s
```

```text
python3 scripts/check-plan-code.py --mutate . --shard0 1/8
✗ mutation SURVIVED — `shard_dest` drops argparse's prefix-strip step ...
NOT MEASURED ... check-rc-contract.py --self-test did not finish in 120s
```

Current PR checks, via `gh pr checks 366`:

```text
mutation-sweep (1) fail
mutation-sweep (2) fail
mutation-sweep (4) fail
mutation-sweep-complete fail
verify fail
mutation-sweep (3,5,6,7,8) pass
schema-gates pass
```

Could not run unsharded `--mutate .`, per constraint. Local shard 2 was voided by timeout after showing the survivor; CI shard 2 is the clean survivor evidence.

**Answers To The Six Questions**

1. A normal fourth key works end to end: `shard2` malformed/empty/out-of-range refused; valid `1/8` parsed; combined with `--shard` refused; without `--mutate` and with `--self-test` refused. A zero-based `shardz` honored `0/8` and refused `8/8`. Colliding keys are bad, as above.
2. Shipped behavior is unchanged in the pure partition check. For `N=3` counts were `404,403,403`; for `N=8` counts were `152,152,151,151,151,151,151,151`; every `--shard0 i/N` slice matched `--shard (i+1)/N`.
3. `_given[0]` is deterministic by dict insertion order. The exclusivity message names every given shard flag, also in dict order, not argv order.
4. The exclusivity message is fine for sane keys. Weird internal keys can make it misleading, especially `self_test`, which reports `--self_test True`.
5. `lstrip("-")` matches argparse’s default prefix stripping for tested prefixed names like `---shard-x`; keys that are only hyphens make argparse raise `TypeError`. The test for this was incomplete, which is the survivor.
6. Counts agree: self-test 177, manifest 105 for `check-plan-code`, declared sum 1210, anchors 1218. PR/dashboard narration is now misleading where it implies the fold’s CI measurement is green; current CI at `56eafeef` is red for real mutation-sweep failures.

**Tried To Refute And Could Not**

I could not refute the normal-key abstraction: `shard2` is parsed, mode-checked, mutually exclusive, and invalid specs refuse. I could not refute shipped `--shard`/`--shard0` slice equivalence. I also could not refute the independent count/anchor figures.

| Severity | Deliverable Or Instrument | Caused By This Fold? |
|---|---|---|
| High | Instrument: self-test call-through can enter nested real sweep and void shards | Yes |
| High | Instrument: `shard_dest` prefix-strip mutation survives | Yes |
| Low | Instrument: `SHARD_FLAGS` accepts dest-colliding keys badly | Yes |

Final note: I restored the failed local mutation’s change to `scripts/check-plan-code.py`. The worktree still shows the pre-existing `docs/explainers/questions.md` and r8 Claude review, plus local memory files that appeared during the run; I did not use or edit them for the verdict.
