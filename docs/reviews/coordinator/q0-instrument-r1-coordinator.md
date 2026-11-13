# Round 1 — `q0-instrument` (PR #483, backlog #177) — coordinator — NOT CONVERGED (Codex half); both findings fixed

Codex half: `docs/reviews/codex/q0-instrument-r1-codex.md`, which reviewed `985de1b6`.
REVIEW GAP: claude — prose-only change: Q0's own *prose* row and Q1 give it ONE round, inside the round cap (Q4c); the
Codex half ran it.

```yaml
round: 1
fixes_nontrivial: true
subject: q0-instrument
halves:
  codex: ran
  claude: skipped
findings:
  - id: M1
    severity: medium
    disposition: fixed
  - id: M2
    severity: medium
    disposition: fixed
```

**Q0 for this change:** prose only → one round (Q1), stop at the prose floor.

- **M1 — FIXED.** `process-checklists.md` → *A side job inherits NO design approval* still defined a seam as including
  "a new module", contradicting the narrowed Q0 row. It now points at Q0's definition, and its "when Q0 lands" note
  says it has landed.
- **M2 — FIXED.** The FAILS-IF counted "two or more of the four signals" as proof Q0 chose wrong, an uncalibrated
  threshold that contradicts Q0's own "Q5 remains the trigger". It now defers to Q5's causal test and calls the
  signals prompts until calibrated.
