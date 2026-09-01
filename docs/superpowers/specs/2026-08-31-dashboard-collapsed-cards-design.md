# Dashboard entry cards collapse to one line — Design Spec

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

**Status:** v1 — approved by the user 2026-08-31, not yet reviewed.

Extends [`2026-08-28-project-dashboard-design.md`](2026-08-28-project-dashboard-design.md) §5 (the
*What changed* section) and [`2026-08-31-dashboard-ask-choices-design.md`](2026-08-31-dashboard-ask-choices-design.md)
§1a (the derived badges, which must survive the collapse). Supersedes neither.

**Reported by the user, 2026-08-31**, reading the live page with a screenshot attached:

> *"dashboard list many cards and I want to see them as tighter list initially ie, rather than
> series of thick cards, thin cards with just title line initially. At the end of title small
> triangle icon indicates it can be open to show 'What this means' text when user clicked. 'Raw
> technical detail' button can be shown at the end of 'what this means' section."*

and, on the same page:

> *"I also noticed that date/serial lines is shown as '2026-08-31 2026-08-31/3'. 2026-08-31 is
> repeated twice"*

A third defect was found while grounding the first two, and is **not** cosmetic: text an author
wrote is currently displayed nowhere. It is folded into this slice because collapsing the cards makes
the title line the only thing visible until a click, which raises the cost of losing part of it.

---

## 1. The three defects, measured

### 1a. Every card spends four lines before it says anything

`scripts/gen-dashboard.py:995-1002` emits, per entry:

```python
f'{day_anchor}<article class="entry" id="{eid}">'
f'<h3>{_html.escape(e["date"])} '
f'<span class="eid">{_html.escape(e["id"])}</span>{flag}</h3>'
f'<p class="title">{_inline(e["title"])}</p>'
f'<details id="{eid}-plain"><summary>What this means</summary>'
f'<div class="prose">{_prose(e["plain"], drop_headline=True)}</div>'
f'</details>{tech}</article>'
```

A meta row, a title that wraps to two lines, and **two sibling folds** — both of which are shut, so
three of those four rows carry no information beyond "there is more here". The store holds 29
entries; roughly five fit on a screen.

### 1b. The date is printed twice, by construction

```python
:379   entry["id"] = f"{date}/{seen[date]}"
:997   <h3>{e["date"]} <span class="eid">{e["id"]}</span>…
```

The id is **derived** from the date, so `2026-08-31 2026-08-31/3` is not a property of some entries —
it is guaranteed for every entry that renders. Authors never type the ordinal; `## 2026-08-29` is the
whole header they write (`HEADER = re.compile(r"^## (\S+)(.*)$")` in `check-dashboard-entry.py:25`),
and `/3` is the generator's own within-day counter.

### 1c. ⛔ The tail of a long opening sentence is displayed NOWHERE

**Measured, not inferred** — by calling the delivered functions:

```
TITLE_CAP: 110
title  : 'The backlog page refused to build until the newest item was described in
          plain words, which is the guard…'
prose  : <p class="lede">Second para follows.</p>

TAIL IN TITLE?  False
TAIL IN PROSE?  False
```

Two rules, each correct alone, compose into content loss:

1. `:428` caps the title at `TITLE_CAP = 110` and appends `…`;
2. `_prose(…, drop_headline=True)` (`:250-258`) drops the entry's first sentence from the fold,
   because when the title shows that sentence **in full** an unedited lede repeats it word for word.

Rule 2 derives the sentence by re-applying `_first_sentence` **uncapped** (`cap=len(first)`), which is
deliberate and documented — matching on the *displayed* title would never match a truncated one. The
consequence is that the fold drops the whole sentence while the title showed only its first 110
characters. Everything between the cut and the full stop exists in the store and reaches no reader.

This is live on the user's page today: the top card in the reported screenshot ends
`…which is the guard…`, and the remainder of that sentence is not on the page.

The existing guard at `:2087-2091` covers the *adjacent* case — a first paragraph with **no**
terminator — and its comment names the same failure. The terminated case was left open.

---

## 2. What the card becomes

One `<details>` per entry. The `<summary>` **is** the collapsed row.

```
2026-08-31/5  heads-up   The backlog page refused to build until the newes…  ▸
2026-08-31/4             Both asks on the previous entry are settled: the c…  ▸
2026-08-31/3  resolved   The page can no longer tell you that something ne…  ▸
```

### 2a. The row

| Part | Rule |
|---|---|
| id | `e["id"]` **alone**. The bare date is deleted from the row — the id already contains it |
| badge | stays on the collapsed row, unchanged (`needs you` / `heads-up` / `resolved`) |
| title | fills the remaining width; clipped with a real ellipsis, not a character cap |
| triangle | `▸` at the **end** of the row, rotating to `▾` when open |

**Why the id alone, and not `2026-08-31 · 5`.** The id is not decoration: it is the reference an
author types as `[resolved: 2026-08-31/5]`, and pass 2 of `parse_entries` (`:434-445`) resolves those
strings against it. A prettier rendering stops being copy-pasteable. `2026-08-31/5` is one token,
contains the date, and is the canonical form.

**The row is built from `e["date"]`/`e["ordinal"]`/`e["id"]` as separate fields** (`:368`, `:378`).
Nothing splits the id string. A positional read of a shape this file merely believes in is the defect
class recorded in `docs/backlog.md` as the `cells[-2]` incident, and it is avoidable here for free.

### 2b. Clipping is CSS, and the text stays in the DOM

```css
summary{display:flex; gap:.6rem; align-items:baseline; list-style:none}
summary::-webkit-details-marker{display:none}
.entry .title{white-space:nowrap; overflow:hidden; text-overflow:ellipsis}
details[open] .entry .title{white-space:normal; overflow:visible}
```

The clipped remainder is present in the document, so in-page find (Cmd-F) still locates it and the
browser scrolls it into view. Opening a card un-clips **that card's own** title, which then wraps in
full above its prose.

The triangle is `aria-hidden`. `<summary>` already exposes its expanded state to assistive
technology; a second announcement would be noise, not access.

### 2c. The expanded body

The prose appears **directly**, with no `What this means` label. The title above it is now the
disclosure's own heading, so that label would be a second control naming the same thing.

`Raw technical detail` stays a nested `<details>` at the end of the prose — a fold inside a fold,
which is what the user asked for and what the content is: detail behind detail.

### 2d. A broken entry does not fold

An entry that failed to parse (`class="entry broken"`, `:983-988`) keeps rendering its error and its
raw text **open and unfoldable**. Hiding a parse failure behind a click makes a problem quieter
instead of louder — the exact defect this page shipped in August and fixed in PR #186.

### 2e. Everything starts collapsed

No exception for the newest entry, and none for a `needs you` badge: anything genuinely waiting on
the reader is already listed in the **What needs you** tray above this section, so opening a card by
default would duplicate that, not add to it.

---

## 3. The truncation fix — delete the cap, not patch around it

`:428` stops capping. `entry["title"]` becomes the full first sentence.

With §2b's CSS owning the visible clip, `TITLE_CAP` has no reader left. Its only remaining effect is
the content loss in §1c, so the following are **deleted**, not disabled:

- `TITLE_CAP` and the truncation branch of `_first_sentence` (`:141-158`, from `if len(out) > cap:`);
- `_close_orphan_markup` in full (`:171-201`);
- the self-test cases bound to them — at `:2380` (a two-delimiter loop), `:2397`, `:2427` and
  `:2449-2453`;
- the three mutations in `scripts/mutations/gen-dashboard.json` that guard the orphan repair:
  *"a truncated headline is not re-balanced, so an orphan delimiter ships"*, *"the orphan closer
  becomes a SECOND scanner again, disagreeing on code"*, and *"closers are appended PAST the cap, so
  TITLE_CAP stops bounding"*.

`_close_orphan_markup` exists **solely** because cutting mid-`**bold**` orphaned the opener — a wound
the cap inflicts on itself. Removing the cut removes the class.

`drop_headline` is unchanged and its de-duplication now holds unconditionally: the title always shows
the sentence whole when open, so no text can fall between the two rules.

### 3a. The mutation-count revision, stated as a rule not a number

`EXPECTED_MUTATIONS` in `scripts/check-plan-code.py` pins `gen-dashboard` at **56** (measured
2026-08-31, alongside 242 self-test cases). Three entries die with the code they guard, and this
slice adds entries for the new properties in §4.

**The new pin is whatever `--mutate .` measures after the change, recorded with a comment naming the
three deleted entries and why they went.** This spec deliberately does not predict the final number:
a count pinned to a past event must not be "corrected" to a number nobody ran, and the difference
between *coverage deleted with its code* and *coverage quietly narrowed* is exactly what the comment
has to carry.

---

## 4. Falsifiers — the observation that makes each one FAIL

Each is a `--self-test` case in `scripts/gen-dashboard.py` unless marked otherwise.

| # | Property | Fails when |
|---|---|---|
| F1 | A long first sentence reaches the reader whole | the full sentence is not a substring of the rendered card |
| F2 | The date appears once per card row | the rendered row contains the date twice |
| F3 | The badge is on the collapsed row | the badge markup falls inside the fold's body rather than its `<summary>` |
| F4 | The tech fold is nested inside the entry fold | `…-tech` appears as a sibling of the entry `<details>` rather than within it |
| F5 | A broken entry is not foldable | a `class="entry broken"` card emits a `<details>` |
| F6 | Cards are shut by default | any entry `<details>` renders with the `open` attribute |
| F7 | The title clip is CSS, not a character cap | a rendered title ends in `…` that the author did not write |
| F8 | Every `<details>` still has an id | *(existing case, `:1701`)* the counts diverge |
| F9 | No duplicate DOM ids | *(existing case)* the id set is smaller than the id list |

**Two existing cases must be re-aimed rather than deleted**, because they are bound to the old
two-fold layout and would otherwise pass vacuously or fail spuriously:

- `:1525` — *"tech is behind a fold"*, which pins `<details id="{eid}-tech">`. The id survives the
  restructure, so the case survives; its comment, which explains that the assertion was narrowed
  *away* from a bare `"<details" in html` because the glossary always emits one, must be kept and
  extended: after this change the entry card emits a `<details>` too, which makes the bare form
  wrong in a second way.
- `:1701` — *"every details has an id"* counts `<details id=` against `<details`. The new entry fold
  must therefore carry an id of its own; `{eid}-card` is free (`{eid}`, `{eid}-plain` and
  `{eid}-tech` are taken, and `-plain` disappears with the label).

---

## 5. Out of scope

- The **What needs you** tray, the **Worth knowing** block, the chart, and the glossary fold are
  untouched. Only the *What changed* cards collapse.
- No expand-all / collapse-all control. It is one more piece of state to get wrong, and the browser's
  own find-in-page already reaches clipped titles (§2b).
- No deep-link auto-open. `#day-<date>` anchors land on a row, which is legible collapsed; forcing a
  targeted card open needs JS for a case nobody has reported.
- Backlog #78 (the entry gate cannot see entry-only branches) is unrelated and stays open.

---

## 6. Blast radius

One file emits these cards — `scripts/gen-dashboard.py:995-1002` — verified by
`grep -rn 'class="entry' scripts/`, which returns only that file's two sites. `brief-compose.py`
composes the page but does not render entry cards. `page_markup.py` renders inline spans and is
untouched: this slice changes card *structure*, not inline markup.

The page is derived and regenerated by hook, never hand-edited, so shipping it means regenerating
and looking at it — §4's falsifiers are necessary and not sufficient.
