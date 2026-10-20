<!-- codex-review: model=gpt-6.1-sol -->

1. **High — `scripts/check-review-decision.py`, `rounds_for`: fallback discards another reviewer’s High.**  
   Input: no coordinator headers; Codex records clean rounds 1 and 2; Claude’s round 2 records a valid deliverable High. The `if h["round"] in by_round: continue` clause discards Claude’s entire round because Codex was read first. Executed result: `decide(..., "full-loop", True)` returns **`STOP`**, claiming no Blocking/High and nothing in the deliverable. Coordinator precedence does not justify treating one half as adjudication of the other.

2. **High — `scripts/check-decision-scheme.py`, `_round_docs` / `subjects_starved`: starvation depends on filesystem traversal order.**  
   Input: historical Codex r1/r2 documents, then a coordinator r2 document added after arming. `_round_docs` retains only one path per round. When the new coordinator path overwrites the historical half, `subjects_starved` names the historical subject as newly starved. I reproduced this through `_round_docs`. Conversely, an old path overwriting a new path hides the addition.

   Independently, `sorted(rounds)[1]` identifies the second **number**, not the document whose arrival established two rounds. With historical r2 and newly added r1, the function returns `[]`, missing the subject’s actual transition into scope. The ratchet needs historical round membership, rather than one surviving filename.

3. **High — `scripts/check-decision-scheme.py`, `main` / `_corpus_now`: failed measurement produces a reassuring pass.**  
   Input: `_corpus_now` returns its documented failure shape, `{"median": null, "mean": null, "error": "permission denied"}`, with an armed baseline and otherwise quiet inputs. Normal mode never checks `error`; trigger 6 skips the missing measurements. Executed output:
   ```
   pinned median 4 vs now None
     all triggers quiet
   ```
   Exit status is **0**. The error text is suppressed. Only `--rederive` handles this as CANNOT RUN, contradicting the exception-handler comment.

4. **High — `scripts/check-decision-scheme.py`, `validate_row`: an exhausted ladder can place another bet.**  
   Input:
   ```json
   {"subject":"s","unit":"u","route":"accrete","routes_tried":["accrete","redesign","split","defer"],"outcome":null}
   ```
   `route_next` correctly returns `None`, but `validate_row` accepts this pending retry because it never relates `route` to `routes_tried`. Executed `main` returns **0**, reporting `all triggers quiet`. Trigger 2 also stays silent because the outcome is pending. This is an explicitly recorded retry after exhaustion, requiring no inference about causation.

5. **Medium — `scripts/check-decision-scheme.py`, `validate_row` / `t5_ranker_miss`: malformed booleans erase misses.**  
   Input: two otherwise valid continued rows with `"ranker_hit":"false"`. Validation accepts both strings, and `bool("false")` converts both to hits. Executed result: **exit 0, all triggers quiet**, instead of rejecting unusable rows with exit 2. This concerns structural validation of authored data, not verification of the author’s judgement.

6. **Medium — `scripts/check-decision-scheme.py`, `t4_no_improvement`: units are counted as independent subjects.**  
   Input: five stopped rows for five different units of **one subject**, each recording four rounds; distribute routes so trigger 3 remains quiet. Executed result: **exit 1**, asserting “the last 5 subjects” have median four. Only one subject was measured. Since the pinned comparator is per subject, this creates a premature failure with an incompatible denominator.

7. **Medium — `scripts/check-decision-scheme.py`, `main` / `validate_row`: unreadable inputs become ordinary process failures.**  
   Input: a JSONL line containing `null`. `read_log` successfully decodes it, then `validate_row` raises an uncaught `TypeError`. A log read raising `PermissionError` likewise escapes the `except ValueError` handler. Both terminate the CLI with **exit 1 and a traceback**, rather than exit 2 and CANNOT RUN. No trigger measurement established a failure.

8. **Medium — `scripts/mutations/check-decision-scheme.json`, coverage of `paths_added_since`: the history-selection clause is unguarded.**  
   I changed `--diff-filter=A` to `--diff-filter=M` in memory and ran the resulting suite: **64/64 passed**. This mutation stops detecting newly added round documents and selects edits instead. No manifest entry exercises that clause; the starvation tests inject `added` and bypass its production entirely.

   Both recorded rejection reasons do hold: `v >= n1` is equivalent to `v == n1` because `n1` is the maximum; changing `< 2` to `< 1` raises `IndexError` with **zero `[FAIL]` lines**, which I reproduced.

Execution evidence: decision-scheme **64/64**, review-decision **91/91**, review-rounds, ratchet-contract, fixture-variation, main-drivable, self-test-count audit, and plan-code **178/178** passed. The full mutation sweep was not run.

The requested numbers reproduce: **254/261 = 97%**, **171/261 = 66%**, **91/261 = 35%**; mean components **13.8**; exact one-sided lower bound **36.84%**; median **4** over **57** subjects; **5/10** tied at first place. No numerical discrepancy found in those claims.

NOT CONVERGED
