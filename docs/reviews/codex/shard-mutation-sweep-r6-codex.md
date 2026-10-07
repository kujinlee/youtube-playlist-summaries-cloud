<!-- codex-review: model=gpt-5.5 -->

**Findings**

**Low · Deliverable · caused by this fold’s v4 parser exposure:** the accept set is not exactly canonical ASCII decimals. `parse_shard` uses `SHARD_SPEC.match(spec.strip())` at [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:1572), so leading/trailing whitespace is accepted before the canonical regex sees the value.

Concrete exhibits:

```text
parse_shard(" 1/8")   -> (1, 8)
parse_shard("1/8\n")  -> (1, 8)
parse_shard("1/8 ")   -> (1, 8)
parse_shard("0/8\n", zero_based=True, flag="--shard0") -> (1, 8)
```

This directly refutes the requested `^(0|[1-9][0-9]*)/(0|[1-9][0-9]*)$` accept set. It also means the new workflow call `--shard0 "$SHARD_INDEX/$SHARD_TOTAL"` will accept values like `SHARD_INDEX=' 0'` or `SHARD_TOTAL='8 '` if they ever reach the env. The Unicode and leading-zero holes are closed, but the canonical-boundary hole remains.

Fix, **UNVERIFIED**: remove `.strip()` and use `SHARD_SPEC.fullmatch(spec)`, or at minimum `SHARD_SPEC.fullmatch(spec)` with no pre-normalization. Keep the refusal message printing the original `spec!r`.

**Verification**

Commands run, with real results:

```text
git status --short
-> M docs/explainers/questions.md
-> ?? docs/reviews/claude/shard-mutation-sweep-r6-claude.md
```

No tracked files modified by me.

```text
python3 scripts/check-plan-code.py --self-test
-> 168/168 passed
```

Direct parser probe:

```text
SHARD_SPEC ^(0|[1-9][0-9]*)/(0|[1-9][0-9]*)$
'+1/8' => None
' 1/8' => (1, 8)
'1/8\n' => (1, 8)
'1/8 ' => (1, 8)
'１/８' => None
'٠/8' => None
'²/8' => None
'1_0/8' => None
'0x8/8' => None
'' => None
'00/8' => None
'08/8' => None
'01/8' => None
'1/08' => None
'1/٨' => None
```

Zero-based boundary probe:

```text
'0/8' => (1, 8)
'7/8' => (8, 8)
'8/8' => CANNOT RUN — --shard0 8/8 names a shard that does not exist...
' 0/8' => (1, 8)
'0/8\n' => (1, 8)
'0/8 ' => (1, 8)
```

Both-flags refusal:

```text
python3 scripts/check-plan-code.py --mutate . --shard 1/8 --shard0 0/8
-> rc=2
-> CANNOT RUN — --shard and --shard0 are the same control with different bases; pass one...
```

No control/mutation lines printed, so it refused before work.

Shard equivalence, direct:

```text
N=3: every --shard0 i/3 matched --shard (i+1)/3 and selected same slice
N=8: every --shard0 i/8 matched --shard (i+1)/8 and selected same slice
```

Mutation shards:

```text
python3 scripts/check-plan-code.py --mutate . --shard 1/8
-> OK — 151 mutation(s), 151 killed, 151 attributed, 0 survivor(s)

python3 scripts/check-plan-code.py --mutate . --shard 2/8
-> OK — 151 mutation(s), 151 killed, 151 attributed, 0 survivor(s)

python3 scripts/check-plan-code.py --mutate . --shard 8/8
-> OK — 150 mutation(s), 150 killed, 150 attributed, 0 survivor(s)
```

Pin falsifier on a `git archive HEAD` temp copy:

```text
control rc=0
delete setup-python from mutation-sweep only
mutant rc=1
FAILED — 1 job(s) pin no Python version:
    ci.yml:mutation-sweep
```

Broad gates:

```text
check-docs                 rc=0, Documentation integrity OK
check-selftest-counts      rc=0, 50 script(s) verified
check-python-pin           rc=0, advisory only for local Python 3.14 vs CI 3.12
check-features             rc=0, 26 nodes
check-anchors              rc=0, 13 registered, all claimed
check-vocabulary-collisions rc=0, no unjustified duplicate mechanism
check-ratchet-contract     rc=0, ratchet contract OK
check-backlog-closure      rc=0, warnings only
```

NOT MEASURED: unsharded `--mutate .`, live CI, shard 3/8 rerun.

**Answers To The Six Questions**

1. **No.** Unicode digits, plus signs, underscores, hex, empty, and leading zeros refuse. But whitespace-wrapped specs are accepted: ` 1/8`, `1/8\n`, `1/8 `, `1/8\r`, `1/8\t`.

2. **Mostly yes.** `--shard0 0/8 -> (1,8)`, `7/8 -> (8,8)`, `8/8` refuses. The refusal message correctly reports `--shard0 8/8`, not converted `9/8`.

3. **No disagreement found.** For all valid zero-based `i/N` at `N=3` and `N=8`, `--shard0 i/N` matched `--shard (i+1)/N` and selected the same `shard_slice`.

4. **Yes.** `--shard 1/8 --shard0 0/8` refuses before work and returns `2`.

5. **Yes.** `.github/workflows/ci.yml` now interpolates only `SHARD_INDEX/SHARD_TOTAL` into `--shard0`; no arithmetic, validation, or embedded interpreter remains in the workflow. `check-python-pin.py` still sees `mutation-sweep`; deleting that job’s `setup-python` on a temp archive made it red and named `ci.yml:mutation-sweep`.

6. **Confirmed.** The two retargeted entries load once in the flattened manifest: malformed `--shard` at position 473, shard 1/8, and nonexistent shard at position 474, shard 2/8. Shards 1/8 and 2/8 both passed with full attribution, and the visible mutation names matched the original subjects.

**Tried To Refute And Could Not**

I could not refute the Unicode fix, leading-zero fix, `--shard0` 0-to-1 conversion, both-flags early refusal, workflow logic removal, `check-python-pin` coverage of `mutation-sweep`, or the retargeted mutation attribution. The fold is tighter in the Unicode/overflow dimensions, but not exact in the canonical-string dimension.

| Severity | Deliverable or instrument | Caused by this fold? |
|---|---|---|
| Low | Deliverable: `parse_shard` / `--shard0` accepts whitespace-wrapped shard specs | Yes for v4’s exposed parser/canonical claim; underlying `.strip()` predates this fold |

**Verdict**

**NOT CONVERGED.** This is not a clean round, so it is neither quiet round 1 nor quiet round 2.
