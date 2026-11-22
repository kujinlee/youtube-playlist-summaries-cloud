# Round 4 — `merge-ready-thrash-hold` — coordinator — CONVERGED; no findings

Codex reviewed bf5d397c (the round-3 fold of backlog #680 part 2): `docs/reviews/codex/merge-ready-thrash-hold-r4-codex.md`
(no BLOCKER or MAJOR; VERDICT: CONVERGED). Rounds 2+ alternate, so the Claude half did not run this round.

REVIEW GAP: claude — alternation

**The Codex half stated a limitation, so the coordinator ran the missing probes.** Codex confirmed the two self-tests
(467/467, 130/130), `parse_header` identical to master over 2998 review files, and 3 of the 9 new mutations red in
full clones, but said it did not run adversarial inputs through `main()`. A single CONVERGED is not proof, so the
coordinator re-ran round 3's reviewer probes (`variants.py`, 17 header shapes, through `main()` with `gh` faked and
git real, in a full clone at bf5d397c):

- **FAILS IF (a thrashing pair gets READY):** every one of the 17 shapes returns rc 3. 14 are cannot-judge HOLDs (a
  second or re-spelled key, `[]` with items under it, unindented sequences, near-miss and `<<` field names, a ` #` in
  a component, multi-line flow forms) and 3 arm THRASHING (indented control, tab indent, `fix_induced: yes`). None
  returns READY.
- **False HOLD on an ordinary PR:** a clean pair (`findings: []  # none` twice), a pair with non-fix-induced findings,
  and a pair with only one fix-induced round each return rc 0, READY.

Round cap: from r4 only a BLOCKER is folded. There is none and nothing to file; backlog #695 (filed at r3) stands.

```yaml
round: 4
fixes_nontrivial: false
subject: merge-ready-thrash-hold
halves:
  codex: ran
  claude: gap
findings: []
```
