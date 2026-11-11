# Round 3 — `agenda-499b` (backlog #499 slice 2, PR #503) — coordinator — NOT CONVERGED (Codex), all folded

```yaml
round: 3
fixes_nontrivial: false
subject: agenda-499b
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: scripts/goal-tree.py, disposition: fixed}
  - {id: X2, severity: Low, aim: deliverable, fix_induced: false, component: scripts/goal-tree.py, disposition: fixed}
```

REVIEW GAP: claude — budget (weekly usage 92%, new agents refused at 94.6%); alternation would have given r3 to Claude.

- **X1 (High, FIXED):** `snap_agenda` checked `refs` was a list but not its entries; `refs: [1]` read `ok` and crashed
  `_refset` in the tags and the page. `_ref_ok` now requires every entry to be `[str, int]` — the shape both writers
  (`REF_RE.findall` → `[k, int(n)]`) produce. Not induced by r2: the entries were never checked; r2's `ok` made the
  gap a stated guarantee. Case (two bad ref shapes → malformed) + mutation.
- **X2 (Low, FIXED):** `snap_history` normalised with `or []`, so `agenda_history: false` was silently read as none.
  It now defaults only a MISSING key; `false`, `""`, `0` and `None` are said. Case + mutation.
- Codex also noted the "only readers" wording is literal-false (`tree_blocks` and `agenda_html` touch `snap["agenda"]`
  to hand it to the guarded reader). No crash; the docstring's rule is "no reader INDEXES it but through this", which
  both satisfy.

312/312; 203 mutations; all 51 backlog #499 mutants killed by their named case without a traceback.
Round cap: from r4, findings are FILED unless BLOCKER (`review-method.md` §0 Q4c).
