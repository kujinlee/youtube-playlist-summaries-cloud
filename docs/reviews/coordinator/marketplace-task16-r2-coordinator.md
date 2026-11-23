# Round 2 — `marketplace-task16` — coordinator — NOT CONVERGED (Codex): the r1 fold's install-root rule judged a derived root too early and filed `nonlocal` one level out

Codex ran on 3188ca5e (the r1 fold, scanner at 3db9d353): `docs/reviews/codex/marketplace-task16-r2-codex.md`, 2 MAJOR,
self-test 116/116, its fresh scan identical to the committed one apart from `measured_at`.

REVIEW GAP: claude — alternation.

**Both r2 findings were caused by the r1 fold, in detector 2's install-root rule** (`_inert` and `_Scopes.owner`). That
is the thrashing signal the r1 coordinator named: the r1 bet in the decision log is LOST. The r1 fold accreted. Retrying
`accrete` on the same unit is the repeat the decision ladder refuses, so this fold restructures the rule instead (route
`redesign`).

**Design chosen.** The r1 rule judged the root at its *immediate parent* and skipped a listed set of parents ("inert").
A value that kept flowing past a listed parent was hidden, and X1 is two instances of that (an f-string, a `relpath`).
Two fixes were weighed:

- **A sink list**, the inversion the brief proposed: report only when the root reaches a listed sink (`cwd=`, `chdir`,
  `open`, a return, a path argument). It fails toward **no finding**. A sink nobody listed is silent, and that is X1's
  failure direction. For a publishability scan, a false negative means a component is published broken.
- **Chosen: derivations as path forms, judged at the terminal use.** Every listed derivation is now a from-file path in
  `_from_file`: an f-string (its first piece joined with a `/` tail), `str`, `os.fspath`, `relpath` without a root
  start, `joinpath`, plus the existing `/`, `os.path.join`, `.parent`, `dirname`, `.resolve()`. So the expression
  judged is the outermost one still derived from the root. `_inert` reads only that terminal use, and **every terminal
  it does not list is reported**. A wrapper not on the derivation list is judged as an argument handed on, and it is
  reported (the `shlex.quote(str(ROOT))` case). Both lists therefore fail toward a **finding**. X1's class, where a
  derivation hides a root that is handed on, cannot recur by omission. An omission now costs one false positive, which
  a reader sees. The direction is stated in the code at *THE DERIVATIONS*.

```yaml
round: 2
fixes_nontrivial: true
subject: marketplace-task16
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: Major, aim: deliverable, fix_induced: true, component: publishability-install-root, disposition: fixed}
  - {id: X2, severity: Major, aim: deliverable, fix_induced: true, component: publishability-install-root, disposition: fixed}
```

| # | Severity | Finding | Disposition |
|---|---|---|---|
| X1 | MAJOR (r1-fold-caused) | The inert list hides a root handed on through an f-string (`subprocess.run(["git"], cwd=f"{ROOT}")`) or `os.chdir(os.path.relpath(ROOT))`. | **Fixed by redesign** (above). Fixed in 2f4b59ce. Four cases: each of the two inputs, RED first and now `(3, ".")`. A derivations case (a bound and joined f-string, `joinpath`, `os.fspath`, an unlisted wrapper reported), RED first. The adjacent negative (a root only compared; only printed through an f-string, `str()` or `os.fspath()`; only measured against by `relpath`'s start, positional or `start=`) gives `[]`. It passed before the change and is a regression lock. |
| X2 | MAJOR (r1-fold-caused) | `nonlocal` stores are filed under the immediately enclosing function, not the one Python resolves (a → b → c, `nonlocal root` in c rebinding a's). | **Fixed.** `_Scopes._nonlocal` walks outward to the nearest enclosing function that binds the name itself. A function that declares it `nonlocal` too passes it further out. `global` already went to module scope. One case with three shapes, RED first (got `docs/x.md` at :10): a middle function that does not bind the name, so no finding; one that does, so `docs/y.md`; and one that declares it `nonlocal` too, so no finding. |

**Cases and mutations.** The self-test went from 116 to 121 cases. The pin in `expected_mutations.py` went from 226 to
237. The code of four r1 entries no longer exists, and each was replaced with an entry on its successor: the `nonlocal`
owner, the comparison, the f-string piece, `str()`. Eleven entries were added, one per new branch. Each of the 15 went
red on its named case on a scratch copy, and so did the 59 existing detector-2 mutations, re-run. Every anchor in every
manifest resolves exactly once. Two branches have no mutation: `joinpath` with a non-literal part (the mutation crashes
in `_placed`, so its red would prove nothing), and `_nonlocal`'s fallback for a name no enclosing function binds
(Python refuses that source as a SyntaxError).

**The rescan against the previous scan:** 365 findings before and after, **none gained or lost**, and the mentions are
unchanged. The zero was checked rather than assumed. The 28 shipped `.py` files hold no f-string over a file-derived
root, no `joinpath`, and no multi-level `nonlocal` that rebinds a root. Their two `relpath` calls do not take the root.
So the fixture cases are the only witnesses of the new rule. `scan-2026-11-21.json` was regenerated at 2f4b59ce, and only
its `measured_at` changed. Tier A's L5 limit now states the terminal-use rule and the `nonlocal` resolution, and both
records cite the new commit.

**Thrashing watch for r3 (Claude, alternation):** r2 is the first round whose findings came from the previous round's
fold. If r3 finds a defect caused by *this* fold in `_from_file`'s derivations, `_fstring_path`, `_inert` or
`_Scopes._nonlocal`, that makes two consecutive such rounds in one component, and Phase 6 convenes. The bet is in the decision log.
