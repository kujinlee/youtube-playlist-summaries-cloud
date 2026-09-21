# closing-table — round 8 — independent Claude half (fix verification)

**Status: IN PROGRESS.** Appended as confirmed; verdict at the end.

Subject: branch `fix/closing-table-r7-findings` (PR #327), on top of `master` `365f8d75`.
Task: refute the claimed fixes for r7's **F2** (`_INJECTED` widened), **F4** (self-test count
derived), **F5** (docstring corrected, banner-guard half filed as backlog #148).

Out of scope, already filed with r7's measurements: F1 (#145), F3+F7 (#149), F6 (#151), #148.

## Plan

1. Read the diff myself (`git diff master...fix/closing-table-r7-findings`), not the summary.
2. F2: hunt for a MISS introduced by folding — a person or a genuinely-new-instruction turn that
   now gets swallowed; re-run the r7 replay against the FIXED code for the new firing profile.
3. F2: check whether folding moves a real warning onto the wrong subject.
4. F4: attack the derivation — can `cases` still lie? Does the mutation die via its named case?
5. F5: read the corrected docstring against what the code now does.
6. Hold the 4 new self-test cases and 2 new mutations to the r7 standard: mutate the thing each
   case names and see whether the case actually dies.
7. Answer the struck `_META_IS_REALLY_A_MESSAGE` argument — concede or quote code.

## Findings

_(appended as confirmed)_
