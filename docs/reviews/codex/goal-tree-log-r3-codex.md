<!-- codex-review: model=gpt-6.1-sol -->

1. **Major — FIX-INDUCED: a conflicting identity token reclassifies an action and merges it into a decision.** `scripts/goal-tree.py:404`

   **Reproduction:** In the temporary checkout, combine `needs_from_backlog(BACKLOG_FIXTURE)[0]` with:

   ```python
   needs_from_ledger([{
       "id": "probe",
       "what": "WAITS-ON-OWNER: ACTION: decision: backlog #5 — run the command"
   }])
   ```

   The ledger item becomes `kind="decision"`, despite its `ACTION:` marker. `consolidate()` merges it into backlog #5’s “Pick a name” decision. No separate action remains. This refutes the bet against merging across kinds.

   **Fix:** Preserve the independently declared action kind. Reject a conflicting identity, keep the item separate, and report the conflict. Add a case and mutation covering disagreement between `ACTION:` and the identity token.

2. **Minor — FIX-INDUCED: dashboard metadata is accepted for identity but discarded for counts and source text.** `scripts/goal-tree.py:385`

   **Reproduction:**

   ```text
   ## 2026-10-01 [needs-you]
   Pick a name.

   decision: backlog #5 (answers-open: 14)
   ```

   `needs_from_dashboard()` returns identity `[5, "decision"]`, but `multi=None` and text `"Pick a name."`. Consolidation merges the entry while dropping its explicitly stated fourteen answers. Moving the annotation onto the title produces `multi=14`.

   **Fix:** Parse identity and count from the same complete source before shortening display text. Preserve the relevant body text and count in merged provenance. Cover annotations in dashboard bodies and beyond display truncation limits.

3. **Medium — FIX-INDUCED: the tokenizer violates its stated quoting, heredoc and assignment bounds.** `scripts/regen-pages.py:52`, `:64`, `:87`; `scratchpad/pr363.md:38`

   **Reproduction:** These were checked with `may_merge()` and actual Bash execution using a harmless `gh()` function that prints `EXECUTED`:

   | Bash input | `may_merge()` | Bash result |
   |---|---:|---|
   | `echo '<<EOF'` followed by `gh pr merge 433` | False | Executes `gh` |
   | `X="a b" gh pr merge 433` | False | Executes `gh` |
   | `echo \; gh pr merge 433` | True | Prints text; no `gh` execution |
   | `cat <<'END DOC'` followed by `gh pr merge 433` and `END DOC` | True | Prints heredoc data; no `gh` execution |

   The heredoc regex reads quoted ordinary text as a redirection, suppressing subsequent commands. It also misses valid quoted delimiters containing spaces. Non-POSIX `shlex` mishandles escaped separators and assignments containing quoted spaces.

   These are ordinary simple-command forms, beyond the documented misses involving `case`, functions, `eval` and command substitution. The categorical claims that heredoc bodies never match and assignment prefixes are skipped are false.

   **Fix:** Recognise heredocs and shell words with quotation and escape provenance, or explicitly narrow the supported grammar and remove the categorical guarantees. Add these four cases and corresponding mutations.

4. **Minor — FIX-INDUCED: #318’s recorded reasoning misstates the historical redesign.** `docs/backlog.md:302`

   **Reproduction:** Compare the new rationale—`redesigned` and `moot` are answered because “the finding’s subject was removed”—with `docs/reviews/coordinator/ship-src-root-alone-r2-coordinator.md`. Its H1 section explicitly retains the “consulted the world exactly once” requirement and replaces interception with a static/dynamic design. It reports mutations against that replacement. The property was removed in **round 3’s retreat**, documented in the next coordinator record.

   **Fix:** Explain `redesigned` through the implemented replacement that answers the finding, rather than claiming removal. Distinguish that from the property removal accompanying this particular retreat. The coordinator can choose conservative vocabulary semantics, but the supporting history must be accurate.

Validation ran in `/tmp/pr433-r3.JFBF5w`; no repository files were edited. Round-2 examples were rerun. The original reference-number counts and non-backlog dependency flags no longer reproduce; the original quoted-semicolon and basic heredoc examples are fixed. Conditional-command over-firing is now accurately documented. The replay notice identifies the stored snapshot and refresh command.

The choices on #114, #117 and #211 are defensible. #318’s vocabulary choice is defensible, subject to the factual correction above. Retaining #306 is defensible: `sequence_error()` documents and prevents false adjacency across missing rounds. The other listed backlog items retain recorded owner involvement or an owner execution requirement; I found no additional standing-rule violation.

Checks passed: **140/140**, **40/40**, hook wrapper **40/40**, shared suites **67/67, 18/18, 246/246 and 203/203**. All **72 kept mutations were killed and attributed to their named cases**. Retirement explanations cover the deleted heuristics; the re-anchored assignment mutation remains present. Manifest counts match `EXPECTED_MUTATIONS`, totaling **2,502**. Passing mutations do not cover the counterexamples above.

VERDICT: NOT CONVERGED
