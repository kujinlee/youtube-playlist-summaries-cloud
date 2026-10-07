<!-- codex-review: model=gpt-5.5 -->

**Verification**

Ran all required commands at `835d2e65` on `d2-main-drivable`; working tree was clean.

```text
$ python3 scripts/check-main-drivable.py --self-test
<unknown>:10: SyntaxWarning: "\s" is an invalid escape sequence...
438/438 passed
```

```text
$ python3 scripts/check-main-drivable.py
44 guards on disk · 7 without main() (outside the population) · 37 in population
  10 drive main() over a constructed world — param 3, argv 3, rebind 8, subproc 1 (a guard may take more than one route, so these need not sum)
  27 pinned as ADR-0014 identity debt
D2 OK — every guard with a main() either drives it over a constructed world or is pinned.
```

```text
$ python3 scripts/check-main-drivable.py --report
44 rows emitted; summary:
44 guards on disk · 7 without main() · 37 in population
10 compliant · 27 pinned debt
routes: param 3, argv 3, rebind 8, subproc 1
```

```text
$ python3 -c "import json;print(len(json.load(open('scripts/mutations/check-main-drivable.json'))))"
183
```

I also independently imported the script and ran `classify()` over all 44 `scripts/check-*.py` files: `44` rows, `37` in population, `10` compliant, `27` debt, `7` no-main. I did not run `python3 scripts/check-plan-code.py --mutate .`, per instruction.

**Findings**

None.

No Blocking / High / Medium / Low findings. I found no live false green in the fold, and no candidate fix to apply. Therefore there is no blast-radius table for findings; the measured live population remains unchanged at 10 compliant / 27 debt / 7 outside population.

**Design Verdict**

1. **The property is the right property.** For the rebind route, the question is not “does this expression mention a case-bound name?” but “does this substitution hand `main` the same world global it already had?” That matches the module-dict branch’s existing identity comparison and removes the round-10 proxy.

2. **The residual leaf test is acceptable as residual, not the old proxy under a new name.** It now fires only after the rule has failed to follow provenance through a `Name` or resolvable `Call`. I probed the boundary with helper-wrapped `os.path.join('.', x)` and `os.path.relpath(x)`: direct spellings earn `rebind`; helper-wrapped spellings refuse. That is a lost-credit boundary, not a false credit.

3. **The boundary is one-hop/static provenance, and the miss direction I measured is safe.** `hands_back_the_same_world` follows names through bindings and calls through `_resolve_callee` in the callee’s scope. One hop past that, it can refuse credit for a value that would dynamically resolve to the tempdir. I did not find a case where that boundary grants false credit.

4. **The implementer was right to refuse the coordinator’s brief.** Independently measured:

```text
os.path.join('.', td) == td -> True
abspath(relpath(td)) == td -> True
realpath(relpath(td)) == realpath(td) -> True
```

So the literal `return bool(yielded) and yielded != {name}` would have refused cases that do hand `main` the tempdir the case built. The fold’s 3-of-5 closure is intentional and, on this evidence, correct.

**What I Tried To Refute**

I tried to refute the redesign by pushing one hop beyond its resolver: lambda-returning-`ROOT`, nested helper returning `ROOT`, helper returning `join('.', x)`, and helper returning `relpath(x)`. The identity cases refused credit; the helper-wrapped ambient-path cases also refused credit. That found the stated conservative boundary, not a false green.

I also rechecked backlog #224’s parked shapes (`'.' + ''`, `not False`, `1 and 2`) against `ast.literal_eval`; all raise `ValueError`, matching the park rationale rather than producing a new structural finding.

**Q4(a) Convergence Table**

No findings.

| Severity | Aim | Caused by round 10 fold’s own fix? |
|---|---|---|
| none | n/a | n/a |

Final verdict: **NOT CONVERGED**. This round is clean, but `docs/review-method.md` requires two consecutive quiet rounds before stopping.
