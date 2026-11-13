Reviewed head: 9f12aea5275516c53e0d9dff566016cb39e9e6ab

# Round 3 — `held-pins-head` (PR #541, backlog #538) — Claude half (adversarial, mandate: REFUTE)

Codex is skipped this round by alternation. I read the r1 and r2 coordinator records, the r2 Codex review, and
`git show 9f12aea5`.

## What I ran (on 9f12aea5, worktree clean)

| Check | Result |
|---|---|
| `python3 scripts/check-merge-ready.py --self-test` | 392/392, rc 0. Wall time 72–105 s on a loaded machine; user CPU 36–39 s |
| `python3 scripts/check-plan-code.py --self-test` | 418/418, rc 0 |
| `stage_tree` control (no edit) | 392/392, rc 0 |
| Mutation A: the child's `"scripts"` pointed at `PINS_READER.parent` (the working tree) | **killed**, rc 1: "a head whose harness imports a module HEAD does NOT hold… untracked copy" (True, False, False) |
| Mutation B: `_json_strict`'s duplicate-key `raise` → `pass` | **SURVIVES**, 392/392 (R3-F3) |
| Mutation C: the timeout path's `os.killpg(child.pid, 9)` → `pass` | **SURVIVES**, 392/392 (R3-F2) |
| `check-merge-ready.py --pr 541 --flagged-block` | 15 ids, answered below |

Each mutation ran alone in a fresh `stage_tree` copy, with `PYTHONDONTWRITEBYTECODE=1`.

## Findings

### R3-F1 — Medium — A committed `scripts/importlib/` forges the child's answer: master HELD this fall, the branch reads none

**FOLD-INDUCED** (r2 fold, `_DRIVER`). Location: `scripts/check-merge-ready.py:1526-1528`, and bound (c) at `:1410-1412`.

The driver puts HEAD's `scripts/` at `sys.path[0]` (`:1526`) and only THEN runs `import importlib.util` (`:1528`).
In a `-I -B -S` child, `importlib` is not yet in `sys.modules` (measured: only `_frozen_importlib` and
`_frozen_importlib_external` are loaded). So a HEAD `scripts/importlib/__init__.py` or `scripts/importlib.py` is
imported as `importlib`. It runs before the harness loads, inside the driver, and can rewrite what the driver
serialises. `json.dumps` reads the module global `json._default_encoder` at call time, so the captured `_dumps` does
not protect the output.

In the master gate process, `importlib.util` is imported at the top of `check-merge-ready.py:51`, so the same
committed file never runs. **Bound (c) says the forging edit "is in `check-plan-code.py`, which sweeps FULL". That is
false for this route:** `check-plan-code.py` is byte-identical to the honest one.

**Repro.** A real git repository. The base commit holds the real `scripts/*.py` and `scripts/mutations/expected_mutations.py`.
The HEAD commit lowers `scripts/check-vocabulary-collisions.py` 5 → 4 in the display and adds:

```python
# scripts/importlib/__init__.py
import os, json
_std = os.path.join(os.path.dirname(os.__file__), "importlib")
__path__ = [_std]
exec(compile(open(os.path.join(_std, "__init__.py")).read(), os.path.join(_std, "__init__.py"), "exec"), globals())
class _E(json.JSONEncoder):
    def encode(self, o):
        if isinstance(o, dict) and "held" in o and isinstance(o.get("base"), dict):
            o = dict(o); o["base"] = o["head"]
        return json.JSONEncoder.encode(self, o)
json._default_encoder = _E()
```

`pin_pair(run, "basebr")` then `pin_falls`, with each module's file placed in that repository's `scripts/`:

```text
master falls: ['loosens a gate: the mutation pin for scripts/check-vocabulary-collisions.py drops 5 -> 4']
branch falls: []
```

The control is the same repository after a commit that removes only `scripts/importlib/`. There, both master and
the branch report the 5 → 4 fall.

**Why Medium, not High.** The route needs committed code under `scripts/` named after a stdlib package, and that code
appears in the reviewed diff. Master already trusts a forging *sibling* that the harness imports, such as
`coverage_verdict.py`. So the trust CLASS is the same. But this input is one master refused, and the stated bound
misdescribes where a forging edit has to be.

**Fix.**
1. In `_DRIVER`, `import importlib.util` BEFORE `sys.path.insert(0, req["scripts"])`, next to `import json, sys`. I
   measured that `json.dumps`/`json.loads` import nothing lazily afterwards, so `importlib` is the only driver import
   that follows the insert.
2. Add a case built from this repro: a committed `scripts/importlib/__init__.py` beside an honest harness and a
   lowered display. It must HOLD the fall, equal to the control, and it is killed by moving the import back.
3. Reword bound (c). HEAD's `scripts/*.py` that the HARNESS imports are trusted, as they are when it runs as
   `python3 scripts/check-plan-code.py`, whose script directory is `sys.path[0]`. A forging edit can therefore be in
   any of those files, not only `check-plan-code.py`.

### R3-F2 — Low — The timeout's group kill is unpinned, and the second `communicate()` has no bound

**FOLD-INDUCED.** Location: `scripts/check-merge-ready.py:1602-1607`.

- **Mutation C survives.** Replacing `os.killpg(child.pid, 9)` with `pass` leaves the suite at 392/392. The timeout
  case's child sleeps 3 s and exits by itself, so `child.communicate()` returns either way. A child that never exits
  would hang the gate with no verdict. The bound the brief describes as a "60 s group-kill timeout" is not witnessed.
- **The kill can be escaped.** A grandchild that calls `setsid()` leaves the session. It keeps stdout open, and the
  unbounded `child.communicate()` at `:1606` waits for it. Measured with the same Popen/`killpg`/`communicate()`
  sequence, a 1 s timeout, and a `setsid` grandchild sleeping 8 s: it returned after 8.1 s. A grandchild that sleeps
  forever is a permanent hang. This fails closed (never READY), and only HEAD code can do it.

**Fix.**
- Make the timeout case's child spawn a grandchild in its session that holds stdout and sleeps 30 s. Assert the
  verdict arrives in well under that time. This kills both `killpg` → `pass` and `killpg` → `child.kill()`.
- Bound the post-kill `communicate()` with a short timeout, then close the pipes.
- State in the comment at `:1605` that a process which leaves the session is not killed.

### R3-F3 — Low — `_json_strict`'s duplicate-key refusal is unpinned

**FOLD-INDUCED.** Location: `scripts/check-merge-ready.py:1565-1576`.

Mutation B, the duplicate-key `raise` → `pass`, survives at 392/392. The driver's `json.dumps` of a dict cannot emit
a duplicate key, so only a forged answer can. Bound (c) trusts a forged answer anyway, which keeps this Low.

I did not check whether a refused NaN is pinned. Treat that as NOT RUN, not as passing.

**Fix.** Either add a `_forge` case with a duplicated `"held"` key, killed by mutation B (and one with `NaN`), or drop
the "refusing duplicate keys and NaN" claim from the commit/comment, since nothing the suite can see depends on it.

## Answers to the mandate

**1. Can the child read anything but HEAD's `scripts/*.py`?**
- **Environment.** Each of the following was set to a directory holding a `json.py` that prints `LEAK`:
  `PYTHONHOME`, `PYTHONPATH`, `PYTHONSAFEPATH`, `PYTHONPLATLIBDIR`, `PYTHONSTARTUP`, `PYTHONUSERBASE`,
  `PYTHONEXECUTABLE`, and `__PYVENV_LAUNCHER__`. Under `-I -B -S` none of them reached `sys.path`, and nothing leaked.
  On macOS, `PYTHONEXECUTABLE` still rewrites `sys.executable`, and pointed at a fake venv with a `pyvenv.cfg` it also
  changes `sys.prefix`. `sys.path` stayed the base stdlib in both cases.
- **A venv `sys.executable` with a `.pth`.** A real `python3 -m venv`, with a `.pth` that writes to stderr. `-I -B -S`
  did NOT run it. `-I` alone did run it, so `-S` is what blocks it, and that is confirmed.
- **cwd.** `sys.flags.safe_path=True` and `isolated=1`, so neither the cwd nor `''` is on `sys.path`. The cwd is the
  temporary directory in any case.
- **Stdlib-named HEAD files.** `json` and its dependencies are imported before the insert. `importlib`/`importlib.util`
  are imported AFTER it, which is R3-F1. The harness's own stdlib imports (`argparse`, `ast`, …) are shadowable by HEAD
  siblings, exactly as when the harness runs as a script. That is HEAD code in the harness's import closure.
- **Symlinks.** `_head_blobs` refuses anything but modes 100644 and 100755. `_materialise` opens with `"xb"`, under
  `scripts/` only, and refuses empty, `.` and `..` parts. A case-folded collision raises and becomes CANNOT RUN. I found
  no symlink route. The bytecode refusal checks suffixes case-sensitively (`.pyc`), but a `.PYC` is not `*.py`, so it is
  never written, and that is harmless.

**2. Can a child outcome read READY when it should be CANNOT RUN?**
- **Extra text or a partial write.** `_json_strict` needs exactly one document, and the "noise at import" case pins this.
- **Exit 0 with stderr.** It is accepted, but only after the schema check, which is correct.
- **Swapped sides.** The driver's own code cannot swap them. Only a forge can, which is bound (c), except for R3-F1's
  route.
- **A timeout with grandchildren.** It fails closed, but it can hang (R3-F2).

READY is reachable wrongly only by R3-F1.

**3. Is the stated bound sound?** The trust class equals master's. Master ran the working-tree harness and its
siblings in-process; the branch runs HEAD's committed `scripts/*.py`, which is narrower in WHERE the code comes from.
The bound's sentence that the forging edit "is in `check-plan-code.py`" is wrong: siblings already break it, and
R3-F1 adds a file that master's gate never executed.

**4. Retired mutations, re-pinning, and the tightened case.**
- I diffed the manifest against `dd7a2977`. Ten names left the old manifest, but two of them are master's
  `pins_at`/SystemExit entries renamed and re-bound (to `_child_pins` and the driver's `BaseException`), so
  8 = 10 − 2. Seven names are new, two of which are those same renamed entries, so 5 = 7 − 2.
- Three re-bound entries keep their names: #536, the working-tree harness, and C-F1. 5 = 3 + 2.
- Each of the 8 retired entries targets code that is gone from the file: `_isolated_import`, `_lib_roots`, `own()`,
  `saved_mods`, the per-call `got` cache, and the restore. `grep` finds none of them.
- Their subjects are covered by the `-I` entry, the untracked-copy case (mutation A killed it), and the X-F3
  "UNCHANGED" case.
- The tightened SystemExit case adds `"SystemExit" in r`. With an `except Exception` catch the child would exit 0 with
  empty stdout, and the verdict would name a JSON error, not SystemExit. The case is therefore red, so it was tightened
  correctly.
- `-B`/`-S` stay unpinned, as the comment states.

**5. Self-test cost (Low at most; not filed as a finding).**
- Measured: 122 `_head_read` calls take 31.6 s of a 52.9 s in-process run.
- A bare `-I -B -S` child costs 0.036 s. Most of each roughly 0.26 s call is compiling the roughly 7,000-line harness
  from source, because no bytecode exists or is written.
- `-X frozen_modules` is already on by default in this build, so it gains nothing.
- A real cut needs either a driver that answers several display pairs per child (one child per fixture), or a
  bytecode cache, and a cache reopens X-F1. I would not trade coverage for it.

**6. PR #543 behaviour.**
- The merge base is `b15e4f96`, which is `origin/master`.
- Comparing the AST-unparsed text of the two files: `flag_id`, `failure_path_flags`, `flagged_block`, `flag_binds`,
  `answered_flags` and `review_answers` are IDENTICAL to master.
- Master's mutation entries survive, except the two `pins_at` entries re-bound because `pins_at` is deleted.

## Judgement

All three findings come from the r2 fold, in the same component (`isolation`). r2's findings were caused by r1's fold
in that component too. By the definition in `docs/dev-process.md` (two consecutive rounds with fold-induced findings
in one component), this is **THRASHING**, although the class has shrunk: the r2 redesign removed every in-process
route, and R3-F1 is a one-line import ordering plus a corrected bound sentence.

## Loosening answers
LOOSENING-CHECK d2d3b8498823: not a loosening
LOOSENING-CHECK a3675a17d265: not a loosening
LOOSENING-CHECK c65bf04c5a84: not a loosening
LOOSENING-CHECK 7987d773f208: not a loosening
LOOSENING-CHECK aeac2f13505f: not a loosening
LOOSENING-CHECK 46da71649200: finding: HEAD's display/held read now runs in a child whose driver imports importlib after HEAD's scripts/ is on sys.path, so a committed scripts/importlib/__init__.py (harness unchanged) rewrites the child's answer and a 5 -> 4 pin fall that master HELD reads as no fall
LOOSENING-CHECK ed1d0f2f0938: finding: the display parse is serialised by a driver that a committed scripts/importlib/__init__.py can subvert before the harness loads; with it the base display is reported as HEAD's and master's held 5 -> 4 fall is not seen
LOOSENING-CHECK 1ae2b3e74a4b: not a loosening
LOOSENING-CHECK e36f8dfa2eb5: not a loosening
LOOSENING-CHECK bb9bf96e21f2: not a loosening
LOOSENING-CHECK 3e8b51e50547: finding: the merge base's pins now come from the child, and a committed scripts/importlib/__init__.py makes them equal HEAD's lowered display, so a pin fall master HELD reads as none
LOOSENING-CHECK be450713bce4: finding: HEAD's displayed pins now come from the child, which a committed non-harness scripts/importlib/__init__.py can rewrite before serialisation, an input master never executed
LOOSENING-CHECK c47564441466: finding: the held pins now come from the child's JSON, which a committed scripts/importlib/__init__.py can rewrite, so the held-versus-display check master enforced from the harness module itself can be forged without editing check-plan-code.py
LOOSENING-CHECK 7514eca741d1: not a loosening
LOOSENING-CHECK 90f61d5b450f: not a loosening
VERDICT: NOT CONVERGED
