# Round 3 — `held-pins-head` (PR #541, backlog #538) — coordinator — NOT CONVERGED; THRASHING → Phase 6

REVIEW GAP: codex — alternation

```yaml
round: 3
fixes_nontrivial: true
subject: held-pins-head
halves:
  codex: gap
  claude: ran
findings:
  - {id: C-F1, severity: Medium, aim: deliverable, fix_induced: true, component: isolation, disposition: fixed}
  - {id: C-F2, severity: Low, aim: deliverable, fix_induced: true, component: isolation, disposition: fixed}
  - {id: C-F3, severity: Low, aim: deliverable, fix_induced: true, component: isolation, disposition: fixed}
```

Claude (`docs/reviews/claude/held-pins-head-r3-claude.md`) reviewed `9f12aea5`, the child-process redesign.

- **C-F1 (Medium, a real loosening against master).** The driver puts HEAD's `scripts/` FIRST on `sys.path`, and only
  then imports `importlib.util`. A committed `scripts/importlib/__init__.py` therefore runs before the harness and
  forges the JSON the child prints. Measured: master reports `drops 5 -> 4`, the branch reports `falls: []`, and a
  control commit that removes only that directory makes both report the fall. Five flagged ids were answered
  `finding` on this.
- **C-F2 (Low).** The timeout's group kill is not tested: `killpg` → `pass` survives. A `setsid` grandchild escapes
  the kill, and `communicate()` then waits on it without a bound. This fails closed, but it can hang.
- **C-F3 (Low).** The duplicate-key refusal is not tested.

**THRASHING.** r2's findings came from r1's fold, and r3's come from r2's, all in the isolation component. Phase 6
is armed: `docs/reviews/architecture-review-2026-11-08-held-pins-child.md`. The class has shrunk from "anything in
the process" to "HEAD's `scripts/` shadows a name the child resolves". The question for Phase 6 is whether
APPENDING `scripts/` after the stdlib, instead of prepending it, removes that class by construction, for the
driver's imports AND the harness's own stdlib imports, or whether something else is needed.

## Phase 6 outcome

The review is `docs/reviews/architecture-review-2026-11-08-held-pins-child.md`. It chose design (c): any materialised
top-level name under HEAD's `scripts/` that is a standard-library module is refused, CANNOT RUN. That closes the
child route by construction, whatever the `sys.path` order. The driver's order is unchanged. Appending `scripts/`
was rejected: the harness re-prepends its own directory, and 3 of 95 shadows (`msvcrt`, `nt`, `_winapi`) still ran.

**R3-F1's "loosening against master" is refuted for master's real entry point.** Master's gate process, started as
`python3 scripts/check-merge-ready.py`, puts the WORKING TREE's `scripts/` first on `sys.path`. Measured:
- its real entry point (`--help`) executed a committed `scripts/importlib/__init__.py`;
- master's gate code executed 51 of 95 stdlib-named files, and the branch's child 48, all among master's 51.

So the class is pre-existing in master's gate process. It is filed as backlog #578 and is not folded here.

**The five r3 `finding:` answers will be re-answered by the next review round**, against the gate as it is actually
invoked: `46da71649200`, `ed1d0f2f0938`, `3e8b51e50547`, `be450713bce4` and `c47564441466`. Each rests on "master
never executed it", which the measurement above refutes.

The fold also bounds the wait after the timeout's group kill (R3-F2: `CHILD_GRACE`, with a `setsid` case), pins the
duplicate-key refusal (R3-F3), and deletes the untested NaN refusal. check-merge-ready 392 -> 400 cases; mutations
181 -> 187.
