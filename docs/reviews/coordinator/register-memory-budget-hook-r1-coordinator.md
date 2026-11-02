# Round 1 — `register-memory-budget-hook` (PR #430) — coordinator — NOT CONVERGED (Codex); folded

REVIEW GAP: claude — a three-file registration of a hook already reviewed when it was written (backlog #309's review), run at 74% of the session's usage budget; the Codex half executed the full attack. A Claude half is not owed again in round 2 under the owner's 2026-10-28 answer to backlog #339 (one reviewer per round).

```yaml
round: 1
fixes_nontrivial: true
subject: register-memory-budget-hook
halves:
  codex: ran
  claude: gap
findings:
  - {id: P1, severity: High, aim: deliverable, fix_induced: false, component: hook, disposition: fixed}
  - {id: P2, severity: Low, aim: instrument, fix_induced: true, component: mutation-manifest, disposition: fixed}
```

**P1** the harness writes the index through its alias `~/.claude/projects/<slug>/memory/MEMORY.md`, a symlink into
`docs/memory/`; `is_index_path` matched lexically, so the newly registered hook was SILENT on the normal route. Fixed:
the EDITED FILE's symlinks are resolved before matching (never the hook's own location — the regression its header
records). Measured end to end: an over-budget index through a symlinked alias → OVER BUDGET; an adjacent `OTHER.md` →
silent. **P2 (fix-induced)** emptying `UNREGISTERED` made REPO_ROOT itself compliant, so the mutation "main() ignores the
root it is given" no longer reddens its named case — it passes for an AMBIENT reason. Retargeted to the discriminating
"divergent registration exits 1" case, the reason recorded on the entry. 34/34 killed and attributed. **Held:** rc 0 on
malformed, missing, null, 10 MB, outside-repo and symlinked inputs; a linked worktree reports its own index; 64 ms
median per non-memory edit.
