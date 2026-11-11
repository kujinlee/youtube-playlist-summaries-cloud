# Round 1 — `backlog-kinds` (PR #442, backlog #394, backlog #395) — coordinator — NOT CONVERGED (both halves)

Codex half: `docs/reviews/codex/backlog-kinds-r1-codex.md`. Claude half: `docs/reviews/claude/backlog-kinds-r1-claude.md`. Both reviewed `fcc14858`.

```yaml
round: 1
fixes_nontrivial: true
subject: backlog-kinds
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: Low, aim: deliverable, fix_induced: false, component: kinds, disposition: fixed}
  - {id: X2, severity: Low, aim: instrument, fix_induced: false, component: namespace-exemption, disposition: fixed}
  - {id: M1, severity: High, aim: deliverable, fix_induced: false, component: namespace-exemption, disposition: fixed}
  - {id: m1, severity: Low, aim: deliverable, fix_induced: false, component: kinds, disposition: fixed}
  - {id: m2, severity: Low, aim: deliverable, fix_induced: false, component: kinds, disposition: fixed}
  - {id: m3, severity: Low, aim: deliverable, fix_induced: false, component: marker-grammar, disposition: fixed}
```

**Codex found no way to get new prose past the narrowed gate.** It found two Low issues:
- X1: #222's kind should be task under ruling 3.
- X2: there is no case for the invalid-marker fallback.

**The Claude half found the one real hole (M1).** `removed_lines` sets the path only on `+++ b/`, so a DELETED file's removed lines are credited to the previous file in the diff. A line moved out of an out-of-scope deleted file, with a marker appended, then enters a scoped file unjudged. This is the "same file" rule the owner approved, failing at its edge. **Fold:** key removed lines on the `--- a/` path, and add the reviewer's deleted-file case with a mutation.

**The kinds (m1, m2):**
- #195 and #53 become `task`: in each, the row's own text says no claim is false (ruling 3), and #195 is a design question (ruling 1).
- `residue carried out of backlog #91` is PROVENANCE, not parentage. That is consistent with this branch's earlier calls on #64 and #372. So #107's `part of: backlog #91` is REMOVED, rather than added to #108 and #109.

**The grammar (m3):** an Item cell cannot quote the marker syntax. The restriction is STATED where the grammar is documented, rather than parsed around, because skipping backticked spans would be a second grammar inside the first.
