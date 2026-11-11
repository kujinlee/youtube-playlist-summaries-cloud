# Round 3 — `suite-cost-a` (PR #537, backlog #231) — coordinator — Claude NOT CONVERGED; THRASHING armed Phase 6, and the goal-tree sibling cache was REDESIGNED to live only in the self-test's sweep

```yaml
round: 3
fixes_nontrivial: true
subject: suite-cost-a
halves:
  claude: ran
  codex: gap
findings:
  - {id: R3-F1-claude, severity: Medium, aim: deliverable, fix_induced: true, component: goal-tree-sibling-cache, disposition: fixed}
  - {id: R3-F2-claude, severity: Low, aim: deliverable, fix_induced: false, component: goal-tree-sibling-cache, disposition: fixed}
  - {id: R3-F3-claude, severity: Low, aim: deliverable, fix_induced: true, component: goal-tree-sibling-cache, disposition: fixed}
  - {id: R3-F4-claude, severity: Low, aim: deliverable, fix_induced: true, component: goal-tree-sibling-cache, disposition: fixed}
  - {id: R3-F5-claude, severity: Low, aim: deliverable, fix_induced: false, component: goal-tree-sibling-cache, disposition: fixed}
```

REVIEW GAP: codex — alternation

Claude ran (`docs/reviews/claude/suite-cost-a-r3-claude.md`, NOT CONVERGED). Round 3 runs one half by alternation
(`docs/review-method.md` → *Round topology*). All five findings are in `scripts/goal-tree.py`'s sibling cache.

- **R3-F1 (Medium, fix_induced: yes):** the stack pop that r2 put in `finally` had no case; moving it out survived,
  and the consequence was a stale `.pyc` served after any failing import.
- **R3-F2 (Low, fix_induced: no):** two goal-tree INSTANCES importing in two threads still leaked the bytecode
  settings. Keys stayed sound.
- **R3-F3 (Low, fix_induced: yes):** a sibling whose import starts a thread that calls `_sibling` and joins it
  deadlocks on r2's lock.
- **R3-F4 (Low, fix_induced: yes):** r2's threads case killed the no-lock mutant only if T2 started within 0.2 s.
- **R3-F5 (Low, fix_induced: no):** a failing outermost import's settings restore had no case.

## THRASHING, so Phase 6 ran before the fold

r2's findings were caused by r1's fold and r3's (F1, F3, F4) by r2's, in one component, `goal-tree-sibling-cache`.
That is the arming condition (`docs/dev-process.md` → *Phases*). The narrow review is
`docs/reviews/architecture-review-2026-11-08-goal-tree-sibling-cache.md`. Its verdict: **a redesign removes the class**.
Every finding from r1 to r3 needed a constructed caller (one that rewrites files while still asking, re-enters, or
overlaps imports), and the only caller that needs the cache is the self-test.

## The fold: the memo exists only inside `_sibling_sweep()`, which only the self-test opens

- Outside a sweep, every `_sibling` call is a fresh import, as on master. The sibling's own bytes are compiled
  directly (`compile(..., dont_inherit=True)`), so it never runs a stale `.pyc` (r1 Claude F2 stays fixed) and no
  process-wide setting is touched.
- Inside a sweep, a sibling is imported once per path. The bound: the sweep reads the tree as it stood when it
  started; a rewrite during a sweep is out of scope. No case rewrites a real sibling or patches a sibling's
  attribute (checked by `grep` at this fold).
- Removed: the audit hook, the read-list stack, the lock, and the save and restore of `sys.dont_write_bytecode` and
  `sys.pycache_prefix`.
- `_self_test` stays one `with fixture_git.isolated(): return _self_test_body()`; `_self_test_body` runs the outside
  probe, opens the sweep, and calls `_self_test_cases`. The first shape opened the sweep inside `_self_test` itself,
  and `check-fixture-git-isolation.py` refused it, because a case also reaches `_sibling_sweep` outside that block.

Dispositions, all `fixed` because the code each was about is gone or the lesson is applied:

| Finding | Disposition |
|---|---|
| R3-F1 | The stack is gone. The lesson (a restore in `finally` needs a case that raises) is applied to the one restore left, `_sibling_sweep`'s: a case that raises inside a sweep, and two mutations |
| R3-F2 | Dissolved: no import changes a process-wide setting, so two instances cannot leak one. No backlog row needed |
| R3-F3 | Dissolved: there is no lock |
| R3-F4 | Dissolved: the threads case went with the lock |
| R3-F5 | The settings restore is gone; see R3-F1 |

## Cases (437 → 438) and mutations (337 → 336; master 325)

Nine backlog #406 cases are replaced by ten (listed in the architecture review, §4). Four of them observe a caller
OUTSIDE a sweep through `_sibling_outside_probe()`, which `_self_test_body` runs before it opens its sweep, so they see the
module's own default state.

The twelve backlog #406 mutations named code that no longer exists, and are replaced by eleven. Each was applied to a
fresh `git archive HEAD scripts docs` stage with the fold's `goal-tree.py` copied in (no `__pycache__`,
`PYTHONDONTWRITEBYTECODE=1`). The check was suite rc 1 AND `parse_fail_names` (imported from
`scripts/check-plan-code.py`) equal to the entry's `expect`. All eleven: OK.

| Mutation | rc | `parse_fail_names` |
|---|---|---|
| the memo is never consulted | 1 | the same sibling twice is ONE import; a NESTED sweep shares the outer memo |
| a miss is never stored | 1 | the same two |
| the memo is ON by default | 1 | the four OUTSIDE-a-sweep cases |
| the memo is keyed on the name | 1 | one name in two directories is two imports |
| the sibling is loaded through its `__pycache__` | 1 | OUTSIDE a sweep, a SAME-SIZE rewrite … never a stale .pyc |
| the sweep's restore is not in `finally` | 1 | a sweep that RAISES leaves no memo on |
| the sweep never restores | 1 | a sweep that RAISES leaves no memo on |
| a nested sweep starts its own memo | 1 | a NESTED sweep shares the outer memo |
| the outside probe is taken INSIDE the sweep (the call site) | 1 | the four OUTSIDE-a-sweep cases |
| the self-test body runs outside any sweep (the speedup unwired) | 1 | the same sibling twice is ONE import; a NESTED sweep shares the outer memo |
| the sibling compiles under goal-tree's `__future__` flags | 1 | a sibling compiles as ITSELF |

## Measured (goal-tree suite, no `__pycache__`, `PYTHONDONTWRITEBYTECODE=1`, interleaved, load 48 → 20)

| Run | origin/master | r2 fold (`2af17adf`) | this fold | no memo at all |
|---|---|---|---|---|
| 1 | 21.89 s | 2.94 s | 2.34 s | 21.32 s |
| 2 | 17.49 s | 2.10 s | 1.95 s | 14.46 s |
| 3 | 13.57 s | 2.38 s | 2.25 s | 14.93 s |

"This fold" was timed at 437 cases, before the `__future__` case was added. "No memo at all" is this fold with the
sweep switched off: compiling from source without the memo gives none of the speed.

## Decision log

The `accrete` row for `suite-cost-a` is scored `continued`: r3 brought fix-induced findings in this component, and
R3-F2 refuted the prediction's literal wording. A PROSPECTIVE `redesign` row is appended for the same unit.

## Next

Round 4 runs ONE half by alternation: the Codex half. From round 4 findings are FILED unless BLOCKING
(`docs/review-method.md` §0 Q4c); the architecture review's §5 states what is a BLOCKER in this component.
