# D2 `check-main-drivable.py` — adversarial review, round 2 (Claude half)

Subject: branch `d2-main-drivable` — `git show HEAD` (the round-1 fold) **plus the uncommitted
working tree**, which is the round-2 fold. Mandate: refute, attack the FIXES.

---

## What I executed, vs what I only read

**Executed**

| Command / experiment | Result |
|---|---|
| `python3 scripts/check-main-drivable.py --self-test` | `148/148 passed`, rc 0 |
| `python3 scripts/check-main-drivable.py --report` | 44 on disk · 7 without `main()` · 37 in population · 10 compliant · 27 pinned · param 3, argv 3, rebind 8, subproc 1 |
| `python3 scripts/check-main-drivable.py` (gate) | rc 0, `D2 OK` |
| `partial-sweep.py scripts/check-main-drivable.py` | control green in 4s; **all 49 entries red via the case each names**; after-control green; 2.8 min |
| `--self-test` + gate on `check-fixture-variation`, `check-selftest-counts`, `check-ratchet-contract`, `check-guard-coverage` | all rc 0 (67/67, 18/18, 56/56) |
| **Synthetic classification probes** — 30 fixtures through `classify()` across all four routes | findings B1, H1, H2, M3 below |
| **Severance, 15 rules, one at a time, in a repo-shaped staged tree** | **12 stay GREEN** (H4) |
| **Credited-call-site audit** — every call site of all 10 compliant guards, printed with its route and its granting substitution | no live false credit found |
| **Pinned-set audit** — all 27, their `main()` call sites, and a scan for `mock.patch` / `monkeypatch` / `setattr` / `sys.modules[...]=` / `os.environ[...]=` / `with … as <world>` / `chdir` / self-subprocess / `import_module` | **no fifth compliant guard** |
| **Claim re-derivation** — 148, `10 of 37`, route split, 27, `163`, `0 of 44`, `twelve guards`, `35 cases`, `40 → 49`, `1218 → 1227` | two wrong (M2, L2); the rest confirmed |
| **Rebind-distance measurement** — every rebind credit on every live guard, with the distance to its granting substitution | max 27 lines; no far-stale credit |
| **`world_names` leak measurement** — `world` with and without traversing into the suite entry, per guard | L1 |
| **Dying-case experiments** — a pinned guard deleted from the population; a guard made unparseable | one new dying case (M1) |

**Only read**: `docs/adr/0014-a-guards-main-is-drivable.md`, both round-1 reviews,
`docs/reviews/codex/main-drivable-r2-codex.md`, `scripts/mutations/check-main-drivable.json` (all 49
entries, incl. a duplicate-anchor check over every `(file, find)` pair — none duplicated).

**Not run**: repo-wide `check-plan-code.py --mutate .` (the partial sweep is its 49-entry subset for
this file).

⚠ **My first severance harness was invalid and I am recording it rather than hiding it.** I ran the
severed copies from a bare temp directory, so `live_root = Path(__file__).resolve().parent.parent`
pointed at the temp root and `case("this guard is on disk", …)` failed in **every** run — ten
severances read as "red" for a reason that had nothing to do with the severance. This is the repo's
own `a-case-can-pass-for-an-ambient-reason`, inverted. Restaged with a `scripts/` tree holding copies
of all 44 guards, the control goes green at 148/148 and **ten of those ten turn out to be green.**
Every severance result below is from the staged harness.

---

## Blocking

### B1 — `_element_is_constructed` answers True for any call expression, so the LIVE REPOSITORY is a "constructed world" on three of the four routes

**Observation that makes it FAIL**: `classify()` returns a non-empty `routes` for a suite whose only
`main` call hands `main` the live repo root or live process state, spelled as a call.

```
scripts/check-main-drivable.py:931
    return True
```

That is the fall-through of `_element_is_constructed`, reached by `ast.Call`, `ast.Subscript`,
`ast.Dict`, `ast.BinOp` — everything that is not a Constant, Name, Starred or Attribute. Measured,
one fixture per row, all through `classify()`:

| call site | verdict |
|---|---|
| `main([], root=ROOT)` | `[]` — correct, round 1 M1's fix |
| `main([], root=ROOT.parent)` | `[]` — correct, round 2 H2's fix |
| **`main([], root=str(ROOT))`** | **`['param']`** |
| **`main([], root=Path.cwd())`** | **`['param']`** |
| **`main([], root=Path(__file__).parent.parent)`** | **`['param']`** |
| **`main([], root=sys.argv[1])`** | **`['param']`** |
| `main(['--flag'])` | `[]` — correct, the headline discrimination |
| **`main([os.getcwd()])`** | **`['argv']`** |
| **`main([str(ROOT)])`** | **`['argv']`** |
| `…run([sys.executable, __file__], cwd=ROOT)` | `[]` — correct, round 2's Codex High |
| `…run([sys.executable, __file__], stdin=sys.stdin)` | `[]` — correct |
| **`…run([sys.executable, __file__], cwd=str(ROOT))`** | **`['subproc']`** |
| **`…run([sys.executable, __file__], cwd=os.getcwd())`** | **`['subproc']`** |
| **`…run([sys.executable, __file__], cwd=Path(__file__).parent)`** | **`['subproc']`** |
| **`…run([sys.executable, __file__], env=dict(os.environ))`** | **`['subproc']`** |
| **`…run([sys.executable, __file__], input=sys.stdin.read())`** | **`['subproc']`** |

`Path(__file__).parent.parent` **is** `ROOT` — the identical value, by the identical expression the
module computes it with at `:112`. Round 1's Claude M1 is written at `:825-828` as *"`main([], root=ROOT)`
earned it by passing the guard the SAME global it would have read anyway"*, and round 2's Codex High is
written at `:779-781` as *"a guard re-running itself over the live process state, credited for building
nothing"*. **Both fixes compare the NAME.** The shared decision point they both delegate to still says
True for the same world wearing `str()`, `Path(...)`, `dict(...)` or `[...]`. The same defect, found
twice by two reviewers, fixed twice at the call site and never at the rule — which is this repo's
`after-fixing-search-for-the-class` and `a-shim-can-fail-in-both-directions`.

This is also why **docstring limit 2 is now understated** (round-2 question 7). It says the
conservative choice's "failure direction … is MORE pinned debt rather than a guard wrongly credited"
(`:69`). Sixteen measurements say the rule has a false-credit direction too, and the limit does not
admit it.

No currently-shipped guard exploits this, so the gate is not a false green **today** — but it is the
discrimination the whole file exists for, and it is defeated by one function call.

**Proposed fix (a hypothesis)**: make the fall-through refuse rather than admit, and enumerate the
call shapes that count — a call whose own arguments resolve to something the case built
(`str(tmp)`, `Path(td) / "x"`), with `tempfile.*`, `Path(td)`, and a case-assigned name as the roots.
A call that reaches `__file__`, `sys.*`, `os.environ`, `os.getcwd`, `Path.cwd` or a module global the
case never assigned is not a constructed world, whatever wraps it. Because `_element_is_constructed`
is the one decision point for all four routes, this is a single-site change — and it needs a case per
route, not one.

---

## High

### H1 — the `globals()` alias lifetime rule sees only `ast.Assign`, so five rebinding forms kill nothing and the write is credited as a module-global substitution

**Observation that makes it FAIL**: `classify()` returns `['rebind']` for a case whose `g` is bound to
a plain local object at the line it writes through.

```
scripts/check-main-drivable.py:503
        if not isinstance(node, ast.Assign):
            continue
```

Everything after that line — including the round-2 `bound` / `rebound` split at `:521-525` — only
ever sees assignment statements. Measured, with `case('x', main([]), 0)` after each body:

| body | verdict |
|---|---|
| `g = globals(); g = {}; g['FLAG'] = 2` | `[]` — correct, the fix as shipped |
| **`g = globals(); for g in [{}]: pass; g['FLAG'] = 2`** | **`['rebind']`** |
| **`g = globals(); with open(f) as g: pass; g['FLAG'] = 2`** | **`['rebind']`** |
| **`g = globals(); (g := {}); g['FLAG'] = 2`** | **`['rebind']`** |
| **`g = globals(); try: … except Exception as g: pass; g['FLAG'] = 2`** | **`['rebind']`** |
| **`g = globals(); [0 for g in [{}]]; g['FLAG'] = 2`** | **`['rebind']`** |
| `g = globals(); g['FLAG'] = 2` | `['rebind']` — control, correct |

The comment at `:505-510` states the rule categorically — *"a name reassigned to anything else
anywhere in the case is not treated as an alias at all. Conservative — a lost credit, never a false
one"*. Five of the six ways Python rebinds a name are false credits. `ast.For`, `ast.withitem`,
`ast.NamedExpr`, `ast.ExceptHandler` and comprehension targets are all invisible to it.

**Proposed fix (a hypothesis)**: collect `rebound` from every binding form, not from `ast.Assign`
alone — walk for `ast.For`/`ast.AsyncFor` `.target`, `ast.withitem.optional_vars`,
`ast.NamedExpr.target`, `ast.ExceptHandler.name`, comprehension `.target`, `ast.AugAssign.target`,
and the parameter names of any nested function. One case per form; a single case over one form is what
produced this finding.

### H2 — `dispatches_a_suite` tests for a MENTION of the flag in any conditional, not for a dispatch, so round 2's own fixture is refused and one adjacent line restores the credit

**Observation that makes it FAIL**: `classify()` credits a file in which nothing routes `--self-test`
to the suite.

```
scripts/check-main-drivable.py:317-318
    return any(isinstance(n, (ast.If, ast.IfExp)) and _mentions_self_test(n.test)
               for n in ast.walk(tree))
```

`ast.walk(tree)` is the whole module and `_mentions_self_test` is satisfied by `"self_test" in
ast.dump(test)` (`:295`). Measured, each with `case('x', main([str(ROOT/'f')]), 0)` as its only call:

| file shape | verdict |
|---|---|
| no conditional mentioning the flag at all | `[]` — round 2's Codex fixture, correctly refused |
| **the `If` is inside `_self_test` itself** (`if '--self-test' in sys.argv: print('hi')`) | **`['argv']`** |
| **the `If` is in a function nothing calls, and only mentions the NAME** (`if 'self_test' in os.environ:`) | **`['argv']`** |
| **a module-level `IfExp` assigned to a variable** (`x = 1 if '--self-test' in sys.argv else 2`) | **`['argv']`** |

The docstring's own sentence for the rule is *"does its `--self-test` invoke main()"* (`:309`,
`:333`). A conditional that mentions the flag and routes nowhere invokes nothing, and a conditional
*inside the suite the fallback is about* is not a dispatch to it under any reading. The repair for
round 2's High tests a token's presence rather than the property, which is
`assert-the-property-not-the-mechanism`.

Two mitigations, measured and stated so this is not over-sold: **(a)** no live guard depends on the
fallback — for all 10 compliant guards `suite_entries` finds its entry via `main`'s own dispatch
branch (`only_via_fallback=[]` for every one), so no verdict on disk rests on this; **(b)** severing
the precondition's other half is also green (see H4/S15), so no case asserts either half.

**Proposed fix (a hypothesis)**: require the conditional to reach the entry — the `If`/`IfExp` must
contain a `Call` to a name in `SUITE_ENTRY_NAMES`, and must sit at module level or in `main`, not
inside the suite entry itself. The three rows above then each need a case.

### H3 — the functions the file calls PURE are order-dependent on a module-level mutable set, and the suite's own cases call them directly

**Observation that makes it FAIL**: `globals_aliases(fn)` returns a different answer for the same
`fn` depending on which file `classify()` read before it.

```
scripts/check-main-drivable.py:458
GLOBALS_ALIASED_IMPORTS: set[str] = set()
```

reassigned per file inside `classify` at `:958-959`. Measured in one process, on a fixture that never
imports `globals` under any name:

```
direct globals_aliases on a file that NEVER imported gl:  set()
after classify() of a gl-importing file:                  GLOBALS_ALIASED_IMPORTS == {'gl'}
direct globals_aliases on the SAME non-importing file:     {'g'}        <- STALE CREDIT
direct global_writes on it:                                [(10, 'FLAG', False)]
```

The section header at `:181-183` says *"every function below takes source TEXT or an AST and returns
data"*, and `globals_aliases`, `global_writes` and `_is_globals_call` each say **PURE** in their own
first line. They are not: four of them read process state that a previous call wrote.

The **gate path is protected** — `classify` resets before any analysis, and its one early return
(`:954-955`, no top-level `main`) produces an empty verdict, so I could not construct an ordering
inside `assess` that changes a verdict. The **suite is not protected**: its cases call
`globals_aliases(...)` and `global_writes(...)` directly (e.g. `:1697`, `:1704`), after cases that
call `classify`, so every one of them passes or fails partly on case order. Manifest entry 48 names
exactly this risk — *"the alias table carries the PREVIOUS file's spellings into this one"* — and its
case covers only `classify`'s reset.

**Proposed fix (a hypothesis)**: thread the alias-import set as a parameter (`globals_aliases(fn,
imported=frozenset())`, defaulted) and delete the module global, so the functions are what they claim
to be. A case that calls `globals_aliases` on a non-importing fixture **after** a `classify` of an
importing one is the falsifier.

### H4 — twelve rules added by the two folds can be severed with the suite still green

**Observation that makes it FAIL**: deleting the rule, in a repo-shaped copy, leaves
`--self-test` at rc 0 and 148/148.

Control (unsevered, staged): **green at 148/148**, so the harness is valid.

| severance | result |
|---|---|
| S1 `globals_aliases`: drop the TUPLE-target binding clause (`:517-518`) | ⚠ **GREEN** |
| S2 `subprocess_self_calls`: stop excluding `__file__`/`sys` argv elements (`:787-788`) | ⚠ **GREEN** |
| S5 `_wired`: drop the already-wired no-op guard (`:1157`) | ⚠ **GREEN** |
| S8 `_passes_extra_world`: drop the declared-arity check `len(positional) > 1` (`:829`) | ⚠ **GREEN** |
| S9 `_is_restore_value`: drop the `{**saved}` dict-display branch (`:699-701`) | ⚠ **GREEN** |
| S12 `_dead_branch_ids`: drop `ast.While` (`:398`) | ⚠ **GREEN** |
| S13 `suite_entries`: drop the `!= "main"` exclusion (`:345`) | ⚠ **GREEN** |
| S15 `dispatches_a_suite`: drop the "a suite must EXIST" precondition (`:315-316`) | ⚠ **GREEN** |
| S18 `_constructed_at_call_sites`: drop the `node.name in reachable` filter (`:877-879`) | ⚠ **GREEN** |
| S19 `subprocess_self_calls`: drop the `SPAWNERS` attribute check (`:772`) | ⚠ **GREEN** |
| S20 `_element_is_constructed`: resolve a List/Tuple value unconditionally (`:918-919`) | ⚠ **GREEN** |
| S22 `summarise`: count routes over all verdicts instead of `with_main` (`:1045`) | ⚠ **GREEN** (equivalent — not a rule) |
| S3 `_mentions_self_test`: drop the `ast.dump` substring branch | red (5) |
| S14 `note_globals_imports`: ignore `asname` | red (3) |
| S21 `classify`: drop the per-file alias-table reset | red (1) |

Round 1 found eight unasserted rules; the round-2 fold added four cases for its own four findings and
left **eleven real ones** (S22 excepted — it is a no-op, since a verdict without `main` has no
routes). Two deserve naming:

- **S8 is the positional half of round 1's Codex HIGH.** That finding is written at `:816-820` —
  *"`def main(argv=None)` driven as `main([], root=tmp)` classified `param` — a call that raises
  `TypeError` the moment it runs"*. The keyword half has a case; the positional half (`main([], tmp)`
  against a one-parameter `main`) has none. Manifest entry 2 severs the *other* direction.
- **S18 is load-bearing and I proved it.** Severed, a call site in a function the suite cannot reach
  supplies the constructed value that credits a helper:

  ```python
  def _drive(r):  return main([], root=r)
  def _never_called():  return _drive(Path('/tmp/built'))
  def _self_test():  case('x', _drive(ROOT), 0)       # unsevered [] · severed ['param']
  ```

  That is round 1's Codex Blocking — *"a dead call satisfies no part of that"* (`:355-366`) — one hop
  inside the round-1 fix for Claude M1, and nothing asserts it.

**Proposed fix (a hypothesis)**: a case per row. S8, S18, S1 and S9 are the false-credit-direction
ones and should also get manifest entries; S12, S13, S19, S20 and S2 are cheap cases; S5 is `_wired`'s
own idempotence claim.

---

## Medium

### M1 — a third case that DIES rather than reports, and it contradicts the comment four lines above it

**Observation that makes it FAIL**: with one pinned guard absent from the population, `--self-test`
exits 1 having printed **no `N/N passed` line at all**.

```
scripts/check-main-drivable.py:2008
    case("...no pinned name complies", sorted(p for p in MAIN_DEBT if live_verdicts[p].complies), [])
```

Measured — staged tree with `scripts/check-anchors.py` removed:

```
rc = 1
final line of stdout: '        want: []'
a '<n>/<n> passed' summary present: False
stderr last line: KeyError: 'scripts/check-anchors.py'
```

The preceding case *reports* the absence and does not stop, and the next line subscripts
`live_verdicts` with the very name it just reported missing. This is the same class as round 0's
`probs[0]` and round 1's unreadable-file case, now third — a case that dies attributes nothing and the
sweep cannot see which rule it was about. It also falsifies the comment at `:1942-1943`: *"the
existence of each file is its own case, so the suite SIZE cannot vary with the state of the world. A
suite whose count moves cannot be ratcheted."* When a pinned guard leaves disk the suite size does not
move — the suite never reports one. (The adjacent experiment, a guard made unparseable, is handled
correctly: rc 1, count printed.)

**Proposed fix (a hypothesis)**: `sorted(p for p in MAIN_DEBT if p in live_verdicts and
live_verdicts[p].complies)`, plus a case that stages a population missing a pinned name and asserts
the suite still prints its count.

### M2 — the module docstring's baseline is the pre-round-1 one

**Observation that makes it FAIL**: the numbers in the docstring differ from `--report`'s.

```
scripts/check-main-drivable.py:81-82
THE DEBT SET IS NOT A BASELINE OF ZERO. 29 of the 37 guards with a `main()` do not satisfy this
today — this file is in its own population and is one of the 8 that do — …
```

Measured: `--report` prints 37 in population, **10** compliant, **27** pinned, and `MAIN_DEBT` holds
27 names. The commit message re-derived both figures — *"10 of 37 guards compliant (was 8), `MAIN_DEBT`
27 (was 29)"* — and updated the frozenset and the message, not the docstring that states the baseline.
`a-document-inside-the-corpus-it-measures`: this is the one paragraph in the file whose subject is the
file's own run.

**Proposed fix (a hypothesis)**: `27 of the 37` / `one of the 10`, and a case asserting the docstring's
numbers against `summarise(...)` the way the suite already reads the declared case count from `__doc__`
at `:2012-2017` — the one number in this file that cannot drift.

### M3 — the imported-`globals()` fix reaches one of the three places that decide "is this `globals()`"

**Observation that makes it FAIL**: a write through the imported spelling earns nothing while a write
through an alias of it earns `rebind`.

```
scripts/check-main-drivable.py:549-550
            via_call = (isinstance(base, ast.Call) and isinstance(base.func, ast.Name)
                        and base.func.id == "globals" and not base.args)
```

and the same hard-coded name at `:572-573` in `_reads_global`. Only `_is_globals_call` (`:481-483`)
consults `GLOBALS_ALIASED_IMPORTS`. Measured, both files importing `from builtins import globals as gl`:

| body | verdict |
|---|---|
| `g = gl(); g['FLAG'] = 2` | `['rebind']` — the half that was fixed |
| **`gl()['FLAG'] = 2`** | **`[]`** |

Codex's round-2 Medium named both spellings; the fold's docstring at `:475-479` claims the family. The
lost-credit direction is the safe one, so this is a Medium — but three sites answering one question
with two implementations is `a-second-implementation-of-one-rule-drifts`, the defect this repo has
measured seventeen times, inside the commit that fixes an instance of it.

**Proposed fix (a hypothesis)**: route `via_call` and `_reads_global`'s subscript base through
`_is_globals_call`, so the question has one owner. A case on `gl()["X"] = 2` is the falsifier.

---

## Low

### L1 — `world_names` follows `main`'s own dispatch into the suite, so "globals `main` reads" includes everything the suite reads

`world_names` starts at `main` and pushes every module-level function name loaded inside it (`:247-248`).
Every real guard's `main` contains `return _self_test()`, so the traversal enters the suite and keeps
going. Measured, `world` with and without traversing into the suite entry:

| guard | world | production-only | suite-only names |
|---|---|---|---|
| `check-ratchet-contract.py` | 46 | 25 | **21** |
| `check-main-drivable.py` | 59 | 50 | 9 |
| `check-dashboard-entry.py` | 44 | 36 | 8 |
| `check-surface-recall.py` | 33 | 26 | 7 |
| `check-plan-file-tags.py` | 17 | 11 | 6 |

`world_names`' docstring says it is *"what makes the rebind route discriminating rather than
decorative: a case that substitutes some unrelated global and then runs `main` over the real
repository has not constructed a world"* (`:215-217`). Up to 21 of the names it admits are read only
by the suite.

**I tried to turn this into a false green and could not**: across all 8 rebind-credited guards, **zero**
credited call sites depend on a suite-only global (every one survives the narrower world). So the
rule is looser than its own sentence and no verdict rests on the looseness. Filed as a Low because the
claim is overstated, not because a guard is wrongly credited.

### L2 — "failed thirty-five of this file's own cases" is not re-derivable from the delivered tree

```
scripts/check-main-drivable.py:1143-1145
    ⛔ ROUND 2's High is that a suite the flag cannot reach invokes nothing — and the first thing
    that rule did was fail thirty-five of this file's own cases …
```

Measured: `_wired` reduced to `return src`, staged, gives **40** `[FAIL]` lines. 35 may well have been
right at 134 cases; at 148 a reader who checks gets 40. Same class as the `1,160 lines` figure round 1
corrected — `a-retrospective-number-needs-provenance`.

**Proposed fix (a hypothesis)**: say *"fails forty of this file's cases today, measured by reducing
`_wired` to the identity"*, so the number is checkable against the tree it ships in.

---

## Claims I tried to refute and could not

Reported because a reviewer that only reports hits is a biased instrument.

| claim | how I tried to break it | outcome |
|---|---|---|
| **"10 of 37 compliant"**, param 3 / argv 3 / rebind 8 / subproc 1, 27 pinned, 148 cases | `--report`, `--self-test`, and a count of `MAIN_DEBT`'s frozenset | all four exactly right |
| **No credited guard is a false green** (round-2 question 1) | printed every call site of all 10 compliant guards with its route and granting substitution, and opened each | every credit is a real constructed world; none relies on the `dispatches_a_suite` fallback |
| **No pinned guard is actually compliant** (question 2) | all 27: every one has **exactly one** `main()` call in the whole file, the `__main__` block's `sys.exit(main())` — none in a suite. Then scanned for the shapes the four routes do not model: `mock.patch`/`monkeypatch` (0 files), `os.environ[…]=`/`putenv` (0), `with … as <world>` (0), `chdir` (0), `setattr` (1, production parsing in `check-features.py`), `sys.modules[…]=` (3), self-subprocess (2) | **no fifth compliant guard.** The two `subprocess.run([sys.executable, …])` sites launch something else: `check-review-decision.py:636` runs a SIBLING guard, `check-selftest-counts.py:319` runs an arbitrary script. `subproc` correctly declines both |
| **All 49 mutations bind and go red through the case each names** (question 3) | partial sweep; plus a duplicate-anchor check over every `(file, find)` pair in the manifest | clean, control green, no shared anchor, no mid-indentation anchor, no entry that killed the suite without a `[FAIL]` |
| **"163 lines"** | read `check-dashboard-entry.py` at all three lines: `:1276 globals()["FLAG"] = _wide`, `:1282 globals()["FLAG"] = _real_flag`, `:1445 rc = main(["--base", "master"])`; 1445 − 1282 | **163**, correct |
| **"0 of 44" verdicts changed by deleting the `__main__` exclusion** | re-added the clause as a patched module and diffed `(routes, calls)` for all 44 guards | **0 of 44**, correct |
| **"the twelve guards that dispatch from the `__main__` block"** (manifest entry 42) | counted IfExp flag-test nodes (12), guards containing one (12), and guards that LOSE their suite entry if the `IfExp` branch is dropped (12, named) | **12 on all three readings**, correct |
| **`EXPECTED_MUTATIONS` 40 → 49, declared sum 1218 → 1227** | manifest length (49), the arithmetic, and `check-plan-code --self-test` | consistent; `check-selftest-counts`, `check-fixture-variation`, `check-ratchet-contract`, `check-guard-coverage` all green as gates and as suites |
| **Rebind credit is not granted at distance by a stale substitution** | printed, for every rebind credit on every live guard, the granting line and its distance to the call | max **27** lines, median 4; limit 4's generosity does not reach a real verdict |
| **Docstring limits 1, 3, 4, 5** | read each against the code; ran the gate with `paths` and with a constructed root for limit 5 | all four still true (limit 5's `(pin reconciliation SKIPPED …)` line prints on both the gate and `--report` paths). **Limit 2 is understated — see B1** |

---

## Working tree

Nothing committed, staged, pushed or left modified. Every severance and probe ran on a copy under the
scratchpad or a `tempfile.mkdtemp()` tree; each harness asserted the source was byte-identical before
exiting. `git status --porcelain` at the end is identical to its state at the start — the four
round-2 `M` entries, the two untracked PDFs, and the Codex half plus its verdict.

---

## Verdict

**NOT CONVERGED.**

One Blocking, four High, three Medium, two Low. The shape repeats round 1's lesson and sharpens it:
**seven of the ten findings are the FALSE-CREDIT direction**, and three of them (B1, H1, H2) are the
round-1 and round-2 findings' own fixes, applied to the spelling the reviewer happened to write rather
than to the property. B1 is the one to fix first — it is one `return True`, it reaches three routes,
and both of the two reviewers who have looked at this file have now filed an instance of it.

H4 is the structural one: twelve rules the suite executes and never asserts, after a round whose
headline was that it had closed eight such gaps. The pattern across both rounds is that each fold's
new rules arrive with cases for the finding that prompted them and no cases for their own edges —
which is why `--self-test` being green at 148/148 and the sweep being clean at 49/49 are both true and
neither is evidence about the rules severed in H4.
