# Phase 6 architecture review — PR #602 (`decision-tags`) — `explainer-delivery.md` §3a

- **Armed by:** THRASHING. Rounds 2 and 3 each carried findings caused by the previous round's fold, in one component (`explainer-delivery-3a`).
- **Subject:** §3a of `.agents/skills/shared/explainer-delivery.md` against `_DecisionScan` / `render_decisions` in `scripts/brief-compose.py`.
- **Measured against:** `04fb9828`. The worktree moved to `be0a7a79` while I worked (the round 4 record: Codex, no findings, CONVERGED). `git diff 04fb9828..be0a7a79` touches neither §3a nor the script, so every measurement below holds for both.
- **Mode:** read-only. Nothing was written inside the repository (`git status --short` was empty before and after every run; Python ran with `PYTHONDONTWRITEBYTECODE=1`). Fragments, outputs and the harness (`run.sh`) are beside this file. Python 3.14.4.
- **Read first:** the three coordinator records, all five review halves, `CONTEXT.md` (*Canon*, *Decision symbol*), ADR-0015, `docs/reviews/architecture-review-2026-11-12-603-decision-scan.md`, backlog rows 603 / 615 / 616 / 620. No ADR is re-litigated.
- **Marks:** **[M]** = I measured it in this session. **[M-prior]** = measured in the 2026-11-12 review, in real Chromium, and cited. **[I]** = inferred.

## Verdict

**The round 3 fold is the redesign. No further mechanism is owed, and nothing more should change in this PR.**

- **The mechanism.** §3a restated a rule set whose only definition is an ordered `if/elif` chain in code. Any restatement of it is a list, and a list can always be found one member short. Round 1 answered "the list is short" by lengthening the list; round 2 swapped a list of rules for a list of constants. Both were re-wordings of a copy.
- **The fix that ends it** is deleting the copy, and the round 3 fold did that. It is ADR-0015's remedy (*"DELETE the recital and keep the citation"*) applied to a code canon.
- **Why the deletion loses nothing:** every refusal is loud and explains itself. 9 of 9 refused fragments returned rc=1 with the element, the line, the reason and what to change **[M]**. The list in the doc was never needed ahead of time.
- **Not owed:** a doc generated from the code, or a drift check. Both are rejected below with reasons. A drift check that requires §3a to carry the code's set would make the copy mandatory and forbid the round 3 fold.
- **Two small residuals of the same class remain** — a two-function pointer and a three-example bound. Neither is false; both are **FILED**, to be closed by the same edit that backlog row 620 (the scanner's allow-list redesign) already forces on this paragraph.

## 1. The one mechanism behind the thrash

**A prose enumeration of a code set is a completeness claim, and nothing but a reviewer reading the code can test it.**

| Round | What §3a held | What the reviewer found missing | Fold |
|---|---|---|---|
| r1 | a short list of refused cases, stated as a guarantee | table/form/void refusals, open `<details>`, the id collision | **lengthened the list** |
| r2 | a longer list of rules | `datalist`, first-`<summary>`-only, `name` | **replaced it with a list of six symbols** |
| r3 | a list of symbols | `_DECISION_REFUSE_FOREIGN` | **deleted the list; points at two functions** |
| r4 | a pointer | nothing (Codex, CONVERGED) | — |

Three things made the copy impossible to keep right, each checked:

1. **The rule set is not data.** It is five constants, one message constant, one message function and an ordered `if/elif` plus an ancestor loop (`brief-compose.py:1262-1283`). There is no single object a doc could mirror **[M]** (read).
2. **Every finding's own "Fix:" was additive.** Round 1's five fixes each said *add* or *list*; round 2's findings named three more members. A finding's proposed fix is a hypothesis, and here it was the re-wording itself. Only the round 3 reviewer proposed removing the list.
3. **No guard was in the loop.** `check-explainer-delivery.py` and `check-canonical-source.py` are both rc=0 on the head, with the list deleted **[M]**, and the review halves record `check-explainer-delivery.py` green in rounds 1–3 with the list present (`check-canonical-source.py` with the list present: not recorded, **[I]** — it holds no canon for this script). So the guards are indifferent to the list. See §6.

**Thrashing or prose floor?** Thrashing, by the definition: 3 of 3 round-2 findings and 1 of 1 round-3 findings are `fix_induced: true` in one component. It is not a prose floor, because the findings were not about wording — each named a concrete input the code refuses and the doc did not predict.

## 2. Can a redesign remove the class? Is the round 3 fold that redesign?

**Yes, and yes — for the refusal list.** The class is "§3a enumerates what the scanner refuses". With no enumeration, there is no member to omit.

### The four shapes, weighed

| Shape | Verdict | Reason |
|---|---|---|
| **No doc copy; cite the code** (the round 3 fold) | **KEEP** | Deletion is the only move that removes the class. ADR-0015 already decided it for spec ↔ page. |
| Doc generated from the code | **REJECT** | The rules are an `if/elif` chain with inline f-strings, not a table; generating needs the scanner restructured first. Backlog row 620 replaces that scanner (deny-list → allow-list). Building a generator over a model scheduled for removal is waste. And the reader already gets the rule at the moment it applies, from the refusal. |
| A drift check that reads the code's own set and requires §3a to match | **REJECT** | It makes the copy mandatory. Deleting the list — the correct fix — would turn it red. This is the repository's recorded lesson (§6). |
| A canon entry in `check-canonical-source.py` (tokens = the `_DECISION_REFUSE_*` names) | **REJECT** | That guard passes any site that cites the canon, even one that restates and contradicts it (ADR-0015, *Consequences*). The round 2 text named `brief-compose.py`, so it would have been green over the drifted list **[I]** — not run, read from `check-canonical-source.py`'s own header. |

### Attempts to refute "no copy is enough"

**A. "A reader needs the list before composing."** Refuted only if a refusal is silent, vague, or expensive.

| Fragment body | rc | Message carries |
|---|---|---|
| `<table><tr data-decision>…` | 1 | element, line, "ON a `<tr>`", "Move the mark to a visible element" |
| `<p hidden data-decision>` | 1 | "its `<p>` carries hidden" |
| `<details open><summary>s</summary><p data-decision>` | 1 | "move the mark outside the `<details>`, or onto its `<summary>`" |
| `<svg><text data-decision>` | 1 | "move the mark outside the `<svg>`" |
| `<datalist><p data-decision>` | 1 | "inside a `<datalist>`, which is not rendered" |
| second `<summary data-decision>` | 1 | the `<details>` message |
| `<a name="ex-decision-1">` + a mark | 1 | "already uses id/name ex-decision-1 … Rename it" |
| `<div inert><p data-decision>` | 1 | "inside a `<div>` that is hidden or inert" |
| `<template><p data-decision>` | 1 | "inside a `<template>`, which is not rendered" |

9 of 9 refused, no page written, each message names the element and the change **[M]**. The set is the seven members the rounds found missing plus two controls; it is not every branch. One compose takes 0.28 s **[M]**. **Not refuted.** One weak spot: the `<tr>` message says "a visible element", not "mark the `<td>`" — a message-quality point for the code, not the doc.

**B. "The pointer is still a list, so the class survives at size two."** Partly holds. §3a says the rules are *"the refusals raised by `_DecisionScan.handle_starttag` and `render_decisions`"*.

- `handle_starttag` raises nothing; it computes `refusal` (`:1262-1283`) **[M]**.
- A third decision `CANNOT RUN` is raised by `_decision_offset` (`:1319`), called only from `render_decisions` (`:1351`) **[M]**. I could not reach it from a fragment (uppercase tag, a tag split over two lines: both compose) **[M]** — two attempts, so "unreachable" is **[I]**.
- The ancestor stack that decides a refusal is also shaped by `_close_p` and `handle_endtag` **[M]** (read).
- Every decision refusal exits through **one** function, `render_decisions` **[M]** (the three `raise SystemExit` sites at `:1319`, `:1338`, `:1343`; `:1319` is reached only via `:1351`).

So a pointer of size one exists (`render_decisions`), and it cannot be a member short. The coordinator's claim *"this pointer does not go stale when a constant is added"* holds for constants **[I]**; it does not hold if a refusal moves to another method, which backlog row 620 will do (its row names `_DecisionScan` and `render_decisions` as its targets **[M]**). **Residual R1 — filed.**

**C. "The bound is the same class on the negative side."** Holds. §3a's bound reads *"it reads MARKUP, not CSS"* and gives three examples of what is counted. A reader infers that hiding done in markup is caught. It is not:

| Fragment body | Composer | Browser |
|---|---|---|
| `<dialog><p data-decision>` | rc=0, counted **[M]** | not visible **[M-prior]** |
| `<div popover><p data-decision>` | rc=0, counted **[M]** | not visible **[M-prior]** |
| `<canvas>` / `<video>` / `<audio>` around a mark | rc=0, counted **[M]** | not visible **[M-prior]** |
| `<object data="x.png">` around a mark | rc=0, counted **[M]** | **[I]** (the prior review's `<object>` also carried `type=image/png`) |
| `<progress><span data-decision>` | rc=0, counted **[M]** | not visible **[M-prior]** |
| `<ruby>x<rp data-decision>` | rc=0, counted **[M]** | **[I]** (the prior review measured a `<span>` inside `<rp>`, not a mark on it) |
| `<div style="display:none">…` (the doc's own example) | rc=0, counted **[M]** | not visible **[M-prior]** |

I did not render these; the browser column is the 2026-11-12 review's Chromium oracle (finding P6-1: twelve well-formed shapes, none using CSS written by the author). The sentence is **not false** — it says what the scanner reads, and the paragraph opens with *"a mark it CAN TELL"*. But it characterises the scanner's blind side with a rule and three examples, and the blind side is an open set. A fifth round aimed at it would find `<dialog>`. **Residual R2 — filed.**

**Exposure:** 0 of 35 fragments under `docs/explainers/` contain `<dialog`, `popover`, `<canvas` or `<video`; 1 of 35 uses `data-decision` at all **[M]** (`grep -l`, the set is `docs/explainers/*.fragment.html`).

**D. "Deleting the list hides a silent behaviour the author needed."** I looked for a rule in the two functions whose effect is silent. Found: a mark inside raw text (`<textarea><p data-decision>`) or inside a comment composes with rc=0 and **no counter** **[M]**. That is correct (it is text, not markup), it was in no version of §3a, and no fragment does it. **Not refuted.**

### The stop condition

A sentence in §3a about refusals is finished when **the number of members a reviewer could find missing is zero**: no list longer than one, and no rule that describes the scanner's set. The round 3 text is at two (R1) and three (R2). Round 4 found nothing in it, which is one clean reading, not proof.

## 3. Redesign in this PR, or file it?

**File both residuals. Change nothing more in this PR.**

- **The redesign is already in the PR.** The round 3 fold is it.
- **The residuals are not defects today.** R1 points at real code; R2 is a true sentence with a misleading shape. Neither is a BLOCKER, and past the round cap findings are filed unless one is.
- **Another fold re-opens a converged tree.** Round 4 is CONVERGED on this text. Editing §3a again owes another round on a paragraph that has already cost four — the same loop this review was convened to end.
- **One scheduled edit closes both.** Backlog row 620 replaces the deny-list with an allow-list grammar and an in-page visibility check. When it lands, "the composer refuses what it can tell would not be seen" becomes "the composer accepts only …", the function names change, and the bound changes meaning. §3a's paragraph must be rewritten then regardless. Fixing it now means writing it twice.
- **Exposure is nil** (0 of 35 fragments) **[M]**.

## 4. The backlog row (no number)

> | — | 🟡 **`explainer-delivery.md` §3a still describes the decision scanner in two places; both go stale when the scanner is replaced** — filed 2026-11-20 from the Phase 6 review of PR #602 (`decision-tags`; rounds 2 and 3 thrashed on a prose copy of `scripts/brief-compose.py`'s refusal rules, and the round 3 fold deleted the copy). Two residuals of that class remain, neither false today. **(R1)** the pointer names TWO functions (`_DecisionScan.handle_starttag`, `render_decisions`); `handle_starttag` raises nothing, a third decision refusal is raised in `_decision_offset`, and every one of them exits through `render_decisions` alone. **(R2)** the bound says the scanner "reads MARKUP, not CSS" and gives three examples; hiding done in markup alone is also counted — `<dialog>`, `popover`, `<canvas>`/`<video>` fallback, `<progress>` all compose with rc=0 and a counted tag (measured 2026-11-20 at `04fb9828`; not visible in Chromium per `docs/reviews/architecture-review-2026-11-12-603-decision-scan.md` P6-1). 0 of 35 fragments use any of these. **Do it WITH the scanner redesign (backlog #620), in the same PR, not before:** that change rewrites this paragraph anyway. **The shape owed:** §3a names ONE entry point (or only "follow the refusal message"), and states the bound without describing the scanner's set — "a mark that composes is not thereby seen; look at the composed page". **FAILS IF** after the scanner redesign merges, §3a names a function that `grep -n "def <name>" scripts/brief-compose.py` does not find, or §3a's bound still contains the words "MARKUP, not CSS", or §3a contains a list of two or more refused shapes or scanner symbols. ⟦kind: task⟧ | `.agents/skills/shared/explainer-delivery.md` §3a | S | (comprehensibility/explainers) | 🟡 **FILED 2026-11-20** |

Also add one clause to backlog row 620's own text: *"and rewrite `explainer-delivery.md` §3a's refusal paragraph in the same PR"* — otherwise that row can close while the doc still describes the removed model.

## 5. What did this PR decide that is not written down?

1. **ADR-0015 now reaches code, not only specs.** The ADR's rule is about a reader-facing page and a spec. This PR applied its remedy to a skill document and a script, and recorded that only in one sentence of §3a and in a coordinator record. `CONTEXT.md`'s *Canon* entry still defines a canon as a file declared in `check-canonical-source.py`'s `CANONS`; `brief-compose.py` is not one **[M]** (the guard reports three canons: `handoff-path`, `corpus-search`, `marketplace-inventory`). So "the script is the canon for its own refusal rules" is practised and undefined.
2. **The criterion for what a how-to keeps.** After the fold §3a keeps the two SILENT facts (a counted-but-unseen mark; an unmarked question, backlog row 615) and drops the LOUD ones. That is a rule — *a how-to states what fails silently; a loud refusal documents itself* — and it is the reason the deletion is safe. It is written nowhere. Without it the next author of a skill section will list the refusals again, because that is how the first draft of §3a was written.
3. **Private names became the reader's contract.** §3a cites `_DecisionScan.handle_starttag`, an underscore-private method, as where a reader looks. Neither gate I ran resolves a function name cited in a skill document (both stayed green with the pointer present; neither's output mentions it) **[I]** — I did not test a wrong name, because that needs an edit inside the repository. A rename will leave the pointer stale and silent.
4. **A skill section was reviewed claim-by-claim against code.** Rounds 1–3 used a script reviewer's method on prose: every sentence put to the composer. That method is what turned an omission into a finding each round. It was right here, and it was a choice; no document says when a how-to is held to that standard.

## 6. The memory lesson: can a guard mandate the duplication it audits?

**Checked. No guard mandated this one, and one must not be added that would.**

- The lesson's question is *"what fix does this guard FORBID?"* The fix was deleting the list. `check-explainer-delivery.py` (rc=0, `1 shared description, 5 skills cite it, 0 restatements`) and `check-canonical-source.py` (rc=0, three canons) are both green on the head with the list deleted **[M]**. Neither forbade it.
- So the two wasted rounds were not guard-driven. They came from the findings' own additive fixes (§1, point 2).
- **The lesson applies forward.** The obvious "prevent this next time" is a check that §3a names every `_DECISION_REFUSE_*` constant. That check would require the copy, go red on the round 3 fold, and rebuild the loop with a gate holding it shut. It is the rejected third row of §2's table.
- A check that reads the code's own set to build its expectation would also be circular: it could never disagree with the code.

## Measurements, in one place

| Check | Result |
|---|---|
| 9 refusal fragments | 9 × rc=1, message names element + reason + change **[M]** |
| 11 silent-count fragments (CSS, `<dialog>`, `popover`, fallback content, misnesting) | 11 × rc=0, counter reads `1 remaining` **[M]**; unseen in a browser **[M-prior]** for 8, **[I]** for `<rp data-decision>`, `<p data-decision popover>` and `<object data="x.png">` (the prior review's `<object>` also carried `type=image/png`) |
| Raw text / comment | rc=0, no counter **[M]** |
| Decision `raise SystemExit` sites | 3: `:1319`, `:1338`, `:1343`; all reached through `render_decisions` **[M]** |
| `check-explainer-delivery.py`, `check-canonical-source.py` | rc=0, rc=0 **[M]** |
| Fragments using the silent shapes | 0 of 35 **[M]** |
| One compose | 0.28 s wall **[M]** |

**Not run:** `brief-compose.py --self-test`, `check-docs.py` (the round records carry them; nothing here depends on them). No browser was run in this session.
