# Round 2 — `hse-slice-d` — coordinator — NOT CONVERGED (Claude half)

Claude (`docs/reviews/claude/hse-slice-d-r2-claude.md`) reviewed `9984c3c1`, the round 1 fold: 5 MAJOR, 2 MINOR, no BLOCKER,
one fix-induced (the `./` literal, from round 1's XM2 fold). Each finding came with a constructed input it ran; each fold case
below rebuilds that input. Not thrashing: round 1 had no fix-induced finding, so two consecutive rounds do not carry one.

REVIEW GAP: codex — alternation (round 2 is the Claude half's; Codex reviews round 3).

```yaml
round: 2
fixes_nontrivial: true
subject: hse-slice-d
halves:
  claude: ran
  codex: alternation
findings:
  - {id: CM1, severity: High, aim: deliverable, fix_induced: false, component: detector-6-config, disposition: fixed}
  - {id: CM2, severity: High, aim: deliverable, fix_induced: false, component: detector-2-python, disposition: narrowed}
  - {id: Cm1, severity: Medium, aim: deliverable, fix_induced: true, component: detector-2-python, disposition: fixed}
  - {id: CM3, severity: High, aim: deliverable, fix_induced: false, component: detector-2-python, disposition: fixed}
  - {id: CM4, severity: High, aim: deliverable, fix_induced: false, component: detector-4-prose, disposition: fixed}
  - {id: CM5, severity: High, aim: deliverable, fix_induced: false, component: detector-4-prose, disposition: fixed}
  - {id: Cm2, severity: Medium, aim: deliverable, fix_induced: false, component: detector-2-python, disposition: narrowed}
```

| Id | Finding | Fold |
|---|---|---|
| CM1 | `os.getenv("X") or None` counted as a working fallback | an `or` operand after the read is a fallback only when it is not the constant `None`; case `r2: a None given through or …` |
| CM2 | a missing runner target reached through a name (`HELPER = "x.py"`, `os.path.join`) was dropped | NARROWED to a stated bound. Measured: judging every resolved load the reader groups added 29 findings on the live tree, every one a self-test running a fixture file it writes just before the call; statically a file written at run time and a missing file are the same. Kept: a literal argument of a runner. The docstring of `_invocations` states the bound |
| Cm1 | (fix-induced) a `./`-prefixed literal never matched the reader's normalised target | literals are `os.path.normpath`'d before the comparison; case `r2: a runner's missing target …` |
| CM3 | the reader's `unresolved` census was discarded, so a load it could not read became zero findings | each unread load is a detector 2 `unread` finding at its line (62 on the live tree); failing the whole component closed would make most components CANNOT RUN, and a per-load finding is the narrower fail-closed form; same case |
| CM4 | a numbered list introduced by "Then read, in this order …:" — its items were mentions (`brief`: `TaskList`, `docs/backlog.md`, `docs/roadmap-to-launch.md`) | a list item is a prerequisite when its introducing paragraph ends with a colon AND holds an imperative (`LEAD_VERBS`); the colon alone added 42 memory-note bullets under labels such as `**How to apply:**`, the imperative gate removed 41; case `r2: a list item or an untagged block …` |
| CM5 | an untagged fence holding a tool procedure (`explainer-delivery`: `TaskList -> TaskStop …`) was never a dependency | the same introduction rule applies to a line of an untagged fence; same case |
| Cm2 | an aliased `subprocess`/`os` import hides runner and environment reads | NARROWED to a stated bound in `_invocations`: no shipped file loses a coupling today (the two aliased runners run `git` only) |

Live tree, measured on the fold: 228 → 296 findings — +62 `unread`, +5 the CM4/CM5 couplings the review named, +1
`docs/memory/reservation-release-slice-state.md:17` (`gemini`, a list under "**Open residuals …:**": the word "Open" satisfies the
imperative gate; the item does state a prerequisite, "verification … before flipping", so it is kept and recorded here). Self-test
103/103; 6 mutations added and 5 rebound (154), each killed by its named case.
