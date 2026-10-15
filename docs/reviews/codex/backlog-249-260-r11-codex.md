<!-- codex-review: model=gpt-6.1-sol -->

## Blocking

None established.

## High

**H1 — The diagnostic can still discard the crash’s cause, refuting claim 5.** At `scripts/check-plan-code.py:2784`, reproduced through real subprocesses and `run_mutations`:

```python
raise RuntimeError(
    "ROOT_CAUSE_MARKER\n" + "uninformative continuation\n" * 40
)
```

With empty stdout, the 400-character tail contains neither `RuntimeError` nor `ROOT_CAUSE_MARKER`. After 26,456 bytes of stdout, the 200-character stderr allocation loses both again.

The same injection into the actual withdrawal suite’s `signature_of` produces `rc=1`, empty stdout, and the same loss. Thus row #270’s promise that “the next occurrence will name it” is unsupported. Preserve the exception heading alongside bounded context; add a regression case for multi-line exceptions.

## Medium

**M1 — The shard-reassignment explanation is false, refuting claim 2.** Between `b190b713` and `f599182d`, two entries were **appended to `check-withdrawal.json`**. All 30 existing withdrawal entries retain their absolute positions and shards:

| Entry | Position at both commits, zero-based | Shard |
|---|---:|---:|
| `hit_offset` | 1091 | 4 |
| `\|` boundary | 1099 | 4 |
| HARD-break boundary | 1102 | 7 |

The populations differ, 1,529 versus 1,531, but these mutations were not reassigned. Correct row #270’s explanation. The same-commit rerun remains stronger evidence.

**M2 — Canonical printer output can be misparsed, refuting claim 4’s universal readability assertion.** Making the real suite’s `signature_of` return `"sentinel: got payload"` produces:

```text
[FAIL] figure with two words either side: got 'sentinel: got payload' want 'sweep holds 1,414 anchors today'
```

`parse_fail_names` returns:

```text
figure with two words either side: got 'sentinel
```

This is a pre-existing parser limitation, not a regression introduced here. The measured 5/2 failures remain correctly readable, but they do not establish universal printer/parser compatibility.

## Low

**L1 — The stdout figures use the wrong unit.** Reproduced:

| Mutation | Characters | UTF-8 bytes | `[FAIL]` lines |
|---|---:|---:|---:|
| `hit_offset` | 26,455 | 26,791 | 5 |
| `\|` boundary | 26,474 | 26,810 | 2 |

Claim 8’s “26,455 B / 26,474 B” figures are character counts.

**L2 — Withdrawn evidence remains in new comments.** `scripts/check-plan-code.py:2681` and `:3440` still assert 18 failures. The comment at `:2762` also retains the categorical printer accusation that the new message withdraws.

## Checked and found SOUND

- **Claim 1:** Existing CI history contains 39 runs, no duplicate commit runs, and only `38351420487` has a rerun. Attempts 1/2 use the same commit and identical 191-entry progress sequences for both disputed shards. Attribution changes from **189→191 on shard 4** and **190→191 on shard 7**.
- **Claim 3:** Five `main()` call sites and three git-driving helpers precede the suite’s first print. An injected construction exception gives `rc=1`, empty stdout, and no parsed failures.
- **Claim 6:** No different budget requirement between mutation and control diagnostics was established. H1 affects the shared helper; duplicating slicing at this call site would not solve it.
- **Claim 7:** Old/new verdicts and mutation evidence match across 25 representative exit-code/stream combinations, including `rc=2`. The wrapper and replacement use the same producer and `merged_output`; control evidence handling is unchanged.
- **Claim 8, reproducible portions:** 239/239 harness cases; 179/179 withdrawal cases; 1,540 anchors across 1,532 entries; declared population 1,531→1,532; scoped withdrawal sweep **32 killed / 32 attributed**, measured here in **50.08 seconds**.
- New-entry replay: **1 killed / 1 attributed**, with green controls.

## CANNOT RUN

- **Full local mutation sweep:** deliberately not executed under the stated laptop timeout constraint. **Treat this as NOT RUN**, not a pass. Scoped results do not establish full-HEAD coverage.
- **Exact historical 1,259-byte stderr and 58-second replay:** the original injection text, temporary path, and timing conditions were not supplied. My construction probe produced 857 stderr bytes; the scoped sweep took 50.08 seconds. **Treat those exact historical figures as NOT RUN**, not independently verified.

## Instruments

Prepared Python 3.12 venv, with its `bin` first on `PATH`; commit bodies and scoped diffs; historical manifest enumeration; GitHub attempt metadata and logs; real staged subprocesses; adversarial crash/printer probes; old/new behavior comparison; self-tests, binding check, and scoped mutations.

Repository unchanged. No review file written.
