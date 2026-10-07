# Round 3, Claude half — `check-main-drivable.py` on branch `d2-main-drivable`

Subject: `HEAD` = `5f33e0b9` (round 2's fold) plus the **uncommitted/staged** round-3 changes
(`git diff --cached` across `check-main-drivable.py`, `check-plan-code.py`,
`check-fixture-variation.py`, `scripts/mutations/check-main-drivable.json`).

**Verdict: NOT CONVERGED — and THRASHING.** Round 3's Medium fix flipped **six** fixtures from
*refused* to *credited* against `HEAD`, in exactly the vocabulary round 2 added. The two
re-statements round 3 made specifically to end the spelling game — "the repair is the RECURSION …
a rule reached by recursion has no third spelling" and "Python already enumerates the whole: every
rebinding puts the name in a STORE context" — are **both false**, and I falsified each by running
fixtures, not by reading.

---

## What I executed vs only read

### Executed

| Command | Result |
|---|---|
| `python3 scripts/check-main-drivable.py --self-test` | `188/188 passed`, rc 0 |
| `python3 scripts/check-main-drivable.py --report` | 44 guards · 7 without `main()` · 37 in population · 10 compliant (param 2, argv 3, rebind 8, subproc 1) · 27 pinned |
| `partial-sweep.py scripts/check-main-drivable.py` | **66 entries, control GREEN, after-control GREEN, all 66 red via the case each names**, 5.1 min |
| **Instrumented `_element_is_constructed`** over all 44 guards, printing every credited expression + line | credited-call-site audit for all 10 compliant guards (table below) |
| **Instrumented `live_substitutions`/`global_writes`** for every REBIND credit | 6 guards, 14 credited substitutions, each named |
| **Pinned-set derivation**: every `main(` call in each of the 27 pinned files, reachable or not | all 27 have **exactly one** `main(` call in the whole file — the `__main__` dispatch |
| **20 severances**, one at a time, in a `copytree` of `scripts/` under a temp dir | control green; **10 GREEN severances** (table below) |
| **~55 synthetic `classify()` probes** against three builds: the worktree, `HEAD`, and `840a7b43` (round 0) | the differential that classifies each finding (a)/(b)/(c) |
| Claim re-derivation from the manifests and `EXPECTED_MUTATIONS` by script | all six claims re-derive (table below) |
| `git status --porcelain` before and after | identical; nothing committed, staged, unstaged or reverted |

### Only read

`git show HEAD`; `docs/reviews/codex/main-drivable-r3-codex.md`; both round-2 halves;
`docs/adr/0014-a-guards-main-is-drivable.md`. I did **not** run the repo-wide `--mutate .` (the
partial sweep plus `EXPECTED_MUTATIONS` arithmetic is what I measured instead), and I did not run
the other 57 guards' suites.

⚠ All probing was done on **copies** in my scratchpad, never on the repo tree. The one thing I
touched in-repo is this file.

---

## B1 — Blocking. The live world behind a local name is credited whenever it wears a wrapper that is not a bare `Name` or an `Attribute`-on-`Name`. Round 3 closed ONE spelling and opened SIX.

**(a) The observation that would make this FAIL:** a guard whose only `main()` call hands it the
live repository — `os.getcwd()`, `str(ROOT)`, `Path(__file__)`, `sys.argv` — bound to a local
first and then wrapped in anything at all, is reported as COMPLIANT. That is the gate's only
false-green failure mode.

**(b) The code.** `scripts/check-main-drivable.py:1037-1067` — the recursion is reached from
exactly two node kinds:

```python
    if reads_the_live_world(el, set(guard_globals), case_locals(fn)):      # :1036
        return False
    if isinstance(el, ast.Name):                                          # :1038
        ...
        return _element_is_constructed(value, fn, tree, depth, guard_globals, onward)   # :1064
    if isinstance(el, ast.Attribute):                                     # :1069
        ...
    return True                                                           # :1074
```

Every other expression kind falls to `return True` at `:1074` **without recursing into its
children**, and the only thing that was supposed to stop it — `reads_the_live_world` — is now
blinded by `names = names - locals_` at `:978`, which strips exactly the local that holds the live
world.

**Measured, 17 spellings credited over the live world** (all `-> ['param']` or `['argv']`, every
one of which must be `[]`):

```
p = os.getcwd()   ; main([], root=str(p))            -> param
p = os.getcwd()   ; main([], root=Path(p))           -> param
p = os.getcwd()   ; main([], root=Path(p).parent)    -> param
p = os.getcwd()   ; main([], root=p + '/x')          -> param     (BinOp)
p = os.getcwd()   ; main([], root=f'{p}/x')          -> param     (JoinedStr)
p = sys.argv      ; main([], root=p[0])              -> param     (Subscript)
p = os.getcwd()   ; main([str(p)])                   -> argv
p = str(ROOT)     ; main([], root=str(p))            -> param
p = Path(__file__); main([], root=str(p))            -> param
p = os.getcwd()   ; main([], root=[p][0])            -> param
p = os.getcwd()   ; main([], root=(lambda: p)())     -> param     (Lambda + Call)
p = os.getcwd()   ; main([], root=dict(a=p)['a'])    -> param
p = os.getcwd()   ; main([], root=-p)                -> param     (UnaryOp)
p = os.getcwd()   ; main([], root=(p,)[0])           -> param
p = os.getcwd()   ; main([], root=p if 1 else p)     -> param     (IfExp)
p = os.getcwd()   ; main([], root=next(iter([p])))   -> param
p = os.getcwd()   ; _dr([], str(p))                  -> param     (through the helper hop)
```

Controls that correctly stay refused: `root=str(ROOT)`, `root=str(os.getcwd())`, `root=p` with
`p = os.getcwd()`. Controls that correctly keep credit: `root=str(td)` with `td = tempfile.mkdtemp()`,
`root=home` with `home = tempfile.mkdtemp()`.

**(d) Classification — this is the part that decides the round.** I ran the same fixtures against
`HEAD` (round 2's fold) and `840a7b43` (round 0). The generic-name spellings are **(b)
PRE-EXISTING** — identical at all three builds, which means round 3's Blocking fix closed
**one of eighteen**. But for the three names round 2 added to `LIVE_WORLD_READERS`, round 3 is
**(a) INTRODUCED BY A ROUND-3 FIX**, and strictly regressive:

| fixture | `HEAD` (round 2) | worktree (round 3) |
|---|---|---|
| `cwd = os.getcwd() ; main([], root=str(cwd))` | `[]` refused | **`['param']`** |
| `cwd = os.getcwd() ; main([], root=Path(cwd).parent)` | `[]` refused | **`['param']`** |
| `home = os.getcwd() ; main([], root=str(home))` | `[]` refused | **`['param']`** |
| `home = os.getcwd() ; main([], root=Path(home).parent)` | `[]` refused | **`['param']`** |
| `argv = os.getcwd() ; main([], root=str(argv))` | `[]` refused | **`['param']`** |
| `argv = os.getcwd() ; main([], root=Path(argv).parent)` | `[]` refused | **`['param']`** |

Round 3 answered a **lost-credit Medium** by deleting the only test that saw those six, and the
commit text records the Medium as "the safe direction".

**⚠ And this is not a synthetic hole.** My credited-call-site audit shows the un-recursed
`return True` at `:1074` is the **dominant** credit route in this repo — 17 of the 19 element
credits across the 10 compliant guards go through it:

| guard | route | credited expression (all verified genuine) |
|---|---|---|
| `check-fixture-variation.py` | argv | `str(_f)`, `str(_clean)`, `str(_fl)`, `str(_nf)`, `str(_new)`, `str(_bad)`, `str(_lf)`, `str(_lf2)`, `str(_mf)`, `str(_pf)` ×2 — **all `Call`, none recursed** |
| `check-plan-code.py` | argv | `str(g)`, `str(_r)`, `str(_r7)`, `str(root)` — **all `Call`** |
| `check-main-drivable.py` | argv+param+rebind | `world` (Name, recursed), `str(world / 'scripts/check-a.py')`, `str(world / 'scripts/absent.py')`, `str(bad)` |
| `check-selection-card.py` | subproc | `raw if isinstance(raw, bytes) else raw.encode()` (IfExp), `data` |
| `check-ci-watched.py` | param+rebind | `stream`, resolved at its call site |

So the rule's live behaviour rests on the branch that asserts nothing. `str(_f)` is credited for
the same reason `str(p)` is: not because the guard decided `_f` was built, but because it stopped
looking.

**(c) Fix — a hypothesis.** Invert the default: `return True` at `:1074` becomes
`return any(_element_is_constructed(child, fn, tree, depth, guard_globals, seen) for child in
ast.iter_child_nodes(el)) or <no-child case>`, i.e. an expression is constructed when *some leaf
it rests on* is, and a wrapper is transparent. That makes the property hold at every level by
construction rather than at the two levels someone enumerated. ⚠ I have NOT measured what it does
to the 10 current credits — `str(_f)` must stay green and I would expect it to, but the honest
statement is that this hypothesis needs the sweep plus a re-`--report` before anyone believes it.

---

## H1 — High. `case_locals` crosses function-scope boundaries, so a nested `def`'s local shadows `__file__` and the guard's own globals for the OUTER case.

**(a) FAIL observation:** a case containing any nested helper that happens to bind a name is
credited for handing `main` the live repository under that name.

**(b) The code.** `scripts/check-main-drivable.py:1003-1009` — `ast.walk(fn)` descends into nested
`FunctionDef`s, and a Store `Name` in an inner scope is added to the outer case's local set:

```python
    for node in ast.walk(fn):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            out.add(node.id)
```

Measured, both `[]` at `HEAD` and credited now:

```python
def _self_test():
    def helper():
        __file__ = 1            # an inner-scope local; the OUTER __file__ is the module's
    case('x', main([], root=Path(__file__).parent), 0)      # -> ['param']
```

```python
def _self_test():
    def helper():
        ROOT = tempfile.mkdtemp()
    case('x', main([], root=ROOT), 0)                       # -> ['param']
```

The first fixture is **round 2's Blocking verbatim** — `main([], root=Path(__file__).parent)` —
re-admitted by round 3's Medium. The second hands `main` the guard's own global.

**(d) (a) INTRODUCED BY A ROUND-3 FIX.** `case_locals` did not exist at `HEAD`; both fixtures were
refused there.

**(c) Fix — a hypothesis.** `case_locals` should not walk into a nested `FunctionDef`,
`AsyncFunctionDef`, `Lambda` or `ClassDef` body — collect from `fn`'s own scope only, the way
Python's symbol table does. Mirror it in `globals_aliases` (see M2, which is the same bug pointing
the other way).

---

## H2 — High. The Store-context rule is NOT Python's whole enumeration. `del g` and a `match` capture pattern both rebind without a Store `Name`.

**(a) FAIL observation:** a case writes through an alias that no longer names the module globals,
and the write is credited as a live substitution — round 1's Blocking, re-opened.

**(b) The code and the claim.** `scripts/check-main-drivable.py:525-535` asserts exhaustiveness:

```python
    Three rounds, three lists, and the third list was still incomplete — which is the tell that the
    subject was wrong. **Python already enumerates the whole: every rebinding puts the name in a
    STORE context.**
```

It does not. Measured — both `-> ['rebind']`, both must be `[]`:

```python
g = globals(); del g;                       g['X'] = 2     # ast.Name(ctx=Del), not Store
g = globals()
match 1:
    case {'k': g}: pass                                    # MatchMapping/MatchAs bind via a
g['X'] = 2                                                 #   plain `str` field — no Name node
```

`del` unbinds (the subsequent write is a `NameError`); PEP 634 capture patterns bind through
`ast.MatchAs.name` / `MatchMapping.rest`, which are `str`s, not `Name` nodes. So the class rule
misses two of Python's binding forms.

**Credit where it is due, measured:** at `HEAD` the clause list missed **five** forms — `del`,
`g |= {}`, `match`, `g: dict = {}`, `g: dict`. Round 3's single rule closed **three** of them
(both `AnnAssign` forms and the `AugAssign`) and left two. The rule is a real improvement over
three enumerated lists. It is just not the complete enumeration the comment claims.

**(d) (b) PRE-EXISTING** for the two surviving spellings — both were also missed at `HEAD` and at
round 0. **(a)** for the *exhaustiveness claim*, which is new in round 3 and is what a future
reader will rely on instead of re-deriving.

**(c) Fix — a hypothesis.** Either add `ast.Del` context and the `match`-pattern binders to the
rebinding scan (back to a list, honestly labelled as one), or — better — stop hand-rolling it:
`symtable.symtable(src, "<g>", "exec")` gives the bindings of each scope from CPython's own
symbol table, which is the enumeration the comment wants to be citing and also fixes H1 and M2.

---

## M1 — Medium. Ten green severances. Round 3's Medium removed the last observer of the `cwd`/`home` vocabulary round 2 added.

**(a) FAIL observation:** the rule is deleted and `188/188` still passes — the code is load-bearing
for a verdict no case asserts.

**(b) Measured.** 20 severances applied one at a time to a `copytree` of `scripts/`, control green
at `188/188`:

| severance | result |
|---|---|
| `case_locals`: drop vararg/kwarg | **GREEN** |
| `case_locals`: drop `except … as` | **GREEN** |
| `case_locals`: drop the dotted-import head `.split(".")[0]` | **GREEN** |
| `globals_aliases`: drop the dotted-import head `.split(".")[0]` | **GREEN** |
| `globals_aliases`: drop the WALRUS binding clause (`NamedExpr` → `bound`) | **GREEN** |
| `_element_is_constructed`: drop the `List`/`Tuple` element walk | **GREEN** |
| `_element_is_constructed`: a resolved `Constant` stops being refused | **GREEN** |
| `_element_is_constructed`: `Attribute` branch stops forwarding `seen` | **GREEN** |
| **`LIVE_WORLD_READERS`: drop `cwd` and `home`** | **GREEN** |
| `_param_index`: drop `posonlyargs` | **GREEN** |
| the other 10 (incl. all four round-3 rules the manifest names, `__file__`, `from_globals`, the unresolvable-name refusal) | red, 1–8 cases each |

Two deserve separate reading:

- **`LIVE_WORLD_READERS` losing `cwd` and `home` is green** — and those two names were added by
  round 2 *for* the refusal direction. Round 3's Medium then made the only cases that mention them
  the *shadowed* ones (`home = tempfile.mkdtemp()`), which pass either way. So round 3 converted a
  round-2 rule into unfalsifiable code. **(a) INTRODUCED BY A ROUND-3 FIX.**
- **`isinstance(value, ast.Constant): return False` at `:1057` is now dead**, subsumed by round 3's
  recursion (a `Constant` is refused at `:1033`). Harmless duplication, but it is a second copy of
  one rule — `a-second-implementation-of-one-rule-drifts`, 17 measured instances in this repo.

The other eight are **(b) PRE-EXISTING**.

**(c) Fix — a hypothesis.** Three of the ten (`case_locals` `except`/vararg, the walrus clause) are
one-line manifest entries. `cwd`/`home` needs a *refusal* case that is not shadowed. The
`List`/`Tuple` walk and the dead `Constant` clause should be **deleted**, not covered — a rule with
no reachable behaviour is better removed than pinned.

---

## M2 — Medium. `globals_aliases` over-claims across the same scope boundary H1 under-claims across.

**(a) FAIL observation:** a compliant guard is pinned as debt because an unrelated nested helper
binds the same letter.

**(b) The code.** `scripts/check-main-drivable.py:545-553`, same `ast.walk(fn)`. Measured — this
is credited `[]` when it should be `['rebind']`:

```python
def _self_test():
    g = globals()
    def h():
        g = {}              # an INNER scope's local; the outer `g` is untouched
    g['X'] = 2
    case('x', main([]), 0)  # -> []  (the alias was killed by a different scope)
```

The direction is safe — a lost credit, as the docstring claims for the whole-case judgement — but
it is the *same defect as H1*, and H1's direction is a false green. One fix closes both.

**(d) (b) PRE-EXISTING** — `[]` at `HEAD` too.

---

## L1 — Low. The fourth dying case was repaired in the FIXTURE, not in `classify`, so `classify` still has a crash path its own contract denies.

**(a) FAIL observation:** `classify` raises instead of returning a `Verdict`, so the gate exits with
a traceback rather than a `CANNOT RUN`.

**(b) The code.** `Verdict.error` is documented at `:173` as *"unparseable -> fail closed, never
silently pinned"*, and `classify` catches only `SyntaxError` (`:1090`). `main` catches only
`OSError` (`:1246`). Round 3's repair for the `RecursionError` went into the **suite**:

```python
    try:
        _cycle_routes = classify(_CYCLE).routes
    except RecursionError:
        _cycle_routes = "RAISED RecursionError"
```

Measured against the real function:

```
   depth   900: routes=['param']  error=None
   depth  1200: classify() RAISED RecursionError   — not fail-closed
   depth  3000: classify() RAISED RecursionError
```

I could not reach it from a plausible guard source (a 1200-deep name chain), and the three cycle
shapes I tried all terminate correctly (`p=q.x;q=p.y`, `p=[q];q=[p]`, `p=str(q);q=str(p)`, `p=p.x`,
600-deep attribute chain, 400-deep nested list — none hangs, none raises). So: Low.

**(d) (a) INTRODUCED BY A ROUND-3 FIX** — the recursion is round 3's, and the handler it needed was
put in the test. The shape matters more than the severity: mutation 60 severs the cycle guard, and
the case only survives to report because *the case itself* wraps the call. The gate would die.

**(c) Fix — a hypothesis.** Wrap `classify`'s body in `except RecursionError` and return
`Verdict(..., error="resolution too deep")`, so the contract at `:173` is true for every input
rather than for `SyntaxError` alone; then the fixture's `try` can go.

---

## What I tried to refute and could NOT

1. **Is any of the 10 compliant guards a false green?** *No — I could not find one.* I instrumented
   `_element_is_constructed` and printed every credited expression with its line, then opened all
   19 sites plus the 14 REBIND substitutions. Every credited world is a real `tempfile`/`StringIO`
   the case built (`check-fixture-variation.py:1469` `str(_f)`, `check-plan-code.py:2914`
   `str(root)` inside `_mutate_output`, `check-main-drivable.py:2239` `world = Path(td)`,
   `check-ci-watched.py:713` `stream` resolved at its call site,
   `check-selection-card.py:453` where `input=data` *is* `main`'s whole world). The three guards
   credited only for substituting their own `_self_test`/`self_test`
   (`check-ratchet-contract.py:980`, `check-rc-contract.py:781-782`,
   `check-surface-recall.py:721-722`) do observe a real wiring property — main's dispatch line — and
   each has a second, independent credit. **B1 is a live hole in the rule, not yet a live false
   green in the report.**
2. **Is any of the 27 pinned guards actually compliant?** *No.* Derived rather than eyeballed: all
   27 contain **exactly one** `main(` call in the entire file, and in every case it is the
   `if __name__ == "__main__"` dispatch (`main()` or `main(sys.argv[1:])`). There is nothing for the
   rule to have missed. The debt figure of 27 is sound.
3. **Do all 66 mutations bind and go red through the case each names?** *Yes.* `partial-sweep.py`:
   control GREEN, 66/66 red via the named case, **after-control GREEN**, 5.1 min. Independently,
   0 of 66 manifest anchors fail to bind to the current script and 0 bind mid-line.
4. **Claims vs code in the uncommitted diff — all six re-derive.**

   | claim | re-derived |
   |---|---|
   | "188 cases" | `188/188 passed` ✅ |
   | "66 mutations" | manifest has 66 entries; `EXPECTED_MUTATIONS["scripts/check-main-drivable.py"] == 66` ✅ |
   | "EIGHT added and THREE RETIRED" | by name-set: 8 added, 3 removed (`for`-loop target, walrus, `with … as g`), 58 kept; 61+8−3=66 ✅ |
   | "1239 -> 1244" | `sum(EXPECTED_MUTATIONS.values()) == 1244` over 58 files ✅ |
   | "6 absent and 1 present-but-mid-line of 40" | `HEAD^`'s manifest = 40 entries/40 anchors vs `HEAD`'s script: **6 absent** (entries 1, 22, 27, 28, 29, 35) and **1 mid-line** (entry 20) ✅ — the correction of round 2's "TWELVE" is itself correct |
   | "five spellings" | 5 forms in the docstring, 5 cases in the suite, 1 mutation entry ✅ |
   | "10 of 37" | `--report`: 37 in population, 10 compliant, 27 pinned ✅ |

   This fold orphaned **7 of 61** anchors (3 retired with their subject + 4 retargeted). The 4
   retargets are not mentioned anywhere; the manifest is nonetheless consistent, so this is an
   observation, not a finding.
5. **The brief's remaining enumerated shapes are safe:** a class attribute at module level
   (`class C: p = os.getcwd()` → `main([], root=C.p)` → `[]`), a helper's **default argument**
   (`def _dr(args, world=os.getcwd())` → `[]`), a helper parameter resolved at a call site from a
   bare live-world local (`_dr([], p)` with `p = os.getcwd()` → `[]`), and a comprehension as the
   argv expression. Only the *wrapped* forms leak, which is B1.

---

## Thrashing or prose floor?

**Thrashing, and the evidence is arithmetic rather than rhetorical.** This is not a document that
can be polished forever — the subject is a gate whose verdicts I can measure, and the measurement
says round 3 went backwards. Six fixtures that `HEAD` refused are credited now, every one of them
the live repository handed to `main`, all six caused by the one line round 3 added
(`names = names - locals_` at `:978`); and the fix for the Blocking closed exactly one spelling of
the eighteen I found in under ten minutes. Netting those: **−1 defect, +6 defects, plus two false
credits from a function that did not exist at `HEAD` (H1), plus one round-2 rule converted into
unfalsifiable code (M1).** Together with round 3's own half — whose Medium is classified (a) by
Codex and whose Blocking is round 2's fix one assignment away — that is two consecutive rounds
carrying findings caused by the previous round's own fix, in one component. **The project's
arming condition for a scoped architecture review is met.**

**Do I believe the two re-statements? No, and I did not have to argue about it.**

- *"The repair is the RECURSION … a rule reached by recursion has no third spelling."* **False.**
  The recursion is reached from two of roughly ten expression kinds; `return True` at
  `:1074` is the default for all the others, and it never looks at a child. There were seventeen
  further spellings, and — the part that should decide this — **the un-recursed branch is the route
  17 of the 19 live credits in this repo actually take**. The sentence describes a property the code
  asserts along one path and abandons on the rest.
- *"Python already enumerates the whole: every rebinding puts the name in a STORE context."*
  **False.** `del g` binds in a `Del` context and `match … case {'k': g}` binds through a plain
  `str` field with no `Name` node at all. The *intent* — stop enumerating, delegate to the
  language — is exactly right; the execution picked the wrong delegate. `symtable` is the delegate
  that would have been true.

**The observation that would show my verdict wrong:** take the B1 fixture table and the H1 pair,
re-run them against a build in which `:1074` recurses into child nodes and `case_locals` stops
crossing scopes, and find that (i) all nineteen go to `[]`, (ii) `--report` still says 10
compliant with the same 19 credited expressions, and (iii) the sweep stays 66/66 with a green
after-control. If one structural change closes a class I needed seventeen fixtures to describe and
costs nothing in credit, then the subject was tractable all along and these rounds were paying off.
Conversely, if round 4 fixes these seven findings by naming `BinOp`, `JoinedStr`, `Subscript`,
`IfExp`, `Lambda`, `del` and `match` one at a time, round 5 will find the eighth, and the
architecture review should decide whether this rule should be an AST pattern-match at all rather
than a hand-rolled abstract interpreter — the question `gates-detect-defects-not-design` exists
for, and the one per-task review is structurally unable to ask.

---

## NOT CONVERGED

Per-finding classification: **B1 Blocking — (b) for 11 spellings, (a) for 6; H1 High — (a);
H2 High — (b) defect / (a) claim; M1 Medium — (a) for the `cwd`/`home` severance, (b) for 9;
M2 Medium — (b); L1 Low — (a).**

Working tree and index left exactly as found (`git status --porcelain` identical before and after;
four staged modifications, four untracked files, nothing by me but this review).
