# Plan review — goal work threads — round 1 — Codex

**Subject:** `docs/superpowers/plans/2026-09-11-goal-work-threads.md` at `6debfde6`,
against spec v3 and `scripts/gen-goals-page.py`.
**Model:** gpt-5.5 via `scripts/codex-review.py`. Verdict file:
`docs/reviews/verdicts/r1-codex.verdict.json` (`gate_ran=true`).

Proof of subject supplied and correct — it quoted `def thread_prs(thread: dict, history) -> dict:`,
the first Python line of Task 4's step-3 block.

---

<!-- codex-review: model=gpt-5.5 -->

def thread_prs(thread: dict, history) -> dict:

**Blocking** docs/superpowers/plans/2026-09-11-goal-work-threads.md:513  
Task 5’s own test fixture does not match the renderer contract. `_broken` omits `"prs"`, but `render_threads()` immediately does `sum(1 for p in t["prs"] ...)` at plan line 551. The test intended to prove `pr_error=True` renders “could not be read”; instead it raises `KeyError: 'prs'`. Concrete failing scenario: implement Tasks 1-5 exactly, run `python3 scripts/gen-goals-page.py --self-test`, and the Task 5 unreadable-history case crashes before asserting anything.

**High** docs/superpowers/specs/2026-09-11-goal-backlog-pr-join-design.md:187  
The derivation does not prove what the spec claims. A PR is tagged `code` if it touched any non-document path, but `git log --follow -- <doc>` only proves the PR touched the document. It does not prove the non-doc file implemented that document’s thread. Concrete failing scenario: a housekeeping PR edits `2026-09-11-goal-backlog-pr-join-design.md` and also fixes `scripts/check-docs.py`; the thread renders that PR as `code`, making it look like the implementation PR even if the code change is unrelated. Rename history makes this worse: a rename or broad refactor PR pulled in by `--follow` can be tagged `code` because the same PR touched code elsewhere.

**High** docs/superpowers/plans/2026-09-11-goal-work-threads.md:579  
Plan 1 removes the Documents band before implementing the spec’s complete WORK model. The spec says WORK includes document-led threads plus direct work, with attribution method shown; Plan 1 only renders document-led threads and omits direct PRs entirely. Concrete failing scenario: a goal with direct backlog/code work but no spec/plan loses that work from the goal card, while the new “Work” header still looks like the activity view promised by the spec.

**Medium** docs/superpowers/plans/2026-09-11-goal-work-threads.md:541  
`render_threads()` only renders `t["spec"]` and `t["plan"]`, not the full `t["docs"]` list that Task 1 deliberately preserves for collisions. That contradicts the spec claim that every document appears inside its thread after the Documents band disappears. Concrete failing scenario: two specs share a stem; `pair_documents()` keeps the extra in `docs`, but the renderer shows only the first `spec`, so the duplicate document silently vanishes from `/goals`.

**Medium** docs/superpowers/plans/2026-09-11-goal-work-threads.md:518  
Several tests are absence-only and violate the plan’s own “Every case must be able to FAIL” rule. The clearest one is `"and it does NOT also claim there is no code PR"`: a stub returning `"history could not be read"` passes both unreadable-history assertions without proving PR rendering is correct. Similar weak cases include `prs_from_log([]) == []` at line 183 and `files_are_code([]) == False` at line 193.

**Low** docs/superpowers/plans/2026-09-11-goal-work-threads.md:641  
The quoted corpus counts are already stale against the current repo. I re-derived `187` docs under `docs/superpowers/`, `47` anchored, `140` excluded; the plan/spec still say `186`, `46`, `140`. The excluded count happens to remain the same, but the plan also hardcodes `excluded_count(186, 46)` as a test case, which no longer describes the live corpus.

**Low** docs/superpowers/specs/2026-09-11-goal-backlog-pr-join-design.md:377  
The 44/1/1 discrimination measurement is stale. Current derivation over anchored docs gives `44 code`, `1 doc-only`, `2 no-pr`, because the plan under review is also an anchored, unmerged document. This matters because the spec uses that margin to justify the tag’s usefulness.

NOT-CONVERGED
