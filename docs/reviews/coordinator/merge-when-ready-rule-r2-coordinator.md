# Round 2 — `merge-when-ready-rule` — coordinator — ❌ NOT CONVERGED (2 Medium, 1 Low) — BET LOST

```yaml
round: 2
fixes_nontrivial: true
subject: merge-when-ready-rule
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: false, component: diff-parse, disposition: fixed}
  - {id: XM2, severity: Medium, aim: deliverable, fix_induced: true, component: gate-callers, disposition: fixed}
  - {id: XL1, severity: Low, aim: deliverable, fix_induced: true, component: dashboard-text, disposition: fixed}
```

REVIEW GAP: claude — round 2 alternates to the Codex half on the final tree (`review-method.md`, *The
protocol*, step 4; backlog #339 leaves PAIR vs ONE-HALF to the owner, and the gate accepts both).

`X` = Codex half, final tree `d3b1aa2d`. It re-applied all 41 mutations in memory over a green control
(each killed via its named case) and reproduced the 8-of-40 replay.

**The logged bet LOST** (decision log, written before the round): XM2 is a Medium in `gate-callers` caused
by r1's fold — the new caller detector read COMMENT lines, so a reworded workflow comment naming a check
HOLDs at rc 3. XM1 (renames classified by the destination only, so `check-x.py -> validate-x.py` with
`return 1 -> 0` is READY, and a workflow moved out of `.github/workflows/` is READY) is not fold-induced.

**One cause for both, so the next route is REDESIGN, not a third accretion:** two diff parsers, each
deciding paths and comments for itself — r1 patched deletion into both by hand, and they then drifted on
renames and comments. Logged as the next bet before round 3.

Dispositions:
- **XM1 + XM2 FIXED BY REDESIGN:** one parser, `diff_files()`, gives every detector a file's OLD and NEW path
  (from the `diff --git` header, `rename from/to`, and `---`/`+++`), its hunks, and nothing else;
  `is_comment()` is the one comment rule. `diff_lines` becomes a view of it; `failure_path_removals`,
  the new `gate_invocation_removals` and the new `scope_exits` (a gate deleted, or renamed where nothing
  runs it — including a hunkless pure rename) all read it. `main()` passes `-M` explicitly. Ten cases;
  six mutation anchors rebound onto the new parser with the same mutation each; four added (41 -> 45);
  scoped sweep 45/45, each by its named case. Replay unchanged at 8 of 40.
- **XL1 FIXED:** the dashboard no longer says "the last 14 would have merged".
