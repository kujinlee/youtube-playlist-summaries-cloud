# Round 3 — `typography-contract` — coordinator — ❌ NOT CONVERGED (2 Medium, 3 Low) — THRASHING

```yaml
round: 3
fixes_nontrivial: true
subject: typography-contract
halves:
  claude: ran
  codex: "GAP: alternation — Codex took r2, so r3 is the Claude half (backlog #339, NEEDS-OWNER)"
findings:
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: em-dark-state, disposition: split}
  - {id: M2, severity: Medium, aim: deliverable, fix_induced: false, component: fg-cycle, disposition: filed}
  - {id: L1, severity: Low, aim: records, fix_induced: true, component: em-dark-state, disposition: split}
  - {id: L2, severity: Low, aim: records, fix_induced: false, component: records, disposition: fixed}
  - {id: L3, severity: Low, aim: records, fix_induced: false, component: records, disposition: fixed}
```

REVIEW GAP: codex — alternation under the reading this repository uses; backlog #339 asks the owner which governs.

M1, Chromium: a fragment with a light `:root` and both theme palettes but no OS-dark block stays light under OS dark,
and the r2 default gave it dark `--em` — 1.92:1 (from r1's fold, kept by r2). With r2's M1, `em-dark-state` has
fold-caused findings in two consecutive rounds: **THRASHING**; architecture review convened
(`docs/reviews/architecture-review-2026-10-24-em-default.md`) — the shim cannot know whether a page goes dark.
SPLIT: shim restored to `master` (both r2 changes reverted, incl. L1's comment); the three pages declare the pair
in their own palette blocks — 7.79–7.98:1 in six states; the contract says so. M2 (`--fg` cycle, on `master`)
FILED as backlog #351, and the contract notes it. L2: worst-case figures re-measured on `origin/master` as
1.78/1.79/1.78:1 and used everywhere. L3: the garbled dashboard sentence rewritten. Round 4: Codex.
