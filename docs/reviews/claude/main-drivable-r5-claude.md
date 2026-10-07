# D2 `check-main-drivable.py` — round 5, Claude half

Tree: `19ea6fc8`, frozen throughout. `git status --porcelain` before and after: the two pre-existing
untracked PDFs, nothing else. Nothing committed, staged, pushed or reverted.

**Verdict: NOT CONVERGED.** Round 5's Codex half was right about the three things it checked and
wrong to stop there. **The falsifier lands — on a second list, and this time removing the list is
not available.** That is the condition the architecture review itself pre-committed to.

Everything below was produced by running things. The instruments:

| instrument | what it did |
|---|---|
| `partial-sweep.py` on this file | 83 entries, green control **and** after-control, 17.6 min |
| a severance driver over `cpc.stage_tree` / `run_suite_parts` | **60 rules severed one at a time**, two batches, green after-control on both |
| `sys.settrace` line tracer over `_self_test()` | which of the 563 rule statement lines the suite executes |
| `classify()` driven directly over 60+ synthetic fixtures | the world-matrix probes below |
| a credited-call-site census | all 10 compliant guards, all 27 pins, opened by hand |

Severance totals: **35 CAUGHT, 16 DEAD, 9 DIES.** The DEAD and DIES columns are the findings.

---

## The falsifier

**⛔ LANDED.** The architecture review's honest form of it, quoted from
`docs/reviews/architecture-review-2026-10-03.md:245-248`:

> **"a defect whose only fix is to extend a list, where removing the list is not available"** — the
> 2026-10-03 instance had removal available and took it. **If removal is ever unavailable, the
> subject is enumerative and this review was wrong.**

Round 4 landed it on the **node-kind** list and removal was available, so the rewrite survived.
There is a second list, and it is a **name** list: `LIVE_WORLD_READERS` at `:158-159`. Thirteen
distinct spellings of the live repository are credited as a world the case built (§Blocking B1), and
the minimal fix for every one of them is literally to add a name to that list.

**Removing it is not available.** `_expr_children` could delete its list because `ast` *enumerates
the grammar* — "descend through any non-expression node" is a derivation. Nothing enumerates
"standard-library expressions that read ambient process state"; that is a semantic fact about the
stdlib, not a grammar category. I costed the two alternatives by running them rather than arguing:

- **Invert the default** — make an unrecognised `Call` INERT instead of `BUILT` (`:1122-1123`). This
  fixes the direction, but then `tempfile.mkdtemp()`, `io.StringIO()` and `Path("/tmp/fixture")` all
  lose their credit, and those are the three exemplars the `world_class` docstring names at
  `:1115-1121` as the reason that clause exists. Affordable only if a *constructor* allowlist
  replaces the *reader* list. **The list relocates; it does not disappear.**
- **Require a case-local binding chain for BUILT.** Refuses `main([], root=tempfile.mkdtemp())`,
  which is ADR-0014's own D1 repair. Not affordable.

So the subject is irreducibly enumerative in this one dimension. Two things follow, and they are
different claims:

1. The ADR is untouched — D2 is still the right bit to measure, and I do not re-litigate it.
2. **The arch review's conclusion that "changing nothing was right / the subject is not
   enumerative" is no longer established by its own stated test**, and the review's falsifier
   section needs the correction written into it. It already carries one ⛔ box for a claim refuted
   hours later; this is the second, and unlike the first it does not have removal available as an
   escape.

For completeness, the other four lists, each probed:

| list | a world it cannot see | direction | removal available? |
|---|---|---|---|
| `LIVE_WORLD_READERS` `:158` | `Path('.')`, 12 more | **FALSE CREDIT** | **no** — §above |
| `COPIERS` `:726` | `copy.deepcopy(saved)`, 3 more | **FALSE CREDIT** | no (§High H1) |
| `SPAWNERS` `:160` | `os.system`, `os.execv`, `subprocess.getoutput` | lost credit | no, but direction is safe |
| `WORLD_KWARGS` `:161` | a `**{"input": …}` splat (`kw.arg is None`) | lost credit | no, but direction is safe |
| `SUITE_ENTRY_NAMES` `:289` | a suite dispatched from `__main__` under any other name — measured, `calls=0` and `DEBT` | lost credit | **yes** — `suite_entries`' first clause already *derives* the entry from `main`'s dispatch branch; applying the same derivation to the `__main__` conditional covers both and needs no list. `check-dashboard-entry.py`'s `_impure_self_test` is already found without it |

---

## Blocking

### B1 — `LIVE_WORLD_READERS` is the whole rule for "this is the live world", and 13 spellings of the live world are not in it

**The observation that would make it FAIL:** an expression that reads the ambient process state and
classifies `BUILT`. Measured — `classify()` over a fixture whose only `main` call is
`main([], root=<expr>)`:

| verdict | expression | what it is |
|---|---|---|
| `param` | `Path('.')` | **the current working directory** |
| `param` | `Path()` / `Path('')` | the same, two more spellings |
| `param` | `Path('.').resolve()` | resolve of a relative path reads the cwd |
| `param` | `os.getcwdb()` | `getcwd`'s bytes sibling — the list has `getcwd` and not this |
| `param` | `os.path.expandvars('$HOME/x')` | reads the environment |
| `param` | `tempfile.gettempdir()` | reads `TMPDIR` |
| `param` | `pathlib.Path(sys.path[0])` | the script's own directory |
| `param` | `Path(os.sep)` | the live filesystem root |
| `param` | `os.listdir('.')` / `os.scandir('.')` | the live cwd's contents |
| `param` | `Path(__spec__.origin)` | the guard's own file |
| `param` | `Path(sys.modules['__main__'].__file__)` | **`__file__`, laundered one hop through `sys.modules`** |
| `DEBT` | `Path.cwd()`, `os.getcwd()`, `Path(__file__)` | **controls** — these three *are* in the list |
| `param` | `Path(tempfile.mkdtemp())` | **control** — a genuinely built world |

Fourteen rows, three correct refusals, one correct credit, **thirteen false credits**. The three
correct answers are exactly the three names the list happens to contain. This is the same shape of
measurement that condemned the pre-rewrite rule — *the verdict is a function of the vocabulary, not
of the world* — relocated from the node kinds to the names.

`Path(sys.modules['__main__'].__file__)` is the sharpest: `world_class`'s very first LIVE test is
`expr.id == "__file__"` (`:1078`), and one dictionary subscript defeats it.

**file:line.** The default that turns every unrecognised reader into a credit:

```python
# scripts/check-main-drivable.py:1122-1123
    if isinstance(expr, ast.Call):
        return BUILT
```

**Blast radius.** Not a live false green: I enumerated every credited call site on disk (§Q2) and
every value substituted at every REBIND credit, and all of them are genuinely built. **Latent**,
with no case and no mutation — `scripts/mutations/check-main-drivable.json` has zero entries at
`:158`, and severing the bare-name branch (`:1101`) and the attribute branch (`:1106`) are both
CAUGHT, so the *list's membership* is guarded while its *completeness* is not.

**Fix (a hypothesis).** Two parts, and only the second is structural. (a) Add the measured names —
`getcwdb`, `expandvars`, `gettempdir`, `sep`, `listdir`, `scandir`, `path`, `origin`, `modules`, and
treat a `Path`/`PurePath` call whose arguments are all `.`/`..`/`''`/`os.sep` as LIVE. (b) Say in the
docstring what (a) is: an enumeration that will be incomplete again, with the failure direction
being a false credit — and either accept that in writing beside `world_class`'s "there is no node
list to extend" sentence, which is now false of the file, or pay for the inversion costed above.

---

## High

### H1 — a missed restore is a FALSE credit, not a lost one, and `_is_restore_value`'s docstring says the opposite

`_is_restore_value` `:729-752` ends its docstring with:

> Admitted restore shapes, deliberately narrow: the bare saved name, a shallow copy of it
> (`dict(saved)`), and a dict display that is exactly `{**saved}`. Anything else is a
> substitution — **and the failure direction of that choice is a lost credit, never a false one.**

**That sentence is inverted.** A substitution the rule *fails to see as undone* stays live for the
rest of the case, so every later `main()` call earns `rebind`. Narrowing the restore set makes the
rule *more* generous, not less.

**The observation that would make it FAIL:** a case that restores its world and then drives `main`
over the real repository, credited `rebind`. Measured, on a fixture that substitutes `globals()["X"]`
and then puts it back:

| restore spelling | verdict |
|---|---|
| `_sv` | `DEBT` ✅ control |
| `dict(_sv)` | `DEBT` ✅ control (`dict` is in `COPIERS`) |
| `{**_sv}` | `DEBT` ✅ control |
| `copy.deepcopy(_sv)` | **`rebind`** ⛔ the idiomatic spelling |
| `copy.copy(_sv)` | **`rebind`** ⛔ |
| `_sv.copy()` | **`rebind`** ⛔ the dict method |
| `dict(**_sv)` | **`rebind`** ⛔ |
| `{k: v for k, v in _sv.items()}` | **`rebind`** ⛔ |

The cause is one `isinstance`:

```python
# scripts/check-main-drivable.py:745-748
    if (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
            and value.func.id in COPIERS and len(value.args) == 1 and not value.keywords):
```

`COPIERS` contains `"copy"` and `"deepcopy"`, which are reachable **only** as bare names
(`from copy import deepcopy`). The spelling everyone actually writes — `copy.deepcopy(x)` — is an
`ast.Attribute`, so the clause refuses it. Two of the seven names in `COPIERS` are unreachable under
their normal import, and the list therefore reads as covering a case it does not cover.

**Blast radius.** Latent — grepped, no guard on disk restores through any of the five refused
spellings, and all 27 pinned guards have zero suite `main` calls (§Q3) so none can flip. No case and
no mutation: severing `len(value.args) == 1 and not value.keywords` leaves the suite **GREEN**
(`raise.restore-copiers-arity`), so the arity half of that line is unreached as well.

**Fix (a hypothesis).** Match the callee by its *tail* attribute, the way `world_class` already does
for `LIVE_WORLD_READERS` at `:1106` — one rule, one place. And correct the docstring sentence: the
failure direction of a narrow restore set is a false credit.

### H2 — REBIND asks nothing at all about the world it credits

PARAM, ARGV and SUBPROC each run the substituted value through `_element_is_constructed`. REBIND
does not:

```python
# scripts/check-main-drivable.py:1243-1244
        if live_substitutions(fn, call.lineno, writes_by_case[id(fn)], aliased) & world:
            routes.add(REBIND)
```

**The observation that would make it FAIL:** a case handed `main` the identical global it would have
read by itself, credited. Measured:

| verdict | the substitution |
|---|---|
| **`rebind`** | `globals()["ROOT"] = ROOT` — **the live world, substituted with itself** |
| **`rebind`** | `globals()["ROOT"] = __file__` |
| **`rebind`** | `globals()["ROOT"] = os.getcwd()` |
| `rebind` | `globals()["ROOT"] = "/nonexistent"` (a bare literal) |
| `rebind` | `globals()["ROOT"] = None` |
| `rebind` | `globals()["ROOT"] = tempfile.mkdtemp()` — control, correct |
| `DEBT` | no substitution — control, correct |

Six of seven worlds, one verdict. Row 1 is word-for-word the defect round 1's Claude M1 fixed for
PARAM, and `_passes_extra_world`'s docstring records the fix at `:876-878` as *"`main([], root=ROOT)`
earned it by passing the guard the SAME global it would have read anyway. **A world argument has to
be a world the case BUILT, on both routes.**"* "Both routes" meant PARAM and ARGV. REBIND was never
brought in, and the module docstring's "⛔ AND A LITERAL-ONLY `argv` EARNS NO CREDIT, WHICH IS THE
WHOLE DISCRIMINATION" is false of one of its four routes.

**⚠ And the naive symmetry fix is wrong — I checked before proposing it.** I classified every value
substituted at every REBIND credit on disk:

| guard | global | `world_class` of the substituted value |
|---|---|---|
| `check-ci-watched.py:713` | `WARN_LOG`, `SENTINEL` | `built` |
| `check-ci-watched.py:713` | `_run`, `_skip_reason` | `inert` (a lambda) |
| `check-dashboard-entry.py:1445`, `:1460` | `collect` | **`inert`** — and it is that file's ONLY credit |
| `check-rc-contract.py:747` | `ROOT`, `MATCHER`, `HOOK` | `built` |
| `check-surface-recall.py:655`, `:682`, `:705` | `DECLARED_RENDER`, `DECLARED_WITH_DETAIL` | **`live`** — and rebind is that file's ONLY route |
| `check-ratchet-contract.py:980`, `check-rc-contract.py:781` | `self_test` / `_self_test` | `inert` (a recursion stub) |

Requiring `BUILT` would send `check-dashboard-entry.py` and `check-surface-recall.py` to DEBT — and
both are legitimate: dashboard-entry substitutes the function that reads the repo with a stub lambda,
surface-recall builds a *modified copy* of the real declaration, which `_is_restore_value`'s own
docstring at `:734` calls "one of this repo's three best constructed-world blocks".

**Fix (a hypothesis).** Refuse `LIVE`, do not require `BUILT`: `world_class(value, …) is not LIVE`.
That kills rows 1–3 of the probe table and keeps all six real credits. Measured on disk before
proposing it — the only values that classify `live` are surface-recall's three, which are `live`
because they *read the global they replace in order to modify it*, so the test needs to exclude the
saved-holder names the way `_is_restore_value` already does. That is the part of this fix I have not
measured, and I am labelling it a hypothesis rather than a design.

---

## Medium

### M1 — nine more cases that DIE rather than report, and one of them is round 2's own Medium

The slice has filed eight. I severed 20 raise-prone preconditions and found **nine** more: the suite
goes red with **zero `[FAIL]` lines**, so a mutation at that line is red and unattributable — the
shape `--mutate .` refuses. Tracebacks captured in a staged tree, over a green control and a green
after-control.

| site | severance | result |
|---|---|---|
| `:1212` `if "main" not in funcs` | removed | ⛔ `[ok]=0`, `[FAIL]=0` — `KeyError: 'main'` at `:1217`, in the suite's **first** case (`:1465`). The mutation prints nothing at all |
| `:1299` `debt & set(verdicts)` → `debt` | r2's Medium re-inserted | `[ok]=184`, `[FAIL]=0` — `KeyError: 'scripts/check-gone.py'` at `:1304`. **The case that exists to catch exactly this dies before it can report** |
| `:789` `if prior and not prior[-1]` | dropped `prior and` | `[ok]=206`, `[FAIL]=0` — `IndexError` at `:789` |
| `:1171` `names.index(name) if name in names` | dropped the test | `[ok]=18`, `[FAIL]=0` — `ValueError: x not in list` |
| `:1167-1168` `_param_index`'s isinstance precondition | removed | `AttributeError` |
| `:700` `saved.get(g, set())` → `saved[g]` | — | `KeyError` |
| `:853` `if kind == "forwarded"` → `if True` | — | `KeyError` from `fwd[call.func.id]` |
| `:1205-1208` `except SyntaxError` | removed | the file's only fail-closed handler; its mutation cannot be attributed |
| `_wired` `:1437` precondition | removed | `ValueError: substring not found` (suite helper, not the rule) |

**The observation that would make each FAIL:** the mutation the ratchet would want at that line
cannot be added today, because it would report no case. ⚠ Stated honestly: none of these nine has a
manifest entry now, so `--mutate .` is not red over them — the defect is that the site is
*unmutatable*, which is how the previous eight were framed and fixed.

**Fix (a hypothesis).** The eighth dying case taught that the fix belongs at the site that RAISES,
not the site that names the rule. For `:1212` the raising site is the suite's first case; for `:1299`
it is the `pin_stale` case's own fixture. Wrap at those sites, then add the manifest entry, then let
the sweep confirm the `[FAIL]` is attributed — the order the r5 fold had to discover twice.

### M2 — four rules that change a verdict and that no case reaches

Severed in a staged tree; suite **GREEN** in all four. Then I built an input for each that the
severance flips, so these are live rules with no coverage rather than dead clauses:

| rule | input | with | severed |
|---|---|---|---|
| `:948-950` `_bound_values`' walrus branch | `if (t := tempfile.mkdtemp()): main([t])` | `argv` | **`DEBT`** |
| `:945-947` its `AnnAssign`/`AugAssign` branch | `t: str = mkdtemp()` and `t += mkdtemp()` | `argv` | **`DEBT`** |
| `:749-751` `_is_restore_value`'s `{**saved}` shape | `globals()["X"] = {**_sv}` then `main([])` | `DEBT` | **`rebind`** ⛔ false credit |
| `:1170` `_param_index`'s `posonlyargs` | `def _h(w, /): main([], root=w)` | `param` | **`DEBT`** |

The module docstring claims `_bound_values` resolves "`=`, `with … as`, `for … in`, the walrus, PEP
634 captures" — five forms. The `with`, `for`, `=` and `match` branches are each CAUGHT by a named
case; **the walrus and the annotated/augmented assignment are not**, and the line tracer confirms
`:949`, `:950` and `:947` are never executed by any of the 225 cases. The case that covers three of
the five is one list away from covering all five:

```python
# scripts/check-main-drivable.py:2441
    case("the resolver reads `with … as`, `for … in` and `=` alike",
```

Row 3 is the dangerous direction: severing it turns a legitimate restore into a substitution.

---

## Low

### L1 — six clauses that are DEAD in the strong sense

Severed; suite green **and** I could construct no input whose verdict changes — so these are
redundant, not merely uncovered. The file has deleted five clauses on exactly this evidence this
slice; these are the sixth through eleventh.

| `:157` | `LIVE_WORLD_NAMES = {"__file__"}` | **zero readers in the file.** `world_class:1078` and `subprocess_self_calls:827,839` each hardcode the string `"__file__"` instead. A constant advertising itself as the owner of "what names are the live world", owning nothing, beside three copies of its content — the second-implementation-drifts shape, pre-drift |
| `:1067-1068` | `if isinstance(expr, ast.Constant): return INERT` | provably subsumed by the shape test at `:1074` — an `ast.Constant` contains no `Name` and no `Attribute`, so it returns `INERT` two lines later by the same value |
| `:1065-1066` | the `ast.Starred` unwrap | subsumed by the generic kids descent at `:1110`. `main([*_args])` → `argv` with it and without it |
| `:968` | `return sorted(out, key=lambda t: t[0])` | `_bound_values`' only production consumer is `:1085`, which discards the lineno and does membership tests (`LIVE in classes`, `BUILT in classes`) — order-independent by construction. The docstring's "in source order" is a property nothing reads |
| `:302` | `out.setdefault(node.name, node)` | `out[node.name] = node` is green |
| `:267` | `argv_forwarders`' `or node.name == "main"` skip | `suite_main_calls` tests `node.func.id == "main"` first, so a self-registered `main` forwarder is never consulted |

### L2 — six more preconditions no case reaches, one with a latent crash

Severed; suite green. Unlike L1 I did not establish redundancy, so these are coverage gaps:

`:855` `return call.args[idx] if len(call.args) > idx else None` — green when the bound is removed,
so no case has a forwarder called with fewer arguments than it forwards; a real guard with that
shape would `IndexError` out of the gate rather than report. Also `:746` (the `COPIERS` arity, see
H1), `:354-356` (`suite_entries`' `next(…, None)` default), `:769` (`_unpack`'s length check),
`:249-250` and `:411-412` (the two `funcs.get(…) is None` continues).

---

## What I tried to refute and could not

A reviewer that only reports hits is a biased instrument, so: three of round 5's claims and the
arch review's third falsifier survived everything I aimed at them.

### Q2 — is any of the 10 compliant guards credited for a suite that cannot observe a wiring defect in its `main`? **No.**

I enumerated every credited call site programmatically (route, line, enclosing function, unparsed
call) and then opened all of them. Every one asserts something about `main`'s exit code *or* its
output, over a world the case built, and most assert both polarities:

- `check-ci-watched.py:713` — reads `WARN_LOG`'s third tab-separated field back and asserts the
  session id, at **two distinct sessions** plus a TTY-stream negative.
- `check-selection-card.py:454` — `subprocess.run([sys.executable, __file__], input=data)` and
  asserts the **exit code**, which the comment at `:446` notes is all the hook can see. Five
  distinct payloads, both polarities.
- `check-dashboard-entry.py:1445`, `:1460` — asserts `rc == 2` / `rc == 1` **and** `"NOT CHECKED"` /
  `"REFUSED"` in captured stdout.
- `check-ratchet-contract.py:941`, `:965` — asserts rc **and** that the output names the orphan and
  the rule, over two different roots, with the comment at `:934` explaining that an rc-only case
  would pass for the wrong reason.
- `check-plan-code.py:2666` — asserts the exact three `[1/1] …` stderr lines.
- `check-fixture-variation.py:1481` ff. — asserts `(rc, substring)` pairs at both polarities.
- `check-surface-recall.py:655` — asserts `(rc, out.count("✗")) == (1, 2)`, with a comment recording
  that an rc-only case *could not* tell the wiring apart.
- `check-plan-file-tags.py:335` — `_drive_main` returns `(rc, out)`; cases assert both.
- `check-rc-contract.py:747` — `_main_over` returns `(rc, out)`; asserts both plus the inert-hook
  negative.
- `check-main-drivable.py:2603`, `:2627`, `:2642`, `:2669`, `:2688` — rc plus a named substring,
  at four distinct worlds and both polarities.

### Q3 — is any of the 27 pinned guards actually compliant? **No, and the answer is structural.**

Every one of the 27 has **exactly one** textual call to `main(` in the whole file, at module level in
its `if __name__ == "__main__"` block — so `suite_main_calls` returns `[]` and `v.calls == 0` for all
27, and the verdict does not depend on any route rule. I also checked the routes the rule *cannot*
see: zero of the 27 re-launch or re-import themselves by any spelling (`sys.executable`, `runpy`,
`exec`, `import_module`, `spec_from_file_location`). The six `spec_from_file_location` calls among
them all load a *different* script. Widening the rule cannot pay a single pin; only writing a case
can.

### Q4 — do all 83 mutations bind and go red through the case each names? **Confirmed.**

`partial-sweep.py scripts/check-main-drivable.py` → green control, **all 83 entries red via the case
each names**, green after-control, 17.6 min. Separately, statically: all 83 `old` strings occur
**exactly once** in the delivered file — no orphans, no ambiguous anchors.

### Q8 — claims vs code

| claim | re-derived | how |
|---|---|---|
| 225 cases | **225** ✅ | `grep -c '^  \[ok\]'` on `--self-test`, 0 `[FAIL]` |
| 83 mutations | **83** ✅ | `len(json.load(…/check-main-drivable.json))` |
| `check-plan-code` expects 83 | **83** ✅ | `EXPECTED_MUTATIONS` read by `ast.literal_eval` |
| declared sum 1261 | **1261** ✅ | `sum(EXPECTED_MUTATIONS.values())`, 58 targets |
| 10 of 37 compliant | **10 of 37** ✅ | `--report`; 44 on disk, 7 without `main()` |
| `MAIN_DEBT` 27 | **27** ✅ | `len(MAIN_DEBT)`, and 27 = 37 − 10 |
| 5 dead clauses | **✅ as code** | `_last_assigned_value` 0 occurrences; `_is_main_guard`, `ast.stmt`, the `__main__` clause and the `seen` set survive only in comments and docstrings. The two remaining `seen: set[str]` are `world_names`' and `suite_reachable`' visited sets, not the deleted one |
| 8 dying cases | **not re-derivable** ⚠ | a count of the slice's history, not a property of the tree. What I *can* say: the eighth's fix holds (`raise.computed_argv-precondition` → CAUGHT 1, the named case), and the true total is now at least **17** (§M1) |
| 19+ orphaned anchors | **not re-derivable** ⚠ | same — a count of folds already made. All 83 anchors bind at this commit, which is the only checkable half |

### Round 5's own two findings

Both fixes hold, by the instrument that found them: `callsites.keyword-fallback` severed → CAUGHT 1,
and the `[FAIL]` is *"the hop resolves a helper's parameter supplied BY KEYWORD at the call site (r5
Medium)"* — the case it names. `raise.computed_argv-precondition` severed → CAUGHT 1 via *"...and an
opaque argv variable is not evidence of a built world"*, which is the eighth dying case's relocated
fix working at the site that raises.

### Things I probed that were already right

`_expr_children`'s grammar-category traversal held against every adversarial cell I could build —
lambda defaults, comprehension `iter`/`ifs`, keyword values, `Starred`, nested dict displays,
f-strings, subscripts, PEP 634. Severing it → CAUGHT 7, naming the r4 falsifier cases. The depth
bound, `_own_scope`'s `nonlocal` exception and its nested-def pruning, LIVE-dominance across a name's
bindings, `globals_aliases`' Store-context rule, `_unpack`'s positional split, the subprocess
world-must-be-built test, the dead-branch and `__main__` exclusions, parameter shadowing, the
suite-only-global exclusion and the `module_globals` import clause are each CAUGHT by a named case.
35 of 60 severances went red through a case that names them.

---

## Summary

| # | severity | finding |
|---|---|---|
| B1 | **Blocking** | `LIVE_WORLD_READERS` is a name list whose removal is **not available**, and 13 live-world spellings — `Path('.')` among them — are credited as built. The arch review's pre-committed falsifier fires |
| H1 | High | `_is_restore_value`'s failure direction is **inverted** — a missed restore is a false credit; `copy.deepcopy(saved)` and 4 more spellings are read as substitutions |
| H2 | High | REBIND asks nothing of the substituted value. `globals()["ROOT"] = ROOT` earns the route; 6 of 7 probed worlds give one verdict |
| M1 | Medium | **9 more dying cases**, including round 2's own Medium, and one that prints zero `[ok]` and zero `[FAIL]` |
| M2 | Medium | 4 verdict-changing rules no case reaches — the walrus and `AnnAssign`/`AugAssign` binding forms, the `{**saved}` restore, `posonlyargs` |
| L1 | Low | 6 clauses DEAD in the strong sense, `LIVE_WORLD_NAMES` (zero readers) among them |
| L2 | Low | 6 more unreached preconditions, one a latent `IndexError` on a real guard shape |

**NOT CONVERGED.**
