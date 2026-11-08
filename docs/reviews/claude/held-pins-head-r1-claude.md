Reviewed head: a4177e28dbaa4d16c07b2af9ce28cd9cd5ae3783

# held-pins-head (PR #541, backlog #538): round 1, Claude half

Mandate: REFUTE. Subject: `git diff origin/master...HEAD` (one commit, `a4177e28`).

## What was run (against `a4177e28`)

| Check | Result |
|---|---|
| `python3 scripts/check-merge-ready.py --self-test` | 354/354, rc 0 |
| `python3 scripts/check-plan-code.py --self-test` | 418/418, rc 0 (38 s) |
| Mutation `...keeps the working tree on sys.path...` (manifest index 160), hand-run in a `stage_tree` copy | rc 1; `parse_fail_names` = exactly its one `expect` case (353/354) |
| Mutation `...hides no loaded module...` (index 161), same method | rc 1; `parse_fail_names` = exactly its two `expect` cases (352/354) |
| Ad-hoc mutation: drop `sys.path[:] = saved_path` from `_isolated_import`'s `finally` | **rc 0, 354/354: SURVIVES** (R1-F2) |
| Ad-hoc mutation: replace the whole `finally` restore with `pass` | **rc 0, 354/354: SURVIVES** (R1-F2) |
| Constructed repro: dirty working-tree `pin_display` over an honest pin fall | **clean tree HOLD, dirty tree READY** (R1-F1) |
| Instrumented self-test: `tarfile` add/extract | 406 adds 0.6 s, 62 extracts 2.0 s, out of 56 s (R1-F3) |

The failure paths: a failing `git archive` and a junk archive are both CANNOT RUN and both are pinned. A harness that will not
import goes through `_import_sibling` → `PinsUnreadable`. The isolation restores in a `finally`, so an exception inside
the block still restores. I found no path where a held-side failure returns READY. No existing failure-path line is
loosened: the old `held_pins` body is replaced, and `pin_pair`'s comparison and raise are unchanged.

## Findings

### R1-F1 — High — the DISPLAY side is still parsed by the WORKING-TREE harness, so a dirty `scripts/check-plan-code.py` still turns a pin fall into READY

`scripts/check-merge-ready.py:1333` (`pins_at`: `reader = _pins_reader(PINS_READER)`), which is used for BOTH
`pins_at(run, merge_base)` and `pins_at(run, "HEAD")` at `pin_pair`. The fix moved only the HELD side to HEAD. The display's
TEXT comes from `git show`, but `pin_display`, the code that turns that text into the dict, is still imported from the
working tree. So the two sides of the comparison still disagree in source, and the base's pins are read by uncommitted
code. The commit's own claim, *"a dirty, stale or untracked file in the working tree cannot stand in for it"*, and the
dashboard entry's *"Both now come from the committed pull request"* are false for the display side. Bound (b) at
`:1349` names only *"a working tree whose code patches the standard library"*. That understates it. An ordinary
`pin_display` edit is enough, with no patching and no global rebinding.

**Repro (run, real git, the code at `a4177e28`):**
`/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/f7c144b8-1b6c-4db3-8ef1-932d4e701b12/scratchpad/hph/repro_reader.py <worktree>`
1. base commit = real `expected_mutations.py`, real `check-plan-code.py`, `coverage_verdict.py`;
2. head commit = an HONEST fall: `"scripts/check-merge-ready.py": 162` → `161` in the display (the harness holds the
   same, so held == displayed);
3. dirty the working tree only: append to `scripts/check-plan-code.py`
   `_real_pd = pin_display` / `def pin_display(src): return _real_pd(open(<worktree pins file>).read())`, which is a
   reader that ignores its argument.

Output:
```
clean tree -> ['loosens a gate: the mutation pin for scripts/check-merge-ready.py drops 162 -> 161']
dirty working-tree pin_display -> READY (nothing held)
git status: M scripts/check-plan-code.py
```
The base is now read with HEAD's values, so the fall disappears. Held (HEAD's harness) still equals the display (HEAD's
text), so the new comparison sees nothing.

**Fix:** materialise HEAD's `scripts/` ONCE per `pin_pair` and take `pin_display` from THAT module, isolated, for both
`pins_at` reads as well as `EXPECTED_MUTATIONS`. Then held and displayed share one source, and no working-tree code
reaches the pin rule. `main()` already pins HEAD to the PR head, so HEAD's reader is the PR's reader, exactly as the
working tree was assumed to be. Add the repro above as a case: a clean-tree control that HOLDs, plus a dirty reader that
must still HOLD. Pin it with a mutation that sends `pins_at` back to `_pins_reader(PINS_READER)`. Correct the
dashboard sentence and bound (b). If the owner prefers the narrower fix, then bound (b) must name this route
explicitly. *"Patches the standard library"* does not cover it.

### R1-F2 — Medium — `_isolated_import`'s restore is unpinned: deleting the whole `finally` body survives the suite

`scripts/check-merge-ready.py:1390-1394`. Two ad-hoc mutations, each run in a `stage_tree` copy by the harness's rule:
(a) drop `sys.path[:] = saved_path`; (b) replace the entire `finally` body (drop new modules, `sys.modules.update(saved_mods)`,
restore `sys.path`) with `pass`. **Both: rc 0, 354/354.** So nothing tests the "restored after" half of the isolation
contract, which is half of what the docstring and the dashboard entry promise. The reason is that `_dirty_case.ask()`
(around `:3020-3034`) snapshots and restores `sys.modules`/`sys.path` itself, which masks the production `finally`. The
fake-run cases never inspect the interpreter state afterwards. In production, `held_pins` is the last sibling import in
`main()`'s pin step, so a missing restore probably shows nothing *today*. A later sibling import (`_dashboard_gate`, or
any lazy `import`) would then run with `sys.path` reduced to the library directories and with the head harness's
`coverage_verdict` in `sys.modules`, which is the cross-contamination this PR exists to prevent, in the other direction.

**Fix:** one case at no extra cost, around an existing `held_pins` call (the fake `_prun` path): snapshot `list(sys.path)` and
`dict(sys.modules)` before, then assert equality after, on BOTH a success read and a raising read (the junk archive, or a
harness that raises on import). Add two mutations naming it: no `sys.path` restore, and no `sys.modules.update(saved_mods)`.

### R1-F3 — Low — the self-test's added cost is the 62 extra compiles of a 523 KB harness, not the archive, and most of it is avoidable

Measured, by instrumenting `tarfile` across one full `--self-test`: 406 `TarFile.add` calls took 0.6 s, and 62
`extractall` calls took 2.0 s. `compile()` of `check-plan-code.py` (523,313 bytes) costs 0.10 s on this machine. 62
fresh imports from a new temp directory each time, with no reusable `__pycache__`, make ≈ 6-8 s of compile plus module
body. That accounts for the +8 s. Most of the 62 are fake-run cases whose archive is a copy of the same harness text.
**Fix, without losing coverage:** a per-run `sys.pycache_prefix` would not help, because the cache is keyed by path
and the path differs per extract. Two things would. (i) Materialise to a STABLE per-content
directory in the fakes: `_tar_head` already knows `PINS_READER`, so cache the tar bytes and extract to one directory
per distinct tree. (ii) Memoise `compile` by source sha256 for the `_load` call in tests. The production path
(one call per run) is unaffected either way. A smaller production cost: `git archive HEAD -- scripts` ships all 219
files and ~10 MB, and unpacks in ~1.6 s per real run. Archiving `scripts/*.py` plus `scripts/mutations/` would be
enough for the harness. A harness importing from anywhere else fails closed (CANNOT RUN), as the bound already says.
This is optional.

## Not findings (checked, refuted)

- **`git archive` cwd:** `_run` sets `cwd=ROOT`, so the `scripts` pathspec is root-relative.
- **`.gitattributes` `export-ignore`/`export-subst` in a head:** an ignored harness, sibling or pins file is a missing
  import or `{}`, and both are CANNOT RUN. `export-subst` only rewrites text the head already controls. A `try/except
  ImportError` fallback that behaves differently when archived is the already-stated R8/R9 "acts differently when
  imported" bound.
- **`filter="data"`:** Python 3.12 in CI and 3.14 locally both support it. `git ls-files -s scripts` has no symlinks
  (mode 120000), so the data filter refuses nothing today. If it ever does, the result is CANNOT RUN, never READY.
- **The two hand-checked mutations pin what their names say:** each went red only through its named cases.

VERDICT: NOT CONVERGED
