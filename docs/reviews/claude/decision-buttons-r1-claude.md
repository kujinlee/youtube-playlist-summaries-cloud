# PR #628 decision-card buttons — round 1, Claude half (adversarial)

Subject: `git diff origin/master...HEAD -- scripts/brief-compose.py .agents/skills/shared/explainer-delivery.md`
at `9c972ace` (branch `decision-buttons`). Mandate: refute that the buttons are correct.

## What I ran

- `python3 scripts/brief-compose.py --self-test` in the worktree: **234/234 passed**.
- Real pages under jsdom (the main checkout's `node_modules/jsdom`), with `fetch` stubbed to capture POST bodies:
  - `2026-11-23-brief-goal-node-tree-spec-walkthrough.fragment.html` with every `data-decision` value
    stripped (28 open), composed into scratch. 28 tags, 28 boxes. Every POST's section line was
    `**<label> — DECISION n of 28**`, every quote was the card's question, every ★ Recommended was the
    bold lead of its own `.rec`, e.g. `4.3 → "new child"`, `Q6 → "arm every node that has …"`.
  - `2026-11-23-brief-publishable-components.fragment.html` (4 open). Wrong result, see F3.
- Tray idempotence (backlog #106): I composed a fragment with no decision using a page that carries
  `DECISION_JS` as `--source`. The output holds no `ex-pick`. Recomposing the 28-decision fragment
  from its own output is byte-identical apart from the timestamp. `extract_tray` takes the last
  `<script>`, which is still the tray's because `DECISION_JS` is appended to `body` before `markup` and
  `script`. **Q3: no defect.**
- Mutations on a copy of `scripts/` in scratch. The baseline there is 233/234: the real-fragments case needs `docs/`.
  - KILLED: the label regex reduced to one token, emitting the script on `decisions` instead of `_remaining`, the
    `Recommended:` strip removed, and `LIVE = true` (file pages POST).
  - SURVIVED: **4** mutations, see F4.
- XSS (Q5): every page string reaches the DOM through `textContent`. `innerHTML` is only ever assigned `''`.
  The localStorage value that `sent()` shows also goes through `textContent`. **No defect.**
- Q1, the shape: it matches the tray's `compose()` (`'**' + section + '**\n   > ' + quote + '\n   Q: ' + q`). It
  parses through `ask_answerer.split_body`. The label extraction holds for labelled and unlabelled tags.
  `🟨` is a surrogate pair, but `\S+` takes both halves.

## Findings

### F1 — Major — a click goes to the Ask answerer as a paid question when the answerer is running
`scripts/brief-compose.py:1251` (the POST) and `.agents/skills/shared/explainer-delivery.md:234-237`.
The comment says "the session's question watcher needs no change". But since backlog #625 the same
`questions.md` channel feeds `scripts/ask_answerer.py`, which claims every new entry within about a second
and starts one headless `claude -p` for it. That run is capped at $0.75 and counts toward the 40-a-day
question cap (`Caps`, `ask_answerer.py:290`). The model labels the click a decision, so it goes to the
inbox. `insert_answer` (`ask_answerer.py:613`) then finds no heading named `4.1 — DECISION 1 of 28` and
appends a "passed on, not acted on" block **at the end of the fragment**, then recomposes the page.
**Failing input:** start the answerer, open the 28-decision walkthrough and click ★ Recommended on every card.
That costs 28 model runs (up to about $21 and 28 of the 40 daily questions), adds 28 blocks to the end of
the fragment, and produces 28 page rewrites that race the session's own edits to `data-decision` on the
same fragment. It also means the session has to `--claim` (rc 3, already taken) or read `--inbox` before it
can record anything. Neither the comment nor §3a mentions the answerer. **Fix:** mark the entry so the
answerer skips it or routes it to the inbox with no model run (for example, `split_body` recognises
`Q: ANSWER:` from a decision section), or at least state the interaction in §3a.

### F2 — Major — the "sent" state is keyed by position, never expires, and outlives a recompose
`scripts/brief-compose.py:1219` and `:1277`. The key is `ex-pick:<doc>:ex-decision-<n>`. `n` is the tag's
**ordinal** (`render_decisions`), and `if (prior) { sent(box, prior); return; }` hides every button for good.
**Failing input:** a page has Q1, Q2 and Q3 open. Click ✔ Yes on Q2, which stores `ex-decision-2`. The session
then removes Q1, or inserts a new decision above Q2, and recomposes. The old Q3 is now `ex-decision-2`, and on
reload it shows `✓ sent: yes — the page updates when the session records it` with **no buttons**. Nothing
was ever sent for it, and this browser has no way to answer it.
The same lockout happens with no renumbering, whenever the session does not record a value. Examples:
it treats an "Other…" text as a question, or the answerer took the click (F1). The card stays "sent"
forever. That contradicts the new doc line "the card says *sent* until the page is recomposed"
(`explainer-delivery.md:237`), because localStorage survives a recompose. There is no undo or resend.
**Fix:** key the entry on something stable, such as the label plus the question text, or the hash the
question carries. Also drop the stored state once the page is newer than the click, or offer a "resend" link.

### F3 — Minor — `recOf` mislabels a real fragment whose `.rec` has no `<b>` lead and reads "Recommend:"
`scripts/brief-compose.py:1263-1265`. With no `<b>`, the code falls back to the whole `.rec` paragraph.
The strip only matches `Recommended:?`.
**Failing input (a tracked page):** `2026-11-23-brief-publishable-components.fragment.html:289`
`<p class="rec">Recommend: yes. It puts your four named features first, …</p>`. Measured under jsdom:
- the button reads `★ Recommended: Recommend: yes. It puts your four named …`;
- the click sends `Q: ANSWER: recommended (Recommend: yes. It puts your four named features first, at 13.25 h, and re-prices after waves 1–2)`.

That is a 200-character rationale where the choice belongs. All four cards on that page do this. The
fallback also takes the **first** `<b>` anywhere in the paragraph, not a leading one. **Fix:** accept
`Recommend(ed)?`, and when there is no leading `<b>`, cut at the first sentence end. Add a case built from
this fragment's own shape.

### F4 — Minor — four behaviours the cases name, or the code relies on, survive mutation
Mutations applied to a scratch copy. Each one left every `buttons:` case green:
1. **`recOf` stops at the next decision** (`:1261`): deleting `if (s.querySelector && s.querySelector('.ex-decision')) return '';` survives. The stub's `.rec` has no next sibling, so no case has a decision without a `.rec` followed by one with a `.rec`. In a fragment whose decisions are bare sibling `<p>`s, the first decision would offer the second one's recommendation.
2. **`questionOf` skips the button box** (`:1225`): replacing the `.ex-pick` exclusion with `false` survives. The stub's `p.childNodes` is a static `[tag, txt]` (`:3118`) and `insertBefore` never adds the box to it. In a real DOM, without the exclusion, the quote would end in `★ Recommended…✔ Yes✖ No✎ Other…`.
3. **A reload shows "sent" and no buttons** (`:1277`): deleting `if (prior) {…}` survives. No case reloads with a stored value.
4. **Only a 2xx is remembered** (`:1253`): deleting `if (!r.ok) throw …` survives. The fetch stub always returns `{ok: true}`, so a 4xx or 5xx is saved as sent. Together with F2, a send that failed then locks the card.

The case "labelled by THAT tag (two tags)" runs the two tags in **two separate** `vm` contexts. It cannot
catch a bug where every box on one page sends the first tag's label. **Fix:** give the stub a live
`childNodes` and an element chain with two decisions on one page (one without a `.rec`), a pre-seeded
`localStorage`, and a `{ok: false, status: 400}` fetch.

### F5 — Minor — the button labels leak into the Ask tray's section text on a heading decision
The tray's `headingText` (the lifted tray script, e.g. `2026-11-23-brief-goal-node-tree-spec-walkthrough.html:549`)
excludes only `.askbtn`, which is the "…had never workedask" class of defect its own comment records.
**Failing input:** `<h3 data-decision data-decision-label="Q1">Ship it?</h3>`. Hovering it and clicking *ask* now
gives the section `🟨 ✍ Q1 — DECISION 1 of 1Ship it?★ Recommended: …✔ Yes✖ No✎ Other…`. The tag text was
already leaking before this PR. The buttons make it worse. The answerer then cannot match the section to the
fragment's heading, so the answer lands at the end of the page. Tracked fragments put decisions on `<h4>`
(the marketplace walkthrough Q1–Q4), and `nearestHeading` reads H1–H4. **Fix:** exclude `.ex-pick` and
`.ex-decision` in `headingText`, or put the box outside the heading.

### F6 — Minor — smaller defects in the interaction
- `:1289`: a bare `Enter` sends with no `e.isComposing` guard. In an IME, such as Korean, the Enter that commits the
  composition can send the text before the last syllable is committed. The tray uses Cmd/Ctrl+Enter.
- The buttons are not disabled while a POST is in flight. A double click sends two entries, which with the
  answerer running (F1) means two paid runs.
- `:1201`: `.ex-pick-err { color: #c0392b; }` is a literal colour. It bypasses the token-and-contrast checks
  that every other decision colour goes through (603 r1, "every tag state is READABLE in every theme block").
  On the dark theme it is likely below 4.5:1. I did not measure this.
- "Other…" clears Recommended, Yes and No and offers no way back short of a reload.

## Not defects (checked)
- The script is emitted exactly when `_remaining > 0`. The mutation to `decisions` was killed.
- It does not break the tray region or `extract_tray`. I measured idempotence and checked that it does not leak into a later compose.
- There is no HTML injection.
- The label holds with and without `data-decision-label`. The quote is whitespace-normalised and capped at 400 characters, like the tray's.

VERDICT: NOT CONVERGED
