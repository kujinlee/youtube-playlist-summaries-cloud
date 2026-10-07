<!-- codex-review: model=gpt-5.5 -->

**Verification**

Required commands run:

```text
python3 scripts/check-rc-contract.py --self-test
rc contract: 6 code(s) defined, 4 handled by an arm, 2 declared unhandled
rc contract OK — every defined code is handled or declared, and no arm is dead. What the READER sees is check-surface-recall.py's rule, not this one
56/56 self-test cases passed

python3 scripts/check-surface-recall.py --self-test
surface-recall: 6 declared sentence(s), run against the REAL hook in the REAL repo
surface-recall OK — every declared code renders exactly its approved sentence
59/59 self-test cases passed

python3 scripts/check-plan-code.py --self-test
161/161 passed

python3 scripts/check-plan-code.py --mutate . --shard 5/8
OK — delivered scripts mutated: 54 file(s), 150 mutation(s), 150 killed, 150 attributed to the case each names, 0 survivor(s) — measured over shard 5 of 8 (round-robin)
```

Extra verification run because this component spans shards 5 and 8:

```text
python3 scripts/check-plan-code.py --mutate . --shard 8/8
OK — delivered scripts mutated: 50 file(s), 150 mutation(s), 150 killed, 150 attributed to the case each names, 0 survivor(s) — measured over shard 8 of 8 (round-robin)
```

Targeted temp-copy mutation run over the four component entries:

```text
control scripts/check-rc-contract.py: rc=0; last=56/56 self-test cases passed
control scripts/check-surface-recall.py: rc=0; last=59/59 self-test cases passed
run_mutations ok: True
survivors: []
rc #16 fails: ['the env the scrub hands the production spawn carries PYTHONDONTWRITEBYTECODE — r4 Medium']
rc #17 fails: ['the env the scrub hands the production spawn carries PYTHONDONTWRITEBYTECODE — r4 Medium']
surface #20 fails: ['the subprocess env allowlist is the SAME in both guards — round 8 H1', 'the env the scrub hands the production spawn carries PYTHONDONTWRITEBYTECODE — r4 Medium']
surface #21 fails: ['the env the scrub hands the production spawn carries PYTHONDONTWRITEBYTECODE — r4 Medium']
```

Temp-copy pyc route measurement:

```text
before pyc: []
unset run rc: 0
unset run last: 59/59 self-test cases passed
after unset pyc: ['scripts/__pycache__/check-rc-contract.cpython-314.pyc', 'scripts/__pycache__/check-ratchet-contract.cpython-314.pyc']
env=1 run rc: 0
env=1 run last: 59/59 self-test cases passed
after env=1 pyc: []
```

Could not run: unsharded `--mutate .`, by instruction. CI state was not re-queried.

**Findings**

No Blocking, High, Medium, or Low finding against the r4 fold.

Proposed fixes: none. No UNVERIFIED fix is owed from this review.

**Answers To The Six Questions**

1. Capture fidelity: faithful enough. In [check-rc-contract.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-rc-contract.py:295) and [check-surface-recall.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-surface-recall.py:168), the env dict is built immediately before the `subprocess.run` call. The stand-in changes the child result, but not the env construction being measured. It returns rc 0, empty stderr, valid JSON, so it deliberately holds the success branch open.

2. Restoration: yes. Both helpers patch `subprocess.run`, enter the production call inside `try`, and restore in `finally` at [check-rc-contract.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-rc-contract.py:820) and [check-surface-recall.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-surface-recall.py:604). Exceptions inside `observe`, `_render_once`, JSON parsing, or the capture function still restore the global.

3. Distinct inputs: distinct enough for the local fixture-variation rule, but the env is not expected to semantically depend on rc/payload. A constant implementation of the production scrub without `PYTHONDONTWRITEBYTECODE` fails both captures; a constant test double inside the case would be a test mutation, not the deliverable.

4. Old kills preserved: yes. All four temp-copy entries were killed; the named r4 env case appeared in every `[FAIL]` list. `check-surface-recall` #20 remains confounded by the sibling agreement case, while #21 is the clean single-failure carrier for the call-site inline mutant.

5. Shared `scrub_env()`: extraction is still attractive, but I do not think it is owed by this fold. The duplicated helper is now 26 physical lines in each file, with only the signature and production call differing. That is not free, but the coordinator’s “31-line filesystem probe denominator collapsed” argument holds after this fold. Extraction would be a design cleanup, not a convergence blocker.

6. Pre-existing in-process `.pyc`: reproduced, but not a mutation-sweep poison route. With `PYTHONDONTWRITEBYTECODE` unset, `check-surface-recall.py --self-test` writes two sibling-import caches. With the variable set, it writes none. The mutation harness both excludes incoming `__pycache__` from staged trees and runs suites under `child_env`, so I do not see a reachable control/after-control poisoning path in the sweep.

**Tried To Refute And Could Not**

I could not refute the coordinator’s corrected claim that env capture closes the `-B` shim and `PYTHONPYCACHEPREFIX` class: the new case opens no child interpreter and observes the owned dict directly. I also could not refute the four named mutation carriers, shard 5/8, shard 8/8, or the assertion that #20 is still the confounded surface-recall carrier while #21 is clean.

| Severity | Deliverable or Instrument | Caused by Fold Itself? |
|---|---|---|
| None | r4 env-capture instrument | No |
| Low, pre-existing note only | in-process `exec_module` writes `.pyc` when env unset | No |

Final verdict: **NOT CONVERGED**. This fold is clean by my review, but it is the first clean pass after the r4 Claude finding and non-trivial fold, not the second consecutive clean round required by the method.
