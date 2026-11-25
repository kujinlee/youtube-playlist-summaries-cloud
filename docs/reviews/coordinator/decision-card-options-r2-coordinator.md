# Round 2 — `decision-card-options` — coordinator — Codex NOT CONVERGED (1 MAJOR, rejected on trace)

REVIEW GAP: claude — alternation (rounds 2+ run one half; both halves ran round 1).

```yaml
round: 2
fixes_nontrivial: false
subject: decision-card-options
halves:
  codex: ran
  claude: gap
findings:
  - id: XM1
    severity: Major
    aim: option-less decision pages are not byte-identical to master (the shared DECISION_JS grew)
    fix_induced: false
    component: scripts/brief-compose.py DECISION_JS
    disposition: rejected
```

| id | severity | finding | disposition |
|---|---|---|---|
| XM1 | Major | an option-less page composes to 20,235 bytes vs master's 19,655 | **rejected on trace** — see below |

**Why XM1 is rejected.** The byte-identity requirement came from the coordinator's own round-2 prompt, which
overstated the invariant. The approved behaviour is "a card without options is unchanged": it renders and sends
what master's card did. Traced:

- `render_decisions` writes `data-ex-options` / `data-ex-rec` only when options are declared
  (`scripts/brief-compose.py:1719-1720`; the comment at :1120 says the same).
- `offer` (`:1360`) reads `data-ex-options`; when it is absent, the `else` branch is master's button code verbatim:
  ★ Recommended, ✔ Yes, ✖ No, then ✎ Other….
- The 580 extra bytes are therefore code an option-less card never runs: `offerChoices` and the branch.

Emitting a second copy of the script just for option-less pages would put two versions of one rule in the file,
which [one-rule-one-place] warns against. Nothing is folded. Round 3 runs the Claude half to check this
adjudication and the round-1 fold.
