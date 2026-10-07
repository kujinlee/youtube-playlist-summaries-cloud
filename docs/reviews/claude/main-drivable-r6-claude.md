# Round 6 — Claude half — `scripts/check-main-drivable.py` (branch `d2-main-drivable`, PR #365)

**Subject, pinned.** `scripts/check-main-drivable.py` at `0d326382`
("Round 6 found the Blocking's fix firing backwards, and refuted a deletion this slice had
justified in writing"). Working tree carried only the two pre-existing untracked PDFs; the subject
and its manifest were clean at that commit for the whole review.

## The gate RAN — both required commands, plus the full sweep

| Command | Result |
|---|---|
| `python3 scripts/check-main-drivable.py --self-test` | `292/292 passed`, rc 0 |
| `python3 scripts/check-main-drivable.py --report` | 44 on disk · 7 without `main()` · 37 in population · **10** compliant (param 3, argv 3, rebind 8, subproc 1) · **27** pinned |
| `python3 scripts/check-main-drivable.py` (the gate) | rc 0, `D2 OK` |
| all **116** manifest mutations, applied to the DELIVERED script in a full `stage_tree` copy | green control → **116 KILLED, 0 survived, 0 died unattributed** → green after-control |
| `python3 scripts/check-selftest-counts.py` | 51 scripts declare a count, every one verified by running it |
| `python3 scripts/check-ratchet-contract.py` | rc 0 — the guard has a caller (`.github/workflows/ci.yml:394,397`) |

Every severance below was run over a **full staged tree** (`check-plan-code.stage_tree`, `problems
== []`, `child_env`'s redirected `$HOME`) against a **green control of 292/292**. A `scripts/`-only
copy was never used.

**One reproducible script produced every classification quoted below**, so no figure here is
re-typed from a transcript: it loads the subject as a module, wraps each fixture with the subject's
own `_wired`, and prints `classify(...).label`. Its verbatim output is in
*Appendix — the evidence block*. Anything not in that block, or not shown as a severance table row,
is labelled **unverified**.

---

# Blocking

## B1 — the deleted `value.id == name` clause was neither dead nor subsumed, and a one-line identity substitution of any *import* or *def* global now earns REBIND

`scripts/check-main-drivable.py:920-923` justifies a deletion in writing:

> ⛔ A NAME TEST WAS HERE — `if value.id == name: return False` — AND IT WAS BOTH DEAD AND WRONG…
> Dead: **the rebind route only ever considers names in `world`**, so `globals()["ROOT"] = ROOT` is
> LIVE by the test below and the clause never decided anything.

**The premise is false, because there are two different sets and the sentence conflates them.** In
`classify` the rebind intersection uses `world_names(tree)` (`:1420`, `:1445`), which
`module_globals` builds from assignments **plus imports plus defs** — deliberately, for the
`globals()["subprocess"].run` case. But `substitution_changes_the_world` is handed
`guard_world_globals(tree)` (`:1423`, `:1444`), which is **assignments only**, by its own docstring:
*"`ROOT` and `MATCHER` are the world; `Path` and `tempfile` are how you build another one."* Every
global that is an import or a def is in the first set and not the second, so for all of them
`world_class(value) is LIVE` is False, the early return at `:933-934` is never reached, and the
identity substitution is recorded as changing the world.

**The observation that makes it FAIL.**

```text
B1  identity substitution of an import/def global
      DEBT     globals()['ROOT'] = ROOT                  <- module-level ASSIGNMENT, refused (documented)
      rebind   globals()['subprocess'] = subprocess      <- module-level IMPORT, CREDITED
      rebind   globals()['helper'] = helper              <- module-level DEF, CREDITED
      rebind   globals()['ROOT'] = tempfile.mkdtemp()    <- control, a real built world
```

`globals()["subprocess"] = subprocess` hands `main` the exact module it would have resolved by
itself. It is the same defect round 5's High was filed for — *"REBIND never looked at the
substituted value at all"* — surviving its own repair on two thirds of the world, because the
repair picked the wrong set.

**Blast radius — latent, with a large surface.** No guard on disk spells it: I re-derived every
rebind-crediting call site in all eight rebind guards and each substitutes something real
(`g["collect"] = lambda base: …`, `globals()["_self_test"] = lambda: 99`, `ROOT, DOCS = root, docs`,
`EXEMPT = dict(_sv)` then a fresh key, `globals()["ROOT"], globals()["MATCHER"], globals()["HOOK"] =
root, m, h`). But the attack surface is not small, and it is the **cheapest fake-compliance route
in the file**:

```text
$ # for each of the 37 guards with a main(): |world_names| vs the subset guard_world_globals misses
37 guards with a main(): 811 names in world_names(), 535 of them NOT in
guard_world_globals() -> an identity substitution of any of those 535 earns REBIND (66% of the world)
```

`_dead_branch_ids`' docstring calls `if False:` *"the cheapest possible way to fake compliance, and
the cheapest to refuse."* One line — `globals()["subprocess"] = subprocess` — is cheaper, and is
not refused.

**Direction of repair** (yours to choose): the honest fix is not to restore the name test, which the
same comment correctly argues is wrong (`ROOT = tempfile.mkdtemp()` then substituting *that* must
keep its credit). It is to make `substitution_changes_the_world` decide *same world* by **identity
of the expression against the global being replaced** — a bare `ast.Name` whose `id` equals `name`
**and** which the case has not re-bound — or, equivalently, to pass it the same set the rebind
intersection uses and let the existing LIVE test fire. Both are measurable against the four rows
above.

`file:line` — `scripts/check-main-drivable.py:918-935` (the deleted clause and its replacement),
`:1420` / `:1423` / `:1444-1445` (the two sets diverging).

---

# High

## H1 — `_is_restore_value`'s `internal` subtraction is by NAME over the whole expression, not by the binder's SCOPE, and it is wrong in BOTH directions

Round 6 restored the lambda half of `internal` (`:863-866`) because Codex found a restore read as a
substitution. The restored clause is right about the case it names and **introduces the mirror of
it**, because `internal` subtracts a binder's parameter/target names from `names` **everywhere in
the value**, including from references that are not inside the binder at all.

**The observation that makes it FAIL — both polarities, measured:**

```text
H1  _is_restore_value subtracts binder names by NAME, not by SCOPE
      DEBT     globals()['ROOT'] = _sv                              <- control: a plain restore
      rebind   globals()['ROOT'] = (lambda _sv: _sv)(_sv)           <- FALSE GREEN: a restore, credited
      rebind   globals()['ROOT'] = [_sv for _sv in [_sv]][0]        <- FALSE GREEN: same, comprehension
      rebind   globals()['ROOT'] = {**_sv, **(lambda q: q)(td)}     <- control: a real substitution
      DEBT     globals()['ROOT'] = {**_sv, **(lambda td: td)(td)}   <- FALSE DEBT: same substitution,
                                                                       parameter renamed to shadow `td`
```

- **False green** (rows 2 and 3): when the binder's name is the **holder** itself, `names & holders`
  goes empty, `_is_restore_value` returns False at `:869-870`, the restore reads as a live
  substitution and every later `main()` in the case earns REBIND. This is exactly the failure mode
  round 5's High recorded — *"A missed restore leaves the substitution LIVE, so every later `main()`
  in the case earns the rebind route"* — reintroduced through the fix for its inverse.
- **False debt** (row 5): the value genuinely injects the case-built `td` as the lambda's
  **argument**, in the enclosing scope, but `td` is subtracted because a lambda **inside** the value
  happens to use the same parameter name.

Both polarities are one root cause. The comprehension half (`:861-862`) has carried it since before
this slice; round 6 widened it to lambdas. `ast` knows the scope — the subtraction has to apply to
Name nodes **beneath the binder** that are not themselves rebound, not to every Name in the
expression.

**Blast radius — latent.** No guard on disk puts a lambda or a comprehension in a restore value;
I checked all eight rebind guards' substituting lines. The false-green half is the dangerous
direction and it is a one-line fake.

`file:line` — `scripts/check-main-drivable.py:858-875`.

## H2 — the round-6 split was applied to six names and not to five more that fail its own stated property, so a built directory refuses credit

The fold's reasoning is stated as a property, not a membership decision (`:200-207`):

> a NORMALISER returns something exactly as live as what it is given… An AMBIENT READER injects
> state its base does not contain (`expanduser` reads `$HOME`, `getcwd` reads the process) and must
> stay.

**`listdir`, `scandir`, `walk`, `iterdir` and `glob` are not ambient readers by that definition.**
They read the directory they are *given*; they inject nothing their base does not contain. They are
ambient only in the no-argument / `'.'` forms. They were left in `LIVE_WORLD_READERS:215`, and the
attribute branch at `:1296` answers on the TAIL alone — the identical mechanism that sent
`Path(tempfile.mkdtemp()).resolve()` to DEBT and was round 6's High 1.

```text
H2  five directory readers answer on the TAIL
      argv     main([str(Path(td))])                        <- control
      DEBT     main([str(next(Path(td).iterdir()))])         <- a world the case BUILT, refused
      DEBT     main([str(sorted(Path(td).glob('*'))[0])])    <- refused
      DEBT     main([str(os.listdir(td)[0])])                <- refused
      DEBT     main([str(next(os.scandir(td)).path)])        <- refused
      DEBT     main([str(next(os.walk(td))[0])])             <- refused
      DEBT     main([str(glob.escape(td))])                  <- the MODULE named `glob`, refused
      DEBT     main([str(os.listdir('.')[0])])               <- must stay DEBT: ambient base
      DEBT     main([str(next(Path('.').iterdir()))])        <- must stay DEBT: ambient base
```

The last two are the control that distinguishes this from a widening: the ambient-base spellings are
refused through their **base**, exactly as `Path('.').resolve()` is, so moving the five names out
does not lose them. Measured, with the five removed from the set:

| input | listed | removed |
|---|---|---|
| `next(Path(td).iterdir())` | DEBT | **argv** |
| `sorted(Path(td).glob('*'))[0]` | DEBT | **argv** |
| `os.listdir(td)[0]` | DEBT | **argv** |
| `glob.escape(td)` | DEBT | **argv** |
| `os.listdir('.')[0]` | DEBT | DEBT ✓ |
| `next(Path('.').iterdir())` | DEBT | DEBT ✓ |
| `os.listdir()[0]` | DEBT | **argv** ✗ — the no-argument form regresses |

The one regression names its own repair and it is already in the file: the no-argument form is the
`callee &` union at `:1323`, whose `LIVE_WORLD_READERS` term is dead today (see L1) and becomes
load-bearing the moment these five move. **The dead term and this finding are the same seam.**

`glob.escape(td)` is a second shape of the same defect worth separating: a bare entry in the set
collides with an ordinary **module or helper name**. A suite that does `import glob`, or defines a
helper called `walk` or `home`, has everything that passes through it classified LIVE. The file
already learned this for `path` / `modules` / `prefix` and built `LIVE_WORLD_QUALIFIED` for it;
`glob`, `walk`, `listdir`, `scandir`, `iterdir`, `home`, `cwd`, `environ`, `argv` are still bare.

**Blast radius — latent false debt**, same class and same severity as the finding this commit folds.
Normalising, listing and globbing a temp tree are all natural ADR-0014 repairs; each one keeps a
guard pinned while its suite drives `main` over a world it built.

`file:line` — `scripts/check-main-drivable.py:215` (the five names), `:1296` (the tail-answering
branch), `:1323` (where the no-argument form must land).

## H3 — `NAMESPACE_READERS` does not honour the `globals` alias that `_is_globals_call` in the same file already handles, so the round-6 Blocking is closed on three spellings of four

`NAMESPACE_READERS:163` is new in this commit, and it compares **raw names**. The same file, 724
lines earlier, owns the question *"is this a call to `globals`?"* and answers it correctly for the
imported spelling:

> `_is_globals_call` (`:587-598`) — ⚠ ROUND 2 MEDIUM… the matcher accepted only the literal name, so
> `from builtins import globals as gl` made every substitution in such a file invisible… **a rule
> that recognises only the spelling its author happened to use is this repo's most-measured defect.**

`note_globals_imports(tree)` already computes the alias set; `world_class` never receives it.

```text
H3  NAMESPACE_READERS ignores the globals alias _is_globals_call honours
      DEBT     main([str(globals()['__file__'])])
      DEBT     main([str(vars()['__file__'])])
      DEBT     main([str(builtins.globals()['__file__'])])        import builtins
      argv     main([str(gl()['__file__'])])                      from builtins import globals as gl
```

The fourth row is Codex's Blocking 1 — *"the module NAMESPACE is another spelling of every name
above"* — still open under one spelling. It is a false green on the live-repository path: a guard
can pass D2 by handing `main` its own source file.

**Blast radius — latent.** Zero guards on disk import `globals` under an alias (`note_globals_imports`
returns empty for all 44). The file itself argues this is still worth four lines, and it is the
second time this exact spelling has slipped through a rule in this file.

`file:line` — `scripts/check-main-drivable.py:163`, `:1321-1323`; the owner it drifted from,
`:587-598` and `:576-584`.

---

# Medium

## M1 — two more dying cases (the eleventh and twelfth), both the sibling sites of the one round 5 wrapped

Round 5 wrapped `_argv_expr`'s `len(call.args) > idx` precondition after severing it died. The
**identical shape** appears at two more sites and neither reports. Both go red with **zero `[FAIL]`
lines**, so `--mutate .` would refuse the kill.

| severance | rc | ok | `[FAIL]` | class |
|---|---|---|---|---|
| `_argv_expr:1365` — drop the `len()` precondition (round 5's, already wrapped) | 1 | 291 | 1 | CAUGHT |
| **`_constructed_at_call_sites:1399`** — `arg = sub.args[idx] if len(sub.args) > idx else next(…)` → `arg = sub.args[idx]` | 1 | **23** | **0** | **DIES** |
| **`subprocess_self_calls:988`** — `argv = node.args[0] if node.args else None` → `argv = node.args[0]` | 1 | **289** | **0** | **DIES** |

```text
  File ".../scripts/check-main-drivable.py", line 1399, in _constructed_at_call_sites
    arg = sub.args[idx]
          ~~~~~~~~^^^^^
IndexError: list index out of range
```

```text
  File ".../scripts/check-main-drivable.py", line 988, in rec
    argv = node.args[0]
           ~~~~~~~~~^^^
IndexError: list index out of range
```

The first is the worse of the two: it dies at **case 24 of 292**, so 268 cases never run and the
sweep reads a near-total blackout rather than a finding. Round 5's own note — *"The site to wrap is
the one that RAISES, which is not always the one that names the rule — learned twice over, at a cost
of two rounds"* — was applied to the instance, not to the class; a grep for the sibling shape would
have found both.

`file:line` — `scripts/check-main-drivable.py:1399`, `:988`.

## M2 — `subprocess_self_calls`' entire `skip` set has ZERO suite coverage, while the same two halves in the sibling walker are covered

`suite_main_calls:549` and `subprocess_self_calls:978` build the identical `skip` set. Manifest entry
18 anchors on the first line only.

| severance | rc | `[FAIL]` | class |
|---|---|---|---|
| `suite_main_calls:549` — drop `_skip_ids` | 1 | 2 | CAUGHT |
| `suite_main_calls:549` — drop `_dead_branch_ids` | 1 | 1 | CAUGHT |
| `subprocess_self_calls:978` — drop `_skip_ids` | **0** | 0 | **DEAD** |
| `subprocess_self_calls:978` — drop `_dead_branch_ids` | **0** | 0 | **DEAD** |
| `subprocess_self_calls:978` — **drop both at once** (`skip = set()`) | **0** | 0 | **DEAD** |

Dropping both at once is still green, so this is **not** a masking pair — it is a plain coverage
hole. The clause is load-bearing on disk:

```text
  subproc  live branch (control)
  DEBT     the same call inside `if False:`
  DEBT     the same call inside main()'s own body
```

so today the guard correctly refuses both fakes, and nothing in the suite would notice if it stopped.
That is the route the module docstring calls *"the single clearest instance in the repo of the suite
observing what the shipped entry point produces"*, and `if False:` is the shape the file names as
the cheapest fake there is.

`file:line` — `scripts/check-main-drivable.py:978` (uncovered), `:549` (covered, entry 18).

## M3 — six further spellings of the live repository classify BUILT, each the near-miss sibling of a listed name

Target: *find a 16th spelling*. There are at least six, and they cluster where the list stops short
of a name right beside one it holds.

```text
M3  further spellings of the live repository
      DEBT     main([str(tempfile.gettempdir())])                  <- listed
      argv     main([str(tempfile.tempdir)])                       <- the SAME directory, as an attribute
      DEBT     main([str(sys.argv[0])])                            <- listed
      argv     main([str(sys.orig_argv[0])])                       <- sibling (3.10+)
      DEBT     main([str(sys.prefix)])                             <- LIVE_WORLD_QUALIFIED
      argv     main([str(sys.exec_prefix)])                        <- sibling
      argv     main([str(sys.base_prefix)])                        <- sibling
      DEBT     main([str(os.getenv('HOME'))])                      <- listed
      argv     main([str(os.getenvb(b'HOME'))])                    <- sibling of getenv AND environb
      argv     main([str(sys._getframe().f_globals['__file__'])])  <- the module dict, via the frame
```

`tempfile.tempdir` is the sharpest: `:213-214` carries a comment explaining precisely why
`gettempdir` is listed and `mkdtemp` is not, and `tempfile.tempdir` **is** what `gettempdir()`
returns.

I am not filing this as a demand to extend the list — the module docstring at `:166-190` already
concedes the list is irreducible, and backlog #224 owns the fork. **What it does establish is the
size of the residue at this commit**: the list is not one or two spellings from complete, and any
convergence claim resting on "the known escapes are closed" is not supported.

**Blast radius — latent.** None of the ten compliant guards uses any of these.

`file:line` — `scripts/check-main-drivable.py:192-216`, `:218-219`.

## M4 — this commit flipped `os.path.abspath('sub')` from DEBT to a credit, and the wider hole it lands in is that only four relative literals are ambient

```text
M4  a bare relative-path literal through a call wrapper
      DEBT     main([str(os.path.abspath('./sub'))])     <- AMBIENT_PATH_LITERALS prefix rule
      argv     main([str(os.path.abspath('sub'))])       <- the SAME path, spelled without `./`
      argv     main([str(os.path.realpath('sub'))])
      argv     main([str(Path('sub').resolve())])
      argv     main([str(os.path.join('sub','x'))])
      argv     main([str(str('sub'))])
```

Rows 2-4 are a **verdict this commit changed**: with `abspath`/`realpath`/`resolve` still in
`LIVE_WORLD_READERS` all three returned DEBT (measured by re-adding the six removed names and
re-running — all three flip back to DEBT, and `Path(tempfile.mkdtemp()).resolve()` flips back to the
false refusal round 6 fixed). So High 1's repair is right about the normaliser property and wrong
about one case the removed names were accidentally covering: **`abspath`, `realpath`, `resolve`,
`absolute` and `relpath` resolve a *relative* base against the process CWD, which is ambient state
the base does not contain** — the file's own definition of an ambient reader. The property-based
split is sound; its predicate is `base is relative`, not `name is in a list`.

Rows 5-6 show the hole is wider than the three names and pre-dates this commit:
`AMBIENT_PATH_LITERALS:232` holds only `""`, `"."`, `".."`, `"./"`, `"../"` plus a `./`/`../`
prefix test, so **any other relative literal reaching the `Call -> BUILT` fall-through at `:1326`
is credited**. `str("sub")` is a world nobody built.

This is in tension with the docstring's stated limit 2 (`:67-72`), which says a hard-coded path
literal does not count. That is true only of a literal **directly** in argv; through any call
wrapper it does. The wrapper behaviour is deliberate (`:1315-1320` explains why the all-literal
exclusion was deleted and `check-ci-watched.py`'s `_S(True, "…")` must reach BUILT) — so the limit
as written overstates what the code does, which is this branch's signature defect applied to itself.

**Blast radius — latent.** No compliant guard reaches its credit this way; `check-fixture-variation.py:1881`'s
`main(["/nonexistent/nope.py"])` is a bare literal and is still correctly refused.

`file:line` — `scripts/check-main-drivable.py:232`, `:1259-1266`, `:1326-1335`; limit 2 at `:67-72`.

---

# Low

## L1 — a fourth masking pair: the `LIVE_WORLD_READERS` term in the no-argument-call union at `:1323` is unkillable, and reachable only where it is wrong

| severance | rc | `[FAIL]` | class |
|---|---|---|---|
| `:1323` drop `LIVE_WORLD_READERS` from the union | **0** | 0 | **DEAD** |
| `:1323` drop `CWD_CONSTRUCTORS` | 1 | 1 | CAUGHT |
| `:1323` drop `NAMESPACE_READERS` | 1 | 2 | CAUGHT |

It cannot be killed for a structural reason, which is what makes it a masking pair rather than mere
missing coverage: `_expr_children` always yields a Call's `func`, so for any callee whose Name
(`:1291`) or Attribute tail (`:1296`) is in `LIVE_WORLD_READERS`, `kids` already contains LIVE and
`world_class` returns at `:1327` before the Call branch is reached. **Two guards, the same answer,
so neither can be killed** — the shape `world_names`' absent-seed pair and `subprocess_self_calls`'
duplicated shape test were both resolved for.

The input that does reach it is one where it gives the wrong answer: a name the case bound that
happens to collide with the list.

```text
  DEBT     main([str(home())])     with `home = str` in the case   <- the term fires on a case-bound name
  argv     main([str(nope())])     with `nope = str`               <- control
```

That is round 3's Medium (*"A name the case BOUND stops shadowing…"*) unapplied to this branch.

⚠ **Do not delete it** — H2's repair is the thing that makes it load-bearing. Resolve the two
together.

`file:line` — `scripts/check-main-drivable.py:1323`.

## L2 — the Attribute half of `callee` is uncovered but load-bearing

Dropping `:1321` leaves **292/292 green**, yet it is the only thing that catches
`builtins.globals()["__file__"]` (shown DEBT in H3's block; with the line removed the callee set is
`{"builtins"}` and the expression reaches BUILT). Round 6 added both lines together and wrote one
case, for the Name half.

`file:line` — `scripts/check-main-drivable.py:1321`.

## L3 — `locals()` and `dir()` inside a suite function are the CASE's own scope, not the module namespace

```text
L3  locals()/dir() inside a suite function are the CASE's own scope
      DEBT     main([str(locals()['td'])])     <- `td` is the case's own tempdir
      DEBT     main([str(dir()[0])])
```

Every `main`-driving call site this guard examines is **inside a function**, where `locals()` is the
case's frame — the most constructed thing in the file — and `dir()` is a list of its local *names*.
`NAMESPACE_READERS` exists because *"`vars()["__file__"]` and `globals()["__file__"]` reach the live
module dict"*; neither sentence is true of `locals` or `dir` at a suite call site. Lost credit, and
the mirror of the overreach the same commit fixed in High 1.

`file:line` — `scripts/check-main-drivable.py:163`.

## L4 — the round-6 lambda widening beyond plain `args` is uncovered

Reducing `:863-866` to `for a in lam.args.args` leaves **292/292 green**: `posonlyargs`, `kwonlyargs`,
`vararg` and `kwarg` were added in this commit with no case distinguishing them. (The behaviour is
real — `(lambda *_sv: _sv[0])(_sv)` exercises the `vararg` branch — it is simply unasserted.)

`file:line` — `scripts/check-main-drivable.py:863-866`.

## L5 — the `("__file__", "sys")` element filter is uncovered, and can only fire where it is wrong

Dropping `:1014-1015` leaves **292/292 green**. It also cannot change a verdict correctly: any argv
element containing `__file__`, or an unshadowed `sys`, already classifies LIVE through `:1291`, so it
is never BUILT and the filter has nothing to exclude. The one input on which it decides is a case
that **shadows** `sys` with something it built — where the filter discards the case's own world:

```text
  subproc  extra element `td` (built, mentions neither)  -> credited, filter irrelevant
  DEBT     `sys = tempfile.mkdtemp()`, element `sys`     -> the case's own built element, excluded
```

This is the eighth clause of this shape in the file. The ones before it were deleted.

`file:line` — `scripts/check-main-drivable.py:1012-1016`.

---

# What I tried to refute and could not

Named, because a reviewer that only reports hits is a biased instrument.

1. **The manifest. All 116 entries, dynamically.** Full `stage_tree`, green control, each entry
   applied to the delivered script, suite re-run, `[FAIL]` lines matched against the entry's own
   `expect`: **116 KILLED, 0 survived, 0 DIES, 0 red-via-the-wrong-case**, green after-control.
   Statically: every anchor binds **exactly once**; no duplicate names; no duplicate anchor tuples;
   no empty `expect`; and every one of the 116 `expect` strings is an **exact** match for a case
   name the suite actually prints (checked against the 292 printed names, not against the source,
   because several names are f-strings). Three anchors (entries 17, 49, 59) are mid-line rather than
   whole-line; the harness only requires uniqueness and all three resolve, so I am not filing it.
   **I expected to find a masked entry here and did not.**
2. **The normaliser/ambient split at the polarity round 6 fixed it for.** Twenty spellings. Every
   normaliser over a BUILT base is credited (`Path(tempfile.mkdtemp()).resolve()`,
   `.absolute()`, `os.path.abspath(mkdtemp())`, `os.path.realpath(...)`, `os.path.relpath(...)`) and
   every normaliser over an ambient base is still refused (`Path('.').resolve()`,
   `os.path.abspath('.')`, `os.path.abspath(os.curdir)`, `Path.cwd().resolve()`,
   `os.fsdecode(os.getcwd())`). The split holds. M4 is a *different* predicate failing, not this one.
3. **The six rebind credits the brief asked about — in fact all eight.** I re-derived, per guard, the
   crediting call site and the substituting line, then read each one on disk:
   `check-ci-watched.py:706-713`, `check-dashboard-entry.py:1442/1456`,
   `check-fixture-variation.py` (12 sites, `EXEMPT`), `check-main-drivable.py:3157-3161`,
   `check-plan-file-tags.py:333-335`, `check-ratchet-contract.py:977-980`,
   `check-rc-contract.py:743-747` and `:779-782`, `check-surface-recall.py:652/679/701/719`.
   **Every credit is deserved.** I specifically suspected the three guards whose only live
   substitution is `globals()["_self_test"] = <stub>` of being credited for stubbing their own
   suite; each is a real `lambda: 99`/`lambda: 4242` substitution, and in every case the file also
   earns the route elsewhere, so none depends on it. No live false green among the ten.
4. **Namespace reads with arguments, and other routes to the module dict.** `vars(sys.modules['__main__'])`,
   `globals().get('__file__')`, `dict(globals())`, `sorted(globals())[0]`, `list(globals().values())[0]`,
   `builtins.globals()`, `_g = globals; _g()` — all correctly DEBT. Only the import-alias spelling
   escapes (H3).
5. **The restored lambda subtraction against nesting.** A nested lambda `(lambda a: (lambda b: b)(a))(_sv)`,
   a comprehension inside a lambda, and a walrus inside a comprehension (`[y := f(x) for x in _sv]`,
   where `y` correctly binds in the enclosing scope and so correctly reads as a substitution) all
   classify correctly. The defect is name-vs-scope (H1), not nesting.
6. **Nine other deleted clauses.** `_skip_ids`' `__main__` clause (a module-level call has no
   enclosing function and can never be suite-reachable — holds), `argv_forwarders`' `main` skip
   (`suite_main_calls` does test `func.id == "main"` first and `fwd` is read only by `_argv_expr` —
   holds), `_global_target_names`' Attribute unwrap (`ast.walk` does reach the Subscript — holds),
   `world_class`'s `seen` set, its `Starred` unwrap, its post-Constant `return INERT`, its
   `Constant/Name` promotion, the all-literal-argument exclusion, and `_expr_children`'s `ast.stmt`
   refusal. **One of twelve changed a verdict (B1); eleven held.**
7. **Twenty-one further severances on live rules** — `_is_restore_value`'s three clauses,
   `substitution_changes_the_world`'s case-bound-leaf test, both `LIVE_WORLD_READERS` branches, both
   halves of `AMBIENT_PATH_LITERALS`, `suite_main_calls`' reachability test and both skip halves,
   `_unpack`'s shape test, `_wired`'s precondition, `_param_index`, `_argv_expr`,
   `subprocess_self_calls`' reachability test and its argv shape test (round 6's Medium — now
   **CAUGHT**, 291/1, so that fix is good), and the comprehension half of `internal`. All CAUGHT.
8. **`suite_reachable`'s undefended `funcs[name]`**, documented as an invariant rather than an
   oversight. I could not build an input that reaches it with an absent name: every seed comes from
   `suite_entries`, which filters on `in funcs`. The documentation is accurate.
9. **Counts and plumbing.** `EXPECTED_MUTATIONS["scripts/check-main-drivable.py"] == 116` matches the
   manifest; the declared sum 1294 matches `sum(EXPECTED_MUTATIONS.values())`; the docstring's
   "292 cases" matches the run and `check-selftest-counts.py` verifies it by running it; the guard is
   invoked by CI at `.github/workflows/ci.yml:394` and `:397`, and `check-ratchet-contract.py` is
   green on it; `check-docs.py` is green.

---

# Appendix — the evidence block

Verbatim output of the single script that produced every classification quoted above. It imports the
subject from `0d326382`, wraps each fixture with the subject's own `_wired`, and prints
`classify(...).label`.

```text
B1  identity substitution of an import/def global
      DEBT     globals()['ROOT'] = ROOT
      rebind   globals()['subprocess'] = subprocess
      rebind   globals()['helper'] = helper
      rebind   globals()['ROOT'] = tempfile.mkdtemp()
H1  _is_restore_value subtracts binder names by NAME, not by SCOPE
      DEBT     globals()['ROOT'] = _sv
      rebind   globals()['ROOT'] = (lambda _sv: _sv)(_sv)
      rebind   globals()['ROOT'] = [_sv for _sv in [_sv]][0]
      rebind   globals()['ROOT'] = {**_sv, **(lambda q: q)(td)}
      DEBT     globals()['ROOT'] = {**_sv, **(lambda td: td)(td)}
H2  five directory readers answer on the TAIL
      argv     main([str(Path(td))])
      DEBT     main([str(next(Path(td).iterdir()))])
      DEBT     main([str(sorted(Path(td).glob('*'))[0])])
      DEBT     main([str(os.listdir(td)[0])])
      DEBT     main([str(next(os.scandir(td)).path)])
      DEBT     main([str(next(os.walk(td))[0])])
      DEBT     main([str(glob.escape(td))])
      DEBT     main([str(os.listdir('.')[0])])
      DEBT     main([str(next(Path('.').iterdir()))])
H3  NAMESPACE_READERS ignores the globals alias _is_globals_call honours
      DEBT     main([str(globals()['__file__'])])
      DEBT     main([str(vars()['__file__'])])
      DEBT     main([str(builtins.globals()['__file__'])])   import builtins
      argv     main([str(gl()['__file__'])])   from builtins import globals as gl
M3  further spellings of the live repository
      DEBT     main([str(tempfile.gettempdir())])
      argv     main([str(tempfile.tempdir)])
      DEBT     main([str(sys.argv[0])])
      argv     main([str(sys.orig_argv[0])])
      DEBT     main([str(sys.prefix)])
      argv     main([str(sys.exec_prefix)])
      argv     main([str(sys.base_prefix)])
      DEBT     main([str(os.getenv('HOME'))])
      argv     main([str(os.getenvb(b'HOME'))])
      argv     main([str(sys._getframe().f_globals['__file__'])])
M4  a bare relative-path literal through a call wrapper
      DEBT     main([str(os.path.abspath('./sub'))])
      argv     main([str(os.path.abspath('sub'))])
      argv     main([str(os.path.realpath('sub'))])
      argv     main([str(Path('sub').resolve())])
      argv     main([str(os.path.join('sub','x'))])
      argv     main([str(str('sub'))])
L3  locals()/dir() inside a suite function are the CASE's own scope
      DEBT     main([str(locals()['td'])])
      DEBT     main([str(dir()[0])])
```

---

# Verdict

| Severity | Count |
|---|---|
| Blocking | 1 |
| High | 3 |
| Medium | 4 |
| Low | 5 |

**Two of the eight findings above Low were introduced or widened by the round-6 fold itself** (H2's
five unmoved names and M4's flipped verdict are both consequences of High 1's repair; H3 and L2/L4
are gaps in the Blocking's repair), which continues this file's pattern exactly: **every round has
found defects inside the previous round's repairs, and this one is no exception.** B1 and H1 are
false greens; H2 and M4 are the two polarities of the same misidentified predicate.

**NOT CONVERGED.**
