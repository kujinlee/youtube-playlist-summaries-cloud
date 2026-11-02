# Round 8 — `derived-mutation-total` (PR #455, backlog #359) — coordinator — NOT CONVERGED (Codex); F1 and F2 FIXED; the split row scored `continued`, next route DEFER with r9's findings filed, not folded

REVIEW GAP: claude — alternation. Round 8 alternates to the Codex half alone (rounds 2+ alternate, `review-method.md` → *Round topology*; backlog #339).

Codex half: `docs/reviews/codex/derived-mutation-total-r8-codex.md`, which reviewed `256f0844`.

```yaml
round: 8
fixes_nontrivial: true
subject: derived-mutation-total
halves:
  codex: ran
  claude: gap
findings:
  - {id: F1, severity: High, aim: instrument, fix_induced: false, component: sibling-import, disposition: fixed}
  - {id: F2, severity: Medium, aim: instrument, fix_induced: false, component: sibling-import, disposition: fixed}
```

**What Codex found.** Both findings are on the pre-committed stop's ORDINARY-edit side, so both are fixed.
- **F1 (High):** `def pin_display(src): return {}` is an ordinary edit. `check-merge-ready` parses BOTH revisions with
  the working-tree reader, so base and head both became `{}` and a pin falling 5 -> 4 gave **READY, rc 0**.
  `_exact_pins` checked the types but accepted an empty dict.
- **F2 (Medium):** the self-test called `_pins_reader(PINS_READER).pin_display(_real_src)` outside `_cross`. A
  `pin_display` raising `SystemExit(0)` on the real source escaped the self-test before its summary.

**Would real CI have caught F1 anyway? Measured: yes.** On a scratch copy of `check-plan-code.py` with
`def pin_display(src): return {}` added, `--self-test` exits **rc 2**: `own_pin_problems` reports every pin as "the
display says None, this process holds N" and the display-vs-held assertion fails. So CI would be red, hence the PR NOT
READY. The merge-ready verdict was still wrong on its own, which is why it is fixed regardless.

**Fix.**
- **F1:** `_exact_pins` raises when the copied map is empty, "a present check-plan-code.py with no pins is
  unreadable". `pins_at` only reaches `_exact_pins` when `git ls-tree` found the file, so the absent-file `{}` is kept.
- **F2:** the self-test call is `_cross(lambda: _rdr.pin_display(_real_src), reduce=_exact_pins, error=PinsUnreadable)`.

**Red before green.** Three cases through the REAL `main()` on a pin falling 5 -> 4:

| Probe | Red (before) | Green (after) |
|---|---|---|
| reader whose `pin_display` returns `{}` | rc 0 READY (fall hidden) | rc 2 CANNOT RUN, "no pins" |
| the real reader, same fall (adjacent negative) | rc 3 HOLD | rc 3 HOLD |
| `check-plan-code.py` absent at both revisions | rc 0 READY | rc 0 READY (kept) |

Suite: **256/256**. One mutation entry (pin 96 -> 97): the empty-map refusal removed, red via the first case.

**Whole-file audit for a sibling attribute call outside `_cross`** (`.pin_display(`, `.exemption_reason(`, and every
use of a module returned by `_import_sibling`): exactly three sites, `:1020` and `:1112` in production (both inside a
`_cross` lambda) and the self-test site (now inside one). `gate.` at the escape-diagnosis formatter is a string, not
the module. **No case witnesses the self-test site**: reaching it needs `_self_test()` itself driven with a hostile
reader, a recursion with no seam; the production sites carry the cases.

**Codex re-confirmed the 6 FALSE HOLD lines** (five in `check-merge-ready.py`, one in `check-plan-code.py`) against
`origin/master...HEAD`, for the documented replacement and coverage reasons. Nothing new for the merge-time HOLD comment.

## Ladder (decision log)

- **The split row is scored `continued`**, observed = r8 F1/F2, its named failure observation.
- **Next route: DEFER**, on the same unit text. Prediction: any further finding in r9 is filed as a backlog row, not
  folded, and the PR ships. `check-decision-scheme` gives rc 0, WARNs only.
