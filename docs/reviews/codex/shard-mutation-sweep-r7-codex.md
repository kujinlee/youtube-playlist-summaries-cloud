<!-- codex-review: model=gpt-5.5 -->

**Findings**

L1 · [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:4617) · `SHARD_FLAGS` is not actually safe for “one dict entry” future flags with hyphens.

Exhibiting input, in a temp copy only: add `"shard-x"` to `SHARD_FLAGS`, then run:

```text
python3 /tmp/.../scripts/check-plan-code.py --self-test --shard-x 2/5
rc=1
AttributeError: 'Namespace' object has no attribute 'shard-x'. Did you mean: 'shard_x'?
```

So the two consumers can disagree through argparse dest normalization. The current shipped keys `shard` and `shard0` are fine; this is a defect in the new enumeration abstraction and in the comment claiming a third flag is just one dict entry.

Fix, UNVERIFIED: make `SHARD_FLAGS` store option name and argparse `dest` separately, or pass `dest=_dest.replace("-", "_")` while looking up that same normalized dest. Add a temp or real self-test for a hyphenated shard flag if hyphenated flags are intended to be supported.

**Verification**

Repo state stayed as requested:

```text
git status --short
 M docs/explainers/questions.md
?? docs/reviews/claude/shard-mutation-sweep-r7-claude.md
```

Core commands run:

```text
python3 scripts/check-plan-code.py --self-test
173/173 passed

python3 scripts/check-plan-code.py --mutate . --shard0 3/8
OK — delivered scripts mutated: 53 file(s), 151 mutation(s), 151 killed, 151 attributed ..., 0 survivor(s) — measured over shard 4 of 8
```

Mode-refusal spot checks:

```text
--self-test --shard ''          rc=2 CANNOT RUN
--self-test --shard0 ''         rc=2 CANNOT RUN
--self-test --shard0 garbage    rc=2 CANNOT RUN
--self-test --shard 0/8         rc=2 CANNOT RUN
```

Scratch-root parser checks with `--mutate`:

```text
--shard '' / ' ' / garbage / 0/8 / 99/8       rc=2
--shard0 '' / ' ' / garbage / 99/8            rc=2
--shard 1/8 and --shard0 0/8 reached manifest loading, then failed only because scratch root had no manifests
```

Standard gates:

```text
check-docs                         rc=0 Documentation integrity OK
check-selftest-counts              rc=0 50 script(s) declare a count...
check-features                     rc=0 26 nodes...
check-backlog-closure              rc=0 WARN only: #117, #159
check-python-pin                   rc=0 advisory only: local Python 3.14 vs CI 3.12
check-anchors                      rc=0
check-vocabulary-collisions        rc=0
check-ratchet-contract             rc=0
```

Counts independently re-derived:

```text
case invocations: 173
manifest entries: 1207
check-plan-code manifest entries: 102
edit anchors: 1215
duplicate anchor tuples: 0
unresolved/ambiguous anchors: 0
```

NOT MEASURED: I did not run unsharded `--mutate .`, per constraint. I did not re-run all already-measured shards; I ran one missing valid CI-facing shard, `--shard0 3/8`.

**Answers To The Six Questions**

1. H1 is closed for current flags and both dimensions: `--shard` and `--shard0`, including `""`, refuse before self-test when no `--mutate` is present. Valid sharded mutate still works: `--mutate . --shard0 3/8` passed with 151/151 killed.

2. The `SHARD_FLAGS` enumeration can still disagree for future hyphenated keys. Argparse maps `--shard-x` to `shard_x`, but `main` does `getattr(a, "shard-x")`, producing a traceback.

3. `is not None` is right for the current mode predicate. `shard_mode_refusal(None, None)` stays silent; `""`, whitespace, garbage, and valid-looking values refuse without `--mutate`.

4. The reshaped L1 case does not appear to mask the relevant defect: a raise becomes `"RAISED ValueError"`, which does not equal the expected `None` for invalid long inputs or the expected tuple for valid inputs. The 4-digit ceiling is arbitrary but explicit; `9999/9999` accepts and `10000/10000` refuses. It could bite only if someone wants more than 9999 shards.

5. I could not refute #232’s core claims. Confirmed `peer-sites.py:abc` rc=2 while `peer-sites.py:²` rc=1 traceback; `count_drift` uses bare `\d` and raises on 4301 digits; `check-gate-falsifiability --current-release=²` and `check-plan-progress.decide(... paused_unticked: ² ...)` also raise.

6. Counts/anchors agree: self-test 173, manifest 102 for `check-plan-code`, declared sum 1207, anchors 1215, with zero unresolved and zero duplicate tuples.

**Could Not Refute**

I tried to refute the previously measured H1 regressions; they now refuse with rc=2. I tried to break current legitimate shard use; a real `--shard0 3/8` mutation shard passed. I tried to refute #232’s representative examples; the examples reproduced.

| Severity | Deliverable Or Instrument | Caused By This Fold? |
|---|---|---|
| Low | Instrument: shard flag enumeration hardening in `check-plan-code.py` | Yes |

**Verdict**

NOT CONVERGED. This is not a clean round, so it is neither first nor second consecutive clean round; the quiet counter remains 0.
