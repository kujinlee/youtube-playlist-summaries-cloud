# Round 3 — `decision-buttons` (PR #628) — Claude half

Head reviewed: `456482d5` (r2 fold). Scope: `DECISION_JS` and its cases (`scripts/brief-compose.py`),
`is_decision_answer` and its three call sites (`scripts/ask_answerer.py`), §3a/§5 of
`.agents/skills/shared/explainer-delivery.md`, `scripts/mutations/brief-compose.json`.

Method: I composed every real decision fragment in `docs/explainers/` with this head's composer. Each page was composed
with its own source page, so the REAL lifted tray script was in it, and all three fragments compose. I used copies
with every `data-decision` reset to open, which gave 13 + 28 + 4 = 45 open decisions. I loaded each page in jsdom with
both scripts running and no script errors on stderr. I clicked the first button on every card, then fed each captured
POST through `ask_answerer.split_body` and `is_decision_answer`. After that I reloaded with the saved `localStorage`.
I also built a synthetic fragment with an `h2` and an `h3` decision (real tray) and a pair of identical unlabelled
decisions. Harness: `/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/b387c8e6-9003-42f5-a944-1d4eb1de0c9b/scratchpad/dbr3/h.js`.

## What I tried to refute, and could not

| Question | Result |
|---|---|
| 1. Can a click reach the paid answerer? | **No.** All 45 POSTs parse as the three-line shape, and all 45 give `is_decision_answer` = True. The only paid entry point is `answer_one`, and its one non-test caller is `process_new` → `pending()`, which filters these clicks. `recover_stale`'s retry events and `--retry` still reach `answer_one` only through `pending()`. An empty quote still parses, because the server rewrites only `---` lines and `split_body` accepts `"   > "`. |
| 2a. Sent state survives reload, heading decisions with the real tray included | **Yes.** 45/45 cards show *sent* after reload, with 45 distinct keys. In the synthetic page with the real tray, the `h2` and `h3` hold the tray's `.askbtn` (I checked this in the DOM). Their quotes are `Heading two q?` and `Heading three q?`, with no `ask`, and both show *sent* after reload. |
| 2b. Stale *sent* on a different decision | Found one path: **F1** below. |
| 3. Recommended text on the real fragments | **Correct on every card that has a `.rec`.** goal-node-tree has 28/28 and publishable-components 4/4. Each one is the bold lead, or the first sentence less `Recommend…:`. Examples: `recommended (new child)`, `recommended (arm every node that has an anchored document, minus a short named list of exemptions)`. The marketplace page (13 decisions) has no `.rec` element, because its recommendations are `<strong>My recommendation: …</strong>` inline. So it shows no ★ button, which matches §3a ("when the card has a `.rec` line"). That is not a defect. |
| 4. Did the r2 fold add a defect? | The key is computed once at load, before any box is inserted, and the tray script runs after it, so it is stable. Stripping `BUTTON`/`.ex-pick`/`.askbtn` at any depth gives the same text at load and at reload. The occurrence suffix is where F1 lives. F1 is a residue of r2 C1 that the r2 case cannot see, not a regression: before r2 the twins shared a key outright. |
| 5. Self-tests and mutations | `brief-compose.py --self-test` **248/248**. `ask_answerer.py --self-test` **124/124**. `check-plan-code.py --mutate . --only scripts/brief-compose.py`: see *Gates* below. |

## Findings

### F1 — Minor — a recorded decision hands its *sent* to an identical twin (the r2 C1 case does not cover this)

`key()` numbers the occurrences of a base key among **open** tags only
(`document.querySelectorAll('.ex-decision-open')`, then `SEEN[b]`). Take two open decisions with the same label (less
the ordinal) and the same question, A then B. The owner answers A, so A's key is `b` and B's key is `b:2`. The session
then records A's value and recomposes, as §3a says it must. A is now a `.ex-decision-done` tag and is no longer counted,
so B becomes the first occurrence and gets key `b`, which is A's stored answer.

Measured with the synthetic page: two `<p data-decision>Same?</p>`. I clicked ✔ Yes on the first (DECISION 7 of 8),
which stored `ex-pick:syn.html::f414bf6c = yes`. I recomposed with the first set to `data-decision="yes"` and reloaded.
**DECISION 8 of 8 shows `✓ sent: yes`** although nothing was sent for it. The owner then never answers it.

Severity: this is the wrong behaviour r2 C1 claimed to remove ("not its identical twin"). The r2 case reloads with both
twins still open, so it cannot see this. Real fragments have no such twins: all 45 decisions have distinct base keys.
That is why it is Minor and not a BLOCKER. A fix, for whoever picks it up: count occurrences over all `.ex-decision`
tags, done ones included. A done tag's label needs its `— ANSWERED: …` tail stripped, so the numbering does not move
when one is recorded. And forget the key of any decision that is done at load. That second step also clears F2.

### F2 — Minor — a decision the session re-opens shows its old *sent*

The same mechanism as F1. Nothing removes a stored key when its decision is recorded. If a later walkthrough on the
same page path re-opens a decision with the same label and question (`data-decision=""` again, say a re-asked
"Approve?" after a revision), it loads as `✓ sent: <old answer>`. I did not build this case. It follows from `load()`
having no other input than the key, and the key does not change when a decision goes done → open. The suggested
"forget a key whose decision is done at load" fixes it.

### F3 — Nit — the skipped-list filter in `status_text` has no killing case

I made five hand mutations of `ask_answerer.py` on a scratch copy. The baseline on that copy was 118/119, with one case
failing for a fixture-path reason. Four were KILLED (117/119): drop the `pending()` filter, drop the `page_items()`
filter, unanchor the section regex, drop the `ANSWER: ` prefix. **Dropping `and not is_decision_answer(q)` from the
skipped list in `status_text` SURVIVES (118/119).** No paid run follows from it, because `--retry` still goes through
`pending()`, so this is cosmetic in `--status`. Separately, none of the r1 answerer mutations are in
`scripts/mutations/ask_answerer.json`. The paid-run guard, which is this PR's most consequential line, is killed by its
case today but not ratcheted. Worth a manifest entry; it is not a defect in behaviour.

### F4 — Nit — `change` forgets before a new answer is sent

`change` calls `forget(tag)` at once. If the owner clicks it and then reloads, or clicks `change` and abandons it, the
card offers the buttons again although an answer is in `questions.md`. The case "change forgets" makes this
intentional, and §3a says the newest `ANSWER:` wins, so a resend is harmless. I note it only because `save()` on the
next successful send would overwrite the key anyway, so the `forget` buys nothing.

## Gates

- `python3 scripts/brief-compose.py --self-test`: 248/248.
- `python3 scripts/ask_answerer.py --self-test`: 124/124.
- `python3 scripts/check-plan-code.py --mutate . --only scripts/brief-compose.py` (after the r3 fold, in a scratch copy): 102 mutations, 102 killed, 102 attributed to the case each names, 0 survivors, re-control passed (rc 0) — measured over ONLY scripts/brief-compose.py, a diagnostic slice, not the full sweep.

VERDICT: CONVERGED
