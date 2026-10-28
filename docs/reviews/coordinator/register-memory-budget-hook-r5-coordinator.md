# Round 5 — `register-memory-budget-hook` (PR #430) — coordinator — NOT CONVERGED (Codex); DEFER: trivial fixes, stated bounds, stop

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 5
fixes_nontrivial: false
subject: register-memory-budget-hook
halves:
  codex: ran
  claude: gap
findings:
  - {id: T1, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: T2, severity: Low, aim: deliverable, fix_induced: true, component: hook, disposition: fixed}
  - {id: T3, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

Every round 1–4 reproduction behaves as intended (harness, lexical, case and in-checkout hard-link aliases; newline
siblings; checker failures; undecodable output). 24/24, 45/45, all 34 mutations at their named cases.

**T1** the hard-link bound was broader than stated: a hard link to B's index placed inside an UNRELATED checkout A is
not found either, so "in-checkout hard-link aliases are seen" overclaimed. The bound now reads, in the header, the
`decide` docstring and `ci.yml`: a hard link is seen only when it shares identity with the index of a checkout that
CONTAINS it; one placed in another checkout or outside every checkout is unobserved — with a case that pins it.
**T2 (fix-induced by round 4)** truncating before searching for `WARNING` erased a warning past the cut; the decision now
reads the full output and only the SHOWN text is truncated (measured: 5,000 characters then a WARNING → advisory).
**T3** the header kept round 3's pathname bound; rewritten around file identity.

**Route: DEFER — terminal.** The ladder ran accrete, accrete, redesign, split. Every remaining finding this round is a
sentence or a one-line reorder whose fix is certain, so `fixes_nontrivial: false` and no further round is owed. What
stays outside the guarantee is STATED: a hard link from another or no checkout, and writes not made through the tool.
