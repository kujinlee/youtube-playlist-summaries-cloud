# Round 1 — `hse-slice-c-redesign` — coordinator — NOT CONVERGED (both halves)

A redesign restarts the round count (review-method §0 Q4c, *A REDESIGN RESTARTS THE COUNT*). Subject: the Phase 6
redesign `244a6c02` of `scripts/check-shipping-sets.py` (spec:
`docs/reviews/coordinator/architecture-review-2026-11-17-hse-slice-c.md`). Halves: Codex
`docs/reviews/codex/hse-slice-c-redesign-r1-codex.md`, Claude `docs/reviews/claude/hse-slice-c-redesign-r1-claude.md`,
both on `244a6c02`. No BLOCKER. Round cap: round 1 of the new design; rounds 2–3 alternate; from round 4 findings are FILED.

Predictions of the spec: **(b) held** (both halves: 344 live edges, lost 0, gained 0; `--map`/`--closure` 0 gaps).
**(a) refuted** by XM1/CM1, XM2/CM3 and CM2: a loader or interpreter word appears in syntax and the load is neither an
edge nor `unresolved:`. **(c) refuted** (minor) by Xm3/Cm3 and Cm2.

```yaml
round: 1
fixes_nontrivial: true
subject: hse-slice-c-redesign
halves:
  codex: ran
  claude: ran
findings:
  - {id: XM1, severity: High,   aim: deliverable, fix_induced: false, component: load-census, disposition: fixed}
  - {id: XM2, severity: High,   aim: deliverable, fix_induced: false, component: load-census, disposition: fixed}
  - {id: Xm3, severity: Medium, aim: deliverable, fix_induced: true,  component: crash-case,  disposition: fixed}
  - {id: CM1, severity: High,   aim: deliverable, fix_induced: true,  component: load-census, disposition: fixed}
  - {id: CM2, severity: High,   aim: deliverable, fix_induced: true,  component: load-census, disposition: split}
  - {id: CM3, severity: High,   aim: deliverable, fix_induced: true,  component: load-census, disposition: fixed}
  - {id: Cm1, severity: Medium, aim: deliverable, fix_induced: false, component: edge-reader, disposition: fixed}
  - {id: Cm2, severity: Medium, aim: instrument,  fix_induced: true,  component: live-pin,    disposition: fixed}
  - {id: Cm3, severity: Medium, aim: deliverable, fix_induced: true,  component: crash-case,  disposition: fixed}
  - {id: Cm4, severity: Medium, aim: deliverable, fix_induced: false, component: load-census, disposition: split}
```

| Id | Finding | Same as |
|---|---|---|
| XM1 / CM1 | an interpreter argv with `-c` or `-m` is consumed and read as nothing (`:511-513`); 7 live argvs in `session-state.py:1653-1706` silent | each other |
| XM2 / CM3 | `import_module`/`__import__` of a sibling PACKAGE or a missing module gets no `unresolved:` (`:551`, `:641`); only `import` statements get the directory check | each other |
| CM2 | the interpreter and loader censuses match exact names only: `/bin/bash`, `python3.12`, `zsh`, `"…".split()`, `shlex.split`, `runpy.run_module`, `SourcelessFileLoader`, `imp.load_source` slip — worse than the stated bound | — |
| Cm1 | a nested function's default parameter resolves at module scope: a wrong edge plus a silent drop (`:537`) | — |
| Cm2 | the live-tree pin checks the COUNT 344 only; one lost plus one gained edge passes | — |
| Xm3 / Cm3 | the crash case reads only the first output line, so an extra `[FAIL]` passes (master rejected it); merge-gate lines `c4530de76b8a`, `e7535ba71eed` answered as loosening findings by both halves | each other |
| Cm4 | after `sys.path.insert`, an import of a missing file is dropped; `pty.spawn` and `subprocess.run(["./x.sh"])` are silent and undocumented | — |

**Route: SPLIT** (decision log; the redesign bet's prediction (2) lost). Fold now: XM1/CM1, XM2/CM3, Cm1, and the two
weakened tests (live pin compares the edge SET; crash case restores the parsed-names check). One invariant closes the
folded forms: every clause that recognises a loader or interpreter call ends in an edge or `unresolved:`, never in
nothing. **Split out:** CM2 and Cm4 — an exact-name census cannot be closed by enumeration in one fold (each round names
more names) — go to their own backlog row, and the docstring states them as bounds until then. Dispositions above record
that fold and are committed with it.

**Fold (as done).** XM1/CM1: `-c` is `unresolved:`, `-m <name>` a module load. XM2/CM3: the call-form module outcome
check (directory, no file). Cm1: a default is read in its `def`'s scope (an enclosing function or a class body). Cm2:
the live case pins the edge set's digest. Xm3/Cm3: the crash case compares every `[FAIL]` line. The invariant is one
helper: each recognised clause ends in `_add` or `_unread`, and `paths()` is CANNOT RUN otherwise. `--closure`: 65 →
89 `unresolved:`, none dropped, 0 gaps. CM2 and Cm4 are docstring bounds citing backlog #671.
