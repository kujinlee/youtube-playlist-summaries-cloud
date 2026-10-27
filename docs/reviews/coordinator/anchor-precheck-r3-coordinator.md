# Round 3 — `anchor-precheck` — coordinator — ⏹ STOPPED (CONFIRMATION; code confirmed, one prose correction)

```yaml
round: 3
fixes_nontrivial: false
subject: anchor-precheck
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XL1, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

REVIEW GAP: claude — round 3 alternates to the Codex half on the final tree (`review-method.md`, *The
protocol*, step 4; backlog #339).

`X` = Codex, tree `852a4795`: 246/246; 2,109 entries matching the pin, no refusals; fixture variation passes; each
of the four backlog #252 mutations reddens its named case in an isolated copy.

- **XL1 (prose, fixed):** the dashboard and PR body read as if each mutant reddened EXACTLY its named case. The
  wiring mutant also reddens the `--only` and two-orphan cases, which depend on that same wiring — expected, and
  now said. No code change; the loop stops here.
