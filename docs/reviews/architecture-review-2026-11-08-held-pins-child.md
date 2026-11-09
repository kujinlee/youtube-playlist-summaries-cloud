# Architecture review (Phase 6, narrow) — `held-pins-head`: the child's import isolation

Subject: `scripts/check-merge-ready.py` at `507558ed` (PR #541, backlog #538), branch `held-pins-head`.
Trigger: THRASHING in one component. r2's findings came from r1's fold, and r3's came from r2's
(`docs/reviews/coordinator/held-pins-head-r3-coordinator.md`).
Read: `CONTEXT.md`, `docs/adr/` (no ADR covers this component; none is re-litigated), the r1–r3 coordinator records,
`docs/reviews/codex/held-pins-head-r{1,2}-codex.md`, `docs/reviews/claude/held-pins-head-r{1,3}-claude.md`, and
`_head_blobs`, `_materialise`, `_DRIVER`, `_head_read`, `_json_strict`, `_child_pins` and the bound block above
`HEAD_LS`.

Python used for every measurement: 3.14.4 on macOS (`/usr/local/bin/python3`). CI pins 3.12 on Linux. Anything
claimed for 3.12 or Linux is **inferred**. The scratch harness is in
`/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/f7c144b8-1b6c-4db3-8ef1-932d4e701b12/scratchpad/arch/`:
`mkrepo.sh`, `addshadows.py`, `pername.py` (output in `pername.out`), `run_branch.py`, `probe_master.py`,
`make_c.py`, and `lows.py`.

## 1. Answer first

**(c) removes the class by construction. The other three do not.** (c) refuses, as CANNOT RUN, any materialised
top-level name under HEAD's `scripts/` that is in `sys.stdlib_module_names`.
- Collisions today: **0 on master (`b15e4f96`) and 0 on HEAD (`507558ed`)**, so the refusal costs nothing.
- **(a) is not by construction.** HEAD's harness re-prepends its own directory at `check-plan-code.py:99`.
  Appending also lets a stdlib name that this *platform* lacks resolve to HEAD: measured with `msvcrt`, `nt` and
  `_winapi`, which the child really imports.
- **(b) works.** A meta-path finder that resolves stdlib names only from the stdlib blocked all 95 names. But it is
  more machinery and gives the same coverage as (c).
- **(a)+(c): do not add (a).** Under (c), every input that (a) would catch is refused first, so no mutation can pin
  (a). It would be a masked second clause.

**A finding that changes R3-F1.** R3-F1 says master "never runs" a committed `scripts/importlib/__init__.py`, so the
branch is a loosening against master. **That is false for master as it is actually invoked.**
`python3 scripts/check-merge-ready.py` puts the working tree's `scripts/` at `sys.path[0]`.
- Master's real entry point, `--help`, **executed** the shadow `importlib/__init__.py`.
- Run from a probe with the same `sys.path[0]`, master executed **51 of 95** stdlib-named shadows.
- The branch's child executes 48 of them, a **subset** of master's 51.
- The r3 forge, extended to patch `builtins.sorted`, made master report `falls: []`.

So the class is **pre-existing on master, in the gate process itself**. The child adds no name master did not
already run. The gate process is still exposed on the branch, with (c) applied too (measured). Closing it needs a
change to how the gate starts, not to the child. That belongs in a separate backlog row (§6), not in this fold.

## 2. What the child resolves: measured, by design

**Method.**
1. A real git repository. Its base commit holds `507558ed`'s `scripts/`. Its HEAD lowers
   `scripts/check-vocabulary-collisions.py` 5 → 4 in `scripts/mutations/expected_mutations.py`.
2. An audit hook in the driver recorded every fresh import with `sys.path` at that moment (`trace0.txt`). That gave
   **82 top-level stdlib names**, all in `sys.stdlib_module_names`.
3. 13 plausible lazy imports were added (`difflib`, `textwrap`, `traceback`, `hashlib`, `string`, `typing`,
   `struct`, `base64`, `codecs`, `encodings`, `site`, `sitecustomize`, `linecache`), for **95**.
4. For EACH name ALONE, a commit added `scripts/<name>.py`. The file logs that it ran, then delegates to the real
   module, so the run still reaches a verdict.
5. Four readers ran over each commit:
   - master's gate code, exec'd from a probe file inside that `scripts/`, so `sys.path[0]` is `scripts/` as in
     `python3 scripts/check-merge-ready.py`;
   - the branch's `_head_read` at `507558ed`, which prepends;
   - driver (a): `importlib.util` imported first, then `sys.path.append`;
   - driver (b): (a) plus a stdlib-only meta-path finder.

**Totals.**

| Reader | Shadows that RAN (of 95) | Verdicts other than the honest `drops 5 -> 4` |
|---|---|---|
| master's gate process | **51** | 0 (the shadows delegate honestly) |
| branch child, prepend (`507558ed`) | **48**, all also in master's 51 | 0 |
| (a) append, driver imports first | **3**: `msvcrt`, `nt`, `_winapi` | 0 |
| (b) stdlib-only finder | **0** | 0 |
| (c) refuse stdlib-named top-level names | refused before the child starts (§3) | n/a |

**Per-name detail** (`pername.out`).
- Master only: `json`, `_json` and `linecache`. The driver imports `json` before it touches `sys.path`.
- Run by both master and the branch child:
  - `importlib`, `__future__`, `argparse`, `gettext`, `ast`, `dataclasses`, `copy`, `weakref`, `_weakrefset`
  - `inspect`, `annotationlib`, `dis`, `opcode`, `_opcode_metadata`, `tokenize`, `token`, `contextlib`, `pathlib`
  - `_winapi`, `nt`, `glob`, `fnmatch`, `grp`, `fcntl`, `shutil`, `zlib`, `bz2`, `compression`, `_bz2`, `lzma`
  - `_lzma`, `_zstd`, `subprocess`, `locale`, `signal`, `threading`, `warnings`, `_py_warnings`, `msvcrt`
  - `_posixsubprocess`, `select`, `selectors`, `math`, `tempfile`, `random`, `bisect`, `_bisect`, `_random`
- Never run by any reader:
  - built-in and frozen modules (`os`, `io`, `abc`, `posixpath`, `stat`, …), which `BuiltinImporter` and
    `FrozenImporter` answer before `PathFinder`;
  - modules already loaded before `sys.path` changes (`re`, `enum`, `functools`, `collections`, …);
  - most of the 13 extras.
- The extension modules in `lib-dynload` (`math`, `zlib`, `select`, …) ARE shadowed when the path is prepended.

**The brief's specific names, by ordering.**

| Name | master gate | branch (prepend) | (a) append | (b) finder | (c) |
|---|---|---|---|---|---|
| `re` | not run (loaded at startup) | not run (loaded by `import json` before the insert) | not run | not run | refused |
| `json` (package) | **RAN** | not run | not run | not run | refused |
| `importlib` (package) | **RAN** | **RAN** (R3-F1) | not run | not run | refused |
| `ast` | **RAN** | **RAN** | not run | not run | refused |
| lazy, after the harness's own insert at `:99` | none in this run: `coverage_verdict` was the only fresh import after `:99` | — | — | — | — |
| `msvcrt` / `nt` / `_winapi` | **RAN** | **RAN** | **RAN** | not run | refused |

**Why (a) is not by construction. Two reasons, both measured.**
1. **The harness undoes it.** `check-plan-code.py:99` is `sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))`.
   Any stdlib module first imported after that line resolves from HEAD's `scripts/` again. In this run nothing was
   (the trace shows only `coverage_verdict` after `:99`). But that is a fact about today's harness, not a property of
   the design: one new lazy `import difflib` inside `pin_display` reopens it.
2. **A name the stdlib lacks on this platform falls through to the appended entry.** On POSIX, `pathlib`,
   `shutil` and `subprocess` probe for `nt`, `_winapi` and `msvcrt` inside `try`. Appended, those probes find
   `scripts/msvcrt.py` and RUN it. The r3-style end-to-end run on a `msvcrt` shadow, driver (a), logged `msvcrt`.

The probes reveal no third route. Case-folded names do not shadow: a `scripts/Ast.py` and a `scripts/ARGPARSE.py`
under a prepended path left `ast` resolving to the stdlib, because `FileFinder` checks exact case. Submodules resolve
through their parent package's `__path__`, never through `sys.path`. So only TOP-LEVEL names matter.

**The R3 forge end to end.** The repository is `rf`. Its HEAD adds R3's `scripts/importlib/__init__.py`, plus a
`builtins.sorted` patch so that it can forge in-process too.

| Reader | Verdict |
|---|---|
| master gate process (probe) | `falls: []`: **forged** |
| branch gate process (probe, branch code) | `falls: []`: **forged** |
| branch child only (`507558ed`) | `falls: []`: **forged** (R3-F1 reproduced) |
| child, driver (a) | `drops 5 -> 4`: held |
| child, driver (b) | `drops 5 -> 4`: held |
| child, (c) | `CANNOT RUN: HEAD: 'scripts/importlib/__init__.py' is named for the standard-library module 'importlib'…` |
| child, (a)+(c) | the same CANNOT RUN |
| control: master on `r0` (no shadow) | `drops 5 -> 4` |

**Master's real entry point.** The probe is not the only evidence. In repository `rm1` I wrote master's file to
`scripts/check-merge-ready.py`, added a logging `scripts/importlib/__init__.py`, and ran
`python3 scripts/check-merge-ready.py --help`. It returned rc 0, and the log reads `importlib`. The same run with the
branch's code plus (c) also logs `importlib`, so the gate process stays exposed after the fold (§6).

## 3. The options

| | Removes the class by construction? | Measured | Cost | Pinnable |
|---|---|---|---|---|
| (a) driver imports first, then APPEND | **No**: the harness re-prepends at `:99`, and a name missing on this platform falls through | 3 of 95 still RAN | 2 lines | Yes, by `importlib`, but only while (c) is absent |
| (b) explicit load plus a stdlib-only meta-path finder | Yes, for code that does not remove the finder (HEAD code that runs can, but that is bound (c)'s trusted closure anyway) | 0 of 95 RAN; the forge held | About 20 lines of import machinery in a string; a second resolution rule beside Python's own | Yes |
| **(c) refuse a stdlib-named top-level name** | **Yes.** With no colliding top-level `.py` or package in the materialised tree, no `sys.path` order and no later insert can make a stdlib name resolve to HEAD, because `PathFinder` looks only for `<name>.py`, `<name>/` and extensions (and only `*.py` is materialised) | `rf`, `rs` (all 95) and `rw` (`msvcrt`) refused; `r0` (control) and `rn` (adjacent negatives) still read `drops 5 -> 4` | About 4 lines in `_materialise`. **0 collisions on master or HEAD today** | Yes, by any colliding name |
| (d) (a)+(c) | Yes, by (c) | as (c) | (c) plus 2 lines | **(a) is not pinnable.** Every input (a) catches, (c) refuses first, so the append mutation survives every case |

**Fails toward safety.** If a future Python adds a stdlib module that shares a name with a project file, the gate
says CANNOT RUN and names the file. It never passes in silence.

**Recommendation: (c) alone.** Keep the driver's order exactly as it is. Its `insert(0, …)` matches what the harness
does to itself at `:99`, and what `python3 scripts/check-plan-code.py` does. Under (c), ordering no longer matters
for stdlib names, so there is nothing for (a) to add. Do not ship (b): it is a second import-resolution rule that
must be kept right, and it buys nothing over (c).

## 4. The Lows

**R3-F2: the post-kill `communicate()` is unbounded.** Measured with `_head_read`'s exact sequence
(Popen with `start_new_session`, a 1 s `communicate` timeout, `killpg`, `communicate()`). The child forked a
`setsid` grandchild that sleeps N seconds and holds stdout.
- Current code, N = 6: **6.1 s**. It waits for the grandchild, so a grandchild that never exits hangs the gate.
- Bounded form, N = 60: **3.0 s**, child rc −9. The sequence is: `killpg`, then `communicate(timeout=2)`; on
  `TimeoutExpired`, close stdin, stdout and stderr, then `wait(timeout=2)`. The `setsid` grandchild survived and had
  to be killed by hand. It leaves the session, so a group kill cannot reach it. That is a stated bound, not a fix.

**The fold for R3-F2:**

```python
        except subprocess.TimeoutExpired:
            with contextlib.suppress(OSError):
                os.killpg(child.pid, 9)         # its whole session: a grandchild holding the pipes open included
            try:
                child.communicate(timeout=CHILD_GRACE)
                outlived = ""
            except subprocess.TimeoutExpired:   # a process that LEFT the session (setsid) still holds a pipe
                for pipe in (child.stdin, child.stdout, child.stderr):
                    with contextlib.suppress(OSError):
                        pipe.close()
                with contextlib.suppress(subprocess.TimeoutExpired):
                    child.wait(timeout=CHILD_GRACE)
                outlived = "; a process it started left its session and outlived the kill"
            raise PinsUnreadable(f"HEAD: the child that reads {PINS_SCRIPT} ran past {CHILD_TIMEOUT} s{outlived}") from None
```

`CHILD_GRACE = 2`, a module global beside `CHILD_TIMEOUT` so that a case can lower it.

**Tests for R3-F2.** The two observables are the message suffix and the elapsed time. Both are measured shapes; the
suite code itself is not written yet.
- **K1, the group kill.** The child spawns a grandchild in ITS session (a plain `subprocess.Popen`, no `setsid`)
  that inherits stdout and sleeps 20 s. The child itself sleeps 20 s. Run with `CHILD_TIMEOUT = 0.5`.
  - Expect CANNOT RUN `ran past 0.5 s` and NO `outlived` suffix.
  - Under `killpg → pass`, nothing is killed, so the grace expires and the suffix appears: red.
  - Under `killpg → child.kill()`, the in-session grandchild survives and holds the pipe, so the suffix appears: red.
- **K2, the escape.** The same, but the grandchild calls `os.setsid()` first and writes its pid to a file.
  - Expect CANNOT RUN with the `outlived` suffix, and elapsed time under 10 s.
  - Cleanup: `os.kill(pid, 9)` from the pid file, ignoring `OSError`.
  - Under post-kill `communicate(timeout=CHILD_GRACE) → communicate()`, it waits the grandchild's 20 s: red on the
    elapsed time.

**R3-F3 and NaN: run against `507558ed`.**
- `_json_strict` refuses `{"a":1,"a":2}`, `NaN`, `Infinity` and `-Infinity` (measured directly).
- **Duplicate key:** R3 measured that mutating `raise` to `pass` survives the suite (392/392).
- **NaN: I mutated `parse_constant`'s `raise` into `return float(...)`, in a clean clone at `507558ed`.
  `check-merge-ready.py --self-test` returned 392/392, rc 0. It SURVIVES; the NaN refusal is not tested.**

The two refusals differ in kind:
- **The duplicate key is NOT masked.** `{"…", "held": <lowered>, "held": <display>}` is schema-valid after a
  last-wins parse. Pin it with case D1: a `_forge` that writes raw text with two `"held"` keys, the first lowered and
  the last matching the display. Expect CANNOT RUN `not one JSON document` containing `duplicate key`.
- **The NaN refusal IS masked.** A non-finite number can only land where `_child_answer_ok` demands an exact `int`,
  `str` or `None`, so a `float('nan')` is already CANNOT RUN (`outside its schema`). Only the reason text differs.
  **Delete `parse_constant`** and drop "and a non-finite number" from `_json_strict`'s docstring. Pinning a message
  is not a guard. (That the schema check catches every placement is inferred from reading `_child_answer_ok`; I did
  not mutate it.)

## 5. Bound (c), re-stated

The current text says the forging edit "is in `check-plan-code.py`, which sweeps FULL". That is false on two counts.
- Any module in the harness's import closure can forge: `coverage_verdict` today, `fixture_git` on a self-test path.
- Until this fold, a stdlib-named file could forge too.

Replace the bound with:

> (c) HEAD's harness is the subject, and the child runs it the way `python3 scripts/check-plan-code.py` runs it,
> with HEAD's `scripts/` on `sys.path`. So the harness AND every HEAD module its imports reach (today
> `coverage_verdict.py`, and `fixture_git.py` on a self-test path) are trusted.
>
> Code in any of them that forges the child's answer is trusted, as `_cross`'s F4 trusts a well-typed wrong answer.
> It is HEAD code in the reviewed diff, but not necessarily in `check-plan-code.py`. Nothing here checks which sweep
> a sibling edit selects.
>
> A HEAD file cannot stand in for a STANDARD-LIBRARY module. Any materialised top-level `scripts/` name in
> `sys.stdlib_module_names` (`scripts/<name>.py` or `scripts/<name>/`) is refused, CANNOT RUN, so no `sys.path`
> order, the harness's own insert included, can resolve a stdlib import to HEAD.
>
> ⚠ This covers the CHILD only. The gate process, run as `python3 scripts/check-merge-ready.py`, has the WORKING
> TREE's `scripts/` at `sys.path[0]`, so a stdlib-named file there runs before this script's first statement. Master
> does the same: measured, 51 of 95 names. Backlog #<new>.

Bound (d) gains one sentence: "A process that leaves the child's session (`setsid`) is not killed. The gate stops
waiting for it after `CHILD_GRACE` and says so in the CANNOT RUN reason."

## 6. Out of scope for this fold: file it

The gate PROCESS has the same exposure, on master and on the branch. **File a backlog row, and do not fold it.**
- **Title:** every `python3 scripts/X.py` runs a stdlib-named file in `scripts/`, the merge gate included.
- **Evidence:** §2's master column, and the `rm1` real-entry log, with and without (c).
- **Why the fix is not in-file:** `from __future__ import annotations` is the first statement, it is itself a
  shadowable import (`__future__` RAN), and no in-file guard can run before it.
- **Candidate fixes (inferred, not run):**
  - a repository-wide CI check, run as `python3 -I scripts/<check>.py` so that it cannot itself be shadowed, that
    refuses a stdlib-named top-level name under `scripts/`;
  - and/or start the gate with `-P`.

**R3-F1's five `finding:` LOOSENING-CHECK answers rest on "master never executed it", which §2 refutes.** The next
round's answering half should re-answer those ids, `46da71649200`, `ed1d0f2f0938`, `3e8b51e50547`,
`be450713bce4` and `c47564441466`, against the gate as actually invoked. The fold still closes the child route,
because it is a real route, and after the fold the child is strictly tighter than master.

## Fold specification

**Code (`scripts/check-merge-ready.py`):**
1. In `_materialise`, after the `.py` filter and before `target = …`:
   ```python
   top = parts[1][:-3] if len(parts) == 2 else parts[1]
   if top in sys.stdlib_module_names:
       raise PinsUnreadable(f"HEAD: {path!r} is named for the standard-library module {top!r}, which it would "
                            "shadow in the child")
   ```
   It sits after the `.py` filter on purpose: only materialised files can resolve. A non-`.py` directory is never
   written. Prototype: `make_c.py` → `cmr_c.py`.
2. `_DRIVER`: **no change.** Do not append, and do not reorder.
3. `_head_read`'s timeout path: the bounded form in §4, with a new `CHILD_GRACE = 2` global.
4. `_json_strict`: delete `parse_constant` and the `constant` helper, and reword the docstring to cover duplicate
   keys only.
5. The bound block: replace (c) with §5's text, add §4's sentence to (d), and add an ⟳ r3 / Phase 6 line citing this
   document.

**New cases.** Each reads through `_pp(_honest, None, extra)` with a lowered HEAD display. The control is the same
input without the extra files, which must hold the fall.

| Id | Input (extra HEAD files) | Expect | Killed by |
|---|---|---|---|
| S1 | R3's `scripts/importlib/__init__.py` forge (a package) | CANNOT RUN, `standard-library module 'importlib'` | M1, M1b |
| S2 | `scripts/msvcrt.py` (a module; a name this platform lacks, the one append let through) | CANNOT RUN, `'msvcrt'` | M1 |
| S3 | Every name of §2's 95, each alone as `scripts/<n>.py`, plus `importlib/` and `json/` as packages | the refused set == `{n for n in NAMES if n in sys.stdlib_module_names}`, AND that set ⊇ the fixed core `{importlib, json, re, ast, argparse, __future__, msvcrt, nt, _winapi, inspect, tokenize, dataclasses, pathlib, subprocess, tempfile, shutil, contextlib}` (so the list cannot shrink to nothing on 3.12) | M1 |
| S4 (adjacent negatives) | `scripts/Json.py` and `scripts/tools/json.py`, each logging if run | still `drops 5 -> 4` (not CANNOT RUN), and nothing ran | M1c |
| K1 | child plus an IN-session grandchild holding stdout, both sleeping 20 s; `CHILD_TIMEOUT = 0.5` | CANNOT RUN `ran past 0.5 s` with NO `outlived` | M2 |
| K2 | the same, with a `setsid` grandchild that writes its pid | CANNOT RUN with `outlived`, under 10 s; cleanup kills the pid | M3 |
| D1 | `_forge` writing raw JSON with two `"held"` keys, the last one honest | CANNOT RUN `not one JSON document` with `duplicate key` | M4 |

The names for S3, with their source in `pername.out`:
- `json`, `re`, `enum`, `types`, `_types`, `_sre`, `functools`, `abc`, `_abc`, `collections`, `_collections_abc`
- `itertools`, `keyword`, `operator`, `_operator`, `reprlib`, `_collections`, `_functools`, `copyreg`, `_json`
- `importlib`, `__future__`, `argparse`, `os`, `stat`, `_stat`, `posixpath`, `errno`, `genericpath`, `gettext`
- `ast`, `_ast`, `dataclasses`, `copy`, `weakref`, `_weakrefset`, `inspect`, `annotationlib`, `dis`, `io`, `opcode`
- `_opcode`, `_opcode_metadata`, `tokenize`, `token`, `_tokenize`, `contextlib`, `pathlib`, `ntpath`, `_winapi`, `nt`
- `glob`, `fnmatch`, `pwd`, `grp`, `fcntl`, `shutil`, `zlib`, `bz2`, `compression`, `_bz2`, `lzma`, `_lzma`, `_zstd`
- `subprocess`, `locale`, `_locale`, `signal`, `threading`, `_contextvars`, `warnings`, `_py_warnings`, `msvcrt`
- `_posixsubprocess`, `select`, `selectors`, `math`, `tempfile`, `random`, `bisect`, `_bisect`, `_random`
- `difflib`, `textwrap`, `traceback`, `hashlib`, `string`, `typing`, `struct`, `base64`, `codecs`, `encodings`
- `site`, `sitecustomize`, `linecache`

S3 is refused at materialisation, before any child starts, so its cost is materialisation only (inferred cheap; not
timed). Keep the existing `_slow` timeout case as it is.

**Mutations (`scripts/mutations/check-merge-ready.json`):**

| Id | Edit | Expect (case) |
|---|---|---|
| M1 | `if top in sys.stdlib_module_names:` → `if False:` | S1, S2, S3 |
| M1b | `parts[1][:-3] if len(parts) == 2 else parts[1]` → `parts[1][:-3] if len(parts) == 2 else None` (packages unchecked) | S1 |
| M1c | `if top in sys.stdlib_module_names:` → `if top.lower() in sys.stdlib_module_names:` (over-broad: refuses `Json.py`) | S4 |
| M2 | `os.killpg(child.pid, 9)` → `pass` | K1 |
| M3 | `child.communicate(timeout=CHILD_GRACE)` → `child.communicate()` | K2 |
| M4 | `_json_strict`'s duplicate-key `raise ValueError(...)` → `pass` | D1 |

- **Retire:** none. No manifest entry targets `parse_constant`. (R3's NaN survivor shows it had none; the
  `parse_constant` text has no entry in the manifest.)
- **Re-bind:** none. The existing "child has no timeout" entry's expect, `…a child that runs past its timeout`,
  still names the unchanged `_slow` case.
- **Do NOT add** a mutation for the driver's ordering. Under (c) it is unpinnable, which is why it is not in the
  design.

**Pin arithmetic** (`scripts/mutations/expected_mutations.py`): `"scripts/check-merge-ready.py": 181` →
**187** (= 181 + 6: M1, M1b, M1c, M2, M3, M4; 0 retired; 0 re-bound). The history comment line:

> ⟳ backlog #538 Phase 6 (`docs/reviews/architecture-review-2026-11-08-held-pins-child.md`): +6. A stdlib-named HEAD
> `scripts/` name is refused (module, package, not over-broad), the group kill, the bounded post-kill wait, and the
> duplicate-key refusal. The NaN refusal is deleted: the schema check already refuses every non-int, so its only
> observable was a message.

**Verification the build must run:**
- `--self-test`, green.
- Each of M1–M4 alone, red.
- `check-plan-code.py --mutate . --only check-merge-ready.py`, 187 caught.
- Re-run `rf` against the folded code; expect CANNOT RUN.
- `git ls-tree` collisions on the merge base, still 0.

## Measured vs inferred

| Claim | Status |
|---|---|
| 0 top-level `scripts/` names collide with `sys.stdlib_module_names` on master `b15e4f96` and HEAD `507558ed` | **Measured** (3.14) |
| The child freshly imports 82 top-level stdlib names, all in `sys.stdlib_module_names`; only `coverage_verdict` after the harness's `:99` insert | **Measured** (audit hook, `trace0.txt`) |
| Shadows that RAN, of 95: master 51, branch child 48 (⊂ master's), (a) 3 (`msvcrt`/`nt`/`_winapi`), (b) 0 | **Measured** (`pername.out`) |
| Master's REAL entry (`python3 scripts/check-merge-ready.py --help`) executes a committed `scripts/importlib/__init__.py` | **Measured** (`rm1`, `real.log`) |
| The branch gate process with (c) still executes it | **Measured** (`rm1` with `cmr_c.py`) |
| R3's forge (+ a `sorted` patch) makes master and the branch report `falls: []`; (a), (b), (c) and (a)+(c) do not | **Measured** (`rf`) |
| R3-F1's "master never runs it" holds only when master is imported from outside `scripts/` | **Measured** (my entry-point run; how r3 imported master is inferred from its text) |
| Case-folded names (`Ast.py`, `ARGPARSE.py`) do not shadow; nested `tools/json.py` does not | **Measured** (macOS) |
| (c) refuses `rf`, `rs`, `rw`; it passes `r0` and `rn` | **Measured** (prototype `cmr_c.py`, `cmr_ac.py`) |
| (a) is unpinnable under (c) | **Inferred** (every (a)-caught input is a stdlib name, which (c) refuses first; not mutated) |
| Post-kill `communicate()` waits for a `setsid` grandchild (6.1 s for 6 s); the bounded form returns in 3.0 s | **Measured** (`lows.py`) |
| `_json_strict` refuses a duplicate key, NaN and ±Infinity | **Measured** |
| The NaN-refusal mutation survives the suite (392/392) | **Measured** (clean clone at `507558ed`) |
| The duplicate-key mutation survives (392/392) | Measured by R3, not re-run here |
| A NaN can only reach a place `_child_answer_ok` already refuses | **Inferred** (read, not mutated) |
| `msvcrt`, `nt` and `_winapi` are in `sys.stdlib_module_names` on 3.12/Linux, and S3's core set exists on 3.12 | **Inferred** (true on 3.14 macOS; documented as platform-independent) |
| K1/K2's mutations go red as described; S3 is cheap | **Inferred** (cases not written) |
| A sibling edit's sweep selection | **Not checked** |
| Gate-process fixes (`-P`, a CI `-I` check) | **Inferred**, not run |
