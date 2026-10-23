<!-- codex-review: model=gpt-6.1-sol -->

**Major — pins exempt future losses on the same unit.** `scripts/check-decision-scheme.py:396` (identity reduced to `(subject, unit)` at `:1158`).

- **Input, executed:** current log plus the backfill row from `17db30c2`; append a prospective `redesign` bet with `outcome: continued` on either pinned unit. Tested both units independently; both histories pass `invalid_rows`.
- **What happens:** both runs exit **0**, with no trigger-3 failure. Trigger 10 falsely reports the new loss among `"2 lost bet(s) PREDATE trigger 3"`. The historical pin transfers to subsequent losses without ever becoming unused. Reusing a unit name has the same identity collision.
- **Fix:** pin the specific historical bet, using an immutable row identity or fingerprint. Preserve that identity through `lost_bets`; match exemptions against bets rather than units. Add tests where the historical bet escalates and its successor loses, for both pinned histories.

**Low — explicit `null` bypasses malformed-pin refusal.** `scripts/check-decision-scheme.py:1144`.

- **Input, executed:** `"lost_bets_before_trigger3": null`.
- **What happens:** `pinned_lost_bets` returns `(frozenset(), None)`. An armed world with an empty log exits **0**, saying `"all triggers quiet"`; the current log exits **1**, blaming historical losses instead of reporting CANNOT RUN. This contradicts the documented refusal of a present key with the wrong shape.
- **Fix:** distinguish an absent key from a present null value; require a list whenever the key exists. Add explicit-null parser and CLI cases.

Other mandate checks:

- The acknowledgment validator, corpus verification, verdict parser, and associated mutation entries are removed. No trigger still dispatches on the removed row kind. The plan note accurately records removal; remaining mentions describe history.
- Trigger 2’s complete function text is **identical to master**, also identical to `753645a7`.
- Against master’s corpus, master’s log exits **0** with one historical hit and one unused backfill pin. Adding the exact backfill row exits **0** with both pins hit. Using the branch corpus with master’s log instead produces an unrelated trigger-1 failure for `trigger3-lost-bet`; that failure must not mask these checks.
- **245/245 self-tests pass.** All **107/107 manifest mutations** were individually applied on a temporary copy, failed the suite, and produced their expected named failures. Manifest counts match: **128 → 107**, repository total **1863**.
- The pin tests use distinct units and ladder positions, but omit the transition from a pinned historical loss to a later loss on that same unit. Thus green tests and mutations do not refute the Major finding.

All executions used temporary copies; no worktree files or git state were written.

VERDICT: NOT CONVERGED
