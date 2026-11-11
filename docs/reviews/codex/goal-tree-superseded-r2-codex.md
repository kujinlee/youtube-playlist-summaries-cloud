<!-- codex-review: model=gpt-6.1-sol -->

**NOT CONVERGED.** Three findings; all reproductions executed.

1. **Medium — `Previously:` does not exclude the history suffix.**  
   `scripts/goal-tree.py:134`, `:597`

   Failing Status cell:

   ```text
   🟠 **OPEN** — reopened. Previously: pending — ✅ **SUPERSEDED by backlog #12**
   ```

   `row_fates` returns `('superseded', 'superseded → backlog #12')`. Even two spaces after `Previously:` defeats the exclusion. The negative lookbehind checks only the immediately preceding characters, contradicting the promised “anything after `Previously:` is ignored.”

   **Fix:** strip code spans, truncate at the first `Previously:`, then match markers. Test intervening prose, whitespace, and multiple historical markers.

2. **Medium — valid double-backtick code spans activate quoted markers.**  
   `scripts/goal-tree.py:597`

   Failing Status cell:

   ```text
   ✅ **FIXED** — use ``✅ **SUPERSEDED by backlog #12**`` as an example
   ```

   Result: superseded. The single-backtick regex removes the empty delimiter pairs and leaves their contents exposed.

   **Fix:** strip code spans using matching backtick delimiter runs. Add double-backtick examples, including contents containing a single backtick.

3. **Low — a precedence mutation survives all 192 tests.**  
   `scripts/goal-tree.py:304`, tests around `:1342`

   Executed mutation:

   ```python
   state in ("merged", "next", "closed", "notfound")
   ```

   **192/192 still pass.** With `backlog #10, PR #999`, #10 superseded and #999 absent from otherwise successful gh results, this mutation replaces the required `❓ notfound` with `✖ superseded`.

   **Fix:** assert state and detail for an unlisted PR alongside each fate, and register this mutation. The existing implementation handles this correctly; its promised precedence lacks regression coverage.

The coordinator’s reopen assumption is also too strong. **Today’s backlog #327 (`docs/backlog.md:311`) actually appends “REOPENED BY THE OWNER” after supersession prose without moving that prose behind `Previously:`.** Its supersession is lowercase and unbolded, so today’s parser correctly leaves it live; it is not a current false classification. However, the admitted failure becomes reachable by applying the supported fate-marker spelling to this existing history shape. The backlog does not establish the claimed universal reopen convention.

Validation: `python3 scripts/goal-tree.py --self-test` passed **192/192**. Real `row_fates(docs/backlog.md)` returned **434 Items rows, no problems**, with only **124, 125, 127, 189, 213, 405** superseded; #405 points to #481. No repository plan contents were read.

**NOT CONVERGED**
