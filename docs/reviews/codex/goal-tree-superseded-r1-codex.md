<!-- codex-review: model=gpt-6.1-sol -->

`python3 scripts/goal-tree.py --self-test`: **176/176 passed**. Four findings:

1. **High — explanatory text becomes the row’s fate.**  
   [scripts/goal-tree.py:571](scripts/goal-tree.py#L571) searches the entire Status cell for `WITHDRAWN`. The actual backlog #484 Status says `✅ FIXED … `WITHDRAWN` prints ✖ withdrawn …`; `row_fates` classifies **#484 itself as withdrawn**.  
   **Fix:** distinguish the current status declaration from quoted examples and history. Add #484’s actual Status cell as a negative regression case.

2. **High — dated SUPERSEDED declarations are missed.**  
   [scripts/goal-tree.py:568](scripts/goal-tree.py#L568) requires exactly `SUPERSEDED by backlog #N`.  
   **Failing input:** `✅ **SUPERSEDED 2026-11-02** — goal moved to backlog #481`, with a leaf naming that row and merged PR #20. Result: **✅ merged**. Existing rows #124, #125, #127 and #213 use dated SUPERSEDED declarations that likewise yield no fate.  
   **Fix:** recognize SUPERSEDED independently of its optional destination; extract a destination separately when available.

3. **High — empty or missing referenced rows silently permit ✅.**  
   [scripts/goal-tree.py:573](scripts/goal-tree.py#L573) treats zero parsed rows as a successful read; [scripts/goal-tree.py:276](scripts/goal-tree.py#L276) treats an absent row as having no fate.  
   **Failing input:** an empty `docs/backlog.md`, or a header-only table, with leaf `backlog #10, PR #20` and PR #20 merged. Result: **✅ merged**, with no parser problem. A truncated file omitting #10 has the same problem.  
   **Fix:** retain all parsed row numbers and make a leaf CANNOT RUN when any referenced row is absent.

4. **Medium — first-ref-only mutation survives every test.**  
   [scripts/goal-tree.py:276](scripts/goal-tree.py#L276): replacing `for n in rows` with `for n in rows[:1]` still passes **176/176**; verified in memory.  
   **Failing input:** leaf `backlog #10, backlog #11, PR #20`, #10 ordinary, #11 superseded, PR #20 merged. The mutant prints **✅ merged**.  
   **Fix:** add rendered multi-ref cases with only the second row superseded or withdrawn, reverse their order, and register the mutation.

The second table, `(was 🟠)` title prefixes, and escaped title pipes passed the combined probe. No repository files changed; `.claude/plans/` was not read.

**NOT CONVERGED**
