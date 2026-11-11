<!-- codex-review: model=gpt-6.1-sol -->

Both baseline suites pass: **30/30** generator cases and **68/68** begin-plan cases. The following defects were reproduced using temporary data; no repository files were modified.

1. **Blocking — cycle handling leaves cycles intact and rendering hangs.**  
   `scripts/gen-work-lines.py:106–110`, `:121–128`

   Input: a plan containing `<!-- parent: a -->` whose slug is `a`. The fallback adds it to `roots` but never removes its self-referencing child. `render()` then enters `line_state()`, which has no visited set.

   Executed result:
   ```text
   self cycle render: TIMEOUT after 1 second
   ```

   This is reachable through ordinary re-arming. In a temporary directory, calling `cmd_begin("a", ...)` twice returned:
   ```text
   rearm rc= 0 self-parent= True old retained= False
   ```

   The cycle tests only inspect root slugs, so their “terminates” claims never exercise either traversal used by the page.

   **Fix:** reject self-parent creation; detect and explicitly break/report cyclic edges during forest construction. Test complete rendering of self-cycles and two-node cycles, asserting each plan appears once.

2. **Major — reducing sentinel paths to stems can silently attach an unrelated parent.**  
   `scripts/begin-plan.py:358–359`

   Input: sentinel `plan: elsewhere/real.md`, with an unrelated `.claude/plans/real.md` present. The code never validates the referenced file or its location; `Path(prev).stem` turns both paths into `real`.

   Executed result:
   ```text
   wrong-path parent= 'real'
   wrong-path attached children= [('real', ['kid', 'wrong-path'])]
   ```

   The page presents a normal parent-child relationship without warning. A deleted target also gets recorded:
   ```text
   missing parent= 'gone'
   ```
   That case eventually receives an orphan warning, but the wrong-path collision silently invents lineage.

   **Fix:** validate the sentinel’s actual resolved target before deriving a parent identifier. Preserve or explicitly report an invalid reference instead of matching another file by basename.

3. **Major — the narrowed exception handler still hides implementation failures.**  
   `scripts/begin-plan.py:356–361`

   The `try` covers module loading, parsing, dictionary access, and path construction. Catching `AttributeError`, `KeyError`, and `ValueError` across that whole block can convert programming errors into absent lineage.

   I injected `AttributeError("implementation typo")` into `_load_plan_progress()` in memory, then began a child with a sentinel present:
   ```text
   AttributeError injected into loader: rc= 0 parent marker= False
   ```

   The command succeeded and overwrote the sentinel, losing the link.

   **Fix:** move loading and parsing outside recovery intended for I/O failures. Handle expected malformed input explicitly, and report any deliberate lineage omission.

4. **Major — multiline `--serving` values are accepted but silently disappear from the page.**  
   `scripts/begin-plan.py:191` (marker emission); `scripts/gen-work-lines.py:50` (`SERVING` regex)

   Passing a human objective containing a newline writes a multiline comment. The reader requires a single-line match.

   Executed writer-to-reader round trip:
   ```text
   serving roundtrip 'first line\nsecond line' -> None
   ```

   The original objective—the feature’s central context—is therefore absent without any warning.

   **Fix:** either reject multiline objectives before writing anything or use an encoding/parser that preserves them. Add a writer-to-reader round-trip test.

5. **Minor — newly created plans are falsely described as predating the feature.**  
   `scripts/gen-work-lines.py:169–170`

   Input: a newly generated plan with no armed predecessor and no `--serving`. Rendering it produces:
   ```html
   <p class="serving absent">no parent recorded, and no stated objective — this plan predates the work-line fields</p>
   ```

   Missing metadata does not establish the plan’s age. The same misleading explanation can follow lost metadata.

   **Fix:** say only “no parent recorded, and no stated objective” unless a reliable version field establishes more.

6. **Minor — the count test does not test the count it names.**  
   `scripts/gen-work-lines.py:376–377`

   The case named “the count of lines that still owe something is stated” checks only whether `"still owe something"` occurs.

   In a temporary script copy, I replaced `{len(open_lines)}` in the rendered count with `{999}`:
   ```text
   mutant count rc= 0 30/30 self-test cases passed
   ```

   **Fix:** assert the actual rendered number using fixtures with different open-line counts.

VERDICT: NOT CONVERGED
