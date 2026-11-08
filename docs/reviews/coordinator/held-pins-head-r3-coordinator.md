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
