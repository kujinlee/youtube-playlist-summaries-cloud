# Round 4 — `register-memory-budget-hook` (PR #430) — coordinator — NOT CONVERGED (Codex); SPLIT to file identity

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 4
fixes_nontrivial: true
subject: register-memory-budget-hook
halves:
  codex: ran
  claude: gap
findings:
  - {id: S1, severity: Low, aim: deliverable, fix_induced: false, component: hook, disposition: fixed}
  - {id: S2, severity: Low, aim: deliverable, fix_induced: false, component: hook, disposition: fixed}
  - {id: S3, severity: Low, aim: deliverable, fix_induced: true, component: hook, disposition: fixed}
```

Every round 1–3 reproduction behaves as intended. **S1** a case alias (`memory.md`, `DOCS/MEMORY/MEMORY.md`) on this
case-insensitive filesystem and **S2** a hard link to the index were silent: names always miss SOME alias. **S3
(fix-induced by round 3's rewrite)** undecodable checker output raised `UnicodeDecodeError`, rc 1. Also: 10 MB of
checker output was forwarded whole.

**Route: SPLIT** (the ladder ran accrete, accrete, redesign). "Fires on every write to the index" is a claim about every
possible alias, the wall this session keeps meeting. The decidable half ships: the index is identified by FILE
IDENTITY — `samefile` against the index of each checkout containing the edited path (walking up from its lexical and
resolved forms) — so symlink, case and in-checkout hard-link aliases are seen by construction. STATED BOUND: a hard
link from OUTSIDE every checkout is not found by any walk, and the CI comment now says so. Accreted: output decoded
with replacement (rc 0 with an advisory, no traceback) and capped at 4,000 characters. ⟳ One round-3 expectation
SUPERSEDED, not lost: an `A/docs/memory/MEMORY.md` linking to `B/other.md` IS A's index under identity — the file a
session in A loads — so A measures it; round 3's NOT MEASURED came from the name rule. An index-named file in NO
checkout is still NOT MEASURED. Self-test 24/24; every round-4 input reproduced end to end.
