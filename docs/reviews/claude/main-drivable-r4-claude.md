# Round 4 — Claude half — `scripts/check-main-drivable.py` (branch `d2-main-drivable`, PR #365)

**Subject, pinned.** `scripts/check-main-drivable.py` at
`sha256 1202c2f6c88ead774a482df7c0a0026fd93806f7cca9f52a5c2a1aa74e6979d7`, 2624 lines, suite
`210/210`. Manifest `scripts/mutations/check-main-drivable.json` at
`sha256 ea7bc1b481e9759df4f69c52f89dc9e74ee8811be66819a37bdfb3748afe2a90`, 77 entries. That script
hash is now `HEAD` (`06b009dc`, *"Round 4 on the rewrite: the falsifier held…"*) and the working
tree; every line number below is derived against it.

⚠ **THE SUBJECT MOVED UNDER ME AND ONE OF MY VERDICTS WAS STALE BECAUSE OF IT.** At my first read
the file was 2597 lines and the suite reported `207/207`; by my second it was 2624 and `210/210`,
and the manifest's hash changed again later. My first partial sweep reported **3 problems** and my
first independent mutation pass reported **1**; all four were artefacts of reading a tree the
coordinator was mid-edit on. Everything in this document was re-derived at the pinned hashes above,
and the stale verdicts are recorded as stale rather than dropped — §Checks.

---

## What I executed vs only read

**Executed.**

- `--self-test` (`210/210`) and `--report` (44 guards · 7 without `main()` · 37 in population ·
  10 compliant · 27 pinned), from the repo and from a disposable copy.
- A 21-case leaf-provenance probe over synthetic guards (lambda defaults, comprehension
  generators/`ifs`, `nonlocal`, PEP 634 `MatchStar`/`MatchMapping`, `except … as`, in-place dict
  mutation, `functools.partial`, decorator and nested-def default evaluation, `**kwargs`).
- A **20 wrapper × 6 world = 120-cell matrix**, the architecture review's own instrument, widened.
- **27 severances**, one rule at a time, each in a disposable repo (`<tmp>/repo/scripts/` with the
  other 43 guards symlinked so `ROOT` still enumerates the real population), control proved green
  first (`210/210`, 0 `[FAIL]`).
- **All 77 manifest mutations** applied and run independently of `check-plan-code.py`, asserting
  each produced a `[FAIL]` line carrying its own `expect` string.
- `partial-sweep.py scripts/check-main-drivable.py` — **twice**, 12.3 min and 13.1 min.
- A **call-site census**: every credited call site of all 10 compliant guards, and every `main` call
  of all 27 pinned ones, printed with its route and `ast.unparse`.
- **Line coverage** of the rule region by its own suite, via `sys.settrace`.
- **Re-derivation of the "21 of 21"** claim against the pre-rewrite code (`fc91505c`), by
  instrumenting the old bare `return True` and counting at recursion depth 0.
- A **1,850-file fuzz**: `classify` over the whole Python 3.14 stdlib, plus the repo's own 71
  `.py` files, plus 9 adversarial synthetic guards.
- Count reconciliation: `EXPECTED_MUTATIONS` sum (1255) against manifest entries on disk (1255).

**Only read.** ADR-0014; `docs/reviews/architecture-review-2026-10-03.md`;
`docs/reviews/codex/main-drivable-r4-codex.md`; `git show 534c761c`. I did not re-derive the
architecture review's dynamic-instrument figures (87s, 7 compliant), which it already labels as not
re-derived.

---

## Findings

### Blocking — the child walk at `:1069` is a node-kind list, and two grammar categories are missing from it. This is the pre-committed falsifier.

**The observation that would make it FAIL:** a world argument whose only live leaf sits in a child
that is not an `ast.expr` is credited as BUILT. Two such categories exist: `ast.arguments` (a
lambda's `defaults` / `kw_defaults`) and `ast.comprehension` (a comprehension's `iter` and `ifs`).

```
scripts/check-main-drivable.py:1069
    children = [c for c in ast.iter_child_nodes(expr) if isinstance(c, ast.expr)]
scripts/check-main-drivable.py:1070
    children += [k.value for k in getattr(expr, "keywords", []) or []]
scripts/check-main-drivable.py:1083
    if isinstance(expr, ast.Call):
        return BUILT
```

Line 1070 is the fix the commit message cites as proof the falsifier cannot be landed — *"`ast.keyword`
is not an `ast.expr`, so the child walk skipped keyword arguments … Fixed by traversing a category
the grammar already defines."* **`ast.arguments` and `ast.comprehension` are two more categories the
grammar already defines, and neither is traversed.** A `Call` whose live leaf hides in one of them
reaches `:1083` with all-INERT children and returns BUILT.

Measured, `main([], root=<expr>)` against `ROOT = Path('/real/repo')`:

| world expression | runtime passes | verdict | |
|---|---|---|---|
| `(lambda: ROOT)()` | the live repo | `DEBT` | correct — `body` **is** an `ast.expr` |
| `(lambda z=ROOT: z)()` | the live repo | **`param`** | ⛔ false credit |
| `(lambda *, z=ROOT: z)()` | the live repo | **`param`** | ⛔ false credit |
| `next(z for z in [ROOT])` | the live repo | **`param`** | ⛔ false credit |
| `list(z for z in [ROOT])[0]` | the live repo | **`param`** | ⛔ false credit |
| `next(z for z in ['a'] if ROOT)` | the live repo | **`param`** | ⛔ false credit |
| `sorted([ROOT])[0]` | the live repo | `DEBT` | correct — control |
| `[z for z in [tempfile.mkdtemp()]][0]` | a built world | `DEBT` | ⛔ false refusal, same hole |

The `(lambda: W)()` / `(lambda z=W: z)()` pair is the clincher: identical semantics, opposite
verdicts, and the only difference is which *slot of the grammar* the world sits in.

**The matrix the architecture review used to condemn the old rule, re-run over an adjacent wrapper
set.** The commit claims `wrapper rows that ignore the world  15/15 -> 0/15` and `90-cell matrix,
cells wrong  45 -> 0`:

```
20 wrappers × 6 worlds (3 live: ROOT, os.getcwd(), __file__ · 3 built: tempfile.mkdtemp(), td, Path(td))
  cells wrong ............................. 15 of 120   (12 false credits over the live world, 3 false refusals)
  rows whose verdict IGNORES the world ...... 5 of 20
```

The five constant rows are `(lambda z=W: z)()`, `next(z for z in [W])`,
`list(z for z in [W])[0]`, `next(z for z in ['a'] if W)` and `[z for z in [W]][0]` — i.e. **every
one of them is one of the two missing categories, and nothing else is wrong.** `0/15` is true of
the review's fifteen wrappers and is not a property of the rule.

So the load-bearing sentence of the rewrite — *"There is no node list left to extend."* — is false.
There is exactly one list, at `:1069`, and it is two entries short. The defect is worse than a
plain hole because the claim of structural completeness is what ends the search: round 1 → 2 → 3
each closed the spellings the previous round named, the architecture review correctly diagnosed
*dispatching on the top node* as the cause, and the rewrite then reintroduced the same shape one
level down — dispatching on **which grammar slot a child occupies** instead of on which node kind
the parent is.

**Fix (a hypothesis).** Replace the slot test with the traversal `ast.iter_child_nodes` already
gives you, rather than enumerating three categories:

```python
children = [n for c in ast.iter_child_nodes(expr)
              for n in ([c] if isinstance(c, ast.expr) else _exprs_under(c))]
```

where `_exprs_under(non_expr_child)` yields the `ast.expr` nodes beneath any non-`expr` child
(`ast.keyword`, `ast.arguments`, `ast.comprehension`, and whatever a future grammar adds) without
descending through an `ast.expr` boundary — so the recursion stays one level, as now. That removes
the list instead of extending it, which is the only fix that does not re-arm this finding. ⚠ It
widens `[z for z in [tempfile.mkdtemp()]][0]` to BUILT, which is the correct direction, and it
must **not** also pick up a nested `Lambda`'s `body` (already an `ast.expr` child and already
handled) or you double-count.

---

### High — the suite-reachability floor is applied at one site and is unfalsifiable at the second. Round 1's Blocking, half one, is live again at `_constructed_at_call_sites`.

**The observation that would make it FAIL:** a `main` call in a *reachable* helper, whose world is
that helper's parameter, earns the PARAM route from a call site in a function **nothing invokes** —
while every reachable call site passes the live world.

```
scripts/check-main-drivable.py:1144-1146
        if not (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name in reachable):
            continue
```

Severing `and node.name in reachable` (`:1145`) → `and True` leaves the suite at **`210/210`, zero `[FAIL]`**.
It is not covered by any of the 77 mutations either: the manifest's reachability entry
(*"⭐ ROUND 1 BLOCKING, HALF ONE. The suite-reachability rule is dropped…"*) anchors on
`suite_main_calls`, a different call of `suite_reachable`.

Proved live, not merely uncovered:

```python
def _drive(p):          return main([], root=p)
def _never_called():    return _drive(tempfile.mkdtemp())   # nothing calls this
def _self_test():       _drive(ROOT)                         # the only reachable call
```

| | verdict |
|---|---|
| with the filter | `DEBT` — correct: every reachable call passes the live `ROOT` |
| filter severed | **`param`** — round 1's Blocking, at a second site |

Over the 44 guards on disk the severance changes **0 verdicts**, so this is a floor rather than a
current false green — the same standing as the rules round 1 added. That is precisely why it needs
a case: an unfalsifiable floor is a floor that decays silently, and this repo's own
`after-fixing-search-for-the-class` lesson says the second site of a fix is where the class lives.

**Fix (a hypothesis).** A case over the fixture above asserting `DEBT`, plus a manifest entry
anchored on `:1145` naming it. No code change — the code is right; only its falsifier is missing.

---

### High — `_own_scope` prunes a nested scope that CAN write the enclosing one, so a `nonlocal` rebind to the live world is credited as built.

**The observation that would make it FAIL:** a case that builds a world, lets a nested function
rebind that name to the live repository via `nonlocal`, and then drives `main` over it, is credited.

```
scripts/check-main-drivable.py:904-906
        if not first and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                           ast.Lambda, ast.ClassDef)):
            continue
```

```python
def _self_test():
    p = tempfile.mkdtemp()
    def inner():
        nonlocal p
        p = ROOT            # the live repository
    inner()
    main([], root=p)        # runtime passes ROOT
```

→ **`param`**. Measured. The rewrite's own docstring at `:895` states the premise it violates:
*"A name bound inside a nested `def` is not bound in the enclosing one"* — true of a plain binding,
**false of one declared `nonlocal` or `global`**, which is the entire purpose of those statements.
The pruning is correct for the case round 4's Blocking half one was about (`p = ROOT` then
`def inner(): p = tempfile.mkdtemp()` → correctly `DEBT`, verified) and wrong for its mirror.

⚠ This one does **not** land the falsifier: the fix is to read a declaration, not to extend a node
list. I separate it deliberately.

**Fix (a hypothesis).** In `_own_scope`, before pruning a nested `FunctionDef`/`AsyncFunctionDef`,
descend into it anyway if any `ast.Nonlocal`/`ast.Global` in its own scope names a target it assigns
— or, narrower and cheaper, have `_bound_values(name, fn)` additionally collect bindings from nested
scopes that declare `nonlocal name` / `global name`. Either way LIVE still dominates, so the result
is `DEBT`.

---

### Medium — `computed_argv`'s precondition has no case that observes a verdict, and removing it truncates the suite at case 37 of 210 with ZERO `[FAIL]` lines.

**The observation that would make it FAIL:** a non-`List`/`Tuple` argv expression reaching
`expr.elts`.

```
scripts/check-main-drivable.py:1114-1116
    if not isinstance(expr, (ast.List, ast.Tuple)):
        return False
    return any(_element_is_constructed(el, fn, tree, 0, world) for el in expr.elts)
```

Severed (the two lines deleted), the suite does not report — it **dies**:

```
rc=1 | [FAIL] lines: 0 | [ok] lines: 36
last [ok] before death: ...and neither does main(['--self-test']) — the live false pass this rule exists for
AttributeError: 'Name' object has no attribute 'elts'   @ computed_argv:1116
```

All five `computed_argv` cases in the suite pass an `ast.List` (`_gg`, `_lit`, `_built`,
`ast.parse("[p]")`); none passes anything else. The manifest's nearest entry (*"a TUPLE argv stops
being read"*) narrows the tuple half and leaves the precondition itself unmutated. So the clause's
only falsifier is a crash — and the crash is **invisible to the harness's report format**, which
joins on `[FAIL] <case name>`: 36 cases print `[ok]`, 174 never run, and nothing says so. This is
the same class as round 4's own High (*"a crash where a verdict belongs"*), one function away, and
the class search after that fix did not reach it.

**Fix (a hypothesis).** `case("computed_argv refuses a non-list argv", computed_argv(ast.parse("x").body[0].value, None), False)`
plus a manifest entry anchored on `:1114`. Separately, this is evidence for making
`check-plan-code.py` treat *red with zero `[FAIL]` lines* as a distinct outcome from *red via the
named case* — it already prints that wording, so the distinction exists in the message and not in
the contract.

---

### Medium — the mutation join key contains two counts that are already wrong, so every correction to them silently unbinds the mutation. It did, during this review.

```
scripts/check-main-drivable.py  (the case name, and the manifest's `expect`)
  "⛔ the subprocess EXTRA-ARGV path returns a verdict instead of raising (r4 High) —
   207 cases and 71 mutations all passed over a line that crashed"
```

Re-derived at the pinned hashes: the suite is **210** cases and the manifest holds **77** entries.
Both embedded numbers are stale. They matter because the case name **is** the join key: the manifest
stores it verbatim in `expect`, and the harness decides *killed via its own case* by substring. I
watched this break and be repaired inside one session — my first independent pass and `partial-sweep`
run #2 both reported this entry as `KILLED BUT NOT BY ITS CASE` with `expect` reading `199 cases`
against a file saying `207`; the manifest hash then changed (`b0aea5cb` → `ea7bc1b4`) and it bound
again. The next count correction re-breaks it, and the failure mode is a mutation that looks like a
survivor.

**Fix (a hypothesis).** Strip the counts from the case *name* and put the retrospective figure in a
comment above it, where nothing joins on it. Derived numbers do not belong in an identifier; this
repo has `a-retrospective-number-needs-provenance` and `a-document-inside-the-corpus-it-measures`
for exactly this, and the join-key property makes it mechanical rather than cosmetic.

---

### Low — four rules are redundant with a neighbour, two of them in a function with zero callers.

Each severed alone leaves `210/210`:

| | rule | why it is unfalsifiable |
|---|---|---|
| `:1022-1023` | `if isinstance(expr, ast.Constant): return INERT` | strictly subsumed by `:1029`, *no `Name` and no `Attribute` anywhere* — a `Constant` has no children. No manifest entry. |
| `:1020-1021` | `if isinstance(expr, ast.Starred): expr = expr.value` | a `Starred`'s `value` **is** an `ast.expr`, so the generic walk at `:1069` already reaches it |
| `:961-964` | the whole of `_last_assigned_value` | **zero callers** — `grep` finds one hit, its own `def`. Not in the manifest. |
| `:1056-1057` | `if expr.id in LIVE_WORLD_READERS: return LIVE` (the **bare-name** reader) | see the §Unreached-branch answer below |
| `:935-937` | `_bound_values`' `AnnAssign`/`AugAssign` branch | no case binds a world with `p: Path = …` or `p += …`; behaviour verified correct by probe |
| `:938-940` | `_bound_values`' walrus (`NamedExpr`) branch | no case binds a world with `:=` |
| `:839-840` | the subproc extra-argv `("__file__", "sys")` exclusion | no case drives an extra-argv element naming either |

`_last_assigned_value` is the one worth more than a line. The rewrite **deliberately deleted** the
last-binding-wins rule — `:1045-1051` argues it at length, because reading only the last binding
was round 4's Blocking half two. The function that implements that deleted rule is still in the
file, correct, documented (*"The value of the LAST binding"*), and one import away from
reintroducing the Blocking. Gutting its body to `raise AssertionError` changes nothing. It is a
second implementation of a rule the file argues against — the `a-second-implementation-of-one-rule-drifts`
shape, pre-drift.

---

### Low — the `rebind` route credits a case for substituting the suite's own entry point.

`world_names` excludes suite functions from its *traversal* (`:233`, round 2's Claude Low) but
`_self_test` is itself a module global that `main` reads, via the dispatch, so it lands in the world
set. Measured credits:

```
scripts/check-rc-contract.py       L781,L782  REBIND['_self_test']   main(['--self-test']) / main(['--nope'])
scripts/check-surface-recall.py    L721,L722  REBIND['_self_test']
scripts/check-ratchet-contract.py  L980       REBIND['self_test']
```

`check-rc-contract.py:779-780` is `globals()["_self_test"] = lambda: 99` — a deliberate stub so
`main(["--self-test"])` does not recurse. It is a real global substitution, so it satisfies the
letter of the rebind route; it is not a *world*, and crediting it is not evidence `main` can be
driven over a constructed repository. **Not a false green today:** all three guards also comply
through a genuine route (`check-rc-contract.py:747` rebinds `HOOK, MATCHER, ROOT`;
`check-surface-recall.py:655/682/705` rebind `DECLARED_RENDER`; `check-ratchet-contract.py:941/965`
take PARAM), verified by the call-site census. Filed because it is a route that will carry a guard
on its own as soon as one is written that way.

**Fix (a hypothesis).** Subtract `suite_entries(tree)` from `world_names`' result, not just from its
traversal frontier.

---

## The falsifier

**⛔ LANDED, twice over, and the commit that asserts it held is `06b009dc`.** The pre-committed
falsifier was *"any defect in it whose fix is 'add a node kind to a list inside it.'"*

There is exactly one node-kind list left in the rewrite — `:1069`,
`[c for c in ast.iter_child_nodes(expr) if isinstance(c, ast.expr)]` — and it is **two grammar
categories short**: `ast.arguments` (lambda defaults) and `ast.comprehension` (a comprehension's
`iter` and `ifs`). The minimal fix for each of the five broken wrapper rows is literally to add that
kind to that list, which is why I am calling it landed rather than arguing about it; the better fix
(§Blocking) removes the list instead, and that is the same move the commit made twice and stopped
one short of. The commit's own evidence convicts it: it cites `ast.keyword` as a category it added
to this very list, calls that "traversing a category the grammar already defines", and then concludes
*"There is no node list left to extend."* Two categories the grammar already defines were never
traversed.

Three independent instruments agree, and the first two are the review's own:

1. The 20×6 matrix: **5 of 20 wrapper rows give the same verdict for all six worlds** and **15 of
   120 cells are wrong** — against a claimed `0/15` and `0 of 90`. All five rows are in the two
   missing categories; nothing else in twenty wrappers is wrong.
2. The semantic pair `(lambda: ROOT)()` → `DEBT` vs `(lambda z=ROOT: z)()` → `param`. Same
   expression, same world, opposite verdict, the only difference being a grammar slot.
3. The hole is directional in both directions — `next(z for z in [ROOT])` is a false **credit** over
   the live world, `[z for z in [mkdtemp()]][0]` a false **refusal** of a built one — which is the
   signature of a traversal gap rather than a tuned threshold.

A second finding (§High, `nonlocal`) is a defect in the rewrite but **does not** land the
falsifier, and I say so rather than counting it: its fix reads a scope declaration, not a node list.

---

## The unreached branch (question 8)

A branch no case reaches, where a mutation would therefore prove nothing — the same shape as the
`NameError` that survived 199 cases and 71 mutations. `sys.settrace` line coverage of the rule
region (every statement line below the `─ THE SUITE ─` banner excluded) gives **two**, and the
severance confirms each:

1. **`:1056-1057` — the bare-`Name` live-world reader.**
   ```python
   if expr.id in LIVE_WORLD_READERS:
       return LIVE
   ```
   Never executed by any of the 210 cases; no manifest entry anchors it (the one that reads
   *"the live-world READERS list stops being consulted, so `os.getcwd()` reads as a world the case
   built"* anchors the **`Attribute`** branch at `:1060-1062`, a different consultation of the same
   set). Severed → `210/210` green. The branch is nevertheless **correct**: probed with
   `from os import getcwd` + `main([], root=getcwd())` it returns `DEBT`, and the adjacent negative
   `from os import listdir` + `listdir()` returns `param`. It protects nothing on disk today — no
   guard imports a `LIVE_WORLD_READERS` name as a bare name (checked all 44) — which is exactly why
   nothing would notice it being deleted or inverted.

2. **`:935-937` — `_bound_values`' `AnnAssign`/`AugAssign` branch.** Never executed; no manifest
   entry (the augmented-assignment entry anchors `module_globals`, a different function); severed →
   `210/210`. Also verified correct by probe: `p: str = tempfile.mkdtemp()` → `param`,
   `p = ROOT; p += 'x'` → `DEBT`.

Both are *Low* as defects and *the answer to the question* as evidence: the `NameError` was not a
one-off, and what makes a line like this invisible is not that it is obscure but that **the case
and the mutation are chosen from the same reading of the code**. The suite covers what the author
noticed; the manifest anchors what the suite covers. Nothing in the loop enumerates the branches.
A `settrace` run over the suite takes under two seconds and names them, and I would put that in
`check-ratchet-contract.py`'s contract before I would add these two cases by hand.

---

## What I tried to refute and could not

- **A false green among the 10 credited guards (question 2).** I printed every credited call site
  of all ten with its route and source. I found none. The weakest are the three
  `REBIND['_self_test']` credits (§Low), and all three guards comply through a genuine route as
  well, so no verdict on disk rests on them.
- **A compliant guard among the 27 pins (question 3).** None — and the reason is stronger than *the
  rule refuses them*: **all 27 have ZERO suite calls to `main()`**, and 18 of 27 declare no
  parameter but `argv` (9 declare nothing at all). No leaf-provenance rule, however generous, can
  move a pin, so the `compliance over 44 guards … IDENTICAL` claim was never at risk from the
  rewrite's added generosity. The four refused-BUILT shapes my probe found (`case [*q]`,
  `case {**q}`, `except … as e`, `d['root'] = …`) are lost credits in principle with **no instance
  on disk**; I am not filing them, because the §Blocking fix is the wrong place to bolt them on and
  a guard that wants one can be written in a shape the rule already reads.
- **A case that dies rather than reports, in shipped code (question 6).** `classify` survived
  **1,850 stdlib files** (68 with a top-level `main`), the repo's own 71 `.py` files, and 9
  adversarial guards (`main` as `async def`, decorated `main`, a `set` argv, `**kwargs`-only call,
  a forwarder whose `func` is an `ast.Attribute`, a starred subprocess argv, an 11-deep alias
  chain, a `p = q; q = p` cycle) — **zero exceptions**. The one death I found needs a line removed
  to reach (§Medium, `computed_argv`). `_line_of`'s bare `next()` at `:1361` (`return next(i for i, line in …)`) is the standing hazard
  — `StopIteration` kills the suite with no `[FAIL]` — but all six call sites' needles are fixture
  text, not text `_wired` inserts, so no mutation reaches it.
- **All 77 mutations bind and go red through the case each names (question 4).** Yes, at the pinned
  hashes, by two independent instruments — `partial-sweep.py` (13.1 min, after-control GREEN) and
  my own harness, which re-applies each edit and asserts the printed `[FAIL]` carries that entry's
  own `expect` string. Zero survivors, zero unbound anchors, zero killed-but-not-by-its-case.
- **The "21 of 21" claim (question 7).** Re-derived against `fc91505c` by instrumenting the old
  bare `return True` and counting at recursion depth 0: **21 outermost element-level credits, 21 of
  21 reaching that branch.** Exact. ⚠ My first pass said **25**, which was my instrument
  double-counting recursive inner `True`s (the bare branch is hit at depths 1–3 only, never 0) —
  recording that because a *disagreeing* number is the thing most likely to be believed. `0 of 25`
  would have been a false finding against a correct claim.
- **`EXPECTED_MUTATIONS`.** 58 entries summing to **1255**; manifest entries on disk **1255**;
  `check-main-drivable.py` declared **77**, on disk **77**. The commit's `1249` / `71` are its own
  snapshot, superseded by the fold. The suite's declared `# 210 cases` matches `210/210`. (I
  certified only this file's 77; the other 1178 need `--mutate .`.)

### Stale verdicts, recorded as stale

My first `partial-sweep` run (12.3 min) reported **NOT CLEAN — 3 problems**: the `_own_scope` and
`concatenation` mutations as SURVIVED, and the `EXTRA-ARGV` one as killed-without-a-`[FAIL]`-line.
All three were against a tree the coordinator was mid-edit on (2597 lines). Re-run at the pinned
hashes: the first two are killed via their own case; the third was a genuine `expect`-string drift
(`199` vs `207`) that the coordinator fixed in the manifest while I was running, and now binds. My
independent 77-entry pass straddled that manifest edit and reported the same one problem for the
same reason. **None of the three is a finding.** The coordinator's warning was right, and the
mechanism is worth keeping: a sweep pins nothing, so its verdict is only as good as the hash you
took it at — which is why this document leads with one.

---

## Checks

| Check | Result |
|---|---|
| `--self-test` | **210/210**, rc 0 |
| `--report` | 44 guards · 7 no `main()` · 37 in population · **10 compliant** · **27 pinned** (param 3, argv 3, rebind 8, subproc 1) |
| `partial-sweep.py` (run 1, stale tree) | NOT CLEAN — 3 problems · **all three stale**, see above |
| `partial-sweep.py` (run 2, pinned hashes) | 77/77 red via the named case · after-control GREEN · 13.1 min · 1 problem, since fixed by the coordinator |
| 77 mutations, independent harness | **77/77 bind; 77/77 red via their own `expect`** at manifest `ea7bc1b4` |
| Severances (27 attempted, 1 anchor miss) | **8 GREEN** — `Constant→INERT`, `Starred` unwrap, `_last_assigned_value`, bare-name reader, `AnnAssign`/`AugAssign`, walrus, `_constructed_at_call_sites` reachability, subproc argv exclusion |
| Severance control | `210/210`, 0 `[FAIL]`, in the disposable repo, before every run |
| 20 × 6 wrapper/world matrix | **15 of 120 cells wrong · 5 of 20 rows ignore the world** |
| Leaf-provenance probe, 21 shapes | 6 false credits over the live world · 4 false refusals of a built one |
| Rule-region line coverage | 2 branches no case reaches (`:1056-1057`, `:935-937`) |
| Fuzz: stdlib + repo + adversarial | 1,850 + 71 + 9 inputs · **0 exceptions** |
| "21 of 21" re-derived vs `fc91505c` | **21 of 21**, exact |
| `EXPECTED_MUTATIONS` vs disk | 1255 = 1255 · this file 77 = 77 |
| Credited call sites audited | 10 of 10 guards, every site · no false green |
| Pinned guards audited | 27 of 27 · **all have 0 suite calls to `main()`** |
| Working tree left as found | `git status --porcelain` = the two pre-existing untracked PDFs only; nothing committed, staged, pushed or reverted |

**NOT CONVERGED.**

The §Blocking is not a spelling and it is not the next instance in the round-1→2→3 series — it is
the *same structural mistake the architecture review diagnosed*, reintroduced one level down:
dispatching on which grammar slot a child occupies instead of on which node kind the parent is. The
rewrite is right that the subject is the leaves; it is still asking the grammar a closed question.
Fixing it by adding two entries to `:1069` would make round 5 the fourth consecutive round whose
findings come from the previous round's fix in one component — so the fix that converges this is
the one that **removes** the list, and the test for it is not a wrapper I enumerate but
`ast.iter_child_nodes` reaching every `ast.expr` beneath a non-`expr` child without being told
which kinds those are.
