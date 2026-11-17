Reviewed head: cca375aba038e13d87350471ec5931fd774153d5

# Round 3 — `hse-slice-c` — Claude half

Scope: the round-2 fold `c223fcbf` (`scripts/check-shipping-sets.py`, `components.json`, `shipping-sets.json`).
The tree moved during the review to `cca375ab`, whose only change is a two-line anchor in
`scripts/mutations/check-shipping-sets.json` (`readable = v.format_spec is None and v.conversion`); the script is
byte-identical, so every result below holds at that head. Every input below was RUN against HEAD by loading the script and calling `python_loads` / `closure` /
`closure_gaps`, or the CLI.

## Task 1 — round-2 findings re-run at HEAD

| Id | Input | Result at HEAD |
|---|---|---|
| XM1 | `importlib.import_module(name='secret')` | FIXED — edge `scripts/secret.py` |
| XM2 | `NAME='secret'; runpy.run_path(f'{NAME!s}.py')` | FIXED — edges `scripts/secret.py`, `secret.py` |
| XM3 | unconditional `runpy.run_path('scripts/secret.py')` | FIXED — an edge, not optional; the waiver no longer exists |
| XM4 | a map carrying `optional_edges` | FIXED — `REFUSED: \`optional_edges\` is retired ...`, rc 1 |
| Xm5 | `{}` appended to real `recall.installed_files` | FIXED — `CANNOT RUN: recall: installed_files holds something that is not a path`, rc 2 |
| Xm6 | real `ci-layer` component `expected_count` = 999 | FIXED — `REFUSED: ci-layer: component 'check-plan-code' declares expected_count 999 for 1 file(s)`, rc 1 |

## Task 2 — refuting the fold

Guard forms that the proof correctly REJECTS (load stays an edge, so the closure gaps it): negated test
(`if not os.path.exists(p)`), `or`, early return, the `else` of a negated test, walrus in the test, a
reassignment inside the body (two forms), a guard in an outer function with the load in a nested `def`. All
re-run, all edges.

## Findings

- **MAJOR — scripts/check-shipping-sets.py:310 (with :344, :374):** the guard proof accepts a test on a DIFFERENT
  path. `_guarded` compares forms, and `forms` of `X / "secret.py"` drops any base it cannot read (`_base` filters
  UNK, line 374; line 344 then returns `right` alone), so `(Path.cwd() / "secret.py").is_file()`,
  `(Path(sys.argv[1]) / "secret.py").exists()` and `(Path(tempfile.gettempdir()) / "secret.py").is_file()` all
  read as the same form as `HERE / "secret.py"`. Input: installed `scripts/a.py` =
  `HERE = Path(__file__).parent` / `if (Path.cwd() / "secret.py").is_file():` /
  `    runpy.run_path(str(HERE / "secret.py"))`; `secret.py` in the repository only, not installed. Observed:
  `closure()` = `['optional: scripts/secret.py', 'scripts/a.py', ...]`, `closure_gaps` = `[]` (the CLI would say
  "loaded only inside an existence guard on itself" and count 0 gaps); run from a cwd holding a `secret.py`, the
  materialised script dies `FileNotFoundError: .../inst/scripts/secret.py`. The docstring/fold claim "a test
  proves its own single path exists" is false whenever the base is unreadable. Not a BLOCKER: the live tree's one
  optional load (`regen-pages.py:870-871`, `_cpc_path = SCRIPTS / "check-plan-code.py"` / `if _cpc_path.is_file():`)
  tests the very name it loads. Fix direction: a guard matches only when the guard and the load are the same
  NAME (or the same expression), or when neither form dropped a base. (fix_induced: yes — the guard proof is the
  r2 fold's.)

- **MAJOR — scripts/check-shipping-sets.py:379 (with :250-261):** a load whose path is built by a
  self-referencing assignment is read as a WRONG concrete path and silently dropped — no edge, NOT listed
  unresolved. `_name` returns `set()` on a cycle (`if key in seen: return set()`, line 379), so in
  `p = 'secret'` / `p = p + '.py'` / `runpy.run_path(p)` the second assignment contributes nothing and `p` reads
  as `'secret'` (no such file, so no edge). Same silent outcome for `p += '.py'` (`_assigned` ignores
  `AugAssign`), a name rebound by `global` in a called function (reads the module value), and a tuple target or
  `except ... as p` in a function shadowing a module-level name (reads the module's `other.py` — a false edge AND a
  dropped one). Observed (`python_loads('scripts/a.py', ...)`): `({'scripts/secret', 'secret', 'scripts/runpy.py'},
  set(), [])` for both the self-reference and `+=`; `({..., 'scripts/other.py', 'other.py'}, set(), [])` for the
  tuple, `global` and `except as` inputs. Closure on an installed `scripts/b.py` with the self-reference:
  `closure_gaps` = `[]`, no `unresolved:` line; running it: `FileNotFoundError: .../scripts/secret.py`. This
  contradicts the r2 docstring (lines 37-40: "one assignment of several it cannot read — is never dropped") and
  the fold's "the docstring claim is now exact". Not a BLOCKER: over the 23 shipped `.py` files, no `_name` cycle
  fires and no loader argument names an `AugAssign`/`global`/tuple-bound name (checked loader calls, not argv
  lists). (fix_induced: no — the cycle return and `_assigned` predate c223fcbf; the false coverage claim is r2's.)

- **MINOR — scripts/check-shipping-sets.py:286-290:** the proof is LEXICAL, not temporal: anything between the
  test and the load that changes what the path names still passes as guarded. Inputs: `if os.path.exists(p):
  swap(); runpy.run_path(p)` with `swap` rebinding `global p = 'other.py'` → `optional {'secret.py', ...}`, and
  `other.py` is not an edge at all; `if os.path.exists(p): os.remove(p); runpy.run_path(p)` → optional; a lazy
  generator `(runpy.run_path(p) for _ in [0])` created in the guard body and consumed after it → optional. All
  contrived; no live instance. Worth one sentence in the BOUND. (fix_induced: yes.)

## The live result

- `--self-test`: `126/126 self-test cases passed`.
- `--map docs/marketplace/components.json`: `0 gaps`, rc 0.
- `--closure docs/marketplace/shipping-sets.json`: `0 gaps`, rc 0; one `optional: scripts/check-plan-code.py`
  (comprehensibility, the correct guard above), `ci-layer: SKIPPED`.
- The 28 `unresolved:` lines — none hides a shipped dependency a stranger needs:
  - 7 are self re-execs `[sys.executable, str(pathlib.Path(__file__).resolve()), "--watch"|"--start"|"--stop"|
    "--status"]` (`ask_answerer.py:1216, 2369, 2373, 2391, 2397`; `explainer-serve.py:2817`) — the file itself.
  - `check-rc-contract.py:296` `subprocess.run(["bash", str(hook)], ...)` — `hook = _stub_tree(...)` in a temp
    dir, a self-test stub.
  - 20 in `check-surface-recall.py` are calls of the wrapper `render(rc, out, hook=None)` (line 202) whose
    `bash target` reaches either a self-test fixture (`hook=_fx`, `_fxt`, `fx`) or the default
    `HOOK = ROOT / ".claude" / "hooks" / "surface-recall.sh"` (line 41), which `recall` declares in its
    `installed_files`.

VERDICT: NOT CONVERGED
