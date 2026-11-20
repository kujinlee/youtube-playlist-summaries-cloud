# Round 3 — `decision-tags` — coordinator — NOT CONVERGED (Claude half)

Claude (`docs/reviews/claude/decision-tags-r3-claude.md`) reviewed `867e18b7`, the round 2 fold. There was no BLOCKER and there was 1 MINOR finding, caused by
the fold itself. The round 2 fold had replaced §3a's copied refusal list with a pointer to the scanner's symbols, but the pointer was still a LIST, and it left out
`_DECISION_REFUSE_FOREIGN` (`<svg>`, `<math>`), a rule the round 1 text had named.

Reproduced before folding, outside the repository: a fragment holding `<svg><text data-decision>Q?</text></svg>`, composed with
`brief-compose.py --content <frag> --slug tb --title T --out <scratch>/ob.html`, gives rc=1 and
`CANNOT RUN — decision 1 of 1 (<text data-decision> at line 1) would be counted but not seen: it is on or inside a <svg>, foreign content whose visibility this check does not model`.
So the code refuses it and §3a's list of symbols did not mention it.

The fold stops listing. §3a now names the two functions that produce every refusal, `_DecisionScan.handle_starttag` (which computes each refusal reason,
`brief-compose.py:1262-1283`) and `render_decisions` (which raises it, and the `id`/`name` collision, at 1337-1345). A new constant added to the scanner is read
by `handle_starttag`, so this pointer does not go stale when one is added. The bound (the scanner reads markup, not CSS) is unchanged.

⚠ **THRASHING is armed.** Rounds 2 and 3 both carry findings caused by the previous round's fold, in one component (`explainer-delivery-3a`). Both were the
same class: a prose copy of a code list, which drifts. Phase 6 fires on that condition (dev-process.md, *The arming condition*). Round 4 is past the round cap
(review-method.md §0 Q4c), so its findings are FILED unless a BLOCKER.

REVIEW GAP: codex — alternation (rounds 2+ run one half; round 3 is the Claude half).

```yaml
round: 3
fixes_nontrivial: false
subject: decision-tags
halves:
  codex: gap
  claude: ran
findings:
  - {id: Cm1, severity: Medium, aim: deliverable, fix_induced: true, component: explainer-delivery-3a, disposition: fixed}
```

| Id | Finding | Fold |
|---|---|---|
| Cm1 | the pointer listed the scanner's symbols and omitted `_DECISION_REFUSE_FOREIGN` (`<svg>`/`<math>`) | §3a points at `_DecisionScan.handle_starttag` and `render_decisions`, the two functions that produce the refusals, and lists no constants |

Mutations/verification: no script was touched, so there is no self-test and no mutation manifest for this fold. Checked: both named functions exist in
`scripts/brief-compose.py` (`class _DecisionScan` 1206, its `handle_starttag` 1242, `render_decisions` 1324), and every `refusal =` assignment in the scanner
lies inside `handle_starttag` (1262-1283). `check-docs.py` reports `Documentation integrity OK`; `check-explainer-delivery.py` reports
`1 shared description, 5 skills cite it, 0 restatements`.
