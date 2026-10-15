---
name: parallel-branches-append-to-one-log
description: "FIRES-WHEN: opening a second branch that touches dashboard-entries.md or the roadmap — Parallel branches each appending to docs/dashboard-entries.md + the roadmap conflict pairwise; `git merge-tree` reported ZERO conflicts when a real merge found three; and 'keep both' FUSES two entries into one when they share a header line"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 0beebe91-3b3b-4a67-97b9-3f6df9869680
  modified: 2026-10-07T19:35:00.000Z
---

Three branches cut from master on the same day (PRs #191, #192, #193 on 2026-09-01) each appended a
block to the END of `docs/dashboard-entries.md` and inserted a section at the SAME roadmap anchor.
The first merges clean; **every subsequent one conflicts** — measured: #192 conflicted on
`ci.yml` + both docs, #193 on both docs.

The process *requires* each branch to add an entry (`check-dashboard-entry.py` refuses otherwise) and
to update the roadmap in the same turn. So the conflict is structural, not carelessness: **the
per-branch documentation rules guarantee a collision whenever branches run in parallel.**

⚠ **`git merge-tree <base> <a> <b>` reported 0 conflict hunks. A real merge found 3.** The legacy
form emits a diff, not conflict markers in the shape I grepped for — a false negative that would have
let me tell the user "they merge cleanly". **Assert by performing:** `git worktree add --detach` a
throwaway tree, `git merge` each branch in order, read `git diff --name-only --diff-filter=U`, then
`git worktree remove --force`. The repo is never touched.

**Why:** handing an AFK user three PRs that conflict is friction they did not create, and a
mis-resolution silently drops an entry or a CI step.

⛔ **"KEEP BOTH" IS NOT ENOUGH WHEN THE TWO BLOCKS SHARE A HEADER LINE** — measured 2026-09-09,
merging master (PR #273) into `mutation-faithfulness-r1` (PR #272). Both sides appended an entry
whose first line was the byte-identical `## 2026-09-09 [needs-you]`. Git **auto-merged the shared
header** and raised conflict markers around the two BODIES only. So the literal keep-both — delete
the three markers, keep everything between — produces **ONE entry whose body is two entries
concatenated**. No parse error, and the page renders one card silently claiming two
unrelated pieces of work were the same thing. The header must be **duplicated by hand**.

⟳ **CORRECTED 2026-10-07: "no gate failure" was WRONG.** `check-dashboard-entry.py` returned
**rc=1** on exactly this fusion (PR #370), because it reads the **committed diff** and the fused
block contains **no `+## ` line at all** — the branch's only new header was the one git ate as
context. ⚠ The gate therefore catches the fusion **only when the fused entry is the branch's only
entry**. That was true here and is not true in general, so do not rely on it: run the grep falsifier.

**Falsifier that catches it in one line:** `grep -c '^## <date>'` before and after. Fusion shows up
as a count that did not rise. Here: 7 before, 8 after resolving correctly.

⚠ **Entry ids are POSITIONAL** (`YYYY-MM-DD/N`, N counting that date's entries in file order), so
resolution ORDER assigns ids. Put the side already ON MASTER first — its id is published and may be
referenced; the branch's has never been seen. Check `grep -n 'resolved: <date>'` before choosing:
a `[resolved:]` pointing into the range you are about to renumber silently rebinds to a different item.

**How to apply:** before opening a SECOND parallel PR, decide the shape up front — either stack the
branches (`gh pr edit <n> --base <parent-branch>`, so each diff stays honest and GitHub retargets on
merge) or batch the work into one PR. If they are already open and conflicting, say so with the
merge ORDER and the fact that every hunk is **pure addition, zero deletions**, so the resolution is
"keep both" — verify that claim with `git diff --numstat`, do not assume it. Do not force-push a
rewrite of the user's open PRs unattended; offer it.

Related: [[a-check-result-is-not-the-claim]] — the reason NOT to just rebase one
branch onto another without retargeting its PR base is that the diff would then silently carry the
other PR. [[quote-the-code-dont-characterise-it]]

## ⭐⭐ IT RECURRED 2026-10-07, AND THIS FILE ALREADY SAID SO — the enforcement gap, on me

Merging #369, then #368, then rebasing #370 — all three appending to `docs/dashboard-entries.md`.
I wrote an auto-resolver doing keep-both over any conflict block in the two append-only logs, ran it
across four rebase steps, and it **fused #370's entry onto #368's**: the precise failure documented
above, with its falsifier, in this file.

⛔ **Why the note did not fire: the `MEMORY.md` index row carried the cheap half and dropped the
lethal one.** It read *"3 same-day PRs: #1 clean, rest CONFLICT"* — true, and the part that costs
nothing. The part that silently corrupts the log lived only in this file, which is not in context.
**A hook naming the irritation instead of the damage will not prevent the damage.**

⛔ **An automated keep-both resolver must carry the falsifier INSIDE it**, not beside it: count
`^## ` before and after and REFUSE unless the count rose by the number of blocks resolved. A
resolver that cannot detect fusion produces the defect faster than hand-editing would.
