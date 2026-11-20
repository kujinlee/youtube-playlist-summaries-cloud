# Round 3 — `memory-shape-check` — coordinator — CONVERGED (Claude half)

Claude (`docs/reviews/claude/memory-shape-check-r3-claude.md`) reviewed `6ee2860f` (the round 2 fold plus the merge of
`origin/master`, slice D #600): no BLOCKER, no MAJOR, 5 MINOR. The round 2 folds hold on the reviewer's own probes
(undefined escapes refused, trailing comments read as YAML reads them, delimiters inside same-block code ignored).

The verdict is CONVERGED, so the five MINORs are FILED, not folded: all are backlog #677. None changes what the check
reports on today's memory corpus (each has 0 instances there); finding 3 and 5 fail loudly (a valid file refused), and
findings 1 and 2 are false passes only for an input the corpus does not hold.

**Thrashing?** YES, in `link-reader`. Round 2's XM2/Xm2 were caused by the round 1 fold (comment stripping), and round
3's findings 1 and 2 were caused by the round 2 fold (code-span and fence recognition) — two consecutive rounds of
fix-induced findings in one component, so the arming condition holds (`docs/dev-process.md` → *The arming condition*).
`frontmatter-parser` is not armed: round 3's findings 3–5 there are not fix-induced. Phase 6 is convened on
`link-reader` before the merge: `docs/reviews/architecture-review-2026-11-20-memory-link-reader.md`.

REVIEW GAP: codex — alternation (round 3 is the Claude half's).

```yaml
round: 3
fixes_nontrivial: false
subject: memory-shape-check
verdict: CONVERGED
blockers: 0
filed: [677]
halves:
  codex: gap
  claude: ran
findings:
  - {id: Cm1, severity: Medium, aim: deliverable, fix_induced: true, component: link-reader, disposition: filed}
  - {id: Cm2, severity: Medium, aim: instrument, fix_induced: true, component: link-reader, disposition: filed}
  - {id: Cm3, severity: Medium, aim: deliverable, fix_induced: false, component: frontmatter-parser, disposition: filed}
  - {id: Cm4, severity: Medium, aim: deliverable, fix_induced: false, component: frontmatter-parser, disposition: filed}
  - {id: Cm5, severity: Medium, aim: deliverable, fix_induced: false, component: frontmatter-parser, disposition: filed}
```

| Id | Finding | Fold |
|---|---|---|
| Cm1 | the code-span alternative of `_COMMENT_RE` is not block-aware: a span across list items, after an escaped backtick or over an indented fence swallows a real comment, so its links count | filed, #677 |
| Cm2 | the r2 fold's stated behaviours (same-length closers, fence indent, unclosed fence, tilde fences, several escapes) have no case; hand mutants survive 104/104 | filed, #677 |
| Cm3 | a full-line `# comment` in frontmatter is refused; `# note: x` is stored as a field | filed, #677 |
| Cm4 | `tags: - x`, tab indentation and a stray indented key are accepted | filed, #677 |
| Cm5 | escapes are validated, never decoded: `name: "foo\x2Dbar"` is refused against `foo-bar.md` | filed, #677 |
