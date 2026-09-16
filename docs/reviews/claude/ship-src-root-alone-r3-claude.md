# Round 3 — `ship-src-root-alone` — Claude half (ran first)

```yaml
round: 3
subject: ship-src-root-alone
half: claude
ran_first: true
head: c7a474b4
converged: false
findings:
  - {id: B1, severity: Blocking, aim: instrument, fix_induced: true,  component: src-caller, kind: regression}
  - {id: B2, severity: Blocking, aim: instrument, fix_induced: true,  component: src-caller, kind: false-coverage-claim}
  - {id: M1, severity: Medium,   aim: instrument, fix_induced: true,  component: review-evidence}
  - {id: L1, severity: Low,      aim: instrument, fix_induced: true,  component: src-caller}
  - {id: L2, severity: Low,      aim: instrument, fix_induced: true,  component: src-caller}
deliverable_findings: 0
stopping_rule_triggered: true
```

## The verdict, first

**The redesign did not hold, and it triggers the pre-committed retreat.** The property *"the `/src/`
caller consults the world exactly once, via `src_root()`"* is still unguarded, in both of its
clauses, and one of the two escapes is a **measured regression**: the same mutation is **KILLED at
the parent commit `78100320` and SURVIVES at the delivered tree**.

**The deliverable took no finding, for a third round.** I looked at it directly (§5) rather than
inheriting that verdict. Everything below is about the instrument.

Control: `python3 scripts/explainer-serve.py --self-test` → **150/150 passed**, and 150/150 again
under a non-existent `$HOME`. All sixteen gates green (§6). Every mutation was applied to a copy of
the delivered file, run, and restored by `cp`; `git status --short` was empty at start and end and
`scripts/explainer-serve.py` md5 `30fabdf7cb998f53c89053b832cf029c` throughout. No git command that
can alter a tree was used.

---

## B1 — BLOCKING — a second `src_root()` observation survives, and this is a REGRESSION

**fix-induced: YES**, on the strongest evidence available: the mutation is killed at the parent
commit and survives at the child. The static case is round 2's fix; its incompleteness is a defect
in that fix.

r2's H1 was *"with `src_root` stubbed, calling it twice is free."* The redesign answered it with a
static case at `scripts/explainer-serve.py:2093-2094`:

```python
case("the /src/ branch observes the world EXACTLY once — one src_root() call",
     lambda: _src_branch_src().count("src_root()") == 1)
```

That is a **literal substring count**. One level of indirection defeats it, and the dynamic half
cannot help — because **`_drive_src` still stubs `src_root` (`:2010`)**, which is precisely the
mechanism the architecture review identified as attempt 4's fatal flaw and did not remove.

| mutation in the `/src/` region | delivered `c7a474b4` | parent `78100320` |
|---|---|---|
| `root = src_root().root` — the arch review's headline | **149/150 KILLED** | KILLED |
| `_probe = src_root` / `root = _probe().root` | **150/150 SURVIVES** | **130/133 KILLED** |

At `78100320` it dies by name, on the two cases the redesign deleted:

```
  [FAIL] the caller reads the environment ONCE — src_root is the only reader
  [FAIL] …including on the 404 path, where the help is rendered
```

(That tree's control is 132/133 — one unrelated pre-existing red, constant across both runs, so the
delta is exactly the two cases named.)

**It is a real production defect, not a test artefact.** Driving `do_GET` in the production
configuration — nothing stubbed, nothing forbidden, only a counting wrapper on the real mapping:

```
PRISTINE:     status=200  REAL env reads of EXPLAINER_DOCS_ROOT: 1 ['get']
MUTATION G:   status=200  REAL env reads of EXPLAINER_DOCS_ROOT: 2 ['get', 'get']
```

⭐ **This is r2's H1 repeated one round later, by the same move.** H1 was *"attempt 4 retired the
coverage attempt 2 had bought, and the comment asserted the deleted cases were redundant."* The
redesign retired the same coverage again, kept the stub that makes the defect free, and replaced the
counter with a check that matches the **literal spelling of the mutation that exposed it** — this
project's recorded *assert the PROPERTY, not the mechanism*.

It also refutes a load-bearing sentence in the architecture review
(`docs/reviews/architecture-review-2026-09-15-src-caller.md:80`):

> Both previously-invisible escapes now die, and nothing that was caught stopped being caught.

The second clause is false, measured.

**Falsifier:** apply `_probe = src_root` / `root = _probe().root` to the `/src/` region and run
`--self-test`. If it goes red, this finding is wrong.

---

## B2 — BLOCKING — "never names an environment API, IN ANY SPELLING" is four literal tokens

**fix-induced: YES**, but in a narrower sense than B1, and the distinction is measured rather than
argued. The *escape* is pre-existing — mutation A survives at `78100320` too (132/133, identical to
that tree's control). What the redesign introduced is the **claim of closure**, and the claim is
what made shipping a fifth guard acceptable.

`:2100-2105`:

```python
# ⛔ NO ENVIRONMENT API IN THE REGION, IN ANY SPELLING.
for _api in ("os.environ", "os.getenv", "environb", "putenv"):
```

*In any spelling* is a denylist of four strings. Four genuine second reads of the environment,
placed in the `/src/` region, pass the whole suite:

| # | second read of the environment | result |
|---|---|---|
| A | `from os import environ as _ENV` at module level, `_ENV[SRC_ROOT_ENV]` **in-region** | **150/150 SURVIVES** |
| D | `import posix`, `posix.environ.get(...)` **in-region** | **150/150 SURVIVES** |
| E | `_CACHED_DOCS_ROOT = os.environ.get(...)` at **import time**, used in-region | **150/150 SURVIVES** |
| F | module-level helper reading `os.environb` | **150/150 SURVIVES** |

⚠ **A and D need no helper at all**, so they are not covered by the stated limit at
`architecture-review-…:108-111` (*"the static half cannot see into helpers; that is the dynamic
half's job"*). They are in the region, in plain sight, and the static half reports a pass.

Production-level confirmation for A, counting at the `os._Environ` **class** level so the alias is
visible (`Mapping.get` delegates to `__getitem__`, hence two raw reads per logical consult):

```
PRISTINE:    status=200  env reads (incl. via alias): 2 ['get', 'getitem']
MUTATION A:  status=200  env reads (incl. via alias): 5 ['get', 'getitem', 'get', 'getitem', 'getitem']
```

**The controls all die, so the region is genuinely exercised and the static half genuinely fires:**

| control — the same read, differently spelled | result |
|---|---|
| inline `os.environ.get(...)` | 143/150 killed (6 dynamic + the `os.environ` static case) |
| module-level helper using `os.environ` | 144/150 killed (dynamic only) |
| `from os import getenv as _getenv` | 144/150 killed (`getenv` reaches `os.environ` at runtime) |

⭐ **The structural point, and it is the reason this is Blocking rather than Low.** The architecture
review's central claim is that asking the question statically makes the set **CLOSED**:

> The property is about a **bounded region of code we own** … There is no open set of runtime
> surfaces to enumerate — only the names appearing in a region.

The region is bounded; **the set of ways to name the environment from inside it is not.** Aliased
imports, `posix.environ`, import-time caching and `environb` are four members found in one sitting,
and nothing suggests they are the last. The static half is **attempt 5 of the identical shape** — a
denylist over an open set — relocated from runtime surfaces to source text. That is why B1 and B2
are one root cause with two demonstrations, and why enumerating harder is not the answer here either.

*(A whitelist would be closed — "the region may name only these tokens" — but that is a design
proposal, and per the stopping rule it is explicitly not what this round is for.)*

**Falsifier:** add `from os import environ as _ENV` at module level and read `_ENV[SRC_ROOT_ENV]`
inside the `/src/` branch. If the suite goes red, this finding is wrong.

---

## M1 — MEDIUM — four recorded measurements each reproduce one higher

**fix-induced: yes** (the numbers were written in this round's own commit and review docs).

Every mutation count recorded in `architecture-review-2026-09-15-src-caller.md:71-78` and in
`c7a474b4`'s commit message reproduces at **exactly one more passing case** than recorded:

| mutation | recorded | I measured |
|---|---|---|
| `root = src_root().root` | 148/150 | **149/150** |
| re-read via `os.environb` | 147/150 | **148/150** |
| `SRC_ROOT_ENV in os.environ` | 142/150 | **143/150** |
| `safe_path` bypassed at the caller | 146/150 | **147/150** |

A consistent `+1` across four independent mutations is a systematic recording defect, not four
slips. **No kill/survive verdict changes** — each of those four is still killed, so the substance
holds. It matters because these four numbers are the *evidence* offered for the redesign, in the
document that armed the retreat, and this project's rule is *never write a cost table from memory —
derive, don't store*. The commands are in §7 so the next reader can re-derive rather than trust.

**Falsifier:** re-run the four mutations; if any reproduces at the recorded figure, I mis-measured.

---

## L1 — LOW — the first slice marker fails loud, the second fails SILENT

**fix-induced: yes.** `architecture-review-…:105-107` states the limit as:

> A marker that moves raises inside the case thunk (r4's rule), so it reports as `[FAIL]` rather
> than aborting the suite.

True of the **first** marker, false of the **second**. `_src_branch_src()` (`:2089-2092`) splits on
`'if path.startswith("/src/"):'` then on `"resolved = resolve_page("`.

- Requoting marker 1 to `'/src/'`: **143/150**, six `[FAIL]` lines carrying `IndexError: list index
  out of range` — loud, exactly as designed.
- Changing marker 2 to `resolve_page(path=path, root=ROOT)` — an innocent switch to keyword
  arguments: **150/150, silent.** Measured directly, the region silently widens from **18 to 27
  lines** and swallows the tail of `do_GET`; all six static cases still pass because that tail
  happens to contain neither `src_root()` nor a listed token.

The drift is in the conservative direction (a larger region is checked, not a smaller one), so this
is Low on its own. It is filed because the *stated* limit says both markers fail loud, and a limit
that over-states itself is how round 1's security clause went wrong on this same file.

**Falsifier:** change `resolved = resolve_page(path, ROOT)` to pass keywords; if the suite goes red,
this finding is wrong.

---

## L2 — LOW — `_EXERCISE` binds a surface name to its probe by convention only

**fix-induced: yes** (the derived-population/floor pair is this round's fix for r2 L2/S3).

The per-surface case (`:2161-2163`) looks up `_EXERCISE[n]`, but nothing ties the lambda at key `n`
to surface `n`. Repointing two probes at a *different* surface:

```python
"setdefault": lambda: _fb.get("X"), "pop": lambda: _fb.get("X"),
```

→ **150/150 passes.** Two cases reading *"`_Forbidden` refuses the `setdefault` read surface — the
guard is not vacuous"* and the same for `pop` now prove nothing about `setdefault` or `pop`; they
re-prove `get`. That is the *operands share one closure* shape the comment at `:2150` invokes for
the floor, present one line lower in the map the floor is checked against.

**Contained, which is why it is Low — the ratchet itself holds in both directions.** I tried to
compose it into a real hole and the floor stopped me:

| probe | result |
|---|---|
| remove `pop` from `_Forbidden` | **148/149** — floor red ✓ |
| add `clear = _raise` to `_Forbidden` | **149/151** — reconciliation red + the new surface's own case red ✓ |
| repoint the `setdefault`/`pop` probes **and** remove both surfaces | **147/148** — floor red ✓ |

So r2's S3 repair works: a surface cannot silently disappear. Only the *claim each case makes about
itself* can go stale.

**Falsifier:** repoint `_EXERCISE["pop"]` at `_fb.get("X")`; if the suite goes red, this is wrong.

---

## 5 — The deliverable, examined directly

**No findings.** The brief asks whether three clean rounds mean it is right or that nobody looked, so
I looked rather than inheriting the verdict: `SrcRoot` (`:481-511`), `src_root` (`:519-541`),
`src_root_help` (`:544-585`), `_gone_checkout_help` (`:588-618`), and the `/src/` branch of `do_GET`
(`:1134-1150`).

It is right. The carried-observation design closes the class the docstring names — every field is
read once at probe time, `src_root_help` branches on `observed.fallback_ok` rather than re-probing
(`:575`), and `_gone_checkout_help` describes what was seen without naming a cause. Pre-existing
coverage is intact, not hollowed by the redesign:

| pre-existing mutation | result |
|---|---|
| `safe_path` bypassed at the caller | 147/150 killed |
| master's unfilled `<dir>` 404 text restored | 148/150 killed |
| `SRC_ROOT_ENV in os.environ` in the region | 143/150 killed |

Two things I checked and am **not** filing, stated so the next reviewer need not re-derive them:
`"raw=1" in <query string>` (`:1147`) is a substring test that `?notraw=1` also satisfies — same
file either way, loopback dev server, no consequence; and `target.relative_to(root.resolve())`
(`:1149`) is safe only because `safe_path` resolves both sides, which the Q4a mutation demonstrates
by raising `ValueError` the moment it is bypassed — the coupling is real but the guard is present
and cased.

Not re-filed, per the brief: backlog **#122**, **#123**, **#125/#126/#127**, **#128**, and r1's L4.

---

## 6 — Gates

All green at `c7a474b4`, run from a clean tree:

| gate | result |
|---|---|
| `explainer-serve.py --self-test` | **150/150** |
| …under `HOME=$(mktemp -d)/.home` | **150/150** |
| `check-fixture-variation.py --self-test` | 67/67 |
| `gen-dashboard.py --self-test` | 325/325 |
| `check-plan-code.py --self-test` | 128/128 |
| `check-docs.py` | rc=0, Documentation integrity OK |
| `check-selftest-counts.py` | rc=0, 39 scripts, every count verified by running it |
| `check-ratchet-contract.py` | rc=0, 36 guards, contract OK |
| `check-review-rounds.py` | rc=0, 252 parsed, 0 silent gaps |
| `check-arch-findings.py` | rc=0, 2/18 criteria, 0 regressed |

---

## 7 — How to reproduce

Mutations were applied to a copy of the delivered file via a harness that refuses to run unless the
tree matches a pristine md5, reads the **`N/M passed` line** for its verdict (never a grep for
FAIL-shaped tokens — r2's coordinator defect), restores by `cp`, and re-checks the md5. Harness and
specs: `…/scratchpad/mutate.py`, `m{A,C,D,E,F,G,G0,B1,B2,R1,R2,R3,R4,Q4a,Q4b,Z1,Z2}.json`.
Production-level env counting: `…/scratchpad/prod_probe.py` (object level) and `prod_probe2.py`
(`os._Environ` class level, so a module-level alias is counted).

The pre-redesign comparisons used `git show 78100320:scripts/explainer-serve.py` written **outside
the repo** and run with `PYTHONPATH=<repo>/scripts`. No checkout, restore, stash, reset, add or
commit was performed; no process was killed; no port was bound.

---

## Q4 / Q5 — convergence

**CONVERGED: NO.**

Two Blocking findings, both fix-induced, both in `src-caller`, one of them a measured regression
against the parent commit.

⛔ **The pre-committed stopping rule is triggered, and I am reporting it as binding rather than
proposing a sixth guard.** `ship-src-root-alone-r2-coordinator.md:153-159` says that if round 3
finds another fix-induced defect in `src-caller` caused by the redesign, the answer is to **delete
the "consulted the world exactly once" property from this suite**, state in the comment that it is
unguarded and why, and let the behavioural cases stand alone.

B1 meets that condition on the narrowest possible reading — the defect is in code the redesign
wrote, and the same mutation dies at the parent commit. B2 supplies the reason it will keep
happening: the static half is a denylist over an open set, which is the shape that has now failed
**five** times in this component.

I am **not** sketching a fix, deliberately. Two observations for whoever executes the retreat:

1. The **behavioural** cases are sound and should stand — `/src/` resolving a root with nothing set,
   the 404 rendering the pasteable help, confinement over a real target outside the root. They are
   what caught the four-day outage, and none of them depends on the property being retired.
2. The comment that replaces the property should record that **`_drive_src`'s stub of `src_root`
   (`:2010`) is what makes a second call free**. If the stub survives the retreat without that
   sentence, the next reader will assume `_Forbidden` still covers the caller, which is the belief
   B1 measures as false.

M1, L1 and L2 are independent of that decision and can be taken or declined on their own merits.
