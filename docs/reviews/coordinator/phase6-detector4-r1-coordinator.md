# Round 1 — `phase6-detector4` — coordinator — NOT CONVERGED; §6 stop condition → fallback N

Both halves reviewed 637950d2 (the build of candidate F, c5afc7c0, and its rescan), each briefed to REFUTE FAILS IF 1–6
of `docs/reviews/architecture-review-2026-11-21-publishability-detector4.md` §6. Codex:
`docs/reviews/codex/phase6-detector4-r1-codex.md` (B1, M1; NOT CONVERGED). Claude:
`docs/reviews/claude/phase6-detector4-r1-claude.md` (B1, M2, m3–m6; NOT CONVERGED).

**Both BLOCKERs are FAILS IF 1 (a loss) caused by the build — verified by the coordinator, not taken from the reviews.**
Fresh copies of `scripts/check-publishability.py` (+ `check-shipping-sets.py`) from `git show` at 49c3f923 (old) and
637950d2 (new), each input through `_markdown_kind(lines, line, term)` (lines numbered from 1):

| Input | 49c3f923 | 637950d2 |
|---|---|---|
| Codex B1: `Run these:` / `  - first` / `` - `CronList` and `acmecorp` `` | prerequisite | None (mention) |
| Claude B1: `docs/superpowers/specs/2026-09-25-decision-card-soundness-design.md:386-387` (`#136 also carries:` read as a heading) | 3 dependencies | 0 |

§6 decided this in advance: *"If that round observes FAILS IF 1, 2 or 3 caused by the build: do not fold. Fall back to
N."* So no finding is folded into F. The build is reverted and N is built instead: 49c3f923's three walkers untouched,
the `NEGATES` constant and its use deleted (`any(not re.search(NEGATES, …) for m in …)` becomes
`bool(re.search(LEAD_VERBS, para, re.I))`), the round-3 negation case flipped (a negated verb still introduces), and its
mutation repurposed to plant a negation filter back. Measured on N:

- self-test 105/105; with a negation filter planted (`and "never" not in para`), the flipped case goes red (104/105);
- rescan `docs/marketplace/scan-2026-11-17.json`: 46 components, **302** findings — FAILS IF 2's set exactly (the
  301-pair diff against the pre-build scan on the same tree: 0 lost, 0 gained);
- N cannot lose a finding by construction: deleting a filter that runs after the verb test can only turn a mention into
  a dependency.

The other findings are F's own (M1 the 17 s quadratic line, M2 the indented-list losses, m3–m6) and die with F; none
applies to N. What F would have fixed, and N does not, is filed as backlog #693 (the four live
`.agents/skills/brief/SKILL.md:62` misses and §5.4's MISS bounds), with the r1 inputs as the cases any later attempt
must pass. §6: no second fold in this component under any outcome.

```yaml
round: 1
fixes_nontrivial: true
subject: phase6-detector4
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: Blocker, aim: deliverable, fix_induced: true, component: publishability-detector4, disposition: fixed}
  - {id: X2, severity: Major, aim: deliverable, fix_induced: true, component: publishability-detector4, disposition: fixed}
  - {id: C1, severity: Blocker, aim: deliverable, fix_induced: true, component: publishability-detector4, disposition: fixed}
  - {id: C2, severity: Major, aim: deliverable, fix_induced: true, component: publishability-detector4, disposition: fixed}
  - {id: C3, severity: Minor, aim: deliverable, fix_induced: true, component: publishability-detector4, disposition: fixed}
  - {id: C4, severity: Minor, aim: deliverable, fix_induced: true, component: publishability-detector4, disposition: fixed}
  - {id: C5, severity: Minor, aim: deliverable, fix_induced: true, component: publishability-detector4, disposition: fixed}
  - {id: C6, severity: Minor, aim: deliverable, fix_induced: true, component: publishability-detector4, disposition: fixed}
```

"fixed" here means removed with F by the fallback, not patched. X = Codex, C = Claude, numbered as in each review.
Round 2 reviews N (one half, alternation).
