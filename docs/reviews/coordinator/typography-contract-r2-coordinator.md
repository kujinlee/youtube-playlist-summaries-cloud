# Round 2 — `typography-contract` — coordinator — ❌ NOT CONVERGED (1 Medium)

```yaml
round: 2
fixes_nontrivial: true
subject: typography-contract
halves:
  codex: ran
  claude: "GAP: alternation (one-half-per-round reading; backlog #339, NEEDS-OWNER)"
findings:
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: em-dark-state, disposition: fixed}
```

REVIEW GAP: claude — alternation under the reading this repository uses; backlog #339 asks the owner which governs.

Codex M1, reproduced in Chromium: r1's default `:root:not([data-theme="light"])` (0,2,0) TIED a fragment's own OS-dark
rule and won by source order, so a fragment's deliberate dark `--em` on a grey ground went 5.74:1 -> 2.86:1, and §2's
"a fragment's own value overrides" was false. Fix-induced. Measuring the fix showed the PRE-EXISTING pressed pair
`:root[data-theme=…]` had the same defect on a press (2.86:1 with dark pressed). REDESIGNED as one principle rather
than two patches: every default at the LOWEST specificity that works — `html:where(…)` (0,0,1) and `html[data-theme=…]`
(0,1,1). Six theme states measured on five pages (min 5.74:1, Codex's own fixture); all 22 fragments compose with the
same rc and controls as `master`; §2's cascade sentence rewritten to the exact specificities; +2 mutations, scoped run
30/30. ⚠ Thrashing watch: fix-induced in `em-dark-state`; one more consecutive round there arms Phase 6. Round 3: Claude.
