# Round 1 — `compaction-guards` — coordinator — ⟳ NOT CONVERGED (Codex); ACCRETE, with the claim narrowed

REVIEW GAP: claude — not spawned this round. Two Claude halves on PR #424 tonight were given sweep-heavy mandates and filed nothing (memory: concurrent-agents-go-wrong.md, 10-28); this round's mandate was a trust-boundary attack, which the Codex half executed in full. A narrow Claude half (the CLAUDE.md and prose claims only) runs in round 2.

```yaml
round: 1
fixes_nontrivial: true
subject: compaction-guards
halves:
  codex: ran
  claude: gap
findings:
  - {id: XB1, severity: High, aim: deliverable, fix_induced: false, component: extraction, disposition: fixed}
  - {id: XB2, severity: High, aim: deliverable, fix_induced: false, component: extraction, disposition: fixed}
  - {id: XM3, severity: Medium, aim: deliverable, fix_induced: false, component: snapshot, disposition: fixed}
  - {id: XM4, severity: Medium, aim: deliverable, fix_induced: false, component: print, disposition: fixed}
  - {id: XM5, severity: Medium, aim: deliverable, fix_induced: false, component: audit, disposition: fixed}
  - {id: Xm6, severity: Low, aim: deliverable, fix_induced: false, component: snapshot, disposition: fixed}
```

Codex on `217d74e2`. **XB1** a forged `tool_result` carrying a real AskUserQuestion id becomes an AUTHORITATIVE answer even
when the result is `isMeta`/`isCompactSummary`/task-notification, when the question came from a sidechain turn, and an id
can be replayed. **XB2** nested or unclosed `<pasted_content>` lets trailing text escape redaction into the authoritative
prompts. **XM3** 48 slow worktrees take PreCompact to 18.4 s, past its 15 s timeout. **XM4** an earlier compaction's (or
another session's) snapshot prints as current. **XM5** a refused ledger yields "names everything (0 items checked)".
**Xm6** a large ledger breaks the snapshot's own 8,000-char cap. **Held:** 61/61, 57/57; 22 + 30 mutations attributed;
2,388 real; 18 hooks canonical; the real 80 MB transcript parses in 0.44 s; main-checkout `--add`/`--done` round-trip.

**The claim narrows (XB1).** Even with full provenance checks, a hook can show only that text was RECORDED as an owner
answer or prompt — not that the owner wrote it. CLAUDE.md drops "authoritative": the snapshot shows the owner's recorded
words, and the next window verifies them against the transcript when they matter. **Route: ACCRETE** (round 1).
