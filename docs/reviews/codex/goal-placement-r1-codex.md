<!-- codex-review: model=gpt-6.1-sol -->

## Findings

- **MAJOR — scripts/goal-tree.py:1491:** Ledger waits are still discarded. Input `{"id":"job","what":"work","goal":"g","waits":"PR #123"}` with declared goal `g` produces a placed item whose agenda `waits` is `None`. The page therefore says “not recorded” despite an explicit wait, violating #514(d). Preserve `waits` through placement and loose-entry derivation into the agenda; test a nonempty wait.

- **MINOR — scripts/goal-tree.py:702:** Declaring a matching thread falsely reports completion. Start with `{"id":"job","what":"work PR #9","goal":"g"}` placed by goal; then declare `- fix · PR #9 · work` under `g`, keeping the ledger and open PR unchanged. `changes()` emits `no longer in flight: job` even though the thread remains `inflight=True`. Account for handoffs to reference placement before emitting removal.

- **MINOR — scripts/mutations/session-state.json:1512:** The mutation “the refusal never says to propose a goal” generates an unterminated string literal at session-state.py:345. It cannot exercise its expected behavioral assertion. Replace the message fragment with syntactically valid Python, then verify the named assertion kills the mutant.

Both self-tests passed: goal-tree **495/495**, session-state **134/134**. All mutation anchors matched; the mutation above was the only generated syntax failure.

## Loosening answers
LOOSENING-CHECK e7aa5bfc3ab7: not a loosening
LOOSENING-CHECK 52fb30e94f81: finding: --add with --goal g and no --thread is now accepted; master refused goal-only entries.
LOOSENING-CHECK 554ec5c87391: finding: --add with --goal g and no --thread is now accepted; master refused goal-only entries.
VERDICT: NOT CONVERGED
