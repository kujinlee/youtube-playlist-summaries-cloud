# Round 1 — speed-main-drivable — claude

Subject: branch `speed-main-drivable` at `1accbd93` (PR #449, backlog #401), against `origin/master`.
Scope: the brief's (1) and (2) in depth, plus (3)/(4) measurements. **The 25-minute
`check-plan-code.py --mutate . --only scripts/check-main-drivable.py` sweep was NOT run by this half**
(the coordinator assigned it to Codex), so this review says nothing about mutant kills beyond one
targeted check below.

All experiments ran on copies under `scratchpad/r401c/`; the worktree was not edited (`git status`
clean after every run).

## What was run

| Check | Result |
|---|---|
| `--self-test` on the branch, Python 3.14.4 | **441/441 passed**, rc 0, 10.1 s, peak RSS 173 MB |
| `--self-test` on the branch, Python 3.12.9 (CI's) | **441/441 passed**, rc 0, 9.7 s, peak RSS 168 MB |
| `--self-test` on `origin/master` (copy of `scripts/` with master's file), 3.14 / 3.12 | 438/438, **78.6 s** / **84.0 s**, peak RSS 124 / 119 MB |
| Differential, every memoised helper, cached vs decorator-stripped, 3.14 and 3.12 (`r401c/diff_helpers.py`) | **90,604 comparisons, 0 differing results** on each Python |
| Live run as CI runs it (`assess(texts, MAIN_DEBT, whole=True)` over the 55 `scripts/check-*.py`), master vs cached vs uncached, 3.14 and 3.12 (`r401c/live.py`) | **6 of 6 outputs identical** after canonicalising frozenset print order; 0 problems in each |
| Live-run time, master → branch | 3.14: **68.6 s → 6.8 s**; 3.12: **93.0 s → 12.5 s** |

### The differential, in detail

`uncached.py` is the branch file with its six `@_memo_by_node` lines deleted (verified: 6 → 0), so
the only difference is the cache. Both modules are called on the SAME tree objects; answers are
normalised to node identities (`id`) and values; the cached helper is called twice (miss, then hit)
and both must equal the uncached answer.

- **Phase A**, all 87 `scripts/*.py`, trees kept alive (as `assess` does): `_all_functions`,
  `note_globals_imports`, `_class_methods`, `_defs_in_scope(tree)` per tree; `_own_scope` and
  `_defs_in_scope` on every `FunctionDef`/`AsyncFunctionDef`/`Lambda`/`ClassDef`; `_bound_values(n, fn)`
  for EVERY `Name.id` appearing in each such node; plus `_own_scope(None)` and `_bound_values(n, None)`.
  42,548 comparisons.
- **Phase B**, 40 files re-parsed and DROPPED per pass, twice, with `gc.collect()` between — the
  address-reuse hazard.
- **Phase C**, 300 same-shaped synthetic trees (a `globals` alias, a class with a method holding a
  nested def, a function binding `td` by `=`, by `with … as`, and through a `nonlocal` writer), each
  dropped after use.
- Per helper: `_bound_values` 71,035; `_own_scope` 9,084; `_defs_in_scope` 9,084; the three per-tree
  helpers 467 each. **Differing: 0** (3.14.4 and 3.12.9).

### (1) Can a cached answer differ from the uncached one?

I could construct exactly ONE sequence that does it, and it needs something no caller does — see
Minor M1. Each other hazard the brief names was checked and does not apply:

- **Impure helpers.** All six read only their arguments: `ast.walk`/`iter_child_nodes` plus attribute
  reads, and `_bound_values` calls `_own_scope` and `_unpack`. None reads a global that changes,
  the filesystem, or mutable state.
- **An id reused because the entry does not hold every argument.** The entry stores `(args, out)`,
  and every AST argument is in `args`. The only non-AST arguments are `name: str` and `fn=None`, both
  keyed by value. Phases B and C, which drop each tree, found 0 differences.
- **A key that omits an argument that changes the result.** The key is every positional argument.
  `grep` finds no keyword call to any of the six helpers, and a keyword call would raise `TypeError`
  rather than miss the cache.
- **Freezing changing a caller's behaviour.** Every caller iterates, indexes, tests membership or
  truthiness, or wraps in `frozenset(...)`/`set(...)`: `:503`, `:540`, `:573`, `:1217`, `:1477`,
  `:1728`, `:1752`, `:1903`, `:2033`, `:2185`, `:2293`. At `:2185` the result is used in
  `callee & (A | B | aliases)`, and a frozenset gives the same answer there as the set it replaced.
  The pre-existing cases at `:3512`/`:3514` compare the result with a `set`, and
  `frozenset == set` is True.

**The mutant that stops an entry holding its nodes is killed reliably, so the new identity case does
not pass for an ambient reason.** `r401c/noholds.py` (`(args, out)` → `(None, out)`) run over the
case's own 256-tree expression, 20 runs each: on 3.14, 248–253 of 256 answers wrong; on 3.12,
**40–248 wrong, never 0**. The unmodified branch gave 0 wrong in 5 of 5 runs on each Python. The
case's comment claims "9 to 58 of 64", which is consistent with these numbers.

### (2) The live run, and the other importer

- **ci.yml:717** runs `python3 scripts/check-main-drivable.py`. Its live path (`assess` over the
  population) gives byte-identical verdicts on master, the cached branch and the uncached branch, on
  both Pythons.
- **`check-fixture-git-isolation.py:208`** is the only importer outside this file. It calls
  `suite_entries(tree)` alone, which returns a fresh `set` (`out |= …`). It never sees the frozen
  `_all_functions` mapping, and it neither mutates the trees nor their answers: a `grep` for
  `NodeTransformer`, `fix_missing_locations` and `.body` assignment or `insert`/`append` returns
  nothing. Its `_main_drivable()` is `functools.cache`d (`:177`), so ONE module instance and ONE memo
  last for the whole process. That is safe for correctness, because the keys are identities of live
  trees, but it is where memory accumulates (M2).

## Findings

### Minor M1 — the memo's soundness rests on an unstated invariant: a tree is never mutated after a helper first sees it

`scripts/check-main-drivable.py:314` (`_memo_by_node`). The docstring explains why identity keys are
safe (the entry keeps the nodes alive) and freezes the ANSWER against a mutating caller. It says
nothing about the ARGUMENT. A tree changed in place after its first lookup gets the stale answer.
Constructed, and run (`r401c/stale.py`):

```
t = ast.parse("def main(argv=None):\n    return 0\n")
note_globals_imports(t); _all_functions(t)         # prime: set(), {'main'}
t.body.insert(0, <from builtins import globals as gl>)
t.body.append(<def _self_test(): pass>)
cached:   note_globals_imports -> set()   _all_functions -> {'main'}
uncached: note_globals_imports -> {'gl'}  _all_functions -> {'main', '_self_test'}
```

**No caller does this today.** A `grep` over this file and its importer finds no `NodeTransformer`,
`fix_missing_locations`, `.body` assignment or `insert`/`append`, or AST attribute assignment. The
differential above confirms the repository's real call pattern gives 0 differences. Severity is Minor
because nothing reaches this path. The fix is one docstring line, so that a future caller that
annotates or rewrites trees (a common pattern) knows the memo silently forbids it: *"a tree must not
be mutated after any memoised helper has seen it; the answer would be the pre-mutation one."*

### Minor M2 — memory: +~49 MB on the suite, and an unbounded memo in a process that imports the module once

`_memo_by_node` has no bound; `_parents` beside it is `lru_cache(maxsize=16)`. The suite parses
hundreds of synthetic trees, and every one stays alive for the life of the process. Measured peak
RSS for the suite: 124 → 173 MB (3.14) and 119 → 168 MB (3.12). For the live run on 3.14: 104 →
120 MB. On 3.12 the live run went 101 → 87 MB, which is GC noise; the memo did not shrink anything.
Each run is bounded by its own input, so this is acceptable for a CLI. **A long-lived importer would
grow without bound:** `check-fixture-git-isolation` caches the module (`:177`), so every tree it hands
`suite_entries` stays alive until it exits. Its run is also bounded by its population, so this is not
a defect today. I did NOT measure that importer's RSS.

The docstring cites `_parents` for the id-safety argument, and the citation is correct. The reader
should not also infer `_parents`' bound from it, so stating "unbounded, per process, by design" would
close that gap.

## Not covered by this half

- The full mutation sweep (189 entries) was not run here; Codex runs it.
- Speed on an actual GitHub runner was not measured. Local 3.12.9 is the closest proxy I have: suite
  84.0 s → 9.7 s, live run 93.0 s → 12.5 s.

## Verdict

**CONVERGED** — 0 Blocking, 0 Major, 2 Minor (M1 a docstring line, M2 a docstring line plus no
change). The differential over every memoised helper found 0 differing results in 90,604 comparisons
per Python, on 3.14.4 and 3.12.9. The only divergence I could construct needs in-place tree mutation,
which no caller performs.
