<!-- codex-review: model=gpt-6.1-sol -->

**NOT CONVERGED.** Two of #297’s supposedly resolved drifts remain in both pages. The coordinator’s correction in §D is false.

No Blocking findings. **2 High, 2 Medium, 1 Low.**

1. **High — C4 is still graded against D9 in both pages.**

   Files: `docs/explainers/2026-10-15-brief-marketplace-inventory-walkthrough.fragment.html:487` and served `.html:564`; incorrect closure at `docs/backlog.md:287`.

   The criteria table still says C4 is “graded against **D9**’s support bar.” Later, the same pages say “**D9 does not grade C4**” at fragment `:1024` / served `:1101`. The spec explicitly rejects that grading predicate at `:298` and `:624`.

   Executed:

   ```text
   rg -n 'graded against.*D9|D9 does not grade' docs/explainers/2026-10-15-brief-marketplace-inventory-walkthrough*
   ```

   Both assertions occur in **each** page. The architecture review’s original finding was correct: observing the corrected passage did not establish that the earlier assertion was gone. Rewording the spec heading leaves the page contradiction intact.

2. **High — D5’s retired falsifier remains; the fix reached a different passage.**

   Files: fragment `:584`, served page `:661`; new incorrect reference at fragment `:721` / served `:798`.

   Both pages still announce “**Its falsifier, stated now**” and say the scheme fails if readers act as though `argued` means `measured`. The spec withdraws precisely that unobservable condition at `:521` and supplies the checkable visual-unit/scenario conditions.

   Executed:

   ```text
   rg -n 'read and|acted on|same visual unit' docs/explainers/2026-10-15-brief-marketplace-inventory-walkthrough*
   ```

   Output includes the retired assertion at fragment `:584–585` and served `:661–662`; neither page contains `same visual unit`.

   The correction at fragment `:717–721` acknowledges that the reader-based condition cannot fire, contradicting the earlier assertion. Its replacement citation also points to **§4c**, which contains D6/harvest. D5’s checkable rule is in **§4b**.

3. **Medium — surviving carrier behaviors remain unpinned by the 41 cases.**

   File: `scripts/check-claim-propagation.py:167`, `:184`, `:197`.

   I applied three independent mutations to temporary copies and ran each suite:

   | Mutation | Result | Observable changed behavior |
   |---|---|---|
   | Accumulate `data` instead of `data.strip()` | `rc=0`, `41/41` | Padded carrier text retains surrounding spaces |
   | Reduce `VOID` to `img` | `rc=0`, `41/41` | `<br data-derived="k">771` wrongly captures `771` |
   | Clear the stack on an unmatched closing tag | `rc=0`, `41/41` | `<p data-derived="k">1</unmatched>2</p>` yields `1`, losing `2` |

   Command: `python3 /tmp/r5-probes.py`.

   These are coverage gaps, not demonstrated regressions in the current implementation. The existing void mutation proves the `img` witness; it does not pin the surviving void vocabulary.

4. **Medium — the new memory lesson repeats the “unmutatable” inference already withdrawn in the guard.**

   File: `docs/memory/a-harness-cannot-read-a-cause-from-a-childs-text.md:54–58`.

   It calls the derived-page path mutation “unmutatable” and says writing a case would address “a defect that was not there.”

   I tested the **`fcd1a205` version itself**, replacing the derived-page expansion with the direct page set:

   ```text
   wanted |= {d["page"] for d in DERIVED}
   ```

   Running the temporary guard with `--self-test` produced:

   ```text
   rc=1 traceback=False
   [FAIL] audit: an absent COMPOSED page reached only through DERIVED is CannotRun:
          got 'FileNotFoundError' want 'CannotRun'
   1 of 96 self-test case(s) FAILED
   ```

   The lesson promotes one crashing probe into an impossibility claim. A non-crashing, attributed witness already existed when this memory commit was written.

5. **Low — the ratchet’s retirement accounting is false.**

   File: `scripts/check-plan-code.py:634`; repeated in `docs/roadmap-to-launch.md:2401`.

   Comparing the two manifests by mutation identity gives **17 retired entries**, not 19. Four retained entries were retargeted. The actual arithmetic is `32 − 17 = 15`.

   Command: `python3 /tmp/r5-canon-retire.py`.

   ```text
   RETIRED 17
   ```

   I inspected all 17 removed anchors. I did **not** establish an unjustified numerical fall: their prose-matching subjects were removed. The explanation of that fall needs correction.

Executed coverage and limits:

| Claim | Result |
|---|---|
| **A1 — HTML widening** | Re-derived through `_walked_textfiles`: **2,023 files, 84 HTML**; zero HTML hits for every token of either pre-existing canon. |
| **A2 — new tokens** | All six occur in the spec; no unexpected non-exempt carrier outside the actual declared sites and registry. The registry declares **four** citing sites, despite comments saying two. |
| **A3 — mutations** | **15 killed, 15 attributed, zero survivors**, with green before/after controls and complete `HARNESS_TREE` staging. Full manifest validation retained: 1,472 entries, no load/count/home-escape errors. I did **not** execute all 1,472 mutations. |
| **A4 — counts** | Guard: **41/41**. Harness: **178/178**. Manifest actual and declared sum: **1,472**. Count checker: **54 script declarations verified by execution**. |
| **A5 / D — three drifts** | **False:** C4/D9 and D5 remain. D8’s “all three” / “any of the three” correction is present in both pages. |
| **B6–7 — surviving behavior / rename** | Ran the additional surviving-branch mutations above and **20,000 differential parser inputs** against `_Blocks`: **zero derived-value or carrier-count differences**. No whitespace/void-separator rename regression found. |
| **B8 — canon bound** | Executed: control `[]`; contradicting citing page `[]`; new unciting token carrier refused. The prospective-only bound is accurate and plainly stated in ADR-0015. |
| **B9 — retirements** | Compared manifests and inspected all **17 actual removals**. |
| **B10 / C — documents** | Inspected the named live documents and four earlier commits. Found the uncorrected memory claim above; no additional filename-contract defect in the named documents. |

**Thrashing or prose floor?** Continued thrashing, with additional ground uncovered. The two High findings are known contradictions left standing by the architecture implementation’s own corrective pass, now accompanied by false closure claims. The retirement count is another error introduced by that pass. The coverage probes are additional ground; the memory defect comes from an earlier unreviewed commit. These are testable defects, not a prose floor.
