# Round 4 — `ffmpeg-deb-cache` — coordinator — ⟳ NOT CONVERGED (budget half of the bet LOST); route DEFER: filed, loop stops

```yaml
round: 4
fixes_nontrivial: false
subject: ffmpeg-deb-cache
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XP1, severity: Medium, aim: deliverable, fix_induced: false, component: budget, disposition: filed}
  - {id: XL2, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

REVIEW GAP: claude — round 4 alternates to the Codex half on the final tree (`review-method.md`, *The
protocol*, step 4; backlog #339).

`X` = Codex, tree `903d93a5` (the r3 fold `1a8d6b5e` plus a merge of master that touched only docs logs). Confirmed:
no cache work inside the install step; the step `timeout-minutes` expression is valid and selects 13 only when the
key step's `updated=yes` output exists (20 when the key step is skipped); 13 minutes covers the install's configured
apt bounds on the reused-index path (700 s); a same-size forged archive was rejected again with nothing copied.

- **XP1 (Medium, FILED as backlog #360):** the "28.3 / 27.3 / 21.3 of 30 by STEP CAPS" budget was false. `verify` has
  83 steps and only six have a `timeout-minutes`; my figures added the measured runtime of the 77 uncapped ones. The
  explicit caps are 23 / 16 / 19 / 21 per path, each plus R, which only the job's 30-minute limit bounds — true of
  master too (install 20 + R), so this PR does not create the gap; it made a claim about it that was not true. The
  claim is corrected in the PR body and the dashboard entry; the cap work itself is not folded, per the DEFER row.
- **XL2 (Low, fixed — prose only):** the dashboard's r1 sentence still said "all three" cache steps.

Route DEFER, written before round 4: round 4 is the last and its findings are filed. The loop stops here; the
decision-log row is closed (`outcome: stopped`, `rounds_at_termination: 4`).
