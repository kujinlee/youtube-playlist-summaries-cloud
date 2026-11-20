Reviewed head: 28545f11d932f6a49295e5f606fe3e7bf75c4457

# decision-tags — round 1, Claude half

Subject: `git diff origin/master...HEAD` — new §3a in `.agents/skills/shared/explainer-delivery.md`
(the `data-decision` markup) plus one entry in `docs/dashboard-entries.md`.

Method: every §3a claim was put to `scripts/brief-compose.py` by composing small fragments in a
scratch directory outside the repository (`--content <frag> --slug t<x> --title T --out <scratch>/o<x>.html`),
and grepping the composed page; code quoted from `scripts/brief-compose.py` (`_DecisionScan`,
`render_decisions`). Fifteen fragments, a–o.

## Gates

- `python3 scripts/check-explainer-delivery.py` → `explainer delivery: 1 shared description, 5 skills cite it, 0 restatements`, rc=0
- `python3 scripts/brief-compose.py --self-test` → last lines:
  `ok     603 r1: an ANSWERED tag reads the green tokens, and green differs from yellow everywhere` / `226/226 passed`
  (matches the dashboard entry's "226/226 unchanged").

## Claims that held (tried to refute, could not)

- Open mark: `<p data-decision>Keep the stranger audience?</p>` → `🟨 ✍ DECISION 1 of 1` (fragment a).
- Answered mark: `data-decision="Yes — owner, 11-11"` → `🟩 ✍ DECISION 1 of 1 — ANSWERED: Yes — owner, 11-11` (b).
- Label: `data-decision-label="D7"` → `🟨 ✍ D7 — DECISION 1 of 1`; the counter's link also reads `D7 — DECISION 1` (c).
- No mark → no counter, no decision CSS (g; `render_decisions` returns the markup unchanged at `total == 0`).
- Counter (h, 1 open + 1 answered): `✍ 2 decisions on this page · 1 remaining · 1 answered · next: DECISION 1`, linked to `#ex-decision-1`, placed after the first `</h1>` (`page_chrome.place_bar`).
- Refusals named in §3a: `hidden` (e), `inert` ancestor (k), `<svg>` (l), a `<details>` body (d) — each CANNOT RUN, no page written. `<summary data-decision>` composes (j), consistent with "move it" guidance.
- Palette tokens `--decide*`/`--decided*` emitted by the composer for light, OS-dark and both `[data-theme]` keys (`DECISION_CSS`), only on a page with a mark.
- "Answering … then recomposing (§3's rule — same commit)": §3's boxed rule does say "EDIT THE FRAGMENT, THEN RECOMPOSE — IN THE SAME COMMIT".
- A reader following §3a + §3's fragment shape produces a page that composes (a, b, c, h, m all ✅).
- Owner date/time 2026-11-11 06:03 and backlog #603/#615 match `docs/backlog.md` and the code comment.

## Findings

- **MAJOR — .agents/skills/shared/explainer-delivery.md:237:** "A mark the reader could not see is CANNOT RUN, not a silently-counted tag" is stated as a guarantee, and it is false for ordinary, non-hostile shapes. Input n: `<div style="display:none"><p data-decision>Q?</p></div>` → composed ✅, `🟨 ✍ DECISION 1 of 1` and counter `1 remaining` — counted, never seen. Same for any class-based hiding (the scanner reads only the `hidden`/`inert` attributes, `_DECISION_HIDING_ATTRS`). Input i (the misnesting bound the code's own `_DecisionScan` docstring records, backlog #616): `<p>a<b hidden>c</p><div data-decision>Q?</div>` → composed ✅ and counted. The doc names the refused cases as if they were the definition of "could not see"; the code's docstring states the bound and §3a drops it. Fix: phrase it as "these are refused: …", and add the bound (CSS hiding — `style`, a class — and misnested hidden markup are NOT detected; the mark is counted).
- **MINOR — .agents/skills/shared/explainer-delivery.md:229:** "tag after it" is wrong about placement. Observed (a): `<p data-decision><span class="ex-decision ex-decision-open" …>🟨 ✍ DECISION 1 of 1</span>Keep the stranger audience?` — the tag is the element's FIRST child, before the question text (`edits[at + len(text)]`, right after the start tag). A reader may take "after it" to mean after the element and mark the element above the question. Fix: "a tag at the start of that element".
- **MINOR — .agents/skills/shared/explainer-delivery.md:238:** "in a collapsed `<details>`" implies an `open` one is fine; it is not. Input d: `<details open><summary>s</summary><p data-decision>Q?</p></details>` → CANNOT RUN ("it is in a <details> outside its <summary>…"). A mark ON a `<details>` is refused too. Fix: "anywhere in a `<details>` except its `<summary>`, open or not".
- **MINOR — .agents/skills/shared/explainer-delivery.md:237-238:** the refusal list omits the ON-element refusals, the most likely to be hit by a page author: a mark on a table row/structure, a form control or a void element (`_DECISION_REFUSE_ON`: `table`, `tr`, `thead`, `caption`, `option`, `textarea`, `img`, `br`, …). Input f: `<table><tr data-decision><td>Q?</td></tr></table>` → CANNOT RUN ("it is ON a <tr>…"). It fails loudly, so nothing ships wrong, but a reader following §3a alone cannot predict it; "mark the `<td>`, not the `<tr>`" is the one-line fix. Also unmentioned: a fragment already using id/name `ex-decision-<n>` is CANNOT RUN.
- **MINOR — .agents/skills/shared/explainer-delivery.md:234:** the counter is described as "total · remaining · answered"; when everything is answered the answered count is replaced (m: `✍ 2 decisions on this page · 0 remaining · all answered`, no link). Harmless, but the "exact text" a reader expects differs in the all-answered state; a whitespace-only value (`data-decision="   "`, o) is OPEN, also unstated.

VERDICT: NOT CONVERGED
