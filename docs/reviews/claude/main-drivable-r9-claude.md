# Round 9 — Claude adversarial half · `scripts/check-main-drivable.py`

**Subject:** `scripts/check-main-drivable.py` (ADR-0014 rule D2) · branch `d2-main-drivable` · PR #365
**Tree:** frozen at `6965ea47`
**Mandate:** REFUTE. Assume a sixth spelling of "hand `main` the world it already had" exists, and
audit `world_class` for a third clause made unreachable by the child-dominance check.

**Both assumptions landed.** The sixth spelling is round 8's own repair with one argument added; the
third unreachable clause is the one that repair lives in. They are the same finding.

---

## Verification — I could execute

```
$ python3 scripts/check-main-drivable.py --self-test | tail -1
381/381 passed                                                           (rc 0)

$ python3 scripts/check-main-drivable.py --report | tail -3
44 guards on disk · 7 without main() (outside the population) · 37 in population
  10 drive main() over a constructed world — param 3, argv 3, rebind 8, subproc 1 (a guard may take more than one route, so these need not sum)
  27 pinned as ADR-0014 identity debt
```

Both match the brief exactly.

**Green control on a staged full tree** (`cpc.stage_tree(REPO, d)` + `cpc.child_env(d)`, `$HOME`
redirected, `cwd=d`): `rc=0`, `0 [FAIL]`, `381/381 passed`. Every run below is against that control.
`scripts/` alone was not used.

**Blast radius method.** For each finding I wrote a candidate fix, loaded the shipped file and the
patched copy as two modules, and diffed `classify(...).label` over all 44 `scripts/check-*.py` on
disk. "0 of 44" below means *literally* that diff, re-run per fix, not an argument.

---

## The manifest — 155 entries, swept, all green

I could not refute target 6. Measured, not reasoned:

| check | result |
|---|---|
| every `edits[i][0]` matches the delivered file **exactly once** | 155 / 155 |
| duplicate edit-tuples (the harness refuses these) | 0 |
| entries with an empty `expect` | 0 |
| **mutation applied to a staged full tree, suite run, dies via a case its `expect` names** | **155 / 155 CAUGHT** |
| DEAD (survivor — masked by a newer clause) | 0 |
| DIES (red with zero `[FAIL]` lines — unattributed) | 0 |
| WRONG-CASE (red, but not through the named case) | 0 |

Sweep design note, because I got it wrong the first time: my first pass shared ten staged trees
across threads by `i % N` and reported two DEAD at entry 26 and 29. That is a race — a second
worker restores the pristine file under a running one — and it is the *live agent's file is not
static* hazard. I killed it and re-ran with one tree held per thread for its whole life. The re-run
is the table above; the two DEAD did not reproduce. **Do not cite the first run.**

Only observation: four anchors (entries 17, 59, 72, 130) end mid-line rather than at a newline. The
harness does not require a line boundary — it refuses only `count > 1` — so this is fragility, not
a violation. Listed as L5.

---

## Blocking

### B1 — the helper identity resolution sits BELOW the child-dominance check, so **one argument** reopens round 8's Codex Blocking, on all four routes

Round 8's Codex Blocking closed `globals()["ROOT"] = same_root()` where `def same_root(): return
ROOT` — an identity hidden behind a name. The repair was put at `:1671-1690`, which is **after**
`kids` at `:1607-1611`. A call with any argument the case built therefore answers `BUILT` at
`:1610` and the helper resolution never runs.

This is the **third** time a call-level rule in this function has been written below the rule about
its children — `relpath` (r9), the method resolution (r9), and now the clause round 9's own commit
message cites as the precedent for moving the other two.

**The observation that makes it FAIL** — fixture: `def same_root(x): return ROOT`, plus a second
helper `def same_cwd(x): return os.getcwd()`:

| call site | shipped verdict | should be |
|---|---|---|
| `globals()["ROOT"] = same_root0()` *(r8's closed shape, 0 args)* | `DEBT` ✓ | DEBT |
| `globals()["ROOT"] = same_root(td)` | **`rebind`** | DEBT |
| `main([same_root(td)])` | **`argv`** | DEBT |
| `main([], root=same_root(td))` | **`param`** | DEBT |
| `main([], root=same_cwd(td))` | **`param`** | DEBT |
| `subprocess.run([sys.executable, __file__], cwd=same_root(td))` | **`subproc`** | DEBT |
| `globals()["ROOT"] = tempfile.mkdtemp()` *(control)* | `rebind` ✓ | rebind |
| `main([], root=Path(td))` *(control)* | `param` ✓ | param |

`td = tempfile.mkdtemp()` is **discarded by the callee**. Every one of those calls hands `main` the
live `ROOT` (or the live cwd) and earns a route for it. The argument does no work except make
`kids` say `BUILT`.

`file:line` — `scripts/check-main-drivable.py:1671` (the clause), `:1607-1611` (the check that
pre-empts it), `:1586-1594` (where r9 put the sibling rule, correctly, above `kids`).

**Blast radius.** Candidate fix: hoist the helper-return resolution into the first `Call` block
beside the method resolution.
- `classify` over 44 guards on disk: **0 of 44 change verdict.**
- Staged full-tree suite under the fix: **`rc=0`, `381/381 passed`** — *no case distinguishes the
  shipped ordering from the corrected one.* The r8 fixture `_R8H` (`:3230-3237`) calls `same_root()`
  and `wrapped()` with **no arguments**, which is precisely the shape the ordering cannot affect.

**Second half, and it needs its own repair.** With the hoist applied, the three argv/param/subproc
rows go to `DEBT` — but the `rebind` row **stays credited**. `substitution_changes_the_world`
reaches `:1157` and the r8 exception "`LIVE` *with* a case-bound leaf is a world derived FROM the
live one" fires on `td`. The premise is false here: `td` is not derived into the value, it is thrown
away. Candidate fix (a call whose callee's returns are LIVE and mention none of its parameters hands
back the same world, whatever its arguments): **0 of 44**, suite **381/381**.

Deliverable. **Caused by the previous round's fix?** No — caused by round 8's, and round 9 moved two
sibling rules for this exact reason without moving this one.

---

## High

### H1 — `f"…"` defeats **every** relative-literal test in the rule

`_is_relative_literal` (`:1443`) and the ambient-literal test in the `Constant` branch (`:1504`)
both require `isinstance(expr, ast.Constant)`. An f-string with no interpolation is a `JoinedStr`
whose only element is a `Constant` — the same string by every runtime measure — and it is matched by
neither. All four relative-literal clauses read off those two tests, so all four fall together.

Measured, 9 shapes × 2 spellings, `main([], root=<expr>)`:

```
   Path('.')                        DEBT     | Path(f".")                         param
   os.path.abspath('.')             DEBT     | os.path.abspath(f".")              param
   os.listdir('.')                  DEBT     | os.listdir(f".")                   param
   Path('./x')                      DEBT     | Path(f"./x")                       param
   os.path.abspath('./x')           DEBT     | os.path.abspath(f"./x")            param
   os.listdir('./x')                DEBT     | os.listdir(f"./x")                 param
   Path('sub')                      DEBT     | Path(f"sub")                       param
   os.path.abspath('sub')           DEBT     | os.path.abspath(f"sub")            param
   os.listdir('sub')                DEBT     | os.listdir(f"sub")                 param
```

**9 of 9 flip from a correct refusal to a credit.** Add r9's own `relpath` clause:
`os.path.relpath(td, start=f"sub")` → `param`, where `start='sub'` → `DEBT`.

**On scope.** #224 parks *"here is another relative-path literal"*. This is not that, and the
distinction is the one round 8 drew correctly for `iglob`/`glob`: no list grows here. `f"sub"` is
the other half of `"sub"` — one syntactic form of the same literal, excluded by an `isinstance`
test, and the repair is derivational (a `JoinedStr` all of whose values are `Constant` **is** a
string constant). If this is still judged parked, say so explicitly; it should not be dropped
silently.

`file:line` — `:1443` (`_is_relative_literal`), `:1504` (the `Constant` branch), consumers at
`:1604`, `:1639`, `:1650`.

**Blast radius.** Candidate fix: teach `_is_relative_literal` that a constant-only `JoinedStr` is a
string literal. **0 of 44** change verdict; staged suite **381/381** — the suite is blind to it.

Deliverable. Previous round's fix? No — pre-existing, and round 9 widened its reach by adding a
fourth consumer.

---

### H2 — round 9's method resolver is a SECOND IMPLEMENTATION of round 8's helper resolver, and it has already dropped a half

`:1586-1594` re-derives "collect a callee's returns, classify them, LIVE wins". `:1671-1690` already
does that for a `Name` callee, and it carries one more rule that round 8 added as its own finding
F1: **a returned parameter resolves to its default** (`:1682-1687`). The method copy does not.

Measured on two fixtures that differ only in whether the callee is a function or a method:

| shape | verdict |
|---|---|
| `def same(p=ROOT): return p` → `globals()["ROOT"] = same()` | `DEBT` ✓ |
| `class C: def msame(self, p=ROOT): return p` → `globals()["ROOT"] = C().msame()` | **`rebind`** ✗ |
| `def gen_same(): yield ROOT` → `next(gen_same())` | `DEBT` ✓ |
| `class C: def mgen(self): yield ROOT` → `next(C().mgen())` | `DEBT` ✓ |

The yield half is in both copies; the defaults half is in one. This is the file's own most-cited
defect — *"a second implementation of a rule drifting from the first"*, which the module documents
seventeen prior instances of — occurring **inside the commit that added the second copy**, in the
same function, 95 lines apart.

`file:line` — `:1586-1594` (copy), `:1671-1690` (owner).

**Blast radius.** Candidate fix: give the method branch the same `_defaults` resolution (the
one-owner repair is to extract both into a single `_callee_returns_live`). **0 of 44**; staged suite
**381/381**.

Deliverable. **Caused by the previous round's fix — yes, directly.**

---

### H3 — the method resolver declines on an ambiguous name even when **every** candidate is LIVE, and the suite's ambiguity case is built so it cannot notice

`:1590` bails unless `len(_methods) == 1`. The comment justifies it: *"two classes sharing one
method name cannot be told apart without types, and guessing there is the false-credit direction."*
True when the candidates disagree. **When they all answer LIVE there is nothing to guess.**

```
class C: def same(self): return ROOT
class D: def same(self): return ROOT        # both LIVE
globals()['ROOT'] = C().same()   ->  rebind        (false credit)
# remove class D and the identical line     ->  DEBT  (correct)
```

The verdict turns on the existence of an unrelated class.

**Why no case caught it, and this is the instrument half.** The suite's ambiguity row at `:3266`
uses `_R9M`, whose colliding pair is `E.dup → ROOT` (LIVE) and `F.dup → tempfile.mkdtemp()` (BUILT)
— a **mixed** fixture, the one shape where declining is right. The adjacent shape where declining is
wrong has no case at all. *A forced-choice test cannot fail*: the row asserts only the polarity that
agrees with the implementation.

`file:line` — `:1586-1594`; fixture `_R9M` at `:3252-3268`.

**Blast radius.** Candidate fix: `if _methods and all(candidate resolves LIVE): return LIVE`, keeping
the `len == 1` branch below it (so the mixed row at `:3266` is unchanged). **0 of 44**; staged suite
**381/381** — including the mixed row, confirming the fix does not weaken it.

Deliverable (plus one instrument observation). **Caused by the previous round's fix — yes.**

---

## Medium

### M1 — a `@property` is not a `Call`, so no identity closure ever sees it

Six rounds of identity closures all live in the `Call` branch. `C().prop` is an `ast.Attribute`,
handled at `:1563-1569`, which falls through to `world_class(expr.value)` — and `C()` is `BUILT`.

```
class C:
    @property
    def prop(self): return ROOT

globals()['ROOT'] = C().prop     ->  rebind       (hands main the live ROOT)
```

Three characters shorter than `C().same()`, which round 9 closed. Same family as r7's *"`[subprocess][0]`
— three characters longer — walked straight back through it."*

`file:line` — `:1563`.
**Blast radius.** Candidate fix (resolve an unambiguous `@property` of the same name): **0 of 44**.
Deliverable. **Caused by the previous round's fix — yes** (it closed the method form and left the
property form, which is the same member access without parentheses).

### M2 — nested classes are invisible to the method resolver

`:1586` iterates `tree.body`, so only top-level `ClassDef`s are searched.

```
class Outer:
    class Inner:
        def deep(self): return ROOT

globals()['ROOT'] = Outer.Inner().deep()    ->  rebind
```

`_all_functions` (`:409`) already uses `ast.walk` for exactly this reason, and says so in its
docstring; the method lookup added 1200 lines later does not.

**Blast radius.** `tree.body` → `ast.walk(tree)`: **0 of 44**; staged suite **381/381**.
Deliverable. **Caused by the previous round's fix — yes.**

### M3 — a non-`Constant` key defeats both module-dict identity branches

`:1121` (`.get`) and `:1127` (subscript) require `isinstance(..., ast.Constant)` on the key. A
variable key falls through, and because the value then classifies LIVE *with a case-bound leaf* (the
key variable), `:1157`'s exception credits it.

```
k = 'ROOT'
globals()['ROOT'] = globals()[k]        ->  rebind     (globals()['ROOT'] -> DEBT)
globals()['ROOT'] = globals().get(k)    ->  rebind
globals()['ROOT'] = globals().get(f"ROOT")  ->  DEBT   (refused, for an unrelated reason)
```

False-credit direction. The safe reading is: a module-dict read whose key cannot be decided is **not**
evidence of a different world.

**Blast radius.** Candidate fix (move the `Constant` test inside the branch and answer `False` when
the key is undecidable): **0 of 44**; staged suite **381/381**.
Deliverable. **Caused by the previous round's fix — partly**: r9 added the `.get` spelling and
inherited r8's key test unchanged.

### M4 — `_dead_branch_ids` marks only the BODY of a statically-false test

`:554-557`. Round 1's Codex Blocking called `if False:` *"the cheapest possible way to fake
compliance, and the cheapest to refuse."* The `orelse` of a statically-**true** `if` is the same
branch written the other way round, and it is not refused:

```
if True:
    pass
else:
    main([str(td)])          ->  argv
if 1: pass
else: main([str(td)])        ->  argv
if False: main([str(td)])    ->  DEBT     (the closed shape)
```

⚠ **`while False: … else:` must NOT be included** — I ran it: the `else` of a `while` with a falsy
test **does execute**. The fix is `ast.If` only; a symmetric `(If, While)` repair would be wrong.

**Blast radius.** Candidate fix (`elif isinstance(node, ast.If): mark orelse`): **0 of 44**; staged
suite **381/381**.
Deliverable. Previous round's fix? No — round 1's, instance-not-class.

### M5 — the module-dict READ branches drop the `aliased` set the WRITE side receives

`_global_target_names` is handed `aliased` (`:829`), so `gl()["ROOT"] = …` is recognised as a write
when the module does `from builtins import globals as gl`. The two read branches at `:1122` and
`:1128` call `_is_globals_call(_g)` and `globals_aliases(fn)` **with the defaults** — both functions
take an `aliased` parameter and neither call passes it.

```
from builtins import globals as gl
gl()['ROOT'] = tempfile.mkdtemp()     ->  rebind   (write side: alias honoured)
gl()['ROOT'] = gl()['OTHER']          ->  DEBT     (read side: alias not honoured)
globals()['ROOT'] = globals()['OTHER'] ->  rebind  (control)
gl()['ROOT'] = gl().get('OTHER')      ->  DEBT
```

Lost credit, and the asymmetry is inside one rule. `_is_globals_call`'s own docstring: *"a rule that
recognises only the spelling its author happened to use is this repo's most-measured defect."* I
checked the false-credit direction too — `gl()['ROOT'] = gl()['ROOT']` is still refused, by
`_is_restore_value` — so this is a lost credit only.

**Blast radius.** Candidate fix (thread `aliased` into both branches): **0 of 44**.
Deliverable. **Caused by the previous round's fix — yes** for the `.get` half.

### M6 — `relpath`'s `start`: the comment states a property the code does not test, and the gap may be irreducible

`:1596-1605`. The comment is *"The question is not whether the default was overridden but whether
what overrode it is ambient."* The code tests `_start is None or _is_relative_literal(_start)` —
*is it a relative **literal***. A `start` that is relative but not a literal is credited:

```
rel = os.path.join('a', 'b')
main([], root=os.path.relpath(td, start=rel))      ->  param
main([], root=os.path.relpath(td, start=f"sub"))   ->  param     (H1's half; cleanly fixable)
main([], root=os.path.relpath(td, start='sub'))    ->  DEBT      (r9's closed shape)
main([], root=os.path.relpath(td, start=os.curdir))->  DEBT      (caught, via LIVE_WORLD_READERS)
```

I tried the repair the prose implies — *credit only an absolute literal `start`* — and it is **not
free**: staged suite `rc=1`, **379/381**, failing the two asserted rows
`os.path.relpath(mkdtemp(), start=mkdtemp())` and its positional twin, which deliberately credit a
**built** start. So the rule is knowingly generous to a built `start`, and source text cannot tell a
built-absolute from a built-relative one — the same wall as `gettempdir()` vs `mkdtemp()`. That is a
defensible price, but **it is not what the comment says**, and this file's standard for a comment
asserting a property its code does not implement is explicit. Fix the sentence, close the f-string
half under H1, and record the built-relative `start` as a stated limit beside limits 1-5.

Deliverable. **Caused by the previous round's fix — yes** (r9 wrote this clause and this sentence).

---

## Low

**L1 — `_tail` and `tail` are the same derivation, character for character, twice in one function.**
`:1576-1577` and `:1624-1625`. Round 9 added the first without reusing or hoisting. One rule, one
place; the drift risk is the file's own thesis.

**L2 — `_mentions_self_test` uses the name-contains shortcut that `suite_entries` says was rejected.**
`:428-432` tests `"self_test" in ast.dump(test)`. `suite_entries`' docstring (`:485-489`) records
that a name-contains test was *tried and REJECTED* because it admits
`discover_self_tested_nonguards` and `run_self_test`. Demonstrated: a module whose only dispatch is
`def _unrelated(no_self_test_mode): if no_self_test_mode: return _self_test()` classifies `argv`.
I scanned all 44 guards for a conditional whose test names an identifier merely *containing*
`self_test`: the only two hits are inside this guard's own source (`:464`, `:495`), and it complies
by three routes anyway — **no live false green today.**

**L3 — `NAMESPACE_READERS` includes `vars`, and no-argument `vars()` is `locals()`, not the module dict.**
`:160-168`. The set's comment claims *"`vars()["__file__"]` and `globals()["__file__"]` reach the
live module dict"*, and the ⚠ two lines below excludes `locals` because inside a function it is
*"the case's own frame — the most constructed thing in the file."* That reasoning applies verbatim
to `vars()`. Measured, Python 3.14.4, inside a function: `'__file__' in vars()` → **False**.
Direction is over-refusal (safe), so this is a false justification rather than a false green — but
the comment is load-bearing for the `locals`/`dir` exclusion sitting beside it.

**L4 — `_passes_extra_world` cannot see a world passed through `*args` or `**kwargs`**, and the
docstring's limit list does not say so. `def main(argv=None, **kw)` + `main([], root=td)` → `DEBT`;
`def main(argv=None, *rest)` + `main([], td)` → `DEBT`. Both execute fine. Lost credit — arguably
the right conservatism, since neither signature declares a world — but limits 1-5 enumerate the
other lost credits and omit this one. `:1296-1301`.

**L5 — four manifest anchors end mid-line** (entries 17, 59, 72, 130). Not a harness violation
(`check-plan-code.py:1682` refuses only `count > 1`), but *an anchor is unbound by ANY nearby edit*
has cost this repo seven orphans in one session. Instrument.

---

## What I tried to refute and could not

| attempt | result |
|---|---|
| **the 155 manifest entries** — anchors, duplicates, `expect` binding | 155/155 bind exactly once; 0 duplicate tuples; 0 empty `expect`; **155/155 die via the case their `expect` names.** No survivor, no unattributed red, no wrong-case red |
| r9's method clause is above `kids` | Confirmed correct, and **pinned by a case** (`:3262` names the ordering in its own title). `C().same()` → `DEBT` |
| r9's `relpath` clause is above `kids` | Confirmed correct and pinned (`:3170`, three rows) |
| the ordering of the other post-`kids` clauses — `CWD_CONSTRUCTORS`, the two `BASE_RELATIVE_PATH_OPS` branches, the no-args namespace union | All four require a call with no non-literal arguments, so no `BUILT`/`LIVE` child can pre-empt them. **Only the helper clause (B1) is reachable-but-pre-empted** |
| the `base = expr.args[0]` selection at `:1640` is wrong for a method call with arguments (`Path(td).glob("*.py")` takes `"*.py"` as the base) | Real, but **masked in every shape I could build** — a built receiver makes `kids` answer `BUILT` first, so `Path(td).glob("*.py")` keeps its credit and `Path("sub").glob("*.py")` is still `DEBT`. Not filed |
| `super().same()`, a `staticmethod`, a method on an instance in a local, a method colliding with a module function | All resolve correctly or over-match, and over-matching here only ever returns `LIVE`, which **refuses** a route. Safe direction |
| a method returning `self.x` | `C(ROOT).get()` → `LIVE`, caught through the receiver. The `c = C(); c.r = ROOT` form escapes, but attribute-assignment tracking is a different rule and no existing clause claims it |
| a third *spelling* reaching the module dict: `dict(globals())["ROOT"]`, `getattr(sys.modules[__name__], "ROOT")`, `vars()["ROOT"]`, `gl()["ROOT"]` | All four correctly **refused** as the same world. They are key-insensitive (so `…["OTHER"]` is a lost credit — the M5 family), but none is a false green |
| a **fourth bad deletion** among the sixteen | Could not find one. Re-ran the four riskiest: the `seen` set (a 10-deep alias chain → `INERT`, a 3-deep → `param`, a cycle → `DEBT` — the depth bound answers all three), the `Starred` unwrap, the two `is None` guards, and the `__main__` clause (a `__main__`-block call with a built element → `DEBT`, subsumption holds). The r5 pattern holds: *subsumed-by-a-later-mechanism* deletions survive |
| a **seventh masking pair** | None found. Every clause I isolated in `world_class` decides at least one input no other clause reaches |
| the live population | `--report` reproduces 10 of 37 / `MAIN_DEBT` 27; `rc=0` with no `pin_paid` / `pin_stale` / `main_not_drivable` findings |
| **every candidate fix against the 44 real guards** | **0 of 44 verdicts change, for all nine fixes.** No finding here is a live false green on a shipped guard |

---

## Deliverable or instrument, and STOP-row test

| finding | severity | deliverable / instrument | caused by the previous round's fix? |
|---|---|---|---|
| B1 helper clause below child dominance | Blocking | deliverable | no (round 8's, not extended by round 9) |
| H1 f-string defeats every relative-literal test | High | deliverable | no |
| H2 method resolver dropped the defaults half | High | deliverable | **yes** |
| H3 ambiguity declined when all candidates are LIVE | High | deliverable (+1 instrument) | **yes** |
| M1 `@property` | Medium | deliverable | **yes** |
| M2 nested classes | Medium | deliverable | **yes** |
| M3 non-`Constant` key | Medium | deliverable | **yes** (the `.get` half) |
| M4 dead `orelse` | Medium | deliverable | no (round 1's) |
| M5 `aliased` dropped on the read side | Medium | deliverable | **yes** (the `.get` half) |
| M6 `relpath` `start` comment vs code | Medium | deliverable | **yes** |
| L1 `_tail` / `tail` duplicate | Low | deliverable | **yes** |
| L2 `_mentions_self_test` substring | Low | deliverable | no |
| L3 `vars` in `NAMESPACE_READERS` | Low | deliverable | no |
| L4 `*args` / `**kwargs` world | Low | deliverable | no |
| L5 four mid-line anchors | Low | **instrument** | no |

**1 Blocking · 3 High · 6 Medium · 5 Low = 15.**
**14 deliverable, 1 instrument. 8 of 15 are the previous round's repair one step short.**

`docs/review-method.md:104` STOP row — *no Blocking or High, no finding in the deliverable, no
non-trivial fixes, everything aimed at the instrument*:

| STOP condition | met? |
|---|---|
| no Blocking or High | **no** — 1 Blocking, 3 High |
| no finding in the deliverable | **no** — 14 of 15 |
| no non-trivial fixes | **no** — B1 alone needs two clauses moved/added |
| everything aimed at the instrument | **no** — one of fifteen |

**0 of 4.**

### The thrashing question, answered rather than counted

`dev-process.md` obliges asking at four rounds. Nine rounds in, the honest answer is **not
thrashing, and not the prose floor either.** Two of round 9's three findings came from round 8's own
fixes, and eight of these fifteen come from round 9's — that is the thrashing *shape*. But the
counter-evidence is that **a redesign would remove them**: B1, H2, H3, M1, M2, L1 are all one
structural fact — *"resolve a callee's identity"* exists as **two near-copies at two different
positions relative to `kids`, with two different lookup scopes**. Extract one
`_callee_returns_live(callee, tree, world, depth)`, call it once above `kids` for `Name`, `Attribute`
and property callees, and six findings disappear together. That is a redesign the test *can a
redesign remove it?* answers yes to, which is the opposite of thrashing. The same is true of H1 and
M6: one owner for "is this a relative path literal", including the `JoinedStr` form.

What the rounds are measuring is real and the code is converging — but it is converging by
accretion, and the accretion is now the defect generator.

---

## NOT CONVERGED
