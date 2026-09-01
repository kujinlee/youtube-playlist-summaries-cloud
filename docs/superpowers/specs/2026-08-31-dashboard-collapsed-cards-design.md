# Dashboard entry cards collapse to one line — Design Spec

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

**Status:** **v3 — rounds 1 and 2 folded in, BOTH halves each round.**
**Approved by the user 2026-08-31; proceeding in AFK mode from here.**
Reviews at `docs/reviews/spec-dashboard-collapsed-cards-r{1,2}-{codex,claude}.md`.

| Round | Codex | Claude |
|---|---|---|
| 1 | 1 Blocking, 3 High, 1 Medium, 1 Low — **executed** (`--self-test` 266/266, `--mutate .` 120/0) | 2 Blocking, 2 High, 2 Medium, 1 Low |
| 2 *(scoped to round 1's own fixes)* | **0 Blocking**, 1 High, 1 Low — executed 3 suites | **0 Blocking**, 1 High, 2 Medium, 1 Low |

**The two halves overlapped and each found things the other missed, in both rounds** — §7 and §8
record which. The design shape in §2 is unchanged from the version the user approved.

> ⚠ **v3's §2f is SMALLER than v2's, and that is the point.** Round 2 was scoped to what round 1's
> fixes added, on the measured expectation that a fix is where the next defect lives — the immediately
> preceding slice had *every* round-2 Blocking turn out to be a regression from round 1's own fix.
> It paid: v2's brand-new §2f could hide an entry's raw technical detail entirely. v3 does not
> widen the rule to cover that case; it **deletes the text comparison** that made the case possible.

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

One `<details>` per entry, **inside** the existing `<article class="entry" id="{eid}">`. The
`<summary>` **is** the collapsed row.

```
2026-08-31/5  heads-up   The backlog page refused to build until the newes…  ▸
2026-08-31/4             Both asks on the previous entry are settled: the c…  ▸
2026-08-31/3  resolved   The page can no longer tell you that something ne…  ▸
```

### 2a. The row, and the element that carries it

The summary's entire content is **one `<h3 class="row">`** holding, in order: id, badge, title,
triangle.

| Part | Rule |
|---|---|
| id | `e["id"]` **alone**. The bare date is deleted from the row — the id already contains it |
| badge | stays on the collapsed row, unchanged (`needs you` / `heads-up` / `resolved`) |
| title | `<span class="title">`, filling the remaining width; clipped by CSS, not by a character cap |
| triangle | `▸` at the **end** of the row, rotating to `▾` when open, `aria-hidden` |

**Why a heading and not a `<p>` or a bare span** *(r1: Claude H1, Codex H3 — agreeing)*. `<summary>`'s
content model is **phrasing content, or a single heading element**. The delivered markup's
`<p class="title">` is neither, so moving it into the summary as-is emits non-conforming HTML. A single
`<h3>` wrapping the whole row is explicitly allowed.

**The heading outline changes, deliberately** *(r1: Claude H2, Codex H3)*. Today there are 29 `<h3>`s,
one per entry, each reading `2026-08-31 2026-08-31/1` — id and date only, so heading navigation yields
a list of dates. Keeping a real `<h3>` preserves the entry-level stop **and improves it**: the outline
becomes a list of what happened. A `<summary>` is *not* automatically a heading, so this must be the
element, not an inference.

**Why the id alone, and not `2026-08-31 · 5`.** The id is not decoration: it is the reference an
author types as `[resolved: 2026-08-31/5]`, and pass 2 of `parse_entries` (`:434-445`) resolves those
strings against it. A prettier rendering stops being copy-pasteable. `2026-08-31/5` is one token,
contains the date, and is the canonical form.

**The row is built from `e["date"]`/`e["ordinal"]`/`e["id"]` as separate fields** (`:368`, `:378`).
Nothing splits the id string.

### 2b. The anchor stays where it is

`<article class="entry" id="{eid}">` is **preserved unchanged** *(r1: Codex M5)*. The *What needs you*
tray links to `href="#{_slug(e["id"])}"` (`:877-880`) and that target lives on the article. The new
fold gets its **own** id, `{eid}-card` — verified free (`grep -n '\-card"'` returns nothing) — so the
tray's links keep resolving. Moving the canonical id onto the fold would break every tray link while
leaving them rendered and plausible.

### 2c. Clipping is CSS, and the text stays in the DOM

```css
.entry summary{display:flex; gap:.6rem; align-items:baseline; list-style:none; cursor:pointer}
.entry summary::-webkit-details-marker{display:none}
.entry .title{flex:1; min-width:0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis}
.entry details[open] .title{white-space:normal; overflow:visible}
```

Two corrections from round 1, both measured against the emitted DOM:

- `flex:1; min-width:0` is **required** *(Codex Blocking 1)*. A flex item's default `min-width:auto`
  refuses to shrink below its content, so `text-overflow:ellipsis` never engages in a flex row.
- The un-clip selector is `.entry details[open] .title`, **not** `details[open] .entry .title`
  *(Codex Blocking 1, Claude L1 — agreeing)*. `.entry` is the article, an **ancestor** of the fold; the
  original selector looked for it as a descendant and matched nothing.

The clipped remainder is present in the document, so in-page find (Cmd-F) still locates it and the
browser scrolls it into view. Opening a card un-clips **that card's own** title, which wraps in full
above its prose.

The triangle is `aria-hidden`: `<summary>` already exposes its expanded state to assistive technology,
so a second announcement would be noise, not access.

### 2d. The expanded body

The prose appears **directly**, with no `What this means` label. The `<h3>` above it is now the
disclosure's heading, so that label would be a second control naming the same thing.

`Raw technical detail` stays a nested `<details id="{eid}-tech">` at the end of the prose — a fold
inside a fold, which is what the user asked for and what the content is: detail behind detail.

### 2e. A broken entry does not fold

An entry that failed to parse (`class="entry broken"`, `:983-988`) keeps rendering its error and its
raw text **open and unfoldable** — it emits no `<details>` at all. Hiding a parse failure behind a
click makes a problem quieter instead of louder.

### 2f. ⛔ A row with nothing behind it has no triangle

*(r1: Claude B1 — a defect the collapse itself creates.)* **Measured:**

```
entry: "## 2026-08-31\nThe page can no longer contradict itself.\n"
  title: 'The page can no longer contradict itself.'
  prose: '<p class="lede">The page can no longer contradict itself.</p>'
  tech : None
```

`_prose` **deliberately keeps** that repetition: the drop is guarded by `elif len(paras) > 1`
(`:250-265`), whose comment says the fold must not open empty because *"the reader is worse off than
with the repetition"*. Sound while the title was fully visible beside a small fold. Once the triangle
is the card's only affordance, it advertises hidden content and returns the line just read.

**Rule** *(narrowed in v3; round 2 found the v2 wording could hide the raw technical detail)*:

> **Suppress the fold iff the rendered prose is empty AND the entry has no tech block.** Then emit the
> row as a plain non-interactive line — **no `<details>`, no triangle** — with the `<h3>` and the
> article id unchanged.

When the prose is empty but a tech block exists, the fold **stays**, and the empty
`<div class="prose">` is **omitted** — the fold contains the nested tech fold alone.

A disclosure that discloses nothing is a lie about the content. But a row that hides the only route to
the raw detail is worse, and v2's wording did exactly that — see §8 for the reproduced probe.

**There is no text comparison.** v2 also suppressed when the body's tag-stripped text *equalled* the
title's, which was (a) unspecifiable — the two sides are produced by different functions with
different whitespace handling, so `Same  title.` versus `Same title.` and a `**bold**` span were all
undefined — and (b) unnecessary, once §3a's COUPLING 3 makes the prose genuinely empty in that case.
Emptiness needs no normalisation rules; an equality test needs several, and each is a place to be
wrong.

### 2g. Everything else starts collapsed

No exception for the newest entry, and none for a `needs you` badge: anything genuinely waiting on the
reader is already listed in the **What needs you** tray above this section, so opening a card by
default would duplicate that, not add to it.

---

## 3. The truncation fix — delete the cap, not patch around it

`:428` stops capping. `entry["title"]` becomes the full first sentence.

With §2c's CSS owning the visible clip, `TITLE_CAP` has no reader left. Its only remaining effect is
the content loss in §1c, so the following are **deleted**, not disabled.

### 3a. The deletion cascade, and the two couplings that make it dangerous

```
TITLE_CAP + the truncation branch of _first_sentence   (:141-158, from `if len(out) > cap:`)
  └─ gen-dashboard._close_orphan_markup                (:171-201) — sole caller is that branch (:157)
       └─ gen-dashboard._orphaned_delimiters           (:162-168) — sole callers are :193, :196
            └─ page_markup.orphaned_delimiters         (:253-264) — whose docstring says, correctly,
                                                        "Its one consumer is
                                                        gen-dashboard._close_orphan_markup"
```

*(r1: Codex L6, **escalated to High here** — it makes §6's blast radius false, and a wrong blast radius
sends the next reviewer to the wrong file.)* The whole chain goes, including
`page_markup.orphaned_delimiters` and its **4** self-test cases (`page_markup.py:436-439`). Measured:
`page_markup.json` holds 14 mutations and **none** name `orphaned_delimiters`, so page_markup's
mutation count is unaffected by its removal.

> **Alternative considered and rejected:** keep `orphaned_delimiters` with a corrected docstring
> recording that it has no consumer. Rejected because a primitive nothing calls, documented against a
> function that no longer exists, is the precise defect Codex flagged; git restores it if a future
> truncation policy needs it.

**⚠ COUPLING 1 — `_prose` must stop passing `cap=`** *(r1: Codex H2).* `_prose` calls
`_first_sentence(first, cap=len(first))` (`:252`). An implementer who deletes the `cap` parameter along
with `TITLE_CAP` makes **every normal entry** raise
`TypeError: _first_sentence() got an unexpected keyword argument 'cap'`. Either the parameter stays as
a no-op or `_prose` calls `_first_sentence(first)`. **This spec requires the latter** — a no-op
parameter is a reader trap — and requires a case that renders a complete normal entry, which no
existing case does at that granularity.

**⚠ COUPLING 2 — the no-terminator guard must relax in the SAME commit** *(r1: Claude B2).*
**Measured**, with the cap simulated away:

```
para = 159 chars, no '.', '?' or '!'
  UNcapped title: the whole paragraph
  prose still contains the paragraph?  True
```

`drop_headline` refuses to drop when the first paragraph has no terminator (`:250-258`), and its case
at `:2087-2091` states the reason: dropping it *"while the title showed only TITLE_CAP characters"*
deleted unseen text. **The cap is that guard's entire premise.** Uncapped, the title always shows the
paragraph whole, so dropping loses nothing — and *not* dropping renders an unbounded paragraph twice.

So: delete the no-terminator refusal and its case, and let §2f suppress the fold for an entry that
then has nothing behind it. Ship the cap deletion alone → text duplicates on the page. Ship the guard
relaxation alone → §1c's content loss returns. **Same commit, or neither.**

**⚠ COUPLING 3 — the `else` branch pops, and its comment must be rewritten** *(r2: Claude H1).*
`_prose`'s tail (`:265-271`) keeps the first paragraph when nothing else remains, and states why:

```python
# else: the headline is the entire entry. Keep it — an empty fold is worse than a repeated
# sentence, and there is nothing else to show.
```

**§2f overturns that premise:** with no fold, an empty fold is not the alternative — a plain row is.
So the branch pops unconditionally. **Measured**, simulating the pop:

```
single sentence  -> paras after drop: []
sentence + para  -> paras after drop: ['Second paragraph.']
no terminator    -> paras after drop: []
markup only      -> paras after drop: []
```

The prose comes back genuinely empty in every shape that previously repeated, which is what lets §2f
test emptiness instead of comparing strings.

**The comment is load-bearing documentation of a decision this slice reverses, and rewriting it is
part of the change, not tidying.** Changing the behaviour and leaving the comment would leave the file
arguing against its own code.

### 3b. The mutation-count revision, stated as a rule not a number

`EXPECTED_MUTATIONS` in `scripts/check-plan-code.py` pins `gen-dashboard` at **56** and `page_markup`
at **14** (measured 2026-08-31, alongside 242 gen-dashboard self-test cases). Three gen-dashboard
entries die with the code they guard — *"a truncated headline is not re-balanced, so an orphan
delimiter ships"*, *"the orphan closer becomes a SECOND scanner again, disagreeing on code"*, *"closers
are appended PAST the cap, so TITLE_CAP stops bounding"* — and this slice adds entries for §4's new
properties.

The comparison is **exact equality**, not a floor: `if got != want:` (`check-plan-code.py:540`), with
the drift message requiring the pin to move *"in the SAME commit"* (`:543`). The codebase's rule is
that coverage cannot shrink **unnoticed** (`:547`), not that it cannot shrink.

**The new pin is whatever `--mutate .` measures after the change, recorded with a comment naming the
three deleted entries and why they went.** This spec deliberately does not predict the number: a count
pinned to a past event must not be "corrected" to a number nobody ran, and the difference between
*coverage deleted with its code* and *coverage quietly narrowed* is exactly what the comment carries.

---

## 4. Falsifiers — the observation that makes each one FAIL

*(r1: Codex H4 and Claude M1/M2 rebuilt this section. The originals were vacuous in the way this
codebase has already been bitten by: `gen-dashboard.py:1520-1525` records a bare `"<details" in html`
assertion that passed with the tech fold **deleted**, because the glossary always emits one.)*

**Every case below obeys three rules, and a case that does not is not a falsifier:**

1. **Parse to a fragment.** Assert against the markup of **one synthetic entry**, located by its own
   `id`, never against the whole page — the ask tray and the glossary satisfy page-wide substring
   tests independently of entry cards.
2. **Positive existence first.** Before asserting a property, assert the thing exists:
   `details id="{eid}-card"`, its `summary`, its `h3`, its `.title`, its badge, its nested
   `{eid}-tech`. An assertion over an absent fixture passes while the feature is missing.
3. **Unique sentinels.** Fixture text must not occur in the glossary, the tray, or another fixture.

| # | Property | Fails when |
|---|---|---|
| F1 | A long first sentence reaches the reader whole | the sentence, **tag-stripped**, is not in the card fragment. One fixture's first sentence carries both a `**` span and a backtick span — the two delimiters the deleted repair handled |
| F2 | The date appears once in what the reader sees | the date occurs more than once in the summary's **visible text**, tags stripped. ⚠ It legitimately occurs **5×** in one card's markup — `day-<date>`, the article id, the fold id and the visible id — so this can only be asserted on text |
| F3 | The badge is on the collapsed row | the badge markup is not between `<summary>` and `</summary>` of the located fold |
| F4 | The tech fold nests inside the entry fold | `{eid}-tech` is not within the `{eid}-card` fold's boundaries |
| F5 | A broken entry is not foldable | a `class="entry broken"` fragment contains `<details` |
| F6 | Cards are shut by default | any entry fold renders with `open` |
| F7 | The title clip is CSS, not a character cap | a rendered title ends in `…` the author did not write, for a fixture whose first sentence exceeds 110 characters |
| F8 | An entry whose body adds nothing has no fold | a single-sentence, **no-tech** fixture emits `<details` or a triangle (§2f) |
| F8b | …but a tech block always keeps its route | a single-sentence fixture **with** a unique `<!--tech-->` block fails to emit both `{eid}-card` and a nested `{eid}-tech` (§2f; this is the defect r2 found in v2) |
| F8c | No empty prose container | a fixture with empty prose and a tech block emits `<div class="prose"></div>` (§2f) |
| F9 | The entry anchor still resolves | any *What needs you* link's target id is absent from the What changed section (§2b) |
| F10 | Entry-level headings survive | the count of `<h3` in the What changed section is not one per non-broken entry (§2a) |
| F11 | A complete normal entry renders at all | building a page with one ordinary entry raises (§3a, coupling 1) |
| F12 | Every `<details>` has an id | *(existing, `:1701`)* the counts diverge |
| F13 | No duplicate DOM ids | *(existing)* the id set is smaller than the id list |

**One existing case must be kept and extended, not deleted:** `:1525`, *"tech is behind a fold"*, pins
`<details id="{eid}-tech">`. The id survives, so the case survives — but its comment explains that the
assertion was narrowed *away* from a bare `"<details" in html` because the glossary always emits one,
and after this change the **entry card emits one too**, which makes the bare form wrong in a second
way. Extend the comment; do not drop the history.

---

## 5. Out of scope

- The **What needs you** tray, the **Worth knowing** block, the chart, and the glossary fold are
  untouched. Only the *What changed* cards collapse.
- No expand-all / collapse-all control. One more piece of state to get wrong, and find-in-page already
  reaches clipped titles (§2c).
- No deep-link auto-open. `#day-<date>` and `#{eid}` anchors land on a row, which is legible collapsed;
  forcing a targeted card open needs JS for a case nobody has reported.
- **The 4 `orphaned_delimiters` cases carry no mutations at all** (measured, §3a). That is a
  pre-existing coverage gap in `page_markup`, and deleting the function retires it rather than fixing
  it. Not this slice's job; noted so the retirement is not mistaken for a fix.
- Backlog #78 (the entry gate cannot see entry-only branches) is unrelated and stays open.

---

## 6. Blast radius

**Two files, not one** *(corrected in v2; v1 wrongly said `page_markup.py` was untouched)*:

- `scripts/gen-dashboard.py` — the only emitter of these cards, verified by
  `grep -rn 'class="entry' scripts/`, which returns only that file's two sites. `brief-compose.py`
  composes the page but renders no entry cards.
- `scripts/page_markup.py` — loses `orphaned_delimiters` and its 4 cases (§3a). `_inline` and every
  other shared renderer is untouched: this slice changes card *structure*, not inline markup.

Plus `scripts/mutations/gen-dashboard.json` and the `EXPECTED_MUTATIONS` pin (§3b).

The page is derived and regenerated by hook, never hand-edited, so shipping it means regenerating and
looking at it in a browser — §4's falsifiers are necessary and not sufficient. Neither review half
observed `text-overflow: ellipsis` inside a flex `<summary>` in a real browser; Phase 4 must.

---

## 7. Round 1 — what each half caught, and why both were needed

Both halves returned **NOT CONVERGED**. They agreed on three findings and each found things the other
missed, which is the fourth time this project has measured that the halves are not redundant.

| Finding | Codex | Claude | Where it landed |
|---|---|---|---|
| Un-clip selector cannot match | **Blocking** | Low | §2c |
| …and flex needs `flex:1; min-width:0` | **Blocking** | *missed* | §2c |
| `<summary>` content model / heading semantics | High | High | §2a |
| Falsifiers pass vacuously | High *(all of F2–F9, systematically)* | Medium *(F1, F2)* | §4, rebuilt |
| `_prose` still passes `cap=` → `TypeError` | **High** | *missed* | §3a, coupling 1 |
| Tray anchor `#{eid}` can be broken | **Medium** | *missed* | §2b |
| Deletion orphans `page_markup.orphaned_delimiters` | Low | *missed* | §3a, **escalated to High** |
| A fold that discloses nothing (single-sentence entry) | *missed* | **Blocking** | §2f |
| Uncapped title duplicates an unterminated paragraph | *missed* | **Blocking** | §3a, coupling 2 |

**Codex executed; the Claude half did not.** Codex ran `--self-test` (266/266) and `--mutate .`
(120 mutations, 0 survivors) against the current tree. It also reached the frontier model by
fallthrough — `gpt-5.6-sol`, `-terra`, `-luna` each returned HTTP 400 before `gpt-5.5` took the run,
which is `scripts/codex-review.py` behaving exactly as designed.

⚠ **The Claude half was COORDINATOR-run, not a dispatched subagent** — a session constraint, not a
choice. The previous session measured the dispatched half out-finding the coordinator in all three of
its rounds. Its two Blockings here were both real, but treat it as the weaker instrument and prefer a
dispatched half for round 2.

---

## 8. Round 2 — scoped to round 1's own fixes, and it paid

Round 2 deliberately did **not** re-read the whole document. It attacked only what round 1 added,
because the immediately preceding slice measured that every round-2 Blocking was a regression from
round 1's own fix. Both halves returned 0 Blocking and converged on one High.

| Finding | Codex | Claude | Where it landed |
|---|---|---|---|
| §2f can suppress the only route to the tech block | **High** | **High** *(reproduced independently)* | §2f, **narrowed** |
| §2f's tag-stripped equality was never specifiable | *implied* | Medium | §2f, comparison **deleted** |
| Nothing says whether an empty prose div is emitted | *missed* | Medium | §2f + F8c |
| §6 still said 5 `orphaned_delimiters` cases | Low | Low | §6, now 4 |
| Couplings 1 and 2, the cascade, §2b, §4's fragment boundary, F10's scope | **verified correct, by execution** | verified correct | unchanged |

**The reproduced probe** — v2's §2f, on an entry with one plain sentence and a tech block:

```
title            : 'Same title.'
prose stripped   : 'Same title.'
tech             : 'raw unique detail'
prose == title?    True
-> v2 §2f would SUPPRESS the fold and take the tech with it: True
```

**Why the fix is a deletion, not a widening.** Codex proposed comparing over the complete hidden
payload. That works, but it keeps a string comparison whose normalisation v2 never defined. Instead,
COUPLING 3 makes `_prose` return genuinely empty text in the repeating case, so §2f tests emptiness —
which has no normalisation rules at all. **v3's rule is one clause shorter than v2's and covers a case
v2 got wrong.**

**Codex executed, again:** `gen-dashboard --self-test` 266/266, `page_markup --self-test` 78/78,
`check-plan-code --mutate .` 5 files / 120 mutations / 0 survivors. It also confirmed there is no
case-count pin on `page_markup` in CI (`.github/workflows/ci.yml:195-196`) that the deletion would
break — a question §3a raised and neither half had answered.

⚠ Both Claude halves were **coordinator-run**, not dispatched subagents (session constraint). Both
found real defects the executing half missed, but the previous session measured a dispatched half
out-finding the coordinator in three of three rounds. If a round 3 becomes necessary, dispatch it.
