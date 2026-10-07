<!-- codex-review: model=gpt-5.5 -->

**Findings**

**Low, deliverable, caused by this fold’s L2 guard shape:** the `SHARD_INDEX` guard treats any all-digit string as safe for Bash arithmetic, but Bash arithmetic is fixed-width and not decimal-string-safe. Concrete exhibit:

```text
SHARD_INDEX=18446744073709551616 SHARD_TOTAL=8
case guard: accepts
$((SHARD_INDEX + 1)) -> 1
computed spec: 1/8
```

That starts measuring shard 1, reproducing the L2 “all jobs can alias to shard 1” failure mode for a hostile env value. Also:

```text
SHARD_INDEX=08 -> bash: 08: value too great for base
SHARD_INDEX=3x -> guard refuses, but its message says bash would read it as 0; actually bash errors loudly
```

This is not reachable from GitHub’s legitimate `strategy.job-index` values, and `0`/`7` are accepted correctly. But it refutes the guard’s implicit premise that `[0-9]+` is a safe arithmetic input.

Proposed fix, **UNVERIFIED**: compute `I+1` with a decimal parser that does not overflow, e.g. a tiny Python snippet reading `SHARD_INDEX`/`SHARD_TOTAL`, validating both as canonical non-negative decimal integers, then printing `i+1/n`; or bound-check shell-side before arithmetic and refuse leading-zero / oversized forms with a precise message.

**Verification**

Required commands run:

```text
python3 scripts/check-plan-code.py --self-test
-> 161/161 passed

python3 scripts/check-plan-code.py --mutate . --shard 5/8
-> OK — delivered scripts mutated: 54 file(s), 150 mutation(s), 150 killed,
   150 attributed to the case each names, 0 survivor(s)
   — measured over shard 5 of 8 (round-robin)

python3 scripts/check-plan-code.py --mutate . --shard "" ; echo "rc=$?"
-> CANNOT RUN — --shard '' is not of the form I/N ...
-> rc=2

python3 scripts/check-rc-contract.py --self-test
-> 56/56 self-test cases passed

python3 scripts/check-surface-recall.py --self-test
-> 59/59 self-test cases passed
```

Other checks: manifest is **57 files / 1200 entries / declared sum 1200**; `check-plan-code.py` declares `95`, `check-rc-contract.py` `17`, `check-surface-recall.py` `21`. Working tree after review remains dirty only at `docs/explainers/questions.md`.

NOT MEASURED: unsharded `--mutate .`, per instruction.

**Answers To The Six Questions**

1. **L1:** fixed. `--shard ""` now reaches `parse_shard` and exits `rc=2`. By reading `main`, absent `--shard` remains `None`, bypasses parsing, and still means whole manifest; I did not execute unsharded `--mutate .`.

2. **L2:** legitimate matrix values are fine: `0 -> 1/8`, `7 -> 8/8`. Empty, whitespace, newline, `abc`, `3x` refuse. But very large all-digit values can overflow to a valid shard, and `08` errors in Bash before Python. The message is only partly honest: `abc`/empty read as 0 without the guard, but `3x` does not.

3. **M1:** confirmed. Backlog row 217 is `✅ (was 🟠)` and roadmap line 2227 is `- [x]`. The row’s figures check out: CI slowest shard `248s`, so `1800/248 = 7.3x`; PR #365 head tree has `scripts/check-main-drivable.py: 183` and its manifest has 183 entries; contiguous estimate `~5843s` is about 97 minutes.

4. **M2:** current tree figures are `1200` entries, declared sum `1200`, self-test `161`. The corrected code comments now name the 95 count and the 1198 -> 1200 fold. Dashboard/PR body use append-only corrections; the stale earlier figures remain visible but are explicitly corrected to `1200`, `161`, and measured shard times. I found no still-wrong corrected site.

5. **#230/#231:** #230 accurately records the aggregator hole: `mutation-sweep-complete` reads only `needs.mutation-sweep.result`, not distinct shard IDs or union coverage. #231’s timeout math is supported by CI times and PR #365’s 183-entry tree. The failure direction is loud, not silent.

6. **Ledger hole:** true. `check-review-rounds.py` checks round halves and verdict testimony; `check-review-recorded.py` checks whether a branch recorded a review and whether a Codex verdict saw the final tree; `check-merge-ready.py` checks PR readiness. None parses review-doc findings and requires each to be fixed, declined, or filed.

**Tried To Refute And Could Not**

I could not refute the L1 fix, the #217 ticks, the corrected current counts, the #230 deferral rationale, the #231 timeout-headroom rationale, or the ledger-hole claim. I also could not produce a dropped or duplicated real matrix shard for GitHub’s legitimate `strategy.job-index` values.

| Severity | Deliverable Or Instrument | Caused By This Fold? |
|---|---|---|
| Low | Deliverable CI guard around `mutation-sweep` | Yes, in the new guard’s accepted input class/message |

**Verdict**

**NOT CONVERGED.** This is not a clean round, so it is not quiet round 1 or quiet round 2; the consecutive-clean-round streak does not advance.
