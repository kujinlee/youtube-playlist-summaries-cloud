# Round 1 — `trim-always-loaded` — coordinator — fold of both halves

```yaml
round: 1
fixes_nontrivial: false
subject: trim-always-loaded
halves:
  codex: ran
  claude: ran
findings:
  - {id: C1, severity: Medium, aim: deliverable, fix_induced: true, component: plugins-spine, disposition: fixed}
  - {id: C2, severity: Medium, aim: deliverable, fix_induced: true, component: plugins-spine, disposition: fixed}
  - {id: C3, severity: Medium, aim: deliverable, fix_induced: true, component: dev-process-spine, disposition: fixed}
  - {id: C4, severity: Medium, aim: deliverable, fix_induced: true, component: plugins-spine, disposition: fixed}
  - {id: C5, severity: Low, aim: deliverable, fix_induced: true, component: plugins-spine, disposition: fixed}
  - {id: C6, severity: Medium, aim: deliverable, fix_induced: false, component: token-claim, disposition: fixed}
  - {id: C7, severity: Low, aim: deliverable, fix_induced: true, component: moved-blocks, disposition: fixed}
  - {id: L2, severity: Low, aim: deliverable, fix_induced: true, component: plugins-spine, disposition: fixed}
  - {id: L5b, severity: Low, aim: deliverable, fix_induced: true, component: plugins-spine, disposition: fixed}
```

Both halves held the verbatim-move and no-dangling-pointer claims and refuted "no action rule lost".

| Finding (source) | Disposition |
|---|---|
| C1 Codex M1 / Claude F5-adjacent: commit-before-spawn and the three serialise-only hazards dropped | FIXED `docs/plugins.md` Code Review intro paragraph |
| C2 Codex M2 / Claude F5: capture with no findings section is a failed run; prefer the reviewer that reports a finding | FIXED `docs/plugins.md` fail-open bullet |
| C3 Codex M3 / Claude F4: plan-leak gate per-clone install, not in CI, 8-word bound; schema-workflow ordering | FIXED `docs/dev-process.md` push-hook row and `schema-gates.yml` row |
| C4 Codex M4 / Claude F5: resolver refusal, read its message, `codex exec -m` in a worktree before a REVIEW GAP | FIXED `docs/plugins.md` Codex model paragraph |
| C5 Codex L: rc=3 recovery (move the capture or `--allow-overwrite`) | FIXED `docs/plugins.md` rc=3 comment |
| C6 Codex M / Claude F1: token saving priced as uncached input, "per turn" wrong unit, before-total mismatch | FIXED `docs/trim-floor-walkthrough.md` (table, saving, Risk) and `docs/dashboard-entries.md` entry; before total re-measured 47,377 chars |
| C7 Codex L / Claude F3: moved blocks' "this file" / "RULE box above" now false | FIXED bracketed notes at `docs/review-method.md` (Agent-tool paragraph) and `docs/process-checklists.md` (layer table row 1) |
| L2 Claude F2: alternation needs a `REVIEW GAP: … alternation` line | FIXED `docs/plugins.md` Code Review intro |
| L5b Claude F5: do not trust the completion ping | FIXED `docs/plugins.md` bounded-wait bullet |

Line budget: `dev-process.md` stays at 214 / 220 (edits were in place).

next: r2, one half (codex), with a `REVIEW GAP: claude — alternation` line.
