<!-- codex-review: model=gpt-6.1-sol -->

## Blocking

None established. No finding below changes a mutation verdict.

## High

**H1 — Wording #4 is refuted: the line need not have begun `Exception ignored in`. Delete the annotation.**

At `scripts/check-plan-code.py:629`, the backward scan stores `lines[k].strip()`. The annotation at `:3031` claims a prefix of the original child-written line, but the boolean tests its normalized version.

Reproduced through a real child and production `run_mutations`:

```python
raise RuntimeError(
    'real\n'
    '\tException ignored in FORGED\n'
    'Traceback (most recent call last):\n'
    '  File "fake", line 1\n'
    'AFTER'
)
```

The rendered report contains:

```text
RuntimeError: real · AFTER [a line ABOVE that run began
'Exception ignored in', which the CHILD wrote]
```

Its diagnostic window also contains the actual tab-prefixed line. That line **began with a tab**. No child-written line in this witness began with the claimed prefix.

The index relation survives: `intro` is above the consumed run. The commit’s construction argument proves that relation, but does not prove the entire annotation.

**The annotation should no longer exist.** Follow `9dd9c985`’s stopping rule: remove it and its otherwise-unused flag/backward scan, with corresponding subject-bound test and manifest changes. Its historical sever was green; its current sole falsifier requires the sentence’s presence without validating its truth. I propose no wording #5.

## Medium

**M1 — “A run of FRAME-SHAPED lines” still overstates what the code establishes.**

`scripts/check-plan-code.py:639` requires **any one** line in the consumed run to match `^[ \t]+File "`. The run also consumes arbitrary indented text and blanks.

A real child writing this stderr and exiting 1:

```text
Exception ignored in FORGED
  File "
    THIS IS NOT A FRAME

AFTER
```

produces a rendered report describing `AFTER` as following:

```text
a run of FRAME-SHAPED lines
```

The purported run contains arbitrary prose and a blank, and its sole matching line is the incomplete prefix `  File "`.

An ordinary real `raise RuntimeError("ACTUAL")` likewise produces a run containing both a frame line and its source-code line; the report applies the same phrase to both.

**Stop claiming the consumed run consists of frame-shaped lines.** The fold removed an authenticity claim but replaced it with an unsupported claim about every member of the run. No additional frame validator is warranted.

## Low

**L1 — The published 4.89–6.06s timing spread was not independently reproduced.**

Per the requested contract, this is a reproducibility finding, **not evidence that the historical observations were false**.

With green controls and each revision’s complete mutation-manifest set, two runs per revision measured:

| Revision | First | Second | Control |
|---|---:|---:|---|
| `74a44551` | 4.46s | 4.40s | 178/178 |
| `c5660227` | 5.42s | 5.57s | 298/298 |
| `9232cbd9` | 5.75s | 5.66s | 298/298 |

These runs do not reproduce either the exact historical spread or its claimed relationship to between-commit differences. Preserve the figure as a dated observation under the original conditions; it does not establish that the effect is currently unmeasurable on this hardware. These two-sample measurements also do not establish the original 4s→6s regression.

## Checked and found SOUND

- **Reviewed committed HEAD `9dd9c985`**, both round-14 reviews, all three specified commit messages, and `c5660227..9dd9c985`.
- **Index attacks:** no reversed relation, empty `intro` with a true flag, or reused `intro` index was established. The original grid reproduced **59,049 streams, 3,720 annotations, zero adjacent labels**, with distances **2: 1,944; 3: 1,296; 4: 480**. Indexed transcription matched production extraction on every stream.
- An expanded **117,649-stream** grid, including indented ignored-prefix lines and repeated headers, emitted **11,250 annotations** with **zero invalid index relations, zero empty introductions, and zero reused introduction indices**. These checks support the positional subclaim; they do not rescue H1.
- **Canonical indices reproduced:** label/`intro` at **0**, bare header at **1**, run start at **2**. Its rendered production report was inspected.
- **Counts:** HEAD **298/298**; this file **147 entries**; manifest total and `EXPECTED_MUTATIONS` sum both **1549**; zero per-file mismatches in either direction; declared-sum case pins **1549**.
- **Binding:** **1557 anchors / 1549 entries**, all resolving exactly once; **0 unbound**.
- **Nothing retired to fund the rise:** manifest comparison shows the existing separator entry retargeted in place plus one added annotation entry. Case comparison shows one renamed/replaced expectation, with no case retirement.
- **Current annotation sever:** green control **298/298** → **297/298**, exactly `...and the harness's OWN note is there, in text raw stderr cannot supply` red → restored **298/298**.
- **Original annotation sever at `c5660227`:** separate `HARNESS_TREE` copy, **298/298 control → 298/298 severed → 298/298 restored**.
- **Both scoped mutations reproduced:** `736/1549` and `721/1549` each yielded **1 killed, 1 attributed, 0 survivors**. Positions were independently mapped to their manifest entries.
- **Both named expectations can observe their mutations.** They consume `_repq` from real `run_mutations`. Separately severing the join separator produced **297/298**, with exactly its named report-joining case red.
- **Historical closure counts reproduced at the requested revisions:** `ab53945a^` **291/291**, `ab53945a` **298/298**. Rows #279/#280’s correction is sound.
- **#270’s withdrawal is supported:** `ci.yml:674–675` explicitly says even per-shard mutation counts prove nothing about balance. Equal counts do not establish equal cost.
- **Shard 8 independently confirmed green twice:** [CI at `c5660227`](https://github.com/kujinlee/youtube-playlist-summaries-cloud/actions/runs/38492264883), [CI at `9232cbd9`](https://github.com/kujinlee/youtube-playlist-summaries-cloud/actions/runs/38496138078). The latter has all eight mutation shards and the completion job green. These successes do not diagnose the prior cancellation; **UNDIAGNOSED remains honest**.

## CANNOT RUN

**Treat these as NOT RUN—failures of verification scope, never passes.**

- Full local `--mutate .`: excluded by the supplied timeout constraint. Two scoped mutations do not establish population-wide correctness.
- Original 4s→6s regression magnitude and exact historical timing spread: not reproduced under their original conditions.
- Fresh CI replay: not run. Existing GitHub job metadata was inspected.
- An initial master timing instrument mixed historical code with later manifests and returned **177/178**. That attempt was a **red-control CANNOT RUN** and was discarded. After supplying all historical manifests, both master controls passed **178/178**.

## Instruments

Prepared `.venv/bin/python` **3.12.9**, venv-first mutation `PATH`; real child processes and rendered production reports; indexed exhaustive probes; structural manifest and AST comparisons; separate staged `HARNESS_TREE` copies; controlled severs and restorations; historical revision controls; GitHub job metadata.

Worktree remained clean. **No review file written.**
