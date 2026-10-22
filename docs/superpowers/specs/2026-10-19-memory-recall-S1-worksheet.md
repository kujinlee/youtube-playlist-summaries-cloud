# S1 worksheet — were these 75 recall fires worth interrupting for?

> **Anchor:** `review-decides-itself` — **ADR:** 0014
> **Goal:** A review loop decides its own next step — run, stop, or escalate — from recorded
> evidence rather than recall, and reaches the human only for decisions that are genuinely theirs.

**Status:** ⏳ **UNJUDGED INSTRUMENT.** Companion to
`2026-10-19-memory-recall-survey.md` (measurement **S1**). Committed unfilled on purpose: the
assembly is done so that judging is the only work left, and the judging is explicitly not mine
alone. ⚠ Derived from `.claude/recall-cache/*.json`, which is **not in git** — so this table is a
snapshot, and re-deriving it after the caches rotate will not reproduce it.

Every row is a REAL fire from `.claude/recall-cache/*.json`, 2026-09-30 → 2026-10-19.
Judge the last column only: **Y** worth interrupting, **N** not, **?** borderline.

⛔ The author of these memories should not be the sole judge — that is backlog row 191's own
recorded contamination (*"the labels are still the original author's"*). This sheet exists so the
judging is the only work left, not so it can be done alone.

**75 fires** · 31 distinct entries · 39 plans

## Fires per entry, most-fired first (the ranking S1 would be re-ranking)

- `running-codex` — **20**
- `feedback-agree-before-filing` — **9**
- `merge-ready-slice-merged-324` — **6**
- `a-filed-finding-s-proposed-fix-is-a-hypothesis` — **5**
- `review-convergence-is-not-the-final-tree-gate` — **3**
- `stopping-rule-defect-class-shift` — **3**
- `how-to-shape-a-message-to-me` — **3**
- `process-conventions` — **2**
- `backlog-191-semantic-recall-replicated` — **2**
- `concurrent-agents-go-wrong` — **1**
- `verify-the-other-copy-exists-before-deleting` — **1**
- `print-selection-cards-in-chat` — **1**
- `a-mutation-loses-its-binding` — **1**
- `push-from-a-worktree-needs-an-explicit-refspec` — **1**
- `a-bound-enumerates-what-is-witnessed` — **1**
- `a-convention-catches-what-you-read` — **1**
- `a-sever-substitutes-todays-value` — **1**
- `what-mutation-testing-proves` — **1**
- `a-title-is-scanned-not-read` — **1**
- `defined-not-derived-constants` — **1**
- `a-retreat-you-author-for-yourself-is-not-a-gate` — **1**
- `a-retrospective-number-needs-provenance` — **1**
- `a-case-can-pass-for-an-ambient-reason` — **1**
- `exercise-the-producer-at-two-distinct-inputs` — **1**
- `a-forced-choice-test-cannot-fail` — **1**
- `hardcode-only-what-fails-loudly` — **1**
- `a-gates-channel-can-be-weaker-than-the-gate` — **1**
- `a-document-inside-the-corpus-it-measures` — **1**
- `mutation-manifest-retarget-merged` — **1**
- `a-measurement-is-only-as-good-as-its-corpus` — **1**
- `a-shim-can-fail-in-both-directions` — **1**

---

## The worksheet

| # | date | plan · step | the step said | entry surfaced | worth it? |
|---|---|---|---|---|---|
| 1 | 2026-10-15 | `afk-r6-lows-r7-and-r18-ver` · 1 | apply the ten Lows, or record each with a reason | `a-filed-finding-s-proposed-fix-is-a-hypothesis` |  |
| 2 | 2026-10-15 | `afk-r6-lows-r7-and-r18-ver` · 2 | dispatch against the pushed tip | `running-codex` |  |
| 3 | 2026-10-15 | `afk-r6-lows-r7-and-r18-ver` · 5 | tick what landed, file what was discovered | `feedback-agree-before-filing` |  |
| 4 | 2026-10-14 | `afk-staleplan-and-two-fold` · 5 | apply the Claude half, then delete the demoted procedure | `a-filed-finding-s-proposed-fix-is-a-hypothesis` |  |
| 5 | 2026-10-14 | `afk-staleplan-and-two-fold` · 6 | apply the Claude half to the canonical-source redesign | `a-filed-finding-s-proposed-fix-is-a-hypothesis` |  |
| 6 | 2026-10-14 | `afk-staleplan-and-two-fold` · 7 | dispatch against 52f47910 | `running-codex` |  |
| 7 | 2026-10-14 | `afk-two-folds-and-r18` · 2 | process-281 r5 and plugins r6, concurrently | `concurrent-agents-go-wrong` |  |
| 8 | 2026-10-14 | `afk-two-folds-and-r18` · 3 | apply the Claude half, then delete the demoted procedure | `verify-the-other-copy-exists-before-deleting` |  |
| 9 | 2026-10-14 | `afk-two-folds-and-r18` · 4 | apply the Claude half to the canonical-source redesign | `a-filed-finding-s-proposed-fix-is-a-hypothesis` |  |
| 10 | 2026-10-14 | `afk-two-folds-and-r18` · 5 | dispatch against 52f47910 | `running-codex` |  |
| 11 | 2026-10-17 | `arch-review-marketplace` · 3 | backlog rows plus the roadmap in the same turn, and the review document | `feedback-agree-before-filing` |  |
| 12 | 2026-10-02 | `arch-review-wiring-class` · 4 | re-derive every load-bearing claim; findings to backlog AND roadmap in the same  | `feedback-agree-before-filing` |  |
| 13 | 2026-10-08 | `backlog-249-260-r4` · 3 | launch codex-review.py and read the capture file, not the ping | `running-codex` |  |
| 14 | 2026-10-08 | `backlog-249-260-r4` · 5 | relay check-merge-ready verbatim and report the clean-round count | `merge-ready-slice-merged-324` |  |
| 15 | 2026-10-08 | `backlog-249-260-r5` · 1 | launch codex-review.py against ea857e4a..9017b6c9 and read the capture | `running-codex` |  |
| 16 | 2026-10-08 | `backlog-249-260-r5` · 3 | launch it against the folded tip | `running-codex` |  |
| 17 | 2026-10-08 | `backlog-249-260-r5` · 5 | count consecutive clean rounds and relay check-merge-ready verbatim only if conv | `review-convergence-is-not-the-final-tree-gate` |  |
| 18 | 2026-10-08 | `backlog-249-260-r6` · 1 | launch it against 9017b6c9..aee7dd8e and read the capture | `running-codex` |  |
| 19 | 2026-10-08 | `backlog-249-260-r6` · 3 | launch against the folded tip, asking for the real CommonMark parser again | `running-codex` |  |
| 20 | 2026-10-08 | `backlog-249-260-r6` · 5 | count consecutive clean rounds; enumerate the tree gate THREE answers | `stopping-rule-defect-class-shift` |  |
| 21 | 2026-10-08 | `backlog-249-260-r7` · 1 | launch it against aee7dd8e..54625c75 and read the capture | `running-codex` |  |
| 22 | 2026-10-08 | `backlog-249-260-r7` · 3 | launch against the folded tip, asking again for the real parser | `running-codex` |  |
| 23 | 2026-10-08 | `backlog-249-260-r7` · 5 | count clean rounds and enumerate the tree gate three answers | `review-convergence-is-not-the-final-tree-gate` |  |
| 24 | 2026-10-08 | `backlog-249-260-r8` · 1 | launch it against 54625c75..3b49db97 and read the capture | `running-codex` |  |
| 25 | 2026-10-08 | `backlog-249-260-r8` · 3 | launch against the folded tip, pointing it at /tmp/cmvenv | `running-codex` |  |
| 26 | 2026-10-08 | `backlog-249-260` · 1 | mark the row resolved — PR #370 already shipped its fix | `feedback-agree-before-filing` |  |
| 27 | 2026-10-13 | `backlog-267-parser-swap` · 5 | alternate the halves; the gate clears only if the last round needs no guarded-co | `review-convergence-is-not-the-final-tree-gate` |  |
| 28 | 2026-10-17 | `candidate-1-page-cites` · 1 | settling with the owner which passages of the walkthrough are RULES (must cite)  | `print-selection-cards-in-chat` |  |
| 29 | 2026-10-17 | `candidate-1-page-cites` · 3 | removing the token-registry half, keeping the derived-figures half, and pruning  | `a-mutation-loses-its-binding` |  |
| 30 | 2026-10-17 | `candidate-1-page-cites` · 6 | committing to marketplace-inventory, force-with-lease push from the worktree, th | `push-from-a-worktree-needs-an-explicit-refspec` |  |
| 31 | 2026-10-19 | `chrome-bar-converge` · 1 | declare the bound (generator- or skill-authored markup) at the enforcement site  | `a-bound-enumerates-what-is-witnessed` |  |
| 32 | 2026-10-19 | `chrome-bar-converge` · 4 | dispatch the Claude and Codex halves, alternating per round topology | `running-codex` |  |
| 33 | 2026-10-19 | `chrome-bar-converge` · 5 | apply r6 findings, or write the thrashing verdict with per-finding evidence | `stopping-rule-defect-class-shift` |  |
| 34 | 2026-10-19 | `chrome-bar-converge` · 6 | record the entry, open the PR for CI signal, notify the owner | `merge-ready-slice-merged-324` |  |
| 35 | 2026-10-18 | `chrome-r4-ship` · 2 | fix what it finds, with a falsifier per fix BEFORE the fix is called done | `a-filed-finding-s-proposed-fix-is-a-hypothesis` |  |
| 36 | 2026-10-18 | `chrome-r4-ship` · 4 | state the verdict plainly; NOT CONVERGED if it is | `stopping-rule-defect-class-shift` |  |
| 37 | 2026-10-02 | `close-201-202` · 3 | full local gate set, then branch+PR batched | `merge-ready-slice-merged-324` |  |
| 38 | 2026-10-17 | `corpus-pass-295` · 4 | judging whether the reader is worth shipping as a check or is a one-off sweep | `a-convention-catches-what-you-read` |  |
| 39 | 2026-09-30 | `correct-arch-review-verdic` · 2 | its row states the refuted framing as the primary verdict | `feedback-agree-before-filing` |  |
| 40 | 2026-09-30 | `correct-arch-review-verdic` · 5 | dashboard entry, gates, commit, push | `process-conventions` |  |
| 41 | 2026-10-02 | `d1-ratchet-main-world` · 3 | control green, then sever violations=assess(...) and require NAMED red, then aft | `a-sever-substitutes-todays-value` |  |
| 42 | 2026-10-03 | `d2-main-drivable` · 5 | backlog row for entry-point-vs-main, dashboard entry, roadmap tick | `feedback-agree-before-filing` |  |
| 43 | 2026-10-16 | `doc-citations-redesign` · 7 | all CI document guards, then the dashboard entry, then hand you the PR decision | `merge-ready-slice-merged-324` |  |
| 44 | 2026-10-16 | `finish-291-branch` · 2 | gh pr create --body-file, stating NOT CONVERGED with the round record | `merge-ready-slice-merged-324` |  |
| 45 | 2026-10-16 | `finish-291-branch` · 4 | report the PR, the CI state, and what is still open | `how-to-shape-a-message-to-me` |  |
| 46 | 2026-10-07 | `finish-364` · 2 | dispatching Codex then the Claude half against c0200f60 under the freeze | `running-codex` |  |
| 47 | 2026-10-07 | `finish-364` · 3 | folding Blocking/High in the deliverable only, filing the rest as backlog rows | `feedback-agree-before-filing` |  |
| 48 | 2026-10-07 | `finish-364` · 6 | killed in step 5's world -> close #240 and #241, the un-pin is earned; SURVIVED  | `what-mutation-testing-proves` |  |
| 49 | 2026-10-06 | `finish-365` · 4 | dispatching the Claude half as a subagent and Codex with --model gpt-5.5 | `running-codex` |  |
| 50 | 2026-10-06 | `finish-365` · 5 | folding Blocking/High in the deliverable only, filing everything else as backlog | `feedback-agree-before-filing` |  |
| 51 | 2026-10-06 | `finish-365` · 6 | check-merge-ready.py --pr 365, a dashboard entry, and a notification | `a-title-is-scanned-not-read` |  |
| 52 | 2026-10-17 | `fold-q3-q4-then-r3` · 6 | Codex half first, then fold, then the Claude half | `running-codex` |  |
| 53 | 2026-10-17 | `fold-r3-codex` · 5 | PAGE_HTML is named by zero claims; derive it from PAGE, and recompose the drifte | `defined-not-derived-constants` |  |
| 54 | 2026-10-17 | `fold-r3-mediums` · 7 | dispatch against the folded tree, then fold, then the Claude half | `running-codex` |  |
| 55 | 2026-10-17 | `fold-r4-claude` · 4 | corpus pass vs round 5, against the pre-committed condition in the r4 round docu | `a-retreat-you-author-for-yourself-is-not-a-gate` |  |
| 56 | 2026-10-16 | `fold-r5-citations` · 4 | declared 64 against 67 actual, and the retirement figures were wrong by two both | `a-retrospective-number-needs-provenance` |  |
| 57 | 2026-10-16 | `fold-r5-codex` · 3 | deleting a legacy UTF-16 document hits the pre-images NUL refusal before reachin | `a-case-can-pass-for-an-ambient-reason` |  |
| 58 | 2026-10-16 | `fold-r5-codex` · 4 | a reader returning None for everything still satisfies the containment witness,  | `exercise-the-producer-at-two-distinct-inputs` |  |
| 59 | 2026-09-30 | `fold-recall-llm-r1` · 5 | dispatch one half against the fixes, then the other | `running-codex` |  |
| 60 | 2026-09-30 | `llm-recall-matcher` · 2 | scripts/recall-llm.py — one call per PLAN matching every step at arm time, cache | `backlog-191-semantic-recall-replicated` |  |
| 61 | 2026-09-30 | `llm-recall-matcher` · 3 | the arm-time hook plus a self-test and mutation entries | `backlog-191-semantic-recall-replicated` |  |
| 62 | 2026-09-30 | `llm-recall-matcher` · 4 | pad the trigger corpus to 300/600/1000 and re-run the 80-item probe | `a-forced-choice-test-cannot-fail` |  |
| 63 | 2026-10-17 | `marketplace-r3` · 1 | run codex-review.py against the r2-Claude fold and the seven owner decisions | `running-codex` |  |
| 64 | 2026-10-17 | `marketplace-r3` · 6 | all document guards plus check-claim-propagation, then commit on the branch | `process-conventions` |  |
| 65 | 2026-10-15 | `namespace-token-guard` · 2 | fix the token forms and the rule-bearing file set, both derived rather than chos | `hardcode-only-what-fails-loudly` |  |
| 66 | 2026-10-15 | `namespace-token-guard` · 3 | refuse a newly-added bare reference in rule-bearing files, cases for every shape | `a-gates-channel-can-be-weaker-than-the-gate` |  |
| 67 | 2026-10-15 | `namespace-token-guard` · 4 | amend process-checklists §Qualify-every-number in place, with the new measuremen | `a-document-inside-the-corpus-it-measures` |  |
| 68 | 2026-10-01 | `recall-llm-r9` · 1 | running check-plan-code.py --mutate . (1177 expected) | `mutation-manifest-retarget-merged` |  |
| 69 | 2026-10-01 | `recall-llm-r9` · 3 | codex-review.py --review-id recall-llm-r9-codex | `running-codex` |  |
| 70 | 2026-10-02 | `ship-recall-fold` · 5 | declare the 3 open Highs, the NO-REVIEW reason for D1, the arch review | `merge-ready-slice-merged-324` |  |
| 71 | 2026-10-14 | `three-review-rounds` · 4 | relay verdicts, counts and what is NOT converged | `how-to-shape-a-message-to-me` |  |
| 72 | 2026-10-02 | `unify-explainer-style` · 1 | rewrite the row: no shared stylesheet, 6.47MB across 62 pages, backlog page is t | `feedback-agree-before-filing` |  |
| 73 | 2026-10-02 | `unify-explainer-style` · 3 | run the harness on the corpus as it stands and commit the numbers | `a-measurement-is-only-as-good-as-its-corpus` |  |
| 74 | 2026-10-02 | `unify-explainer-style` · 4 | append the backlog page's :root token block, light and dark, at send time | `a-shim-can-fail-in-both-directions` |  |
| 75 | 2026-09-30 | `wrap-for-arch-review` · 2 | what a person returning would need to know, plus the decision now waiting | `how-to-shape-a-message-to-me` |  |

