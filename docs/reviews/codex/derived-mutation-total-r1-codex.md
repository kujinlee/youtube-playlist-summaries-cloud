<!-- codex-review: model=gpt-6.1-sol -->

1. **HIGH — Coverage can shrink with green self-tests and no HOLD.** `scripts/check-merge-ready.py:868–870`; `scripts/check-plan-code.py:6499–6500`. **Fix-induced: yes**, through removal of the independent total backstop; the regex limitation predates this change.

   Concrete input: retain the existing pin and immediately append a duplicate key:

   ```python
   "scripts/check-vocabulary-collisions.py": 5,
   "scripts/check-vocabulary-collisions.py": (
       4
   ),
   ```

   Delete the last entry from `scripts/mutations/check-vocabulary-collisions.json`: `"the collision report names only ONE table — header truncated and per-hit lines dropped"`.

   Python uses the later value, so coverage falls from five entries to four and the manifest matches its effective pin. The changed lines contain no match for `PIN_LINE`; the unchanged original pin never enters its removed-line map.

   **Reproduced:** `check-plan-code --self-test` passes **253/253**, and `check-merge-ready --self-test` passes **209/209**. In a temporary real Git repository, production `gather()` followed by `hold_reasons()` returns `[]`; `final_verdict(0, "READY", [])` returns **READY**. This tests the house-rule decision with otherwise-green PR gates, rather than asserting live GitHub checks passed.

   Ordinary single-line decreases and removals are held. Moving an existing single-line pin to multiline formatting is also held as a removal. Once multiline, however, changing only its numeric continuation evades the regex. The duplicate-key input bypasses that initial formatting HOLD in one change.

2. **MEDIUM — The new source scan permits a typed total to return.** `scripts/check-plan-code.py:6504`. **Fix-induced: yes**, in the newly introduced guard.

   Concrete input:

   ```python
   case("typed total reintroduced", declared_total(), 2981,)
   ```

   Update the self-test header to its accurate count, 254. **Reproduced: exit 0, 254/254 passed.** The trailing comma prevents the regex from matching because it requires `)` immediately after the integer and optional whitespace. Numeric separators (`2_981`) and `assert declared_total() == 2981` also evade it. Thus a normally formatted typed-total assertion can restore the shared conflict line this change intends to prohibit.

Baseline foreground runs passed **253/253** and **209/209**, using the existing `node_modules` link. The extraction preserves the existing counting and mismatch logic, adds the derived diagnostic, and leaves all current mutation anchors resolvable: **2,981 entries, no loader refusals or anchor problems**. The +1/−1 check works.

Searches across `scripts/`, `.github/`, and `docs/` found historical examples and the intentional literal mutant, but no remaining executable reader of the old total. No file under `.claude/plans/` was accessed. All probe edits were restored; the worktree is clean.

**NOT CONVERGED**
