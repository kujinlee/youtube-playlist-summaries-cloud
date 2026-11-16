# Round 3 — `idle-stop-guard` — coordinator — ⟳ NOT CONVERGED (Claude half) — Phase 6 ARMED

Claude (Opus, `docs/reviews/claude/idle-stop-guard-r3-claude.md`) reviewed `39c468cc`: 1 BLOCKER, 3 MINOR,
NOT CONVERGED. Self-test 93/93 quoted; 3,146 real stops replayed through `last_tool_asked` with no answered card
let through and no false "unreadable"; no wedge input found.

REVIEW GAP: codex — alternation (rounds 2+ run one half; Codex reviewed round 2).

```yaml
round: 3
fixes_nontrivial: true
subject: idle-stop-guard
halves:
  codex: skipped
  claude: ran
findings:
  - {id: CB1, severity: Blocking, aim: deliverable, fix_induced: false, component: pause-exception, disposition: fixed}
  - {id: Cm1, severity: Minor, aim: deliverable, fix_induced: true, component: ci-signal, disposition: fixed}
  - {id: Cm2, severity: Minor, aim: deliverable, fix_induced: true, component: question-exception, disposition: fixed}
  - {id: Cm3, severity: Minor, aim: deliverable, fix_induced: false, component: question-exception, disposition: fixed}
```

## Arming condition — read by hand

`check-review-decision.py` answers CANNOT RUN on the Major/Minor vocabulary (backlog #661), so this is read by hand
from the r2 and r3 YAML:

| Component | r2 fix-induced | r3 fix-induced | Consecutive? |
|---|---|---|---|
| question-exception | XM1 (the r1 fold's AskUserQuestion exception kept an ANSWERED card) | Cm2 (the r2 fold's "last card wins" reset is unwitnessed) | **YES — armed** |
| ci-signal | none (XM4 was not fix-induced) | Cm1 | no |
| worktree-signal | XM5 | none | no |

**Phase 6 fires** on `question-exception`. CB1 (the pause marker excuses every idle stop for 24 h, and the block
message teaches the agent to create it) is in the sibling component — the guard's other ALLOW exception — so the
Phase 6 review takes BOTH exceptions in scope. Dispositions for all four findings wait for its verdict.

**Round cap:** the next round is round 4; from round 4 a non-BLOCKER is FILED (`docs/review-method.md` §0 Q4c).
CB1 is a BLOCKER and must be fixed before merge whatever Phase 6 says.

## Phase 6 verdict and dispositions

Phase 6 (Fable, `docs/reviews/architecture-review-2026-11-16-idle-stop-guard.md`, `6ce1e99a`) recommends **option D:
remove both ALLOW exceptions and the transcript reader**, so every ALLOW reads state the stopping agent did not
author. Each exception saved one refusal on its honest path (the continuation passes on `stop_hook_active` anyway),
fired on 4 of 3,147 replayed stops, and owned 26 of 99 mutations. The coordinator ADOPTS D.

| Finding | Disposition |
|---|---|
| CB1 (pause marker) | dissolved by removal — the marker is no longer read; a case pins it across a literal list of ages |
| Cm2 (last-card reset unwitnessed) | dissolved by removal — no card logic remains |
| Cm3 (unreadable transcript unexplained) | dissolved by removal — the transcript is never opened |
| Cm1 (`__typename` shape unwitnessed) | FIX — a case for a malformed `__typename` |

**Stop condition for round 4:** "an honest stop costs one refusal" and "a work signal can be forged" are FILED, not
folded. A BLOCKER in round 4 is only an announcement-only stop that exits 0 on its first attempt without forging a
work signal.
