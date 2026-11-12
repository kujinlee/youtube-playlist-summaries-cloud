Reviewed head: d89729a54e8255b2ffd51ea4f033bbfb4c43274d

# 495-survivor-retry — round 3, Claude half (adversarial; the only half this round)

Subject: PR #564, branch `495-survivor-retry`, head `d89729a5`. Focus: the r2 fold (`d738b4f9..d89729a5`) —
X1 (re-run snapshot dereferences symlinks), X2 (`shard_count` + `read_flaky` requires every shard file; the
download step lost `continue-on-error`), X3 (`flaky_names` reads to `FLAKY_TAIL`).

## What was run

| Check | Result |
|---|---|
| `check-plan-code.py --self-test` (worktree) | 443/443, rc 0 |
| `sweep-red-alert.py --self-test` | 32/32, rc 0 |
| `batch-ci.py --self-test` | 169/169, rc 0 |
| `check-merge-ready.py --self-test` | 400/400, rc 0 |
| X1 mutant on a temp copy outside the repo (`symlinks=True` back in `rerun_snapshot`) | RED, 439/443 — the pin holds |
| REAL controls: `stage_tree` into a temp dir, then every one of the 93 manifest targets' `--self-test` run once in it via `run_suite` (the control) | 93/93 rc 0; symlinks in the staged tree: **0 after staging, 0 after all 93 controls** (tree 94 MB) |
| `copytree` (dereferencing, as the fold now does) over: absolute link, relative file link, relative dir link | OK — each becomes a plain copy; the absolute link's bytes are the target's at copy time |
| ... a dangling link; a self-loop link | `shutil.Error` → CANNOT RUN, as the docstring says |
| ... a DIRECTORY link to an ancestor (`sub/up -> d`) | NOT an immediate failure: 33 nested copies of the tree (33 MB from a 1 MB tree) before ELOOP; with a second alias (`rel-dirlink -> sub`) it grew to 431 MB / 191k files in under 2 minutes and I killed it |
| `shard_count(ci.yml)` | 38, equal to the matrix (`strategy.job-index` 0..37 → `shard-0.txt`..`shard-37.txt`) |
| `flaky_names` over all 4,663 REAL manifest names in the harness's real line shape (prefix, `✗`, the real tail incl. `(by 'x: y')`) | 0 wrong; 1,550 of the names contain `: ` |
| `main()` with a fake `gh`, 37 of 38 shard files present, one FLAKY name in `shard-0.txt` | see M1 |
| Doubt mutants on sweep-red-alert (temp copy) | `range(shards-1)` RED; `range(1, shards+1)` RED; `re.search` for the matrix RED; `rpartition`→`partition` green (equivalent unless the tail repeats); `is_file`→`exists` green (equivalent but for a directory named `shard-N.txt`); ci.yml `merge-multiple: false` green; ci.yml shard file named `shard-$SHARD_TOTAL.txt` green (m2) |

Answers to the brief's specific questions:

- **Does dereferencing break any real suite or turn a legit survivor into CANNOT RUN?** No, measured: no real control
  leaves a link in the tree (0 of 93), and `stage_tree` already dereferences, so the snapshot is byte-equivalent to
  the pre-fold one on today's tree. X1 is closed.
- **Cancelled shard / re-run job — does a missing file false-red a green master sweep?** No. A shard writes its file
  unconditionally once its sweep step runs (`grep ... > shard-$SHARD_INDEX.txt` creates it even with no match), and
  any path that leaves it missing (a failure before the sweep step, a job timeout, an upload failure) already makes
  that shard red, so `SWEEP` is not `success`. A re-run attempt re-uploads with `overwrite: true` and the download
  takes the latest. A GREEN master sweep with a missing file is not reachable from today's workflow.
- **Download step without `continue-on-error`:** a failed download is a red step; the alert step still runs
  (`!cancelled()` replaces the implicit `success()`), files any red sweep first, then raises. It cannot open a false
  `sweep-red` (that is decided by `SWEEP` alone) and cannot open a false `sweep-flaky` (it raises before filing).
  But see M1: the raise also DISCARDS the FLAKY names it did read.
- **X3:** closed — measured over every real name, above.

## Findings

### M1 — MAJOR — one missing shard file discards every OTHER shard's FLAKY names, unfiled
`scripts/sweep-red-alert.py:99-112` (`read_flaky`), `:146-149` (`main`). `fix_induced: true` (r2 X2's fold).

`read_flaky` raises when ANY shard's file is absent, and it raises BEFORE reading the files that are present, so
`file_flaky` never runs. Measured with a fake `gh`: 37 of 38 files present, `shard-0.txt` holding
`mutation FLAKY — #495: real name: SURVIVED its first run, then KILLED on its one re-run ...`, `shard-5.txt` absent:

```
failure RAISED: FLAKY_DIR '...' lacks 1 of 38 shard files (shard-5.txt): the FLAKY scan did NOT RUN
  creates: ['sweep-red']
```

The `sweep-red` issue body (`red_body`) says nothing about FLAKY; the FLAKY name read from shard-0 is filed nowhere.
This is the realistic red path, not a hypothetical: `ci.yml`'s own history records shards CANCELLED at the job
timeout (run 42387350733: shards 3, 12, 14) — a job-level timeout skips the `!cancelled()` upload, so exactly one
or a few files go missing while the other shards' FLAKY lines sit in the download. Before the r2 fold (r1), the
same partial directory filed what it found (it was silent about the gap — Codex r2 X2); after it, it is loud about
the gap and silent about what it found. The owner's rule is "named AND FILED"; a FLAKY mutant is intermittent by
definition, so the next sweep may not see it again. The `NOT RUN` text says "for them" (the missing shards), which
is correct for them and wrong for the shards that were read.

Smallest fix at the cause: read every PRESENT file, file its names (`file_flaky`), and THEN raise naming the
missing shards — the same "file first, then go red" order `main` already uses for the red alert. A case: the
partial directory above files the shard-0 name AND exits non-zero naming `shard-5.txt`.

### m1 — MINOR — the docstring's "a loop fails the copy" is false for a directory cycle; the copy multiplies first
`scripts/check-plan-code.py:2242-2245` (`rerun_snapshot` docstring), `:2253`. `fix_induced: true`.

Dereferencing a directory link to an ancestor does not fail fast: measured 33 nested copies of the tree before
ELOOP, and with two aliases growth is exponential (431 MB / 191k files in under 2 minutes from a 1 MB tree, killed
by hand). The snapshot is taken in EVERY shard run, before any budget check (`budget_spent` is checked only in
`rerun_fresh`), from a 94 MB tree. NOT reachable today — measured 0 links after all 93 real controls — so this is a
stated-bound defect, not a live one. Fix: either correct the docstring's BOUND ("a dangling or self-referencing
link fails the copy; a directory cycle is copied ~32 levels deep first"), or refuse up front when `d` holds any
symlink (`any(p.is_symlink() for p in d.rglob('*'))` → CANNOT RUN), which is cheaper than copying and states the
measured fact that no real suite leaves one.

### m2 — MINOR — the producer's file name and the consumer's are not tied by any case
`.github/workflows/ci.yml:1412` (`shard-$SHARD_INDEX.txt`), `.github/workflows/ci.yml:1508-1510` (`merge-multiple`),
`scripts/sweep-red-alert.py:106`. `fix_induced: true` (the per-file contract is new in r2).

`read_flaky` now requires the exact names `shard-0.txt`..`shard-<N-1>.txt`, but the self-test writes those names
itself (`step(...)`, `f"shard-{i}.txt"`) and never reads the shard step's `run:` block or the download's
`merge-multiple`. Two mutants on a temp copy stayed GREEN (32/32): the shard file named `shard-$SHARD_TOTAL.txt`,
and `merge-multiple: false` (each artifact lands in its own subdirectory). Both would make every master FLAKY scan
raise NOT RUN — loud, not silent, so MINOR — but the first master run is where it would be found. Fix: one case
that reads the shard step's file-name template and the download's `merge-multiple: true` out of `ci.yml`, as the
download step's `continue-on-error` is already read.

### m3 — MINOR — FLAKY names are de-duplicated across manifests, and the line does not name the script
`scripts/sweep-red-alert.py:74` (`if name and name not in names`), `scripts/check-plan-code.py:2502`.
`fix_induced: false` (r1).

Measured: 8 mutation names are shared by two or three manifests (e.g. `the main session is gated too` in
`check-agent-long-call.json` and `check-agent-large-read.json`; two `PR #440 r1 m1 ⟳ r2 ...` entries in three
manifests). The FLAKY line carries the name only, so two distinct FLAKY mutants with one name are filed as one,
and the issue cannot say which script's case is weak. Fix: put `fname` in the FLAKY line (before the name, so the
fixed tail is untouched) and file `<file>: <name>`.

### m4 — MINOR — a NOT RUN FLAKY scan on master reaches only a red check that nothing in the repo reads
`scripts/sweep-red-alert.py:148`; `scripts/session-state.py:731` (`fetch_sweep_red` lists `sweep-red` only).
`fix_induced: false` (r1 introduced the raise; r2 widened its triggers).

When the scan raises, no issue is opened (neither label), and `session-state.py` surfaces only open `sweep-red`
issues — not `sweep-flaky` ones, and not a red `mutation-sweep-complete` on master. So both a filed FLAKY and an
unrun FLAKY scan reach a person only through GitHub notifications (the "a gate's channel can be weaker than the
gate" shape). Fix candidates: `fetch_sweep_red` also lists `sweep-flaky`; and an unrun scan comments on/opens a
`sweep-flaky` issue saying NOT CHECKED before raising.

## Prior-round findings

- r2 X1: CLOSED (case + mutant red, 0 real links).
- r2 X2: CLOSED for its stated defect (a partial or empty download no longer reads as "no FLAKY"); M1 is the fold's
  new defect on the same path.
- r2 X3: CLOSED (4,663 real names, 0 wrong).

VERDICT: NOT CONVERGED
