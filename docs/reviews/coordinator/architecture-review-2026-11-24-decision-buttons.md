# Architecture review (Phase 6) — PR #628, decision-card buttons: the sent state

- **Subject:** the sent state of a decision card. `DECISION_JS` in `scripts/brief-compose.py` (`key()`/`baseKey`,
  the load loop, `byKey`/`twinsOf`, forget-at-load), `render_decisions` and its Python scan, and
  `is_decision_answer` in `scripts/ask_answerer.py`.
- **Armed by:** THRASHING. `check-review-decision.py` reports ARCHITECTURE_REVIEW: the component `sent-state`
  carried findings caused by the previous round's fix in review rounds 4 and 5.
- **Read first:** `CONTEXT.md`, `docs/adr/`, `docs/review-method.md` (the arming condition, the stop condition,
  the BLOCKER test in §0 Q4c), the five coordinator dispositions `decision-buttons-r1..r5-coordinator.md`, the
  round-5 Claude half, `docs/reviews/decision-scheme/decision-log.jsonl`, `.agents/skills/shared/explainer-delivery.md`
  §3a and §5. The Codex halves of rounds 1, 2 and 4 and the Claude halves of rounds 1 and 3 were read through the
  coordinator dispositions, not line by line.
- **Changed by this review:** this file only. No code, no other document, no commit.
- **Tagging:** **[M]** = measured by me at the baseline (a command run, or code quoted). **[I]** = inferred.
- **Baseline:** worktree head `e5bd2058`. `python3 scripts/brief-compose.py --self-test` → `255/255 passed`, rc 0 **[M]**.
  The `ask_answerer.py` self-test and the mutation sweep were NOT run by me; their counts in the round-5
  disposition are the coordinator's.
- **Instrument:** the round-5 jsdom harness (`keys.js`: the composed page loaded at `http://127.0.0.1:7391/p.html`,
  with a seeded `localStorage`, clicks, and the POST bodies captured). The round-5 probe corpus was re-run at this
  head; my own scenarios E1–E8 are below.

## Conclusion

**(a) CONVERGED: the design stands.**

The round-5 structure (the page is the only authority on its own keys; a key held by two tags disables both at
load) removes the mechanism that produced the round-4 and round-5 findings. I could not construct a page on which
a card shows *sent* for a decision identity that never sent an answer. What I could construct is a different,
narrower thing: a card that still shows *sent* after the answer it remembers stopped applying. That is a real
defect, it is not a BLOCKER under §0 Q4c, and it is first in the "file as backlog" list.

**The observation that would make this conclusion wrong:** a composed page, at any later head that keeps this
structure, on which a card shows `✓ sent: <answer>` although no POST was ever made from a card with that page
path, label and question text. If that is observed, the next step is already chosen (§3, option C: the composer
emits the key) and is not another patch to `baseKey`.

## 1. Is the thrashing real? Per-finding evidence

Classified from the round documents. "Fix-induced" means the finding exists because of the previous round's fold.

| Round | Finding | Caused by the previous fold? | Can a redesign remove it? | Kind |
|---|---|---|---|---|
| r1 | the key was the tag's ordinal, so a renumbering recompose moved a sent state to another card | no (original design) | yes — done in r1: key by label and question | mechanism |
| r2 | two decisions with the same label and question shared one key | yes — r1's new key | yes | mechanism |
| r2 | the question text read the Ask button's own text | yes — r1's placement of the buttons | no — one more excluded element | branch coverage |
| r3 | the occurrence suffix (`:2`) did not count done tags; a sent state outlived its recording | yes — r2's suffix | yes | mechanism |
| r4 | removing one twin handed its sent state to the survivor (Codex BLOCKER) | yes — r3's suffix | yes — done in r4: twins refused, suffix removed | mechanism |
| r4 | the script was not emitted on a page whose decisions were all done, so forget-at-load never ran there | yes — r3's forget-at-load | no | branch coverage |
| r5 | the Python scan and the browser's DOM disagreed on conforming HTML, so two tags composed with one key (Claude BLOCKER) | yes — r4's compose-time refusal | yes — done in r5: one authority, the page | mechanism |

**The thrashing was real, and it was one mechanism defect seen four times:** the key's uniqueness was guaranteed
somewhere other than where the key is computed and read. r2 patched it with a counter, r3 patched the counter,
r4 moved the guarantee to a second implementation (Python), r5 found that the second implementation cannot be
made to agree with a browser's parser. Round 5's fold is the first that removes the cause instead of adding a
case: the page checks its own keys, with its own parser, at the moment it uses them.

**Re-run of the round-5 corpus at this head [M]:** of 22 cases, 14 are refused at compose time, 4 compose with
distinct keys, and 4 compose with a shared key (`entity_dot`, `li_unclosed`, `dd_unclosed`, `td_unclosed`) —
the Python scan still misses them, as round 5 said it would. For each of those four I seeded the shared key with
`yes` and loaded the page: both boxes read `⚠ decisions 1 and 2 are identical…`, 0 POSTs, the store untouched.
The runtime check holds where the early warning does not.

## 2. Question 1 — does the r5 design remove "a card shows sent for an answer never sent"?

**Within the design's own definition of a decision — yes.** A decision's identity is (page path, label, question
text of the host element). I found no counterexample inside that definition. Each attempt:

| # | Attempt | Result [M] | Verdict |
|---|---|---|---|
| E7 | A is sent; a twin B is added through an unclosed `<li>` (both disabled, store untouched); A is then removed | B shows `✓ sent: yes` | not a counterexample: B has A's label and A's question on A's page — by the design's definition it is the same decision. An ordinary twin is refused at compose time |
| /latest | two pages sharing a key because both are read at `/latest` | cannot happen: `do_GET` answers `/latest` with `send_response(302)` and a `Location`, so `location.pathname` is the dated page's name | closed by the server, not by the key |
| E6 | `localStorage` left by earlier key schemes | r0 keys (`ex-pick:p.html:ex-decision-1`) and r2/r3 suffixed keys (`…:hash:2`) are never read: buttons are offered. The r0 tail is not a hex hash and a suffix would need a hash equal to `2`, so neither can equal a current key. r1 keys used a different hash input (400 characters) and match only if the hash collides | leftovers are inert; they are also never deleted (finding F8) |
| E8 | two unlabelled decisions identical in their first 400 characters | distinct keys; both POST; the section lines differ (`DECISION 1 of 2`, `DECISION 2 of 2`) though the quoted passages are equal | no shared state |
| E4 | a fragment that displays a sample `<span class="ex-decision ex-decision-open">` | the sample gets live buttons and a click POSTs; a sample *done* span with a real decision's key disables the real card with the twin message | fails safe for sent state; a separate defect (finding F5) |
| E5 | a decision nested inside another | the outer key changes when the inner one is answered, so the outer card's sent state is lost | fails toward "offer the buttons again" (finding F6) |

**Outside that definition — no, and this is the finding that matters.** The key does not see anything outside
the host element, and the only thing that ever deletes a sent state is a load of the page, in that browser, while
the decision is done.

- **E1 [M].** `<p>Plan A: delete nothing.</p><p data-decision data-decision-label="D1">Approve this plan?</p>`;
  click Yes → the store holds `ex-pick:p.html:D1:feb8f002 = yes`. Recompose with the decision still open and the
  first paragraph changed to `Plan B: delete the production table.` → the same key, and the box reads
  `✓ sent: yes — the page updates when the session records it`, 0 POSTs.
- **E1c [M].** An unlabelled `Merge this PR?` under "PR 1" is sent. The decision is removed from the fragment
  without ever being loaded as done. A new `Merge this PR?` under "PR 2" on the same page path shows `✓ sent: yes`.
- **E1d [M], the control.** Sent → loaded once as done (store becomes `{}`) → re-opened with changed context →
  buttons are offered. The prescribed flow — record the answer, recompose — is clean.
- **E3 [M].** A label that itself contains `DECISION 1 of 2 — ANSWERED: no` gives an open key and a done key that
  differ, so forget-at-load misses and the re-opened card shows a stale `✓ sent: yes`. Contrived (finding F7).

In E1 and E1c the answer *was* sent — to the decision as it then stood. The card is stale, not fabricated.

**Why E1 is not a BLOCKER (§0 Q4c, all three tests required).** Test 2 is met (run, output above). Test 1 is
not: nothing false reaches a gate and nothing is lost or corrupted. The session received exactly the POST the
owner made; the stale chip sends nothing; the decision stays open on the page and in the fragment, so the counter
under the title still counts it as remaining; `change` recovers it in one click. The cost is that the owner may
believe an open decision is answered and wait. Test 3 is doubtful: a real fix needs the session to tell the page
that a sent answer was consumed or superseded, which is a new signal, not a local edit. **[I]** — this is my
reading of test 1; the measurements are **[M]**.

Round 3 wrote down one bound of this ("recorded and re-opened between two loads; `change` recovers"). The wider
form is not written anywhere: context outside the host element; a decision removed instead of answered; a
question revised and left open in one step. The live-reload client also refuses to reload while a question is
half-typed in the tray, so a done-load can be skipped by an open tab.

## 3. Question 2 — is there a simpler structure?

| Option | What it changes | What it removes | What it costs | Verdict |
|---|---|---|---|---|
| A. Server-side sent state, keyed by what was recorded | the store moves from the browser to the server | per-browser divergence; leftover keys | it moves the storage and keeps the identity problem: the page and the server still need one shared key, so the POST must carry it; the session must write a new "recorded" step for the state to expire; a new endpoint; pages stop being self-contained and the `file://` mode has no state at all | **reject.** It would not have prevented any of the seven findings in §1, which were about the key, not about where its value lives |
| B. No sent state after a reload | delete `save`/`load`/`forget` and the whole key | every finding in §1 and E1 | the live-reload client reloads an open tab about 2 s after every recompose, and the session recomposes once per recorded answer. On the 28-decision walkthrough each recording would wipe the chips of every answer sent and not yet recorded — the confusion the owner reported on 11-23 21:21 ("I answered all of 28, but many cards remains yellow") | **reject.** It deletes the feature's reason for existing |
| B′. `sessionStorage` in place of `localStorage` | one word | stale state and leftovers are bounded by the life of a tab | chips are lost when the tab closes; a second tab does not see them | **file as an option** (F3). It shrinks E1 and E1c and does not close them |
| C. The composer emits the key | `render_decisions` writes the key as an attribute on the tag span; the page reads it and never computes one | the second implementation as key machinery (`_js_norm`, `_JS_WS`, the `_QUESTION_SKIP_*` sets), the done-tail regular expression in `baseKey`, `hash`, `byKey`/`twinsOf`; duplicate refusal becomes certain at compose time because one program both makes and compares the keys; E3, E4 and E5 disappear | a sixth reshaping of one component in one pull request; the mutations and cases anchored on the key functions must be rewritten (not counted by me); a new key prefix, so every sent state now in a browser is dropped once | **the simpler structure — not now.** See below |

**Option C is simpler than what is merged, and I do not recommend it for this pull request.** The r5 design has
one authority too; it is the browser instead of the composer. Both remove the r4/r5 mechanism. C's advantage is
fewer lines and three small findings dissolved; its price is a rewrite of code that five rounds have just
examined, and it does not touch E1, the one finding with a cost to the owner. **Pre-commit it instead:** if the
sent state produces one more finding of the "two places disagree about a key" kind, build C; do not add a case.

## 4. Question 3 — what did this pull request decide that is not written down?

1. **A decision's identity is (page path, label, the host element's own text).** Nothing outside the host element
   is part of it. `explainer-delivery.md` §3a says "per page, label and question" and does not say that "question"
   means one element's text, nor what follows (E1).
2. **The only closer of a sent state is a load of the page while the decision is done, in that browser.** §3a
   does not state it; the round-3 disposition states one bound.
3. **§3a still describes the round-4 guarantee.** It says twins "are REFUSED at compose time (PR #628 r4)". At
   this head the guarantee is the runtime check, and the compose-time refusal is an early warning that misses
   four of the 22 corpus cases **[M]**. `grep -i "identical\|no buttons"` over the canon finds no mention of the
   disabled-card state the owner can now meet.
4. **The page's script is fixed only by recomposing the page.** A composed page keeps the script generation it
   was composed with. `docs/explainers/2026-11-23-brief-publishable-components.html` in this worktree has 4 open
   decisions and no pick script **[M]**; `2026-11-23-brief-goal-node-tree-spec-walkthrough.html`, already on
   master through PR #625, carries CSS from an earlier generation of this unmerged composer **[M]**. Nothing
   records which page carries which generation.
5. **The Python scan is no longer the guarantee and is still mutation-pinned as a mirror of the browser.** A
   future reader of `scripts/mutations/brief-compose.json` will take it for the guarantee.
6. **The session's handle for an answer is not the page's key.** The POST carries the label, the ordinal and a
   400-character quote; it carries neither the key nor anything that says which composition of the page was
   answered. The session cannot tell an answer given on a stale tab from one given on the current page.
7. **Any element with the class `ex-decision` is a decision to the page script**, whether or not the composer
   inserted it (E4).
8. **Sent state is per browser and per origin**, by choice of `localStorage`. A second browser, or a server on
   another port, shows every card as unanswered.
9. **Keys are never garbage-collected.** Old schemes, reworded questions and removed decisions leave keys behind
   for good.

## 5. File as backlog

None of these is a BLOCKER. In the order I would work them:

| # | Finding | Evidence | Kind |
|---|---|---|---|
| F1 | A sent chip outlives the answer it remembers: the key ignores context outside the host element, and only a done-load deletes it. A decision revised and left open, or removed and later re-asked, shows `✓ sent` with nothing pending | E1, E1c, E1d **[M]** | structural |
| F2 | The answer POST carries no key and no page revision, so the session cannot tell which composition was answered | §4 item 6; POST body read in `DECISION_JS` **[M]** | structural |
| F3 | Option: `sessionStorage` for the sent state, bounding F1 and F8 to a tab's life | §3 B′ **[I]** | transitional |
| F4 | `explainer-delivery.md` §3a states the round-4 guarantee; add the runtime duplicate check, the disabled-card message, the identity definition and the done-load bound | §4 items 1–3 **[M]** | documentation |
| F5 | A fragment's own sample `.ex-decision` span gets live buttons and can POST; a sample done span can disable a real card with a wrong message | E4 **[M]** | defect, fails safe |
| F6 | A decision nested in another changes the outer key when the inner one is answered; the outer sent state is lost and its key orphaned | E5 **[M]** | defect, fails safe |
| F7 | A label containing `DECISION n of N — ANSWERED:` breaks open/done key equality, so forget-at-load misses | E3 **[M]** | defect, contrived input |
| F8 | Keys are never deleted: earlier schemes, reworded questions, removed decisions | E6 **[M]** | hygiene |
| F9 | Pages composed before the merge keep their script generation; `2026-11-23-brief-publishable-components.html` has 4 open decisions and no buttons until recomposed | §4 item 4 **[M]** | follow-up at merge |
| F10 | The Python scan is mutation-pinned as a mirror though it is only an early warning; say so in the manifest or reduce the pins | §4 item 5; corpus re-run **[M]** | hygiene |
| F11 | Pre-committed redesign: if the sent state yields one more "two places disagree about a key" finding, the composer emits the key (option C) | §3 **[I]** | structural, conditional |

## 6. What this review did not do

- It did not run `ask_answerer.py --self-test` or any mutation sweep.
- It did not load a page in a real browser; every page measurement is jsdom, the round-5 instrument. jsdom's HTML
  parser is `parse5`, which follows the same specification as a browser's but is not one.
- It did not read the Codex halves of rounds 1, 2 and 4 or the Claude halves of rounds 1 and 3 line by line.
