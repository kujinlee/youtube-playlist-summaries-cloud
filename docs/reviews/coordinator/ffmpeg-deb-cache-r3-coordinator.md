# Round 3 — `ffmpeg-deb-cache` — coordinator — ⟳ NOT CONVERGED (bet LOST); owner: fix both, one more round

```yaml
round: 3
fixes_nontrivial: true
subject: ffmpeg-deb-cache
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XP1, severity: Medium, aim: deliverable, fix_induced: true, component: cache-steps, disposition: fixed}
  - {id: XP2, severity: Medium, aim: deliverable, fix_induced: false, component: budget, disposition: fixed}
  - {id: XL3, severity: Low, aim: deliverable, fix_induced: true, component: cache-steps, disposition: fixed}
  - {id: XL4, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

REVIEW GAP: claude — round 3 alternates to the Codex half on the final tree (`review-method.md`, *The
protocol*, step 4; backlog #339).

`X` = Codex, tree `140706d0`, in an `ubuntu:26.04` container. Integrity HELD again (a read-only same-size forgery
rejected and later replaced by verified bytes; extras removed; a bad staging hash withholds the save; a hung
`--print-uris` returns 124 with no key). **The availability half of the bet was LOST:**

- **XP1 (fold-induced, fixed):** the verify-and-copy block still ran INSIDE the required install step, in a subshell.
  A failure exit was caught, but a STALL is not an exit: only the 20-minute step cap could end it (shown by fault
  injection). It is now its own bounded, `continue-on-error` `Seed` step; the install step is master's except the
  reused index and its cap.
- **XP2 (fixed):** the "28.0 min worst case" summed inner bounds and omitted steps; by STEP CAPS it was 36.3 against
  the job's 30 (master: 25). Now the install cap is 13 when it reuses the key step's index (its own bounds total
  11.7) and 20 otherwise, and the cache caps shrank: 28.3 / 27.3 / 21.3 of 30 by caps, per path.
- **XL3 (fixed by the same move):** the subshell masked an individual copy failure behind "0 rejected".
- **XL4 (fixed):** "all three" cache steps — there are five.

The pre-committed stop said this round's findings are filed; the **owner chose (2026-10-26 ~17:00) to fix both and run
one more round** instead. Route DEFER (decision-log row written before the change): round 4 is the last, and its
findings are filed.
