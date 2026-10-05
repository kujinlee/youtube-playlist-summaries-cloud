# Round 7 — Claude adversarial half · `scripts/check-main-drivable.py`

**Subject:** `scripts/check-main-drivable.py` (ADR-0014 rule D2), branch `d2-main-drivable`, PR #365.
**Tree:** frozen at `2a01fd5e`. **Reviewer:** Claude (Opus 5), 2026-10-04.

## The gate RAN

Every verdict below is from an executed command. Controls first:

```
$ python3 scripts/check-main-drivable.py --self-test
334/334 passed                                              (rc 0)

$ python3 scripts/check-main-drivable.py --report
44 guards on disk · 7 without main() (outside the population) · 37 in population
  10 drive main() over a constructed world — param 3, argv 3, rebind 8, subproc 1
  27 pinned as ADR-0014 identity debt                       (rc 0)
```

Severances were run two ways, both with a green control established first:

* **Full staged tree** via `cpc.stage_tree` + `cpc.child_env` (the mandate's recipe).
  Control: `334/334 passed`, rc 0.
* **In-process** (`exec` the mutated source into a fresh module registered in `sys.modules`,
  then call `_self_test()`), ~26 s per run. Control: `334/334 passed`, rc 0, and three
  manifest entries re-killed as known positives before any negative was trusted.

⚠ One instrument of mine was broken and discarded rather than believed: a first `symtable`
ground truth returned the empty set for the known positive `_sv`, because
`st.get_children()[0]` is the `__annotate__` block on Python 3.14, not the function. Fixed
and re-validated before use. A second trap the mandate warns about caught me too — see
**L3**, where a severance that read DEAD turned out to be a semantic no-op.

---

## Summary

| Sev | # | Deliverable / Instrument | Caused by the previous round's fix? |
|---|---|---|---|
| Blocking | 0 | — | — |
| High | 2 | 2 deliverable | H2 **yes** (round 6); H1 no — round 6's fix is incomplete, not causative |
| Medium | 4 | 3 deliverable, 1 instrument | M1 partly, M3 **yes** (round 7), M4 no |
| Low | 5 | 1 deliverable, 4 instrument | no |

**Blast radius, measured honestly: none of these changes a verdict on the 44 guards on disk
today.** I applied a candidate fix for H2 and for M2 and diffed `classify` over all 44 real
guards: `0` verdict changes each. Every finding below is latent. They matter because the debt
set has 27 names in it and the routes below are what a guard will be *written to* when someone
pays one down.

**The manifest is in good order.** All 133 entries re-run on a full staged tree:
`Counter({'CAUGHT': 133})`, elapsed 2680 s. Every anchor binds exactly once; every entry has an
`expect`; **every named `expect` case actually reddened** (0 misses). No entry is masked.

---

# High

## H1 — Round 6's "cheapest fake compliance" route is closed for ONE spelling. Nine of twelve trivial wrappers still earn REBIND, on 66% of the world.

**Deliverable.** Not caused by round 7; it is the uncovered remainder of round 6's own fix.

`substitution_changes_the_world` (`scripts/check-main-drivable.py:1031`) closes the identity
case with a test on a **bare `Name`**:

```python
if isinstance(value, ast.Name) and value.id == name and not _bound_values(name, fn):
    return False
```

The comment above it states the defect as a class — *"an IDENTITY substitution is recorded as
changing the world"* — and calls it cheaper than `if False:`. The general LIVE branch below
backs the bare-Name test up only for globals that are module **assignments**, because
`world_class` reaches LIVE through `expr.id in world` and `world` here is
`guard_world_globals()` (assignments only). For an **import** or a **def**, the name is INERT,
so nothing but the bare-Name special case stands between an identity substitution and a route.

I re-derived round 6's own figure rather than quoting it:

```
37 guards with main(); world_names total 814; absent from guard_world_globals 537 (66%)
```

Twelve wrappers, each evaluating to **exactly the same object** as the global being replaced,
run through `classify` on a fixture with one assignment global, one import and one def:

| wrapper | `ROOT` (assignment) | `subprocess` (import) | `helper` (def) |
|---|---|---|---|
| `X` — round 6's fix | DEBT | DEBT | DEBT |
| `(X)` | DEBT | DEBT | DEBT |
| `globals()['X']` | DEBT | DEBT | DEBT |
| `[X][0]` | DEBT | **rebind** | **rebind** |
| `(X,)[0]` | DEBT | **rebind** | **rebind** |
| `X if True else X` | DEBT | **rebind** | **rebind** |
| `X or X` | DEBT | **rebind** | **rebind** |
| `(X,)[-1]` | DEBT | **rebind** | **rebind** |
| `{0: X}[0]` | DEBT | **rebind** | **rebind** |
| `(lambda: X)()` | DEBT | **rebind** | **rebind** |
| `[v for v in [X]][0]` | DEBT | **rebind** | **rebind** |
| `next(iter([X]))` | DEBT | **rebind** | **rebind** |

Concrete input and verdict:

```python
def _self_test():
    globals()["subprocess"] = [subprocess][0]      # hands main the module it already had
    return main([])
# -> routes = ['rebind']   (classify, fixture.py)
```

`[subprocess][0]` is three characters more than `subprocess`. **The observation that would make
this FAIL** is the table above: any row where the import/def column is not DEBT.

**Why it is High and not Blocking:** no guard on disk writes this. It is High because the
cheapest route to a false green on this gate is still open, and the gate's live job is to
police 27 guards that will each be edited to get off that list.

**Suggested direction (a hypothesis, not a verdict):** the test is on the value's *class*; the
property is *does this expression evaluate to the global itself*. A leaf test — "every free
name in the value is this global, the value binds nothing and adds no literal" — is the same
shape `_is_restore_value` already uses successfully, and would subsume all twelve rows without
a list of wrappers.

---

## H2 — A zero-argument directory reader is the live cwd and classifies BUILT. Round 6's fix caused it; the deletion has to be partly reversed. (The third reversal.)

**Deliverable. Caused by the previous round's fix — measured across commits.**

Round 6 (`b1c20403`) moved `listdir`, `scandir`, `walk`, `iterdir`, `glob` **out** of
`LIVE_WORLD_READERS` and into `BASE_RELATIVE_PATH_OPS` (`:237`), where liveness is decided by
the *base*:

```python
if tail in BASE_RELATIVE_PATH_OPS:
    base = (expr.args[0] if expr.args
            else expr.func.value if isinstance(expr.func, ast.Attribute) else None)
    if base is not None and _is_relative_literal(base):
        return LIVE
```

`os.listdir()` and `os.scandir()` take **no argument** and default to `'.'`. With no argument
and a module-function callee, `base` resolves to the `os` Name, which is not a relative
literal, and the function falls through to `return BUILT`.

Measured across the two commits (`world_class`, same expression, same fixture):

```
os.listdir()           pre-r6fix(0d326382)=live    HEAD(2a01fd5e)=built
os.scandir()           pre-r6fix(0d326382)=live    HEAD(2a01fd5e)=built
sorted(os.listdir())   pre-r6fix(0d326382)=live    HEAD(2a01fd5e)=built
os.listdir('.')        pre-r6fix(0d326382)=live    HEAD(2a01fd5e)=live     <- correct, both
Path(td).iterdir()     pre-r6fix(0d326382)=live    HEAD(2a01fd5e)=built    <- the fix's real win
os.listdir(td)         pre-r6fix(0d326382)=live    HEAD(2a01fd5e)=built    <- the fix's real win
```

Round 6 was right about the two bottom rows and overshot by three. End to end, two spellings of
**the identical runtime value** now get opposite verdicts:

```python
def _self_test():
    return main([], root=os.listdir())      # -> routes = ['param']     FALSE CREDIT
    return main([], root=os.listdir('.'))   # -> routes = DEBT          correct
    return main([], root=os.getcwd())       # -> routes = DEBT          correct
    return main([], root=sorted(os.scandir()))  # -> routes = ['param'] FALSE CREDIT
```

**The observation that would make this FAIL:** `main([], root=os.listdir())` earning any route.

⛔ **This is NOT the case parked in backlog #224**, and the distinction is load-bearing. #224
parks *"here is another spelling of the live repository"* — a name nobody enumerated. `listdir`
and `scandir` are **already in this file's own list**; the rule has already decided they read
ambient state and simply fails to apply that when the defaulted argument is omitted. It is a
regression in the handling of an enumerated name, and it has a falsifier the parked class
lacks: the same call with its default written out explicitly gets the opposite answer.

**Blast radius: latent.** I grepped the tree — there is no zero-argument `listdir()`/`scandir()`
anywhere in `scripts/`. I applied the fix (a zero-arg, non-attribute call in the ops set returns
LIVE) and diffed `classify` across all 44 guards on disk: **0 verdict changes**.

**Coverage note:** the suite pins the BUILT direction of this clause (`:3007`, seven expressions
over `td`) and the relative-literal direction (seven more), and has **no case at all** for the
zero-argument form. That is why round 6's overshoot shipped.

---

# Medium

## M1 — `free_names` diverges from CPython on a re-read walrus target, and a restore written that way earns a false REBIND.

**Deliverable.** Round 7's `NamedExpr` clause closed the binding site and left the read site;
the defect pre-dates it, so round 7's fix did not *cause* it — it is one spelling short of
covering it.

I differential-tested `free_names` against CPython's own `symtable` over 41 expression shapes
(ground truth: names the expression reads from the enclosing function scope). **38 agree; 3
diverge, all the same class:**

```
EXPR                                        free_names            symtable (truth)
(_t := _sv) or _t                           ['_sv', '_t']         ['_sv']
[q for n in _sv if (q := n)]                ['_sv', 'q']          ['_sv']
[k for i in _sv for j in i if (k := j)]     ['_sv', 'k']          ['_sv']
```

`free_names` drops the walrus **target** at its binding site (`:868-877`, round 7's fix) but
counts a later read of that target, in the same expression, as a free name of the case. Both
consumers then fail in the **credit** direction, because the target is a Store name and
therefore in `_is_restore_value`'s `locals_`:

```python
def _self_test():
    _sv = WORLD
    globals()["WORLD"] = (_t := _sv)                       # -> DEBT    correct (r7's fix)
    globals()["WORLD"] = (_t := _sv) or _t                 # -> rebind  FALSE: this is a restore
    globals()["WORLD"] = [q for n in [_sv] if (q := n)][0] # -> rebind  FALSE: this is a restore
    return main([])
```

**The observation that would make this FAIL:** either of the last two earning a route, when
`globals()["WORLD"] = _sv` earns none.

`scripts/check-main-drivable.py:846`, walrus branch at `:868`. Latent — no guard on disk writes a restore this way.

## M2 — A case that names its tempdir after one of the guard's own globals is refused. The file states the opposite rule.

**Deliverable.** Not caused by round 7.

`world_class`'s Name branch (`:1399`) tests `expr.id in world` **before** it consults
`_bound_values`, so a local binding can never shadow a module-global name:

```python
if expr.id in LIVE_WORLD_NAMES or expr.id in world:
    return LIVE
bindings = [v for _, v in _bound_values(expr.id, fn) if v is not None]
```

The verdict therefore depends on the local variable name the case happened to pick:

```python
def _self_test():
    td = tempfile.mkdtemp();    return main([], root=td)    # -> ['param']  correct
    ROOT = tempfile.mkdtemp();  return main([], root=ROOT)  # -> DEBT       lost credit
    ROOT = tempfile.mkdtemp();  return main([], root=Path(ROOT))  # -> DEBT
    ROOT = tempfile.mkdtemp();  return main([], root=str(ROOT))   # -> DEBT
```

This contradicts the file's own stated rule. `:1479` says *"a name the case BOUND that happens
to collide with the list (`home = str`), where round 3's shadowing rule says the case's own
binding wins."* That is true of `LIVE_WORLD_READERS`, whose test sits **after** the bindings
block, and false of `world`, whose test sits before it. One principle, applied to one of two
lists — and a comment asserting a property the code does not implement is the defect this file
names six times.

**Reachability:** the shape is on disk. `check-fixture-variation.py:_self_test` shadows
`EXAMINED_KEYS`/`KNOWN_UNVARIED`/`EXEMPT` 28 times; `check-plan-file-tags.py:_drive_main`
shadows `ROOT`/`DOCS` 4 times. Neither loses its verdict, because both comply by another route.
**I applied the fix and diffed all 44 guards: 0 verdict changes.** Latent, lost-credit
direction.

## M3 — `_is_relative_literal` was added this commit, and its rule was hand-inlined 150 lines below in the same commit.

**Deliverable (drift risk). Caused by the previous round's fix — this commit's.**

Round 7 added `_is_relative_literal` (`:1303`) as the named owner of *"is this literal a
relative path"*. The `CWD_CONSTRUCTORS` branch at `:1457-1461` asks the same question of its own
argument with a hand-written copy:

```python
if tail in CWD_CONSTRUCTORS and len(expr.args) == 1 and not expr.keywords:
    only = expr.args[0]
    if (isinstance(only, ast.Constant) and isinstance(only.value, str)
            and not only.value.startswith(("/", "\\"))):
        return LIVE
```

I replaced those three lines with `if _is_relative_literal(only):` and measured:

```
verdict changes over the 44 guards on disk:        0
world_class changes over 29 path expressions:      0
full suite:                                        334/334 passed   (DEAD)
```

Behaviourally identical — so this is duplication, not divergence, **today**. The repo has
measured a second implementation of one rule drifting from the first **seventeen** times, most
recently inside the commit that added the first; `_is_globals_call` carries that exact warning
at `:614` and `_global_target_names` at `:698` records paying for it. The two copies also have
separate manifest entries (121 and 132), so a drift between them is not what either entry tests.

## M4 — The lambda-DEFAULT scope rule in `free_names` is unfalsifiable, and severing it flips a verdict.

**Instrument (a suite gap), with a measured deliverable consequence.** Not caused by round 7.

Round 6 rewrote `free_names` on the stated principle that *"the parts that evaluate OUTSIDE a
binder — a lambda's defaults, a comprehension's first iterable — are the enclosing scope's.
That is Python's own rule, read off the grammar."* Manifest entry 116 claims to cover the
lambda half. It mutates the defaults loop to `for d in []:` — which tests that defaults are
**visited at all**, and is correctly CAUGHT. Nothing tests the scope they are visited **in**.

Severance: move the defaults loop below `params` and pass `bound | params`.

```
DEAD   T8 free_names: lambda defaults evaluated INSIDE the lambda scope
       tally=334/334 passed  nfail=0
```

It is not a no-op — it changes `free_names` and it changes a verdict:

```
{**_sv, **(lambda td: td)(td)}       base=['rebind']  severed=['rebind']   (r6's own shape)
{**_sv, **(lambda td=td: td)()}      base=['rebind']  severed=['DEBT']  <- uncaught flip
{**_sv, **(lambda *, td=td: td)()}   base=['rebind']  severed=['DEBT']  <- uncaught flip
```

Round 6's High was this exact false-debt, via a lambda **argument**. The **default** spelling is
unprotected. Round 6 already recorded reading "cannot die" as "does nothing" on this very
function and having to put the clause back; the lesson applies again one parameter over.

---

# Low

## L1 — A fifteenth dying case: `len(expr.args) == 1` raises `IndexError` on `Path()`.

**Instrument.** `scripts/check-main-drivable.py:1457`.

```
DIES   T1 CWD_CONSTRUCTORS: drop `len(expr.args) == 1`
       tally=None  nfail=0  exc=IndexError: list index out of range
```

Zero `[FAIL]` lines and no tally — the suite dies and the mutation is unattributable, which is
exactly what `--mutate .` refuses. The trigger is a bare `Path()` (manifest entry 89's subject)
reaching `only = expr.args[0]`. The site that raises is `world_class`, not the case that names
the rule — the distinction `_caught`'s docstring says was "learned twice over, at a cost of two
rounds". The fix is a `_caught` wrapper on the case that feeds `Path()` through, not a change to
the clause.

## L2 — Five clauses in and around the new code cannot be killed by any case.

**Instrument.** All measured at `334/334 passed`, each confirmed to be a real edit (not a
reformat) before being called dead:

| severance | result | why |
|---|---|---|
| drop `"./"`, `"../"` from `AMBIENT_PATH_LITERALS` (`:253`) | DEAD | subsumed by `startswith(("./", "../"))` on `:1379` — both members match it |
| drop `not expr.keywords` from the `CWD_CONSTRUCTORS` branch (`:1457`) | DEAD | no case passes a keyword to a path constructor |
| drop `base is not None` (`:1471`) | DEAD | `_is_relative_literal(None)` already returns False |
| drop `isinstance(expr, ast.Constant)` from `_is_relative_literal` (`:1317`) | DEAD | no case supplies a non-Constant base |
| drop `isinstance(expr.value, str)` from `_is_relative_literal` (`:1317`) | DEAD | no case supplies a non-str Constant base |

**Two of the five are in the three-line helper this commit added** — of its three conjuncts,
only `startswith` is covered (entry 132). ⚠ And the right repair is **not** deletion: with both
type guards gone, `_is_relative_literal` raises `AttributeError` on a non-Constant base, and
that base is reachable — a bare-name call whose tail is in the ops set (`resolve()`, `glob()`,
`walk()`, `iterdir()`) resolves `base` to `None`. These clauses need **cases**, not the
"cannot die ⇒ delete" treatment this file has applied fourteen times and had to reverse twice.

## L3 — The `bound if i == 0 else inner` ternary at `:895` is provably equal to `inner`.

**Deliverable (dead expression), and a correction to my own hypothesis.**

I first recorded this as a sixth dead clause: severing it to `rec(gen.iter, inner)` leaves
`334/334 passed`. The mandate's warning applies — I checked whether the mutation changes
behaviour, and **it does not**. `inner` is initialised to `bound` and is only updated *after*
`rec(gen.iter, …)`, so at `i == 0` the two arms are the same object, and at `i > 0` both select
`inner`. The conditional cannot have an effect at any input.

So it is not a coverage gap; it is a no-op dressed as the load-bearing scope distinction its own
`⚠` comment claims it to be. Manifest entry 117 kills the *other* mutation of the same line
(`→ bound`, which really does change `i > 0`), so the line is covered — by a case that tests a
property this expression is not the one providing. The enclosing-scope rule for the first
iterable rests entirely on `inner = bound`, one line above.

## L4 — `:1822` declares a count that is wrong by a factor of two.

**Instrument.** *"IT IS DEFINED FIRST BECAUSE NINE CASES NEED IT"* — there are **19**
`_caught(` call sites (18 with a lambda, plus the `def`). `check-selftest-counts.py` passes
(rc 0, "51 script(s) declare a count, every one verified by running it") because it reads
declared `--self-test` counts, not prose. This repo has recorded three declared-count drifts;
this is a fourth, in a sentence about the dying-case mechanism that is itself the subject of
fifteen findings.

## L5 — Two of 133 manifest anchors are mid-line fragments.

**Instrument.** All 133 bind exactly once today and all 133 are CAUGHT. Two do not start at a
line boundary:

```
[ 49] ' or expr.id in world:'
[114] 'and value.id == name and not _bound_values(name, fn):'
```

Both are fragments of a larger `if`. The repo's measured lesson is that an anchor is unbound by
any nearby edit; a 21-character fragment inside a boolean expression is the fragile end of that.
Entry 114 in particular anchors on the very clause H1 proposes to restructure.

---

# What I tried to refute and could not

* **A sixth masking pair — attacked and REFUTED by its own test.** My candidate was
  `base is not None` (`:1471`) against `isinstance(expr, ast.Constant)` inside
  `_is_relative_literal` (`:1317`): on the input `base is None`, each returns False and either
  alone suffices. Both are individually DEAD, which is the signature. The pair test is whether
  severing **both** is CAUGHT — it is not:
  ```
  DEAD   A only (drop `base is not None`)                 334/334
  DEAD   B only (drop `isinstance(expr, ast.Constant)`)   334/334
  DEAD   A AND B together                                 334/334
  ```
  They are dead for the same missing input, not because they mask each other. **No sixth
  masking pair found.** Reported as L2 instead.
* **The identity early-return** (`:1031`). Severed: CAUGHT, 332/334, and the two reddening
  cases are precisely the import and def cases round 6 wrote. The clause is falsifiable; H1 is
  about its *width*, not its existence.
* **The base precedence in `BASE_RELATIVE_PATH_OPS`.** I suspected `expr.args[0] if expr.args`
  picks the wrong base for a method call with arguments (`Path(td).glob("*.py")`). Severing to
  prefer the receiver is CAUGHT (331/334). And the concern does not arise: `kids` is computed
  first, so a method call with a built receiver returns BUILT before the clause is reached.
  `Path(td).glob('*.py')` → `built`, `sorted(Path(td).glob('*.py'))` → `built`. Held.
* **`free_names` against CPython's own `symtable`, 41 shapes** — nested comprehensions,
  starred targets, posonly and kw-only lambda params, lambdas inside comprehension conditions,
  comprehensions inside lambda defaults, async comprehensions, dict comprehensions, generator
  chains. 38 of 41 exact agreement. The three divergences are M1 and are one class. The
  Lambda and comprehension branches are correct on every other input I could build.
* **`global`/`nonlocal` interaction.** `_own_scope`'s escape hatch for a nested def that
  declares `nonlocal`/`global` is CAUGHT when severed (333/334). Held.
* **The depth bound** (`:1369`). Raising 8 → 400 is CAUGHT. Held.
* **`live_substitutions` ordering** (`prior[-1]` → `prior[0]`): CAUGHT, 319/334. Held strongly.
* **`_is_restore_value`'s subscript-index exemption**: CAUGHT. Held.
* **`suite_main_calls`' skip of `main`'s own body**, and **`subprocess_self_calls`'
  reachability filter**: both CAUGHT. Held.
* **Identity substitutions through `sys.modules['X']`, a `globals()` read-back, a tuple
  assignment, and a parenthesised name**: all correctly DEBT. Held — H1 is the wrapper set,
  not these.
* **The 133 manifest entries.** Re-run on a full staged tree: 133/133 CAUGHT, every anchor
  binding once, every named `expect` case reddening. I found no survivor and no masked entry.
* **`--report` / `assess` reconciliation.** `pin_paid`, `pin_stale` and the `whole` gating all
  behave as documented on a subset and on an override. Nothing found.

---

# Stop-condition answers

**Per finding — deliverable or instrument, and did the previous round's fix cause it?**

| # | Aim | Previous round's fix caused it? |
|---|---|---|
| H1 | **Deliverable** (the rule's verdicts) | No — round 6's fix is *incomplete*, one spelling of twelve |
| H2 | **Deliverable** | **Yes** — round 6 (`b1c20403`) moved the names out of `LIVE_WORLD_READERS`; measured LIVE→BUILT across the commit |
| M1 | **Deliverable** | Partly — round 7 (`2a01fd5e`) fixed the walrus binding site and left the read site |
| M2 | **Deliverable** | No — pre-dates the slice |
| M3 | **Deliverable** (drift risk) | **Yes** — round 7 created both the owner and the inlined copy |
| M4 | **Instrument** (suite gap) with a measured verdict flip | No — round 6's gap, unclosed |
| L1 | **Instrument** | No |
| L2 | **Instrument** | Two of five are in code round 7 added |
| L3 | **Deliverable** (dead expression) | No |
| L4 | **Instrument** | No |
| L5 | **Instrument** | No |

**Split: 5 deliverable, 5 instrument, 1 mixed (M4).**

**Thrashing or prose floor?** Two of eleven findings were *caused* by the immediately preceding
fix (H2 by round 6, M3 by round 7), and one more (M1) is the preceding fix one spelling short.
That is the same shape as rounds 4–6. But the character has shifted: this round found **no
Blocking**, and **every finding is latent** — a candidate fix for each of the two Highs changes
**0 of 44** verdicts on disk. The defects are now in the rule's *reach*, not its *answers*. The
test *"can a redesign remove it?"* answers yes for H1 (a leaf-provenance identity test subsumes
all twelve wrappers, the way `_is_restore_value`'s rewrite subsumed its `COPIERS` list) and no
for H2, which is a one-line reinstatement. I do not think this is thrashing on the rule; I think
H1 is the last structural item and the rest are a prose floor forming underneath it.

---

# NOT CONVERGED

Two Highs, one of them a measured regression introduced by the previous round's fix that
requires partly reversing a deletion — the third such reversal in this slice. A duplicated rule
implementation created by this commit. A fifteenth dying case. Five unkillable clauses, two of
them inside the three-line helper this commit added.
