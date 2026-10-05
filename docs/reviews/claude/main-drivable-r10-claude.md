# Round 10 — Claude adversarial review of `scripts/check-main-drivable.py`

**Subject:** `scripts/check-main-drivable.py` (ADR-0014 rule D2)
**Tree:** branch `d2-main-drivable`, frozen at `5101f82c`, working tree clean
**Delta reviewed:** `7794d825^..HEAD`, centred on the extraction in `449bfb82`
**Verdict:** **NOT CONVERGED**

---

## 1 · Verification — what I actually ran

Everything below was executed on this tree. Nothing in this review rests on reading alone
unless the line says so.

### The four mandatory runs

```
$ python3 scripts/check-main-drivable.py --self-test
404/404 passed                                               rc=0

$ python3 scripts/check-main-drivable.py
44 guards on disk · 7 without main() (outside the population) · 37 in population
  10 drive main() over a constructed world — param 3, argv 3, rebind 8, subproc 1
  27 pinned as ADR-0014 identity debt
D2 OK — every guard with a main() either drives it over a constructed world or is pinned.
                                                             rc=0

$ python3 scripts/check-main-drivable.py --report
(44 rows; 10 labelled by route, 27 DEBT, 7 "no main()")       rc=0

$ python3 -c "import json;print(len(json.load(open('scripts/mutations/check-main-drivable.json'))))"
163
```

### Numbers re-derived rather than trusted

| Brief said | I measured | Verdict |
|---|---|---|
| "~404 cases" | **404/404**, and **404 unique case names** (captured by wrapping `case`) — no duplicate names | confirmed |
| "44 guards on disk" | `ls scripts/check-*.py` → **44** | confirmed |
| "roughly +648 / −93" | `git diff --numstat 7794d825^..HEAD` → guard `441/55` + manifest `207/38` = **648 / 93** | confirmed **exactly** |
| manifest size | **163** entries, a JSON list | confirmed |
| population split | 37 in population / 10 compliant / 27 debt, and my own in-process `classify()` over the 44 files reproduces `compliant = 10, in population = 37` | confirmed |
| "`7794d825^..HEAD` is the fold" | `HEAD` (`5101f82c`) touches **only `docs/backlog.md`**; the guard's last change is `449bfb82` | corrected detail, no consequence |

### Instrumented runs

- **Case-name capture.** Wrapped `case()` and ran `_self_test()` in-process: 404 names, all unique.
- **Manifest binding check.** All **163** `edits` anchors occur **exactly once** in the file, and all
  **163** `expect` strings match a real emitted case name — **0 orphans**.
  ⚠ My first attempt at this check compared `expect` against the *source text* and reported
  "74 not found". That was wrong: case names are wrapped across source lines. The negative was an
  artefact of my own corpus, caught by re-measuring against what the suite emits. Recorded because
  the wrong number is the more instructive half.
- **Mutation experiments.** Run **in-process with `__file__` bound to the real script path**, over a
  text-level replacement, so nothing on disk changed and `ROOT` resolved to the real repo. A first
  attempt that ran a *copy* from the scratchpad produced three `[FAIL]`s in every arm, including the
  unmutated one — an ambient failure (`ROOT` pointed at the scratchpad). **Every mutation result
  below is reported against a green control** (`CONTROL — unmutated: 404/404 passed`).
- **Blast radius.** For every candidate fix: apply it, then diff `classify().routes` over all 44
  guards on disk against the unpatched baseline.

### What I could not run — stated, not hidden

- **`scripts/check-plan-code.py --mutate .` was NOT run.** `5101f82c`'s own commit message measures
  the full sweep at **~85 minutes** (and PR #365's `verify` was cancelled at the 30-minute ceiling
  26.2 minutes in, having never reached 119 of this file's 163 entries). I did not run it.
  ⛔ **Therefore every claim in this review about the mutation manifest's behaviour under the real
  harness is NOT MEASURED.** What I did measure is weaker and stated as such: the manifest's anchors
  and expect-strings all bind (above), and three specific severances run in-process against a green
  control (finding **M3**). Whether the harness would grade those identically is NOT MEASURED.
- **No live false green was found.** Every finding below measured **0 of 44**. That is a negative
  result, not an unrun check — see §3 for how hard I looked.

---

## 2 · Findings

Severity order. **Findings and proposed fixes are stated separately, and every proposed fix is
UNVERIFIED** — round 8's reviewer shipped a fix that was dead *and* wrong while its finding was
correct, and my own first draft of the **H3** fix did exactly that (§2.4).

---

### B1 · Blocking — on the REBIND route, one case-built argument discards `world_class`'s LIVE verdict, re-opening callee identity *and* every ambient-path rule

**Aim: deliverable. Caused by round 9's own fix: PARTLY. Blast radius: LATENT, 0 of 44.**

`substitution_changes_the_world` asks `world_class(value, …) is LIVE` and then, at
`scripts/check-main-drivable.py:1200-1210`, throws that answer away whenever any leaf of the value
is a name the case bound:

```python
    if world_class(value, fn, tree, world) is LIVE:
        bound_here = {n.id for n in ast.walk(fn or value)
                      if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
        if not (names & bound_here):
            return False
    return True
```

This is round 9's Blocking B1 — *"ONE argument the case built makes the child answer first, so the
repair never runs"* — recurring on the **fourth route**, through a different overriding mechanism.
Round 9 moved the callee-identity question above `kids` for PARAM/ARGV/SUBPROC. REBIND does not
consult `kids`; it consults this clause, and this clause overrides the single owner's answer.

**Measured.** Column 2 is `world_class`'s own verdict as the PARAM route consumes it; column 3 is
what the same expression earns on REBIND:

| substituted value | PARAM | REBIND | |
|---|---|---|---|
| `same_root(td)` where `def same_root(x=None): return ROOT` | refused | **`rebind`** | callee identity, round 8's Codex Blocking |
| `K(td).same()` where `same` returns `ROOT` | refused | **`rebind`** | method identity, round 9's Codex High |
| `os.path.relpath(td)` | refused | **`rebind`** | round 8's `relpath` repair |
| `os.path.join('.', td)` | refused | **`rebind`** | round 5's ambient-literal rule |
| `os.path.join(f'.', td)` | refused | **`rebind`** | round 9's own f-string High |
| `os.path.abspath('sub')` (no case-bound leaf) | refused | refused | control |
| `tempfile.mkdtemp()` / `os.path.join(td, 'x')` | `param` | `rebind` | control, correct both ways |

Concrete exhibiting input (the whole module; `ROOT` is the guard's world global):

```python
def same_root(x=None):
    return ROOT
def main(argv=None, root=ROOT):
    if '--self-test' in argv:
        return _self_test()
    return ROOT
def _self_test():
    td = tempfile.mkdtemp()
    globals()['ROOT'] = same_root(td)      # hands main the world it already had
    case('x', main([]), 0)
```
→ `routes = ['rebind']`. Remove the argument (`same_root()`) and it is correctly refused — so the
*only* thing buying the credit is one case-bound argument the helper discards.

**Why this answers the brief's question 3 in the negative.** The extraction made `_resolve_callee`
the only place callee identity is *derived*. It is not the only place callee identity is *decided*:
this clause decides it by discarding the derivation. The duplication that remained is of the
**verdict**, not of the resolver — which is why looking for a second resolver (as round 9's fold
did) could not find it.

**Severity reasoning.** False **credit** — the false-green direction. It applies to the route that
8 of the 10 compliant guards on disk use, and it voids three repairs the file already paid for
(rounds 5, 8 and 9) on that route. The clause's own comment already records that it "SWALLOWED
round 8's own `relpath` repair on this route" — in the past tense, as a reason the clause was
wrong, while the clause and the behaviour both remain.

**Classification: STRUCTURAL.** The rule states the property it needs — `world_class` is the
declared owner of *"is this expression the LIVE repository, a world the case BUILT, or neither?"* —
and this route declines to apply it. No list grows; a route stops overriding an owner.

**Proposed fix — UNVERIFIED, and incomplete.** Ask the identity question through the single owner
*before* the leaf-level exception:

```python
    names = free_names(value)
    if (isinstance(value, ast.Call)
            and callee_returns_live(value, tree, world, 0)):
        return False
    if world_class(value, fn, tree, world) is LIVE:
```

Measured: **404/404 green, blast radius 0 of 44**, and it closes exhibits 1 and 2. ⛔ It closes
**2 of 5** — `os.path.relpath(td)` and both `os.path.join` forms still earn `rebind`, because they
are LIVE for an *ambient-path* reason rather than a callee-identity one. **The general repair is
not determined by this review.** The shape it must have: the exception exists to admit a world
*derived from* the live one (a modified copy — `{**saved, 5: saved[5] + " Detail:"}`) and a stub
(`lambda base: ([], False, "boom")`), and it must stop admitting a value that simply **is** the
live world or the ambient directory. An enumerative patch naming the five shapes would be the wrong
shape and I am not proposing one.

**Upper bound on what the exception protects, measured:** deleting `if not (names & bound_here):`
outright is **0 of 44** on disk and costs **8 of 404** suite cases. So the exception is defended by
eight synthetic cases and zero live guards. (This does **not** contradict the docstring's warning
that *requiring BUILT* sends `check-dashboard-entry.py` and `check-surface-recall.py` to DEBT —
that is a different change, and I did not test it.)

---

### H1 · High — round 9's Blocking case asserts the REBIND route with a row that cannot fail

**Aim: instrument. Caused by round 9's own fix: YES. Blast radius: n/a (a case, not a rule).**

Round 9's fold closed its Blocking with a four-row case, one row per route
(`scripts/check-main-drivable.py`, the `_R9B` block):

```python
for _s, _route in (("    case('y', main([], root=same_root(td)), 0)\n", "PARAM"),
                   ("    case('y', main([same_root(td)]), 0)\n", "ARGV"),
                   ("    subprocess.run([sys.executable, __file__, same_root(td)])\n", "SUBPROC"),
                   ("    globals()['ROOT'] = same_root(td)\n", "REBIND")):
    case(f"⛔ ONE argument the case built must not reopen the helper identity — {_route} …",
         _b9(_s), frozenset())
```

The REBIND row inserts a `globals()[…] = …` write and **no `main(...)` call**. `REBIND` can only
be added inside `classify`'s `for call, fn, kind in calls:` loop, so with `calls == 0` that loop
never runs and the row asserts `frozenset()` for a reason unrelated to the rule.

**Measured, with the subject sabotaged two different ways:**

| | PARAM | ARGV | SUBPROC | REBIND |
|---|---|---|---|---|
| as shipped (`suite main calls`) | `[]` (1) | `[]` (1) | `[]` (0) | `[]` (**0**) |
| `callee_returns_live` severed to `return False` | `['param']` | `['argv']` | `['subproc']` | `[]` |
| …and `substitution_changes_the_world` forced to `True` | `['param']` | `['argv']` | `['subproc']` | `[]` |

Three rows are falsifiable. The fourth stays green with the entire identity machinery removed *and*
with the rebind rule forced to the opposite answer. **The route whose repair the Blocking was about
is the one route its case does not test — and B1 is live in exactly that gap.**

**Classification: STRUCTURAL.** The case states its own premise (*drive the route*) and does not
establish it. The repair is to add the `main(...)` call the row needs, not to add a name.

**Proposed fix — UNVERIFIED.** Append `    case('x', main([]), 0)\n` to the REBIND row's inserted
body so the route can fire, and fix the expectation to what the corrected rule should produce
(`frozenset()` once B1 is fixed; **today it is `frozenset({REBIND})`**, which is the defect). Note
the ordering consequence: **this row cannot be repaired without deciding B1 first**, because a
faithful row written against today's behaviour would assert the false credit.

---

### H2 · High — a helper defined *inside* the suite that returns the live world earns PARAM, ARGV and SUBPROC

**Aim: deliverable. Caused by round 9's own fix: NO (round 8's). Blast radius: LATENT, 0 of 44.**

`_resolve_callee` resolves a bare-name callee through `_toplevel_functions`
(`scripts/check-main-drivable.py:1559-1562`):

```python
    if isinstance(func, ast.Name):
        return _toplevel_functions(tree).get(func.id)
```

A helper defined inside `_self_test` is not in `tree.body`, so it does not resolve, so
`callee_returns_live` answers `False`, so the call falls through to `return BUILT`. One indent
defeats round 8's Codex Blocking (*"an identity can hide behind a name"*).

**Measured — round 8's exemplar, with the helper at module level versus nested in the suite:**

| route | helper at module level | helper nested in the suite |
|---|---|---|
| PARAM | refused | **`param`** |
| ARGV | refused | **`argv`** |
| SUBPROC | refused | **`subproc`** |
| REBIND | refused | refused |

Identical results for `same_root()` with **no argument at all** — i.e. round 8's Blocking input
verbatim. Exhibiting input:

```python
def _self_test():
    td = tempfile.mkdtemp()
    def same_root(x=None):
        return ROOT
    case('y', main([], root=same_root()), 0)      # -> ['param']
```

**Classification: STRUCTURAL.** The file already owns the broader resolver: `_all_functions`
(`:418`) — *"Every function DEFINED anywhere in the module, nested ones included, by name"* — sits
140 lines above and is not consulted here. This is round 8's `iglob`/`glob` line exactly: the rule
applied to half the names the file already knows about.

**Proposed fix — UNVERIFIED.** `_all_functions(tree).get(func.id)` in place of
`_toplevel_functions(tree).get(func.id)`. Measured: **404/404 green, blast radius 0 of 44**.
⚠ Why it is still unverified: `_all_functions` is *flat by name* and its own docstring says *"two
nested helpers sharing a name collapse"*. A module with a top-level `f` and an unrelated nested `f`
would resolve to whichever `ast.walk` reached last — a correctness question this fix does not
settle and I did not measure. 39 of 44 guards on disk define nested-only functions, so the
population for that hazard is not small.

---

### H3 · High — `string_literal` excludes the empty f-string, so `f""` is credited where `""` is refused

**Aim: deliverable. Caused by round 9's own fix: YES (its own High, one spelling short).**
**Blast radius: LATENT, 0 of 44.**

Round 9's High established that *"a `JoinedStr` all of whose values are `Constant` IS a string
constant"*. The implementation adds a truthiness conjunct that excludes the one JoinedStr with no
values (`scripts/check-main-drivable.py:1500`):

```python
    if isinstance(expr, ast.JoinedStr) and expr.values and all(
            isinstance(v, ast.Constant) and isinstance(v.value, str) for v in expr.values):
```

`f""` parses to `JoinedStr(values=[])`, so `string_literal(f"")` is `None` while `string_literal("")`
is `""` — and `""` is in `AMBIENT_PATH_LITERALS`, i.e. the ambient directory (`Path("")` is
`PosixPath('.')`; `os.path.abspath("")` is the cwd).

**Measured — 4 of 4 tested shapes flip from refusal to credit on one `f`:**

| expression | `root=` plain | `root=` with `f` |
|---|---|---|
| `Path('')` / `Path(f'')` | refused | **`param`** |
| `os.path.abspath('')` / `…(f'')` | refused | **`param`** |
| `os.path.join('', td)` / `…(f'', td)` | refused | **`param`** |
| `os.listdir('')` / `…(f'')` | refused | **`param`** |
| control: `Path('.')` / `Path(f'.')` | refused | refused |

False **credit** — the false-green direction, and the strongest two exhibits are unambiguous:
`Path(f"")` and `os.path.abspath(f"")` both evaluate to the live working directory.

**Classification: STRUCTURAL.** The fix is the deletion of one conjunct from a rule whose own
docstring already states the property: `all([])` is `True` and `"".join([])` is `""`, so the
derivation already covers the empty case and the conjunct removes it.

**Proposed fix — UNVERIFIED.** Drop `expr.values and`. Measured: **404/404 green, blast radius
0 of 44**, and `world_class(f"")` becomes `live`, matching `""`.

⚠ **My first draft of this fix was dead and wrong**, and I am recording it because the brief
predicted exactly this. I drafted it with an `ast.literal_eval` fall-through for constant
arithmetic as well; that draft went **403/404**, failing
`` `_is_relative_literal` refuses a non-Constant and a non-str Constant rather than raising … (r7 Claude Low) ``
with `RAISED AttributeError` — because `ast.walk(None)` raises and that case deliberately feeds
`None`. Adding `expr is not None` restored 404/404. The finding was unaffected; the fix was wrong.

---

### M1 · Medium — `_ret_exprs` reads a nested definition's `return` as its parent's

**Aim: deliverable. Caused by round 9's own fix: NO (round 8's `ast.walk(helper)`), but the
extraction widened its reach to method and property callees. Blast radius: LATENT, 0 of 44.**

```python
def _ret_exprs(fn: ast.AST) -> list[ast.expr]:
    """Every value this definition hands back — `return`, `yield` and `yield from` alike."""
    return [n.value for n in ast.walk(fn) …]
```

`ast.walk` descends into nested `FunctionDef`s, so a nested function's `return` is collected as the
parent's. Since the rule is *any* return being LIVE makes the callee LIVE, the leak can only add
LIVE — a **false refusal** (lost credit), never a false credit.

**Measured:**

| module | verdict |
|---|---|
| `def builder():` / nested `def inner(): return ROOT` / `return tempfile.mkdtemp()` | **refused** |
| control, same without the nested def | `param` |
| control, `f = lambda: ROOT` instead of a nested def | `param` — a `Lambda` body is not a `Return` node, so lambdas do not leak |

**Classification: STRUCTURAL.** The docstring says *"Every value **this definition** hands back"*;
a nested function's return is not one. Deriving the correct set is a boundary condition on an
existing walk, not a new name.

**Proposed fix — UNVERIFIED.** Walk children but stop at `FunctionDef`/`AsyncFunctionDef`/`Lambda`
boundaries below the top node. Measured: blast radius **0 of 44**.

---

### M2 · Medium — a returned parameter's default is substituted even when the call site supplies that argument

**Aim: deliverable. Caused by round 9's own fix: NO (round 8's F1). Blast radius: LATENT, 0 of 44.**

`_definition_returns_live` rewrites a returned `Name` to its default unconditionally
(`scripts/check-main-drivable.py:1595-1598`), before `world_class` gets the chance to resolve the
parameter to its call sites — which the file already does elsewhere (`_constructed_at_call_sites`).

**Measured:**

| module | call | verdict |
|---|---|---|
| `def same(p=ROOT): return p` | `main([], root=same(td))` | **refused** |
| `def same(p): return p` | `main([], root=same(td))` | `param` |

Adding a default to a parameter the call site *overrides* loses the credit. The suite does not
contradict this: round 8's own cases (`_R8M`) call `same_p()` and `same_kw()` with **no
arguments**, where resolving to the default is correct. The supplied-argument input is untested.

False **refusal**. Direction is safe; the verdict is still wrong.

**Classification: STRUCTURAL.** The docstring's claim — *"A returned PARAMETER resolves to its
DEFAULT: `def same(p=ROOT): return p` hands back the global as surely as `return ROOT`"* — is true
only when the default is what the call uses. The call's own `args`/`keywords` are in hand at
`callee_returns_live`, and the call-site mechanism already exists.

**Proposed fix — UNVERIFIED.** Pass the call's supplied positional count and keyword names down,
and drop a default from the substitution map when the call covers that parameter. Measured with a
`self`-offset approximation: blast radius **0 of 44**. ⚠ The `self`-offset for a method receiver is
a guess in my probe, not a derivation, and would need settling before shipping.

---

### M3 · Medium — a masking pair inside round 9's own extraction: two clauses deciding "resolve a single candidate", neither killable

**Aim: deliverable (dead code) and instrument (unkillable region). Caused by round 9's own fix: YES.**
**Blast radius: 0 of 44, and behaviour-equivalent — no latent wrong verdict.**

```python
        if len(named) == 1:
            return named[0]
        if named and all(_ret_exprs(f) for f in named):
            return named if len({id(f) for f in named}) > 1 else named[0]
```

`named` holds distinct AST nodes, so `len({id(f) for f in named}) > 1` is true whenever
`len(named) >= 2` — and `len(named) == 1` was already returned above. The ternary's `else named[0]`
arm is **unreachable**; and with that arm present, clause 1 is **redundant** — a single candidate
reaches `named[0]` either way, and a single candidate with no returns yields `False` on both paths
(`_definition_returns_live` of `[fn]` with no returns, versus of `None`).

**Measured, in-process, against a green control:**

| arm | result |
|---|---|
| CONTROL — unmutated | **404/404 passed**, rc=0 |
| `if len(named) == 1:` → `if False:` | **404/404 passed**, rc=0 — unkillable |
| ternary → always `return named` | **404/404 passed**, rc=0 — unkillable |
| ternary → always `return named[0]` | 402/404, rc=1 — killable, so the general clause *is* covered |

`_resolve_callee` for two agreeing candidates returns a **list of 2**, confirming the else-arm never
fires.

⛔ **I am not arguing this deletion the unsound way.** "Its mutation cannot die, so it does nothing"
is the argument this file has had to reverse three times. The sound argument here is subsumption
plus one-rule-one-place: the general clause below is strictly more general and already answers
every input clause 1 answers, identically — verified by constructing both discriminating inputs
(single candidate with returns; single candidate without), not inferred from the unkillability.
This is the file's own thesis — *the copies are the defect generator* — recurring **inside the
extraction written to end it**.

**Classification: STRUCTURAL.**

**Proposed fix — UNVERIFIED.** Collapse both to one owner:

```python
        if named and all(_ret_exprs(f) for f in named):
            return named
```

Measured (as the two separate severances above): 404/404 and 0 of 44 for each half. The composite
was **not** measured as a single edit — NOT MEASURED.

⚠ **Manifest consequence, NOT MEASURED.** Manifest entry 153 mutates `if len(named) == 1:` to
`if named:` (a *widening*, which is killable and which I did not re-run under the harness) and entry
158 severs the general clause. Collapsing the two clauses **unbinds entry 153's `edits` anchor**,
which is this repo's measured orphaning class. Whoever folds this must retarget that entry; I did
not run `--mutate .` and cannot say what the harness would report.

---

### M4 · Medium — `_dead_branch_ids` sees only a bare `Constant` test, so a statically-true non-Constant leaves its `else` credited

**Aim: deliverable. Caused by round 9's own fix: YES (its own Medium, one spelling short).**
**Blast radius: LATENT, 0 of 44.**

Round 9 added the `else` of a statically-true `if` to the dead set. The enclosing condition is
`isinstance(node.test, ast.Constant)`, so only a bare constant is decided.

**Measured** (the suite's shape: a credited `argv` means the dead branch was credited):

| suite body | verdict | |
|---|---|---|
| `if True: pass` / `else: main([str(td)])` | refused | round 9's fix, works |
| `if 1:` …, `if 'x':` … | refused | works |
| `if (1,): pass` / `else: main([str(td)])` | **`argv`** | **false credit** |
| `if ():` `main([str(td)])` | **`argv`** | **false credit** (dead body) |
| `if not False: pass` / `else: main([str(td)])` | **`argv`** | **false credit** |
| `if 1 and 2: pass` / `else: main([str(td)])` | **`argv`** | **false credit** |
| `if False: pass` / `else: main(…)` | `argv` | control, correct |
| `while False: pass` / `else: main(…)` | `argv` | control — round 9 was right not to include `While` |

Round 1 called this shape *"the cheapest possible way to fake compliance"*. Four further spellings
of it are credited.

**Classification: SPLIT, and I am splitting it deliberately rather than claiming the whole thing.**

- `(1,)`, `()`, `[]` — **STRUCTURAL.** A literal collection is a literal, which is the property
  round 4's High already states for `world_class` (*"checked by SHAPE of the whole expression
  rather than by enumerating the operators"*), and `ast.literal_eval` derives it the way `ast` and
  `builtins` already settle grammar questions in this file. Fix measured below.
- `not False`, `1 and 2` — **ENUMERATIVE → park in backlog #224.** `ast.literal_eval` refuses both
  (measured: `ValueError`). Closing them needs an operator-aware constant folder, i.e. a new
  mechanism, not the application of an existing one.

**Proposed fix — UNVERIFIED, and partial by design.** A `_static_truth(test)` helper returning
`(bool,)` when the test contains no `Name`/`Attribute` and `ast.literal_eval` succeeds, else `None`.
Measured: **404/404 green, blast radius 0 of 44**; it closes `if (1,):` and `if ():`, leaves
`not False` and `1 and 2` credited, and the control `if False: pass / else: main(…)` stays credited.

---

### L1 · Low — `callee_returns_live`'s docstring asserts a direction the code does not have

**Aim: deliverable. Caused by round 9's own fix: YES.**

The docstring says of an ambiguous method name: *"two classes sharing a method name cannot be told
apart without types, and **guessing is the false-credit direction**"* — implying that declining is
the safe one. **Measured: declining is also the false-credit direction.** When `_resolve_callee`
declines, `callee_returns_live` answers `False`, the Call falls through to `return BUILT`, and the
route is **granted**:

| module | verdict |
|---|---|
| two classes, `dup` in both returns `ROOT` (agree) | refused — correct |
| two classes, one `dup` returns `ROOT`, the other has no return (declined) | **`param`** |
| two classes, `ROOT` vs `mkdtemp()` (disagree, declined) | **`param`** |

The third row is an asserted, deliberate limit (`N().mix()` → `PARAM`). The finding is not that
limit; it is that the sentence justifying it names the wrong direction. This file has an explicit
standard for exactly this — round 9's own `vars` note: *"this file's standard for a comment
asserting a property its code does not have is explicit."*

**Classification: STRUCTURAL** (a comment is corrected, not a list extended).
**Proposed fix — UNVERIFIED.** Reword to state the real trade: both answers can grant the route, and
declining was chosen because it is the one that does not *invent* a receiver. Row 2 (one candidate
without returns) is additionally not covered by any case.

---

### L2 · Low — constant string arithmetic defeats every literal test → **ENUMERATIVE, park in #224**

**Aim: deliverable. Caused by round 9's own fix: NO. Blast radius: LATENT, 0 of 44.**

`Path('.' + '')` and `Path('' + '.')` earn `param`; `Path('.')` is refused. `string_literal` returns
`None` for a `BinOp`, and the whole-expression shape test then answers `INERT`.

**Measured:** `string_literal` over nine spellings — `'.'`, `f'.'` and `('.')` resolve; `'.' + ''`,
`'' + '.'`, `f'{"x"}'`, `'./'+'x'`, `b'.'` do not.

**Classification: ENUMERATIVE → park.** I checked whether the structural repair was available and
it is not: `ast.literal_eval("'.' + ''")` raises `ValueError` (measured). Folding string
concatenation needs a new evaluator, which is #224's shape, not a one-conjunct deletion like H3.
Recording the distinction because H3 and L2 look like one finding and their repairs are not the
same kind.

---

### L3 · Low — an uncalled method reference classifies LIVE, because a `@property` is not distinguished from a plain method → **ENUMERATIVE, park in #224**

**Aim: deliverable. Caused by round 9's own fix: YES (its property branch). Blast radius: LATENT, 0 of 44.**

`world_class`'s `Attribute` branch calls `_resolve_callee(expr, tree)`, which matches any
`FunctionDef` in any class body by name — decorators unread. So `K().same`, where `same` is a plain
method returning `ROOT`, classifies LIVE, though a bound method object is not the live world.
Measured: `main([], root=K().same)` → refused; `main([], root=K().prop)` → refused (correct).

False **refusal**, harmless in practice. **Classification: ENUMERATIVE → park** — the only repair is
a decorator-name list (`property`, `cached_property`, `functools.cached_property`, …), which is
#224's shape exactly.

---

## 3 · What I tried to refute and could not

This is where the next round should *not* look.

1. **A LIVE false green — looked for two ways, found none.**
   - **Credit side:** I instrumented `classify` to name the line that earns each route for all
     **10** compliant guards and read every one. All ten credits are sound:
     `check-ci-watched.py:713` `main(["--decide"], stream)`; `check-dashboard-entry.py:1445/1460`
     (substitutes `g["collect"]` with a case-built lambda, drives `main`, asserts rc — read the
     source, it is exactly ADR-0014's rebind route); `check-fixture-variation.py` ×12 argv;
     `check-plan-code.py` ×4 argv over built roots; `check-plan-file-tags.py:335`;
     `check-ratchet-contract.py:941/965/980`; `check-rc-contract.py:747`;
     `check-selection-card.py:454` subproc; `check-surface-recall.py:655/705`;
     this guard itself ×5. The only arguable ones are the `REBIND['_self_test']` credits in
     `check-rc-contract.py:781-782` and `check-surface-recall.py:721-722`, where the substituted
     global is the *suite entry* rather than a world — and both guards earn rebind independently
     from genuine world substitutions, so **no verdict turns on it**.
   - **Pin side:** I checked whether any of the **27** pinned guards actually drives `main` from its
     suite. **None does** — `Verdict.calls == 0` for all 27. I then checked whether
     `suite_main_calls` was *missing* a drive, by diffing against every raw `main(...)` call in each
     AST: all 27 misses are the module-level `__main__` entry point
     (`sys.exit(main())` / `raise SystemExit(main())`), correctly excluded. There is no false pin
     of that shape.
   - Every candidate fix in §2 measures **0 of 44**. Consistent with rounds 7, 8 and 9.
2. **The mutation manifest is NOT orphaned.** All 163 `edits` anchors occur exactly once in the
   file, and all 163 `expect` strings match a real emitted case name. I expected orphans — the
   extraction moved two functions' worth of code and this repo has measured 7 orphans in one
   session — and found none. (My first measurement said 74; it was comparing against source text
   rather than emitted names. Corrected above.)
3. **`subprocess_self_calls` is not reachable from module level.** I suspected the SUBPROC route
   could be earned by a `subprocess.run([sys.executable, __file__], …)` outside the suite, since it
   is added *outside* `classify`'s per-call loop. It is gated by `named in reachable`, and `named`
   is `None` for module-level code. No false credit there.
4. **`_mentions_self_test` has no near-miss I could find.** Round 9 replaced the name-contains
   shortcut. I tried `args.self_test_only`, `args.selftest`, `no_self_test_mode`,
   `opts['self_test']` (all correctly **not** a dispatch) and `args.self_test`, `self_test`,
   `'--self-test' in argv`, `'--self-test' == argv[0]` (all correctly a dispatch). Clean.
5. **Round 9 was right not to include `While` in the dead-`else` rule.** I ran the counter-case:
   `while False: pass / else: main([str(td)])` is credited, and correctly — a `while`'s `else`
   executes when the loop does not run.
6. **A lambda does not leak into M1.** `f = lambda: ROOT` inside a helper that returns
   `mkdtemp()` keeps its credit — a `Lambda` body is not a `Return` node. Only nested `def`s leak.
7. **The depth bound does terminate `callee_returns_live`.** I could not construct a hang or a
   `RecursionError` through self-calls or mutual recursion; the `depth > 8` guard answers first.
8. **No new raise path.** I looked for a dying case (a subject that raises, so a mutation is red but
   unattributable) in the seven new/reshaped functions. `_callee_tail`, `string_literal`,
   `_module_dict_read`, `_ret_exprs`, `_resolve_callee`, `_definition_returns_live` and
   `callee_returns_live` are total over the inputs their callers can produce
   (`named[-len(args.defaults):]` is guarded; `_resolve_callee` only ever returns FunctionDefs).
   The one `AttributeError` I provoked was in **my own** proposed fix, not in the shipped code.

---

## 4 · Q4(a) convergence table

Judged by **AIM, not severity** (`docs/review-method.md:104`).

| # | Severity | Aim | Caused by round 9's own fix? |
|---|---|---|---|
| B1 | Blocking | **deliverable** | partly — the callee-identity half became reachable through the extraction; the ambient half predates round 9 |
| H1 | High | instrument | **yes** — it is round 9's own Blocking case |
| H2 | High | **deliverable** | no — round 8's repair, evaded by nesting |
| H3 | High | **deliverable** | **yes** — round 9's own High, one spelling short |
| M1 | Medium | **deliverable** | no — round 8's `ast.walk(helper)`, reach widened by the extraction |
| M2 | Medium | **deliverable** | no — round 8's F1 |
| M3 | Medium | **deliverable** + instrument | **yes** — introduced by the extraction itself |
| M4 | Medium | **deliverable** | **yes** — round 9's own Medium, one spelling short |
| L1 | Low | **deliverable** | **yes** — round 9's own comment |
| L2 | Low | **deliverable** (parked) | no |
| L3 | Low | **deliverable** (parked) | **yes** — round 9's property branch |

**Totals:** 11 findings — 1 Blocking, 3 High, 4 Medium, 3 Low.
**10 of 11 in the deliverable**, 1 aimed at the instrument (M3 straddles both).
**6 of 11 caused by round 9's own fix** (B1 partly, H1, H3, M3, M4, L1, L3 → 6 clear plus B1 partial).
**0 of 11 are LIVE** — every one measures **0 of 44**.

**Stop condition:** a Blocking, three Highs, and ten findings in the deliverable. **CONTINUE.**
The counter stays at **0** — it has not had its first qualifying round.

---

## 5 · Q5 — thrashing, per finding and overall

**Per finding:** see the right-hand column of §4. Six findings are the previous round's own fix one
step short or its own new code; five are older repairs reached from a new position.

**Can a redesign remove this class, or does each fix only create the next instance?**

Round 9 answered *"yes, a redesign can"* and named it: one callee-identity owner. **That redesign
worked for what it named, and the measurement says so** — three of the four routes now consult
`_resolve_callee` once, above `kids`, and H2/M1/M2 are defects *inside* that single owner rather
than drift between copies. Fixing one of them fixes it everywhere, which is precisely what the
extraction bought.

**But B1 shows the class has a second home the redesign did not reach, and it is nameable.** The
duplication that remains is not of the *resolver* — it is of the **verdict**. `world_class` is the
declared owner of "what world is this expression", and the REBIND route overrides its answer at
`:1207` whenever a leaf is case-bound. Round 9 looked for a second resolver and correctly found
none; the second decision site does not resolve anything, it discards. So the redesign that removes
the class is: **one authoritative world verdict that no route may override — all four routes consume
`world_class`'s answer rather than two of them re-deciding.** That is a statable structural change
with a falsifier (*a route that reaches a different verdict than `world_class` for the same
expression*), not an endless stream of spellings.

**So: accretion, not thrashing — but the arming condition deserves the coordinator's judgement, and
I am not going to decide it quietly.** The honest reading of
`docs/dev-process.md` — *two consecutive rounds whose findings came from the previous round's own
fix, in one component* — is that it **appears met**: round 9's Blocking was round 8's repair one
step short, and round 10's H3 and M4 are round 9's repairs one step short in the same file, with
M3 and H1 being defects in round 9's new code itself. One component throughout:
`scripts/check-main-drivable.py`.

The counter-argument, stated so it can be weighed rather than assumed:

- The redesign test that `review-method.md` applies — *can a redesign remove this class?* — comes
  back **yes**, with the specific change named above. Round 9's redesign measurably reduced the
  class rather than relocating it.
- The newest findings are concentrated in code **no round has seen**, which is the expected place
  for them and is not the same signal as a repair that keeps failing.
- **Nothing here is LIVE.** Nine rounds and eleven findings have not produced a wrong verdict about
  a real guard since round 7. Against 44 guards on disk, the thing D2 was built to measure is
  stable; what keeps moving is the synthetic frontier. That is a strong argument that the remaining
  return is in **building**, not in another round — and the repo's own measured lesson is that
  *review is the wrong instrument for a SURFACE*.

My recommendation, which is the coordinator's call and not mine: **fold B1, H1, H2, H3 and M3** —
B1 and H1 together, because H1's row cannot be rewritten without deciding B1 — then park L2, L3 and
M4's operator half in #224, and treat M1/M2/M4-structural/L1 as a batch. Then make the Phase 6
arming decision explicitly, in writing, with the per-finding evidence above.

---

## 6 · Verdict

**NOT CONVERGED.**

One Blocking in the deliverable (a false credit on the rebind route, voiding three previously-paid
repairs), three Highs, and the case that was supposed to cover the Blocking's fourth route cannot
fail. No finding is LIVE: every candidate fix measured **0 of 44**.
