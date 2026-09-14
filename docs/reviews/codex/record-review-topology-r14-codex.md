<!-- codex-review: model=gpt-5.5 -->

**Blocking**

None.

**High**

None.

**Medium**

None.

**Low**

None.

I verified by execution that `case_line` is the single self-test `[PASS]`/`[FAIL]` line shape in `scripts/codex-review.py`: the only two case printers now call it at `scripts/codex-review.py:962` and `scripts/codex-review.py:982`, and direct execution produced byte-identical strings for the previous classifier-with-reason and `chk`-without-reason shapes.

I verified the six new cases are falsifiable. The two shipped new mutations both kill and attribute:

```text
two new entries ok=True killed=2/2 attributed=2/2 survivors=[]
reason dropped -> fails ['the line keeps the canonical shape the harness documents']
stub parser -> fails ["the FAIL line this suite prints parses back to the case name, via the harness's OWN parser", ...]
```

I also verified the coordinator’s load-bearing claim: the full `got=` printer regression is caught but unattributable by construction:

```text
manual full revert got= ok=False killed=1/1 attributed=0/1
expect ... matched 0 red case(s) — caught by something else:
["the FAIL line ...: got=['a plain case: got=1']", ...]
```

The imported parser path looks safe under the tested conditions. `codex-review.py --self-test` passed with redirected `HOME`, ran in `real 0.85`, and the full staged mutation harness passed. When `check-plan-code.py` itself was the mutation target, its own 76-entry subset passed:

```text
control rc: 0 tail: 128/128 passed
ok: True
killed: 76 / 76
attributed: 76 / 76
survivors: []
```

Counts are consistent independently: `17` classifier fixtures + `68` `chk` calls = `85`; `EXPECTED_MUTATIONS` sums to `620`; manifests sum to `620`; `codex-review.json` has `11`; `check-review-recorded.json` has `35`.

Requested regressions were unchanged by AST comparison against `HEAD`: `reviewed_state`, `unredirected`, `verdict_record`, `classify`, `tail_candidates`, `classify_verdict`, and `second_question`.

Requested commands, all from the isolated copy with `.git` absent:

```text
codex-review.py --self-test: 85/85 passed
check-review-recorded.py --self-test: 117/117 passed
check-plan-code.py --self-test: 128/128 passed
check-ratchet-contract.py --self-test: 41/41 passed
check-fixture-variation.py: fixture variation OK
check-selftest-counts.py: 38 script(s) declare a count, every one verified
check-review-rounds.py: 233 parsed, 0 silent gaps
check-plan-code.py --mutate .: 44 file(s), 620 mutation(s), 620 killed, 620 attributed, 0 survivor(s)
```

CONVERGED
