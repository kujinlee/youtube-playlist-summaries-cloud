Reviewed head: f5a477ea39e6eda33207887cfa3698208a0ef1a4

# Round 3 — `marketplace-task16` — Claude half (adversarial)

Subject: plan Task 16, the r2 fold (2f4b59ce code + a8fa1eec rescan/records), `git diff 98efda03..a8fa1eec`, with
detector 2 of `scripts/check-publishability.py` read whole (`_fstring_path`, `_from_file`, `_Scopes`, `_Bound`,
`_inert`, `_rebinds`, `_install_root_uses`).

Method: every input below was RUN. A probe (scratch, outside the repo) imports the script and calls
`_install_root_uses(tree, parent, depth=2, held=lambda p: False)` on a fixture `scripts/x.py` whose header is
`ROOT = pathlib.Path(__file__).parent.parent` and `HERE = pathlib.Path(__file__).parent` (header = 4 lines, so the
first body line is 5). The same probe was run against the pre-fold script (`git show 98efda03:scripts/check-publishability.py`)
to settle causation. Python's own behaviour was checked by executing the nonlocal shape.

## Findings

### M1 — MAJOR — `os.path.relpath(path=ROOT)` now hides the root: the X1 input, spelt with a keyword, regressed to silent

- **Where:** `scripts/check-publishability.py:657-662` (`_inert` now steps through a keyword into the call) together
  with `:497-501` (`_from_file`'s relpath derivation reads only `node.args[0]`).
- **Input:** `os.chdir(os.path.relpath(path=ROOT))`
- **Observed:** at HEAD `[]`; at 98efda03 `[(4, '.')]`.
- **Why:** the derivation treats `relpath` as deriving the root only when the root is the first POSITIONAL argument,
  so `relpath(path=ROOT)` is not a derivation; the root is then judged at the keyword, which the fold's new keyword
  step in `_inert` carries into the call, and `os.path.relpath` is in `INERT_CALLS`. The design's direction ("an
  omission errs toward a FINDING") fails here: an omission in the derivation list meets a listed inert call and the
  result is silence. This is exactly the r2 X1 shape (`os.chdir(os.path.relpath(ROOT))`).
- **Caused by r2 fold: yes.** The keyword step in `_inert` is new in 2f4b59ce; before it, a keyword argument was never
  inert and the input was reported.

### M2 — MAJOR — an f-string holding two from-file paths is placed at the FIRST one; the root in a later piece is lost

- **Where:** `scripts/check-publishability.py:453-463` (`_fstring_path` returns the first embedded from-file path) and
  `:699-701` (the inner node is skipped whenever the outer expression is from-file, without asking whether it is
  derived from THIS node).
- **Inputs and observed (HEAD):**
  - `subprocess.run(["tool", f"{HERE}:{ROOT}"])` → `[]`
  - `os.environ["PYTHONPATH"] = f"{HERE}{os.pathsep}{ROOT}"` → `[]`
  - `subprocess.run(["x"], env={"P": f"{HERE}:{ROOT}"})` → `[]`
  - control, order swapped: `subprocess.run(["x"], env={"P": f"{ROOT}:{HERE}"})` → `[(4, '.')]`
- **Why:** the `ROOT` piece is skipped because its parent JoinedStr is "from-file" — but it is from-file at HERE's
  level (1), not the root's (2), so `place[0] != depth` drops the JoinedStr too. The claim "only the OUTERMOST
  expression still derived from the root is judged" is false here: the outermost from-file expression is derived from
  HERE. Before the fold, no other derivation could hold two from-file paths (`/`, `os.path.join` and `joinpath` take
  literal parts only), so the line-700 skip was sound; the fold's f-string derivation is the first that can.
- **Caused by r2 fold: partly.** The defect is in code the fold added (the f-string derivation feeding the existing
  skip), and it is the X1 class (a derivation hides a root that is handed on). It is NOT a regression of output: at
  98efda03 the same inputs were also `[]` (r1 called every f-string piece inert). Classify as an incomplete X1 fix,
  not as a defect the fold introduced into previously-correct output.

### m1 — MINOR — `nonlocal` resolution regressed for a middle function that binds the name only by a walrus inside a comprehension

- **Where:** `scripts/check-publishability.py:575-584` (`_nonlocal` asks `self.binds`), fed by `:534-537` and
  `_Scopes.scope` `:559-567`, which files a walrus target inside a comprehension under the comprehension (PEP 572
  binds it in the enclosing function).
- **Input:**
  ```
  def a():
      root = pathlib.Path(__file__).parent.parent
      def b():
          [(root := 1) for _ in []]
          def c():
              nonlocal root
              root = None
      return root / "docs" / "x.md"
  ```
- **Observed:** HEAD `[]`; 98efda03 `[(9, 'docs/x.md')]`. Python (executed): `c`'s `nonlocal` rebinds `b`'s `root`,
  `a.root` is unchanged, so the finding is correct and HEAD is a false negative.
- **Caused by r2 fold: yes, as a regression** — the mis-scoped walrus is pre-existing in `_Scopes.scope`, but the old
  `owner` (immediate enclosing function) did not depend on it for this shape; the fold's `_nonlocal` walk does. Rare
  input, hence MINOR.
- Other `_nonlocal` shapes checked and CORRECT at HEAD (matching Python): a class body between (skipped, `[]`); a
  middle function binding by `del`, `for`, `with ... as`, `except ... as`, `import`, or a parameter (finding kept);
  a lambda parameter of the same name (`[]`); `nonlocal` in a method of a class inside `a` (`[]`); `nonlocal` in a
  class body (`[]`); augmented assignment through `nonlocal` (`[]`).

### m2 — MINOR — an f-string tail starting `//` is read as an absolute path and the root is dropped

- **Where:** `scripts/check-publishability.py:461-462` with `_placed` `:632-634`.
- **Input:** `open(f"{ROOT}//docs/x.md")` → HEAD `[]` (98efda03 also `[]`).
- **Why:** the tail `"//docs/x.md"[1:]` is `"/docs/x.md"`, which `_placed` treats as leaving the tree; but string
  concatenation gives `<root>//docs/x.md`, a path below the root. Contrived.
- **Caused by r2 fold: partly** — in the fold's new tail-joining code, not an output regression.

### m3 — MINOR — a chained assignment of the root hides it

- **Where:** `scripts/check-publishability.py:668-675` (`_rebinds` reads `targets[0]` only) vs `:546-548`
  (`_stored` records a value only for a single-target `=`).
- **Inputs:** `R = X = ROOT` then `subprocess.run(["git"], cwd=R)` → `[]`; same with `R = X = pathlib.Path(__file__).parent.parent` → `[]`. Identical at 98efda03.
- **Why:** the binding is skipped as "judged at each use", but its stores carry no value, so no use is followed.
- **Caused by r2 fold: no** (pre-existing in r1 code). Related, also pre-existing and a STATED bound:
  `R = ROOT; R /= "docs"; open(R)` → `[]` (stores disagree, not followed) — the bound itself fails toward silence,
  which the design's "fails toward a finding" sentence does not mention.

### m4 — MINOR — the committed scan no longer matches a fresh scan at HEAD (line numbers only)

- `python3 scripts/check-publishability.py --out <scratch>` at HEAD vs `docs/marketplace/scan-2026-11-21.json`
  (`measured_at` 2f4b59ce): only component `goal-tree` differs, and it is equal once `line` is removed. The shift comes
  from `scripts/goal-tree.py` changing in the master merge 70fefa79 (#612). The committed scan is correct for its
  recorded commit.
- **Caused by r2 fold: no** (master merge). Re-scan before merge if the record must match the merged tree.

## Checked and holding

- **Self-test:** `python3 scripts/check-publishability.py --self-test` → `121/121 self-test cases passed`, rc 0; the
  docstring declares `# 121 cases` (line 5). Match.
- **Mutations:** all 15 new/replaced entries in `scripts/mutations/check-publishability.json` (diffed against
  98efda03) were applied, each alone, to a scratch copy; every one turned its NAMED case `[FAIL]` (15/15 KILLED);
  the unmutated scratch copy had 0 `[FAIL]` lines. (The copy is not a git repo, so its live-tree cases crash after
  the fixture cases; the named cases all sit before them.)
- **Derivation/terminal-use inputs that behave as claimed (HEAD):** walrus `(r := ROOT)` → `(5,'.')`; tuple
  `a, b = ROOT, 1` → reported; root returned from a helper → reported at the return; lambda / comprehension →
  reported; `os.path.exists(ROOT/"x") and open(ROOT/"x")` → `(5,'x')`; root in a list or a `**{"cwd": ROOT}` dict →
  reported; `(ROOT/"x").read_text()` → `(5,'x')`; `IfExp` / `or` → reported; `str(ROOT)` bound, compared, then
  `os.chdir(S)` → reported at the chdir; `relpath(ROOT, ROOT)` / `relpath(ROOT, HERE)` → `[]` (measured against);
  `f"{ROOT!s}/docs/x.md"` → `docs/x.md`; `sys.exit(f"cannot find {ROOT}")` → reported (a false positive, the stated
  direction).

Reviewed head: `f5a477ea39e6eda33207887cfa3698208a0ef1a4` (detector-2 code identical to a8fa1eec; `git diff
a8fa1eec HEAD -- scripts/check-publishability.py` is empty — the merge touched other scripts only).

VERDICT: NOT CONVERGED
