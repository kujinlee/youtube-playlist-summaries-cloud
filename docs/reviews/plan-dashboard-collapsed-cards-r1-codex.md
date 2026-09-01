<!-- codex-review: model=gpt-5.5 -->

**Blocking**

1. **Task 3’s tests crash before any case result because `_bare_tags` is defined later**
   
   Evidence: Task 3 says to add its block near `case("the entry id is rendered", …)` at `docs/superpowers/plans/2026-08-31-dashboard-collapsed-cards.md:291`, and uses `_bare_tags` at `:314-315`. `_bare_tags` is only introduced in Task 1’s later insertion after the URL case at `:45-56`, which is much later in `_self_test`.

   Command in temp copy after applying the plan’s Task 1/3/5 code and test blocks:
   ```text
   python3 scripts/gen-dashboard.py --self-test
   ...
   UnboundLocalError: cannot access local variable '_bare_tags' where it is not associated with a value
   ```
   Smallest fix: define `_bare_tags` before the Task 3 block, or do not share a helper across distant self-test regions.

2. **Task 3 emits a triangle for rows that intentionally have no fold**
   
   Evidence: Spec F8 requires no fold or triangle for a single-sentence no-tech entry at `docs/superpowers/specs/2026-08-31-dashboard-collapsed-cards-design.md:367`. The plan’s renderer builds `row` with an unconditional triangle at `docs/superpowers/plans/2026-08-31-dashboard-collapsed-cards.md:376-378`, then emits `row` directly when `body` is empty at `:379-380`.

   After bypassing the `_bare_tags` ordering crash only to keep executing:
   ```text
   [FAIL] F8: a single-sentence entry with no tech has NO fold and NO triangle
     got:  (False, True, True)
     want: (False, False, True)
   ```
   Smallest fix: compute the triangle from `body`, e.g. `tri = ... if body else ""`, then include `{tri}` in `row`.

3. **Task 1 changes `_prose` behavior but leaves an existing case red**
   
   Evidence: the existing case is `scripts/gen-dashboard.py:2202-2204`:
   ```python
   case("...but the headline is KEPT when it is the entire entry",
        "Ready for you now." in _prose("Ready for you now.", drop_headline=True), True)
   ```
   The plan explicitly says to keep every `_prose` case that does not mention a cap at `docs/superpowers/plans/2026-08-31-dashboard-collapsed-cards.md:164-167`, but Task 1’s new `_prose` pops unconditionally at `:125-148`.

   Executed result:
   ```text
   [FAIL] ...but the headline is KEPT when it is the entire entry
     got:  False
     want: True
   ```
   Smallest fix: replace this case in Task 1 with the new intended property, or explicitly delete it with the same written rationale as the no-terminator case.

**High**

4. **Task 6 mutation 3 crashes the suite instead of reddening its named expected case**
   
   Evidence: mutation 3’s expected case is F8b at `docs/superpowers/plans/2026-08-31-dashboard-collapsed-cards.md:592-594`. But the earlier F4 case uses raw `.index()` on the tech id at `:316-318`.

   Executed on a green review-only corrected temp tree:
   ```text
   ValueError: substring not found
   ...
   expect in output? False
   ```
   Smallest fix: make F4 non-raising by checking presence before comparing positions, or set the mutation’s `expect` to the earlier case it actually reddens after that case is made non-crashing.

5. **Task 6 mutation 5 has a non-unique `find` anchor**
   
   Evidence: Task 6 says `find` strings must match exactly once at `docs/superpowers/plans/2026-08-31-dashboard-collapsed-cards.md:584-585`. Mutation 5 uses `    return out` at `:598-600`.

   Executed count in the delivered Task 1-5 temp file:
   ```text
   return-out 7
   ```
   The harness refuses this before running the mutation. Smallest fix: anchor the whole `_first_sentence` tail, or include enough surrounding context to make the `return out` match unique.

6. **Task 2’s callerless grep is false as written**
   
   Evidence: Task 2 tells the implementer to run `grep -rn "orphaned_delimiters" scripts/ | grep -v "^scripts/page_markup.py"` and expects no output at `docs/superpowers/plans/2026-08-31-dashboard-collapsed-cards.md:243-246`.

   Executed after Task 1 deletion in the temp copy:
   ```text
   scripts/mutations/gen-dashboard.json:508: ...
   scripts/mutations/gen-dashboard.json:552: ...
   scripts/mutations/gen-dashboard.json:553: ...
   Binary file scripts/__pycache__/page_markup.cpython-314.pyc matches
   ```
   Smallest fix: restrict to Python source callers, e.g. `rg -n "orphaned_delimiters" scripts --glob '*.py' --glob '!page_markup.py'`, and separately inspect/delete mutation entries in Task 6.

**Medium**

7. **Spec F3 is not pinned**
   
   Evidence: Spec F3 requires the badge to be inside the collapsed row at `docs/superpowers/specs/2026-08-31-dashboard-collapsed-cards-design.md:362`. Task 3’s tests cover fold existence, F2, F4, F6, F5, F10, F9 at `docs/superpowers/plans/2026-08-31-dashboard-collapsed-cards.md:309-345`, but no case asserts badge markup between `<summary>` and `</summary>`.

   Smallest fix: add a needs-you or resolved fixture and assert the badge span appears inside the summary fragment.

8. **Spec F1/F7 are only indirectly covered by helper tests, not by rendered card HTML**
   
   Evidence: F1 requires the long sentence in the card fragment, tag-stripped, at `docs/superpowers/specs/2026-08-31-dashboard-collapsed-cards-design.md:360`; F7 requires no author-absent rendered-title ellipsis at `:366`. Task 1’s long-sentence cases call `_first_sentence`/`_inline` directly at `docs/superpowers/plans/2026-08-31-dashboard-collapsed-cards.md:56-65`, not `build()` and not `_fragment`.

   Smallest fix: build a page with a long markup-bearing first sentence, locate its article fragment, strip tags from the summary/title, and assert the tail is present and no literal `…` was generated.

**Low / Verified**

- Task 1’s `_prose` patch is syntactically valid. Imported the temp module and printed the resulting function body; it contains `head = _first_sentence(first)`, computes `rest`, and `paras.pop(0)` in the `else`.
- The Task 3 `_fragment` exact article opener works with the proposed renderer: `_slug("2026-08-31/1")` returns `2026-08-31-1`, and the emitted opener is exactly `<article class="entry" id="2026-08-31-1">`.
- Task 5 f-string braces are syntactically valid. The emitted CSS contains `content:"\25B8"` and `content:"\25BE"`; CSS escape decoding yields `▸` and `▾`.
- Existing cases checked: tech fold, every-details-has-id, no-duplicate-ids, seven same-date ordering, WCAG contrast, and `-plain` survived once the plan’s own ordering crash was bypassed. The old `:1862` title case is handled by Task 3 Step 4. The old no-terminator and truncation cases must be deleted. The remaining unhandled red existing case is `"...but the headline is KEPT when it is the entire entry"`.

NOT CONVERGED
