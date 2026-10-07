# Round 8 — Claude adversarial half · `scripts/check-main-drivable.py`

**Subject:** `scripts/check-main-drivable.py` (ADR-0014 rule D2) · branch `d2-main-drivable` · PR #365
**Tree:** frozen at `24199042`
**Mandate:** REFUTE. Assume a fourth spelling of "hand `main` the world it already had" exists.

## Verification — I could execute

```
$ python3 scripts/check-main-drivable.py --self-test
361/361 passed                                                    (rc 0)

$ python3 scripts/check-main-drivable.py --report | tail -3
44 guards on disk · 7 without main() (outside the population) · 37 in population
  10 drive main() over a constructed world — param 3, argv 3, rebind 8, subproc 1
  27 pinned as ADR-0014 identity debt
```

Both match the brief. **Green control on a staged full tree** (`cpc.stage_tree` + `cpc.child_env`,
`$HOME` redirected): `rc=0, 0 [FAIL], 10 credited`. Every severance below was run against that control.

### The 10 credits are real — hand-verified at source

I instrumented `classify` to print the *deciding* call site per route, then opened each one:

| guard | route | site | what I read there |
|---|---|---|---|
| `check-ci-watched.py` | param+rebind | `:713` | `main(["--decide"], stream)`; `stream` constructed at the call sites; four `g[...]` stubs + two tempdir paths live at the call |
| `check-dashboard-entry.py` | rebind | `:1445` | `g["collect"] = lambda base: ([], False, "could not run git: boom", [], [])`, restored in `finally` **after** the call |
| `check-fixture-variation.py` | argv+rebind | `:1475` / `:1481` | `EXEMPT = dict(_sv)` + an added key; `main([str(_f)])` |
| `check-main-drivable.py` | argv+param+rebind | `:3734/:3758/:3773` | `main(args, root=world)` over a built tree |
| `check-plan-code.py` | argv | `:2250` | `main([str(g), "--verify-evidence"])`, `g` a fixture path |
| `check-plan-file-tags.py` | rebind | `:335` | `ROOT, DOCS = root, docs` under `global`, restored in `finally` |
| `check-ratchet-contract.py` | param+rebind | `:941` | `main([], root=_r)` |
| `check-rc-contract.py` | rebind | `:747` | `globals()["ROOT"], globals()["MATCHER"], globals()["HOOK"] = root, m, h` |
| `check-selection-card.py` | subproc | `:454` | `subprocess.run([sys.executable, __file__], input=data)` |
| `check-surface-recall.py` | rebind | `:655` | `{**_saved_decl, 5: _saved_decl[5] + " Detail:"}` — a genuinely modified copy |

**No false green among the 44.** Everything below is therefore *latent* unless stated otherwise.

---

## Blocking

None.

---

## High

### H1 — the case-bound-leaf exception grants REBIND to values that ARE the live global, and it also swallows round 8's own `relpath` fix

`substitution_changes_the_world`, **`scripts/check-main-drivable.py:1079`**:

```python
if world_class(value, fn, tree, world) is LIVE:
    bound_here = {n.id for n in ast.walk(fn or value)
                  if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
    if not (names & bound_here):
        return False
```

The refusal is disabled by **any** case-bound name in the value. The docstring defends this as
"a world derived FROM the live one — a modified copy". But a case-bound name that is merely an
**alias of the global** adds nothing, and three rounds of identity closures (r6 bare name,
r7 twelve wrappers, r8 a module helper) all sit *above* this line and are bypassed by it.

**The observation that makes it FAIL — (a), and this is the repo's own idiom:**

```python
g = globals()
globals()["ROOT"] = g["ROOT"]        # a pure no-op
main([])
```
→ `classify` returns **`['rebind']`**. `main` is handed the object it would have resolved by itself.
`<name> = globals()` appears in **8 of the 44** guards on disk — `check-banner-armed`,
`check-ci-watched`, `check-closing-table`, `check-dashboard-entry`, `check-main-drivable`,
`check-ratchet-contract`, `check-rc-contract`, `check-surface-recall`
(`grep -lE '^\s*[a-z_]+ = globals\(\)' scripts/check-*.py | wc -l` → 8).
The hole needs only that the **write and the read use
different spellings of the module dict** — `g["ROOT"] = g["ROOT"]` and `globals()["ROOT"] =
globals()["ROOT"]` are both correctly **refused**, because then `_global_target_names` makes the
reader a holder and `_is_restore_value` catches it. Mixing the two spellings defeats both tests.

**(b), one local line:**

```python
_g = ROOT
globals()["ROOT"] = _g if True else _g   # -> ['rebind']
_g = ROOT
globals()["ROOT"] = Path("".join([str(_g)]))   # -> ['rebind']
```
The bare `globals()["ROOT"] = _g` **is** refused — but by `_is_restore_value`, not by the identity
test (measured: `_is_restore_value → True`, `substitution_changes_the_world → True`). That is a
**masking pair**; any non-index literal in the value removes the mask.

**(c) — it swallows round 8's `CWD_DEFAULTED_OPS` clause on this route.** With the clause (`:1491`)
present and with it severed to `if False:`:

| shape | with clause | clause severed |
|---|---|---|
| `globals()["ROOT"] = os.path.relpath(td)` | `('rebind',)` | `('rebind',)` |
| `main([os.path.relpath(td)])` | `()` | `('argv',)` |
| `main([], root=os.path.relpath(td))` | `()` | `('param',)` |
| `main([], root=os.path.relpath(td, start=td))` | `('param',)` | `('param',)` |

So the *same expression* is "ambient" on ARGV/PARAM and "a world the case built" on REBIND. Round 8's
Codex High was fixed on two routes of four. **Sixth masking pair.**

**Blast radius of a candidate fix.** F4 — treat a case-bound leaf whose own `world_class` is LIVE as
an alias rather than the case's own:

```python
_own = {n for n in names & bound_here
        if world_class(ast.Name(id=n, ctx=ast.Load()), fn, tree, world) is not LIVE}
if not _own:
    return False
```

| | base | F4 |
|---|---|---|
| (a) `g = globals(); globals()["ROOT"] = g["ROOT"]` | `rebind` | **`()`** |
| (b) `_g = ROOT; globals()["ROOT"] = _g if True else _g` | `rebind` | **`()`** |
| r6 bare / r7 wrapper / r8 helper identities | `()` | `()` |
| CONTROL `_g = tempfile.mkdtemp(); globals()["ROOT"] = Path(_g)` | `rebind` | `rebind` |
| CONTROL dashboard-entry stub shape | `rebind` | `rebind` |
| **all 44 guards on disk** | — | **0 verdict changes** |

Checked individually, not only in aggregate: `check-surface-recall`, `check-dashboard-entry`,
`check-ci-watched`, `check-rc-contract`, `check-fixture-variation`, `check-plan-file-tags`,
`check-ratchet-contract`, `check-main-drivable` all keep exactly their current routes under F4.

⚠ F4 does **not** close one shape I found: `Path = Path` anywhere in the case, plus
`globals()["ROOT"] = Path(str(ROOT))` → `rebind`, while the identical substitution with `_q = 1`
instead → `()`. The verdict turns on whether the case happens to store a name that also appears in
the value — the same "it turned on which local name the case picked" shape as round 7's Claude
Medium, one function over. I did not find a fix for that with zero blast radius.

- **Deliverable or instrument?** **Deliverable.**
- **Did the previous round's fix cause it?** **No** — the exception is round 5's. But round 8's
  `relpath` fix is *masked* by it, so round 8 landed a fix that does nothing on one of four routes.
- **Latent or live?** Latent — no guard on disk uses any of these shapes.

---

## Medium

### M1 — the one-hop helper resolution misses three callee shapes, all of which still earn REBIND over `ROOT`

**`scripts/check-main-drivable.py:1559-1572`.** The branch requires `isinstance(expr.func, ast.Name)`,
indexes only `_toplevel_functions`, and collects only `ast.Return`. Measured, each over a module
global `main` reads:

| shape | verdict |
|---|---|
| `def same(p=ROOT): return p` → `globals()["ROOT"] = same()` | **`['rebind']`** |
| `class _H: def same(self): return ROOT` → `globals()["ROOT"] = _H().same()` | **`['rebind']`** |
| `def same(): yield ROOT` → `globals()["ROOT"] = next(same())` | **`['rebind']`** |
| CONTROL `def same(): return ROOT` (round 8's fix) | `()` ✅ |
| CONTROL `def same(): return tempfile.mkdtemp()` | `['rebind']` ✅ |
| CONTROL conditional `if 1: return ROOT` | `()` ✅ |

Correctly refused, so the branch is not simply shallow: two-hop chains (`a() → b() → ROOT`), mutual
recursion, `async def`, a module-level `same = lambda: ROOT`, a nested helper, and
`sys.modules[__name__].same()` all come back `()`.

**Blast radius of candidate fixes** (each measured over all 44 guards):

| fix | closes | 44-guard verdict changes |
|---|---|---|
| F1 — also resolve a returned **parameter's default** | the `p=ROOT` shape | **0** |
| F3 — count `ast.Yield` / `ast.YieldFrom` as returns | the generator shape | **0** |
| (none attempted) — resolve an `Attribute` callee to a `ClassDef` method | the method shape | — |

Both F1 and F3 leave every control and every real guard unchanged.

- **Deliverable or instrument?** **Deliverable.**
- **Did the previous round's fix cause it?** **Yes, directly** — this is round 8's new clause's own
  coverage boundary.
- **Latent or live?** Latent. ⚠ I note this sits adjacent to what backlog #224 parks; I am reporting
  it because the brief commissions exactly these shapes (target 1), and because the escape is in the
  *resolution mechanism*, not in a list of ambient names.

### M2 — `BASE_RELATIVE_PATH_OPS` holds `glob` and not `iglob`: one operation, two names, opposite verdicts

**`scripts/check-main-drivable.py:238`.** The two are the same stdlib operation with different return
types, and only one is listed:

| | verdict |
|---|---|
| `main([], root=glob.glob("*.py"))` | `()` ✅ refused |
| `main([], root=glob.iglob("*.py"))` | **`('param',)`** ← identical runtime meaning, credited |
| CONTROL `glob.iglob(td)` over a built dir | `('param',)` ✅ |

The comment immediately above that set is about precisely this failure — *"round 6 removed six
NORMALISERS … and applied it to six names while five DIRECTORY READERS kept exactly the defect the
six were removed for. Instance, not class."* `iglob` is the sixth directory reader.

**Blast radius:** adding `"iglob", "rglob", "fwalk"` closes it and changes **0 of 44** verdicts; both
controls keep their credit. (`rglob` and `fwalk` are already caught when the base is a `.`/`..`
literal, via the `Constant` branch — they are listed for the class, not because I found an escape.)

⚠ **Counter-argument, stated rather than hidden:** a reviewer may read this as backlog #224's parked
"another spelling of the live repository". I am reporting it because the escape is *inside a list the
file already curated for this operation*, not a new category of ambient state — the file decided
`glob` is base-relative and then covered half of it. I did **not** report the genuinely parked
neighbours I also found (`os.path.normpath('sub')`, `os.path.isdir('sub')` — both credited `param`),
because those are new names, which is exactly what #224 parks.

- **Deliverable or instrument?** **Deliverable.** **Caused by the previous round's fix?** No —
  round 6's. **Latent or live?** Latent.

### M3 — `free_names` subtracts walrus targets without regard to scope; the oracle is right this time

**`scripts/check-main-drivable.py:928`.** The final subtraction removes every `NamedExpr` target found
by `ast.walk(value)`. PEP 572 scopes a walrus in a **lambda body** to that lambda, not to the case.
Differential test against CPython `symtable` over 23 shapes — **3 diverge, all one class:**

```
free_names=['_sv']          symtable=['_sv', 'z']     (lambda: (z := _sv))() or z
free_names=[]               symtable=['z']            (lambda: (z := 1))() or z
free_names=['_sv']          symtable=['_sv', 'z']     [(lambda: (z := 1))() for q in _sv] or z
```

**Which is wrong: the subject.** `z` outside the lambda genuinely reads the enclosing scope. The
comprehension forms agree (`[(y := q) for q in _sv] and y → ['_sv']` both ways) because there the
walrus *does* bind in the case — which is exactly why round 7's blanket subtraction looked right.

The suite's `_SHAPES` list (`:3185-3197`) contains no lambda-scoped walrus, so the r8 oracle case
cannot see this class. Adding `"(lambda: (z := _sv))() or z"` to `_SHAPES` turns that case red —
that is the concrete falsifier and the concrete repair alongside a scope-aware subtraction.

I could **not** drive this to a verdict change: in `substitution_changes_the_world` both consumers of
a shrunken `names` fail toward **refusal**, and the `_is_restore_value` path that would fail toward
credit needs the dropped name to be a saved holder read both inside and outside a lambda in one value.

- **Deliverable or instrument?** **Both** — the rule at `:928` is deliverable; `_SHAPES` is the
  instrument that cannot see it.
- **Did the previous round's fix cause it?** Round 7's fix introduced the subtraction; round 8
  repaired the *oracle* and did not re-run it against the subject's remaining scope cases.
- **Latent or live?** Latent; no verdict change found.

---

## Low

### L1 — DEAD clause: the `ast.walk` breadth of the helper branch is unfalsifiable by the suite

**`:1566`.** Severance `ast.walk(helper)` → `helper.body`:

```
DEAD (green)   S6 helper: ast.walk -> direct body only   fails=0   44-guard verdictdiff=0
```

⚠ **The mutation is not a no-op** — round 7's mistake, checked for here. Under the severance the
conditional-return control flips:

| probe | shipped | severed |
|---|---|---|
| `def same(): if 1: return ROOT` → `globals()["ROOT"] = same()` | `()` | **`('rebind',)`** |

So the breadth is behaviour-bearing and **no case exercises it**. The manifest's one entry for this
branch severs the whole `if` (`if False:`), which S5 confirms is CAUGHT; nothing pins the walk.
Repair: a case with a helper whose `return ROOT` is inside an `if`.

- **Deliverable or instrument?** **Instrument.** **Caused by the previous round's fix?** Yes — it is
  round 8's new clause, shipped with a case for its outer `if` and none for its breadth.

### L2 — DYING case: the `tree is not None` precondition in the helper branch

**`:1559`.** Removing the guard (not inverting it) — the proper "does this defensive clause have a
reachable input" severance:

```
$ python3 <staged>/scripts/check-main-drivable.py --self-test
rc=1 | [FAIL] lines: 0 | AttributeError: 'NoneType' object has no attribute 'body'
```

Red, zero `[FAIL]`, unattributed — a **seventeenth dying case**. The guard is load-bearing (a case
really does reach `world_class` with `tree=None`), so unlike the four defensive clauses this file has
shed it must stay; what is missing is a case that *reports* rather than crashes. Same remedy the
`computed_argv` precondition got in round 5 (`:1619`'s note): catch and report.

### L3 — a substitution on the SAME source line as the call is silently never credited

**`:1097`** — `prior = [... if g == name and ln < lineno]`, strict `<`. So

```python
globals()["ROOT"] = tempfile.mkdtemp(); main([])     # -> ()
globals()["ROOT"] = tempfile.mkdtemp()               # -> ['rebind']
main([])
```
— measured, both. This is the conservative
direction and is consistent with "the order is LEXICAL", but the module docstring's limit 4 and
`global_writes`'s own note both describe *branch* order, not *same-line* equality. One sentence in
`global_writes`'s docstring would close the gap between what is documented and what is enforced.
(Cost me two probe rounds before I noticed it — which is the evidence it is undocumented.)

### L4 — DEAD member: the `"\\"` half of `_is_relative_literal`'s separator test

**`:1357`** — `not expr.value.startswith(("/", "\\"))`. Severance to `startswith("/")`:

```
DEAD (green)   S16 relative-literal: drop backslash   fails=0   44-guard verdictdiff=0
```

Behaviour-bearing, checked: `main([], root=os.path.abspath("\\\\srv\\share"))` is `('param',)`
shipped and `()` with the member dropped — a false refusal of a Windows absolute literal. The one
manifest entry here severs the **whole** `startswith` test, which the `"/"` half already kills, so
the `"\\"` member is pinned by nothing. Unlike round 7's L2 (where `"./"`/`"../"` were *subsumed by a
derivation* and correctly deleted), this member is not subsumed — it is simply untested. Two honest
verdicts: add a case, or delete it and say the rule is POSIX-only.

- L2, L3, L4: **instrument / documentation.** None caused by round 8.

---

## What I tried to refute and could not

1. **A false green among the 44.** I read every deciding call site (table above). All ten credits are
   real constructed worlds. The 27 debt entries that I spot-checked are real debt.
2. **Thirteen of sixteen severances are CAUGHT**, each with a named `[FAIL]`:
   `S1` relpath clause deleted (2), `S2` arg-count bound dropped (1), `S3` `start=` test dropped (1),
   `S4` relpath clause moved *after* child dominance (2 — **the placement is tested**),
   `S5` helper branch deleted (1), `S7` `LIVE in classes` → `BUILT in classes` (2),
   `S9` `_shadowed` → `set()` (1), `S10` builtins exclusion dropped (1),
   `S11` not-rebound conjunct dropped (1), `S12` identity test deleted (13),
   `S13` live-read early return deleted (4), `S14` case-bound-leaf exception ignored (7),
   `S15` walrus subtraction deleted (1).
3. **A fourth spelling of the live repository through the helper branch's *recursion*.** Two-hop
   chains, mutual recursion, self-recursion, nested helpers, module-level lambdas, async helpers and
   `sys.modules[__name__].x()` are all refused. The depth bound does terminate every cycle I built.
4. **A stdlib path operation with a cwd-reading DEFAULT ARGUMENT other than `relpath`.** I tried
   `Path.relative_to` (no default — correctly not ambient), `glob.glob(…, root_dir=None)`,
   `os.stat`, `open`, `os.path.join`, `os.fwalk`, `Path.rglob`, `tempfile.mkstemp`. Every cwd-reading
   one is already reached through the **relative-literal base** rule or the `Constant` branch —
   `CWD_DEFAULTED_OPS` really does look like a one-member set. The escapes I found are a *missing
   sibling* in an existing list (**M2**, reported) and new names such as `os.path.normpath('sub')`
   and `os.path.isdir('sub')` (not reported — that is exactly backlog #224's parked class).
5. **The 142 manifest entries, STRUCTURALLY.** Every anchor binds **exactly once**, every anchor
   starts at a **line boundary**, there are **no duplicate entry names and no duplicate anchor texts**.
   ⛔ **The other half is NOT RUN — treat it as unverified, not as a pass.** Whether each `expect`
   names a case that *truly reddens* needs all 142 mutations applied and the suite run per entry; I
   started that sweep (green control, `rc=0 / 0 [FAIL]`) and it had not finished when I filed. It had
   reported **no problems** through the entries it reached, but a partial sweep is silence, not a
   result. Re-run before relying on it:
   `python3 scripts/check-plan-code.py --mutate .` is the owning gate.
6. **A second severance batch on OLDER clauses** — `T1` depth bound `8→100`, `T2` depth bound removed,
   `T3` the no-Name-no-Attribute shape test removed, `T4` `_constructed_at_call_sites`'s `depth > 0`
   guard removed, `T5` `_own_scope`'s `nonlocal`/`global` rescue removed: **all five CAUGHT** with a
   named `[FAIL]` and 0 verdict changes. (`T6`–`T10` — `live_substitutions`' `prior[-1]`, the
   `ln < lineno` bound, `_is_restore_value`'s index exclusion, `guard_world_globals`' `AugAssign` —
   had not completed; the `tree is not None` removal in that batch is reported above as **L2**.)
6. **`world_class`'s shadowing precedence.** A local binding is evaluated as `kids` before the Call
   branch, so a case-bound shadow of a module helper or a `LIVE_WORLD_READERS` name wins — I could not
   construct a false *credit* from shadowing, only false refusals.
7. **The oracle's own repair.** Round 8's ancestor-carrying `walk` is correct on all 23 shapes I threw
   at it, including the two it was added for. The divergences I found are the **subject's** fault.

---

## Does this round meet the STOP row?

`docs/review-method.md:104` — *no Blocking or High, no finding in the deliverable, no non-trivial
fixes, everything aimed at the instrument.*

| condition | met? |
|---|---|
| no Blocking | ✅ |
| no High | ❌ — **H1** |
| no finding in the deliverable | ❌ — **H1** and **M1** are in the deliverable; **M2** is too; **M3** straddles |
| no non-trivial fixes | ❌ — F4 and the attribute-callee half of M1 are non-trivial |
| everything aimed at the instrument | ❌ — 3 of 8 findings are in the deliverable (H1, M1, M2); M3 straddles; L1–L4 are instrument |

**The STOP row is NOT met.**

On *thrashing or prose floor?*: **M1 was caused directly by the previous round's fix** (round 8's new
clause), and **H1(c) shows round 8's other fix landing on two routes of four**. That is the second
consecutive round in which findings come from the previous round's repair, in one component
(`world_class` / `substitution_changes_the_world`). Per `docs/dev-process.md`, that is the arming
shape for a Phase 6 architecture review — **but I do not recommend convening one**, for the reason
the existing architecture review already settled: this is the leaf-provenance design working as
specified, and every finding here is a *bounded, zero-blast-radius* extension of a mechanism rather
than a redesign candidate. The test *"can a redesign remove it?"* answers **no** for H1 and M1: both
are the price of reading source text instead of observing a run, which is backlog #224, already filed.

The useful decision is narrower: **H1 has a measured fix with 0 blast radius over 44 guards and
closes the repo's own `g = globals()` idiom as a fake-compliance route. That is worth one more
round. M1's F1 and F3 are two-line changes with 0 blast radius. L1 and L2 are suite work.**

---

**NOT CONVERGED**
