<!-- codex-review: model=gpt-6.1-sol -->

1. **Blocking — owner instructions still disappear.** `scripts/session-state.py:429–430`. **Fix-induced: no; R1 fix incomplete.** On the real ledger, `build-402` records `(owner: 'implement when convenient')`, but `keep_whole()` returns false. Its instruction falls outside the 120-character title. Reproduced complete hiding with six newer routine entries and each of:
   - `what="waits-on-owner: choose A"`
   - `what="NOTE: WAITS-ON-OWNER: choose A"`
   - `what="routine", on_done="OWNER 18:50: chose A"`
   - `what="routine", on_done="NOTE: (card when back) choose A"`

   Only the hidden id remains. **Fix:** follow the decision log’s named fallback: print the ledger whole; trim PRs and snapshot headings.

2. **High — the snapshot digest still excludes real owner decisions.** `scripts/compaction-state.py:680`, `:787–793`. **Fix-induced: no; R1 fix incomplete.** Snapshot capture still selects `waits_on_owner()`, rather than the widened matcher; the digest then drops the in-flight body. Against the real ledger, nine entries recognized by `keep_whole()` vanish from the digest, including `card-451`, `card-old-halves`, and `card-plugins`. Minimal input: `## In flight BEFORE compaction\nNOTE: (card when back) choose A` followed by another section—the decision disappears. **Fix:** preserve the complete ledger block through capture and print; retain NOTE decisions too.

3. **High — “whole” owner sections contain already-truncated decisions.** `scripts/compaction-state.py:484`, `:693`, `:705`. **Fix-induced: no; newly preserved text remains lossy.** Input `what="WAITS-ON-OWNER: "+170*"x"+" CHOOSE_B"` and `on_done=125*"y"+" NEVER_MERGE"` loses both decisive tails in `decision_section()`. The section also has a 1,200-character cap. `/compact instructions` beyond 300 characters are cut at capture and digest. **Fix:** preserve decision text before digesting; trimming headings cannot recover discarded words.

4. **Medium — green tests do not establish the promised protection or size bound.** `scripts/session-state.py:508`, `:518–522`. **Fix-induced: yes, for the added approval regression case.** Both its `what` and `on_done` independently match `OWNER_TEXT`; removing either field’s check still passes that case. Add separate cases with neutral opposite fields. The 25% assertion uses twenty long routine entries and one owner entry; measured real-ledger compact/full output is **5,759/6,690 characters (~86%)**. Owner-heavy input can grow beyond full output because compact mode is uncapped. **Fix:** state and test the intended bound separately from decision retention.

Both foreground suites passed: **81/81** and **103/103**. Additional probes read the real ledger; its hash remained unchanged. No `.claude/plans/` files were accessed.

`normalise_what()` only rewrites the entry supplied to `--add`; canonicalizing a bare marker aligns both colon-based slices. I found no existing-entry migration regression. Absolute ledger paths, file-order-independent `at` sorting, and NOT CAPTURED survival passed the probes.

**NOT CONVERGED.** The real-ledger counterexamples satisfy the decision log’s named failure observation and trigger its **SPLIT** fallback.
