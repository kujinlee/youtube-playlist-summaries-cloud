<!-- codex-review: model=gpt-6.1-sol -->

1. **High — `scripts/check-decision-scheme.py`, `_corpus_now`: an unreadable subtree produces a successful partial measurement.**  
   **Input:** a readable `reviews/codex/` containing one four-round subject, plus `reviews/claude/` containing another subject’s eight rounds, with the latter directory chmod `000`.  
   **Observed:** under CI’s Python 3.12, `rglob` silently skips the unreadable directory. `_corpus_now` returns `{"median":4,"mean":4,"subjects":1}` with **no `error` key**. Driving `main()` with that corpus and otherwise quiet inputs returns **0**, printing **`all triggers quiet`**. The new error check cannot detect a measurement whose traversal silently omitted data.

2. **High — `scripts/check-decision-scheme.py`, `subjects_starved`: historical membership still depends on current paths.**  
   **Input:** commit `docs/reviews/old-r1-codex.md` and `old-r2-codex.md` before arming, then move both into `docs/reviews/codex/`.  
   **Observed:** using the actual historical tree and `_round_docs()` after the move returns **`(['old'], None)`**. Neither current path exists in `before`, so the function counts zero historical rounds and names an entirely historical subject as newly starved. The fold changed the query to a tree listing, but still intersects filenames rather than historical subject/round identities.

3. **Medium — `scripts/check-decision-scheme.py`, `tree_at`: Git’s quoted filenames do not match filesystem filenames.**  
   **Input:** an unchanged historical subject `é`, with two round documents, using Git’s default `core.quotePath`.  
   **Observed:** `ls-tree --name-only` returns quoted paths containing `\303\251`; `_round_docs()` returns literal `é`. `subjects_starved` returns **`(['é'], None)`**, despite both rounds predating arming. This reproduced in a one-commit temporary repository. Use NUL-delimited, unquoted path output rather than newline splitting and stripping.

4. **Medium — `scripts/check-decision-scheme.py`, `t4_no_improvement`: updates do not move subjects to the end of a dict.**  
   **Input:** stopped rows for subjects A–F, recording termination rounds `[9,9,9,1,1,1]`, followed by new stopped rows for A, B and C recording nine rounds. Use `accrete` for the initial rows and `redesign` for the later rows; all nine rows validate.  
   **Observed:** the latest five distinct subjects by stopped-row occurrence are D, E, A, B, C, whose median is **9**. The dict retains first-insertion order A–F, so the implementation selects B–F, whose median is **1**. Executed `main()` returns **0**, printing **`all triggers quiet`**, instead of firing trigger 4.

5. **Medium — `scripts/mutations/check-decision-scheme.json`, entry “rows are grouped by SUBJECT only…”: the declared attribution fails.**  
   **Input:** apply the entry exactly as shipped and run the 113-case suite over a green control.  
   **Observed:** the mutation is killed, but its required case **`unit_key partitions on (subject, unit), not on either alone` remains green**: the mutation changes `group_by_unit`, not `unit_key`. Other cases fail. `check-plan-code.py` requires **every** listed expectation to name exactly one red case, so this entry fails its attribution contract. Reproduced under Python 3.12; the claimed 34/34 verification does not hold. All 19 review-decision entries attribute correctly.

6. **Medium — `scripts/check-decision-scheme.py`, `tree_at` self-test/manifest coverage: selecting today’s tree instead of the historical tree survives.**  
   **Input:** replace the `sha` argument to `git ls-tree` with `"HEAD"`.  
   **Observed:** **113/113 cases still pass**. In production, already-committed post-arming reviews would appear in `before`, suppressing starvation. No manifest entry protects this selection. The positive `tree_at` test checks only that the result is a sufficiently large set, not that it represents the requested instant.

7. **Low — `scripts/check-decision-scheme.py`, `derive_outcome`: appearance counts are treated as round numbers.**  
   **Input:** component `c` appears in rounds 1 and 5. `scope_tally` returns `{"c":2}`; call `derive_outcome("s","c",4,tally)`.  
   **Observed:** it returns **`"stopped"`**, although round 5 proves continuation after round 4. The helper needs occurrence positions, not recurrence counts. Its current lack of production wiring limits the impact and is prudent: wiring it as documented would overwrite an authored `"continued"` with the incorrect `"stopped"`. Correct the observation model before integration; unavailable evidence should remain `None`.

8. **Low — `scripts/mutations/check-decision-scheme.json`, `_rejected_variant`, and `scripts/check-plan-code.py`, rejection commentary: the IndexError rationale is obsolete after the fold.**  
   **Input:** apply the rejected `len(rounds) < 2` → `< 1` mutation to the folded code.  
   **Observed:** the suite exits **1 with three named `[FAIL]` lines**, rather than raising `IndexError` with zero failures. The indexed expression was removed by the redesign. The other rejection reasons hold: `v >= n1` remains equivalent because `n1` is the maximum, and the former in-place shallow-clone branch is environment-equivalent on a full checkout.

Execution: both suites passed **113/113 and 85/85**, including under Python 3.12. The default guard, `--rederive`, review-rounds, ratchet-contract, fixture-variation, main-drivable, documentation integrity, self-test-count audit, and plan-code’s **178/178** suite passed. The full mutation sweep was not run.

Independent derivation from the pinned commit, across both layouts, confirms **105 subjects / 81 eligible / 392 eligible rounds / median 4 / mean 4.84**; coordinator **115/392 = 29.3%**, both-halves **280/392 = 71.4%**, over-four **31/81 = 38.3%**. The separate review-rounds total of 416 includes singleton subjects.

I found no accepted same-key retry bypass, no additional demonstrable t2 miss, and no timestamp interpretation bypass. Invalid earlier rows cause the whole run to refuse; redundant matching `routes_tried` does not override derived history.

NOT CONVERGED
