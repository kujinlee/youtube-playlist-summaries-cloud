# Round 4 — `goal-node-tree-s1` (PR #631) — coordinator — CONVERGED (Codex half); nothing to fold

```yaml
round: 4
fixes_nontrivial: false
subject: goal-node-tree-s1
halves:
  codex: ran
  claude: gap
findings: []
```

REVIEW GAP: claude — alternation (round 4 is the Codex half; the Claude half reviewed round 3)

The Codex half (`docs/reviews/codex/goal-node-tree-s1-r4-codex.md`, gpt-6.1-terra) reviewed head `3e5d8d70`: the r3
fold and the docstring count it changed. **No findings.** It ran both self-tests with stdin closed (96/96, 51/51),
and in a scratch copy confirmed that the restored broad orphan mutant and the narrow r2 one each fail the orphan
case, that reverting F2 or removing the control wording each fails the F2 case, and that the `.get(...)` rewrites
still compare a present value with the same expected value.

## The three loosenings it named — each is the approved spec, not an accident

| Check | Codex | Answer |
|---|---|---|
| `9a6218192351`, `c5f9105b20f3` | stateless nodes, and absent nodes with anchors, now pass rules master refused | **Intended.** `docs/superpowers/specs/2026-11-23-goal-node-tree-design.md` line 67 makes `harness-ships-elsewhere` an anchor whose node is `absent`; line 368 and decision Q13 (owner-approved 11-23 21:20) give a node no `state:` until the owner says `built`. A stateless node still draws every other refusal (an `expected-because:` without `absent`, duplicate keys, an invalid state), which r3's reviewer probed. |
| `1772e62bc392` | the test no longer requires an absent node with an anchor to be refused | **Intended**, for the same line 67: the old case asserted the rule the spec retires. |

The other eleven checks: not a loosening.

Past the round cap, nothing would have been folded except a BLOCKER, and there is none. No guarded file changes after
this round.
