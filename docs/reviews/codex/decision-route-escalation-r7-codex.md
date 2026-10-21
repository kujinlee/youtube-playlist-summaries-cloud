<!-- codex-review: model=gpt-6.1-sol -->

Found two additional scoring failures beyond #337. I found no retry, walk-back, incorrect-gap acceptance, or nonterminal appendability failure through the history-aware validator.

1. **High — retroactive rows silence the route-collapse trigger.**  
   **Location:** `scripts/check-decision-scheme.py:205–210`; `docs/reviews/decision-scheme/decision-log.jsonl:5–6`.

   **Input:** five rows on five distinct subjects, each with `unit: "u"`, `route: "accrete"`, `outcome: "continued"`. Then append the two actual retroactive rows.

   **Observed:** before appending, t3 returns `"all 5 scored rows took route 'accrete'…"`. Afterwards, it returns `None`. The prospective decisions remain entirely collapsed; historical REDESIGN/DEFER entries supply the apparent discrimination.

   **Fix:** record prediction provenance structurally and make t3 select prospective decisions. A prose disclaimer does not affect its population.

2. **Medium — t7 counts retroactive rows and abstentions toward its prediction sample.**  
   **Location:** `scripts/check-decision-scheme.py:311–316`.

   **Input:** eight distinct-subject ACCRETE rows with `outcome: "continued"` and `ranker_hit: true`, followed by the two actual retroactive rows, neither of which contains `ranker_hit`.

   **Observed:** eight rows return `None`; adding the retroactive rows produces:
   ```
   10 scored rows (8 ranker hits) — re-evaluate now; at 10/10
   the one-sided 95% accuracy bound reaches 74%…
   ```
   There were only eight scored ranker predictions. Unlike t5, t7 treats outcome availability as prediction eligibility.

   **Fix:** count eligible prospective ranker predictions, requiring an explicit boolean `ranker_hit`. Keep outcome observations and prediction samples separate.

3. **Medium — #337 is reproducible and can suppress an existing failure.**  
   **Location:** `scripts/check-decision-scheme.py:228–240`; `docs/reviews/decision-scheme/decision-log.jsonl:6`.

   **Input:** five distinct stopped subjects with termination rounds `[4,4,4,1,1]`, baseline median `4`; append the actual retroactive pair.

   **Observed:** t4 initially reports median `4` and fires. Afterwards it returns `None`: the last-five population becomes `[4,4,1,1,2]`, median `2`. Deferred work displaces a subject and looks like improvement.

   **Fix:** distinguish termination disposition and prospective exposure. Excluding retroactive predictions alone would not resolve future prospective DEFER rows being counted as repairs.

4. **Medium — malformed `routes_tried` crashes validation instead of receiving a refusal.**  
   **Location:** `scripts/check-decision-scheme.py:517`.

   **Input:**
   ```json
   {"subject":"s","unit":"u","route":"accrete","routes_tried":null}
   ```
   with `prior=[]`. `false` and `7` reproduce it too.

   **Observed:** `TypeError` from `list(row["routes_tried"])`. This does **not** reopen retries, but malformed log data escapes the intended unusable-row diagnostic.

   **Fix:** validate the optional field’s type before conversion, or refuse it as obsolete. This is an existing boundary defect, not evidence that declared skips permit retries.

The remaining claim attacks produced these observations:

- **Retry, walk-back, exact gap:** I exercised 1,960 retry declarations, 1,190 walk-back declarations, and 1,050 gap probes across accepted histories, including non-list declarations and reordered lists. No invalid acceptance occurred. Case and surrounding-whitespace route variants were refused.
- **Appendability:** enumerating all 15 accepted route-history edges found no nonterminal dead end. DEFER ends the ladder intentionally.
- **Shape-only validation:** `validate_row(row)` accepts even a REDESIGN row with `skipped: false` and no reason. This is the documented weaker API. `main()` supplies history, so I could not turn it into a CLI retry bypass.
- **Reasons:** empty, whitespace, absent, and non-string reasons were refused. `"!!!"` and `"\u200b"` were accepted at line 507. They satisfy the implemented non-empty-string check, but provide no explanatory evidence. Rejecting punctuation would strengthen the approved contract; it would still not establish that a reason is meaningful.
- **Other trigger readers:** t2 returned quiet for the actual terminal history; t5 ignored both retroactive rows because neither supplied `ranker_hit`. t1 also accepts retrospective feeding: the actual pair clears starvation for `decision-log-model-redesign`. That proves coverage, not timely use of the mechanism.

The **first skip is safe as historical evidence only if its provenance remains distinguishable**. The actual line-5 row validates, derives attempts `["redesign"]`, and accounts for `["accrete","redesign"]`; none of those outputs encodes *rule-imposed* versus *judgement-imposed*. Its prose caveat is accurate, but an undifferentiated skip label cannot support “a human judged ACCRETE futile.” Add structured skip provenance before training. I found no implemented training consumer, so I could not demonstrate actual model contamination.

I independently ran both required commands: normal check **rc=0**, with the denominator warning; self-test **162/162**. Using the harness’s `stage_tree` and `run_mutations`, I reproduced **55/55 killed, 55/55 attributed, zero survivors**, with green **162/162** controls before and after.

Both re-pointed entries target relevant production behavior. The attempt-history mutation makes retries report as walk-backs and fails both named cases. The re-anchored exhaustion mutation disables t2 and fails its named exhaustion cases; its “MORE routes” title is now stale wording, but the binding and attribution are substantive. No review file was written.
