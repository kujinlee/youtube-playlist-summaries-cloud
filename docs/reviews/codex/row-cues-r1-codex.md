<!-- codex-review: model=gpt-6.1-sol -->

Found four issues:

1. **High — mutation harness refuses this PR.** [gen-backlog-page.json:802](scripts/mutations/gen-backlog-page.json:802) still anchors the previous `word_diff` tokenization line. Running `python3 scripts/check-plan-code.py --mutate . --only scripts/gen-backlog-page.py` reports `anchor NOT FOUND` and **NOT MEASURED**. Manifest length and pin both equal 73, but the new mutations have no verified kill verdict.

2. **Medium — literal `¶` loses text.** [gen-backlog-page.py:1193](scripts/gen-backlog-page.py:1193) replaces every occurrence, including user content. Executed:
   ```python
   word_diff("a ¶ b", "a ¶ b")
   # a <span class="brk"></span> b
   ```
   The unchanged literal disappears into a block break.

3. **Medium — diff breaks disagree with body layout.** [gen-backlog-page.py:1167](scripts/gen-backlog-page.py:1167) examines raw Markdown without the body’s glyph handling or nesting rules. Executed unchanged-input probes:
   - `word ⚠ **Fix:** value`: diff breaks mid-sentence; body does not.
   - `` `x. **Fix:** y` ``: diff breaks inside code; body does not.
   - An 81-character label: diff breaks; body refuses the overlong label.

   Insertion probes also place break spans inside `<ins>`. These remain valid HTML; I found no tag-splitting or visible markup leak.

4. **Medium — readable lists fail the wall-of-text guard.** [gen-backlog-page.py:1057](scripts/gen-backlog-page.py:1057) counts only outer `seg`/`prov` wrappers. An executed 882-character fixture with two valid, substantial `(a)`/`(b)` items renders as `<ol class="enum"><li>…`, yet `unlaid_rows` returns `[999]`. This wrongly refuses an already laid-out row, including the comment’s recommended remedy.

Other checks:

- **244/244 self-tests passed**; docstring says 244.
- Compared rendered visible text for all **20 edited rows**. No substantive meaning change found. Row 170 repairs broken code delimiters; row 504 relocates its amendment qualifier without changing its claim.
- Checked qualified references against their target subjects; no wrong namespace found. Backlog #56 contains the cited noisy-gate warning.
- Every real Status cell preserves visible text through `layout_body`.
- Confirmed the baseline one-block boundary measurements: **557 below / 639 above**. Current real rows return `unlaid_rows == []`.
- No tracked files modified; `.claude/plans/` was not read.

VERDICT: NOT CONVERGED
