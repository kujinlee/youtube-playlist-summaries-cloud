Reviewed head: 244a6c02450ebb490628a7d8b43d2311c78ac4aa

# hse slice C — Phase 6 redesign, round 1, CLAUDE half

Subject: `git diff e0c64704..244a6c02` — `scripts/check-shipping-sets.py`, the crash-guard case in `scripts/regen-pages.py`,
`scripts/mutations/check-shipping-sets.json`, `scripts/mutations/regen-pages.json`. Spec:
`docs/reviews/coordinator/architecture-review-2026-11-17-hse-slice-c.md`. I did not read `docs/reviews/codex/`.

All the work was done in a scratch directory outside the repository, on copies of the two versions:
`new.py` from 244a6c02 and `old.py` from e0c64704. The tree was not mutated.

## Gates I ran (on 244a6c02's tree)

| Check | Result |
|---|---|
| `check-shipping-sets.py --self-test` | 134/134 pass (~71 s) |
| `check-shipping-sets.py --map` | rc 0, 0 gaps |
| `check-shipping-sets.py --closure` | rc 0, 0 gaps, 65 `unresolved:` lines, 0 lines carrying `optional` |
| `regen-pages.py --self-test` | 121/121 pass |
| New and changed mutations in `check-shipping-sets.json` (21 = 13 added + 8 with changed edits), each applied to a scratch copy with `PLAN_CODE_MUTATION_RUN=1` | 21/21: every anchor matched exactly once, and every mutation turned its NAMED case red (exact-name match on `[FAIL]` lines, cut at `": got "`) |
| Live tree, old vs new `exec_edges` over all 115 tracked `.py` files | 344 edges each; lost 0, gained 0 |
| Live tree, old vs new unresolved lines | old 67, new 191; no load that old listed is silent in new |

## Prediction verdicts

- **(b) — live-tree edges unchanged, no `--map`/`--closure` gap: NOT refuted.** The edge sets are identical (344/344, set
  difference empty in both directions), and both modes report 0 gaps.
- **(c) — no test weakened: REFUTED, Minor** (Cm2 and Cm3). Every removed check-shipping-sets case is either obsolete,
  because the `optional` concept is gone, or replaced by an equal-or-stricter one. The XM2 expected list grew. The
  exceptions are the regen-pages crash case and the pinned live-tree count.
- **(a) — every syntactic mention of a loader, interpreter, shell or binder is an edge or an unresolved line:
  REFUTED** (CM1, CM2, CM3). Every input below gives NO edge to the secret file and NO `unresolved:` line under
  244a6c02. I ran each one as a fixture `scripts/a.py`, through `python_loads` with real `is_file`/`is_dir`.

## Findings

### CM1 — Major — an interpreter argv with `-c`/`-m` is silent (`scripts/check-shipping-sets.py:511-513`)
- **Inputs, each silent:**
  - `subprocess.run([sys.executable, "-c", "import runpy; runpy.run_path('secret.py')"])`
  - `subprocess.run([sys.executable, "-m", "secret"])`
  - `subprocess.run(["bash", "-c", "bash secret.sh"])`
  - `subprocess.run(["sh", "-c", "python3 secret.py"])`
- **Observed:** no edge and no unresolved line. The argv loop sets `read=True` on `-c`/`-m` and breaks. The
  interpreter word counts as a consumed head, so the interpreter census stays quiet as well.
- **Why it matters:** the interpreter word IS in the syntax, so this falsifies (a) as stated. A `-c` string is
  code the reader does not read, and a `-m` module is a load. Neither is "read".
- **Live tree:** `scripts/session-state.py` has `-c`/`-m` argvs at :1653, :1675, :1680, :1686, :1699, :1702 and :1706.
  All are silent today.
- **Caused by the redesign?** Yes, by design: the spec makes `-c`/`-m` terminal and read. The fix is cheap and
  consistent with fail-closed: list them as unresolved, at least `-m <name>` and any `-c` string that mentions a loader
  or interpreter.
- **Old reader:** also silent.

### CM2 — Major — the interpreter and loader censuses are closed lists of exact strings (`scripts/check-shipping-sets.py:183-190`, censuses at :567-586)
- **Inputs, each silent:**
  - Interpreter spelled another way: `subprocess.run(["/bin/bash", "secret.sh"])`, `["python3.12", "secret.py"]`,
    `["/usr/bin/python3", "secret.py"]`, `["zsh", "secret.sh"]`.
  - Argv built from a string: `subprocess.run("python3 secret.py".split())`,
    `subprocess.run(shlex.split("bash secret.sh"))`.
  - Loaders not on the list: `runpy.run_module("secret")`; `importlib.machinery.SourcelessFileLoader` plus
    `spec_from_loader`; `imp.load_source("s", "secret.py")`.
- **Observed:** no edge and no unresolved line.
- **Why it matters:**
  - `INTERPRETERS = ("python","python3","bash","sh")` is compared against whole strings. A path-qualified or
    versioned interpreter is not "a mention", even though the Markdown reader's `EXEC_RE` accepts `python3.N`, so the
    two readers disagree.
  - The docstring's bound excludes only *non-Python, non-shell* interpreters. `/bin/bash` and `python3.12` are
    neither, so the code is worse than its stated bound.
  - A string containing `python3 ` that becomes an argv after `.split()` is a mention in syntax.
  - `run_module` is the module twin of the already-listed `run_path`.
- **Caused by the redesign?** Yes. The census is new, and its vocabulary sets the census's reach.
- **Old reader:** also silent.

### CM3 — Major — `import_module`/`__import__` of a sibling DIRECTORY gets no unresolved line (`scripts/check-shipping-sets.py:641` vs :550-555)
- **Input:** `importlib.import_module('pkg')`, or `__import__('pkg')`, with `scripts/pkg/` a directory beside the file.
- **Observed:** no edge to anything in `pkg/` and no unresolved line. `closure` then drops the edge to the
  nonexistent `scripts/pkg.py` silently.
- **Cause:** only `Import`/`ImportFrom` statements get the `is_dir` package check. The call-form module loaders take
  the file-only path.
- **Why it matters:** the redesign's outcome census (no existing candidate → UNRESOLVED) is implemented for one of
  the two module-load forms. The `p6_imports` control exercises only `import_module('secret')` with a file, never a
  directory.
- **Caused by the redesign?** Yes, an incomplete half of a new mechanism.
- **Old reader:** emitted the edge `scripts/pkg.py`, also unlisted.

### Cm1 — Minor — a nested function's default parameter is resolved at module scope (`scripts/check-shipping-sets.py:537`)
- **Input:**
  `base = "other.py"` at module level, then
  `def outer(): base = "secret.py"; def f(p=base): runpy.run_path(p); f()`.
- **Observed:** an edge to `other.py`. `secret.py`, the path actually loaded, has no edge and no unresolved line.
  That is a wrong edge plus a silent drop.
- **Cause:** `site = None` whenever the bound value is in `fn.args.defaults`. Defaults are evaluated in the
  *enclosing* scope, which is module scope only for a top-level function.
- **Caused by the redesign?** No. It is pre-existing: old.py:471 gives the same output.

### Cm2 — Minor — the pinned live-tree case asserts a COUNT, not the edge set (`scripts/check-shipping-sets.py`, the pinned case near :2109-2117)
- **Input:** a mutation that drops one live edge and adds one spurious edge.
- **Observed:** `(344, [])` still holds. The case name claims "lost none and gained none", which a count cannot
  witness.
- **Side effect:** any unrelated future commit that adds a load turns the case red with no diff shown.
- **Fix:** pin the set's hash, or list the delta.
- **Caused by the redesign?** Yes, the case is new.

### Cm3 — Minor — the regen-pages crash case no longer rejects a second `[FAIL]` line (`scripts/regen-pages.py:885-896`)
- **Input:** mutate the guard's print to emit `  [FAIL] {CRASH_CASE}\n  [FAIL] a second, unattributable name\n    after case: …`.
- **Observed:**
  - Old observation: `(1, [CRASH_CASE, 'a second, unattributable name'], True)`, which differs from the expected
    value, so it goes red.
  - New observation: `(1, '  [FAIL] ' + CRASH_CASE, True)`, which equals the expected value, so it passes.
- **Why:** the new case checks only the first line. It is otherwise stricter on exact indentation and the
  after-case line, and it removes a `NOT RUN` branch.
- **Fix:** also assert `sum(l.lstrip().startswith("[FAIL] ") for l in out.split("\n")) == 1`.
- **Caused by the redesign?** Yes.

### Cm4 — Minor — two silent classes with no stated bound
- **Module edge to a nonexistent file:** `sys.path.insert(0, ...)` then `import secretmod` gives an edge to
  `scripts/secretmod.py`, which does not exist. `closure` filters it out with no unresolved line, the same
  mechanism as CM3.
- **Python execution with no interpreter word:** `pty.spawn("secret.sh")` and `subprocess.run(["./secret.sh"])` are
  silent. They mention no loader or interpreter, so they fall outside prediction (a). Still, the docstring states
  this bound only for Markdown/shell, not for Python files.
- **Caused by the redesign?** No; both pre-exist. `asyncio.create_subprocess_shell` is also silent, but that is
  inside the stated "shell census by name only" bound.

## Behaved correctly (inputs that were an edge or a listed line)
- **Edges:**
  - `asyncio.create_subprocess_exec(sys.executable, "secret.py")`
  - a lambda wrapper
  - a class-attribute path
  - a walrus inside a default
  - a try/except alias of a loader
  - `os.execv`
  - a nested wrapper's call-site scope
- **Flags skipped correctly:** `-I`, `-E`, `-W x`, `-Xdev`, `bash -e`.
- **Listed, correctly:** `--check-hash-based-pycs`, `bash -o pipefail`.

## Manifests
- **`check-shipping-sets.json`:** goes from 184 to 186 entries. 11 are removed, matching the spec. 13 are added:
  the spec's 12 plus a shell-census mutation. 8 have changed edits with the same `expect`. All 21 new or changed
  entries were run, and each turned its named case red.
- **`regen-pages.json`:** only the two crash mutations' `expect` strings changed. The spec says three; grep finds
  only two crash mutations. The expect strings match the new case name. I did not run them.

## Loosening answers
LOOSENING-CHECK d33473a96a90: not a loosening
LOOSENING-CHECK 190b73aac639: not a loosening
LOOSENING-CHECK 939acd9343c1: not a loosening
LOOSENING-CHECK cc245bcb0786: not a loosening
LOOSENING-CHECK 19469b8e02fd: not a loosening
LOOSENING-CHECK c831b4186cd2: not a loosening
LOOSENING-CHECK f5afa5051b4a: not a loosening
LOOSENING-CHECK ff1226fbb8bc: not a loosening
LOOSENING-CHECK a34553d561d3: not a loosening
LOOSENING-CHECK 11b86e8a177d: not a loosening
LOOSENING-CHECK c4530de76b8a: finding: Cm3 — the case now reads only the first output line, so a guard that prints a second unattributable [FAIL] line passes where master's parse_fail_names comparison went red
LOOSENING-CHECK 63c2d7b9967f: not a loosening
LOOSENING-CHECK 2b345742f57d: not a loosening
LOOSENING-CHECK 629172a8b7e0: not a loosening
LOOSENING-CHECK 33af64a6b800: not a loosening
LOOSENING-CHECK b27c359b9752: not a loosening
LOOSENING-CHECK 463867463adb: not a loosening
LOOSENING-CHECK e7535ba71eed: finding: Cm3 — the expected value pins one first-line string instead of master's exactly-one-name list, so an extra [FAIL] line is no longer refused
LOOSENING-CHECK 6b6b1d7f84eb: not a loosening
LOOSENING-CHECK ad4c58b480b5: not a loosening

VERDICT: NOT CONVERGED
