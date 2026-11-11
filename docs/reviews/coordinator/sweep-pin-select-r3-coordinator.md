# Round 3 — `sweep-pin-select` (PR #526, backlog #533) — coordinator — NOT CONVERGED (Claude); one fix-induced Low FIXED BY REDESIGN, one Info (recorded as Low) DECLINED

Claude half: `docs/reviews/claude/sweep-pin-select-r3-claude.md` (NOT CONVERGED), on `248172e0`.

```yaml
round: 3
fixes_nontrivial: true
subject: sweep-pin-select
halves:
  claude: ran
  codex: gap
findings:
  - {id: R3-F1, severity: Low, aim: deliverable, fix_induced: true, component: merge-ready-pins, disposition: fixed}
  - {id: R3-F2, severity: Low, aim: deliverable, fix_induced: false, component: merge-ready-pins, disposition: declined}
```

REVIEW GAP: codex — alternation (r3 runs ONE half).

**The round armed Phase 6.** R3-F1 was caused by r2's fix, and r2's F2 by r1's fix, both in `merge-ready-pins`:
two consecutive fix-induced rounds in one component, which is THRASHING (`docs/dev-process.md` → *Phases*). The
narrow architecture review, `docs/reviews/architecture-review-2026-11-06-sweep-pin-select.md`, found the cause: the
check proved a property of the harness's SPELLING ("writes `PINS_FILE` once, at module level, as this literal"), when
the claim is about its VALUE. Its verdict was option (e), filed as backlog #536. This fold builds (e) instead of the
one-token fix the r3 half proposed, which would have been option (d) and would have continued the thrash.

**R3-F1 — FIXED BY REDESIGN (backlog #536).** A `global PINS_FILE` in a CLASS body rebound the global and was not
counted by `module_writes`. The component that missed it is deleted: `PINS_BINDING`, `_SCOPES`, `module_writes`,
`harness_binding_problems`, `harness_binds_pins`, their cases, and their 5 mutations (3 from r1, 2 from r2). In its
place, `held_pins` reads `EXPECTED_MUTATIONS` from the head harness that `_pins_reader` already imports for
`pin_display`, through `_cross` and `_exact_pins`, and `pin_pair` raises `PinsUnreadable` (CANNOT RUN) naming each
target whose held and displayed values differ, over both sides' keys. A head with no pins at all is not compared;
every pin it drops is HELD, as before.

Test-first. Each case runs the REAL harness, edited, through a real import in a temp working tree that holds the
unchanged pins file and a `pins_v2.py` with `check-anchors.py` lowered 5 → 4. Before the change 16 cases were red
(247/263): the three new `pin_pair` cases, the new `main()` route case, and 12 existing `main()` cases, whose fake no
longer answered the static check's `git show`. After it, 263/263:
- R1 to R7 (plain rebinding, `globals()`, an import, the class-body `global`, `own_pins_path`, a module
  `globals()['EXPECTED_MUTATIONS']`, `exec`) are each CANNOT RUN, naming `check-anchors.py (held 4, displayed 5)`;
- a redirect to a pins file that DROPS the target is CANNOT RUN (`held None, displayed 5`);
- L0 to L4 (the real harness, a helper's local, a class attribute, and r3's two falsely refused shapes) hold nothing;
- R1, R2, R4 and R5 through the real `main()` are rc 2, naming the target.

The legacy synthetic cases now read through a temp working tree holding HEAD's display, because the reader IS the
working tree at the PR head; none of their expectations changed.

The remaining routes are written as a BOUND comment at the comparison: R8 (a write in a function called at run time,
master's E2), R9 (a rebinding under `__main__` or a branch on `sys.argv`) and R9b (the same through `globals()`). They
are backlog #535's class, now narrowed to it.

Three mutations, each applied to a copy of the working tree's `scripts/` with `HOME` redirected. Each turned its
named case red; the unmutated control had 34 reds, none of them a named case (they come from the copy holding only
`scripts/`, with no `docs/` or git context):
- the comparison skipped: R1–R7 red (36 reds);
- the comparison inverted: L0–L4 red (50 reds);
- reading only the held side's keys: the DROPS case red (35 reds).

Self-test: `check-merge-ready` 265 → 263. Pin: `scripts/check-merge-ready.py` 104 → 102 in
`scripts/mutations/expected_mutations.py`.

**R3-F2 — DECLINED.** The half labelled it Info; the header grammar has no Info severity (`check-review-decision.py` refuses it), so the header records it at the floor, Low. Two contrived shapes were falsely refused by `module_writes`. They failed CLOSED (CANNOT RUN,
never READY), the real harness has neither, and both were refused at r1 too. The redesign removes them anyway: L3 and
L4 above are those two shapes, and both now pass.

Reviewed head: 248172e0984debfd4af9fab2d5465dff2ab55af4
