# Phase 6 architecture review — the load reader in `scripts/check-shipping-sets.py` (PR #598, `harness-ships-elsewhere` slice C)

- Subject: `_Loads` (`forms`, `_base`, `_name`, `_assigned`, `_tested`, `_guarded`, `paths`), `python_loads`,
  `exec_edges`, `closure_edges` and the `optional: ` / `unresolved: ` notes, branch `hse-c`, read at `3cb290b8`.
- Armed by THRASHING: round 2 carried XM1 to XM5 (caused by the round-1 fold) and round 3 carries CM1 and Cm3
  (caused by the round-2 fold), both in component `optional-edges`, with CM2 beside them in `edge-reader`
  (`hse-slice-c-r2-coordinator.md`, `hse-slice-c-r3-coordinator.md`, `claude/hse-slice-c-r3-claude.md`,
  `codex/hse-slice-c-r2-codex.md`).
- Read first: `CONTEXT.md` (it defines no term for an edge, a closure or an optional load), `docs/adr/` (none governs
  this reader; ADR-0013's principle, *assert the capability, do not digest the privilege*, is the same move as
  question 1 and nothing here re-opens it), the round 2 and round 3 documents above, `docs/review-method.md` →
  *The stop condition* and *Can a redesign remove it?*, and the shape precedent
  `architecture-review-2026-11-15-harness-ships-elsewhere-b.md`.
- No tracked code was changed. Every fixture ran against a COPY of the script in the session scratch directory; the
  prototype reader lives there too and is not part of this commit. Nothing under `.claude/plans/` was read.
- Every claim is tagged **[M]** (measured here: a command was run and its output read) or **[I]** (inferred).
- Baseline at `3cb290b8` **[M]**: `--self-test` 126/126, `--map docs/marketplace/components.json` 0 gaps,
  `--closure docs/marketplace/shipping-sets.json` rc 0, 0 gaps, 28 `unresolved: ` lines, 1 `optional: ` line
  (`comprehensibility: optional: scripts/check-plan-code.py`).

## Recommendation

**Route: REDESIGN.** One fold, three moves, in this order.

1. **Delete `optional-edges` outright.** No `_tested`, no `_guarded`, no `guards` argument, no `optional` return
   slot, no `optional: ` note. A load under an existence test is a plain edge: shipped or a gap. The one live
   guarded load (`scripts/regen-pages.py:870`) is removed at its source, by making the crash-guard case stop loading
   `check-plan-code.py` (section 1). Do NOT ship `check-plan-code.py` in the plugin.
2. **Make the reader fail CLOSED by census.** The reader stops asking "which forms do I recognise" and instead
   counts every place a load can enter (a loader name, an interpreter word, a name binding, a path that resolves to
   nothing) and requires each one to end as an edge or as an `unresolved: ` line. What is not positively read is
   listed (section 2).
3. **State what is left as bounds in the docstring, by name** (section 4), and FILE two follow-ups rather than build
   them: a per-file `unresolved` count in the declaration, and a consumer-side witness for the `[FAIL]` contract.

Not `accrete`: two accrete bets on this component already lost (the decision log rows of `3cb290b8`), and the
round-3 patch list (compare bases in `_guarded`, read `AugAssign`, read `global`) was measured here to leave 20 more
dropped inputs behind it (section 3). Not `split`: the two components fail for one reason each and one fold removes
both. Not `defer`: CM1 is a wrong `0 gaps` on a shipped package, which is the deliverable.

## 1. Can `optional-edges` be deleted? Yes

### What it is, and why it thrashes

`optional-edges` is a STATIC proof of a RUNTIME property: "this load runs only when its file exists". Each round
found a program for which the syntax says yes and the run says no:

| Round | Finding | The gap between syntax and run |
|---|---|---|
| 2 | XM3, XM4 | a map waiver named a load nobody proved guarded |
| 3 | CM1 | the test is on a different path, equal only after an unreadable base is dropped (`:310`, `:344`, `:374`) |
| 3 | Cm3 | the test is in the right place and the file is gone by the time the load runs (`:286-290`) |

A static proof of that property needs path identity (CM1) and flow sensitivity (Cm3). Neither can be completed in an
AST reader; each fix adds a rule and the next round finds the program outside it. That is the class **[I]**, and all
three fixture forms are accepted as `optional` by the current reader **[M]** (set 2 below, last three rows).

### The population is one load **[M]**

`--closure` prints exactly one `optional: ` line. Its source:

```python
_cpc_path = SCRIPTS / "check-plan-code.py"
if _cpc_path.is_file():
    ...                                   # load check-plan-code.py, call _cpc.parse_fail_names(out)
else:
    print("  NOT RUN (no scripts/check-plan-code.py in this tree): the crash-guard case")
```

It was added in `64e4b67a` (PR #536). It loads a 621,548-byte file to call one pure two-line function,
`parse_fail_names` (`check-plan-code.py:3103`), in one self-test case.

### Three constructions, measured

| Construction | Result |
|---|---|
| A. Ship `check-plan-code.py` in `comprehensibility` | Rejected. Its reach through `exec_edges` is 4 files (`check-plan-code.py`, `coverage_verdict.py`, `fixture_git.py`, `sweep-red-alert.py`) **[M]**. It is the entry point of ANOTHER package (`ci-layer`), and the map allows only a `library` to be shared, so the map rule would need an exception to host it **[M, read from `components.json` and `load_map`]** |
| B. Move `parse_fail_names` into a shared library | Rejected. It edits the mutation harness itself, and the fixtures that copy only `check-plan-code.py` into a temp tree (`check-diff-coverage.py:513`, `:619`) would need the new sibling too **[I]** |
| C. Remove the load from `regen-pages.py`: pin the PRODUCER side of the contract | **Recommended.** Precedent in a shipped file: `brief-compose.py:1635` `_report_line` pins the `[FAIL]` line on the producer side without loading the consumer **[M]** |

### What construction C changes

In `regen-pages.py` the crash-guard case keeps `_raises`, drops the `_cpc` load and the `if/else`, and asserts on the
guard's own output: the first line of `out` equals `"  [FAIL] " + CRASH_CASE`, `": got "` does not occur in
`CRASH_CASE` (the one token `parse_fail_names` splits on), and `after case: the case before the crash` is present.
The case is renamed (it no longer says "that the harness's parse_fail_names reads"), so the three `expect` values in
`scripts/mutations/regen-pages.json` that quote the old name change in the same commit. A two-file edit.

### What deleting costs, and what it removes

- **Removes**: CM1 and Cm3 as a class, not as instances: with no proof there is nothing to fool. The `NOT RUN`
  branch too, which in a stranger's install was a self-test case that silently did not run **[M, the branch prints
  and adds no failure]**.
- **Removes from the checker**: `_tested`, `_guarded`, the `guards` parameter of `_visit` and `_node`, the
  `"optional"` kind in `paths` (`:441`, `:456`, `:477`, `:483`), the middle slot of `python_loads`' return, the
  `optional: ` entry of `NOTES` and its branch in `closure_edges`, the four XM3 cases (`:1647` to `:1671`), and 11
  of the manifest's 184 mutations (list under *Mutations*). `load_map`'s refusal of `optional_edges` (`:671`) STAYS,
  with its case and its mutation.
- **Costs**: `regen-pages.py`'s own suite no longer runs the real consumer over the guard's output. What still does:
  the mutation sweep runs `check-plan-code`'s real `parse_fail_names` over `regen-pages.py --self-test` output, and
  the three crash mutations go red only if that read works **[I — the sweep was not run here]**. A direct
  consumer-side case is FILED, not built.
- **Costs in principle**: a future genuinely optional sibling has no way to be declared. That is the intended
  position: it ships, or the code does not load it. A waiver is how round 2 began.

## 2. Can the reader fail CLOSED by construction? Yes, by census; not absolutely

### What is positively read today **[M, read from `_Loads`]**

| Thing | Positively read |
|---|---|
| Loader calls | `spec_from_file_location`, `SourceFileLoader`, `run_path` and the other `PATH_LOADERS`; `import_module`, `__import__` (`MODULE_LOADERS`), matched by the called NAME |
| Interpreter argv | a list or tuple literal whose first element is `sys.executable` or one of `python`, `python3`, `bash`, `sh`; flags skipped; the first non-flag element is the script |
| Path expressions | string constants, f-strings, `+`, `/`, `joinpath`, `os.path.join`, `Path(...)` wrappers, `with_name`, conditional expressions |
| Name bindings | `Assign`, `AnnAssign`, `NamedExpr` to a bare name; `for` over a literal; a parameter, through the wrapper fixpoint |
| Imports | `import x`, `from x import y` → `x.py` beside the file |

Everything else falls through. The defect is the fall-through's default: a binding the reader does not see is not
"unknown", it is ABSENT, so the name resolves to its other bindings or to a module name, and the load is dropped
or mis-attributed with no line printed. CM2's five inputs are five members of that set; section 3 has 20 more.

### The inversion

Four censuses. Each enumerates its population from the GRAMMAR, not from a list of handled forms, and each member
must end as an edge or an `unresolved: ` line.

1. **Binding census.** For every scope, every node field that binds a name is a binder. Derive it from the AST: every
   `Name` whose context is not `Load`, every import alias, and every `str`-valued field of every node except a fixed
   list of ten that do not bind (`Name.id`, `Attribute.attr`, `keyword.arg`, `Constant.value`, `Constant.kind`,
   `ImportFrom.module`, `alias.name`, `alias.asname`, `Global.names`, `Nonlocal.names`). A binder that is not one of
   the four positively read forms makes the name OPAQUE: it resolves to unknown. This covers tuple targets,
   `AugAssign`, `with … as`, `except … as`, `import … as`, `del`, `match` captures, `def` and `class` names, and
   whatever binder a later Python adds, because a new node's `str` field is a binder unless listed. Plus: a name in
   any `global` or `nonlocal` statement is unknown everywhere; a `from x import *` makes every module-level name
   unknown; a self-reference is unknown (today `_name` returns the EMPTY set at `:379`, which is the drop); a class
   body is a scope functions do not see; `*args` and `**kwargs` are parameters.
2. **Loader census.** Every mention of a loader name (a `Name`, an `Attribute`, a string constant equal to one, a
   `from … import loader as other`) that no positive rule consumed is listed. A loader call whose argument cannot be
   placed (omitted, behind a `*` splat) is listed. This covers an alias, a loader kept in a dict, `functools.partial`,
   `getattr(runpy, "run_path")`.
3. **Interpreter census.** Every `.executable` attribute and every string constant equal to an interpreter word that is
   not the consumed head of an argv literal is listed. An argv with an interpreter head and no script, `-c` or `-m`
   is listed. This covers an interpreter held in a name, `shutil.which("python3")`, an argv built by `.append`.
   Add the same for the shell: `os.system`, `os.popen`, a call with `shell=` not literally `False`, builtin `exec`
   and `eval`.
4. **Outcome census.** A positively read path that is absolute, climbs out of the tree, or names a file that exists
   at neither candidate location is listed (today: dropped by the filter at `:483` and by `exec_edges`). A wrapper
   that no call in the file binds, or that is handed on by name, is listed. A relative import, a dotted or relative
   `import_module`, and an import whose name is a sibling DIRECTORY are listed.

### What becomes `unresolved: ` that was silent **[M]**

Measured on the 23 shipped `.py` files of `shipping-sets.json` with the prototype, existence asked of the repo:

| | Before | After |
|---|---|---|
| `--closure` `unresolved: ` lines, total | 28 | 60 |
| `comprehensibility` | 6 | 36 |
| `recall` | 22 | 24 |
| `optional: ` lines | 1 | 0 (the note is gone; the load is gone) |
| Edges read from shipped files | 21 + 4 | 21 + 4 (lost 0, gained 0) |
| `--closure` gaps | 0 | 0 **[I]** — edges unchanged, and `check-plan-code.py` stops being loaded |
| `--map` gaps | 0 | 0 — over all 115 tracked `.py`, edges lost 0, gained 0 **[M]** |
| `--map` `unresolved: ` lines | 0 (the map prints none) | 0 (unchanged; listing stays a closure note) |
| Repo-wide `unresolved` returned by the reader, 115 files | 67 | 187 |

The shell census (item 3's last sentence) was counted separately, not prototyped: 3 more lines
(`fixture_git.py:330`, `:333`, `goal-tree.py:216`), so at most 63 **[M for the 3; the sum is I]**.

The 32 new lines, every one opened **[M]**:

- **27 name a file that does not exist in the tree.** All are self-test fixtures loading a file the case itself
  writes to a temp directory: `goal-tree.py` `_sibling("sib-…")` 13 times and `:4980` (a shim written three lines
  above); `regen-pages.py` `launch("g.py" …)` 9 times and `:1936`; `explainer-serve.py:4731`, `:4755`;
  `check-surface-recall.py:519` (`does-not-exist.sh`, a negative case).
- **5 are census lines**: `ask_answerer.py:1379` (`sys.executable` inside a shebang f-string written to a fixture);
  `gen-dashboard.py:3352` (`argv[0] == sys.executable`, a comparison); `regen-pages.py:709`, `:755` (`run=launch`,
  the wrapper as a default argument); `check-surface-recall.py:799` (`render.__defaults__`).

**None hides a shipped dependency [M by reading each line; I that the reading is complete].** `goal-tree.py`'s real
siblings (`session-state`, `gen-dashboard`, `gen-backlog-page`, `gen-work-lines`, `brief-compose`) are read as edges
before and after.

## 3. Refutation

Two sets of small programs, each loading `secret.py` by one form. "Dropped" means neither an edge to `secret.py`
nor an `unresolved: ` line: the closure would print `0 gaps` and nothing else.

**Set 1, 30 inputs, against the current reader and the prototype [M]:**

| Input | Current | Prototype |
|---|---|---|
| CM2's five (self-reference, `+=`, `global`, tuple target, `except … as`) | dropped ×5 | listed ×5 |
| class-body name shadowing a module-level one | dropped | edge |
| `*args` name, loader alias, `from runpy import run_path as rp`, `getattr(runpy, "run_path")` | dropped ×4 | listed ×4 |
| argv `.append`, interpreter held in a name | dropped ×2 | listed ×2 |
| `with … as`, `import … as`, `for` over a non-literal, `match` capture, `nonlocal`, lambda default | dropped ×6 | listed ×6 |
| star import (two forms) | dropped ×2 | listed ×2 |
| `spec_from_file_location("name")` with the location omitted | dropped | listed |
| a concrete path that does not exist, unreadable base with a missing file, absolute path, upward escape | dropped ×4 | listed ×4 |
| `**kw` shadow, argv built by `+`, walrus in a comprehension, two controls | listed or edge ×5 | same ×5 |
| **Dropped** | **25 of 30** | **0 of 30** |

**Set 2, 24 inputs written AFTER the prototype passed set 1, to break it [M]:**

| Input | Current | Prototype |
|---|---|---|
| guarded load with the file absent; CM1's guard on another path; Cm3's `os.remove` between test and load | `optional` ×3 (0 gaps) | edge ×3 (a gap when unshipped) |
| loader in a dict, `functools.partial`, `with_name`, wrapper never called, parameter rebound by `+=` | dropped ×5 | listed ×5 |
| sibling package import, relative import, dotted and relative `import_module` | dropped ×4 | listed ×4 |
| `B = "bash"` in an argv, `shutil.which("python3")` in an argv | dropped ×2 | listed ×2 |
| wrapper as a `map` callback, wrapper via `**kw`, same-named method, `os.execv` | edge ×4 | edge ×4 |
| `os.system("python3 secret.py")`, `subprocess.run("bash secret.sh", shell=True)`, `exec(open(…).read())` | dropped ×3 | dropped ×3 → listed by the shell census **[I, not prototyped]** |
| `globals()["p"] = "secret.py"`, `getattr(runpy, "run_" + "path")`, `cmd[1] = "secret.py"` after the literal | dropped ×3 | **dropped ×3 — the residual** |
| **Dropped or wrongly `optional`** | **20 of 24** | **6 of 24, 3 after the shell census** |

So the honest answer to "fail closed by construction" is: closed over every form that MENTIONS a loader, an
interpreter or a binder in syntax. Three forms mention none of them in a way a census can count, and they are the
bounds of section 4. I could not make them structural at a tolerable price: `globals()` occurs in 14 of the 23
shipped files **[M]**, so "reflection makes every name unknown" would list nearly every load in the tree.

**The patch route, for comparison [I from the two tables]:** the round-3 fix list (compare bases in `_guarded`, read
`AugAssign`, read `global`, read tuple targets and `except … as`) closes 5 of set 1's 25 and none of set 2's 20
except by further additions. Each is a form added to a list whose complement is silent.

**A refutation that partly landed: the channel.** `unresolved: ` is "listed, not checked, not a gap". Sixty lines
nobody is obliged to read is a weak channel (`a gate's channel can be weaker than the gate`), and failing closed
moves real risk INTO that list. The redesign makes the list complete; it does not make it read. Hence the first
follow-up below. This is the redesign's known weakness and round 4 is right to say so.

## 4. What stays a stated bound

To be written in the module docstring, replacing the false "never dropped" at `:40` and `:163`:

1. **Reflection**: a name rebound through `globals()[…]`, `setattr`, `vars()`, or `exec` of a string.
2. **A loader reached by a computed name**: `getattr(runpy, "run_" + "path")`.
3. **An argv mutated after it is written**: `cmd[1] = …`, `cmd.insert`. No shipped file binds an argv literal to a
   name today **[M]**, so this costs nothing now.
4. **A callee in another module**: the wrapper fixpoint is per file.
5. **Base drop**: an unreadable base of `/` is dropped and the remainder tried beside the file and at the root. A
   real target at a third location, with a same-named file at one of those two, is a false edge and a missed one.
   31 load lines in shipped files have a dropped base **[M]**; listing all of them adds 26 lines of noise, so it is
   not recommended. Follow-up: read `__file__`, `.parent` and `dirname` positively.
6. **Flow**: a name's value is the union of all its readable bindings: a superset, never a subset.

## 5. The stop condition

The thrash had two engines: a proof that needed a new rule per program (`optional-edges`), and a default that
turned "not recognised" into "absent" (`edge-reader`). Deleting the first and inverting the second removes both.
What could thrash next is the census's own exclusion list (the ten non-binding fields) and the residual of section
4. If round 4 or later finds a SYNTACTIC form (one that names a loader, an interpreter or a binder) that is neither
an edge nor listed, the census is wrong and this review's premise failed: stop and re-open, do not add the form.

## Build brief

### The rule, in one paragraph

A file's loads are read by `python_loads(rel, text) -> (edges, unresolved)`. An edge is a load every part of which a
positive rule read. Every other mention of a loader name, an interpreter word or the shell, every load through a
name with a binder the reader does not read, and every read path with no existing candidate, is an `unresolved`
line. No load is optional. `--closure` treats an edge the package lacks as a gap whether or not the code tests for
the file first.

### Functions

| Function | Change |
|---|---|
| `_Loads._tested`, `_Loads._guarded` | DELETE |
| `_Loads._visit`, `_node` | drop the `guards` parameter; a `ClassDef` becomes a scope whose names functions inside do not see |
| `_Loads._assigned` | REPLACE with `_bindings(body) -> (env, opaque)`: the four read forms fill `env`; the binding census fills `opaque` |
| `_Loads._params` | include `vararg` and `kwarg` |
| `_Loads._name` | a name in any `global` / `nonlocal` → unknown; a cycle → unknown (not the empty set); an opaque name adds unknown to its readable values; a star import makes module-level names unknown |
| `_Loads._add` | an EMPTY form set is unresolved; drop the `"optional"` kind |
| `_Loads.paths` | record every consumed loader and interpreter node; a loader call with no placeable argument is unresolved; an interpreter argv with no script, `-c` or `-m` is unresolved; after the fixpoint run the loader, interpreter, shell and wrapper censuses; return each path load's candidates GROUPED by line so existence can be asked per load |
| `python_loads` | return `(edges, unresolved)`; add relative imports and dotted or relative module loads to unresolved |
| `exec_edges`, `closure_edges` | a path load none of whose candidates exists in the tree being read is unresolved (asked here, where the tree is known); delete the `optional: ` branch; a sibling-directory import is unresolved |
| `NOTES` | drop `"optional: "` |
| `load_map` | unchanged: `optional_edges` stays REFUSED |
| `regen-pages.py`, crash-guard case | construction C of section 1, with `scripts/mutations/regen-pages.json`'s three `expect` values |

`exec_edges` must keep returning the same edges for the same tree: the 115-file measurement (lost 0, gained 0) is
the acceptance check, re-run by the builder.

### Red cases to write first

Each loops over a LITERAL list written in the case, independent of the reader's own tables, and each has a control.

| Case | Fails when |
|---|---|
| a load under an existence guard is a plain edge, and a gap when the package omits it (the three guard programs of set 2) | any of the three prints `0 gaps`, or the word `optional` appears in the output |
| every binder form the reader does not read makes the name unresolved (set 1's binder inputs, one sub-result each) | any one returns no `unresolved` line and no edge to `secret.py` |
| control: the four READ binder forms still give the edge and no unresolved line | an over-eager census lists a plain `p = "secret.py"` |
| every loader mention that is not a read call is unresolved (alias, import-as, `getattr`, dict, `partial`, omitted argument) | any one returns an empty `unresolved` |
| every interpreter or shell mention that is not a read argv head is unresolved (name-held, `which`, `.append`, `os.system`, `shell=True`, `exec`) | any one returns an empty `unresolved` |
| control: `[sys.executable, "secret.py"]` is an edge and adds no unresolved line | the census counts a consumed head |
| a read path with no existing candidate is unresolved: missing file, absolute, upward, unreadable base with a missing file | `--closure` prints no `unresolved: ` line for it |
| control: the same path with the file present is an edge and not listed | existence is not consulted |
| a wrapper never called, and a wrapper handed on by name, are unresolved | the load line is absent from `unresolved` |
| a relative import, a dotted `import_module`, a sibling-directory import are unresolved | any one is silent |
| the live tree: the reader's edges over every tracked `.py` equal a pinned count, and `--closure` has no `optional: ` line | an edge is lost or gained by the rewrite |
| `regen-pages.py`: the crash guard's first line is exactly `  [FAIL] <CRASH_CASE>` and `CRASH_CASE` has no `": got "` | the guard prints another shape, or the case does not run (there is no `NOT RUN` branch left) |

### Mutations

RETIRE with the code they anchor (11 of 184, named as in the manifest): *a guarded load is not said*, *the else
branch is guarded too*, *the if body is not guarded*, *a function under a guard inherits it*, *a lambda under a
guard inherits it*, *a conjunct of an and guards nothing*, *os.path.exists guards nothing*, *any guard guards
every load*, *a name bound twice is guarded*, *a guarded load is a plain edge*, *a guarded load the tree carries is
not followed*. KEEP *optional_edges is still accepted* and *an unresolved load is a gap*.

ADD, each killed by the case named:

| Mutation | Killed by |
|---|---|
| the opaque set is never consulted in `_name` | the binder case |
| one entry added to the non-binder list (`ExceptHandler.name`) | the binder case, `except … as` sub-result |
| a cycle returns the empty set again | the binder case, self-reference sub-result |
| `global` / `nonlocal` names are not unknown | the binder case |
| the loader census is skipped | the loader case |
| the interpreter census is skipped | the interpreter case |
| a consumed head is not recorded | the argv control |
| an empty form set is not unresolved | the loader case, omitted-argument sub-result |
| the existence check always answers yes | the missing-file case |
| the existence check always answers no | the present-file control |
| the uncalled-wrapper census is skipped | the wrapper case |
| a guarded load is skipped as before (re-introduce any `if` test exemption) | the guard case |

### Filed, not built

1. **A per-file `unresolved` count in the declaration**, derived, so that a NEW unresolved line in a shipped file makes
   the declaration stale and therefore red. It turns the list from printed into gated. Needs its own slice.
2. **A consumer-side witness** that `check-plan-code.parse_fail_names` reads `regen-pages.py`'s crash line, placed in
   the harness's own suite.
3. **Path algebra for `__file__`, `.parent`, `dirname`**, which removes bound 5 and resolves the self re-exec lines already listed today **[I]**.

## Prediction for round 4

Written before round 4 runs. If the redesign is right, round 4 will NOT find:

1. any finding in an existence-guard proof, because none exists;
2. any program in which a loader name, an interpreter word, a shell call or a name binder appears in SYNTAX and the
   load is neither an edge nor an `unresolved: ` line;
3. any change in the edges read from the live tree, or a `--map` or `--closure` gap.

Round 4 MAY restate the six bounds of section 4, and MAY say the `unresolved` list is long and unread (the filed
follow-up). A finding of kind 1 or 2 falsifies this review.

## What we decided on this branch that is not written down

- **No load is optional.** A sibling a shipped file loads is shipped, or the load is removed. There is no waiver in
  the map and no proof in the reader. This deserves a sentence in the script's docstring and, if the marketplace
  work gets an ADR of its own, a line there.
- **`unresolved` means "a human must read this line", and nothing yet obliges one to.**
- **A self-test case that cannot run in an installed tree is a failure of the case**, not a `NOT RUN` print.

## Bound of this review

- The prototype is 321 lines replacing `_Loads` and `python_loads` only; `exec_edges` and `closure_edges` were driven
  through a harness, not rewritten. The closure counts after the change are the reader's output over the shipped
  files, not the CLI's.
- The shell census, the `regen-pages.py` edit and the manifest edits were specified, not built. No mutation sweep was
  run.
- "None hides a shipped dependency" rests on reading 32 lines by eye.
- Two fixture sets, 54 inputs, written by the reviewer who wrote the prototype: an independent reviewer's inputs are
  what round 4 is for.
