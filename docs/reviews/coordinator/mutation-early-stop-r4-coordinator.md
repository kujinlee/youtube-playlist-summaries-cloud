# Round 4 — `mutation-early-stop` (draft PR #476, backlog #405) — coordinator — NOT CONVERGED (Codex half); one BLOCKER, folded by NARROWING the design

Codex half: `docs/reviews/codex/mutation-early-stop-r4-codex.md`, which reviewed `3bc06510`.
REVIEW GAP: claude — alternation (rounds 2+ run ONE half per round, `docs/review-method.md` → *Round topology*).

```yaml
round: 4
fixes_nontrivial: true
subject: mutation-early-stop
halves:
  codex: ran
  claude: skipped
findings:
  - {id: X4-B1, severity: Blocker, aim: deliverable, fix_induced: true, component: stop-rule, disposition: fixed}
```

- **X4-B1 (Codex), a BLOCKER, so folded despite the round cap.** The r3 closure's `early_sources` skips
  `node_modules`, but staging copies it. A suite that imports through a module there escapes the closure, so early
  stop records KILLED where a full run records SURVIVED (constructed; no production instance).

**Why the design is narrowed instead of patched.** This is the third "what does a changed script reach" finding:
r1 a named import, r3 a transitive one, r4 one through an unscanned directory. Each fix widened a text-matching
surface. The r3 fold also MEASURED what the closure costs: for 94 of 95 single-script changes it already forces all 86
targets to FULL. So the narrow rule gives up almost nothing measured:

- **Any changed `.py` makes the whole run FULL.** `early_path_allowed` refuses every `.py`.
- **The closure, `early_sources` and the stem matcher are deleted.** No import is traced, so there is nothing for a
  reviewer to route around.
- **The per-file rule keeps one arm:** a changed manifest forces its own file to FULL.

Early stop then applies to PRs that change only docs, `*.md` and manifests while the sweep still runs (a staged
`.md`, for example). Matching real imports to win back script PRs is filed as its own backlog row, with its own
design and review.
