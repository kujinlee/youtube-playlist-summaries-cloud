# Round 1 — `pace-band` (PR #555) — coordinator — both halves NOT CONVERGED; folding

Both halves ran at `d7efd2eb`.
- Codex: `docs/reviews/codex/pace-band-r1-codex.md` — 1 MAJOR, 1 MINOR.
- Claude: `docs/reviews/claude/pace-band-r1-claude.md` — 1 MAJOR, 5 MINOR.

Both halves found the hard stop unchanged (Codex: 7,308 comparisons over three time zones; Claude: AST-identical
functions) and no WARN→OK loosening on any path that existed before.

```yaml
round: 1
fixes_nontrivial: true
subject: pace-band
halves:
  claude: ran
  codex: ran
findings:
  - {id: U1, severity: High, aim: deliverable, fix_induced: false, component: usage-pace-band, disposition: fixed}
  - {id: C2, severity: Low, aim: deliverable, fix_induced: false, component: usage-pace-band, disposition: fixed}
  - {id: L1, severity: Low, aim: test, fix_induced: false, component: usage-pace-band, disposition: fixed}
  - {id: L2, severity: Low, aim: test, fix_induced: false, component: usage-pace-band, disposition: fixed}
  - {id: L3, severity: Low, aim: deliverable, fix_induced: false, component: usage-pace-band, disposition: fixed}
  - {id: L4, severity: Low, aim: deliverable, fix_induced: false, component: usage-pace-band, disposition: fixed}
  - {id: L5, severity: Low, aim: deliverable, fix_induced: false, component: usage-pace-band, disposition: fixed}
```

## The two halves agree on the one MAJOR

**U1 (Codex 1 = Claude MAJOR-1): an UNKNOWN band returns OK, so the prompt hook says nothing.** The rule is that
an unknown start% never reads as fine, and the hook speaks only on WARN. The self-test pins the wrong result.
**Decision (coordinator, not the owner's; it is the stricter reading of a rule they set):** an UNKNOWN band is a
WARN (rc 1) whose message says the band is unknown and why (no meter row in this window). It only arises when the
window has no meter row, so it is rare. REFUSE and CANNOT RUN are unchanged. Cases: no meter rows in the window → WARN,
and the adjacent pass (a known start% at NORMAL → OK).

## The rest

- **C2:** the last-day rule excludes midnight itself (`<` where `<=` belongs, line 487). Use the inclusive boundary
  for the band only; the hard stop is untouched. Cases at 00:00:00 and one second before.
- **L1 (Claude MINOR-1):** the override is keyed by LOCAL dates and no case proves it. Add Tue 17:00 PST (already Wed
  in UTC) → the Tue band.
- **L2 (MINOR-2):** the trend case edges are too far from the line (21.0 / 21.2 against 21.108): tighten them so a
  +0.05 change in the constant fails.
- **L3 (MINOR-3):** the override's Thu/Fri `use all` entries are dead because `rise_start` covers them. Remove them,
  or make a case that only the override satisfies; say which and why.
- **L4 (MINOR-4):** stale 1.5× comment at line 1557.
- **L5 (MINOR-5):** start% has no age bound: a row days old gives a spurious early NO NEW STARTS. A start row older
  than the day it stands for makes the band UNKNOWN (and so a WARN, per U1).

Round 2 runs ONE half (alternation).
