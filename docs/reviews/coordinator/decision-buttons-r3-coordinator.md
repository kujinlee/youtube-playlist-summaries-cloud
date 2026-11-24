# Round 3 — `decision-buttons` (PR #628) — coordinator — CONVERGED (Claude half); every finding FIXED

```yaml
round: 3
fixes_nontrivial: true
subject: decision-buttons
halves:
  codex: gap
  claude: ran
findings:
  - {id: F1, severity: Medium, aim: deliverable, fix_induced: false, component: sent-state, disposition: fixed}
  - {id: F2, severity: Medium, aim: deliverable, fix_induced: false, component: sent-state, disposition: fixed}
  - {id: F3, severity: Low, aim: instrument, fix_induced: false, component: answerer, disposition: fixed}
  - {id: F4, severity: Low, aim: deliverable, fix_induced: false, component: sent-state, disposition: fixed}
```

REVIEW GAP: codex — alternation (round 3 is the Claude half)

Claude (`docs/reviews/claude/decision-buttons-r3-claude.md`: CONVERGED, 2 Minor, 2 Nit) reviewed head `456482d5`, the
round 2 fold. In the header, severities use the vocabulary `check-review-decision.py` validates (Minor → Medium,
Nit → Low). For the same reason, the r1 and r2 headers' Major/Minor were rewritten to High/Medium in this fold; their
prose is unchanged. None of the four findings was caused by the r2 fold. F1 is a residue of r2 C1 that the r2 case could
not see.

| Finding | Disposition | Evidence |
|---|---|---|
| **F1** (Minor): recording one of two identical decisions handed its *sent* state to the other | **fixed** | Confirmed in `DECISION_JS`. Occurrences were counted over `.ex-decision-open` only, so once twin A became a done tag, B was the first occurrence and took A's key. Now every `.ex-decision` is keyed in one pass at load, done tags included. A done tag's label has its `— ANSWERED: <value>` tail stripped first (`baseKey`), so a decision has the same base key open or done. New case "recording one of two identical decisions does not hand its 'sent' to the other". It covers unlabelled twins with only A answered, where B must offer the buttons, and labelled twins with both answered, where B must keep its own `no` and A's key must be gone. Mutations: count over open tags only → RED; leave the ANSWERED tail in the key → RED. |
| **F2** (Minor): a decision the session re-opens showed its old *sent* | **fixed** | The loop that keys every tag now calls `forget` on any tag that is done at load. Once the session has recorded the decision, the browser's *sent* is spent, and if the decision is later re-opened it starts clean. New case "a decision done at load forgets its key; re-opened, it offers the buttons": answered, then loaded done (store empty), then loaded open again (buttons offered). Mutation: drop that `forget` → RED. **Bound:** the key is forgotten only if this browser loads the page while the decision is done. A page that is recorded and re-opened between two of the owner's loads still shows the old *sent*. `change` recovers from that. |
| **F3** (Nit): no case killed the `status_text` skipped-list filter, and the r1 answerer mutations were not ratcheted | **fixed** | New case in `ask_answerer.py`, "r3 (#628): --status lists a skipped question but never a skipped decision answer". A question and a card click are both asked while the answerer is off, and both become `skipped`. Only the question is listed. Five mutations were added to `scripts/mutations/ask_answerer.json`: the `pending()` filter, the page panel's filter, the anchored section regex, the `ANSWER: ` prefix, and the `status_text` filter. Before adding them, I applied each one by hand to a scratch copy of `scripts/`, and each turned the case it names RED. Pin 52 → 57. |
| **F4** (Nit): `change` forgot the sent answer before a new one was sent | **fixed (removed)** | Decided: the eager `forget` is removed, and so is the now-unused `remembered` parameter of `sent()`. The answer that was sent IS in `questions.md` until a new one replaces it, and `save()` on the next successful send overwrites the key. So after an abandoned `change`, or a reload, the card now shows what was actually sent instead of offering the buttons as if nothing had been sent. The r1 case "change forgets" was rewritten to "`change` offers the buttons again and keeps the answer sent; a reload still shows it". Mutation: restore `forget(tag)` in `change` → RED. |

The four new brief-compose mutations went into `scripts/mutations/brief-compose.json`, pin 98 → 102. Before adding
them, all three fix pieces were reverted together on a scratch copy, and the two new F1/F2 cases and the rewritten F4
case all went RED. The copy's 4th failure was the real-fragments case, which fails only because the copy has no
`docs/`.

## Decision log

`check-decision-scheme.py` trigger 1 failed on CI ("decision-buttons reached >=2 rounds with no log row"). Two
retroactive rows were added, one per fold, each an `accrete` unit, following the per-fold precedent of
`agent-watchdog` and `hse-slice-d`. r1 fold: bet LOST, because r2 found C1 and C2, one of them fix-induced. r2 fold:
the bet was lost in part, because r3 still found F1 and F2 in the sent state, but the stream stopped at round 3.

## Gates (worktree, after the fold)

- `python3 scripts/brief-compose.py --self-test`: 250/250 (248 → 250: two new cases; the "change forgets" case was rewritten). USAGE count updated.
- `python3 scripts/ask_answerer.py --self-test`: 125/125 (one new case). USAGE count updated.
- `python3 scripts/check-plan-code.py --mutate . --only scripts/brief-compose.py`, run in a scratch copy: 102 mutations, 102 killed, 102 attributed to the case each names, 0 survivors, re-control passed (rc 0) — measured over ONLY scripts/brief-compose.py, a diagnostic slice, not the full sweep.
