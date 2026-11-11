Reviewed head: 5fd14032ad6b7205d3dcfae88ea9994fa9f3e674

# Round 1 — 586-slice1 — claude

Subject: PR #557, branch `586-slice-1-strace`, head `5fd14032`, base `origin/master` `25324b48`. Mandate: refute.
All experiments ran in the scratchpad, outside the repository; nothing in the tree was changed except this file.

## What I ran, and what held

| check | result |
|---|---|
| Every figure in the measurement doc vs the committed JSON (syscall union and per-name counts, ioctl table, 48 spawners, 28 unresolved, largest non-spawner ratio 7.23, the ten-ratio table, shard times) | **all equal**, recomputed by script |
| Task 1.0 Step 2 counts (90 targets, 47 untraced, traced readers = `check-canonical-source`/`check-dashboard-entry`/`check-features`, 33 untraced with non-empty `today`, `today_full` null) | **hold** |
| Task 1.0 Step 1b `today` re-derived from `git archive d206e066` with THAT tree's `sweep_sources`/`module_sources`/`select_manifests`, one path at a time | **identical** to the fixture (64 targets, same paths) |
| `check-fixture-git-isolation.py --self-test` / main | 141/141; main OK |
| `check-ratchet-contract.py --self-test` / main | 56/56; `ratchet contract OK` |
| `check-merge-ready.py --self-test` | 400/400 |
| Downloaded the NEWER run `42901768433` (head `5fd14032`, the fixed tree) and merged it with `--merge` | see F1, F2; syscall union and ioctl tokens IDENTICAL to the committed run, so the two red suites of the committed run did not shrink the union |
| `actionlint` | **NOT RUN** — not installed |

Item 7 (loosening): none found. The `check-merge-ready.py` diff adds one `ACCOUNTED_MENTIONS` row
`("strace-measure.yml", "pull_request:") -> (1, "the workflow TRIGGER ...")`, the same shape as the existing
`schema-gates.yml` row; the workflow has no PR-only step and is not required. The `"--self" + "-test"` split is the
population exception `check-fixture-git-isolation.py` documents itself (R3, line 95), and `NO-MUTATIONS:` is
`check-ratchet-contract.py`'s documented escape; neither guard's code changed.

## Findings

### F1 — Medium — `TRACE_FACTOR` is a single noisy sample; the second run of the same workflow gives 12, not 20
`docs/reviews/measurements/2026-11-10-strace-on-runner.md:29`, `scripts/strace-measure.py` `merge` (`worst = max(...)`).
**Evidence:** run `42893595762` (committed): `scripts/batch-ci.py` seed 1109, plain 3.26 s, traced 64.99 s, ratio
19.94 → 20. The SAME target, seed 0, in the SAME run: plain 6.34 s, traced 65.94 s, ratio 10.4 — the plain time
halves between seeds while the traced time does not move. Run `42901768433` (head `5fd14032`, merged by me with the
committed `--merge`): `trace_factor` **12**, from `batch-ci.py` seed 0, 5.04 s / 59.21 s = 11.75. A constant the later
slices pin moves 20 → 12 between two runs of one tree and one image. 20 is the safer direction for a timeout, but the
doc presents it as THE measured value, and a re-run would silently lower it.
**Fix:** state `TRACE_FACTOR` as the max over BOTH runs (20, cite both run ids) and say it is a one-sample max of a
noisy ratio; or define it over a plain-time floor / per-target median. Either way the doc must show it is not
reproducible as a point value.

### F2 — Medium — strace's `???` syscall shape is left unparsed; "the driver left no line unparsed" is true of one run only
`scripts/strace-measure.py:56` (`LINE`: the name must match `[A-Za-z_][A-Za-z_0-9]*`); doc line 17.
**Evidence:** run `42901768433`, `unparsed_line_samples`:
`scripts/compaction-state.py: ['7044  ???( <unfinished ...>', '7044  <... ??? resumed>)                = ?']` — strace
prints `???` when it cannot read the syscall number (a thread exiting mid-call). Neither line is counted, and the
shape is absent from `scripts/fixtures/strace-lines/`, so slice 2's parser will be cased against a corpus that lacks
a shape the runner produces.
**Fix:** accept `\?\?\?` as a name in `LINE` (and in its `resumed` branch), add the two lines above to the fixtures,
and qualify the doc's "no line unparsed" with its run id plus this counter-example.

### F3 — Medium — `samples.json` holds none of the signal / exit / spawn shapes the doc and plan promise
`scripts/fixtures/strace-lines/samples.json`; doc lines 119-120 ("plus signal, exit and spawn lines"); plan Task 1.1
(b) "plus every `--- SIG`, `+++ exited`/`+++ killed` and `clone`/`clone3`/`vfork` line shape seen".
**Evidence:** the file's shapes are exactly `{= N: 101, resumed: 100, unfinished: 100, -yy label: 48, = -1 E: 36,
AT_FDCWD<: 10, other: 5}` = 400; no entry contains `---` or `+++`. The shard `lines.json` keeps these under a
separate `shapes` key (`measure_shard`), which the fixture build dropped. Only 3 signal/exit lines survive, inside
each whole log; `+++ killed` appears nowhere.
**Fix:** add the shards' `shapes` entries (spawn/signal/exit) to the fixture, or correct the doc's sentence.

### F4 — Medium — a successful `O_CREAT` open counts as "created", so removing a PRE-EXISTING external file it opened is missed
`scripts/strace-measure.py` `removed_and_created` (the `open`/`openat` branch) feeding `is_created`.
**Constructed input** (run through `analyse_log`, copy `/t`):
```
100 openat(AT_FDCWD</t>, "/home/runner/.gitconfig", O_WRONLY|O_CREAT|O_TRUNC|O_CLOEXEC, 0666) = 3</home/runner/.gitconfig>
100 unlink("/home/runner/.gitconfig") = 0
```
→ `external_removals` `[]`, `unresolved` 0. `O_CREAT` without `O_EXCL` succeeds on an existing file, so it is not
proof of creation; the doc's "an unlink/rename/rmdir of a pre-existing path OUTSIDE the copy: **none**" (line 63) is
blind to exactly the truncate-then-delete pattern. Same class: `mkdir` is guarded by `ok`, but a removal itself is
never guarded by `ok` (a failed `unlink` of an outside path is reported), and a FAILED `rename`'s new side is added to
`created` unconditionally (`created.append(resolve(...))` before `if ok:`), suppressing later removals beneath it.
**Fix:** count a creation only for `O_EXCL`, `mkdir*` = 0, `link*`/`symlink*` = 0, and a SUCCESSFUL `rename*`; carry
the rule into slice 2's parser and caveat the doc's "none".

### F5 — Low — a remover line `split_args` cannot balance is dropped silently (not unresolved, not unparsed)
`scripts/strace-measure.py` `analyse_log`: `if args is None or (...): continue`.
**Constructed input:** `100 unlinkat(3</home/runner/a<b>, "f", 0) = 0` → external 0, unresolved 0, unparsed 0.
Whether strace 6.19 escapes `<` inside a `-yy` label I did NOT verify; the point is the fail-open branch: an
unparseable REMOVER must be counted (append to `unresolved`), never vanish.
**Fix:** when `name in REMOVERS and args is None`, record it as unresolved.

### F6 — Low — the ptrace probe fails OPEN if `strace` itself fails
`.github/workflows/strace-measure.yml`, step "ptrace probe": `strace -f -o /tmp/p.log git --version && grep -q execve /tmp/p.log`.
**Evidence:** under GitHub's `bash -e`, a failure of a NON-final command in an `&&` list does not exit:
`bash -e -c 'false && grep -q x /dev/null; echo "probe: $(grep -c execve /nonexistent) line(s)"'` → prints and rc=0.
If ptrace is denied, `strace` exits non-zero, `grep` never runs, the `echo` runs, and the step is GREEN — the step
the comment calls "that failure IS the measurement". (Run 42893595762's probe genuinely passed, so no figure is wrong.)
**Fix:** two lines (`strace -f -o /tmp/p.log git --version` then `grep -q execve /tmp/p.log`), or `|| exit 1`.

### F7 — Low — the doc names the merge commit as the "head", and cites the run measured on the pre-fix tree
Doc line 1: "head `be0f552f`". `be0f552f` is `GITHUB_SHA` of a `pull_request` run — the synthetic merge ref, not
reachable here (`git cat-file -t be0f552f` → not a valid object). `gh run list` gives the run's `headSha`
`7aac29e1`. That head carries the two broken suites (`check-fixture-git-isolation`, `check-merge-ready` red in both
runs); run `42901768433` on `5fd14032` has both green and an identical syscall/ioctl union (my merge, above).
**Fix:** cite head `7aac29e1` (merge `be0f552f`), and cite run `42901768433` as the confirming run on the final head
(it also bears on F1 and F2).

### F8 — Low — `-yy` label escapes are not decoded
`scripts/strace-measure.py` `label_of`: the label text is returned raw, while `unquote` decodes the path argument.
Input `unlinkat(3</home/runner/my\x20dir>, "f", 0) = 0` resolves to `/home/runner/my\x20dir/f`, which can never equal a
decoded created path or the copy root. Harmless on today's `/tmp/strace-measure-*` paths; slice 2 must decode.
**Fix:** pass the label through the same C-escape decoder.

## Verdict

No BLOCKER and no High. Four Medium: two are a constant / claim that a second run of the same workflow already
contradicts (F1, F2), one a fixture that lacks what the doc says it holds (F3), one a hole in the "no external
removal" detector (F4).

VERDICT: NOT CONVERGED
