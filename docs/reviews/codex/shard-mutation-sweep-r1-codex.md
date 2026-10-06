<!-- codex-review: model=gpt-5.5 -->

**Verification**

Ran from `/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud` at `eee31527`, with only `docs/explainers/questions.md` dirty and ignored.

```text
$ python3 scripts/check-plan-code.py --self-test

155/155 passed
```

```text
$ python3 scripts/check-plan-code.py --mutate . --shard 2/8
...
OK — delivered scripts mutated: 50 file(s), 149 mutation(s), 149 killed, 149 attributed to the case each names, 0 survivor(s) — measured over shard 2 of 8 (round-robin)
```

Additional probes:

```text
$ python3 scripts/check-plan-code.py --mutate . --shard 1194/1194
CANNOT RUN — shard 1194 of 1194 is EMPTY: the manifest holds 1193 mutation(s), so there is nothing for this shard to measure. A shard that passes over an empty subset reports success for work it never did. Lower N. NOTHING WAS MEASURED. Treat this as NOT CHECKED.
rc=2

$ python3 scripts/check-plan-code.py --mutate . --shard 0/8
CANNOT RUN — --shard 0/8 names a shard that does not exist: I must be at least 1 and at most N. NOTHING WAS MEASURED. Treat this as NOT CHECKED.
rc=2

$ python3 scripts/check-plan-code.py --mutate . --shard two/eight
CANNOT RUN — --shard 'two/eight' is not of the form I/N (two integers, e.g. `--shard 2/5`). NOTHING WAS MEASURED. Treat this as NOT CHECKED.
rc=2
```

I did not run unsharded `--mutate .`, per instruction. `actionlint` is not installed locally; PyYAML is also unavailable. Ruby stdlib YAML did parse `.github/workflows/ci.yml` and saw jobs `mutation-sweep`, `mutation-sweep-complete`, `verify`, matrix `shard: [1..8]`, and `mutation-sweep-complete` needing `mutation-sweep` with `always()`.

**Findings**

Medium: `--shard` is silently accepted with `--self-test`, a mode where it means nothing.

The early self-test return in [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:4333) happens before the new shard validation at [scripts/check-plan-code.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:4375). That leaves a meaningless shard flag accepted as success:

```text
$ python3 scripts/check-plan-code.py --self-test --shard 2/8
155/155 passed
rc=0

$ python3 scripts/check-plan-code.py --self-test --shard 9/9
155/155 passed
rc=0
```

This is not the catastrophic “mutation dropped while green” failure, because self-test does not claim mutation-sweep coverage. But it directly violates the stated contract that `--shard` only means something with `--mutate`, and it leaves one accepted path where a caller can believe a shard-shaped subject was checked.

Proposed fix, UNVERIFIED: move the `if a.shard and not a.mutate` refusal before `if a.self_test`, or refine it to allow only the exact intended modes and add a self-test case for `main(["--self-test", "--shard", "2/8"]) == 2`.

**Design Questions**

1. Round-robin is the right partition for this manifest shape. Since `load_manifests()` sorts manifest files and preserves each file’s contiguous entries, contiguous slicing would concentrate an expensive file block; round-robin spreads that block. It is stable for a fixed manifest ordering and commit. If a manifest file is added or removed, all shards in a normal CI run still check out the same commit, so they partition the same list. A rerun against a different commit would be a different workflow run, not two shards in one run disagreeing.

2. `strategy.job-total` / `job-index` is a reasonable single source of truth here. GitHub documents `strategy.job-index` as zero-based and `strategy.job-total` as the total matrix job count, so the shell `SHARD_INDEX + 1` is the right conversion to the script’s 1-based `I/N` format. GitHub also documents that matrix variable order determines job creation order, and this matrix has one axis, so the indices cover exactly `1..N` for the list length. An absent `SHARD_TOTAL` would produce `1/`, which `parse_shard` refuses rather than becoming unsharded. Sources: [GitHub strategy context](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts), [GitHub workflow syntax for matrix jobs](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).

3. The control floor is accounted for honestly in the workflow comment and in the observed shard. Shard 2/8 controlled 50 files, ran 149 mutations, then re-controlled the same 50 files. The stated worst-case arithmetic `214 + 4890/N` gives `825.25s` at `N=8`, i.e. about 13.8 minutes, which is correctly under the 30-minute ceiling with real headroom.

4. The aggregator shape is sufficient for failed/skipped/cancelled shards as written. GitHub documents `needs.<job_id>.result` as a job result with values including `success`, `failure`, `cancelled`, and `skipped`, and documents that jobs needing a failed/skipped job are skipped unless a conditional such as `always()` makes them continue. Since the aggregator exits nonzero unless the aggregate result is exactly `success`, it should fail for red, cancelled, or skipped sweep shards rather than pass them. Source: [GitHub needs context](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts), [GitHub jobs/needs behavior](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-jobs).

**Tried To Refute And Could Not**

I could not construct a dropped-or-duplicated mutation from the implemented `muts[index - 1::total]` slicing; the required real shard reported the expected `149` mutations for shard 2/8 and ended with `149 killed, 149 attributed, 0 survivor(s)`.

I could not make a sharded mutation run report `OK` without controls for files it mutated. The code derives `targets` from `shard_muts`, and the measured shard ran both control and re-control over 50 touched files.

I could not make malformed, out-of-range, or empty `--mutate --shard` pass. Those probes all refused with rc=2.

I could not find evidence that the global manifest checks became per-shard: load, duplicate-name/anchor refusal, expected-count drift, target home-escape scan, and replacement-text home-escape scan all run over whole `muts` before `shard_muts` is formed.

Final verdict: **NOT CONVERGED**.
