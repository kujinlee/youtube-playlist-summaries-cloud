# Round 6 — `push-hook-quoted` (PR #542, backlog #428) — coordinator — CONVERGED; one literal loosening on an unproducible input is folded anyway

REVIEW GAP: codex — the Codex run was killed by the OS for low memory before it produced anything (2026-11-08 21:10); the Claude adversarial fallback stood in, per `docs/plugins.md`.

```yaml
round: 6
fixes_nontrivial: false
subject: push-hook-quoted
halves:
  codex: gap
  claude: ran
findings:
  - {id: C-F1, severity: Low, aim: deliverable, fix_induced: false, component: hook-adapter, disposition: fixed}
  - {id: C-F2, severity: Low, aim: deliverable, fix_induced: false, component: detector-judge, disposition: fixed}
```

The Claude adversarial fallback (`docs/reviews/claude/push-hook-quoted-r6-claude.md`) reviewed `ffcdb4b1`: the
round 5 floor fold, with master merged in. **Verdict: CONVERGED — no BLOCKER.**

- "No worse than master" holds by construction. Every command master's trigger matches also matches the branch's
  push-word check, so the floor runs on every command `decide` allows that master would act on.
- The floor is master's exact blob (`ddb129b5`). It runs the bytes it hashed, and every failure path refuses.
- 351/351 and 59/59 pass. Two mutations were hand-checked, and each was killed through its named case.

**C-F1 (Low): a payload of TWO JSON documents.** If the first document carries a non-string command mentioning
`hookspath` and the second a feature-branch push, master's `jq -r` reads both and refuses, while the branch reads one
and allows. Claude Code sends one JSON object per call, so this input cannot be produced. But it is a literal
loosening, and the reviewer correctly answered flagged id `2d51171ccc52` as `finding`. **Folded rather than argued:**
the hook refuses any payload that is not exactly one JSON document. That makes the adapter strictly at least as strict
as master on its input path, with a case and a mutation, and a scoped round 7 re-answers the id.

**C-F2 (Low): fixed in the fold (it cost 0.017 s), not filed.** The equivalence case exercises the floor through only three kinds of command. A floor bypass
limited to another kind would leave it green. The guarantee rests on `verdict`'s four lines, which two mutations
pin. The suggested follow-up is a test where the floor always refuses, checked against every command `decide`
allows. It goes to backlog #428's status as a follow-up.

**Fold.** C-F1: the hook reads the payload with `jq -s` and refuses NOT CHECKED unless it is exactly one JSON
document with a string command (`.claude/hooks/block-default-branch-push.sh`); the reviewer's two repros now refuse
on the branch (master: deny and allow). Hook self-test 59 → 65, with a one-document multi-line feature push as the
allowed control. The check is shell, which the mutation harness cannot mutate, so it is pinned by those cases in CI's
hook self-test step; three hand mutations of the read each reddened them. C-F2's suggested test cost 0.017 s, so it
was added rather than filed: `floor` stubbed to always refuse, every one of the 92 commands `decide` allows with a
push word must come back refused (detector 351 → 352 cases), and a mutation that calls the floor only for `<`, `>`,
`-o`, `-c` or `=` — which leaves the equivalence case green — reddens it (mutations 107 → 108).
