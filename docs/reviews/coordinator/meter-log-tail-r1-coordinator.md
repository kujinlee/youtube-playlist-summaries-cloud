# Round 1 — `meter-log-tail` (backlog #501, PR #531) — coordinator — ⟳ NOT CONVERGED (both halves); folded

Both halves ran on `f645d4bd`. Codex: NOT CONVERGED, 1 finding (C1, Medium). Claude: NOT CONVERGED, 5 findings
(R1-F1 High, R1-F2 Medium, R1-F3 to R1-F5 Low). This is round 1, so none is filed: four are fixed, and R1-F5, the
optional one, is declined with a reason.

```yaml
round: 1
fixes_nontrivial: true
subject: meter-log-tail
halves:
  codex: ran
  claude: ran
findings:
  - {id: C1, severity: Medium, aim: deliverable, fix_induced: false, component: scripts/check-usage-pace.py, disposition: fixed, commit: 302625b4}
  - {id: R1-F1, severity: High, aim: deliverable, fix_induced: false, component: scripts/check-usage-pace.py, disposition: fixed, commit: 302625b4}
  - {id: R1-F2, severity: Medium, aim: deliverable, fix_induced: false, component: scripts/check-usage-pace.py, disposition: fixed, commit: 302625b4}
  - {id: R1-F3, severity: Low, aim: deliverable, fix_induced: false, component: scripts/check-usage-pace.py, disposition: fixed, commit: 302625b4}
  - {id: R1-F4, severity: Low, aim: deliverable, fix_induced: false, component: scripts/check-usage-pace.py, disposition: fixed, commit: 302625b4}
  - {id: R1-F5, severity: Low, aim: deliverable, fix_induced: false, component: scripts/check-usage-pace.py, disposition: declined, commit: 302625b4}
```

## Each finding: what was done, and which case covers it

The cases were written first. C1 and R1-F3 went red on `f645d4bd` (371/374: C1 gave the wrong **55** with no
refusal, and F3 was refused). The R1-F1, R1-F2 and R1-F4 cases pin code that was already correct, so they were
green on `f645d4bd`. Each goes red under the mutation named for it.

| Finding | Disposition | Case(s) that cover it |
|---|---|---|
| **C1** (Codex): rows out of time order in a cut tail give a WRONG start with no refusal | **fixed**. When the read was cut and any two rows of the part (of any window) are out of time order, `pace_line` refuses with `TAIL_OUT_OF_ORDER` (NOT RUN). Equal times count as in order. Uncut, today's rule stands (the newest row at or before midnight, whatever the order). The blind spot is stated in the docstring and in backlog row 501: disorder that CROSSES the window edge cannot be seen, because nothing can be proved about rows that were not read. The real log was measured in order (r1 Claude half). | `⭐ #501 r1 C1: a CUT part holding two rows out of time order is refused…` (red on base: 55); `#501 r1 C1: the same rows read WHOLE keep today's rule…`; `…two rows with the SAME time are not out of order…`; `…disorder among rows of an EARLIER window counts too…` |
| **R1-F1** (Claude): `check-fixture-variation.py` red on three new parameters | **fixed**, with real cases and no exemption. `evaluate(meter_cut=True/False)` over the same text gives NOT RUN versus 94%. `read_meter(path, limit)` under and at the file's size gives a cut and a whole read. `read_meter(deadline=0.3)` is covered by R1-F2's case. The gate is now rc 0. | `⭐ #501 r1 F1: evaluate(meter_cut=True) says the line is NOT RUN…`; `#501 r1 F1: read_meter(limit=…) under the file's size reads the TAIL…` |
| **R1-F2** (Claude): `read_meter`'s `(False,)` fallback is unpinned; dropping it crashes `main` and loses the STOP | **fixed** (test and mutation; the code was correct). `_read_tail` is swapped for a slow reader and for a raising one. In both, `read_meter` returns `(None, why, False)`, and `main --hook spawn` at weekly 95% still DENIES, with rc 0 and the reason shown. | `⭐ #501 r1 F2: read_meter(deadline=0.3) of a stalled log…`; `…a reader that RAISES is (None, why, False)…`; `…at the stop, a STALLED meter read still DENIES the spawn…`; `…a meter reader that RAISES still DENIES the spawn`. Mutation: `path, deadline, (False,))` → `path, deadline)` |
| **R1-F3** (Claude): a reset between midnight and the first row read was refused | **fixed**. An earlier window's row ANYWHERE in the part read proves the cut (the `at <= midnight` clause is dropped), and the docstring now says so. | `⭐ #501 r1 F3: a reset between midnight and the first row read is answered from this window's first row (51), not refused` (the reviewer's repro; red on base) |
| **R1-F4** (Claude): no case cuts inside a multi-byte character; `errors="replace"` unpinned | **fixed** (test and mutation; the code was correct). | `⭐ #501 r1 F4: a cut one and two bytes INSIDE a 3-byte character drops that line whole — no U+FFFD`; `⭐ #501 r1 F4: one invalid byte in the tail skips ITS row…`. Mutation: the tail's `errors="replace"` dropped |
| **R1-F5** (Claude, optional): every hook parses the whole tail (0.27 s at the bound) | **declined**. The C1 fix needs every pair of rows in the part to be checked for order, so stopping at the first row that settles the start would hide disorder in the rows not walked. 0.27 s is within what the brief accepts. The reason is in `pace_line`'s docstring. | none (declined) |

## Mutations

There are 7 new mutations in `check-usage-pace.json`, and one existing entry gains the R1-F3 case in its `expect`
(and drops "pre-midnight" from its name). The pin goes from 164 to 171, with a comment in `expected_mutations.py`.
The harness's own `load_manifests`/`manifest_counts`/`pin_drift`/`anchor_problems` report no drift and no anchor
problems, and the sweep `--mutate . --only scripts/check-usage-pace.py` kills all 171.
