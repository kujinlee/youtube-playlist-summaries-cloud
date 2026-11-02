# Round 3 — `plan-leak-guard` (PR #443, backlog #393) — coordinator — DEFER, terminal: findings FILED

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 3
fixes_nontrivial: false
subject: plan-leak-guard
halves:
  codex: ran
  claude: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings:
  - id: F10
    severity: Low
    aim: deliverable
    disposition: filed
    filed_as: "backlog #416"
    fix_induced: true
  - id: F11
    severity: Low
    aim: deliverable
    disposition: filed
    filed_as: "backlog #416"
    fix_induced: false
```

Codex reviewed `8e065f71`, the SPLIT fold first, with real pushes into bare remotes and the hook installed in temp repos only.

**The push half of the bet held.** There was no `hits 0` bypass under any of the settings tried: `diff.mnemonicPrefix`, `color.diff=always`, `diff.relative`, an external diff, `core.quotePath` with non-ASCII paths, renames and copies, `includeIf` configuration, or `GIT_DIR`/`GIT_WORK_TREE` overrides. The external-diff and pager probes ran nothing. A moved clone and a main checkout on an old branch push unchecked, as documented, and the status and session warnings name both. 119/119 cases passed.

**The output half lost twice.** Both findings are Low, and both concern a push that is already BLOCKED:
- F10 (fix-induced): F5's redaction keys on added-name hits, so a phrase-named path that already exists on the remote prints in full.
- F11: a plan's own phrase-named file shows up in the HIT line's source label.

Nothing reaches the remote. The words reach the hook's stderr, which the model reads. **Route: DEFER, terminal, no fold.** Both are FILED into backlog #416 (F10, F11), with one fix (a single output sanitizer) and a FAILS IF. Across three rounds, every push form tried was blocked. The unit closes here.
