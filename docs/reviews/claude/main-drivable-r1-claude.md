# `check-main-drivable.py` r1 — Claude adversarial half

> **Subject:** commit `840a7b43` on `d2-main-drivable`, base `master`. Load-bearing file
> `scripts/check-main-drivable.py` (1,065 lines — the brief said ~700) with
> `scripts/mutations/check-main-drivable.json` (18 entries).
> **Mandate:** refute, not confirm. ADR-0014 itself is out of scope.

---

## What I executed vs only read

**Executed** (all from the repo root, Python 3.14.4):

| Command | Result |
|---|---|
| `python3 scripts/check-main-drivable.py --self-test` | **79/79 passed**, rc 0, 1.07s |
| `python3 scripts/check-main-drivable.py --report` | 44 guards · 7 no `main()` · 37 in population · **8 comply** · 29 pinned |
| `python3 scripts/check-main-drivable.py scripts/check-anchors.py` | rc 0, prints `D2 OK — every guard…` over a population of **one** |
| `python3 scripts/check-main-drivable.py <chmod 000 file>` | **`PermissionError` traceback, rc 1** — not rc 2, not `NOT CHECKED` |
| `partial-sweep.py scripts/check-main-drivable.py` | control green in 2s; **18/18 red via the case each names**; `after-control: GREEN`; 0.4 min |
| `check-fixture-variation.py` / `check-selftest-counts.py` / `check-ratchet-contract.py`, suite + live | all rc 0 (67/67, 18/18, 56/56) |
| 10 severance experiments on a **copy** of `scripts/` in a temp root | 8 stayed 79/79 green — §H3, §H1 |
| 7 synthetic probes against `classify` / `global_writes` / `live_substitutions` | §B1, §H2, §M1, §M2 reproduced |
| Re-derivation of the 1.99s → 0.076s performance claim | **substantiated**, see below |

**Read only, not executed:** `docs/adr/0014-a-guards-main-is-drivable.md`;
`docs/reviews/architecture-review-2026-10-01.md` §⛔ Corrections; the full commit message of
`840a7b43`; all 1,065 lines of the guard; the 18 manifest entries; the call sites of all 8
compliant guards and of the 2 pinned guards that have any `main` call at all.

**Not run:** `check-plan-code.py --mutate .` in full (the brief authorised the partial sweep
instead; the partial sweep is explicitly *not* a coverage verdict). No `git` write of any kind.

### Claims I tried to refute and could not — stated because a reviewer that only reports hits is a biased instrument

1. **The performance claim is TRUE.** I reconstructed the pre-fix shape described at
   `check-main-drivable.py:386-394` and `:430-434` (candidate set rebuilt inside the loop over
   statements *and* targets, plus `global_writes` recomputed once per name inside
   `live_substitutions`) and ran it on `check-plan-code.py`: **2.421s** reconstructed vs
   **0.0741s** shipped, same `routes={'argv'}`. The claimed 1.99s is my reconstruction's 2.42s to
   within the fidelity of a reconstruction; the claimed 0.076s reproduces exactly.
2. **`check-rc-contract.py:742-747` is as described** — save at `:742`, tuple substitution of
   `ROOT`/`MATCHER`/`HOOK` at `:743`, `rc = main([])` at `:747`. ✅
3. **`module_globals`' justification is true of the repo** — `globals()["subprocess"].run = …`
   exists at `check-ci-watched.py:502` and `:531`. ✅
4. **"THE CREDIT IS PER CALL SITE, NOT PER FILE" is coherent and correct** as written. ✅
5. **No false credit among the 8 changes a verdict.** I opened every credited call site. All eight
   are substantively genuine: `check-ci-watched.py:713` (a constructed `_S` stream),
   `check-fixture-variation.py` (14 computed argv), `check-plan-code.py:2666/2880/2914`
   (`main(["--mutate", str(_r)])` on a poisoned tree), `check-plan-file-tags.py:335` (`global
   ROOT, DOCS` swap), `check-ratchet-contract.py:941/965/980` (`root=_r`),
   `check-rc-contract.py:747`, `check-surface-recall.py:682/705`, and this file itself.
6. **The documented lexical over-credit (limit 4) is NOT reachable today.** Every credited rebind
   site on disk is straight-line or inside the same `try:` as its substitution. Answering
   question 1 directly: no guard on disk has a substitution in one `if` branch and its `main`
   call in the other.
7. **The pinned 29 contain almost no room for a route-rule false negative.** 28 of the 29 have
   **zero** suite calls to `main` at all (measured with `suite_main_calls` over each). The verdict
   for those is `no suite call reaches main()`, which does not depend on any of the subtle route
   logic. §B1 and §B2 are the two exceptions, and both are real.
8. **The manifest is attributable.** All 18 went red through the `expect` case each names, over a
   control proved green first, with the after-control green. No entry was unkillable; none was red
   only because the suite died (the harness refuses an unattributable kill, and the commit message
   records that rule being paid for). Sibling registrations are consistent:
   `EXPECTED_MUTATIONS` 1178 → 1196 (+18) and the declared-sum case moved with it.

---

## Findings

### 🔴 Blocking

#### B1 — `check-dashboard-entry.py` is pinned on a FALSE verdict, and the guard's own headline regression case asserts that false verdict with a reason that is not the determinant

The suite's flagship "three files this rule judged wrongly on its first live run" loop at
`scripts/check-main-drivable.py:1028-1036` asserts:

```python
("check-dashboard-entry.py", False, "its FLAG substitution is restored before main runs"),
```

The file is indeed reported `DEBT`. **But the FLAG restore is not why.** Measured:

```
is `collect` a global main transitively reads?  True
is `FLAG` in main's world?                      True
shipped verdict: DEBT
same file with `g[...]` spelled `globals()[...]`: rebind
  (lines changed: 4 )
```

`check-dashboard-entry.py:1437-1447` is a textbook rebind over a constructed world:

```python
    g = globals()
    real_collect = g["collect"]
    g["collect"] = lambda base: ([], False, "could not run git: boom", [], [])
    try:
        with _cl.redirect_stdout(_io.StringIO()) as buf:
            rc = main(["--base", "master"])
    finally:
        g["collect"] = real_collect
```

`collect` is the function that reads the world (git), it **is** in `world_names(main)`, and the
substitution is live at the call. Its own comment at `:1450-1454` says this is *"the only case that
fails if the argument is not passed through, so it is the one that makes the wiring load-bearing"* —
i.e. it is already ADR-0014's repair, done. A second such block follows at `:1455-1461`.

The rule misses it for one reason: `_global_target_names` (`:316-339`) matches only a **literal**
`globals()[...]` subscript, so `g = globals()` aliasing is invisible. Nothing in the module
docstring's limit list (`:68-80`) mentions aliasing — limit 3 names classes, closures and
function-local imports only.

**(a) The observation that makes this FAIL:** rewriting `g["collect"]` as `globals()["collect"]` —
the *same operation*, 4 lines, no semantic change — flips the verdict from `DEBT` to `rebind`. A
rule whose answer depends on how the author spelled an identical operation is not measuring the
bit it claims to measure. The committed case is right-answer/wrong-reason, which the commit message
itself names as the failure that *"survives review and then stops being right"* (defect 2) —
shipped here as the headline case.

**(b) Quote:** `scripts/check-main-drivable.py:331`
```python
        probe = node.value if isinstance(node, ast.Attribute) else node
```
(the whole matcher around it keys on `probe.value.func.id == "globals"`), and
`scripts/check-dashboard-entry.py:1437` `g = globals()`.

**(c) Proposed fix — HYPOTHESIS, not verified:** in `global_writes`, pre-scan the case for
`NAME = globals()` bindings and treat `NAME[...]` subscript targets as `globals()[...]`. Then
re-derive `MAIN_DEBT` from the tool's own run (it will shrink by at least one) and retarget the
regression case to the real determinant. ⚠ Do **not** simply flip the case's expectation to `True`
— the FLAG-restore mechanism (defect 3) then loses its only live regression subject, and that
mechanism is still worth a case; give it a synthetic one, as `R_RESTORED` at `:849-860` already
does.

---

#### B2 — `check-selection-card.py` drives `main()` eight times over a world the case constructed, and is pinned as debt. The route list needs a fourth member

`scripts/check-selection-card.py:452-456`:

```python
    def _rc_for(raw) -> int:
        data = raw if isinstance(raw, bytes) else raw.encode()
        return subprocess.run([sys.executable, __file__], input=data,
                              capture_output=True).returncode
```

`def main() -> int:` at `:560` takes **no parameters at all** — its entire world is stdin — and
`_rc_for` is called 8 times with payloads the case built, including `b"\xff\xfe garbage"`. The
comment at `:449-452` is ADR-0014's defect verbatim and records the repair:

> *"The hook reads exactly ONE thing from this script — its exit code — and nothing executed
> `main()`. `return 2` -> `return 0` left 24/24 green, so the manifest was green, so CI was
> green, while every malformed card was admitted."*

So this file is the repo's **second worked example of ADR-0014's repair**, and arguably the
stronger one: it drives the real `__main__` entry point, which no in-process route does. The guard
reports `calls=0`, `DEBT`.

**(a) The observation that makes this FAIL:** the pin asserts *"no case can point this `main` at a
world it built"*. That sentence is false of this file today. This is the **same class** of error as
the one the architecture review's ⛔ Corrections section caught (a detector refusing the repo's own
exemplar); the correction was applied to one instance and not to the class — which is this repo's
`after-fixing-search-for-the-class` failure, inside the commit that cites it.

**(b) Quote:** `scripts/check-selection-card.py:454`
```python
        return subprocess.run([sys.executable, __file__], input=data,
```
versus `scripts/check-main-drivable.py:287-311` (`suite_main_calls`), which only ever matches
`ast.Call` with `func.id == "main"`.

**(c) Proposed fix — HYPOTHESIS:** add a fourth route, `subproc` — the suite runs
`[sys.executable, __file__]` (or `str(Path(__file__))`) with an `input=`, `env=`, `cwd=` or extra
`argv` element the case computed. It is a narrow AST shape and `__file__` makes it unambiguous.
⚠ Note the honest limit this adds: a subprocess run cannot be credited for a *constructed world*
unless something is actually passed to it, so the discrimination must be "a computed `input=`/`env=`/
`cwd=`/argv element", mirroring `computed_argv`. Alternatively, pin this file with a written
`NO-ROUTE:` reason rather than silently as debt. Either way, `grep -n "sys.executable" scripts/check-*.py`
returns **exactly one** such guard today, so the population cost is one file.

---

### 🟠 High

#### H1 — `whole` can be switched off by one token with the suite green AND the live gate green, and no manifest entry covers that direction

`scripts/check-main-drivable.py:613`:
```python
    whole = not a.paths and root == ROOT
```

Severed to `whole = False` in a copy of `scripts/`:
```
      suite: 79/79 passed
      live : D2 OK — every guard with a main() either drives it over a constructed world or is pinned.
```
rc 0. `pin_stale` — the only rule that stops the debt set rotting through a rename or a deletion —
never runs, and nothing reports it. Manifest entry 16 severs this line in the **other** direction
(`whole = True`) and is killed; there is no entry for `whole = False`.

Answering question 4 precisely: **no, a real CI run cannot get `whole=False` today.** Both new steps
in `.github/workflows/ci.yml:385-395` pass no arguments, and `ROOT` is derived from `__file__`, so
`root == ROOT` holds regardless of cwd. The exposure is not the current invocation; it is that the
guard's *own* protection for this bit is one-directional.

A second half of the same finding: the pass sentence at `:633-634` is a **false universal** under a
subset. Measured:
```
$ python3 scripts/check-main-drivable.py scripts/check-anchors.py
1 guards on disk · … · 1 in population
  (pin reconciliation SKIPPED — a subset cannot see an absence)
D2 OK — every guard with a main() either drives it over a constructed world or is pinned.
```
The `SKIPPED` notice is the only mitigation, and **it is unasserted**: deleting it from the gate
path (`:621-622`) leaves the suite 79/79 green (see H3).

**(a) FAILS IF:** `whole = False` produces a suite failure, or the gate's pass line is qualified
when `whole` is false. Neither holds.
**(b) Quote:** `scripts/check-main-drivable.py:613`, `:621-622`, `:633-634`.
**(c) Fix — HYPOTHESIS:** add manifest entry 19 severing `whole = not a.paths and root == ROOT` →
`whole = False`, with a new case asserting that a **whole** run over a constructed tree whose
`MAIN_DEBT` names an absent file reports `pin_stale` (the existing `probs4` calls `assess`
directly and so cannot see `main`'s computation of `whole`); and make the pass line read
`D2 OK — over the N guards read` when `whole` is false.

---

#### H2 — `is_restore` false-positives on `globals()["X"] = {**saved, …}`, which destroys credit for a genuine substitution. Live on disk

The restore heuristic at `:413-415` is `value_names <= holders`, where `holders` is every local
that ever held a value *reading* that global. A substitution **derived from** the saved copy
therefore reads as a restore. Measured:

```
PROBE A writes: [(7, 'DECL', True), (10, 'DECL', True)]      # BOTH read as restores
PROBE A live at main call line 8: set()
PROBE A verdict: DEBT
PROBE A' verdict: rebind   # same block with a comprehension value instead of {**saved, …}
```

This is live at `scripts/check-surface-recall.py:652`:
```python
        globals()["DECLARED_RENDER"] = {**_saved_decl, 5: _saved_decl[5] + " Detail:"}
```
preceded by `_saved_decl = dict(DECLARED_RENDER)` at `:650`. That block — the wiring case for H1's
net, explicitly written to be ADR-0014's repair — earns **nothing**. The file complies only because
its other two blocks happen to use a comprehension (`{k: v for … if k != 4}`) and a
different-global value, whose `value_names` are not a subset of the holders.

**(a) FAILS IF:** two cases that construct the same world differ in verdict purely by whether the
substituted value mentions the saved local. It does — `PROBE A` vs `PROBE A'`, one token apart.
**(b) Quote:** `scripts/check-main-drivable.py:413-415`
```python
                holders = saved.get(g, set())
                value_names = {n.id for n in ast.walk(value) if isinstance(n, ast.Name)}
                is_restore = bool(value_names) and value_names <= holders
```
**(c) Fix — HYPOTHESIS:** require the restore's value to be a **bare** holder name (or a tuple of
bare holder names) — `ast.Name`/`ast.Tuple`-of-`Name` only, not any expression mentioning one.
`{**_saved, 5: …}` is then correctly a substitution, and `globals()["FLAG"] = _real_flag` (the
`check-dashboard-entry.py:1282` shape the rule was built for) is still a restore. I did not run the
whole population under this change; it should be re-derived, not assumed.

---

#### H3 — the suite executes eight rules it does not assert; one of them is the only thing granting a route

Severed one at a time in a copy of `scripts/`, `--self-test` re-run each time. **All eight stayed
79/79 green:**

| Severed | Line | Consequence if it rotted |
|---|---|---|
| the `argv=` keyword branch of `_argv_expr` | `:453-456` | `main(argv=[str(f)])` loses the ARGV route — **this is the only code granting it** (verified: PROBE E credits `argv` today, and nothing fails when the branch is gone) |
| `module_globals` stops handling `ast.AugAssign` | `:194` | an `X += …` module global stops being a global |
| `world_names` stops shadowing `*args`/`**kwargs` | `:238-241` | a `**kwargs`-shadowed name counts as a world read |
| `computed_argv` stops accepting `ast.Tuple` | `:472` | `main((str(f),))` loses the ARGV route |
| `summarise` drops the per-route breakdown | `:581-583` | the only line reporting the 8-vs-29 split, silently gone |
| the `calls`-vs-`no calls` detail ternary | `:550-551` | the finding stops saying whether any call exists |
| the `pin reconciliation SKIPPED` notice on the **gate** path | `:621-622` | H1's only mitigation, silently gone |
| `_global_target_names`' two `ast.Attribute` probes | `:331`, `:337` | nothing — see L1, they are already dead |

**(a) FAILS IF:** a case or a mutation entry goes red for any of these. None does.
**(b) Quote:** `scripts/check-main-drivable.py:453-456`
```python
    for kw in call.keywords:
        if kw.arg == "argv":
            return kw.value
    return None
```
**(c) Fix — HYPOTHESIS:** six cases, not six mutation entries — which is ADR-0014's own consequence
2 (*it changes their kind, not their number*): `classify` on a fixture using `main(argv=[str(_f)])`,
`main((str(_f),))`, a `**kw`-shadowed global, an `X += 1` module global; plus an assertion on the
route-breakdown substring and on the `SKIPPED` notice in both the gate and `--report` paths. The
`detail` ternary deserves one case per branch.

---

### 🟡 Medium

#### M1 — the PARAM route has no literal discrimination, and the asymmetry with ARGV is live

`_passes_extra_world` (`:459-463`) returns `True` on **arity alone**:
```python
    if len(call.args) > 1:
        return True
```
Measured: `main(["--self-test"], ROOT)` → `param`. `main([], root=ROOT)` → `param`. Both run `main`
over the **live repository** while being credited for "supplying main's world" — the exact
false-pass the ARGV route builds a whole discrimination to refuse (`A_LIT` at `:774`,
`A_SELFTEST` at `:777`). A live instance: `check-ci-watched.py:735` is `main(["--clear"], None)`, a bare
`None` literal, credited `param`. That file still complies on substance via `:713`, so no verdict
is wrong today — but the mechanism is unguarded and the docstring claims the opposite
discrimination is "the whole discrimination".

**Fix — HYPOTHESIS:** apply `computed_argv`'s own test to the extra argument: a bare `ast.Constant`
(including `None`) earns nothing; a `Name`, call, f-string or attribute does. `check-ci-watched.py`
keeps its credit from `:713`; nothing on disk loses one.

#### M2 — a restore written as a CONSTANT is not recognised as a restore, so it over-credits — one spelling away from defect 3 being unfixed

```
PROBE C (constant restore) verdict: rebind
  writes: [(5, 'FLAG', False), (7, 'FLAG', False)]
```
`is_restore` requires `bool(value_names)`, so `globals()["FLAG"] = False` / `= None` / `= 0` is read
as a *second substitution*, left live, and credits a later `main(["--base","master"])` over the live
repo. Had `check-dashboard-entry.py` restored to a literal rather than to `_real_flag`, defect 3's
fix would not fire. `globals().update(keep)` and `g.update(keep)` restores (e.g.
`check-ci-watched.py:717`) are likewise invisible.
**Fix — HYPOTHESIS:** treat a constant assignment to a previously-substituted global as a restore
when a save for it exists; and recognise `globals().update(NAME)` / `NAME.update(…)` as a restore of
every key the saved dict was built from. Conservative direction only (more debt, never more credit).

#### M3 — an unreadable guard file is neither rc 2 nor `NOT CHECKED`; it is a bare traceback at rc 1

The CANNOT-RUN check at `:603-607` uses `p.is_file()`, which is `True` for a `chmod 000` file, so
`p.read_text()` at `:610-611` raises. Measured:
```
PermissionError: [Errno 13] Permission denied: …/scripts/check-anchors.py
rc=1
```
The docstring's contract (`:88-90`, "the population is empty (CANNOT RUN, rc 2)") and this repo's
own rule — *"cannot run" is a FAILURE that must say treat this as NOT RUN* — both ask for rc 2 and
the sentence. rc 1 means "findings" to every caller of this gate. A non-UTF-8 byte in a guard file
takes the same path (`UnicodeDecodeError`). It is loud, so this is not a false pass — it is a
mislabelled one.
**Fix — HYPOTHESIS:** wrap the comprehension at `:610-611` in a `try/except OSError,
UnicodeDecodeError` that appends to `unreadable` and takes the existing rc-2 path.

#### M4 — "1,160 lines" is wrong; it is 163

`scripts/check-main-drivable.py:358-362` (and the commit message, which repeats it):

> *"`check-dashboard-entry.py` substitutes `globals()["FLAG"]` at :1276 and restores it at :1282 —
> **1,160 lines before** the `main(["--base", "master"])` at :1445"*

Verified by grep: substitution `:1276` ✅, restore `:1282` ✅, `main(["--base", "master"])` `:1445`
✅ — and 1445 − 1282 = **163**. The three line numbers are right and the derived distance is wrong
by a factor of seven. Low stakes on its own; filed because this file's own stated reason for
existing is that *"a guard whose comments assert things its code does not do is the defect six of
today's review findings were"*, and because `a-retrospective-number-needs-provenance` is a measured
recurring failure here. ⚠ The argument the number supports is unaffected: 163 lines and an
intervening `case(...)` is still a restore long before the call.
**Fix:** change `1,160` to `163`, in the docstring and in any prose quoting it.

---

### 🔵 Low

**L1 — two dead branches, 4 lines, neither falsifiable.** `:331` and `:337` special-case
`ast.Attribute` to reach `node.value`, but the enclosing loop is `for node in ast.walk(target)`,
which already visits that child. Severing `:331` to `probe = node` leaves 79/79 green *and* the
`R_ATTR` case passing. Harmless, but it reads as load-bearing and is cited in the docstring.

**L2 — `check-ci-watched.py` is reported `param` only, while ADR-0014's own Corrections table
counts it as rebinding globals at 6 sites.** All 11 of its substitutions go through
`g = globals()` (`:556-558`, `:621-625`, `:706-710`, `:729-732`) and the rule sees none — the B1
mechanism, measured at scale on the file ADR-0014 names as its precedent. The route-count line
`rebind 5` in `--report` is therefore an undercount of the repo, not just of this guard.

**L3 — `--report` over a subset carries the same over-claim as H1** and is additionally documented
as "always exit 0". Fine as advisory; worth a line in the `--report` output naming the population
it read, which `summarise` already does.

---

## Answers to the seven questions, in brief

| # | Question | Answer |
|---|---|---|
| 1 | False credit among the 8? | **No** — all eight substantively genuine; the lexical `if`-branch over-credit is **not** reachable on disk. Mechanisms exist unguarded (M1, M2). |
| 2 | False negative in the pinned 29? | **Yes, two** — B1 (`check-dashboard-entry.py`, via `g = globals()`) and B2 (`check-selection-card.py`, via subprocess). The other 27 have zero `main` calls and are safe from the route logic. |
| 3 | Assert or merely execute? | **Eight rules deletable with 79/79 green** (H3), one of them the sole grantor of a route. |
| 4 | `whole=False` in CI? | **Not reachable today** — both CI steps pass no args and `ROOT` is `__file__`-derived. But `whole = False` is a one-token, suite-green, gate-green kill of `pin_stale`, uncovered in that direction (H1). |
| 5 | CANNOT RUN honesty? | Empty and absent-override paths are correct (rc 2, measured). **Unreadable ≠ unparseable is not handled** (M3). A clean or shallow clone is fine — the guard touches no `git`. |
| 6 | Manifest attributability? | **Clean** — 18/18 red via the named case, control green, after-control green, none unkillable, none killed by suite death. Gap is coverage (H3/H1), not attribution. |
| 7 | Claims vs code? | 4 of 5 checked claims **true** (per-call-site paragraph; `check-rc-contract.py:742-747`; `globals()["subprocess"].run`; the 1.99s → 0.076s fix, re-derived at 2.42s → 0.074s). **One number false: 1,160 → 163** (M4). Plus the docstring's limit list omits `g = globals()` aliasing, which is B1. |

---

## Verdict

**NOT CONVERGED** — two Blocking findings. Both are the same shape as the defect the architecture
review's ⛔ Corrections section already caught once on this rule: a detector that refuses a file
which is *already doing what the ADR asks*. `check-dashboard-entry.py` (B1) is the sharper of the
two, because the guard ships a regression case that asserts the wrong verdict and attributes it to a
mechanism that is not the determinant — the exact *right-answer-for-the-wrong-reason* failure the
commit message says defect 2 taught it to avoid.

⚠ **`MAIN_DEBT` must be re-derived from the tool's own run after B1 and B2 are fixed, not
hand-edited** — the commit message's own closing warning, and the set will shrink.
